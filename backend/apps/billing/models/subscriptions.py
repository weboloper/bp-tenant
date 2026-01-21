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
        'billing.SubscriptionPlan',
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
        'billing.SubscriptionPlan',
        related_name='old_subscriptions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Old Plan")
    )
    new_plan = models.ForeignKey(
        'billing.SubscriptionPlan',
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
