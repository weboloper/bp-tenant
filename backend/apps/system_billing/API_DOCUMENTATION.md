# System Billing API Documentation

## Overview
API endpoints for subscription payments, invoices, and payment management.

**Base URL:** `/api/v1/billing/`

---

## Authentication
All endpoints require authentication except for public subscription plans listing.

**Header:**
```
Authorization: Bearer <JWT_TOKEN>
```

---

## Endpoints

### 1. Subscription Plans

#### List Plans (Public)
```http
GET /api/v1/billing/plans/
```

**Query Parameters:**
- `billing_cycle`: Filter by `monthly` or `yearly`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Basic Plan",
    "price": "99.00",
    "billing_cycle": "monthly",
    "billing_cycle_display": "Monthly",
    "max_employee": 5,
    "max_locations": 1,
    "max_appointments_per_month": 100,
    "has_online_booking": true,
    "has_sms_notifications": false,
    "has_analytics": false,
    "features": {},
    "is_active": true
  }
]
```

#### Get Plan Details
```http
GET /api/v1/billing/plans/{id}/
```

---

### 2. Payments

#### List Payments
```http
GET /api/v1/billing/payments/
```

**Query Parameters:**
- `status`: Filter by payment status (pending, completed, failed, etc.)
- `payment_type`: Filter by type (subscription, sms_package)
- `payment_method`: Filter by method (iyzico, bank_transfer, eft)
- `search`: Search by transaction ID or bank reference
- `ordering`: Sort by created_at, amount (prefix with - for descending)

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "tenant": 5,
      "tenant_name": "Acme Salon",
      "payment_type": "subscription",
      "payment_type_display": "Subscription Payment",
      "payment_method": "iyzico",
      "payment_method_display": "iyzico Checkout Form",
      "amount": "99.00",
      "currency": "TRY",
      "status": "completed",
      "status_display": "Completed",
      "gateway_name": "iyzico",
      "gateway_transaction_id": "24478123",
      "subscription": 3,
      "subscription_plan": "Basic Plan",
      "bank_reference": null,
      "approved_by": null,
      "approved_at": null,
      "notes": "",
      "created_at": "2026-01-13T20:30:00Z",
      "updated_at": "2026-01-13T20:31:00Z"
    }
  ]
}
```

#### Get Payment Details
```http
GET /api/v1/billing/payments/{id}/
```

---

### 3. Create Payment (iyzico)

#### Initialize iyzico Checkout
```http
POST /api/v1/billing/payments/subscription/checkout/
```

**Request Body:**
```json
{
  "subscription_plan_id": 1,
  "billing_cycle": "monthly",
  "buyer_name": "John",
  "buyer_surname": "Doe",
  "buyer_email": "john@example.com",
  "buyer_phone": "+905555555555",
  "buyer_identity_number": "11111111111",
  "buyer_address": "123 Main St, Apt 4B",
  "buyer_city": "Istanbul",
  "buyer_country": "Turkey",
  "buyer_zip_code": "34000",
  "enabled_installments": [1, 2, 3, 6, 9]
}
```

**Response:**
```json
{
  "payment_id": 123,
  "checkout_form_content": "<div id=\"iyzipay-checkout-form\"... </div><script>...</script>",
  "status": "pending"
}
```

**Usage:**
1. Call this endpoint to initialize checkout
2. Inject `checkout_form_content` HTML into your frontend page
3. User completes payment on iyzico form
4. iyzico redirects to callback URL
5. Frontend redirects to: `{FRONTEND_URL}/billing/payment-result/{payment_id}/`

---

### 4. Create Payment (Manual)

#### Submit Manual Payment
```http
POST /api/v1/billing/payments/subscription/manual/
Content-Type: multipart/form-data
```

**Request Body (Form Data):**
```
subscription_plan_id: 1
payment_method: bank_transfer  (or "eft")
bank_reference: REF123456  (optional)
payment_proof: <file>  (optional - image or PDF, max 5MB)
notes: Paid via bank transfer on 2026-01-13  (optional)
```

**Response:**
```json
{
  "payment_id": 124,
  "status": "pending",
  "message": "Payment submitted. Awaiting admin approval.",
  "amount": "99.00",
  "currency": "TRY"
}
```

**Notes:**
- Payment will be in `pending` status until admin approves
- Admin can approve via Django admin panel
- After approval, subscription will be activated

---

### 5. iyzico Callback (Internal)

#### Handle iyzico Callback
```http
GET /api/v1/billing/payments/iyzico/callback/?token=xxx
```

**Query Parameters:**
- `token`: Checkout form token (provided by iyzico)

**Response:**
```json
{
  "success": true,
  "payment_id": 123,
  "status": "completed",
  "redirect_url": "http://localhost:3000/billing/payment-result/123/"
}
```

**Note:** This endpoint is called automatically by iyzico after payment completion. You don't need to call it manually.

---

### 6. Invoices

#### List Invoices
```http
GET /api/v1/billing/invoices/
```

**Query Parameters:**
- `invoice_type`: Filter by type (sale, refund)
- `invoice_date`: Filter by date
- `search`: Search by invoice number, tax number, or company title
- `ordering`: Sort by invoice_date, created_at

**Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "payment": 123,
      "payment_amount": "99.00",
      "tenant_name": "Acme Salon",
      "invoice_type": "sale",
      "invoice_type_display": "Sale Invoice",
      "invoice_number": "INV-2026-001",
      "invoice_date": "2026-01-13",
      "invoice_file": "/media/invoices/INV-2026-001.pdf",
      "invoice_file_url": "http://example.com/media/invoices/INV-2026-001.pdf",
      "tax_office": "Kadıköy",
      "tax_number": "1234567890",
      "company_title": "Acme Beauty Salon Ltd.",
      "notes": "",
      "created_at": "2026-01-13T21:00:00Z",
      "updated_at": "2026-01-13T21:00:00Z"
    }
  ]
}
```

#### Get Invoice Details
```http
GET /api/v1/billing/invoices/{id}/
```

#### Download Invoice
```http
GET /api/v1/billing/invoices/{id}/download/
```

**Response:**
```json
{
  "invoice_number": "INV-2026-001",
  "file_url": "http://example.com/media/invoices/INV-2026-001.pdf"
}
```

---

## Permissions

### Payment Management
- **View payments**: User must belong to a tenant (company)
- **Create iyzico payment**: Authenticated user with company
- **Create manual payment**: Authenticated user with company
- **Manage billing**: `can_manage_billing` permission required (for admin operations)

### Invoice Management
- **View invoices**: User must belong to a tenant
- **Download invoices**: User must belong to tenant that owns the payment

### Admin Operations
- **Approve manual payments**: Django admin staff only
- **Create invoices**: Django admin staff only
- **Manage subscriptions**: Django admin staff only

---

## Payment Flow

### iyzico Payment Flow:
```
1. User selects subscription plan
   ↓
2. Frontend calls: POST /api/v1/billing/payments/subscription/checkout/
   ↓
3. Backend creates pending Payment record
   ↓
4. Backend calls iyzico Initialize API
   ↓
5. Backend returns checkout_form_content
   ↓
6. Frontend injects HTML form
   ↓
7. User enters card details (on iyzico's secure form)
   ↓
8. iyzico redirects to: GET /api/v1/billing/payments/iyzico/callback/?token=xxx
   ↓
9. Backend retrieves payment result from iyzico
   ↓
10. Backend updates Payment status (completed/failed)
    ↓
11. Backend activates subscription (if successful)
    ↓
12. Backend returns redirect URL
    ↓
13. Frontend redirects to: /billing/payment-result/{payment_id}/
```

### Manual Payment Flow:
```
1. User selects subscription plan
   ↓
2. Frontend calls: POST /api/v1/billing/payments/subscription/manual/
   (with payment_proof file)
   ↓
3. Backend creates pending Payment record
   ↓
4. Backend returns: "Awaiting admin approval"
   ↓
5. Admin reviews payment in Django admin
   ↓
6. Admin clicks "Approve Payment" action
   ↓
7. Backend updates Payment status to "completed"
   ↓
8. Backend activates subscription
   ↓
9. User can now access subscription features
```

---

## Error Responses

### 400 Bad Request
```json
{
  "buyer_phone": [
    "Phone must start with +90"
  ],
  "subscription_plan_id": [
    "Subscription plan not found or inactive"
  ]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "User does not belong to any company"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Environment Variables

Add these to your `.env` file:

```bash
# iyzico Settings
IYZICO_API_KEY=your-api-key
IYZICO_SECRET_KEY=your-secret-key
IYZICO_TEST_MODE=True  # False for production

# Frontend URL (for payment redirects)
FRONTEND_URL=http://localhost:3000
```

---

## Testing with iyzico Sandbox

### Test Credentials
Get sandbox credentials from: https://sandbox-merchant.iyzipay.com/

### Test Cards
Use these test cards in sandbox mode:

**Successful Payment:**
- Card Number: `5528790000000008`
- Expiry: `12/30`
- CVV: `123`
- 3D Secure Password: `123456`

**Failed Payment:**
- Card Number: `5406670000000009`
- Expiry: `12/30`
- CVV: `123`

**More test cards:** https://dev.iyzipay.com/en/test-cards

---

## Example Frontend Integration

### React Example (iyzico Checkout):

```javascript
// Step 1: Initialize checkout
const response = await fetch('/api/v1/billing/payments/subscription/checkout/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    subscription_plan_id: 1,
    billing_cycle: 'monthly',
    buyer_name: 'John',
    buyer_surname: 'Doe',
    buyer_email: 'john@example.com',
    buyer_phone: '+905555555555',
    buyer_identity_number: '11111111111',
    buyer_address: '123 Main St',
    buyer_city: 'Istanbul',
    buyer_country: 'Turkey',
    enabled_installments: [1, 2, 3, 6]
  })
});

const data = await response.json();

// Step 2: Inject checkout form
document.getElementById('checkout-container').innerHTML = data.checkout_form_content;

// Step 3: iyzico handles the rest (payment, callback, redirect)
```

### React Example (Manual Payment):

```javascript
const formData = new FormData();
formData.append('subscription_plan_id', 1);
formData.append('payment_method', 'bank_transfer');
formData.append('bank_reference', 'REF123456');
formData.append('payment_proof', fileInput.files[0]);
formData.append('notes', 'Paid on 2026-01-13');

const response = await fetch('/api/v1/billing/payments/subscription/manual/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const data = await response.json();
// Show success message: "Payment submitted. Awaiting admin approval."
```

---

## Next Steps

1. **Test API endpoints** using Postman or curl
2. **Integrate with frontend** using examples above
3. **Configure iyzico credentials** in environment variables
4. **Test payment flow** with sandbox cards
5. **Set up admin workflow** for manual payment approval
6. **Create invoice upload workflow** for admins

---

## Support

For API issues or questions:
- Check Django logs: `tail -f logs/debug.log`
- Check iyzico API docs: https://docs.iyzico.com/
- Review error responses for detailed messages
