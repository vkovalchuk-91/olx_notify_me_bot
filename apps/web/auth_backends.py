from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class CaseInsensitiveUsernameBackend(ModelBackend):
    """Authenticate usernames without case sensitivity."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if username is None or password is None:
            return None

        candidates = get_user_model()._default_manager.filter(username__iexact=username)
        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
