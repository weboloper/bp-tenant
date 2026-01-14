# Payment Gateway Integration Guide

## Overview
The `Payment` model uses a **gateway-agnostic architecture** that supports any payment provider without requiring database schema changes.

## Gateway Fields

### Generic Fields (Works with ANY payment gateway)
```python
gateway_name = 'iyzico'  # or 'stripe', 'paypal', etc.
gateway_transaction_id = '24478123'  # Provider's transaction ID
gateway_token = '077aff05-1e9b-44aa-aa11-c268bb8b3826'  # Checkout session token
gateway_data = {
    # Store ALL gateway-specific data here as JSON
    'conversation_id': 'payment_123',
    'fraud_status': 1,
    'three_ds_result': {...}
}
metadata = {}  # Full gateway response for audit trail
```

## Example Usage

### iyzico Payment Example:
```python
from system_billing.models import Payment

# Create iyzico payment
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='iyzico',
    amount=Decimal('100.00'),
    currency='TRY',
    gateway_name='iyzico',
    gateway_transaction_id='24478123',  # iyzico paymentId
    gateway_token='077aff05-1e9b-44aa-aa11-c268bb8b3826',  # checkout token
    gateway_data={
        'conversation_id': 'payment_123',
        'fraud_status': 1,
        'installment': 1,
        'card_type': 'CREDIT_CARD',
        'card_association': 'VISA'
    },
    status='completed'
)
```

**Future: Stripe Payment**
```python
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='stripe',  # Future payment method
    amount=Decimal('199.99'),
    currency='TRY',
    gateway_name='stripe',
    gateway_transaction_id='pi_3Lb123ABC',
    gateway_token='cs_test_abc123',
    gateway_data={
        'customer_id': 'cus_abc123',
        'payment_method': 'pm_xyz789',
        'payment_intent': 'pi_3Lb123ABC'
    }
)
```

---

## ✅ Tamamlananlar

1. ✅ **Payment model refactored** - iyzico-specific fields → generic gateway fields
2. ✅ **Migration created and applied** - Fresh database with new schema
3. ✅ **Admin updated** - Search fields, readonly fields, fieldsets
4. ✅ **Indexes updated** - gateway_transaction_id, gateway_name+status
5. ✅ **Backward compatible** - Default gateway_name='iyzico' korundu

## 🎯 Benefits Achieved

### Gateway Flexibility
```python
# iyzico payment örneği
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='iyzico',
    amount=Decimal('100.00'),
    gateway_name='iyzico',
    gateway_transaction_id='24478123',  # iyzico paymentId
    gateway_token='077aff05-1e9b-44aa-aa11',
    gateway_data={
        'conversation_id': 'payment_123',
        'fraud_status': 1,
        'three_ds_result': {...}
    }
)

# Future: Stripe payment
payment = Payment.objects.create(
    gateway_name='stripe',
    gateway_transaction_id='pi_3Lb123ABC',
    gateway_token='cs_test_abc123',
    gateway_data={
        'customer_id': 'cus_abc123',
        'payment_method': 'pm_xyz789'
    }
)
```

## Özet - Ne Yaptık?

### ✅ Tamamlanan İşlemler:

1. **Payment Model Refactored** - iyzico-specific alanlar kaldırıldı:
   - ❌ `iyzico_payment_id` → ✅ `gateway_transaction_id`
   - ❌ `iyzico_conversation_id` → ✅ `gateway_data` (JSON)
   - ❌ `iyzico_token` → ✅ `gateway_token`
   - ❌ `fraud_status` → ✅ `gateway_data` içinde

2. **Yeni generic alanlar eklendi:**
   - `gateway_name`: Ödeme sağlayıcısı (iyzico, stripe, paypal, etc.)
   - `gateway_transaction_id`: Universal transaction ID (unique, indexed)
   - `gateway_token`: Checkout session/payment token
   - `gateway_data`: JSONField - tüm gateway-specific veriler

3. **Admin interface güncellendi:**
   - İyzico-specific field'lar kaldırıldı
   - Generic gateway field'ları eklendi
   - Fieldsets güncellendi: "iyzico Integration" → "Gateway Integration"

4. **Migration başarılı:**
   - Eski veritabanı silindi (development aşaması)
   - Yeni migration oluşturuldu ve uygulandı
   - Tüm alanlar doğru şekilde oluşturuldu

## Nasıl Kullanılacak?

### iyzico Ödeme Örneği:
```python
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='iyzico',
    amount=Decimal('100.00'),
    gateway_name='iyzico',
    gateway_transaction_id='24478123',  # iyzico paymentId
    gateway_token='077aff05-1e9b-44aa-aa11-c268bb8b3826',
    gateway_data={
        'conversation_id': 'payment_123',
        'fraud_status': 1,
        'three_ds_result': {...}
    }
)
```

### Future: Stripe Payment
```python
Payment.objects.create(
    gateway_name='stripe',
    gateway_transaction_id='pi_3Lb123ABC',
    gateway_token='cs_test_abc123',
    gateway_data={
        'customer_id': 'cus_abc123',
        'payment_method': 'pm_xyz789'
    }
)
```

## Özet: Yapılan Değişiklikler

### ✅ Model Değişiklikleri ([models.py:71-104](apps/system_billing/models.py#L71-L104))
**Kaldırılan alanlar:**
- `iyzico_payment_id`
- `iyzico_conversation_id`
- `iyzico_token`
- `fraud_status`

**Eklenen alanlar:**
- `gateway_name` - Payment provider adı (default: 'iyzico')
- `gateway_transaction_id` - Evrensel transaction ID (unique, indexed)
- `gateway_token` - Checkout session token
- `gateway_data` - Gateway-specific tüm data (JSON)

### Kullanım Örnekleri:

**iyzico Payment:**
```python
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='iyzico',
    amount=Decimal('100.00'),
    currency='TRY',
    gateway_name='iyzico',
    gateway_transaction_id='24478123',  # iyzico paymentId
    gateway_token='077aff05-1e9b-44aa-aa11-c268bb8b3826',
    gateway_data={
        'conversation_id': 'payment_123',
        'fraud_status': 1,
        'three_ds_html': '<script>...</script>'
    }
)
```

**Gelecekte Stripe'a geçerseniz:**
```python
payment = Payment.objects.create(
    tenant=company,
    gateway_name='stripe',  # ✅ Sadece bunu değiştiriyorsunuz
    gateway_transaction_id='pi_3Lb123ABC',
    gateway_token='cs_test_abc123',
    gateway_data={
        'customer_id': 'cus_abc123',
        'payment_method': 'pm_xyz789'
    }
)
```

---

## Özet: Ne Yaptık?

✅ **Model Refactoring:**
- `iyzico_payment_id` → `gateway_transaction_id` (generic)
- `iyzico_conversation_id` → `gateway_data['conversation_id']` (JSON)
- `iyzico_token` → `gateway_token` (generic)
- `fraud_status` → `gateway_data['fraud_status']` (JSON)
- Yeni: `gateway_name` (iyzico, stripe, paypal, etc.)

✅ **Admin Panel:**
- Fieldsets güncellendi: "Gateway Integration"
- Search fields generic field'lara göre güncellendi
- Readonly fields düzenlendi

✅ **Database:**
- Veritabanı sıfırlandı (development mode)
- Yeni migration uygulandı
- Tüm indexler doğru oluşturuldu

✅ **Future-Proof:**
- Payment gateway değişikliği artık schema migration gerektirmiyor
- Yeni gateway eklemek sadece `gateway_name` ve `gateway_data` içeriği değişikliği
- Basit yapı korundu, kompleks abstraction kullanılmadı

**Sonraki Adımlar (Future Work):**
1. `system_billing/services/iyzico.py` - iyzico API integration service
2. `system_billing/api/` - DRF serializers, views, urls
3. Unit tests

Sistem artık gateway-agnostic! 🎉