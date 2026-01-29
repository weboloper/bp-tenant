# Billing (Faturalama) Modülü

Tenant subscription (abonelik) ve SMS credit (SMS kredisi) yönetim sistemi.

## Hızlı Başlangıç

### 1. Yapılması Gerekenler

```python
# Django shell'i açın
python manage.py shell

# Örnekleri yükleyin
from billing.examples import *

# Tüm örnekleri çalıştırın
run_all_examples()
```

### 2. Yapılmaması Gerekenler ❌

```python
# YANLIŞ: SmsTransaction direkt oluşturmayın
SmsTransaction.objects.create(...)  # ❌

# DOĞRU: Servis katmanını kullanın
SmsService.add_credits(...)  # ✓
```

## Dosya Yapısı

```
billing/
├── models/
│   ├── plans.py           # SubscriptionPlan, SMSPackage
│   ├── subscriptions.py   # TenantSubscription
│   ├── sms.py            # SmsBalance, SmsTransaction
│   └── payments.py       # Payment, Invoice
├── services.py           # İş mantığı servisleri
├── admin.py             # Django admin
├── examples.py          # Kullanım örnekleri
├── WORKFLOW.md          # Detaylı workflow dokümantasyonu
└── README.md            # Bu dosya
```

## Ana Servisler

### SmsService
SMS kredi yönetimi için.

```python
from billing.services import SmsService

# Kredi ekle
SmsService.add_credits(tenant, amount=100, description='Bonus')

# Kredi düş
SmsService.deduct_credits(tenant, amount=5, description='SMS gönderildi')

# Bakiye sorgula
balance = SmsService.check_balance(tenant)
```

### SubscriptionService
Abonelik yönetimi için.

```python
from billing.services import SubscriptionService

# Abonelik oluştur
subscription = SubscriptionService.create_subscription(tenant, plan)

# Aktif abonelik getir
sub = SubscriptionService.get_active_subscription(tenant)

# Durum kontrolü
info = SubscriptionService.check_subscription_status(tenant)
```

### PaymentService
Ödeme işlemleri için.

```python
from billing.services import PaymentService

# SMS paketi ödemesi
payment = PaymentService.create_sms_payment(tenant, package)

# Abonelik ödemesi
payment = PaymentService.create_subscription_payment(tenant, subscription)

# Ödeme tamamlama
PaymentService.complete_payment(payment, gateway_transaction_id='xxx')
```

## Örnekler

Detaylı örnekler için:

- **Kod örnekleri:** [examples.py](examples.py)
- **Workflow dokümantasyonu:** [WORKFLOW.md](WORKFLOW.md)

### Örnek 1: Subscription Satın Alma

```python
from billing.examples import example_1_subscription_purchase

result = example_1_subscription_purchase()
```

### Örnek 2: SMS Paketi Satın Alma

```python
from billing.examples import example_2_sms_package_purchase

result = example_2_sms_package_purchase()
```

### Örnek 3: SMS Kullanımı

```python
from billing.examples import example_3_sms_usage

result = example_3_sms_usage()
```

## Workflow Diyagramları

### Subscription Workflow
```
Plan Seçimi → Subscription (pending) → Payment → Ödeme → Subscription (active)
                    ↓
              Welcome Bonus SMS
```

### SMS Package Workflow
```
Paket Seçimi → Payment (pending) → Ödeme → Payment (completed)
                                      ↓
                              SmsBalance.add_credits()
                                      ↓
                              SmsTransaction (auto)
```

## Admin Paneli

### SmsTransaction Hatası Çözümü

**Problem:** `NOT NULL constraint failed: billing_smstransaction.balance_after`

**Sebep:** SmsTransaction admin panelden manuel oluşturulamaz.

**Çözüm:** SmsTransaction artık read-only. Kredi eklemek için:
1. Admin panelde SmsBalance'ı bulun
2. Veya Django shell'de `SmsService.add_credits()` kullanın

## Migration

```bash
# Migrationları oluştur
python manage.py makemigrations billing

# Migrationları uygula
python manage.py migrate billing
```

## Test

```bash
# Tüm testleri çalıştır
python manage.py test billing

# Örnekleri çalıştır (Django shell)
python manage.py shell
>>> from billing.examples import run_all_examples
>>> run_all_examples()
```

## Önemli Notlar

1. **SMS Transaction:** Hiçbir zaman direkt oluşturmayın, her zaman `SmsService` kullanın
2. **Payment Status:** Payment durumunu direkt değiştirmeyin, `approve()` veya `complete_payment()` kullanın
3. **Atomic Transactions:** Kritik işlemlerde `@transaction.atomic` kullanın
4. **Balance Consistency:** SMS bakiyesi her zaman transaction loglarıyla tutarlı olmalı

## Yardım

- **Detaylı Workflow:** [WORKFLOW.md](WORKFLOW.md)
- **Kod Örnekleri:** [examples.py](examples.py)
- **Django Shell Yardım:**
  ```python
  from billing.examples import show_help
  show_help()
  ```

## Sorun Giderme

### SMS kredileri eklenmiyor
1. Payment status 'completed' mi?
2. `PaymentService.complete_payment()` çağrıldı mı?
3. payment_type ve ilişkiler doğru mu?

### Subscription aktif olmuyor
1. Payment status 'completed' mi?
2. payment_type 'subscription' mi?
3. subscription ilişkisi doğru mu?

### Admin'de SmsTransaction oluşturamıyorum
Bu beklenen davranış! SmsTransaction read-only'dir.
`SmsService.add_credits()` kullanın.

## Katkıda Bulunma

Değişiklik yaparken:
1. Servisleri kullanın (direkt model değişikliği yapmayın)
2. `@transaction.atomic` kullanın
3. Dokümantasyonu güncelleyin
4. Test yazın

---

**Son Güncelleme:** 2026-01-29
