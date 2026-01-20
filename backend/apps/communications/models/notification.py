from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.mixins import TimestampMixin
from core.choices import StatusChoices, PriorityChoices, NotificationTypeChoices, ChannelChoices


class Notification(TimestampMixin, models.Model):
    """
    Unified notification model for all sender/recipient combinations.
    Supports system-to-tenant, tenant-to-client, and system-to-client notifications.

    Uses proper FK relationships instead of manual polymorphism for better
    referential integrity.
    """

    # Sender - Using actual FKs for referential integrity
    sender_company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender Company'),
        help_text=_('Company that sent the notification (null for system)')
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender User'),
        help_text=_('User that sent the notification (null for system/company)')
    )
    is_system_notification = models.BooleanField(
        _('Is System Notification'),
        default=False,
        help_text=_('True if sent by the platform itself')
    )

    # Recipient - Using actual FKs
    recipient_company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_notifications',
        verbose_name=_('Recipient Company')
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Recipient User')
    )
    is_broadcast = models.BooleanField(
        _('Is Broadcast'),
        default=False,
        help_text=_('True if sent to multiple recipients')
    )
    broadcast_target = models.CharField(
        _('Broadcast Target'),
        max_length=20,
        blank=True,
        choices=[
            ('all_tenants', _('All Tenants')),
            ('all_clients', _('All Clients')),
        ]
    )

    # Content
    title = models.CharField(_('Title'), max_length=255)
    message = models.TextField(_('Message'))

    # Notification Type
    notification_type = models.CharField(
        _('Notification Type'),
        max_length=50,
        choices=NotificationTypeChoices.choices
    )

    # Delivery Channels
    channels = models.JSONField(
        _('Channels'),
        default=list,
        help_text=_("List of channels: ['in_app', 'email', 'push', 'sms']")
    )

    # Priority and Status
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )

    # Timestamps
    scheduled_at = models.DateTimeField(_('Scheduled At'), null=True, blank=True)
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    read_at = models.DateTimeField(_('Read At'), null=True, blank=True)

    # Action (optional CTA)
    action_url = models.URLField(_('Action URL'), max_length=500, blank=True)
    action_label = models.CharField(_('Action Label'), max_length=50, blank=True)

    # Metadata
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional data related to this notification')
    )

    # Related object (polymorphic via GenericForeignKey)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Content Type')
    )
    object_id = models.PositiveIntegerField(_('Object ID'), null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_user', 'status']),
            models.Index(fields=['recipient_company', 'status']),
            models.Index(fields=['sender_company']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['scheduled_at', 'status']),
        ]

    def __str__(self):
        return f"{self.notification_type} - {self.title}"

    def clean(self):
        """Validate channels and sender/recipient consistency"""
        super().clean()

        # System notification should not have a sender_company
        if self.is_system_notification and self.sender_company:
            raise ValidationError({
                'sender_company': _("System notifications cannot have a sender company. "
                                    "Set sender_company to null for system notifications.")
            })

        # System notification should not have a sender_user
        if self.is_system_notification and self.sender_user:
            raise ValidationError({
                'sender_user': _("System notifications cannot have a sender user. "
                                 "Set sender_user to null for system notifications.")
            })

        # Non-system notifications must have a sender (company or user)
        if not self.is_system_notification:
            if not self.sender_company and not self.sender_user:
                raise ValidationError(
                    _("Non-system notifications must have either sender_company or sender_user. "
                      "Set is_system_notification=True for platform notifications.")
                )

        # Validate channels
        valid_channels = {c.value for c in ChannelChoices}
        if self.channels and not set(self.channels).issubset(valid_channels):
            raise ValidationError({
                'channels': _("Invalid channels. Must be subset of %(valid)s") % {'valid': valid_channels}
            })

        # Validate recipient presence (unless broadcast)
        if not self.is_broadcast:
            if not self.recipient_company and not self.recipient_user:
                raise ValidationError(
                    _("Either recipient_company or recipient_user is required for non-broadcast notifications")
                )

        # Broadcast requires broadcast_target
        if self.is_broadcast and not self.broadcast_target:
            raise ValidationError({
                'broadcast_target': _("Broadcast target is required for broadcast notifications")
            })

    def mark_as_read(self):
        """Mark notification as read"""
        if self.status != StatusChoices.READ:
            self.status = StatusChoices.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at', 'updated_at'])

    def get_sender_display(self):
        """Get human-readable sender name"""
        if self.is_system_notification:
            return _("System")
        if self.sender_company:
            return self.sender_company.name
        if self.sender_user:
            return self.sender_user.get_full_name() or self.sender_user.username
        return _("Unknown")

    def get_recipient_display(self):
        """Get human-readable recipient name"""
        if self.is_broadcast:
            return self.get_broadcast_target_display()
        if self.recipient_company:
            return self.recipient_company.name
        if self.recipient_user:
            return self.recipient_user.get_full_name() or self.recipient_user.username
        return _("Unknown")
