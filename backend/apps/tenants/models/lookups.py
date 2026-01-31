from django.db import models
from django.utils.translation import gettext_lazy as _
from core.mixins import TenantAwareMixin, TimestampMixin, SystemProtectedMixin


class PaymentMethod(TenantAwareMixin, SystemProtectedMixin, TimestampMixin, models.Model):
    """
    Payment method options for a tenant.

    System records (is_system=True) are copied from DefaultPaymentMethod
    when the company is created and cannot be deleted by the tenant.
    """
    name = models.CharField(_("Name"), max_length=100)
    icon = models.CharField(_("Icon"), max_length=50, blank=True)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")
        ordering = ['order', 'name']
        unique_together = [('company', 'name')]

    def __str__(self):
        return self.name
