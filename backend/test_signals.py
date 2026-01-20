"""
Test script to verify Company creation auto-creates 5 default roles
and assigns default permissions.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from tenants.models import BusinessType, Company, Role, RolePermission, Permission

print("=" * 60)
print("Testing Company Creation with Auto-Role Setup")
print("=" * 60)

# Get or create a user
user, _ = User.objects.get_or_create(
    username='testowner',
    defaults={
        'email': 'testowner@example.com'
    }
)
if not user.password:
    user.set_password('testpass123')
    user.save()
print(f"\n[OK] User: {user.username}")

# Get or create BusinessType
business_type, _ = BusinessType.objects.get_or_create(
    name='Salon',
    defaults={'description': 'Beauty Salon'}
)
print(f"[OK] BusinessType: {business_type.name}")

# Create Company
print("\n[ACTION] Creating new company...")
company = Company.objects.create(
    owner=user,
    name='Test Beauty Salon',
    business_type=business_type,
    description='A test salon to verify role auto-creation'
)
print(f"[OK] Company created: {company.name}")

# Check if 5 roles were auto-created
print("\n" + "=" * 60)
print("Checking Auto-Created Roles")
print("=" * 60)

roles = Role.objects.filter(company=company).order_by('level')
print(f"\n[INFO] Total roles created: {roles.count()}")

if roles.count() == 5:
    print("[SUCCESS] 5 roles auto-created")
    for role in roles:
        print(f"  - {role.get_level_display()} (Level {role.level})")
else:
    print(f"[FAILED] Expected 5 roles, got {roles.count()}")

# Check RolePermissions
print("\n" + "=" * 60)
print("Checking Auto-Assigned Permissions")
print("=" * 60)

total_permissions = Permission.objects.filter(is_active=True).count()
print(f"\n[INFO] Total active permissions in system: {total_permissions}")

for role in roles:
    role_perms = RolePermission.objects.filter(
        company=company,
        role=role,
        is_granted=True
    )
    print(f"\n{role.get_level_display()} (Level {role.level}):")
    print(f"  Assigned permissions: {role_perms.count()}")

    # Show first 5 permissions as example
    if role_perms.exists():
        print("  Examples:")
        for rp in role_perms[:5]:
            print(f"    - {rp.permission.codename}")
        if role_perms.count() > 5:
            print(f"    ... and {role_perms.count() - 5} more")

# Verify permission hierarchy
print("\n" + "=" * 60)
print("Verifying Permission Hierarchy")
print("=" * 60)

basic_role = roles.filter(level=Role.RoleLevel.BASIC).first()
owner_role = roles.filter(level=Role.RoleLevel.OWNER).first()

basic_count = RolePermission.objects.filter(
    company=company,
    role=basic_role,
    is_granted=True
).count()

owner_count = RolePermission.objects.filter(
    company=company,
    role=owner_role,
    is_granted=True
).count()

print(f"\nBasic Role permissions: {basic_count}")
print(f"Owner Role permissions: {owner_count}")

if owner_count >= basic_count:
    print("[SUCCESS] Owner has equal or more permissions than Basic")
else:
    print("[FAILED] Permission hierarchy incorrect")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
