# Billing Sistemi Workflow Dokümantasyonu

Bu dokümantasyon, billing (faturalama) sisteminin çalışma mantığını, iş akışlarını ve kullanım örneklerini açıklamaktadır.

## İçindekiler

1. [Genel Yapı](#genel-yapı)
2. [Modeller](#modeller)
3. [Subscription (Abonelik) Workflow](#subscription-abonelik-workflow)
4. [SMS Package (SMS Paketi) Workflow](#sms-package-sms-paketi-workflow)
5. [Payment (Ödeme) Workflow](#payment-ödeme-workflow)
6. [Servisler](#servisler)
7. [Kod Örnekleri](#kod-örnekleri)

---

## Genel Yapı

Billing sistemi üç ana bileşenden oluşur:

1. **Subscription Management**: Tenant'ların abonelik planlarını yönetir
2. **SMS Credit Management**: SMS kredilerini takip eder ve yönetir
3. **Payment Processing**: Ödemeleri işler ve kaydeder

```
┌─────────────────────────────────────────────────────────────┐
│                    BILLING SYSTEM                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │  Subscription    │  │   SMS Credits    │  │  Payments  ││
│  │  Management      │  │   Management     │  │  System    ││
│  └──────────────────┘  └──────────────────┘  └────────────┘│
│           │                      │                   │       │
│           └──────────────────────┴───────────────────┘       │
│                            │                                 │
│                    ┌───────▼────────┐                       │
│                    │     Tenant     │                       │
│                    └────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Modeller

### 1. SubscriptionPlan (Abonelik Planı)

Platform seviyesinde tanımlanan abonelik paketleri.

**Özellikler:**

- `name`: Plan adı (örn: "Basic", "Premium")
- `price`: Aylık veya yıllık ücret
- `billing_cycle`: monthly/yearly
- `max_employees`: Maksimum çalışan sayısı
- `max_products`: Maksimum ürün sayısı
- `has_inventory`: Stok modülü erişimi
- `welcome_sms_bonus`: Hoşgeldin SMS kredisi

### 2. TenantSubscription (Tenant Aboneliği)

Her tenant'ın aktif aboneliği.

**Durum Geçişleri:**

```
pending → active → expired/cancelled/suspended
```

### 3. SMSPackage (SMS Paketi)

Platform seviyesinde tanımlanan SMS paketleri.

**Özellikler:**

- `sms_credits`: Temel SMS kredisi
- `bonus_credits`: Bonus SMS kredisi
- `price`: Paket ücreti

### 4. SmsBalance (SMS Bakiyesi)

Her tenant'ın SMS kredi bakiyesi (OneToOne).

**UYARI:** SMS bakiyesi direkt değiştirilmez, her zaman `add_credits()` veya `deduct_credits()` metodları kullanılır.

### 5. SmsTransaction (SMS İşlemi)

SMS kredi hareketlerinin geçmişi.

**İşlem Tipleri:**

- `purchase`: Satın alma
- `usage`: Kullanım (SMS gönderimi)
- `refund`: İade
- `admin_adjustment`: Admin düzeltmesi
- `bonus`: Bonus kredi

**ÖNEMLİ:** SmsTransaction kayıtları direkt oluşturulmaz! Her zaman SmsBalance metodları üzerinden otomatik oluşturulur.

### 6. Payment (Ödeme)

Subscription ve SMS paket ödemelerini takip eder.

**Ödeme Metodları:**

- `iyzico`: iyzico Checkout Form
- `bank_transfer`: Banka Havalesi
- `eft`: EFT

**Durum Geçişleri:**

```
pending → completed/failed/cancelled
         ↓
    refunded/partially_refunded
```

---

## Subscription (Abonelik) Workflow

### Yeni Abonelik Oluşturma

```
1. Tenant bir plan seçer
2. SubscriptionService.create_subscription() çağrılır
3. TenantSubscription oluşturulur (status: pending)
4. Welcome bonus SMS varsa otomatik yüklenir
5. Payment oluşturulur
6. Ödeme tamamlandığında subscription aktif olur
```

### Adım Adım Akış Diyagramı

```
┌──────────────┐
│ Plan Seçimi  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ Subscription Oluşturulur │
│   (status: pending)      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Welcome Bonus Varsa      │
│ SMS Kredisi Eklenir      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Payment Oluşturulur      │
│   (status: pending)      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│   Ödeme İşlemi           │
│ (iyzico/bank_transfer)   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Payment Completed        │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Subscription Activated   │
│   (status: active)       │
└──────────────────────────┘
```

---

## SMS Package (SMS Paketi) Workflow

### SMS Paketi Satın Alma

```
1. Tenant bir SMS paketi seçer
2. Payment oluşturulur (type: sms_package)
3. Ödeme tamamlandığında:
   - SmsBalance.add_credits() çağrılır
   - SMS kredileri (base + bonus) eklenir
   - SmsTransaction otomatik oluşturulur
```

### Adım Adım Akış Diyagramı

```
┌──────────────────┐
│ SMS Paket Seçimi │
│ (örn: 1000 SMS)  │
└────────┬─────────┘
         │
         ▼
┌────────────────────────┐
│ Payment Oluşturulur    │
│ type: sms_package      │
│ status: pending        │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   Ödeme İşlemi         │
│ (iyzico/bank_transfer) │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Payment Completed      │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ SmsBalance.add_credits │
│ (base + bonus)         │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ SmsTransaction Oluşur  │
│ type: purchase         │
│ balance_after: X       │
└────────────────────────┘
```

### SMS Kullanımı (Gönderim)

```
1. Sistem SMS göndermek ister
2. SmsService.has_sufficient_credits() ile kontrol edilir
3. SmsBalance.deduct_credits() çağrılır
4. SmsTransaction otomatik oluşturulur (type: usage)
5. SMS gönderilir
```

---

## Payment (Ödeme) Workflow

### İyzico Ödeme Akışı

```
1. Payment oluşturulur (method: iyzico, status: pending)
2. İyzico checkout form başlatılır
3. Kullanıcı ödemeyi tamamlar
4. İyzico callback'i alınır
5. PaymentService.complete_payment() çağrılır
6. İlgili servis aktif edilir (subscription veya SMS)
```

### Manuel Ödeme Akışı (Banka Havalesi/EFT)

```
1. Payment oluşturulur (method: bank_transfer/eft, status: pending)
2. Kullanıcı banka havalesi yapar
3. Dekont yüklenir (payment_proof)
4. Admin kontrolü yapar
5. Admin payment.approve() metodunu çağırır
6. İlgili servis aktif edilir
```

### Ödeme Durum Diyagramı

```
     ┌─────────┐
     │ pending │
     └────┬────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│completed │  │  failed  │
└────┬─────┘  └──────────┘
     │
     ▼
┌──────────────────┐
│ refunded /       │
│ partially_refund │
└──────────────────┘
```

---

## Servisler

### SmsService

Tüm SMS kredi işlemleri bu servis üzerinden yapılır.

**Metodlar:**

- `add_credits(tenant, amount, ...)`: Kredi ekle
- `deduct_credits(tenant, amount, ...)`: Kredi düş
- `check_balance(tenant)`: Bakiye sorgula
- `has_sufficient_credits(tenant, amount)`: Yeterli kredi kontrolü

### SubscriptionService

Abonelik yönetimi için kullanılır.

**Metodlar:**

- `create_subscription(tenant, plan, ...)`: Abonelik oluştur
- `activate_subscription(subscription)`: Abonelik aktif et
- `get_active_subscription(tenant)`: Aktif abonelik getir
- `check_subscription_status(tenant)`: Durum kontrolü

### PaymentService

Ödeme işlemlerini yönetir.

**Metodlar:**

- `create_sms_payment(tenant, package, ...)`: SMS ödeme oluştur
- `create_subscription_payment(tenant, subscription, ...)`: Abonelik ödeme oluştur
- `complete_payment(payment, ...)`: Ödeme tamamla

---

## Kod Örnekleri

### Örnek 1: Tenant Abonelik Satın Alıyor

```python
from billing.models import SubscriptionPlan
from billing.services import SubscriptionService, PaymentService
from tenants.models import Company

# 1. Tenant ve Plan
tenant = Company.objects.get(id=1)
plan = SubscriptionPlan.objects.get(slug='premium')

# 2. Abonelik Oluştur
subscription = SubscriptionService.create_subscription(
    tenant=tenant,
    plan=plan,
    duration_months=1,  # 1 aylık
    notes='İlk abonelik'
)

# 3. Ödeme Oluştur
payment = PaymentService.create_subscription_payment(
    tenant=tenant,
    subscription=subscription,
    payment_method='iyzico'
)

# 4. Ödeme Tamamlandığında (iyzico callback'ten)
PaymentService.complete_payment(
    payment=payment,
    gateway_transaction_id='iyzico_123456',
    gateway_data={'conversationId': 'conv_123'}
)

# Sonuç:
# - subscription.status = 'active'
# - Plan welcome_sms_bonus varsa SMS kredisi eklendi
# - payment.status = 'completed'
```

### Örnek 2: Tenant SMS Paketi Satın Alıyor

```python
from billing.models import SMSPackage
from billing.services import PaymentService, SmsService
from tenants.models import Company

# 1. Tenant ve SMS Paketi
tenant = Company.objects.get(id=1)
package = SMSPackage.objects.get(name='sms_1000')  # 1000 SMS paketi

# 2. Ödeme Oluştur
payment = PaymentService.create_sms_payment(
    tenant=tenant,
    package=package,
    payment_method='bank_transfer'  # Banka havalesi
)

# 3. Kullanıcı havale yaptı, admin onaylıyor
payment.payment_proof = 'dekont.pdf'
payment.bank_reference = 'REF123456'
payment.save()

# 4. Admin Onayı
from django.contrib.auth import get_user_model
User = get_user_model()
admin_user = User.objects.get(username='admin')

payment.approve(admin_user)

# Sonuç:
# - payment.status = 'completed'
# - SMS kredileri otomatik eklendi (base + bonus)
# - SmsTransaction oluşturuldu (type: purchase)
# - tenant.sms_balance.balance artırıldı
```

### Örnek 3: SMS Gönderimi (Kredi Kullanımı)

```python
from billing.services import SmsService
from tenants.models import Company

tenant = Company.objects.get(id=1)

# 1. Önce bakiye kontrolü
if SmsService.has_sufficient_credits(tenant, required_amount=5):
    # 2. SMS gönder
    # ... SMS gönderim işlemi ...

    # 3. Kredi düş
    SmsService.deduct_credits(
        tenant=tenant,
        amount=5,
        description='5 SMS gönderildi (kampanya bildirimi)'
    )
    print("SMS başarıyla gönderildi")
else:
    print("Yetersiz SMS kredisi!")

# Sonuç:
# - tenant.sms_balance.balance 5 azaldı
# - SmsTransaction oluşturuldu (type: usage, amount: -5)
```

### Örnek 4: Admin SMS Kredisi Ekliyor (Bonus/Düzeltme)

```python
from billing.services import SmsService
from tenants.models import Company
from django.contrib.auth import get_user_model

tenant = Company.objects.get(id=1)
admin = get_user_model().objects.get(username='admin')

# Bonus kredi ekleme
SmsService.add_credits(
    tenant=tenant,
    amount=100,
    user=admin,
    description='Promosyon kampanyası - 100 bedava SMS'
)

# Sonuç:
# - tenant.sms_balance.balance 100 arttı
# - SmsTransaction oluşturuldu (type: bonus)
```

### Örnek 5: Abonelik Durumu Kontrolü

```python
from billing.services import SubscriptionService
from tenants.models import Company

tenant = Company.objects.get(id=1)

# Abonelik bilgilerini getir
info = SubscriptionService.check_subscription_status(tenant)

if info['has_subscription']:
    print(f"Plan: {info['plan'].name}")
    print(f"Durum: {info['status']}")
    print(f"Bitiş: {info['expires_at']}")
    print(f"Maks. Çalışan: {info['max_employees']}")
    print(f"Maks. Ürün: {info['max_products']}")
else:
    print("Aktif abonelik yok")
```

### Örnek 6: SMS Bakiyesi Sorgulama

```python
from billing.services import SmsService
from tenants.models import Company

tenant = Company.objects.get(id=1)

# Mevcut bakiye
balance = SmsService.check_balance(tenant)
print(f"Mevcut SMS bakiyesi: {balance}")

# İşlem geçmişi
from billing.models import SmsTransaction

transactions = SmsTransaction.objects.filter(
    tenant=tenant
).order_by('-created_at')[:10]

for tx in transactions:
    print(f"{tx.created_at}: {tx.get_transaction_type_display()} - {tx.amount} SMS")
```

---

## Önemli Notlar

### ❌ YAPILMAMASI GEREKENLER

1. **SmsTransaction direkt oluşturmayın:**

```python
# YANLIŞ ❌
SmsTransaction.objects.create(
    tenant=tenant,
    transaction_type='purchase',
    amount=100,
    balance_after=???  # Bu değer nasıl hesaplanacak?
)
```

2. **SmsBalance direkt değiştirmeyin:**

```python
# YANLIŞ ❌
balance = SmsBalance.objects.get(tenant=tenant)
balance.balance += 100
balance.save()  # Transaction oluşturulmadı, tutarsızlık!
```

3. **Payment durumunu direkt değiştirmeyin:**

```python
# YANLIŞ ❌
payment.status = 'completed'
payment.save()  # İlgili servisler aktif edilmedi!
```

### ✅ YAPILMASI GEREKENLER

1. **Her zaman servis katmanını kullanın:**

```python
# DOĞRU ✅
SmsService.add_credits(tenant=tenant, amount=100, ...)
```

2. **Ödeme tamamlama için approve/complete metodlarını kullanın:**

```python
# DOĞRU ✅
payment.approve(admin_user)  # Manuel ödeme
PaymentService.complete_payment(payment, ...)  # İyzico ödeme
```

3. **Transaction ile atomic işlemler yapın:**

```python
# DOĞRU ✅
from django.db import transaction

@transaction.atomic
def my_billing_operation():
    # Tüm işlemler ya hep başarılı olur ya hep geri alınır
    ...
```

---

## Sorun Giderme

### Problem: "NOT NULL constraint failed: billing_smstransaction.balance_after"

**Sebep:** SmsTransaction admin panelden manuel oluşturulmaya çalışıldı.

**Çözüm:** SmsTransaction manuel oluşturulamaz. SmsBalance metodlarını kullanın:

```python
SmsService.add_credits(...)  # veya
SmsService.deduct_credits(...)
```

### Problem: SMS kredileri eklenmiyor

**Kontrol Listesi:**

1. Payment status 'completed' mi?
2. Payment type 'sms_package' mi?
3. sms_package ilişkisi doğru mu?
4. PaymentService.complete_payment() veya payment.approve() çağrıldı mı?

### Problem: Abonelik aktif olmuyor

**Kontrol Listesi:**

1. Payment status 'completed' mi?
2. Payment type 'subscription' mi?
3. subscription ilişkisi doğru mu?
4. PaymentService.complete_payment() veya payment.approve() çağrıldı mı?

---

## Test Senaryoları

### Senaryo 1: Yeni Tenant Onboarding

```python
# 1. Tenant kaydı
tenant = Company.objects.create(name='Test Şirketi', ...)

# 2. Plan seçimi ve satın alma
plan = SubscriptionPlan.objects.get(slug='basic')
subscription = SubscriptionService.create_subscription(tenant, plan)
payment = PaymentService.create_subscription_payment(tenant, subscription)
PaymentService.complete_payment(payment)

# 3. SMS paketi satın alma
package = SMSPackage.objects.get(name='sms_500')
sms_payment = PaymentService.create_sms_payment(tenant, package)
PaymentService.complete_payment(sms_payment)

# 4. Kontroller
assert subscription.status == 'active'
assert SmsService.check_balance(tenant) >= 500
```

### Senaryo 2: SMS Kullanımı ve Tükenme

```python
tenant = Company.objects.get(id=1)

# Başlangıç bakiyesi
initial_balance = SmsService.check_balance(tenant)

# SMS kullanımı
for i in range(10):
    if SmsService.has_sufficient_credits(tenant, 5):
        send_sms(...)  # SMS gönder
        SmsService.deduct_credits(tenant, 5, description=f'Kampanya SMS {i+1}')
    else:
        notify_low_balance(tenant)
        break

# Bakiye kontrolü
final_balance = SmsService.check_balance(tenant)
assert final_balance == initial_balance - (i * 5)
```

---

## İlgili Dosyalar

- **Modeller:** `apps/billing/models/`
  - `plans.py` - SubscriptionPlan, SMSPackage
  - `subscriptions.py` - TenantSubscription, SubscriptionHistory
  - `sms.py` - SmsBalance, SmsTransaction
  - `payments.py` - Payment, Invoice

- **Servisler:** `apps/billing/services.py`
  - SmsService
  - SubscriptionService
  - PaymentService

- **Admin:** `apps/billing/admin.py`

---

## Katkıda Bulunma

Bu döküman güncel tutulmalıdır. Yeni özellik eklendiğinde veya workflow değiştiğinde bu dökümanı güncelleyin.

**Son Güncelleme:** 2026-01-29

Yöntem 2: Admin Panel (Payment Onayı)
SMSPackage oluştur (yoksa)

Admin → Billing → SMS Packages → Add
Payment oluştur

Admin → Billing → Payments → Add
Payment type: SMS Package Payment
Payment method: Bank Transfer veya EFT
Status: Pending
SMS package: Seçili paket
Payment'ı onayla

Payment'ı aç → Actions → "Approve selected manual payments"
