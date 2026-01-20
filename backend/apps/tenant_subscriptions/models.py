from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class TenantSubscription(models.Model):
    """Tenant'ın aktif aboneliği"""

    STATUS_CHOICES = [
        ('active', _('Active')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
        ('suspended', _('Suspended')),
    ]

    tenant = models.OneToOneField(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name=_("Tenant")
    )
    plan = models.ForeignKey(
        'system_subscriptions.SubscriptionPlan',
        on_delete=models.PROTECT,
        verbose_name=_("Plan")
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_("Status")
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Started At")
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    auto_renew = models.BooleanField(
        default=False,
        verbose_name=_("Auto Renew")
    )

    # Pricing (can differ from package price due to discounts)
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Original Price")
    )

    discounted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Discounted Price")
    )

    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    class Meta:
        verbose_name = _("Tenant Subscription")
        verbose_name_plural = _("Tenant Subscriptions")
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.tenant} - {self.plan.name} ({self.get_status_display()})"


class SubscriptionHistory(models.Model):
    """Tenant abonelik değişiklik geçmişi"""

    tenant = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='subscription_history',
        verbose_name=_("Tenant")
    )
    old_plan = models.ForeignKey(
        'system_subscriptions.SubscriptionPlan',
        related_name='old_subscriptions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Old Plan")
    )
    new_plan = models.ForeignKey(
        'system_subscriptions.SubscriptionPlan',
        related_name='new_subscriptions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("New Plan")
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Changed At")
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By")
    )
    reason = models.TextField(
        blank=True,
        verbose_name=_("Reason")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    class Meta:
        verbose_name = _("Subscription History")
        verbose_name_plural = _("Subscription Histories")
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.tenant} - {self.changed_at.strftime('%Y-%m-%d')}"


# ============================================================================
# SMS Credit Models (moved from tenant_resources)
# ============================================================================

class SmsBalance(models.Model):
    """
    Tenant SMS credit balance.
    Each tenant has a single balance record tracking their current SMS credits.
    """
    tenant = models.OneToOneField(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='sms_balance',
        verbose_name=_("Tenant")
    )
    balance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Balance"),
        help_text=_("Current SMS credit balance")
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated")
    )

    class Meta:
        verbose_name = _("SMS Balance")
        verbose_name_plural = _("SMS Balances")
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['balance']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.balance} SMS"

    def add_credits(self, amount, description='', user=None, payment=None, sms_package=None):
        """Add SMS credits and create transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.balance += amount
        self.save()

        SmsTransaction.objects.create(
            tenant=self.tenant,
            transaction_type='purchase' if payment else 'bonus',
            amount=amount,
            balance_after=self.balance,
            payment=payment,
            sms_package=sms_package,
            description=description,
            created_by=user,
        )

        return self.balance

    def deduct_credits(self, amount, description='', user=None):
        """Deduct SMS credits and create transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient SMS credits")

        self.balance -= amount
        self.save()

        SmsTransaction.objects.create(
            tenant=self.tenant,
            transaction_type='usage',
            amount=-amount,
            balance_after=self.balance,
            description=description,
            created_by=user,
        )

        return self.balance


class SmsTransaction(models.Model):
    """
    SMS credit transaction history.
    Tracks all credit movements: purchases, usage, refunds, adjustments, bonuses.
    """

    TRANSACTION_TYPE_CHOICES = [
        ('purchase', _('Purchase')),
        ('usage', _('Usage')),
        ('refund', _('Refund')),
        ('admin_adjustment', _('Admin Adjustment')),
        ('bonus', _('Bonus')),
    ]

    tenant = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='sms_transactions',
        verbose_name=_("Tenant")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_("Transaction Type")
    )
    amount = models.IntegerField(
        verbose_name=_("Amount"),
        help_text=_("Positive for additions, negative for deductions")
    )
    balance_after = models.IntegerField(
        verbose_name=_("Balance After"),
        help_text=_("SMS balance after this transaction")
    )

    # Related objects
    payment = models.ForeignKey(
        'system_billing.Payment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sms_transactions',
        verbose_name=_("Payment")
    )
    sms_package = models.ForeignKey(
        'system_subscriptions.SMSPackage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("SMS Package")
    )

    # Details
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created By")
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional transaction data")
    )

    class Meta:
        verbose_name = _("SMS Transaction")
        verbose_name_plural = _("SMS Transactions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.tenant.name} - {sign}{self.amount} SMS ({self.get_transaction_type_display()})"
