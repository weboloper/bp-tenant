# providers/admin.py

from django.contrib import admin
from .models import SMSProviderConfig, EmailProviderConfig


@admin.register(SMSProviderConfig)
class SMSProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'is_active', 'is_default', 'updated_at']
    list_filter = ['is_active', 'is_default', 'provider']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('provider', 'is_active', 'is_default')
        }),
        ('Credentials', {
            'fields': ('credentials',),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailProviderConfig)
class EmailProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'is_active', 'is_default', 'updated_at']
    list_filter = ['is_active', 'is_default', 'provider']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('provider', 'is_active', 'is_default')
        }),
        ('Credentials', {
            'fields': ('credentials',),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )