from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class SmsBalance(models.Model):
    """
    Tenant SMS kredisi - Her tenant için TEK kayıt
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


class SmsTransaction(models.Model):
    """
    SMS kredi hareketleri - Her işlem için ayrı kayıt
    """

    TRANSACTION_TYPE_CHOICES = [
        ('purchase', _('Purchase')),           # SMS paketi alımı
        ('usage', _('Usage')),                 # SMS gönderimi
        ('refund', _('Refund')),              # İade
        ('admin_adjustment', _('Admin Adjustment')),  # Manuel düzeltme
        ('bonus', _('Bonus')),                # Bonus kredi
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

    # İlişkiler
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

    # Detaylar
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
