from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import time


class NotificationPreference(models.Model):
    """
    User notification preferences.
    Controls opt-in/opt-out per channel and notification type,
    plus quiet hours and frequency settings.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('User')
    )

    # Global channel toggles
    in_app_enabled = models.BooleanField(_('In-App Enabled'), default=True)
    email_enabled = models.BooleanField(_('Email Enabled'), default=True)
    push_enabled = models.BooleanField(_('Push Enabled'), default=False)
    sms_enabled = models.BooleanField(_('SMS Enabled'), default=True)

    # Type-specific preferences
    type_preferences = models.JSONField(
        _('Type Preferences'),
        default=dict,
        blank=True,
        help_text=_("{ 'appointment_reminder': {'email': True, 'push': False}, ... }")
    )

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(_('Quiet Hours Enabled'), default=False)
    quiet_hours_start = models.TimeField(_('Quiet Hours Start'), default=time(22, 0))
    quiet_hours_end = models.TimeField(_('Quiet Hours End'), default=time(8, 0))

    # Frequency control
    daily_digest_enabled = models.BooleanField(
        _('Daily Digest Enabled'),
        default=False,
        help_text=_('Bundle multiple notifications into a single digest')
    )
    max_notifications_per_day = models.PositiveIntegerField(
        _('Max Notifications Per Day'),
        default=50
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')

    def __str__(self):
        return f"{self.user.username} - Notification Preferences"

    def is_channel_enabled(self, notification_type, channel):
        """
        Check if user allows notification of this type via this channel.

        Args:
            notification_type: Type of notification
            channel: Channel to check ('in_app', 'email', 'push', 'sms')

        Returns:
            True if notification can be sent via this channel
        """
        # Check global channel toggle
        channel_toggles = {
            'in_app': self.in_app_enabled,
            'email': self.email_enabled,
            'push': self.push_enabled,
            'sms': self.sms_enabled,
        }

        if not channel_toggles.get(channel, True):
            return False

        # Check type-specific preference
        type_prefs = self.type_preferences.get(notification_type, {})
        return type_prefs.get(channel, True)  # Default: enabled

    def is_quiet_hours(self):
        """
        Check if current time is within quiet hours.

        Returns:
            True if notifications should be held for later
        """
        if not self.quiet_hours_enabled:
            return False

        now = timezone.now().time()
        start = self.quiet_hours_start
        end = self.quiet_hours_end

        if start < end:
            # Normal range (e.g., 09:00 - 17:00)
            return start <= now <= end
        else:
            # Overnight range (e.g., 22:00 - 08:00)
            return now >= start or now <= end

    def should_send_digest(self, notification_type):
        """
        Check if this notification type should be bundled into daily digest.

        Args:
            notification_type: Type of notification

        Returns:
            True if should be added to digest instead of sent immediately
        """
        if not self.daily_digest_enabled:
            return False

        # Could extend this to check type-specific digest preferences
        type_prefs = self.type_preferences.get(notification_type, {})
        return type_prefs.get('digest', False)
