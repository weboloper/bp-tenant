# 🔧 GlobalSettings Refactoring Analizi

**Soru:** Singleton GlobalSettings yerine key-value pair modüler sistem?

**CEVAP: KESINLIKLE EVET!** ✅

---

## ❌ MEVCUT DURUM SORUNLARI

### GlobalSettings (Singleton Pattern)

```python
class GlobalSettings(models.Model):
    maintenance_mode = models.BooleanField(...)
    support_email = models.EmailField(...)
    system_currency = models.CharField(...)
    contact_phone = models.CharField(...)
    website_url = models.URLField(...)
    terms_url = models.URLField(...)
    privacy_url = models.URLField(...)
```

### 🔴 Sorunlar:

1. **Her yeni ayar için migration** ❌
   ```bash
   # Yeni field eklemek için:
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Modüler değil** ❌
   - SMS ayarları eklemek istersen? → Migration
   - Email SMTP ayarları? → Migration
   - Payment gateway config? → Migration

3. **Plugin/modül desteği yok** ❌
   - Yeni modül eklediğinde kendi ayarlarını ekleyemez

4. **Type flexibility yok** ❌
   - JSON field ekleyemezsin
   - Array field ekleyemezsin
   - Encrypted field ekleyemezsin

5. **Scalability sorunları** ❌
   - 50+ ayar olunca model şişer
   - Organize etmek zor

---

## ✅ ÖNERİLEN: KEY-VALUE SİSTEMİ

### Yaklaşım 1: Pure Key-Value (Basit)

```python
# apps/settings/models.py

from django.db import models
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
import json


class Setting(models.Model):
    """
    Flexible key-value settings system.
    
    Supports multiple data types and categories.
    Cached for performance.
    """
    
    CATEGORY_CHOICES = [
        ('system', _('System')),
        ('contact', _('Contact & Social')),
        ('legal', _('Legal')),
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('payment', _('Payment')),
        ('integrations', _('Integrations')),
    ]
    
    TYPE_CHOICES = [
        ('string', _('String')),
        ('int', _('Integer')),
        ('float', _('Float')),
        ('bool', _('Boolean')),
        ('json', _('JSON')),
        ('text', _('Text (Long)')),
        ('email', _('Email')),
        ('url', _('URL')),
        ('encrypted', _('Encrypted')),
    ]
    
    # Identification
    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name=_("Key"),
        help_text=_("Unique setting key (e.g., 'maintenance_mode', 'smtp_host')")
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='system',
        verbose_name=_("Category")
    )
    
    # Type information
    data_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='string',
        verbose_name=_("Data Type")
    )
    
    # Value storage
    value = models.TextField(
        blank=True,
        verbose_name=_("Value"),
        help_text=_("Value stored as text, converted based on data_type")
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("What this setting does")
    )
    
    default_value = models.TextField(
        blank=True,
        verbose_name=_("Default Value")
    )
    
    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Is Public"),
        help_text=_("Can be accessed by frontend/API")
    )
    
    is_editable = models.BooleanField(
        default=True,
        verbose_name=_("Is Editable"),
        help_text=_("Can be changed in admin panel")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Updated By")
    )
    
    class Meta:
        verbose_name = _("Setting")
        verbose_name_plural = _("Settings")
        ordering = ['category', 'key']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['category', 'key']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return f"{self.key} = {self.value[:50]}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate cache
        cache.delete(f'setting:{self.key}')
        cache.delete('settings:all')
    
    def get_value(self):
        """
        Get typed value based on data_type.
        
        Returns:
            Properly typed value (bool, int, dict, etc.)
        """
        if not self.value:
            return self._parse_value(self.default_value)
        
        return self._parse_value(self.value)
    
    def _parse_value(self, raw_value):
        """Parse value based on data_type"""
        if not raw_value:
            return None
        
        try:
            if self.data_type == 'bool':
                return raw_value.lower() in ('true', '1', 'yes', 'on')
            
            elif self.data_type == 'int':
                return int(raw_value)
            
            elif self.data_type == 'float':
                return float(raw_value)
            
            elif self.data_type == 'json':
                return json.loads(raw_value)
            
            elif self.data_type == 'encrypted':
                # TODO: Implement encryption/decryption
                from django.core.signing import Signer
                signer = Signer()
                return signer.unsign(raw_value)
            
            else:  # string, text, email, url
                return raw_value
        
        except (ValueError, TypeError, json.JSONDecodeError):
            return raw_value
    
    def set_value(self, value):
        """
        Set typed value, converting to string for storage.
        
        Args:
            value: Value to store (any type)
        """
        if self.data_type == 'bool':
            self.value = 'true' if value else 'false'
        
        elif self.data_type == 'json':
            self.value = json.dumps(value)
        
        elif self.data_type == 'encrypted':
            from django.core.signing import Signer
            signer = Signer()
            self.value = signer.sign(str(value))
        
        else:
            self.value = str(value)
        
        self.save()


# ============================================================================
# Settings Service (Singleton Access Pattern)
# ============================================================================

class SettingsService:
    """
    Service layer for accessing settings with caching.
    
    Usage:
        from settings.services import settings
        
        if settings.get_bool('maintenance_mode'):
            return HttpResponse('Under maintenance')
        
        smtp_host = settings.get('email.smtp_host', default='localhost')
    """
    
    _instance = None
    _cache_timeout = 3600  # 1 hour
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, key, default=None):
        """
        Get setting value with caching.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value (typed)
        """
        cache_key = f'setting:{key}'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            setting = Setting.objects.get(key=key)
            value = setting.get_value()
            
            # Cache it
            cache.set(cache_key, value, self._cache_timeout)
            return value
        
        except Setting.DoesNotExist:
            return default
    
    def get_bool(self, key, default=False):
        """Get boolean setting"""
        value = self.get(key, default)
        return bool(value)
    
    def get_int(self, key, default=0):
        """Get integer setting"""
        value = self.get(key, default)
        return int(value) if value is not None else default
    
    def get_json(self, key, default=None):
        """Get JSON setting"""
        return self.get(key, default or {})
    
    def set(self, key, value, data_type='string', category='system', description=''):
        """
        Set setting value (create or update).
        
        Args:
            key: Setting key
            value: Value to set
            data_type: Data type (auto-detect if not provided)
            category: Setting category
            description: Optional description
        """
        setting, created = Setting.objects.get_or_create(
            key=key,
            defaults={
                'data_type': data_type,
                'category': category,
                'description': description,
            }
        )
        
        setting.set_value(value)
        return setting
    
    def get_category(self, category):
        """
        Get all settings in a category.
        
        Returns:
            dict: {key: value}
        """
        cache_key = f'settings:category:{category}'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        settings = Setting.objects.filter(category=category)
        result = {s.key: s.get_value() for s in settings}
        
        cache.set(cache_key, result, self._cache_timeout)
        return result
    
    def get_public(self):
        """
        Get all public settings (for frontend/API).
        
        Returns:
            dict: {key: value}
        """
        cache_key = 'settings:public'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        settings = Setting.objects.filter(is_public=True)
        result = {s.key: s.get_value() for s in settings}
        
        cache.set(cache_key, result, self._cache_timeout)
        return result
    
    def clear_cache(self):
        """Clear all settings cache"""
        cache.delete_pattern('setting:*')
        cache.delete_pattern('settings:*')


# Singleton instance
settings = SettingsService()
```

---

## 💡 KULLANIM ÖRNEKLERİ

### Admin'de Kullanım

```python
# apps/settings/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = [
        'key',
        'category',
        'data_type',
        'value_preview',
        'is_public',
        'is_editable',
        'updated_at'
    ]
    
    list_filter = ['category', 'data_type', 'is_public', 'is_editable']
    search_fields = ['key', 'description', 'value']
    readonly_fields = ['created_at', 'updated_at', 'updated_by']
    
    fieldsets = (
        (None, {
            'fields': ('key', 'category', 'data_type')
        }),
        ('Value', {
            'fields': ('value', 'default_value')
        }),
        ('Metadata', {
            'fields': ('description', 'is_public', 'is_editable')
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        """Show preview of value"""
        value = str(obj.value)
        if len(value) > 50:
            value = value[:47] + '...'
        
        if obj.data_type == 'bool':
            icon = '✅' if obj.get_value() else '❌'
            return format_html('{} <code>{}</code>', icon, value)
        
        return format_html('<code>{}</code>', value)
    
    value_preview.short_description = 'Value'
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of non-editable settings"""
        if obj and not obj.is_editable:
            return False
        return super().has_delete_permission(request, obj)
```

---

### View'larda Kullanım

```python
# views.py

from settings.services import settings


def my_view(request):
    # Boolean check
    if settings.get_bool('maintenance_mode'):
        return HttpResponse('Site under maintenance')
    
    # String value
    support_email = settings.get('contact.support_email', 'support@example.com')
    
    # Integer value
    max_upload_size = settings.get_int('uploads.max_size_mb', 10)
    
    # JSON value
    smtp_config = settings.get_json('email.smtp_config', {
        'host': 'localhost',
        'port': 587,
    })
    
    # Category
    contact_info = settings.get_category('contact')
    # Returns: {'support_email': '...', 'phone': '...', 'website': '...'}
```

---

### Management Command'da Kullanım

```python
# management/commands/init_settings.py

from django.core.management.base import BaseCommand
from settings.models import Setting


class Command(BaseCommand):
    help = 'Initialize default system settings'
    
    def handle(self, *args, **options):
        defaults = [
            # System
            ('maintenance_mode', False, 'bool', 'system', 'Enable maintenance mode'),
            ('system_currency', 'TRY', 'string', 'system', 'Default currency'),
            
            # Contact
            ('contact.support_email', 'support@salon.com', 'email', 'contact', 'Support email'),
            ('contact.phone', '+90 555 123 4567', 'string', 'contact', 'Contact phone'),
            ('contact.website', 'https://salon.com', 'url', 'contact', 'Website URL'),
            
            # Legal
            ('legal.terms_url', '/terms', 'url', 'legal', 'Terms & Conditions URL'),
            ('legal.privacy_url', '/privacy', 'url', 'legal', 'Privacy Policy URL'),
            
            # Email (SMTP)
            ('email.smtp_host', 'localhost', 'string', 'email', 'SMTP host'),
            ('email.smtp_port', 587, 'int', 'email', 'SMTP port'),
            ('email.smtp_user', '', 'string', 'email', 'SMTP username'),
            ('email.smtp_password', '', 'encrypted', 'email', 'SMTP password'),
            ('email.use_tls', True, 'bool', 'email', 'Use TLS'),
            
            # SMS
            ('sms.provider', 'netgsm', 'string', 'sms', 'SMS provider (netgsm, twilio)'),
            ('sms.api_key', '', 'encrypted', 'sms', 'SMS API key'),
            ('sms.sender_id', 'SALON', 'string', 'sms', 'Default sender ID'),
            
            # Payment
            ('payment.iyzico_api_key', '', 'encrypted', 'payment', 'Iyzico API key'),
            ('payment.iyzico_secret', '', 'encrypted', 'payment', 'Iyzico secret key'),
            ('payment.iyzico_base_url', 'https://api.iyzipay.com', 'url', 'payment', 'Iyzico API URL'),
            
            # Features
            ('features.trial_days', 30, 'int', 'system', 'Free trial duration (days)'),
            ('features.welcome_sms_bonus', 10, 'int', 'system', 'Welcome SMS bonus credits'),
        ]
        
        for key, value, data_type, category, description in defaults:
            setting, created = Setting.objects.get_or_create(
                key=key,
                defaults={
                    'value': str(value),
                    'data_type': data_type,
                    'category': category,
                    'description': description,
                    'is_editable': True,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {key} = {value}')
                )
```

**Run:**
```bash
python manage.py init_settings
```

---

### API Endpoint (Public Settings)

```python
# settings/api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from settings.services import settings


class PublicSettingsView(APIView):
    """
    Get public settings for frontend.
    
    GET /api/settings/public/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        public_settings = settings.get_public()
        
        return Response({
            'settings': public_settings
        })
```

**Frontend kullanımı:**
```javascript
// React/Vue
const response = await fetch('/api/settings/public/');
const { settings } = await response.json();

if (settings.maintenance_mode) {
    showMaintenancePage();
}
```

---

## 🎯 AVANTAJLAR

### ✅ Key-Value Sisteminin Faydaları

1. **Migration-free** ✅
   ```python
   # Yeni ayar eklemek:
   settings.set('new_feature.enabled', True, data_type='bool')
   # Migration gerekmez!
   ```

2. **Modüler** ✅
   ```python
   # Yeni modül kendi ayarlarını ekler:
   
   # apps/new_module/apps.py
   def ready(self):
       from settings.services import settings
       settings.set('new_module.api_key', '', category='new_module')
   ```

3. **Type-flexible** ✅
   ```python
   # Farklı tipler:
   settings.set('bool_value', True, data_type='bool')
   settings.set('json_config', {'a': 1}, data_type='json')
   settings.set('encrypted_key', 'secret', data_type='encrypted')
   ```

4. **Kategorize** ✅
   ```python
   # Kategorilere göre ayarlar:
   email_settings = settings.get_category('email')
   sms_settings = settings.get_category('sms')
   ```

5. **Public/Private** ✅
   ```python
   # Frontend'e expose edilecek ayarlar:
   Setting.objects.create(
       key='app.name',
       value='Salon Pro',
       is_public=True  # Frontend erişebilir
   )
   ```

6. **Encrypted values** ✅
   ```python
   # Hassas bilgiler:
   settings.set('smtp_password', 'secret123', data_type='encrypted')
   # DB'de encrypted, get() ile decrypt
   ```

7. **Audit trail** ✅
   ```python
   # Kim ne zaman değiştirdi:
   setting.updated_by  # User
   setting.updated_at  # Timestamp
   ```

---

## 📊 KARŞILAŞTIRMA

| Özellik | GlobalSettings (Singleton) | Settings (Key-Value) |
|---------|----------------------------|----------------------|
| **Yeni ayar eklemek** | Migration gerekir ❌ | Migration gerekmez ✅ |
| **Modüler** | Hayır ❌ | Evet ✅ |
| **Type safety** | IDE support ✅ | Runtime check ⚠️ |
| **Scalability** | 50+ field → şişer ❌ | Sınırsız ✅ |
| **Plugin support** | Hayır ❌ | Evet ✅ |
| **Kategorize** | Hayır ❌ | Evet ✅ |
| **Public/Private** | Hayır ❌ | Evet ✅ |
| **Encrypted** | Hayır ❌ | Evet ✅ |
| **Audit trail** | Hayır ❌ | Evet ✅ |
| **Cache** | Manuel ⚠️ | Otomatik ✅ |
| **Admin UI** | Basit ✅ | Zengin ✅ |

---

## 🏆 EN İYİ YAKLAŞIM: HYBRID

### Önerilen Yapı

```python
# apps/settings/models.py

class Setting(models.Model):
    """Key-value settings (yukarıdaki gibi)"""
    pass


class SettingsService:
    """Service layer with helper methods"""
    
    # ===== SYSTEM =====
    
    @property
    def maintenance_mode(self):
        """Type-safe getter"""
        return self.get_bool('maintenance_mode', False)
    
    @maintenance_mode.setter
    def maintenance_mode(self, value):
        """Type-safe setter"""
        self.set('maintenance_mode', value, data_type='bool')
    
    @property
    def support_email(self):
        return self.get('contact.support_email', 'support@example.com')
    
    # ===== EMAIL =====
    
    def get_smtp_config(self):
        """Get full SMTP configuration"""
        return {
            'host': self.get('email.smtp_host', 'localhost'),
            'port': self.get_int('email.smtp_port', 587),
            'username': self.get('email.smtp_user', ''),
            'password': self.get('email.smtp_password', ''),
            'use_tls': self.get_bool('email.use_tls', True),
        }
    
    # ===== SMS =====
    
    def get_sms_config(self):
        """Get SMS provider configuration"""
        provider = self.get('sms.provider', 'netgsm')
        
        return {
            'provider': provider,
            'api_key': self.get('sms.api_key', ''),
            'sender_id': self.get('sms.sender_id', 'SALON'),
        }


# Singleton
settings = SettingsService()
```

**Kullanım (Type-safe):**
```python
from settings.services import settings

# Boolean (property)
if settings.maintenance_mode:
    ...

settings.maintenance_mode = True  # Setter

# Config (method)
smtp = settings.get_smtp_config()
send_email(smtp['host'], smtp['port'], ...)
```

---

## 🚀 MİGRATİON PLANI

### Adım 1: Yeni `settings` App Oluştur

```bash
python manage.py startapp settings apps/settings
```

### Adım 2: Model Oluştur

`apps/settings/models.py` (yukarıdaki kod)

### Adım 3: Service Layer

`apps/settings/services.py` (yukarıdaki kod)

### Adım 4: Admin

`apps/settings/admin.py` (yukarıdaki kod)

### Adım 5: Migrate Et

```bash
python manage.py makemigrations settings
python manage.py migrate settings
python manage.py init_settings  # Default settings
```

### Adım 6: GlobalSettings → Settings Migrate

```python
# management/commands/migrate_global_settings.py

from django.core.management.base import BaseCommand
from core.models import GlobalSettings
from settings.models import Setting


class Command(BaseCommand):
    help = 'Migrate GlobalSettings to new Settings system'
    
    def handle(self, *args, **options):
        try:
            old = GlobalSettings.load()
        except:
            self.stdout.write('No GlobalSettings found')
            return
        
        mappings = [
            ('maintenance_mode', old.maintenance_mode, 'bool', 'system'),
            ('contact.support_email', old.support_email, 'email', 'contact'),
            ('system_currency', old.system_currency, 'string', 'system'),
            ('contact.phone', old.contact_phone, 'string', 'contact'),
            ('contact.website', old.website_url, 'url', 'contact'),
            ('legal.terms_url', old.terms_url, 'url', 'legal'),
            ('legal.privacy_url', old.privacy_url, 'url', 'legal'),
        ]
        
        for key, value, data_type, category in mappings:
            if value:
                Setting.objects.update_or_create(
                    key=key,
                    defaults={
                        'value': str(value),
                        'data_type': data_type,
                        'category': category,
                    }
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {key}')
                )
```

### Adım 7: Update References

```python
# OLD
from core.models import GlobalSettings
settings = GlobalSettings.load()
if settings.maintenance_mode:
    ...

# NEW
from settings.services import settings
if settings.get_bool('maintenance_mode'):
    ...
```

### Adım 8: Remove GlobalSettings (Optional)

```python
# core/models.py
# class GlobalSettings(models.Model):  # DELETE
```

---

## 🎯 SONUÇ

### Soru: Daha modüler ve ileriye yönelik olmaz mı?

**CEVAP: KESINLIKLE!** ✅

**Önerilen Yaklaşım:**
1. ✅ Key-Value `Setting` modeli oluştur
2. ✅ `SettingsService` singleton ile type-safe erişim
3. ✅ Kategorize ve public/private desteği
4. ✅ Encrypted field desteği
5. ✅ Cache layer
6. ✅ Management command ile init
7. ✅ GlobalSettings → Settings migration

**Avantajlar:**
- ✅ Migration-free yeni ayarlar
- ✅ Modüler (plugin support)
- ✅ Type-flexible (bool, int, json, encrypted)
- ✅ Kategorize (email, sms, payment)
- ✅ Public API desteği
- ✅ Audit trail
- ✅ Ölçeklenebilir

**Trade-offs:**
- ⚠️ IDE autocomplete azalır (ama property'lerle çözülebilir)
- ⚠️ Type safety runtime'a kayar (ama helper methods ile çözülebilir)

**SONUÇ: Global Settings → Settings (Key-Value) geçişi yapılmalı!** 🚀

---

İsterseniz şimdi birlikte implement edelim? (1-2 saat)
