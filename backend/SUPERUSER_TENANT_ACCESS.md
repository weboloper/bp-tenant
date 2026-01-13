# Superuser/Staff Tenant Access

Bu dokümantasyon, superuser ve staff kullanıcıların multi-tenant sistemde farklı company'lere nasıl erişebileceğini açıklar.

## Özellikler

✅ **Superuser/Staff Bypass** - Admin kullanıcılar tenant kısıtlamalarını bypass edebilir
✅ **Company Selection** - Admin kullanıcılar istediği company'yi seçebilir
✅ **Session-based** - Seçilen company session'da saklanır
✅ **Header-based** - API çağrılarında `X-Company-ID` header ile belirtilebilir
✅ **All Companies Access** - Admin kullanıcılar tüm company'leri listeleyebilir
✅ **Deleted Companies** - Admin kullanıcılar soft-deleted company'lere bile erişebilir

## Konfigürasyon

### Settings Ayarı

[config/settings.py](config/settings.py:373-374):
```python
# Multi-Tenant Settings
SUPERUSER_BYPASS_TENANT = True  # Default: True
```

- **`True`**: Superuser/staff kullanıcılar tüm company'lere erişebilir
- **`False`**: Herkes normal tenant kurallarına tabidir (admin dahil)

### Ortam Değişkeni (.env)

```env
SUPERUSER_BYPASS_TENANT=True
```

## Middleware Davranışı

[apps/core/middleware.py](apps/core/middleware.py:29-157)

### Normal Kullanıcılar için:
1. Kullanıcının sahip olduğu company → `request.company`
2. Yoksa, çalıştığı company (employee) → `request.company`
3. Yoksa → `request.company = None`

### Admin Kullanıcılar için (is_superuser=True veya is_staff=True):
1. **X-Company-ID** header kontrol edilir (API için)
2. **Session 'selected_company_id'** kontrol edilir (Web için)
3. Yoksa normal kullanıcı mantığı uygulanır

### Request Attributes

Middleware şu attribute'ları ekler:
- **`request.company`**: Aktif company objesi veya None
- **`request.is_impersonating`**: Boolean (Admin bir company seçtiyse True)

## API Endpoints

### 1. Tüm Company'leri Listele (Admin Only)

**Endpoint:**
```
GET /api/v1/tenants/companies/list_all/
```

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Company A",
    "business_type": 1,
    "description": "...",
    "is_active": true,
    "employee_count": 5,
    "is_owner": false,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "name": "Company B (Deleted)",
    "business_type": 2,
    "description": "...",
    "is_active": false,
    "employee_count": 0,
    "is_owner": false,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

**Not:** Soft-deleted company'ler de listelenir.

---

### 2. Company Seç (Admin Only)

**Endpoint:**
```
POST /api/v1/tenants/companies/{id}/select/
```

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
{
  "detail": "Successfully selected company.",
  "company": {
    "id": 1,
    "name": "Company A",
    "...": "..."
  },
  "is_impersonating": true
}
```

**Davranış:**
- Seçilen company session'a kaydedilir
- Sonraki tüm isteklerde `request.company` bu company olur
- `request.is_impersonating = True` olur

---

### 3. Company Seçimini Temizle (Admin Only)

**Endpoint:**
```
POST /api/v1/tenants/companies/clear_selection/
```

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
{
  "detail": "Company selection cleared.",
  "is_impersonating": false
}
```

**Davranış:**
- Session'dan company seçimi kaldırılır
- Admin normal tenant mantığına döner (kendi company'si varsa o kullanılır)

---

### 4. Tüm Employee'leri Listele (Admin Only)

**Endpoint:**
```
GET /api/v1/tenants/employees/list_all/
```

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "user": 10,
    "user_username": "john_doe",
    "user_email": "john@example.com",
    "company": 1,
    "company_name": "Company A",
    "role": "admin",
    "status": "active",
    "hire_date": "2024-01-01",
    "position": "Developer",
    "department": "IT"
  }
]
```

**Not:** Tüm company'lerdeki employee'ler listelenir, soft-deleted olanlar dahil.

---

### 5. Tüm Product'ları Listele (Admin Only)

**Endpoint:**
```
GET /api/v1/tenants/products/list_all/
```

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "company": 1,
    "company_name": "Company A",
    "name": "Product 1",
    "description": "...",
    "price": "99.99",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

**Not:** Tüm company'lerdeki product'lar listelenir.

---

## Kullanım Senaryoları

### Senaryo 1: Admin, Belirli Bir Company'yi İnceler

```bash
# 1. Tüm company'leri listele
curl -X GET http://localhost:8000/api/v1/tenants/companies/list_all/ \
  -H "Authorization: Bearer <admin_token>"

# 2. Company ID 5'i seç
curl -X POST http://localhost:8000/api/v1/tenants/companies/5/select/ \
  -H "Authorization: Bearer <admin_token>"

# 3. Artık normal endpoint'ler Company 5'e scopelanmış olarak çalışır
curl -X GET http://localhost:8000/api/v1/tenants/employees/ \
  -H "Authorization: Bearer <admin_token>"
# → Company 5'in employee'lerini döner

curl -X GET http://localhost:8000/api/v1/tenants/products/ \
  -H "Authorization: Bearer <admin_token>"
# → Company 5'in product'larını döner

# 4. Seçimi temizle
curl -X POST http://localhost:8000/api/v1/tenants/companies/clear_selection/ \
  -H "Authorization: Bearer <admin_token>"
```

---

### Senaryo 2: API İstemcisinden Header ile Company Belirtme

```bash
# X-Company-ID header ile direkt company belirt (session gerektirmez)
curl -X GET http://localhost:8000/api/v1/tenants/employees/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Company-ID: 3"
# → Company 3'ün employee'lerini döner

# Farklı bir istekte başka company
curl -X GET http://localhost:8000/api/v1/tenants/products/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Company-ID: 7"
# → Company 7'nin product'larını döner
```

**Not:** Header yöntemi session'dan önceliklidir.

---

### Senaryo 3: Tüm Verileri Görüntüle

```bash
# Tüm company'ler (soft-deleted dahil)
curl -X GET http://localhost:8000/api/v1/tenants/companies/list_all/ \
  -H "Authorization: Bearer <admin_token>"

# Tüm employee'ler (tüm company'lerden)
curl -X GET http://localhost:8000/api/v1/tenants/employees/list_all/ \
  -H "Authorization: Bearer <admin_token>"

# Tüm product'lar (tüm company'lerden)
curl -X GET http://localhost:8000/api/v1/tenants/products/list_all/ \
  -H "Authorization: Bearer <admin_token>"
```

---

## Güvenlik Notları

### ✅ Yapılanlar

1. **Permission Check**: Her endpoint `IsAdminUser` permission ile korunmuştur
2. **Settings Check**: `SUPERUSER_BYPASS_TENANT` kontrol edilir
3. **User Check**: `is_superuser` veya `is_staff` kontrol edilir
4. **Invalid ID Handling**: Geçersiz company ID'leri session'dan temizlenir

### ⚠️ Dikkat Edilmesi Gerekenler

1. **Production'da Ayar**: Eğer bu özellik kullanılmayacaksa, `.env` dosyasında `SUPERUSER_BYPASS_TENANT=False` yapın
2. **Admin Erişimi**: Staff/superuser rolünü sadece güvenilir kullanıcılara verin
3. **Audit Logging**: Admin kullanıcıların company değiştirmelerini loglayın (opsiyonel enhancement)
4. **Session Security**: Session ayarlarının güvenli olduğundan emin olun

---

## Django Admin Panel İçin Kullanım

Admin panel'de de bu özelliği kullanmak isterseniz, custom admin view'ları oluşturabilirsiniz:

```python
# apps/tenants/admin.py (örnek)
from django.contrib import admin
from django.shortcuts import redirect
from .models import Company

@admin.action(description='Select this company')
def select_company(modeladmin, request, queryset):
    if queryset.count() == 1:
        company = queryset.first()
        request.session['selected_company_id'] = company.id
        modeladmin.message_user(request, f'Selected company: {company.name}')
    return redirect('admin:tenants_company_changelist')

class CompanyAdmin(admin.ModelAdmin):
    actions = [select_company]
    list_display = ['name', 'owner', 'is_active', 'employee_count']
```

---

## Test

### Unit Test Örneği

```python
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from core.middleware import TenantMiddleware
from tenants.models import Company

User = get_user_model()

class TenantMiddlewareAdminTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='pass123'
        )
        self.company = Company.objects.create(
            owner=self.admin,
            name='Test Company'
        )
        self.middleware = TenantMiddleware(get_response=lambda r: r)

    def test_admin_can_select_company_via_session(self):
        request = self.factory.get('/')
        request.user = self.admin
        request.session = {'selected_company_id': self.company.id}

        self.middleware.process_request(request)

        self.assertEqual(request.company, self.company)
        self.assertTrue(request.is_impersonating)

    def test_admin_can_select_company_via_header(self):
        request = self.factory.get(
            '/',
            HTTP_X_COMPANY_ID=str(self.company.id)
        )
        request.user = self.admin
        request.session = {}

        self.middleware.process_request(request)

        self.assertEqual(request.company, self.company)
        self.assertTrue(request.is_impersonating)
```

---

## Özet

| Özellik | Normal User | Admin User (bypass enabled) |
|---------|-------------|----------------------------|
| Kendi company'sine erişim | ✅ | ✅ |
| Başka company'lere erişim | ❌ | ✅ (selection gerekli) |
| Soft-deleted company'lere erişim | ❌ | ✅ |
| Tüm verileri listeleme | ❌ | ✅ (`list_all` endpoint) |
| X-Company-ID header kullanımı | ❌ | ✅ |
| Session-based company selection | ❌ | ✅ |

---

## İlgili Dosyalar

- [apps/core/middleware.py](apps/core/middleware.py) - TenantMiddleware implementasyonu
- [apps/tenants/views.py](apps/tenants/views.py) - Admin endpoint'leri
- [config/settings.py](config/settings.py) - SUPERUSER_BYPASS_TENANT ayarı
- [apps/tenants/permissions.py](apps/tenants/permissions.py) - Permission class'ları

---

## Gelecek Geliştirmeler (Opsiyonel)

1. **Audit Logging**: Admin kullanıcıların company değiştirmelerini loglama
2. **Time-limited Access**: Seçilen company'nin belirli bir süre sonra otomatik temizlenmesi
3. **Company Group**: Admin kullanıcıların sadece belirli company gruplarına erişimi
4. **UI Component**: Frontend'de company seçici dropdown component
