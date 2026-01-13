"""
Signal handlers for automatic setup of permissions.

When a new Company is created, this module automatically:
- Creates 4 CompanyRolePermission rows with default permissions per level
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company, CompanyRolePermission, RoleLevel


@receiver(post_save, sender=Company)
def create_default_permissions(sender, instance, created, **kwargs):
    """
    Create 4 CompanyRolePermission rows when company is created (for employees only).

    For each of 4 employee levels, creates CompanyRolePermission with default boolean values.
    Owner permissions are not stored - owner has all permissions by default.

    Permission hierarchy (cumulative):
    - Level 1 (BASIC): 6 basic permissions
    - Level 2 (LOW): 13 permissions
    - Level 3 (MEDIUM): 20 permissions
    - Level 4 (HIGH): 24 permissions

    Note: Owner (company.owner) has all 28 permissions without needing a CompanyRolePermission row.
    """
    if not created:
        return

    # Create CompanyRolePermission rows with default values per level
    permissions_to_create = []

    # Level 1 (BASIC) - 6 permissions
    permissions_to_create.append(
        CompanyRolePermission(
            company=instance,
            level=RoleLevel.BASIC,
            # Bookings & Clients
            can_book_appointments=True,
            can_view_own_calendar=True,
            can_view_client_contact=True,
            # Sales
            can_checkout=True,
            # Services
            can_view_services=True,
            # Inventory
            can_view_inventory=True,
        )
    )

    # Level 2 (LOW/Staff) - 13 permissions (includes all from Level 1)
    permissions_to_create.append(
        CompanyRolePermission(
            company=instance,
            level=RoleLevel.LOW,
            # All from Level 1
            can_book_appointments=True,
            can_view_own_calendar=True,
            can_view_client_contact=True,
            can_checkout=True,
            can_view_services=True,
            can_view_inventory=True,
            # Additional for Staff
            can_apply_discount=True,
            can_download_clients=True,
            can_create_services=True,
            can_edit_services=True,
            can_create_products=True,
            can_view_schedules=True,
            can_access_reports=True,
        )
    )

    # Level 3 (MEDIUM/Manager) - 20 permissions
    permissions_to_create.append(
        CompanyRolePermission(
            company=instance,
            level=RoleLevel.MEDIUM,
            # All from Level 2
            can_book_appointments=True,
            can_view_own_calendar=True,
            can_view_client_contact=True,
            can_checkout=True,
            can_view_services=True,
            can_view_inventory=True,
            can_apply_discount=True,
            can_download_clients=True,
            can_create_services=True,
            can_edit_services=True,
            can_create_products=True,
            can_view_schedules=True,
            can_access_reports=True,
            # Additional for Manager
            can_view_all_calendars=True,
            can_delete_services=True,
            can_edit_prices=True,
            can_view_all_sales=True,
            can_import_bulk=True,
            can_bulk_operations=True,
            can_access_insights=True,
        )
    )

    # Level 4 (HIGH/Administrator) - 24 permissions
    permissions_to_create.append(
        CompanyRolePermission(
            company=instance,
            level=RoleLevel.HIGH,
            # All from Level 3
            can_book_appointments=True,
            can_view_own_calendar=True,
            can_view_client_contact=True,
            can_checkout=True,
            can_view_services=True,
            can_view_inventory=True,
            can_apply_discount=True,
            can_download_clients=True,
            can_create_services=True,
            can_edit_services=True,
            can_create_products=True,
            can_view_schedules=True,
            can_access_reports=True,
            can_view_all_calendars=True,
            can_delete_services=True,
            can_edit_prices=True,
            can_view_all_sales=True,
            can_import_bulk=True,
            can_bulk_operations=True,
            can_access_insights=True,
            # Additional for Administrator
            can_void_invoices=True,
            can_manage_staff=True,
            can_view_team_data=True,
            can_edit_business_info=True,
        )
    )

    # Note: No OWNER level - owner permissions are handled via company.owner check

    # Bulk create all 4 CompanyRolePermission rows (employee levels only)
    CompanyRolePermission.objects.bulk_create(permissions_to_create)
