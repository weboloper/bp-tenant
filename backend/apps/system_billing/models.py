from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from core.mixins import TimestampMixin


class Payment(TimestampMixin, models.Model):
    """
    Unified payment tracking for subscriptions and SMS packages.
    Supports both iyzico checkout form and manual payments (bank transfer/EFT).
    """

    PAYMENT_TYPE_CHOICES = [
        ('subscription', _('Subscription Payment')),
        ('sms_package', _('SMS Package Payment')),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('iyzico', _('iyzico Checkout Form')),
        ('bank_transfer', _('Bank Transfer')),
        ('eft', _('EFT')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
        ('refunded', _('Refunded')),
        ('partially_refunded', _('Partially Refunded')),
        ('disputed', _('Disputed')),
        ('chargeback', _('Chargeback')),
    ]

    # Core fields
    tenant = models.ForeignKey(
        'tenants.Company',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_("Tenant")
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name=_("Payment Type")
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name=_("Payment Method")
    )

    # Pricing
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Amount")
    )
    currency = models.CharField(
        max_length=3,
        default='TRY',
        verbose_name=_("Currency")
    )

    # Status workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status")
    )

    # Generic Gateway Fields (works with any payment provider)
    gateway_name = models.CharField(
        max_length=50,
        default='iyzico',
        verbose_name=_("Payment Gateway"),
        help_text=_("Payment provider: iyzico, stripe, paypal, etc.")
    )
    gateway_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_("Gateway Transaction ID"),
        help_text=_("Universal transaction ID from payment gateway")
    )
    gateway_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Gateway Token"),
        help_text=_("Checkout session or payment token")
    )
    gateway_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Gateway Data"),
        help_text=_("Gateway-specific data: conversation_id, fraud_status, etc.")
    )

    # Polymorphic relationships
    subscription = models.ForeignKey(
        'tenant_subscriptions.TenantSubscription',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payments',
        verbose_name=_("Subscription")
    )
    sms_package = models.ForeignKey(
        'system_subscriptions.SMSPackage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payments',
        verbose_name=_("SMS Package")
    )

    # Manual payment details
    payment_proof = models.FileField(
        upload_to='payment_proofs/',
        null=True,
        blank=True,
        verbose_name=_("Payment Proof")
    )
    bank_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Bank Reference")
    )

    # Approval workflow
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_payments',
        verbose_name=_("Approved By")
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Approved At")
    )

    # Audit & notes
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Store full iyzico response and other metadata")
    )

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['status', 'payment_type']),
            models.Index(fields=['gateway_name', 'status']),
        ]

    def __str__(self):
        return f"{self.tenant} - {self.get_payment_type_display()} - {self.amount} {self.currency}"

    def is_manual_payment(self):
        """Check if payment is manual (bank transfer/EFT)"""
        return self.payment_method in ['bank_transfer', 'eft']

    def requires_approval(self):
        """Check if payment requires admin approval"""
        return self.is_manual_payment() and self.status == 'pending'

    def approve(self, admin_user):
        """Approve manual payment and activate subscription/package"""
        if not self.requires_approval():
            raise ValidationError(_("Payment does not require approval"))

        self.status = 'completed'
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save()

        # Activate subscription
        if self.payment_type == 'subscription' and self.subscription:
            self.subscription.status = 'active'
            self.subscription.save()

        # Add SMS credits
        elif self.payment_type == 'sms_package' and self.sms_package:
            from tenant_resources.services import SmsService

            # Calculate total credits (base + bonus)
            total_credits = self.sms_package.sms_credits + self.sms_package.bonus_credits

            # Add credits to tenant balance
            SmsService.add_credits(
                tenant=self.tenant,
                amount=total_credits,
                payment=self,
                package=self.sms_package,
                user=admin_user,
                description=f"Manual payment approved: {self.sms_package.display_name}"
            )

    def can_refund(self):
        """Check if payment can be refunded"""
        return self.status == 'completed' and self.payment_method == 'iyzico'


class Invoice(TimestampMixin, models.Model):
    """
    Invoice records for payments.
    Manually created by admin after issuing invoice via external system (e-Fatura, etc.)
    """

    INVOICE_TYPE_CHOICES = [
        ('sale', _('Sale Invoice')),
        ('refund', _('Refund Invoice')),
    ]

    # Core fields
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_("Payment")
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default='sale',
        verbose_name=_("Invoice Type")
    )

    # Invoice details
    invoice_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Invoice Number")
    )
    invoice_date = models.DateField(verbose_name=_("Invoice Date"))
    invoice_file = models.FileField(
        upload_to='invoices/',
        verbose_name=_("Invoice File")
    )

    # Optional fields
    tax_office = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Tax Office")
    )
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Tax Number")
    )
    company_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Company Title")
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_invoices',
        verbose_name=_("Created By")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['payment', 'invoice_type']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.payment.tenant} - {self.get_invoice_type_display()}"
