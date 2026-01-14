from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class  BusinessType(models.Model):
    name = models.CharField(max_length=255,verbose_name=_("Name"))
    description = models.TextField(blank=True, null=True,verbose_name=_("Description"))
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Icon"),
        help_text=_("Icon name or CSS class (e.g., 'salon', 'barbershop')")
    )
    is_active = models.BooleanField(default=True,verbose_name=_("Is Active"))
    order = models.IntegerField(default=0,verbose_name=_("Order"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Business Type")
        verbose_name_plural = _("Business Types")
        ordering = ["name"]