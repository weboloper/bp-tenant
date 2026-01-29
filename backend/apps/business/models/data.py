from django.db import models
from django.utils.translation import gettext_lazy as _
from core.mixins import TenantAwareMixin, TimestampMixin, SoftDeleteMixin


class Location(TenantAwareMixin, SoftDeleteMixin, TimestampMixin, models.Model):
    """
    Business location (1.2 Locations)
    A company can have multiple locations.
    """
    # Contact
    name = models.CharField(_("Name"), max_length=200)
    phone = models.CharField(_("Phone"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    # Business Type
    main_business_type = models.ForeignKey(
        'tenants.BusinessType',
        on_delete=models.PROTECT,
        related_name='main_locations',
        verbose_name=_("Main Business Type")
    )
    additional_business_types = models.ManyToManyField(
        'tenants.BusinessType',
        blank=True,
        related_name='additional_locations',
        verbose_name=_("Additional Business Types")
    )
    other_business_type = models.CharField(
        _("Other Business Type"),
        max_length=100,
        blank=True
    )

    # Address
    address_line1 = models.CharField(_("Address Line 1"), max_length=255)
    address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True)
    district = models.CharField(_("District"), max_length=100, blank=True)
    city = models.CharField(_("City"), max_length=100)
    postcode = models.CharField(_("Postcode"), max_length=20, blank=True)
    country = models.CharField(_("Country"), max_length=2, help_text=_("ISO country code"))
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Working Hours
    working_hours = models.JSONField(
        _("Working Hours"),
        default=dict,
        help_text=_("Format: {'monday': {'start': '09:00', 'end': '18:00'}, 'sunday': null}")
    )

    # Billing (optional override)
    use_location_for_billing = models.BooleanField(
        _("Use Location for Billing"),
        default=True
    )
    billing_company_name = models.CharField(
        _("Billing Company Name"),
        max_length=255,
        blank=True
    )
    billing_address = models.TextField(_("Billing Address"), blank=True)
    billing_city = models.CharField(_("Billing City"), max_length=100, blank=True)
    billing_postcode = models.CharField(_("Billing Postcode"), max_length=20, blank=True)
    invoice_note = models.TextField(_("Invoice Note"), blank=True)

    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"


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