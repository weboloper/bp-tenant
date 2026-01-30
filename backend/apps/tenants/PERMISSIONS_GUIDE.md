# Permission System Guide

## Overview

This boilerplate uses a **permission-based authorization system** with company-level granular permissions.

Instead of checking role levels (`if employee.role_level >= 3`), you check specific permissions (`if check_permission(user, 'can_view_all_calendars')`). This approach is:

- **Semantic**: Permission names are self-documenting
- **Flexible**: Change permission assignments in database without code changes
- **Company-Specific**: Each company can customize role permissions
- **IDE-Friendly**: Autocomplete for permission field names

## Architecture

### Models

- **CompanyRolePermission**: Wide table with 28 boolean permission fields
- **Role Levels**: 4 employee levels (BASIC=1, LOW=2, MEDIUM=3, HIGH=4)
- **Owner**: Identified via `company.owner` FK, has ALL permissions implicitly
- **Superuser**: Can access all tenants, has ALL permissions

### Permission Hierarchy

```
Owner (company.owner)
  ↓ Has ALL 28 permissions (no database row needed)

Level 4 (HIGH - Administrator)
  ↓ 24 permissions

Level 3 (MEDIUM - Manager)
  ↓ 20 permissions

Level 2 (LOW - Staff)
  ↓ 13 permissions

Level 1 (BASIC - Basic User)
  ↓ 6 permissions
```

## Available Permissions

### Bookings & Clients (6 permissions)
- `can_book_appointments` - Can create and manage appointments
- `can_view_own_calendar` - Can view own calendar/schedule
- `can_view_all_calendars` - Can view all team members' calendars
- `can_apply_discount` - Can apply discounts during booking
- `can_view_client_contact` - Can see client contact information
- `can_download_clients` - Can export client list

### Services (4 permissions)
- `can_view_services` - Can view service list
- `can_create_services` - Can create new services
- `can_edit_services` - Can modify existing services
- `can_delete_services` - Can remove services

### Sales (4 permissions)
- `can_checkout` - Can process sales/checkout
- `can_edit_prices` - Can modify service/product prices
- `can_void_invoices` - Can void/cancel invoices
- `can_view_all_sales` - Can view all sales (not just own)

### Staff (4 permissions)
- `can_view_schedules` - Can view staff schedules
- `can_manage_staff` - Can add/edit/remove staff members
- `can_manage_permissions` - Can modify role permissions
- `can_run_payroll` - Can access payroll functions

### Inventory (4 permissions)
- `can_view_inventory` - Can view inventory levels
- `can_create_products` - Can add new products
- `can_import_bulk` - Can bulk import products
- `can_bulk_operations` - Can perform bulk operations

### Data & Reports (3 permissions)
- `can_access_reports` - Can access basic reports
- `can_access_insights` - Can access advanced analytics
- `can_view_team_data` - Can view all team member data

### Setup (3 permissions)
- `can_edit_business_info` - Can modify company information
- `can_manage_locations` - Can add/edit locations
- `can_manage_billing` - Can manage subscription/billing

**Total: 28 permissions**

## Usage Patterns

### 1. Function-Based Views (Django)

#### Basic Permission Check
```python
from staff.permissions_utils import require_permission

@require_permission('can_view_all_calendars')
def appointments_list(request):
    # User is guaranteed to have permission here
    appointments = Appointment.objects.filter(company=request.company)
    return render(request, 'appointments.html', {'appointments': appointments})
```

#### Multiple Permissions Required
```python
from staff.permissions_utils import require_permissions

@require_permissions(['can_book_appointments', 'can_checkout'])
def booking_checkout(request):
    # User must have BOTH permissions
    # Process booking and checkout...
    return render(request, 'checkout.html', {'booking': booking})
```

#### Manual Check (Conditional Logic)
```python
from staff.permissions_utils import check_permission

def appointments_view(request):
    if check_permission(request.user, 'can_view_all_calendars'):
        # Show all team calendars
        appointments = Appointment.objects.filter(company=request.company)
    else:
        # Show only user's own calendar
        appointments = Appointment.objects.filter(
            employee=request.user.employment
        )
    return render(request, 'appointments.html', {'appointments': appointments})
```

### 2. DRF ViewSets

#### Using HasPermission Class
```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from staff.api.permissions import HasPermission

class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = 'can_book_appointments'

    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
```

#### Using PermissionRequiredMixin (Recommended for Multiple Actions)
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from staff.api.permissions import PermissionRequiredMixin

class AppointmentViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    # Map actions to permissions
    permission_map = {
        'list': 'can_view_own_calendar',
        'retrieve': 'can_view_own_calendar',
        'create': 'can_book_appointments',
        'update': 'can_book_appointments',
        'destroy': 'can_book_appointments',
        'all_calendars': 'can_view_all_calendars',  # Custom action
    }

    @action(detail=False, methods=['get'])
    def all_calendars(self, request):
        # Permission checked automatically by mixin
        appointments = Appointment.objects.filter(company=request.company)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
```

#### Manual Check in DRF Action
```python
from staff.permissions_utils import check_permission
from rest_framework.decorators import action

class AppointmentViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['get'])
    def my_action(self, request):
        if check_permission(request.user, 'can_view_all_calendars'):
            # Show all appointments
            queryset = self.get_queryset()
        else:
            # Show only user's appointments
            queryset = self.get_queryset().filter(
                employee=request.user.employment
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

### 3. Business Logic (Models/Services)

#### In Model Methods
```python
class Appointment(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    def can_user_edit(self, user):
        """Check if user can edit this appointment"""
        from staff.permissions_utils import check_permission

        # Owner can always edit
        if self.company.is_owner(user):
            return True

        # Check if user has permission to book appointments
        return check_permission(user, 'can_book_appointments', self.company)
```

#### In Service Classes
```python
class AppointmentService:
    def get_appointments_for_user(self, user, company):
        """Get appointments user can view"""
        from staff.permissions_utils import check_permission, get_user_employee

        if check_permission(user, 'can_view_all_calendars', company):
            # User can view all appointments
            return Appointment.objects.filter(company=company)
        else:
            # User can only view own appointments
            employee = get_user_employee(user, company)
            return Appointment.objects.filter(employee=employee)
```

## Helper Functions

### check_permission(user, permission_field, company=None)

Check if user has a specific permission.

**Returns:** Boolean

**Example:**
```python
if check_permission(request.user, 'can_view_all_calendars'):
    # User has permission
    pass
```

### get_user_permissions(user, company=None)

Get CompanyRolePermission object for user.

**Returns:** CompanyRolePermission instance or None

**Example:**
```python
perms = get_user_permissions(request.user)
if perms and perms.can_view_all_calendars:
    # User has permission
    pass
```

### get_user_company(user)

Get company for user (owner or employee).

**Returns:** Company instance or None

### get_user_employee(user, company=None)

Get Employee instance for user.

**Returns:** Employee instance or None

## Decorators

### @require_permission(permission_field)

Require user to have specific permission. Raises `PermissionDenied` (HTTP 403) if user lacks permission.

```python
@require_permission('can_view_all_calendars')
def my_view(request):
    # User is guaranteed to have permission
    pass
```

### @require_permissions(permission_fields)

Require user to have ALL specified permissions.

```python
@require_permissions(['can_book_appointments', 'can_checkout'])
def booking_checkout(request):
    # User has both permissions
    pass
```

### @require_company

Require user to have company access.

```python
@require_company
def my_view(request):
    company = request.company  # Guaranteed to exist
    pass
```

## Testing Permissions

```python
from django.test import TestCase
from tenants.models import Company
from staff.models import Employee, RoleLevel
from staff.permissions_utils import check_permission

class PermissionTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@test.com')
        self.company = Company.objects.create(
            owner=self.owner,
            name='Test Company',
            business_type=business_type
        )

        self.basic_user = User.objects.create_user('basic', 'basic@test.com')
        self.employee = Employee.objects.create(
            user=self.basic_user,
            company=self.company,
            role_level=RoleLevel.BASIC,
            hire_date=date.today()
        )

    def test_basic_user_cannot_view_all_calendars(self):
        """Basic user should not have can_view_all_calendars permission"""
        has_perm = check_permission(
            self.basic_user,
            'can_view_all_calendars',
            self.company
        )
        self.assertFalse(has_perm)

    def test_basic_user_can_book_appointments(self):
        """Basic user should have can_book_appointments permission"""
        has_perm = check_permission(
            self.basic_user,
            'can_book_appointments',
            self.company
        )
        self.assertTrue(has_perm)

    def test_owner_has_all_permissions(self):
        """Owner should have all permissions"""
        has_perm = check_permission(
            self.owner,
            'can_view_all_calendars',
            self.company
        )
        self.assertTrue(has_perm)

        has_perm = check_permission(
            self.owner,
            'can_manage_billing',
            self.company
        )
        self.assertTrue(has_perm)

    def test_superuser_has_all_permissions(self):
        """Superuser should have all permissions for any company"""
        superuser = User.objects.create_superuser(
            'admin', 'admin@test.com', 'password'
        )

        has_perm = check_permission(
            superuser,
            'can_view_all_calendars',
            self.company
        )
        self.assertTrue(has_perm)
```

## Default Permission Assignments

### Level 1 (BASIC - Basic User) - 6 permissions
- can_book_appointments
- can_view_own_calendar
- can_view_client_contact
- can_checkout
- can_view_services
- can_view_inventory

### Level 2 (LOW - Staff) - 13 permissions
Includes all BASIC permissions plus:
- can_apply_discount
- can_download_clients
- can_create_services
- can_edit_services
- can_create_products
- can_view_schedules
- can_access_reports

### Level 3 (MEDIUM - Manager) - 20 permissions
Includes all STAFF permissions plus:
- can_view_all_calendars
- can_delete_services
- can_edit_prices
- can_view_all_sales
- can_import_bulk
- can_bulk_operations
- can_access_insights

### Level 4 (HIGH - Administrator) - 24 permissions
Includes all MANAGER permissions plus:
- can_void_invoices
- can_manage_staff
- can_view_team_data
- can_edit_business_info

### Owner - ALL 28 permissions
Includes all ADMINISTRATOR permissions plus:
- can_manage_permissions
- can_run_payroll
- can_manage_locations
- can_manage_billing

## Customizing Permissions

Each company can customize which permissions each role level has by modifying the `CompanyRolePermission` rows.

Example: Give BASIC users the ability to view all calendars for a specific company:

```python
# In Django admin or via API
perm = CompanyRolePermission.objects.get(
    company=company,
    level=RoleLevel.BASIC
)
perm.can_view_all_calendars = True
perm.save()
```

Now all BASIC employees of that company can view all calendars!

## Best Practices

### ✅ DO

- Use permission-based checks (`can_view_all_calendars`) instead of level checks
- Check permissions as close to the action as possible
- Use decorators for function-based views
- Use `HasPermission` or `PermissionRequiredMixin` for DRF ViewSets
- Test permission logic thoroughly

### ❌ DON'T

- Don't check `role_level >= 3` - use permission fields instead
- Don't hardcode permission logic in multiple places
- Don't bypass permission checks for "convenience"
- Don't forget that Owner has ALL permissions implicitly
- Don't create Employee records for owners (validation prevents this)

## Troubleshooting

### User always gets 403 Forbidden

Check:
1. Is user authenticated? (`request.user.is_authenticated`)
2. Does user have company access? (`request.company is not None`)
3. Is user an employee or owner? (`company.is_owner(user)` or `user.employment`)
4. Does CompanyRolePermission row exist for company+level?
5. Is the permission field enabled in CompanyRolePermission?

### Owner cannot access something

- Owner should ALWAYS pass all permission checks
- Check `company.is_owner(user)` returns `True`
- Check permission logic isn't bypassing owner check

### Superuser cannot access something

- Superuser should ALWAYS pass all permission checks
- Check `user.is_superuser` returns `True`
- Check permission logic includes superuser check

## Related Files

- [apps/staff/permissions_utils.py](apps/staff/permissions_utils.py) - Helper functions and decorators
- [apps/staff/api/permissions.py](apps/staff/api/permissions.py) - DRF permission classes (HasPermission, PermissionRequiredMixin, etc.)
- [apps/tenants/api/permissions.py](apps/tenants/api/permissions.py) - IsCompanyOwner permission
- [apps/staff/models/permissions.py](apps/staff/models/permissions.py) - CompanyRolePermission model
- [apps/staff/signals.py](apps/staff/signals.py) - Auto-creates default permissions
- [apps/core/middleware.py](apps/core/middleware.py) - TenantMiddleware sets `request.company`
