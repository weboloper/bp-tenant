from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from communications.models import (
    OutboundMessage,
    Notification,
    MessageTemplate,
    NotificationTemplate,
    NotificationPreference,
    DeliveryLog,
)
from communications.services.messaging import MessagingService


# ============================================================================
# SMS Serializers
# ============================================================================

class SendSMSSerializer(serializers.Serializer):
    """Serializer for sending single SMS"""
    phone = serializers.CharField(
        max_length=20,
        help_text=_("Recipient phone number (e.g., +905551234567)")
    )
    message = serializers.CharField(
        max_length=918,  # 6 SMS parts max
        help_text=_("SMS content (max 918 chars for 6 parts)")
    )
    message_type = serializers.ChoiceField(
        choices=['transactional', 'promotional', 'otp', 'notification'],
        default='transactional'
    )
    sender_id = serializers.CharField(
        max_length=11,
        required=False,
        allow_blank=True,
        help_text=_("Custom sender ID (optional)")
    )

    def validate_phone(self, value):
        """Validate phone number format"""
        if not MessagingService.validate_phone(value):
            raise serializers.ValidationError(
                _("Invalid phone number format. Use +905XXXXXXXXX")
            )
        return value


class BulkSMSSerializer(serializers.Serializer):
    """Serializer for sending bulk SMS"""
    recipients = serializers.ListField(
        child=serializers.CharField(max_length=20),
        min_length=1,
        max_length=1000,
        help_text=_("List of phone numbers (max 1000)")
    )
    message = serializers.CharField(
        max_length=918,
        help_text=_("SMS content")
    )
    message_type = serializers.ChoiceField(
        choices=['transactional', 'promotional', 'otp', 'notification'],
        default='promotional'
    )
    sender_id = serializers.CharField(
        max_length=11,
        required=False,
        allow_blank=True
    )

    def validate_recipients(self, value):
        """Validate all phone numbers"""
        invalid = [p for p in value if not MessagingService.validate_phone(p)]
        if invalid:
            raise serializers.ValidationError(
                _("Invalid phone numbers: %(phones)s") % {'phones': ', '.join(invalid[:5])}
            )
        return value


class SMSCreditCalculateSerializer(serializers.Serializer):
    """Serializer for calculating SMS credits"""
    message = serializers.CharField(help_text=_("Message content"))


class SMSCreditCalculateResponseSerializer(serializers.Serializer):
    """Response serializer for credit calculation"""
    credits = serializers.IntegerField()
    char_count = serializers.IntegerField()
    parts = serializers.IntegerField()
    encoding = serializers.CharField()


# ============================================================================
# OutboundMessage Serializers
# ============================================================================

class OutboundMessageSerializer(serializers.ModelSerializer):
    """Serializer for outbound messages (SMS/WhatsApp)"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)

    class Meta:
        model = OutboundMessage
        fields = [
            'id', 'company', 'recipient_phone', 'recipient_name',
            'content', 'channel', 'channel_display',
            'message_type', 'message_type_display',
            'status', 'status_display',
            'provider_name', 'provider_message_id',
            'credits_used', 'scheduled_at', 'sent_at', 'delivered_at',
            'error_message', 'retry_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'company', 'provider_name', 'provider_message_id',
            'credits_used', 'sent_at', 'delivered_at',
            'error_message', 'retry_count', 'created_at', 'updated_at'
        ]


class OutboundMessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message listing"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OutboundMessage
        fields = [
            'id', 'recipient_phone', 'channel', 'status', 'status_display',
            'credits_used', 'sent_at', 'created_at'
        ]


# ============================================================================
# Notification Serializers
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """Full notification serializer"""
    sender_display = serializers.CharField(source='get_sender_display', read_only=True)
    recipient_display = serializers.CharField(source='get_recipient_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message',
            'notification_type', 'channels', 'priority', 'priority_display',
            'status', 'status_display',
            'sender_display', 'recipient_display',
            'is_system_notification', 'is_broadcast',
            'action_url', 'action_label',
            'scheduled_at', 'sent_at', 'delivered_at', 'read_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification listing"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'notification_type', 'status', 'status_display',
            'read_at', 'created_at'
        ]


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text=_("List of notification IDs to mark as read. If empty, marks all as read.")
    )


# ============================================================================
# Template Serializers
# ============================================================================

class MessageTemplateSerializer(serializers.ModelSerializer):
    """Serializer for message templates"""
    enabled_channels = serializers.SerializerMethodField()

    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'company', 'code', 'name', 'description',
            'sms_enabled', 'sms_template',
            'whatsapp_enabled', 'whatsapp_template',
            'telegram_enabled', 'telegram_template',
            'variables', 'enabled_channels',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'company', 'created_at', 'updated_at']

    def get_enabled_channels(self, obj):
        return obj.get_enabled_channels()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates"""
    enabled_channels = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'company', 'code', 'name', 'description',
            'notification_type', 'is_system_template',
            'in_app_enabled', 'in_app_title', 'in_app_message',
            'email_enabled', 'email_subject', 'email_body_text', 'email_body_html',
            'push_enabled', 'push_title', 'push_body',
            'sms_enabled', 'sms_body',
            'variables', 'enabled_channels',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'company', 'is_system_template', 'created_at', 'updated_at']

    def get_enabled_channels(self, obj):
        return obj.get_enabled_channels()


class TemplateRenderSerializer(serializers.Serializer):
    """Serializer for template rendering"""
    context = serializers.DictField(
        child=serializers.CharField(),
        help_text=_("Variables to render in template")
    )
    channel = serializers.ChoiceField(
        choices=['sms', 'whatsapp', 'telegram', 'email', 'push', 'in_app'],
        required=False,
        help_text=_("Specific channel to render (optional)")
    )


# ============================================================================
# Preference Serializers
# ============================================================================

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user',
            'in_app_enabled', 'email_enabled', 'push_enabled', 'sms_enabled',
            'type_preferences',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'daily_digest_enabled', 'max_notifications_per_day',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


# ============================================================================
# Delivery Log Serializers
# ============================================================================

class DeliveryLogSerializer(serializers.ModelSerializer):
    """Serializer for delivery logs"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        model = DeliveryLog
        fields = [
            'id', 'company', 'channel', 'channel_display',
            'recipient', 'content',
            'provider_name', 'status', 'status_display',
            'error_message', 'message_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'company', 'created_at', 'updated_at']
