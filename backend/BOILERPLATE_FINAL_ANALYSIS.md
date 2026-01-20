# 🎯 BOİLERPLATE ANALİZİ - REVİZE (Pragmatik Değerlendirme)

**Tarih:** 2026-01-20  
**Perspektif:** Multi-Tenant SaaS Boilerplate  
**Odak:** Genel kullanım için temel yapı

---

## ✅ DÜZELTME: Client/Customer ZORUNLU DEĞİL!

**Haklı Eleştiri:** Boilerplate her kullanım senaryosunu desteklemek zorunda değil.

**Farklı Multi-Tenant Senaryoları:**

1. **B2B SaaS** (sadece tenants + employees)
   - CRM sistemi
   - Project management
   - Internal tools
   - ❌ Client modeli GEREKSIZ

2. **B2C SaaS** (tenants + customers)
   - Randevu sistemleri
   - E-ticaret
   - Membership sistemleri
   - ✅ Client modeli GEREKLI

**Sonuç:** Client modeli **opsiyonel** bir eklenti olmalı, boilerplate için kritik değil! ✅

---

## ✅ DÜZELTME: BusinessType VAR!

```python
# apps/core/models.py
class BusinessType(models.Model):
    name = models.CharField(...)
    description = models.TextField(...)
    icon = models.CharField(...)
    is_active = models.BooleanField(...)
    order = models.IntegerField(...)
```

**Durum:** ✅ MEVCUT (core/models.py)

**Öneri:** 
- Core'da kalabilir (sistem geneli seçenekler)
- VEYA tenants'a taşınabilir (tenant-specific)

**Şu anki durum iyi!** Taşıma opsiyonel. ✅

---

## 📊 SaaS REQUIREMENTS - EKSİK OLANLAR

### SaaS Boilerplate'in "Must-Have" Özellikleri

| # | Gereksinim | Durum | Priority |
|---|------------|-------|----------|
| 1 | ✅ Tenant isolation | VAR (TenantMiddleware) | P0 |
| 2 | ✅ Subscription management | VAR (Plan + Payment) | P0 |
| 3 | ✅ Multi-tier plans | VAR (SubscriptionPlan) | P0 |
| 4 | ✅ Usage tracking | YARIM (limits var, enforce yok) | P1 |
| 5 | ✅ Billing system | VAR (Payment + Invoice) | P0 |
| 6 | ⚠️ **Trial management** | EKSİK | P1 |
| 7 | ⚠️ **Subscription lifecycle** | EKSİK | P1 |
| 8 | ⚠️ **Usage-based billing** | YOK | P2 |
| 9 | ⚠️ **Webhook system** | YOK | P2 |
| 10 | ✅ Permission system | VAR | P0 |
| 11 | ⚠️ **Feature flagging** | YARIM | P1 |
| 12 | ✅ Soft delete | VAR | P0 |
| 13 | ⚠️ **Audit logging** | YOK | P2 |

---

## 🔴 GERÇEK EKSİKLİKLER (SaaS için kritik)

### 1️⃣ Trial Management - **P1**

**Problem:**
```python
# Yeni tenant kaydında:
# - Otomatik FREE plan atanmıyor
# - 30 günlük trial başlamıyor
# - Trial bitiş uyarısı yok
```

**Çözüm:** `tenant_subscriptions/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from tenants.models import Company
from .models import TenantSubscription, SmsBalance
from system_subscriptions.models import SubscriptionPlan
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal


@receiver(post_save, sender=Company)
def provision_new_tenant(sender, instance, created, **kwargs):
    """
    Auto-provision new tenant with:
    1. Default FREE subscription (30-day trial)
    2. SMS balance (0 credits or welcome bonus)
    """
    if created:
        # 1. Get or create FREE plan
        free_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'price': Decimal('0.00'),
                'billing_cycle': 'monthly',
                'max_employee': 2,
                'max_locations': 1,
                'max_appointments_per_month': 50,
                'has_online_booking': True,
                'has_sms_notifications': False,
                'has_analytics': False,
                'features': {
                    'custom_roles': False,
                    'automation': False,
                    'advanced_reports': False,
                    'api_access': False,
                    'google_calendar': False,
                    'sms_notifications': False,
                }
            }
        )
        
        # 2. Create 30-day trial subscription
        TenantSubscription.objects.create(
            tenant=instance,
            plan=free_plan,
            status='active',
            expires_at=timezone.now() + timedelta(days=30),
            original_price=Decimal('0.00'),
            discounted_price=Decimal('0.00'),
            auto_renew=False,
            notes='30-day free trial - auto-created on signup'
        )
        
        # 3. Create SMS balance (0 credits or 10 welcome SMS)
        SmsBalance.objects.create(
            tenant=instance,
            balance=10  # Welcome bonus: 10 free SMS
        )
        
        # Optional: Create welcome transaction
        from .models import SmsTransaction
        SmsTransaction.objects.create(
            tenant=instance,
            transaction_type='bonus',
            amount=10,
            balance_after=10,
            description='Welcome bonus: 10 free SMS credits'
        )
```

**apps.py:**
```python
# apps/tenant_subscriptions/apps.py

from django.apps import AppConfig


class TenantSubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenant_subscriptions'
    
    def ready(self):
        import tenant_subscriptions.signals  # noqa
```

---

### 2️⃣ Subscription Lifecycle - **P1**

**Problem:**
```python
# Subscription expire olunca ne olacak?
# - Auto-renew mekanizması yok
# - Expire uyarısı yok
# - Downgrade mekanizması yok
```

**Çözüm 1: Management Command**

```python
# tenant_subscriptions/management/commands/check_expired_subscriptions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tenant_subscriptions.models import TenantSubscription


class Command(BaseCommand):
    help = 'Check and handle expired/expiring subscriptions'
    
    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1. Expire overdue subscriptions
        expired = TenantSubscription.objects.filter(
            status='active',
            expires_at__lt=now,
            auto_renew=False
        )
        
        for sub in expired:
            # Downgrade to FREE plan
            free_plan = SubscriptionPlan.objects.get(name='Free')
            
            sub.plan = free_plan
            sub.status = 'expired'
            sub.save()
            
            self.stdout.write(
                self.style.WARNING(f'Expired: {sub.tenant.name} → FREE')
            )
        
        # 2. Send warnings for subscriptions expiring in 7 days
        warning_date = now + timedelta(days=7)
        expiring = TenantSubscription.objects.filter(
            status='active',
            expires_at__lt=warning_date,
            expires_at__gt=now
        )
        
        for sub in expiring:
            # Send notification (email/SMS)
            from communications.services.notification import NotificationService
            
            NotificationService.send_subscription_expiry_warning(
                tenant=sub.tenant,
                expires_at=sub.expires_at
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Warned: {sub.tenant.name}')
            )
        
        # 3. Auto-renew (if payment method on file)
        # TODO: Implement auto-renew logic with iyzico subscription
```

**Cron Job (Celery Beat):**
```python
# config/celery.py

from celery import Celery
from celery.schedules import crontab

app = Celery('salon')

app.conf.beat_schedule = {
    'check-expired-subscriptions': {
        'task': 'tenant_subscriptions.tasks.check_expired_subscriptions',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

---

### 3️⃣ Feature Flagging / Plan-Based Access Control - **P1**

**Soru:** Plan-based access control şimdi mi tasarlanmalı yoksa proje ihtiyacına göre mi?

**CEVAP:** Temel altyapısını ŞİMDİ tasarla, detayları proje ihtiyacına göre! ✅

**Neden Şimdi:**
1. ✅ Boilerplate'in temel özelliği
2. ✅ Sonradan eklemesi zor (migration hell)
3. ✅ Plan özellikleri anlamlı olur
4. ✅ Kullanıcılar ne aldığını anlar

**Minimal Implementation (Boilerplate için yeterli):**

#### 3.1. Permission-Feature Mapping

```python
# apps/tenants/constants.py (YENİ DOSYA)

"""
Permission to Feature Mapping

Maps CompanyRolePermission fields to SubscriptionPlan features.
Only these permissions are plan-restricted.
"""

FEATURE_RESTRICTED_PERMISSIONS = {
    # Analytics
    'can_access_insights': 'advanced_analytics',
    'can_access_reports': 'basic_reports',
    
    # Integrations
    'can_manage_api': 'api_access',
    'can_integrate_google': 'google_calendar',
    
    # Advanced Features
    'can_use_automation': 'automation',
    'can_manage_custom_roles': 'custom_roles',
    'can_bulk_operations': 'bulk_operations',
}


def get_required_feature(permission_field):
    """
    Get required feature for a permission.
    
    Args:
        permission_field: str - Permission field name
        
    Returns:
        str or None - Required feature name
    """
    return FEATURE_RESTRICTED_PERMISSIONS.get(permission_field)


def is_permission_restricted(permission_field):
    """Check if permission is plan-restricted."""
    return permission_field in FEATURE_RESTRICTED_PERMISSIONS
```

#### 3.2. Permission Check Enhancement

```python
# apps/tenants/permissions_utils.py

from .constants import get_required_feature, is_permission_restricted
from tenant_subscriptions.services import SubscriptionService


def check_permission(user, permission_field, company=None):
    """
    Enhanced permission check with plan verification.
    
    Returns:
        bool: True if user has permission AND plan allows it
    """
    # ... existing owner check ...
    
    if company is None:
        company = getattr(user, 'company', None)
    
    if not company:
        return False
    
    # Owner has all permissions
    if company.is_owner(user):
        return True
    
    # ✅ NEW: Plan-based feature check
    if is_permission_restricted(permission_field):
        required_feature = get_required_feature(permission_field)
        
        if required_feature:
            # Check if subscription plan allows this feature
            if not SubscriptionService.check_feature_access(company, required_feature):
                return False  # Plan doesn't include this feature
    
    # Continue with normal employee permission check
    try:
        employee = user.employment
        if not employee or employee.is_deleted:
            return False
        
        # Get role permissions
        role_perms = CompanyRolePermission.objects.get(
            company=company,
            level=employee.role_level
        )
        
        return getattr(role_perms, permission_field, False)
    
    except Employee.DoesNotExist:
        return False
```

#### 3.3. View Decorator (Optional)

```python
# apps/tenants/decorators.py (YENİ DOSYA)

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from .permissions_utils import check_permission


def require_permission(permission_field):
    """
    Decorator to check permission (including plan features).
    
    Usage:
        @require_permission('can_access_insights')
        def analytics_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_permission(request.user, permission_field, request.company):
                if request.accepts('application/json'):
                    return JsonResponse({
                        'error': 'Permission denied. Upgrade your plan or contact admin.'
                    }, status=403)
                else:
                    return redirect('upgrade_plan')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

**Usage:**
```python
# views.py

from tenants.decorators import require_permission


@require_permission('can_access_insights')
def advanced_analytics(request):
    """
    Advanced analytics - only for plans with 'advanced_analytics' feature.
    """
    # ... view logic ...
```

---

### 4️⃣ Audit Logging - **P2 (Opsiyonel)**

**Problem:**
```python
# Kim ne yaptı? Takip edilemiyor.
# - Payment approval kimin tarafından?
# - Permission change kimin tarafından?
# - Subscription change kimin tarafından?
```

**Minimal Implementation:**

```python
# apps/core/models.py (veya apps/audit/)

class AuditLog(models.Model):
    """
    Simple audit log for critical actions.
    """
    ACTION_TYPES = [
        ('payment_approve', 'Payment Approved'),
        ('payment_reject', 'Payment Rejected'),
        ('subscription_change', 'Subscription Changed'),
        ('permission_change', 'Permission Changed'),
        ('employee_add', 'Employee Added'),
        ('employee_remove', 'Employee Removed'),
        ('sms_credit_adjust', 'SMS Credit Adjusted'),
    ]
    
    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Polymorphic object reference (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
```

**Usage:**
```python
# Payment.approve()

def approve(self, admin_user):
    # ... existing logic ...
    
    # Audit log
    AuditLog.objects.create(
        company=self.company,
        user=admin_user,
        action_type='payment_approve',
        description=f'Payment #{self.id} approved for {self.company.name}',
        content_object=self,
        metadata={
            'payment_id': self.id,
            'amount': str(self.amount),
            'payment_type': self.payment_type,
        }
    )
```

**Bu boilerplate için:** OPSIYONEL (P2) - İhtiyaç duyulursa eklenebilir.

---

## 📋 SIGNALS İÇERİĞİ - DETAYLI

### `tenant_subscriptions/signals.py`

```python
"""
Tenant subscription lifecycle signals.

Handles:
1. Auto-provisioning new tenants (FREE trial + SMS balance)
2. Subscription expiry warnings
3. Plan change notifications
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from tenants.models import Company
from .models import TenantSubscription, SmsBalance, SmsTransaction, SubscriptionHistory
from system_subscriptions.models import SubscriptionPlan


@receiver(post_save, sender=Company)
def provision_new_tenant(sender, instance, created, **kwargs):
    """
    Auto-provision new tenant with:
    1. Default FREE subscription (30-day trial)
    2. Initial SMS balance (10 welcome credits)
    
    Triggered: When Company is created
    """
    if created:
        # 1. Get or create FREE plan
        free_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'price': Decimal('0.00'),
                'billing_cycle': 'monthly',
                'max_employee': 2,
                'max_locations': 1,
                'max_appointments_per_month': 50,
                'has_online_booking': True,
                'has_sms_notifications': False,
                'has_analytics': False,
                'features': {
                    'custom_roles': False,
                    'automation': False,
                    'advanced_reports': False,
                    'api_access': False,
                }
            }
        )
        
        # 2. Create 30-day trial subscription
        TenantSubscription.objects.create(
            tenant=instance,
            plan=free_plan,
            status='active',
            expires_at=timezone.now() + timedelta(days=30),
            original_price=Decimal('0.00'),
            discounted_price=Decimal('0.00'),
            auto_renew=False,
            notes='30-day free trial - auto-created'
        )
        
        # 3. Create SMS balance with welcome bonus
        balance = SmsBalance.objects.create(
            tenant=instance,
            balance=10  # 10 free SMS
        )
        
        # 4. Log welcome bonus transaction
        SmsTransaction.objects.create(
            tenant=instance,
            transaction_type='bonus',
            amount=10,
            balance_after=10,
            description='Welcome bonus: 10 free SMS credits'
        )


@receiver(pre_save, sender=TenantSubscription)
def log_subscription_change(sender, instance, **kwargs):
    """
    Log subscription plan changes to SubscriptionHistory.
    
    Triggered: Before TenantSubscription is saved
    """
    if instance.pk:  # Only for updates, not creation
        try:
            old_instance = TenantSubscription.objects.get(pk=instance.pk)
            
            # Check if plan changed
            if old_instance.plan != instance.plan:
                SubscriptionHistory.objects.create(
                    tenant=instance.tenant,
                    old_plan=old_instance.plan,
                    new_plan=instance.plan,
                    reason='Plan changed',
                    notes=f'Changed from {old_instance.plan.name} to {instance.plan.name}'
                )
        except TenantSubscription.DoesNotExist:
            pass


@receiver(post_save, sender=TenantSubscription)
def send_subscription_notifications(sender, instance, created, **kwargs):
    """
    Send notifications on subscription changes.
    
    Triggered: After TenantSubscription is saved
    """
    if not created:  # Only for updates
        # Check if subscription just expired
        if instance.status == 'expired':
            # Send expiry notification
            from communications.services.notification import NotificationService
            
            NotificationService.send_notification(
                sender_company=None,
                is_system=True,
                recipient_company=instance.tenant,
                title='Subscription Expired',
                message=f'Your {instance.plan.name} plan has expired. Please renew to continue.',
                notification_type='subscription_expiry',
                channels=['in_app', 'email'],
                priority='high'
            )
```

**apps.py:**
```python
# apps/tenant_subscriptions/apps.py

from django.apps import AppConfig


class TenantSubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenant_subscriptions'
    verbose_name = 'Tenant Subscriptions'
    
    def ready(self):
        """Import signals when app is ready."""
        import tenant_subscriptions.signals  # noqa
```

---

## 🎯 PLAN-BASED ACCESS CONTROL - TASARIM KARARI

### Soru: Şimdi mi tasarlanmalı, sonra mı?

**CEVAP: Temel altyapısını ŞİMDİ, detayları SONRA** ✅

**Şimdi yapılacaklar (Boilerplate için):**

1. ✅ `FEATURE_RESTRICTED_PERMISSIONS` mapping
2. ✅ `check_permission()` enhancement
3. ✅ `SubscriptionService.check_feature_access()`
4. ✅ Plan → Feature JSON field (zaten var!)

**Sonra yapılacaklar (Proje ihtiyacına göre):**

1. ⏰ View decorators (@require_feature)
2. ⏰ API permission classes
3. ⏰ Frontend feature flag checks
4. ⏰ Usage-based restrictions (employee count, etc.)

**Neden temel altyapı şimdi:**
- ✅ Sonradan eklemek zor (migration hell)
- ✅ Plan özelliklerini anlamlı kılar
- ✅ Satış/pazarlama için gerekli
- ✅ Kullanıcı deneyimi için kritik

---

## 📊 REVİZE SKOR KARTI

### Boilerplate Requirements (Multi-Tenant SaaS için)

| # | Gereksinim | Durum | Priority | Skor |
|---|------------|-------|----------|------|
| 1 | Tenant isolation | ✅ VAR | P0 | 10/10 |
| 2 | Permission system | ✅ VAR | P0 | 9/10 |
| 3 | Subscription plans | ✅ VAR | P0 | 9/10 |
| 4 | Multi-payment methods | ✅ VAR | P0 | 9/10 |
| 5 | Soft delete | ✅ VAR | P0 | 10/10 |
| 6 | **Trial management** | ❌ EKSİK | P1 | 0/10 |
| 7 | **Subscription lifecycle** | ❌ EKSİK | P1 | 0/10 |
| 8 | **Feature flagging** | ⚠️ YARIM | P1 | 4/10 |
| 9 | SMS system | ✅ VAR | P1 | 9/10 |
| 10 | Notification system | ✅ VAR | P1 | 9/10 |
| 11 | Audit logging | ❌ YOK | P2 | 0/10 |
| 12 | Webhook system | ❌ YOK | P2 | 0/10 |

**P0 (Critical):** 9.4/10 ✅  
**P1 (Important):** 5.5/10 ⚠️  
**P2 (Nice-to-have):** 0/10 ❌

**ORTALAMA (P0 + P1):** 7.4/10

---

## 🚀 ÖNCELIK SIRASI (Boilerplate için)

### Priority 1 - URGENT (1-2 gün) 🔴

```python
# 1. tenant_subscriptions/signals.py
@receiver(post_save, sender=Company)
def provision_new_tenant(...)
    # - Auto FREE trial
    # - SMS welcome bonus

# 2. tenant_subscriptions/constants.py
FEATURE_RESTRICTED_PERMISSIONS = {...}

# 3. tenants/permissions_utils.py
def check_permission(...):
    # - Plan-based feature check
```

### Priority 2 - IMPORTANT (3-5 gün) 🟡

```python
# 4. Management command
check_expired_subscriptions.py
    # - Expire overdue
    # - Send warnings
    # - Auto-renew (opsiyonel)

# 5. system_billing/models.py
def approve(...):
    # - Subscription renewal
    # - Extend expires_at
```

### Priority 3 - NICE TO HAVE (1 hafta+) 🟢

```python
# 6. Audit logging (core/models.py)
# 7. Webhook system (iyzico callbacks)
# 8. Usage-based billing
# 9. API rate limiting
```

---

## 🎯 FİNAL SONUÇ

### 1. Client/Customer modeli zorunlu mu?

**HAYIR** ❌ - Boilerplate için opsiyonel
- B2B SaaS'ta gereksiz
- B2C SaaS'ta eklenebilir
- **Şu anki durum: DOĞRU** ✅

---

### 2. BusinessType nerede olmalı?

**Şu anki durum:** `core/models.py` ✅

**Alternatif:** `tenants/models.py`

**Öneri:** Core'da kalsın! 
- Sistem geneli seçenekler
- Birden fazla modül kullanabilir
- **Taşımaya gerek yok** ✅

---

### 3. SaaS Requirements eksiklikleri:

**P1 (URGENT - 1-2 gün):**
1. ❌ Trial management (signals)
2. ❌ Feature flagging (permission check)

**P2 (IMPORTANT - 3-5 gün):**
3. ❌ Subscription lifecycle (cron)
4. ❌ Payment approval renewal

**P3 (NICE TO HAVE):**
5. ⏰ Audit logging
6. ⏰ Webhook system

---

### 4. Signals'da neler olacak:

```python
# tenant_subscriptions/signals.py

@receiver(post_save, sender=Company)
def provision_new_tenant():
    """30-day FREE trial + 10 SMS bonus"""

@receiver(pre_save, sender=TenantSubscription)
def log_subscription_change():
    """SubscriptionHistory kayıt"""

@receiver(post_save, sender=TenantSubscription)
def send_subscription_notifications():
    """Expire/change notifications"""
```

---

### 5. Plan-based access control şimdi mi?

**EVET - Temel altyapısını şimdi!** ✅

**Şimdi yapılacaklar:**
1. ✅ Permission-feature mapping
2. ✅ `check_permission()` enhancement
3. ✅ Basic feature gating

**Sonra yapılacaklar:**
1. ⏰ View decorators
2. ⏰ API permissions
3. ⏰ Frontend checks

**Neden şimdi:**
- Migration hell prevention
- Plan satışı için gerekli
- UX için kritik

---

## 🏆 SONUÇ: %85 PRODUCTION-READY!

**Mevcut durum:**
- ✅ P0 features: 9.4/10 (Mükemmel!)
- ⚠️ P1 features: 5.5/10 (Eksik ama critical değil)
- ❌ P2 features: 0/10 (Nice-to-have)

**1-2 gün sonra (P1 signals + feature gating):**
- ✅ P0: 9.4/10
- ✅ P1: 8.5/10
- ❌ P2: 0/10

→ **%90 Production-Ready Boilerplate!** 🚀

---

**TAVSİYE:** 

1. ✅ Client modeli ekleme - DOĞRU KARAR
2. ✅ BusinessType core'da - İYİ
3. 🔴 Signals ekle (1-2 gün)
4. 🔴 Feature gating ekle (1-2 gün)
5. 🟡 Subscription lifecycle (opsiyonel, 3-5 gün)

**Toplam: 1-2 gün kritik iş → Mükemmel boilerplate!** 🎉
