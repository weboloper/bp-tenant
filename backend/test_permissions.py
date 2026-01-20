"""
Test script to verify permission system works correctly.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from core.models import BusinessType
from tenants.models import Company, Employee, RoleLevel
from tenants.permissions_utils import check_permission, get_user_permissions
from datetime import date

print("=" * 60)
print("Testing Permission System")
print("=" * 60)

# Get or create business type
business_type, _ = BusinessType.objects.get_or_create(
    name='Salon',
    defaults={'description': 'Beauty Salon'}
)

# Create owner
owner, _ = User.objects.get_or_create(
    username='testowner',
    defaults={'email': 'testowner@example.com'}
)
if not owner.password:
    owner.set_password('testpass123')
    owner.save()

# Create company
company = Company.objects.create(
    owner=owner,
    name='Test Company',
    business_type=business_type
)
print(f"\n[OK] Company created: {company.name}")

# Create basic user
basic_user, _ = User.objects.get_or_create(
    username='basic_user',
    defaults={'email': 'basic@example.com'}
)
if not basic_user.password:
    basic_user.set_password('testpass123')
    basic_user.save()

# Create basic employee
basic_employee = Employee.objects.create(
    user=basic_user,
    company=company,
    role_level=RoleLevel.BASIC,
    hire_date=date.today()
)
print(f"[OK] Basic employee created: {basic_employee}")

# Create manager user
manager_user, _ = User.objects.get_or_create(
    username='manager_user',
    defaults={'email': 'manager@example.com'}
)
if not manager_user.password:
    manager_user.set_password('testpass123')
    manager_user.save()

# Create manager employee
manager_employee = Employee.objects.create(
    user=manager_user,
    company=company,
    role_level=RoleLevel.MEDIUM,
    hire_date=date.today()
)
print(f"[OK] Manager employee created: {manager_employee}")

print("\n" + "=" * 60)
print("Testing Permission Checks")
print("=" * 60)

# Test 1: Owner should have all permissions
print("\n[TEST 1] Owner permissions:")
test_perms = [
    'can_book_appointments',
    'can_view_all_calendars',
    'can_manage_staff',
    'can_manage_billing'
]

for perm in test_perms:
    result = check_permission(owner, perm, company)
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {perm}: {result}")

all_pass = all(check_permission(owner, p, company) for p in test_perms)
if all_pass:
    print("[SUCCESS] Owner has all permissions")
else:
    print("[FAILED] Owner missing some permissions")

# Test 2: Basic user should have limited permissions
print("\n[TEST 2] Basic user permissions:")
basic_should_have = ['can_book_appointments', 'can_view_own_calendar']
basic_should_not_have = ['can_view_all_calendars', 'can_manage_staff']

print("  Should have:")
for perm in basic_should_have:
    result = check_permission(basic_user, perm, company)
    status = "[OK]" if result else "[FAIL]"
    print(f"    {status} {perm}: {result}")

print("  Should NOT have:")
for perm in basic_should_not_have:
    result = check_permission(basic_user, perm, company)
    status = "[OK]" if not result else "[FAIL]"
    print(f"    {status} {perm}: {result}")

basic_pass = (
    all(check_permission(basic_user, p, company) for p in basic_should_have) and
    all(not check_permission(basic_user, p, company) for p in basic_should_not_have)
)

if basic_pass:
    print("[SUCCESS] Basic user has correct permissions")
else:
    print("[FAILED] Basic user permissions incorrect")

# Test 3: Manager should have more permissions
print("\n[TEST 3] Manager permissions:")
manager_should_have = [
    'can_book_appointments',
    'can_view_own_calendar',
    'can_view_all_calendars',  # Manager should have this
    'can_view_all_sales'
]
manager_should_not_have = ['can_manage_staff', 'can_manage_billing']  # Manager doesn't have these

print("  Should have:")
for perm in manager_should_have:
    result = check_permission(manager_user, perm, company)
    status = "[OK]" if result else "[FAIL]"
    print(f"    {status} {perm}: {result}")

print("  Should NOT have:")
for perm in manager_should_not_have:
    result = check_permission(manager_user, perm, company)
    status = "[OK]" if not result else "[FAIL]"
    print(f"    {status} {perm}: {result}")

manager_pass = (
    all(check_permission(manager_user, p, company) for p in manager_should_have) and
    all(not check_permission(manager_user, p, company) for p in manager_should_not_have)
)

if manager_pass:
    print("[SUCCESS] Manager has correct permissions")
else:
    print("[FAILED] Manager permissions incorrect")

# Test 4: get_user_permissions helper
print("\n[TEST 4] get_user_permissions helper:")
basic_perms = get_user_permissions(basic_user, company)
if basic_perms:
    print(f"  [OK] Basic user permissions object: {basic_perms}")
    print(f"    can_book_appointments: {basic_perms.can_book_appointments}")
    print(f"    can_view_all_calendars: {basic_perms.can_view_all_calendars}")
else:
    print("  [FAIL] Failed to get basic user permissions")

owner_perms = get_user_permissions(owner, company)
if owner_perms is None:
    print("  [OK] Owner permissions: None (owner has all permissions)")
else:
    print("  [FAIL] Owner should return None from get_user_permissions")

# Test 5: Superuser
print("\n[TEST 5] Superuser permissions:")
superuser = User.objects.create_superuser('superuser', 'super@example.com', 'password')

super_test_perms = ['can_book_appointments', 'can_view_all_calendars', 'can_manage_billing']
for perm in super_test_perms:
    result = check_permission(superuser, perm, company)
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {perm}: {result}")

super_pass = all(check_permission(superuser, p, company) for p in super_test_perms)
if super_pass:
    print("[SUCCESS] Superuser has all permissions")
else:
    print("[FAILED] Superuser missing some permissions")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)

# Summary
all_tests = [all_pass, basic_pass, manager_pass, super_pass]
passed = sum(all_tests)
total = len(all_tests)

print(f"\nTests passed: {passed}/{total}")

if passed == total:
    print("[SUCCESS] All permission tests passed!")
else:
    print(f"[FAILED] {total - passed} test(s) failed")
