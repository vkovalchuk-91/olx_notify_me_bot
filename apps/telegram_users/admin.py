from django.contrib import admin

from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('user_telegram_id', 'username', 'full_name', 'is_active', 'created_at')
    search_fields = ('username', 'full_name', 'user_telegram_id')
    list_filter = ('is_active',)
