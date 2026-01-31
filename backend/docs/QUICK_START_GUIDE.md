# Quick Start Guide - Notifications & Messaging

## What Was Implemented

### Centralized SMS Infrastructure
All tenants (salon owners) use **ONE NetGSM account** configured globally. No per-tenant SMS setup needed.

### Three Notification Channels
1. **In-App**: Database notifications (instant)
2. **Email**: SMTP email delivery
3. **Push**: Firebase Cloud Messaging (FCM)

---

## Quick Usage Examples

### 1. Send SMS (Most Common Use Case)

```python
from messaging.services import MessagingService
from tenants.models import Company

# Get tenant
tenant = Company.objects.get(id=1)

# Send SMS to a customer
message = MessagingService.send_sms(
    tenant=tenant,
    phone='5551234567',
    message='Randevunuz yarın saat 15:00 te.',
    message_type='transactional'
)

# Check result
print(f"SMS sent: {message.status}")
print(f"Message ID: {message.provider_message_id}")
print(f"Credits used: {message.credits_used}")
```

### 2. Send Bulk SMS

```python
# Send to multiple recipients
result = MessagingService.send_bulk_sms(
    tenant=tenant,
    recipients=['5551234567', '5559876543', '5551112233'],
    message='Kampanya: Bu hafta %20 indirim!',
    message_type='promotional'
)

print(f"Batch ID: {result['batch_id']}")
print(f"Sent: {result['successful']}/{result['total']}")
print(f"Total credits: {result['credits_used']}")
```

### 3. Check SMS Delivery Status

```python
from messaging.models import Message

# Get message
message = Message.objects.get(id=123)

# Update status from provider
updated_message = MessagingService.get_delivery_status(message)

print(f"Status: {updated_message.status}")
if updated_message.delivered_at:
    print(f"Delivered: {updated_message.delivered_at}")
```

### 4. Check Provider Balance (System Admin)

```python
# Check NetGSM account balance
balance_info = MessagingService.get_provider_balance()

print(f"Provider: {balance_info['provider']}")
print(f"Balance: {balance_info['balance']} credits")
```

### 5. Send In-App Notification

```python
from notifications.channels import InAppChannel

# Assuming you have a notification object
result = InAppChannel.deliver(notification, recipient_user)

if result['success']:
    print(f"In-app notification delivered at {result['delivered_at']}")
```

### 6. Send Email Notification

```python
from notifications.channels import EmailChannel

result = EmailChannel.deliver(notification, recipient_user)

if result['success']:
    print(f"Email sent to {result['email']}")
else:
    print(f"Email failed: {result['error']}")
```

### 7. Send Push Notification

```python
from notifications.channels import PushChannel

result = PushChannel.deliver(notification, recipient_user)

if result['success']:
    print(f"Push sent: {result['fcm_message_id']}")
```

---

## Configuration

SMS provider configuration is managed via database, not environment variables.

### Setup via Django Admin

1. Go to Django Admin → Providers → SMS Provider Configs
2. Create a new config:
   - **Provider**: `netgsm`, `twilio`, or `mock`
   - **Is Active**: ✓
   - **Is Default**: ✓
   - **Credentials**: JSON with provider-specific credentials

### Example Credentials

**NetGSM:**
```json
{
  "username": "your_username",
  "password": "your_password",
  "sender_id": "BPSALON"
}
```

**Twilio:**
```json
{
  "account_sid": "ACxxxxx",
  "auth_token": "xxxxx",
  "from_number": "+1234567890"
}
```

**Mock (Development):**
```json
{}
```
In DEBUG mode, if no active provider is configured, mock provider is used automatically.

---

## Important Notes

### SMS Credits
- Credits are checked BEFORE sending
- Credits are deducted ONLY on successful send
- If send fails, credits are NOT deducted
- Turkish characters: 70 chars/SMS (vs 160 for ASCII)
- Long messages use concatenated SMS (multiple credits)

### Error Handling

```python
from tenant_resources.exceptions import InsufficientSmsCredit

try:
    message = MessagingService.send_sms(
        tenant=tenant,
        phone='5551234567',
        message='Test message'
    )
except InsufficientSmsCredit as e:
    print(f"Not enough credits: {e}")
    # Notify tenant to purchase more credits
except Exception as e:
    print(f"Send failed: {e}")
```

### Credit Calculation

```python
from messaging.providers import get_sms_provider

provider = get_sms_provider()

# Calculate credits before sending
message = "Randevunuz yarın saat 15:00 te."
credits = provider.calculate_credits(message)
print(f"This message will use {credits} credits")
```

---

## Automated Background Tasks

These run automatically via Celery:

1. **Update Delivery Statuses** (every 5 minutes)
   - Queries NetGSM for delivery updates
   - Updates message status in database

2. **Retry Failed Messages** (hourly)
   - Retries messages that failed (up to max_retries)
   - Useful for temporary network issues

3. **Send Scheduled Messages** (every minute)
   - Sends messages with scheduled_at timestamp
   - Useful for appointment reminders

4. **Check Provider Balance** (daily)
   - Checks NetGSM account balance
   - Alerts if balance is low

---

## Testing

Run the integration test:

```bash
cd backend
python test_complete_integration.py
```

Expected output:
```
[OK] Centralized SMS provider configured
[OK] SMS status tracking with enum (7 states)
[OK] Credit calculation supports Turkish characters
[OK] All notification channels available
[OK] Provider implements all required methods
```

---

## Common Scenarios

### Appointment Reminder

```python
# Send 24 hours before appointment
message = MessagingService.send_sms(
    tenant=salon,
    phone=customer.phone,
    message=f"Merhaba {customer.name}, yarın saat {appointment.time} randevunuz var.",
    message_type='transactional'
)
```

### Birthday Greeting

```python
# Send on birthday
message = MessagingService.send_sms(
    tenant=salon,
    phone=customer.phone,
    message=f"Doğum gününüz kutlu olsun {customer.name}! {salon.name}",
    message_type='promotional'
)
```

### Promotional Campaign

```python
# Send to all customers
customers = Customer.objects.filter(salon=salon, consent_sms=True)
phones = [c.phone for c in customers]

result = MessagingService.send_bulk_sms(
    tenant=salon,
    recipients=phones,
    message="Bu hafta %30 indirim! Randevu için: 0212 XXX XXXX",
    message_type='promotional'
)
```

---

## File Structure

```
apps/
├── messaging/                    # External messaging (SMS/WhatsApp/Telegram)
│   ├── providers/
│   │   ├── sms_provider.py      # Base provider
│   │   ├── netgsm.py            # NetGSM integration
│   │   └── mock.py              # Development mock
│   ├── services/
│   │   └── messaging_service.py # Main service
│   └── tasks.py                 # Celery tasks
│
└── notifications/                # Internal notifications (in-app/email/push)
    └── channels/
        ├── in_app.py            # In-app delivery
        ├── email.py             # Email delivery
        └── push.py              # Push delivery
```

---

## Documentation

- **MESSAGING_INFRASTRUCTURE.md** - Complete architecture and usage guide
- **IMPLEMENTATION_SUMMARY.md** - What was implemented and why
- **QUICK_START_GUIDE.md** - This file (quick reference)

---

## Next Steps

To complete the notification system, you need to implement:

1. **Notification Models** (from plan)
   - Notification (with polymorphic sender/recipient)
   - NotificationPreference
   - NotificationTemplate

2. **Service Layer** (from plan)
   - SystemToTenantNotificationService
   - TenantToClientNotificationService
   - SystemToClientNotificationService
   - DeliveryService

3. **Admin Panel**
   - Notification admin
   - Template admin

4. **API Endpoints**
   - List notifications
   - Mark as read
   - Get statistics

See the plan file for detailed implementation steps.
