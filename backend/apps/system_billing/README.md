# System Billing Module

Complete payment and invoicing system for subscription management.

## ✅ Completed Features

### 1. Models & Database
- ✅ **Payment Model** - Gateway-agnostic payment tracking
- ✅ **Invoice Model** - Invoice management with PDF upload
- ✅ **Migrations** - Applied successfully
- ✅ **Admin Interface** - Full CRUD with approval workflow

### 2. Payment Gateway Integration
- ✅ **iyzico Service** - Checkout Form API integration
- ✅ **Gateway Abstraction** - Easy to switch providers
- ✅ **PCI Compliance** - No card data storage

### 3. API Endpoints
- ✅ **Subscription Plans** - Public listing
- ✅ **iyzico Checkout** - Initialize payment
- ✅ **Manual Payments** - Bank transfer/EFT submission
- ✅ **Payment History** - List and detail views
- ✅ **Invoice Management** - List, detail, download
- ✅ **iyzico Callback** - Automatic payment verification

### 4. Permissions & Security
- ✅ **Tenant Isolation** - Users only see their own data
- ✅ **Staff Access** - Admins can see all payments
- ✅ **Billing Permission** - Uses existing `can_manage_billing`
- ✅ **File Validation** - Payment proof size and type checks

---

## 📁 Module Structure

```
system_billing/
├── models.py              ✅ Payment + Invoice models
├── admin.py               ✅ Admin interface with approval workflow
├── services/
│   ├── __init__.py        ✅ Service exports
│   └── iyzico.py          ✅ iyzico API integration
├── api/
│   ├── __init__.py        ✅ API package
│   ├── serializers.py     ✅ DRF serializers
│   ├── views.py           ✅ ViewSets and endpoints
│   └── urls.py            ✅ URL routing
├── migrations/
│   └── 0001_initial.py    ✅ Initial migration
├── API_DOCUMENTATION.md   ✅ Complete API docs
├── GATEWAY_USAGE.md       ✅ Gateway flexibility guide
└── README.md              ✅ This file
```

---

## 🚀 Quick Start

### 1. Environment Setup

Add to your `.env` file:

```bash
# iyzico Credentials
IYZICO_API_KEY=your-api-key
IYZICO_SECRET_KEY=your-secret-key
IYZICO_TEST_MODE=True

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### 2. Run Migrations (Already Done)

```bash
python manage.py migrate system_billing
```

### 3. Create Subscription Plans

Via Django admin or shell:

```python
from system_subscriptions.models import SubscriptionPlan
from decimal import Decimal

SubscriptionPlan.objects.create(
    name='Basic Plan',
    price=Decimal('99.00'),
    billing_cycle='monthly',
    max_employee=5,
    max_locations=1,
    is_active=True
)
```

### 4. Test API Endpoints

```bash
# Get subscription plans
curl http://localhost:8000/api/v1/billing/plans/

# Initialize iyzico checkout (requires auth)
curl -X POST http://localhost:8000/api/v1/billing/payments/subscription/checkout/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subscription_plan_id": 1, "billing_cycle": "monthly", ...}'
```

---

## 📖 Documentation

### API Documentation
Complete API documentation with examples: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

### Gateway Flexibility
How to switch payment providers: [GATEWAY_USAGE.md](./GATEWAY_USAGE.md)

---

## 🔑 Key Features

### Payment Model (Gateway-Agnostic)
```python
payment = Payment.objects.create(
    tenant=company,
    payment_type='subscription',
    payment_method='iyzico',
    amount=Decimal('99.00'),
    gateway_name='iyzico',  # Can be: iyzico, stripe, paypal, etc.
    gateway_transaction_id='24478123',
    gateway_token='077aff05-...',
    gateway_data={
        'conversation_id': 'payment_123',
        'fraud_status': 1
    }
)
```

### iyzico Integration
```python
from system_billing.services import IyzicoService

iyzico = IyzicoService()
result = iyzico.initialize_checkout(
    amount=Decimal('99.00'),
    currency='TRY',
    buyer_info={...},
    basket_items=[...],
    callback_url='https://...'
)

if result.success:
    checkout_html = result.checkout_form_content
```

### Manual Payment Approval
```python
# Admin approves manual payment
payment.approve(admin_user)
# → status = 'completed'
# → subscription activated automatically
```

---

## 🔐 Security

### PCI Compliance
- ✅ **No card storage** - All card data handled by iyzico
- ✅ **Secure tokens** - Only store gateway tokens
- ✅ **HTTPS enforced** - Callback URLs must use HTTPS in production

### Data Isolation
- ✅ **Tenant filtering** - Users only see their company's data
- ✅ **Permission checks** - `can_manage_billing` for admin operations
- ✅ **File validation** - Payment proof size (5MB) and type checks

---

## 🧪 Testing

### Test with iyzico Sandbox

**Test Card (Success):**
```
Card: 5528790000000008
Expiry: 12/30
CVV: 123
3D Secure: 123456
```

**Test Card (Failure):**
```
Card: 5406670000000009
Expiry: 12/30
CVV: 123
```

More test cards: https://dev.iyzipay.com/en/test-cards

---

## 📊 Admin Workflow

### Approve Manual Payments
1. Navigate to: Django Admin → System Billing → Payments
2. Filter by: Status = Pending
3. Select payments to approve
4. Action: "Approve selected manual payments"
5. Subscriptions activated automatically

### Create Invoices
1. Navigate to: Django Admin → System Billing → Invoices
2. Click "Add Invoice"
3. Select payment, upload PDF, enter invoice details
4. Save → Tenant can download from API

---

## 🔄 Payment Flows

### iyzico Flow
```
User selects plan
  ↓
POST /payments/subscription/checkout/
  ↓
Backend creates pending Payment
  ↓
Backend initializes iyzico checkout
  ↓
Frontend shows checkout form
  ↓
User enters card on iyzico
  ↓
iyzico calls callback
  ↓
Backend verifies payment
  ↓
Subscription activated
```

### Manual Flow
```
User selects plan
  ↓
POST /payments/subscription/manual/
  ↓
Backend creates pending Payment
  ↓
Admin reviews in Django admin
  ↓
Admin approves payment
  ↓
Subscription activated
```

---

## 🎯 Next Steps

### Implementation Priority

**Phase 1: Core Testing** ✅ DONE
- [x] Models and migrations
- [x] Admin interface
- [x] iyzico service layer
- [x] API endpoints

**Phase 2: Integration** (Next)
- [ ] Frontend integration (React/Vue)
- [ ] Test end-to-end payment flow
- [ ] Error handling and edge cases
- [ ] Email notifications

**Phase 3: Production** (Future)
- [ ] Production iyzico credentials
- [ ] HTTPS enforcement
- [ ] Monitoring and logging
- [ ] Backup and recovery

---

## 📝 Notes

### Gateway Flexibility
The system is designed to be gateway-agnostic. To add a new payment provider:

1. **No schema changes needed** - All gateway-specific data in `gateway_data` JSON field
2. **Create new service** - Similar to `IyzicoService`
3. **Update API views** - Add new endpoint or extend existing
4. **Update `gateway_name`** - Use new provider name

Example for Stripe:
```python
payment = Payment.objects.create(
    gateway_name='stripe',  # Changed from 'iyzico'
    gateway_transaction_id='pi_3Lb123ABC',
    gateway_data={
        'customer_id': 'cus_abc123',
        'payment_method': 'pm_xyz789'
    }
)
```

### Permissions
The module uses the existing `can_manage_billing` permission from `CompanyRolePermission` model (line 399-402 in tenants/models.py). No migration needed.

---

## 🐛 Troubleshooting

### Payment Status Not Updating
- Check iyzico callback URL is accessible
- Verify `FRONTEND_URL` setting is correct
- Check logs for callback errors

### Manual Payment Not Approved
- Ensure payment has `payment_proof` uploaded
- Check admin has staff permissions
- Verify payment status is `pending`

### iyzico Errors
- Verify credentials in `.env`
- Check `IYZICO_TEST_MODE` setting
- Review `payment.metadata` for error details

---

## 📞 Support

- **API Documentation:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **iyzico Docs:** https://docs.iyzico.com/
- **Django Logs:** Check `logs/debug.log` for errors
