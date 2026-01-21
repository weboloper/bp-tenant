from django.db import models
from django.utils.translation import gettext_lazy as _

from core.mixins import TimestampMixin
from core.choices import StatusChoices, ChannelChoices, MessageTypeChoices


class OutboundMessage(TimestampMixin, models.Model):
    """
    External message record for SMS/WhatsApp/Telegram.
    Tracks credit usage, delivery status, and provider responses.

    Renamed from 'Message' for clarity - represents messages sent
    from the system to external recipients.
    """

    # Sender (Company/Tenant)
    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='outbound_messages',
        verbose_name=_('Company')
    )

    # Recipient
    recipient_phone = models.CharField(_('Recipient Phone'), max_length=20)
    recipient_name = models.CharField(_('Recipient Name'), max_length=200, blank=True)

    # Content
    content = models.TextField(_('Message Content'))

    # Channel and Type
    channel = models.CharField(
        _('Channel'),
        max_length=20,
        choices=ChannelChoices.choices,
        default=ChannelChoices.SMS
    )
    message_type = models.CharField(
        _('Message Type'),
        max_length=30,
        choices=MessageTypeChoices.choices,
        default=MessageTypeChoices.TRANSACTIONAL
    )

    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )

    # Provider info
    provider_name = models.CharField(
        _('Provider Name'),
        max_length=50,
        blank=True,
        help_text=_('SMS provider name (e.g., netgsm, twilio)')
    )
    provider_message_id = models.CharField(
        _('Provider Message ID'),
        max_length=255,
        blank=True,
        db_index=True
    )
    provider_response = models.JSONField(
        _('Provider Response'),
        null=True,
        blank=True,
        help_text=_('Raw response from the provider')
    )

    # Credit tracking
    credits_used = models.PositiveIntegerField(_('Credits Used'), default=1)

    # Timestamps
    scheduled_at = models.DateTimeField(_('Scheduled At'), null=True, blank=True)
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)

    # Error tracking
    error_message = models.TextField(_('Error Message'), blank=True)
    retry_count = models.PositiveIntegerField(_('Retry Count'), default=0)
    max_retries = models.PositiveIntegerField(_('Max Retries'), default=3)

    # Related notification (optional)
    notification = models.ForeignKey(
        'communications.Notification',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outbound_messages',
        verbose_name=_('Related Notification')
    )

    # Metadata
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional data related to this message')
    )

    class Meta:
        verbose_name = _('Outbound Message')
        verbose_name_plural = _('Outbound Messages')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status', 'created_at']),
            models.Index(fields=['provider_message_id']),
            models.Index(fields=['recipient_phone', 'created_at']),
        ]

    def __str__(self):
        return f"{self.channel.upper()} to {self.recipient_phone} - {self.status}"

    @property
    def can_retry(self):
        """Check if this message can be retried"""
        return (
            self.status == StatusChoices.FAILED and
            self.retry_count < self.max_retries
        )
