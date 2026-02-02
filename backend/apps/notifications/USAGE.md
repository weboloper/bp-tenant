# Notifications Module - Usage Guide

Bu dokümantasyon, notifications modülünün kullanım örneklerini içerir.

## Kurulum

```python
# settings.py INSTALLED_APPS
INSTALLED_APPS = [
    # ...
    'providers',          # SMS/Email provider infrastructure
    'notifications',      # Notifications (SMS, Email, In-App)
]
```

```bash
# Migration
python manage.py makemigrations providers notifications
python manage.py migrate
```

---

## 1. Template ile Bildirim (Önerilen Yöntem)

En yaygın kullanım şekli. Template'ler Django Admin'den yönetilir.

```python
from notifications.services import notify

# User'a bildirim gönder (SMS + Email + In-App)
result = notify(
    code="task_assigned",
    tenant=company,
    recipient=user,  # User instance
    context={
        "user_name": user.get_full_name(),
        "task_title": "Yeni Görev",
        "due_date": "15 Ocak 2025",
    }
)

print(result)
# {
#     "success": True,
#     "channels": {
#         "sms": {"success": True, "outbound_id": 123, "credits_used": 1},
#         "email": {"success": True, "outbound_id": 124}
#     }
# }
```

### Belirli Kanalları Geçersiz Kılma

```python
# Sadece SMS gönder (template'de email de aktif olsa bile)
result = notify(
    code="task_assigned",
    tenant=company,
    recipient=user,
    context={...},
    channels=["sms"]  # Sadece SMS
)
```

### Gönderen Bilgisi Ekleme

```python
result = notify(
    code="task_assigned",
    tenant=company,
    recipient=user,
    context={...},
    sent_by=request.user  # Kim gönderdi
)
```

---

## 2. Direkt In-App Bildirim

Template kullanmadan doğrudan in-app bildirim oluşturur.

### Tek Kullanıcıya

```python
from notifications.services import NotificationDispatcher

# User'a bildirim
NotificationDispatcher.notify_user(
    user=target_user,
    notification_type="task_assigned",
    title="Yeni Görev",
    message="Size yeni bir görev atandı.",
    tenant=company,
    sender_user=request.user,
    action_url=f"/tasks/{task.id}",
    action_label="Görüntüle",
    related_object=task,  # GenericForeignKey
    priority="high",
    metadata={"task_id": task.id}
)
```

### Tüm Tenant Kullanıcılarına (Broadcast)

```python
from notifications.services import NotificationDispatcher

# Tüm kullanıcılara bildir
NotificationDispatcher.notify_tenant_users(
    tenant=company,
    notification_type="system_announcement",
    title="Duyuru",
    message="Yeni özellikler eklendi!",
    exclude_user=request.user,  # Gönderen kullanıcı hariç
)
```

---

## 3. System Bildirimi

Platform tarafından gönderilen bildirimler (tenant bağımsız).

```python
from notifications.services import NotificationDispatcher

# SMS kredisi uyarısı
NotificationDispatcher.system_notify_user(
    user=tenant_owner,
    notification_type="sms_credit_low",
    title="SMS Krediniz Azalıyor",
    message=f"Kalan krediniz: {balance}. Hemen yükleyin!",
    priority="high",
    action_url="/settings/billing/sms",
    action_label="Kredi Yükle"
)

# Sistem duyurusu
NotificationDispatcher.system_notify_user(
    user=user,
    notification_type="system_announcement",
    title="Yeni Özellik!",
    message="Artık toplu SMS gönderebilirsiniz.",
    priority="normal"
)
```

---

## 4. Doğrudan Channel Kullanımı

Template olmadan doğrudan SMS/Email gönderimi.

### SMS Gönderme

```python
from notifications.channels import get_channel
from notifications.constants import Channel

sms_channel = get_channel(Channel.SMS)

result = sms_channel.send(
    recipient="5551234567",
    content={"content": "Merhaba, bildiriminiz var."},
    tenant=company,
    sent_by=request.user,
    notification_type="custom",
    recipient_name="Ahmet Yılmaz",  # Opsiyonel
    check_credit=True  # Kredi kontrolü (default: True)
)

print(result)
# {
#     "success": True,
#     "outbound_id": 125,
#     "message_id": "MOCK_ABC123",
#     "credits_used": 1
# }
```

### Email Gönderme

```python
from notifications.channels import get_channel
from notifications.constants import Channel

email_channel = get_channel(Channel.EMAIL)

result = email_channel.send(
    recipient="user@example.com",
    content={
        "subject": "Bildirim",
        "body_text": "Bildiriminiz var.",
        "body_html": "<h1>Bildiriminiz var.</h1>"
    },
    tenant=company,
    sent_by=request.user,
    notification_type="custom",
    recipient_name="Ahmet Yılmaz"
)
```

### In-App Bildirim

```python
from notifications.channels import get_channel
from notifications.constants import Channel

in_app_channel = get_channel(Channel.IN_APP)

result = in_app_channel.send(
    recipient=user,  # User instance
    content={
        "title": "Yeni Görev",
        "message": "Size yeni bir görev atandı."
    },
    tenant=company,
    sender_user=admin_user,
    notification_type="task_assigned",
    priority="high",
    action_url="/tasks/123",
    action_label="Görevi Aç",
    related_object=task
)
```

---

## 5. Provider Doğrudan Kullanımı

Düşük seviye SMS/Email API'si.

### SMS Provider

```python
from providers.sms import get_sms_provider

provider = get_sms_provider()

# Tekli SMS
result = provider.send(
    phone="5551234567",
    message="Test mesajı",
    sender_id="COMPANY"  # Opsiyonel
)

print(result)
# SMSResult(success=True, message_id="123", status=SMSStatus.SENT, credits_used=1)

# Toplu SMS
bulk_result = provider.send_bulk(
    recipients=["5551234567", "5559876543"],
    message="Kampanya mesajı",
    sender_id="COMPANY"
)

# Bakiye sorgulama
balance = provider.get_balance()

# Kredi hesaplama
credits = provider.calculate_credits("Merhaba dünya")  # 1
credits = provider.calculate_credits("Türkçe karakterli mesaj: çğışöü")  # 1 (UCS2)
```

### Email Provider

```python
from providers.email import get_email_provider

provider = get_email_provider()

result = provider.send(
    to_email="user@example.com",
    subject="Hoş Geldiniz",
    body_text="Hoş geldiniz!",
    body_html="<h1>Hoş geldiniz!</h1>",
    from_email="noreply@company.com",
    from_name="Company App"
)
```

---

## 6. API Kullanımı

REST API üzerinden bildirim gönderme.

### Template ile Gönderim

```http
POST /api/v1/notifications/send/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "task_assigned",
    "recipient_id": 123,
    "context": {
        "user_name": "Ahmet",
        "task_title": "Görev"
    },
    "channels": ["sms"]  // Opsiyonel
}
```

### Doğrudan SMS

```http
POST /api/v1/notifications/send/sms/
Authorization: Bearer <token>
Content-Type: application/json

{
    "phone": "5551234567",
    "message": "Bildiriminiz var."
}
```

### Doğrudan Email

```http
POST /api/v1/notifications/send/email/
Authorization: Bearer <token>
Content-Type: application/json

{
    "email": "user@example.com",
    "subject": "Bildirim",
    "body_text": "Bildiriminiz var.",
    "body_html": "<h1>Bildirim</h1>"
}
```

### SMS Kredi Kontrolü

```http
GET /api/v1/notifications/sms/balance/
Authorization: Bearer <token>

Response:
{
    "tenant_credits": 500,
    "provider_balance": {"success": true, "balance": 1000, "currency": "TL"}
}
```

---

## 7. Notification Types

Kullanılabilir bildirim tipleri (`notifications/constants.py`):

### System → Tenant
- `system_announcement` - Sistem duyurusu
- `billing_alert` - Fatura uyarısı
- `sms_credit_low` - SMS kredisi düşük
- `sms_credit_depleted` - SMS kredisi bitti
- `subscription_expiry` - Abonelik bitiyor
- `subscription_expired` - Abonelik bitti
- `feature_update` - Yeni özellik

### Tenant → User
- `task_assigned` - Görev atandı
- `campaign` - Kampanya
- `custom` - Özel mesaj

---

## 8. Best Practices

1. **Template kullanın**: Mümkün olduğunca `notify()` fonksiyonunu template ile kullanın.

2. **Context'i tam verin**: Template'de kullanılan tüm değişkenleri context'e ekleyin.

3. **Kredi kontrolü**: SMS göndermeden önce kredi kontrolü otomatik yapılır.

4. **Hata yönetimi**: `result['success']` değerini kontrol edin.

5. **Test ortamı**: Development'ta `MockSMSProvider` ve `MockEmailProvider` otomatik kullanılır.

```python
# Hata kontrolü örneği
result = notify(code="...", ...)

if not result['success']:
    logger.error(f"Notification failed: {result.get('error')}")

for channel, channel_result in result.get('channels', {}).items():
    if not channel_result.get('success'):
        logger.warning(f"{channel} failed: {channel_result.get('error')}")
```
