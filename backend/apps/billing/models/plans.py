from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class SubscriptionPlan(models.Model):
    """Platform subscription plans - defines features and limits for each tier"""

    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', _('Monthly')
        YEARLY = 'yearly', _('Yearly')

    # === BASIC INFO ===
    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True, help_text=_("URL-friendly identifier"))
    description = models.TextField(_("Description"), blank=True)

    # === PRICING ===
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(
        _("Billing Cycle"),
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )

    # === LIMITS ===
    max_employees = models.PositiveIntegerField(
        _("Max Employees"),
        default=5,
        help_text=_("Maximum number of team members")
    )

    max_products = models.PositiveIntegerField(
        _("Max Products"),
        null=True,
        blank=True,
        help_text=_("null = unlimited")
    )


    # === MODULE ACCESS (core modules - individual fields for type safety) ===

    has_inventory = models.BooleanField(
        _("Inventory Module"),
        default=False,
        help_text=_("Product stock tracking")
    )

    # === COMMUNICATION FEATURES ===
    has_sms_notifications = models.BooleanField(
        _("SMS Notifications"),
        default=False,
        help_text=_("Send SMS reminders and notifications")
    )
    has_email_notifications = models.BooleanField(
        _("Email Notifications"),
        default=True,
        help_text=_("Send email reminders and notifications")
    )


    # === EXTENDED FEATURES (rarely used, experimental - JSON for flexibility) ===
    extended_features = models.JSONField(
        _("Extended Features"),
        default=dict,
        blank=True,
        help_text=_("Additional features: {'white_label': bool, 'custom_domain': bool, 'priority_support': bool}")
    )

    # === BONUSES ===
    welcome_sms_bonus = models.PositiveIntegerField(
        _("Welcome SMS Bonus"),
        default=0,
        help_text=_("SMS credits given to new tenants when they start with this plan")
    )

    # === META ===
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_featured = models.BooleanField(
        _("Is Featured"),
        default=False,
        help_text=_("Highlight this plan in pricing pages")
    )
    sort_order = models.PositiveIntegerField(_("Sort Order"), default=0)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ['sort_order', 'price']
        indexes = [
            models.Index(fields=['is_active', 'billing_cycle']),
            models.Index(fields=['billing_cycle', 'price']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()})"

    # === HELPER METHODS ===

    def has_module(self, module_name: str) -> bool:
        """
        Check if plan has access to a module.

        Args:
            module_name: Module identifier ('services', 'products', 'pos', etc.)

        Returns:
            bool: True if module is available in this plan
        """
        module_map = {
            'inventory': self.has_inventory,
            'sms': self.has_sms_notifications,
            'email': self.has_email_notifications,
        }
        return module_map.get(module_name, False)

    def get_limit(self, limit_name: str) -> int | None:
        """
        Get limit value for a resource.

        Args:
            limit_name: Limit identifier ('employees', 'locations', etc.)

        Returns:
            int | None: Limit value (None = unlimited)
        """
        limit_map = {
            'employees': self.max_employees,
            'products': self.max_products,
        }
        return limit_map.get(limit_name)

    def is_unlimited(self, limit_name: str) -> bool:
        """
        Check if a resource limit is unlimited.

        Args:
            limit_name: Limit identifier

        Returns:
            bool: True if limit is None (unlimited)
        """
        return self.get_limit(limit_name) is None

    def has_extended_feature(self, feature_name: str) -> bool:
        """
        Check extended features from JSON field.

        Args:
            feature_name: Feature identifier ('white_label', 'custom_domain', etc.)

        Returns:
            bool: True if feature is enabled
        """
        return self.extended_features.get(feature_name, False)

    def check_limit(self, limit_name: str, current_count: int) -> bool:
        """
        Check if current count is within the plan limit.

        Args:
            limit_name: Limit identifier
            current_count: Current resource count

        Returns:
            bool: True if within limit or unlimited
        """
        limit = self.get_limit(limit_name)
        if limit is None:
            return True  # Unlimited
        return current_count < limit


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
        _("Name"),
        max_length=100,
        unique=True
    )
    display_name = models.CharField(
        _("Display Name"),
        max_length=100
    )
    description = models.TextField(
        _("Description"),
        blank=True
    )

    # SMS credits included
    sms_credits = models.PositiveIntegerField(
        _("SMS Credits"),
        validators=[MinValueValidator(1)],
        help_text=_("Number of SMS credits in this package")
    )

    # Pricing
    price = models.DecimalField(
        _("Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Display settings
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_featured = models.BooleanField(
        _("Is Featured"),
        default=False,
        help_text=_("Featured packages are displayed more prominently")
    )
    sort_order = models.PositiveIntegerField(_("Sort Order"), default=0)

    # Bonus credits (optional)
    bonus_credits = models.PositiveIntegerField(
        _("Bonus Credits"),
        default=0,
        help_text=_("Extra SMS credits given with this package")
    )

    # Metadata
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("SMS Package")
        verbose_name_plural = _("SMS Packages")
        ordering = ['sort_order', 'sms_credits']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['sms_credits']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.sms_credits} SMS - {self.price} TL)"

    def get_price_per_sms(self) -> Decimal:
        """Calculate price per SMS credit"""
        if self.price is None or not self.sms_credits:
            return Decimal('0.00')
        return self.price / Decimal(str(self.sms_credits))

    def get_total_credits(self) -> int:
        """Get total credits including bonus"""
        return (self.sms_credits or 0) + (self.bonus_credits or 0)
