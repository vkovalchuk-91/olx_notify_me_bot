from django.contrib import admin

from .models import JobLog


@admin.register(JobLog)
class JobLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'level', 'source', 'job_name', 'message_preview')
    list_filter = ('level', 'source', 'job_name')
    search_fields = ('message', 'logger_name', 'job_name')
    readonly_fields = ('level', 'source', 'logger_name', 'message', 'job_name', 'created_at')
    date_hierarchy = 'created_at'

    def message_preview(self, obj):
        return obj.message[:120]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
