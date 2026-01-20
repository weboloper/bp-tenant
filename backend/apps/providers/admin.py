from django.contrib import admin
from .models import SmsProvider, EmailProvider, PushProvider


class BaseProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'priority', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['-priority', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SmsProvider)
class SmsProviderAdmin(BaseProviderAdmin):
    pass


@admin.register(EmailProvider)
class EmailProviderAdmin(BaseProviderAdmin):
    pass


@admin.register(PushProvider)
class PushProviderAdmin(BaseProviderAdmin):
    pass
