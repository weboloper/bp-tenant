from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class SubscriptionPlan(models.Model):
    """System-level: Platformun sunduğu paketler"""

    BILLING_CYCLE_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name=_("Name")
    )  # Basic, Pro, Enterprise
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price")
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly',
        verbose_name=_("Billing Cycle")
    )

    # Limitler
    max_employee = models.IntegerField(verbose_name=_("Max Employees"))
    max_locations = models.IntegerField(verbose_name=_("Max Locations"))
    max_appointments_per_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Max Appointments Per Month")
    )

    # Özellikler
    has_online_booking = models.BooleanField(
        default=True,
        verbose_name=_("Has Online Booking")
    )
    has_sms_notifications = models.BooleanField(
        default=False,
        verbose_name=_("Has SMS Notifications")
    )
    has_analytics = models.BooleanField(
        default=False,
        verbose_name=_("Has Analytics")
    )

    features = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Features"),
        help_text=_("Format: {'custom_roles': bool, 'automation': bool, 'advanced_reports': bool, 'api_access': bool, 'google_calendar': bool, 'reserve_with_google': bool, 'sms_notifications': bool, 'email_notifications': bool}")
    )

    # Welcome bonus for new tenants subscribing to this plan
    welcome_sms_bonus = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Welcome SMS Bonus"),
        help_text=_("SMS credits given to new tenants when they start with this plan")
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'billing_cycle']),
            models.Index(fields=['billing_cycle', 'price']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()}"


    def has_feature(self, feature_name):
        """
        Check if package has a specific feature.

        Args:
            feature_name: str - Feature key to check

        Returns:
            bool or str - Feature value
        """
        return self.features.get(feature_name, False)

    def get_limit(self, limit_name):
        """
        Get limit value. 0 means unlimited.

        Args:
            limit_name: str - 'employee', 'locations',  'max_appointments_per_month'

        Returns:
            int - Limit value (0 = unlimited)
        """
        limit_map = {
            'employee': self.max_employee,
            'locations': self.max_locations,
            'max_appointments_per_month': self.max_appointments_per_month,
        }
        return limit_map.get(limit_name, 0)

    def is_unlimited(self, limit_name):
        """Check if limit is unlimited"""
        return self.get_limit(limit_name) == 0



class SMSPackage(models.Model):
    """
    SMS package definitions for companies to purchase.
    These are platform-level packages that companies can buy to top up their SMS credits.

    Example packages:
    - 100 SMS - 50 TL
    - 500 SMS - 200 TL
    - 1000 SMS - 350 TL
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Paket Adı"
    )

    display_name = models.CharField(
        max_length=100,
        verbose_name="Görünen Ad"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Açıklama"
    )

    # SMS credits included
    sms_credits = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="SMS Kredisi",
        help_text="Bu pakette kaç SMS kredisi var"
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Fiyat (TL)"
    )

    # Display settings
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Öne Çıkan",
        help_text="Öne çıkan paketler daha görünür bir şekilde gösterilir"
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Sıralama"
    )

    # Bonus credits (optional)
    bonus_credits = models.PositiveIntegerField(
        default=0,
        verbose_name="Bonus Kredi",
        help_text="Bu paketi alan işletmelere verilen ekstra SMS kredisi"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SMS Package"
        verbose_name_plural = "SMS Packages"
        ordering = ['sort_order', 'sms_credits']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['sms_credits']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.sms_credits} SMS - {self.price} TL)"

    def get_price_per_sms(self):
        """Calculate price per SMS credit"""
        if self.price is None or not self.sms_credits:
            return Decimal('0.00')
        return self.price / Decimal(str(self.sms_credits))

    def get_total_credits(self):
        """Get total credits including bonus"""
        return (self.sms_credits or 0) + (self.bonus_credits or 0)
