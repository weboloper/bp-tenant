from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseTemplate


class MessageTemplate(BaseTemplate):
    """
    SMS/WhatsApp/Telegram message templates.
    Company-specific with variable substitution support.
    """

    # SMS
    sms_enabled = models.BooleanField(_('SMS Enabled'), default=True)
    sms_template = models.TextField(
        _('SMS Template'),
        blank=True,
        help_text=_('Max 160 chars (70 with Turkish chars)')
    )

    # WhatsApp
    whatsapp_enabled = models.BooleanField(_('WhatsApp Enabled'), default=False)
    whatsapp_template = models.TextField(_('WhatsApp Template'), blank=True)

    # Telegram
    telegram_enabled = models.BooleanField(_('Telegram Enabled'), default=False)
    telegram_template = models.TextField(_('Telegram Template'), blank=True)

    class Meta:
        verbose_name = _('Message Template')
        verbose_name_plural = _('Message Templates')
        unique_together = [('company', 'code')]

    def render(self, channel, context):
        """
        Render template for the specified channel.

        Args:
            channel: 'sms', 'whatsapp', or 'telegram'
            context: Dictionary of variables to render

        Returns:
            Rendered string or None if channel not enabled
        """
        channel_config = {
            'sms': (self.sms_enabled, self.sms_template),
            'whatsapp': (self.whatsapp_enabled, self.whatsapp_template),
            'telegram': (self.telegram_enabled, self.telegram_template),
        }

        enabled, template = channel_config.get(channel, (False, ''))
        if not enabled or not template:
            return None

        return self.render_template(template, context)

    def get_enabled_channels(self):
        """Return list of enabled channels"""
        channels = []
        if self.sms_enabled:
            channels.append('sms')
        if self.whatsapp_enabled:
            channels.append('whatsapp')
        if self.telegram_enabled:
            channels.append('telegram')
        return channels


class NotificationTemplate(BaseTemplate):
    """
    Multi-channel notification templates.
    Can be system-wide or company-specific.
    """

    notification_type = models.CharField(
        _('Notification Type'),
        max_length=50,
        help_text=_('Type of notification this template is for')
    )
    is_system_template = models.BooleanField(
        _('Is System Template'),
        default=False,
        help_text=_('System templates cannot be edited by tenants')
    )

    # In-App Notification
    in_app_enabled = models.BooleanField(_('In-App Enabled'), default=True)
    in_app_title = models.CharField(_('In-App Title'), max_length=255, blank=True)
    in_app_message = models.TextField(_('In-App Message'), blank=True)

    # Email
    email_enabled = models.BooleanField(_('Email Enabled'), default=False)
    email_subject = models.CharField(_('Email Subject'), max_length=255, blank=True)
    email_body_text = models.TextField(_('Email Body (Text)'), blank=True)
    email_body_html = models.TextField(_('Email Body (HTML)'), blank=True)

    # Push Notification
    push_enabled = models.BooleanField(_('Push Enabled'), default=False)
    push_title = models.CharField(_('Push Title'), max_length=100, blank=True)
    push_body = models.CharField(_('Push Body'), max_length=250, blank=True)

    # SMS
    sms_enabled = models.BooleanField(_('SMS Enabled'), default=False)
    sms_body = models.CharField(
        _('SMS Body'),
        max_length=160,
        blank=True,
        help_text=_('Max 160 chars (70 with Turkish chars)')
    )

    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        # FIX: Only unique_together, removed unique=True from code field
        unique_together = [('company', 'code')]

    def render(self, context):
        """
        Render all enabled channel templates.

        Args:
            context: Dictionary of variables to render

        Returns:
            Dictionary with rendered content for each enabled channel
        """
        rendered = {}

        if self.in_app_enabled:
            rendered['in_app'] = {
                'title': self.render_template(self.in_app_title, context),
                'message': self.render_template(self.in_app_message, context),
            }

        if self.email_enabled:
            rendered['email'] = {
                'subject': self.render_template(self.email_subject, context),
                'body_text': self.render_template(self.email_body_text, context),
                'body_html': self.render_template(self.email_body_html, context),
            }

        if self.push_enabled:
            rendered['push'] = {
                'title': self.render_template(self.push_title, context),
                'body': self.render_template(self.push_body, context),
            }

        if self.sms_enabled:
            rendered['sms'] = {
                'body': self.render_template(self.sms_body, context),
            }

        return rendered

    def get_enabled_channels(self):
        """Return list of enabled channels"""
        channels = []
        if self.in_app_enabled:
            channels.append('in_app')
        if self.email_enabled:
            channels.append('email')
        if self.push_enabled:
            channels.append('push')
        if self.sms_enabled:
            channels.append('sms')
        return channels
