from django.contrib import admin

from .models import CheckerQuery, FoundAd


class FoundAdInline(admin.TabularInline):
    model = FoundAd
    extra = 0
    readonly_fields = ('ad_url', 'ad_description', 'ad_price', 'currency', 'is_active', 'created_at')


@admin.register(CheckerQuery)
class CheckerQueryAdmin(admin.ModelAdmin):
    list_display = ('query_name', 'user', 'source', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('source', 'is_active', 'is_deleted')
    search_fields = ('query_name', 'query_url', 'user__username')
    inlines = [FoundAdInline]


@admin.register(FoundAd)
class FoundAdAdmin(admin.ModelAdmin):
    list_display = ('ad_url', 'query', 'ad_price', 'currency', 'is_active', 'created_at')
    list_filter = ('is_active', 'currency')
    search_fields = ('ad_url', 'ad_description')
