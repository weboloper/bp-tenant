from django.db import models
from django.utils.translation import gettext_lazy as _

from core.choices import StatusChoices, ChannelChoices


class DeliveryLog(models.Model):
    """
    Audit log for all message/notification deliveries.
    Tracks delivery status, provider responses, and errors.

    Renamed from NotificationLog for clarity - covers all communication types.
    """

    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='delivery_logs',
        verbose_name=_('Company'),
        help_text=_('Company that owns this log (null for system notifications)')
    )

    channel = models.CharField(
        _('Channel'),
        max_length=20,
        choices=ChannelChoices.choices,
        default=ChannelChoices.SMS
    )
    recipient = models.CharField(
        _('Recipient'),
        max_length=255,
        help_text=_('Phone number, email address, or user identifier')
    )
    content = models.TextField(_('Content'))

    # Provider references
    sms_provider = models.ForeignKey(
        'providers.SmsProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_logs',
        verbose_name=_('SMS Provider')
    )
    email_provider = models.ForeignKey(
        'providers.EmailProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_logs',
        verbose_name=_('Email Provider')
    )

    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    error_message = models.TextField(_('Error Message'), blank=True)

    # Provider response
    provider_response = models.JSONField(
        _('Provider Response'),
        default=dict,
        blank=True,
        help_text=_('Raw response from the delivery provider')
    )
    message_id = models.CharField(
        _('Message ID'),
        max_length=100,
        blank=True,
        help_text=_('External message ID from the provider')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Delivery Log')
        verbose_name_plural = _('Delivery Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'channel']),
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} -> {self.recipient} ({self.get_status_display()})"

    @property
    def is_successful(self):
        """Check if delivery was successful"""
        return self.status in [StatusChoices.SENT, StatusChoices.DELIVERED]
