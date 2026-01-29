from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


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
