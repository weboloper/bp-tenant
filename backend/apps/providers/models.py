from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseProvider(models.Model):
    """Abstract base class for all communication providers"""
    name = models.CharField(_('Provider Name'), max_length=50)
    code = models.CharField(
        _('Provider Code'),
        max_length=50,
        unique=True,
        help_text=_('Unique identifier (e.g., netgsm, twilio, sendgrid)')
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    priority = models.PositiveIntegerField(
        _('Priority'),
        default=0,
        help_text=_('Higher number = higher priority')
    )
    config = models.JSONField(
        _('Configuration'),
        default=dict,
        blank=True,
        help_text=_('Provider-specific configuration (API keys, credentials, etc.)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-priority', 'name']

    def __str__(self):
        status = _('Active') if self.is_active else _('Inactive')
        return f"{self.name} ({status})"


class SmsProvider(BaseProvider):
    """SMS service provider configuration (NetGSM, Twilio, etc.)"""

    class Meta:
        verbose_name = _('SMS Provider')
        verbose_name_plural = _('SMS Providers')


class EmailProvider(BaseProvider):
    """Email service provider configuration (SMTP, SendGrid, AWS SES, etc.)"""

    class Meta:
        verbose_name = _('Email Provider')
        verbose_name_plural = _('Email Providers')


class PushProvider(BaseProvider):
    """Push notification provider configuration (FCM, APNS, OneSignal, etc.)"""

    class Meta:
        verbose_name = _('Push Provider')
        verbose_name_plural = _('Push Providers')
