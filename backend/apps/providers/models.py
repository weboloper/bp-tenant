from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class SMSProviderConfig(models.Model):
    """
    SMS Provider Konfigürasyonu
    System Admin tarafından yönetilir
    """
    class ProviderChoices(models.TextChoices):
        NETGSM = 'netgsm', 'NetGSM'
        TWILIO = 'twilio', 'Twilio'
        MOCK = 'mock', 'Mock (Test)'
    
    provider = models.CharField(
        max_length=50,
        choices=ProviderChoices.choices,
        unique=True
    )
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    
    # Credentials (production'da encrypt edilmeli)
    credentials = models.JSONField(
        _('Credentials'),
        default=dict,
        help_text=_('{"username": "xxx", "password": "xxx", "sender_id": "SALON"}')
    )
    # Örnek: {"username": "xxx", "password": "xxx", "sender_id": "SALON"}
    
    # Settings
    settings = models.JSONField(
        _('Settings'),
        default=dict,
        blank=True,
        help_text=_('{"rate_limit": 100, "retry_count": 3}')
    )
    # Örnek: {"rate_limit": 100, "retry_count": 3}

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('SMS Provider Config')
        verbose_name_plural = _('SMS Provider Configs')
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " (Default)" if self.is_default else ""
        return f"{status} {self.get_provider_display()}{default}"
    
    def save(self, *args, **kwargs):
        # Sadece bir tane default olabilir
        if self.is_default:
            SMSProviderConfig.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class EmailProviderConfig(models.Model):
    """
    Email Provider Konfigürasyonu
    """
    class ProviderChoices(models.TextChoices):
        SMTP = 'smtp', 'SMTP'
        SENDGRID = 'sendgrid', 'Sendgrid'
        MOCK = 'mock', 'Mock (Test)'
    
    provider = models.CharField(
        max_length=50,
        choices=ProviderChoices.choices,
        unique=True
    )
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    
    credentials = models.JSONField(
        _('Credentials'),
        default=dict,
        help_text=_('SMTP: {"host": "", "port": 587, "username": "", "password": ""}')
    )
    # SMTP: {"host": "smtp.gmail.com", "port": 587, "username": "", "password": ""}
    # Sendgrid: {"api_key": "SG.xxx"}
    
    settings = models.JSONField(
        _('Settings'),
        default=dict,
        blank=True,
        help_text=_('{"from_email": "noreply@app.com", "from_name": "App"}')
    )
    # {"from_email": "noreply@salon.com", "from_name": "Salon App"}

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Email Provider Config')
        verbose_name_plural = _('Email Provider Configs')
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " (Default)" if self.is_default else ""
        return f"{status} {self.get_provider_display()}{default}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            EmailProviderConfig.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)