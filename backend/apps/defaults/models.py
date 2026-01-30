from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


class BusinessType(models.Model):
    """
    Kuaför, Berber, Güzellik Merkezi gibi işletme türleri.
    Tenant oluşturulurken seçilir.
    """
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    icon = models.CharField(
        _("Icon"),
        max_length=50,
        blank=True,
        help_text=_("Icon name or CSS class (e.g., 'salon', 'barbershop')")
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    order = models.IntegerField(_("Order"), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Business Type")
        verbose_name_plural = _("Business Types")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name



class DefaultPaymentMethod(models.Model):
    """Platform-level payment method defaults"""
    name = models.CharField(_("Name"), max_length=100)
    code = models.SlugField(
        _("Code"),
        unique=True,
        help_text=_("Unique identifier (e.g., 'cash', 'credit_card', 'bank_transfer')")
    )
    icon = models.CharField(_("Icon"), max_length=50, blank=True)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Default Payment Method")
        verbose_name_plural = _("Default Payment Methods")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
