from django.contrib import admin

from .models import InstaContent, InstaObservedUser, InstaSubscription


@admin.register(InstaObservedUser)
class InstaObservedUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('username',)
    list_filter = ('is_active', 'is_deleted')


@admin.register(InstaSubscription)
class InstaSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('observed_user', 'user', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('is_active', 'is_deleted')
    search_fields = ('observed_user__username', 'user__username', 'user__full_name')


@admin.register(InstaContent)
class InstaContentAdmin(admin.ModelAdmin):
    list_display = ('observed_user', 'content_type', 'media_type', 'file_name', 'created_at')
    list_filter = ('content_type', 'media_type')
    search_fields = ('file_name', 'observed_user__username')
