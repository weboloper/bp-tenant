from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    OutboundMessage,
    Notification,
    MessageTemplate,
    NotificationTemplate,
    NotificationPreference,
    DeliveryLog,
)


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ['recipient_phone', 'channel', 'status', 'company', 'created_at']
    list_filter = ['channel', 'status', 'message_type', 'created_at']
    search_fields = ['recipient_phone', 'recipient_name', 'content', 'company__name']
    readonly_fields = ['created_at', 'updated_at', 'provider_response']
    raw_id_fields = ['company', 'provider', 'notification']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('company', 'recipient_phone', 'recipient_name', 'content')
        }),
        (_('Channel & Type'), {
            'fields': ('channel', 'message_type', 'status')
        }),
        (_('Provider'), {
            'fields': ('provider', 'provider_message_id', 'provider_response')
        }),
        (_('Credits & Timing'), {
            'fields': ('credits_used', 'scheduled_at', 'sent_at', 'delivered_at')
        }),
        (_('Error Tracking'), {
            'fields': ('error_message', 'retry_count', 'max_retries'),
            'classes': ('collapse',)
        }),
        (_('Related'), {
            'fields': ('notification', 'metadata'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'status', 'priority', 'get_sender', 'get_recipient', 'created_at']
    list_filter = ['notification_type', 'status', 'priority', 'is_system_notification', 'created_at']
    search_fields = ['title', 'message', 'sender_company__name', 'recipient_company__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['sender_company', 'sender_user', 'recipient_company', 'recipient_user']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('title', 'message', 'notification_type')
        }),
        (_('Sender'), {
            'fields': ('is_system_notification', 'sender_company', 'sender_user')
        }),
        (_('Recipient'), {
            'fields': ('recipient_company', 'recipient_user', 'is_broadcast', 'broadcast_target')
        }),
        (_('Delivery'), {
            'fields': ('channels', 'priority', 'status')
        }),
        (_('Timing'), {
            'fields': ('scheduled_at', 'sent_at', 'delivered_at', 'read_at')
        }),
        (_('Action'), {
            'fields': ('action_url', 'action_label'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Sender'))
    def get_sender(self, obj):
        return obj.get_sender_display()

    @admin.display(description=_('Recipient'))
    def get_recipient(self, obj):
        return obj.get_recipient_display()


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'is_active', 'get_enabled_channels_display', 'updated_at']
    list_filter = ['is_active', 'sms_enabled', 'whatsapp_enabled', 'telegram_enabled']
    search_fields = ['name', 'code', 'description', 'company__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['company']

    fieldsets = (
        (None, {
            'fields': ('company', 'code', 'name', 'description', 'is_active')
        }),
        (_('SMS'), {
            'fields': ('sms_enabled', 'sms_template')
        }),
        (_('WhatsApp'), {
            'fields': ('whatsapp_enabled', 'whatsapp_template'),
            'classes': ('collapse',)
        }),
        (_('Telegram'), {
            'fields': ('telegram_enabled', 'telegram_template'),
            'classes': ('collapse',)
        }),
        (_('Variables'), {
            'fields': ('available_variables',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Channels'))
    def get_enabled_channels_display(self, obj):
        return ', '.join(obj.get_enabled_channels()) or '-'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'notification_type', 'is_active', 'is_system_template', 'get_enabled_channels_display']
    list_filter = ['is_active', 'is_system_template', 'notification_type', 'in_app_enabled', 'email_enabled', 'push_enabled', 'sms_enabled']
    search_fields = ['name', 'code', 'description', 'company__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['company']

    fieldsets = (
        (None, {
            'fields': ('company', 'code', 'name', 'description', 'notification_type', 'is_active', 'is_system_template')
        }),
        (_('In-App'), {
            'fields': ('in_app_enabled', 'in_app_title', 'in_app_message')
        }),
        (_('Email'), {
            'fields': ('email_enabled', 'email_subject', 'email_body_text', 'email_body_html'),
            'classes': ('collapse',)
        }),
        (_('Push'), {
            'fields': ('push_enabled', 'push_title', 'push_body'),
            'classes': ('collapse',)
        }),
        (_('SMS'), {
            'fields': ('sms_enabled', 'sms_body'),
            'classes': ('collapse',)
        }),
        (_('Variables'), {
            'fields': ('available_variables',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Channels'))
    def get_enabled_channels_display(self, obj):
        return ', '.join(obj.get_enabled_channels()) or '-'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'in_app_enabled', 'email_enabled', 'push_enabled', 'sms_enabled', 'quiet_hours_enabled']
    list_filter = ['in_app_enabled', 'email_enabled', 'push_enabled', 'sms_enabled', 'quiet_hours_enabled']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']


@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'channel', 'status', 'company', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['recipient', 'content', 'company__name', 'message_id']
    readonly_fields = ['created_at', 'updated_at', 'provider_response']
    raw_id_fields = ['company', 'sms_provider', 'email_provider']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # Logs should not be manually created

    def has_change_permission(self, request, obj=None):
        return False  # Logs should be read-only
