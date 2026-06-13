from django.db import models


class TelegramUser(models.Model):
    user_telegram_id = models.BigIntegerField(primary_key=True)
    web_user = models.OneToOneField(
        'auth.User',
        on_delete=models.SET_NULL,
        related_name='telegram_profile',
        blank=True,
        null=True,
    )
    username = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    web_registration_code = models.CharField(max_length=12, blank=True, default='')
    web_registration_code_created_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'telegram_user'
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name or self.username or str(self.user_telegram_id)


class WebRegistrationRequest(models.Model):
    token = models.CharField(max_length=64, unique=True)
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        related_name='web_registration_requests',
        blank=True,
        null=True,
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'web_registration_request'
        ordering = ['-created_at']

    def __str__(self):
        return self.token
