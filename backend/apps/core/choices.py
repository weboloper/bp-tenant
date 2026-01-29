from django.db import models
from django.utils.translation import gettext_lazy as _


class StatusChoices(models.TextChoices):
    """Common status choices for messaging and notifications"""
    PENDING = 'pending', _('Pending')
    SENT = 'sent', _('Sent')
    DELIVERED = 'delivered', _('Delivered')
    FAILED = 'failed', _('Failed')
    READ = 'read', _('Read')
    REJECTED = 'rejected', _('Rejected')


class ChannelChoices(models.TextChoices):
    """Communication channel choices"""
    SMS = 'sms', _('SMS')
    EMAIL = 'email', _('Email')
    PUSH = 'push', _('Push Notification')
    WHATSAPP = 'whatsapp', _('WhatsApp')
    TELEGRAM = 'telegram', _('Telegram')
    IN_APP = 'in_app', _('In-App')


class PriorityChoices(models.TextChoices):
    """Message/notification priority choices"""
    LOW = 'low', _('Low')
    NORMAL = 'normal', _('Normal')
    HIGH = 'high', _('High')
    URGENT = 'urgent', _('Urgent')


class MessageTypeChoices(models.TextChoices):
    """Outbound message type choices"""
    TRANSACTIONAL = 'transactional', _('Transactional')
    PROMOTIONAL = 'promotional', _('Promotional')
    OTP = 'otp', _('OTP Verification')
    NOTIFICATION = 'notification', _('Notification')


class NotificationTypeChoices(models.TextChoices):
    """Notification type choices"""
    # System -> Tenant
    SYSTEM_ANNOUNCEMENT = 'system_announcement', _('System Announcement')
    BILLING_ALERT = 'billing_alert', _('Billing Alert')
    FEATURE_UPDATE = 'feature_update', _('Feature Update')
    SUBSCRIPTION_EXPIRY = 'subscription_expiry', _('Subscription Expiry Warning')

    # Tenant -> Client
    APPOINTMENT_REMINDER = 'appointment_reminder', _('Appointment Reminder')
    APPOINTMENT_CONFIRMATION = 'appointment_confirmation', _('Appointment Confirmation')
    APPOINTMENT_CANCELLED = 'appointment_cancelled', _('Appointment Cancelled')
    BIRTHDAY_GREETING = 'birthday_greeting', _('Birthday Greeting')
    PROMOTION = 'promotion', _('Promotion')
    FEEDBACK_REQUEST = 'feedback_request', _('Feedback Request')

    # System -> Client
    PLATFORM_UPDATE = 'platform_update', _('Platform Update')
    MAINTENANCE = 'maintenance', _('Maintenance Notice')
    NEW_FEATURE = 'new_feature', _('New Feature Announcement')


class SmsTransactionTypeChoices(models.TextChoices):
    """SMS credit transaction type choices"""
    PURCHASE = 'purchase', _('Purchase')
    USAGE = 'usage', _('Usage')
    REFUND = 'refund', _('Refund')
    ADMIN_ADJUSTMENT = 'admin_adjustment', _('Admin Adjustment')
    BONUS = 'bonus', _('Bonus')


class ColorChoices(models.TextChoices):
    """Color choices for tags and categories"""
    LIGHT_BLUE = '#93C5FD', _('Light Blue')
    DARK_BLUE = '#3B82F6', _('Dark Blue')
    SKY_BLUE = '#7DD3FC', _('Sky Blue')
    INDIGO = '#818CF8', _('Indigo')
    LAVENDER = '#C4B5FD', _('Lavender')
    PURPLE = '#A78BFA', _('Purple')
    LILAC = '#C084FC', _('Lilac')
    PINK = '#F9A8D4', _('Pink')
    CORAL = '#FB923C', _('Coral')
    DEEP_ORANGE = '#F97316', _('Deep Orange')
    ORANGE = '#FDBA74', _('Orange')
    AMBER = '#FCD34D', _('Amber')
    YELLOW = '#FDE047', _('Yellow')
    LIME = '#BEF264', _('Lime')
    GREEN = '#86EFAC', _('Green')
    TEAL = '#5EEAD4', _('Teal')
    CYAN = '#67E8F9', _('Cyan')


class CurrencyChoices(models.TextChoices):
    """Supported currencies"""
    # USD = 'USD', _('USD')
    TRY = 'TRY', _('TRY')


class PhoneCodeChoices(models.TextChoices):
    """Supported phone codes"""
    TURKEY = '+90', _('Turkey')
    # USA = '+1', _('USA')
