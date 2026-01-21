from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


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
        'billing.Payment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sms_transactions',
        verbose_name=_("Payment")
    )
    sms_package = models.ForeignKey(
        'billing.SMSPackage',
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
