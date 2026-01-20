from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache


class BusinessType(models.Model):
    """
    Kuaför, Berber, Güzellik Merkezi gibi işletme türleri.
    Tenant oluşturulurken seçilir. (Eski system/models.py'den taşındı)
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


class GlobalSettings(models.Model):
    """
    Sistem genelindeki ayarlar (Singleton Pattern).
    Veritabanında sadece tek bir kayıt tutulur.
    """
    maintenance_mode = models.BooleanField(_("Maintenance Mode"), default=False)
    support_email = models.EmailField(_("Support Email"), blank=True)
    system_currency = models.CharField(_("System Currency"), max_length=3, default="TRY")
    
    # İletişim & Sosyal
    contact_phone = models.CharField(_("Contact Phone"), max_length=20, blank=True)
    website_url = models.URLField(_("Website URL"), blank=True)
    
    # Yasal
    terms_url = models.URLField(_("Terms & Conditions URL"), blank=True)
    privacy_url = models.URLField(_("Privacy Policy URL"), blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Global Settings")
        verbose_name_plural = _("Global Settings")

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton enforcement: ID her zaman 1 olsun
        super().save(*args, **kwargs)
        cache.set('global_settings', self)

    def delete(self, *args, **kwargs):
        pass  # Silinmesini engelle

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return "Global System Settings"