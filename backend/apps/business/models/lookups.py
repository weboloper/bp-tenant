from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import ProtectedError
from datetime import timedelta
from core.mixins import TenantAwareMixin, TimestampMixin


class SystemProtectedMixin(models.Model):
    """
    Mixin for lookup tables that can have system-protected entries.

    - is_system=True: Copied from platform defaults, cannot be deleted/edited
    - is_system=False: Created by tenant
    """
    is_system = models.BooleanField(
        _("Is System"),
        default=False,
        editable=False,
        help_text=_("System records cannot be edited or deleted by tenant")
    )
    source_code = models.SlugField(
        _("Source Code"),
        max_length=50,
        blank=True,
        help_text=_("Reference to platform default (for system records)")
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # System records: only allow order change
        if self.pk and self.is_system:
            # Get original from DB
            original = self.__class__.objects.get(pk=self.pk)
            # Restore protected fields
            for field in self._get_protected_fields():
                setattr(self, field, getattr(original, field))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ProtectedError(
                _("System records cannot be deleted"),
                self
            )
        super().delete(*args, **kwargs)

    def _get_protected_fields(self):
        """Override in subclass to specify protected fields"""
        return ['name', 'is_system', 'source_code']

class PaymentMethod(TenantAwareMixin, SystemProtectedMixin, TimestampMixin, models.Model):
    """Payment method options"""
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

