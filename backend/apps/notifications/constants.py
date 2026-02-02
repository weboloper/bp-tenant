# notifications/constants.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class Channel(models.TextChoices):
    """Notification delivery channels"""
    SMS = 'sms', _('SMS')
    EMAIL = 'email', _('Email')
    IN_APP = 'in_app', _('In-App')
    PUSH = 'push', _('Push')  # Future
    WHATSAPP = 'whatsapp', _('WhatsApp')  # Future


class NotificationType(models.TextChoices):
    """Notification type identifiers"""

    # ===== SYSTEM → TENANT =====
    SYSTEM_ANNOUNCEMENT = 'system_announcement', _('System Announcement')
    BILLING_ALERT = 'billing_alert', _('Billing Alert')
    SMS_CREDIT_LOW = 'sms_credit_low', _('SMS Credit Low')
    SMS_CREDIT_DEPLETED = 'sms_credit_depleted', _('SMS Credit Depleted')
    SUBSCRIPTION_EXPIRY = 'subscription_expiry', _('Subscription Expiry')
    SUBSCRIPTION_EXPIRED = 'subscription_expired', _('Subscription Expired')
    FEATURE_UPDATE = 'feature_update', _('Feature Update')

    # ===== TENANT → USER (In-App/Email/SMS) =====
    TASK_ASSIGNED = 'task_assigned', _('Task Assigned')
    CAMPAIGN = 'campaign', _('Campaign')
    CUSTOM = 'custom', _('Custom Message')


class DeliveryStatus(models.TextChoices):
    """Delivery status for outbound messages"""
    PENDING = 'pending', _('Pending')
    SENT = 'sent', _('Sent')
    DELIVERED = 'delivered', _('Delivered')
    FAILED = 'failed', _('Failed')
    REJECTED = 'rejected', _('Rejected')
    # Email specific
    OPENED = 'opened', _('Opened')
    CLICKED = 'clicked', _('Clicked')
    BOUNCED = 'bounced', _('Bounced')


class Priority(models.TextChoices):
    """Notification priority"""
    LOW = 'low', _('Low')
    NORMAL = 'normal', _('Normal')
    HIGH = 'high', _('High')
    URGENT = 'urgent', _('Urgent')


class RecipientType(models.TextChoices):
    """Who can receive notifications"""
    USER = 'user', _('User')