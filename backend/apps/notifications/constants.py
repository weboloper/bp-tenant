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
    
    # ===== TENANT → STAFF (In-App) =====
    APPOINTMENT_NEW = 'appointment_new', _('New Appointment')
    APPOINTMENT_CANCELLED = 'appointment_cancelled', _('Appointment Cancelled')
    APPOINTMENT_UPDATED = 'appointment_updated', _('Appointment Updated')
    APPOINTMENT_REMINDER_STAFF = 'appointment_reminder_staff', _('Appointment Reminder (Staff)')
    CLIENT_NEW = 'client_new', _('New Client')
    TASK_ASSIGNED = 'task_assigned', _('Task Assigned')
    
    # ===== TENANT → CLIENT (SMS/Email) =====
    APPOINTMENT_CONFIRMATION = 'appointment_confirmation', _('Appointment Confirmation')
    APPOINTMENT_REMINDER = 'appointment_reminder', _('Appointment Reminder')
    APPOINTMENT_CANCELLED_CLIENT = 'appointment_cancelled_client', _('Appointment Cancelled (Client)')
    BIRTHDAY_GREETING = 'birthday_greeting', _('Birthday Greeting')
    CAMPAIGN = 'campaign', _('Campaign')
    FEEDBACK_REQUEST = 'feedback_request', _('Feedback Request')
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
    USER = 'user', _('User (Staff)')
    CLIENT = 'client', _('Client')