from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from apps.telegram_users.models import TelegramUser, WebRegistrationRequest


class TelegramWebRegistrationForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторіть пароль', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        token = cleaned_data.get('token')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Паролі не співпадають')

        registration_request = (
            WebRegistrationRequest.objects
            .select_related('telegram_user')
            .filter(token=token, is_used=False)
            .first()
        )
        if not registration_request:
            raise forms.ValidationError('Запит реєстрації не знайдено або вже використано')

        telegram_user = registration_request.telegram_user
        if not telegram_user or not telegram_user.is_active:
            raise forms.ValidationError('Спочатку підтвердіть реєстрацію через Telegram-бота')
        if telegram_user.web_user_id:
            raise forms.ValidationError('Для цього Telegram користувача web-акаунт уже створено')

        created_at = registration_request.created_at
        ttl_minutes = getattr(settings, 'WEB_REGISTRATION_CODE_TTL_MINUTES', 15)
        if not created_at or timezone.now() - created_at > timedelta(minutes=ttl_minutes):
            raise forms.ValidationError('Запит реєстрації застарів. Почніть реєстрацію знову')

        cleaned_data['telegram_user'] = telegram_user
        cleaned_data['registration_request'] = registration_request
        return cleaned_data

    def save(self) -> User:
        telegram_user = self.cleaned_data['telegram_user']
        username = self._build_unique_username(telegram_user)
        user = User.objects.create_user(
            username=username,
            password=self.cleaned_data['password1'],
            first_name=telegram_user.first_name or '',
            last_name=telegram_user.last_name or '',
        )
        telegram_user.web_user = user
        telegram_user.web_registration_code = ''
        telegram_user.web_registration_code_created_at = None
        telegram_user.save(
            update_fields=['web_user', 'web_registration_code', 'web_registration_code_created_at']
        )
        registration_request = self.cleaned_data['registration_request']
        registration_request.is_used = True
        registration_request.save(update_fields=['is_used', 'updated_at'])
        return user

    def _build_unique_username(self, telegram_user: TelegramUser) -> str:
        base = (telegram_user.username or f'tg_{telegram_user.user_telegram_id}').strip()
        candidate = base
        counter = 1
        while User.objects.filter(username__iexact=candidate).exists():
            counter += 1
            candidate = f'{base}_{counter}'
        return candidate


class TelegramUserAdminForm(forms.ModelForm):
    web_user_is_active = forms.BooleanField(label='Web user active', required=False)
    web_user_is_staff = forms.BooleanField(label='Admin/staff', required=False)

    class Meta:
        model = TelegramUser
        fields = ('username', 'full_name', 'first_name', 'last_name', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        web_user = self.instance.web_user
        if web_user:
            self.fields['web_user_is_active'].initial = web_user.is_active
            self.fields['web_user_is_staff'].initial = web_user.is_staff
        else:
            self.fields['web_user_is_active'].disabled = True
            self.fields['web_user_is_staff'].disabled = True
            self.fields['web_user_is_active'].help_text = 'Web-акаунт ще не створено'

    def save(self, commit=True):
        telegram_user = super().save(commit=commit)
        web_user = telegram_user.web_user
        if web_user:
            web_user.is_active = self.cleaned_data['web_user_is_active']
            web_user.is_staff = self.cleaned_data['web_user_is_staff']
            web_user.save(update_fields=['is_active', 'is_staff'])
        return telegram_user
