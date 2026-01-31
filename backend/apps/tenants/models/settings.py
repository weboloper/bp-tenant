
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.mixins import TenantAwareMixin, TimestampMixin


class TenantSettingsMixin(TenantAwareMixin, TimestampMixin, models.Model):
    """
    Base mixin for singleton settings per tenant.
    Ensures only one record per company.
    """
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Singleton enforcement
        if not self.pk:
            existing = self.__class__.objects.filter(company=self.company).first()
            if existing:
                self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_for_tenant(cls, company):
        """Get or create settings for tenant"""
        obj, created = cls.objects.get_or_create(company=company)
        return obj


class BusinessSettings(TenantSettingsMixin):
    """
    Core business settings (1.1 Business Detail)
    """

    class TaxCalculation(models.TextChoices):
        EXCLUSIVE = 'exclusive', _('Retail prices exclude tax')
        INCLUSIVE = 'inclusive', _('Retail prices include tax')

    # Currency & Tax
    currency = models.CharField(_("Currency"), max_length=3, default='TRY')
    tax_calculation = models.CharField(
        _("Tax Calculation"),
        max_length=20,
        choices=TaxCalculation.choices,
        default=TaxCalculation.EXCLUSIVE
    )

    # Language
    team_default_language = models.CharField(
        _("Team Default Language"),
        max_length=5,
        default='tr'
    )
    client_default_language = models.CharField(
        _("Client Default Language"),
        max_length=5,
        default='tr'
    )

    # Social Links
    facebook_url = models.URLField(_("Facebook URL"), blank=True)
    instagram_url = models.URLField(_("Instagram URL"), blank=True)
    twitter_url = models.URLField(_("Twitter URL"), blank=True)
    website_url = models.URLField(_("Website URL"), blank=True)

    class Meta:
        verbose_name = _("Business Settings")
        verbose_name_plural = _("Business Settings")
        constraints = [
            models.UniqueConstraint(fields=['company'], name='unique_business_settings')
        ]

    def __str__(self):
        return f"{self.company.name} - Business Settings"


class TaxRate(TenantAwareMixin, TimestampMixin, models.Model):
    """
    Tax rates (3.2 Tax Rates)
    """
    name = models.CharField(_("Name"), max_length=100)
    rate = models.DecimalField(_("Rate"), max_digits=5, decimal_places=2)
    is_default = models.BooleanField(_("Is Default"), default=False)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Tax Rate")
        verbose_name_plural = _("Tax Rates")
        ordering = ['name']
        unique_together = [('company', 'name')]

    def save(self, *args, **kwargs):
        # Ensure only one default per company
        if self.is_default:
            TaxRate.objects.filter(company=self.company, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"