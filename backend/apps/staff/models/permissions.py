from django.db import models
from django.utils.translation import gettext_lazy as _
from core.mixins import SoftDeleteMixin, TimestampMixin, TenantAwareMixin
from core.managers import SoftDeleteManager, TenantAwareManager

# Create your models here.

class RoleLevel(models.IntegerChoices):
    """
    Global role level choices for Employees.
    Used by Employee and CompanyRolePermission models.

    Note: Owner is NOT an employee level - owners are identified via company.owner FK.
    """
    BASIC = 1, _('Basic User')
    LOW = 2, _('Staff')
    MEDIUM = 3, _('Manager')
    HIGH = 4, _('Administrator')



class CompanyRolePermission(TenantAwareMixin, models.Model):
    """
    Company-specific permission settings for each role level.
    Wide table approach with boolean fields for each permission.
    One row per company per level (5 rows per company).

    Allows hard-coded field access in views for IDE autocomplete support.
    """
    level = models.IntegerField(
        choices=RoleLevel.choices,
        verbose_name=_("Role Level")
    )

    # === Bookings & Clients ===
    can_book_appointments = models.BooleanField(
        default=False,
        verbose_name=_("Can Book Appointments")
    )
    can_view_own_calendar = models.BooleanField(
        default=False,
        verbose_name=_("Can View Own Calendar")
    )
    can_view_all_calendars = models.BooleanField(
        default=False,
        verbose_name=_("Can View All Calendars")
    )
    can_apply_discount = models.BooleanField(
        default=False,
        verbose_name=_("Can Apply Discount")
    )
    can_view_client_contact = models.BooleanField(
        default=False,
        verbose_name=_("Can View Client Contact Info")
    )
    can_download_clients = models.BooleanField(
        default=False,
        verbose_name=_("Can Download Client List")
    )

    # === Services ===
    can_view_services = models.BooleanField(
        default=False,
        verbose_name=_("Can View Services")
    )
    can_create_services = models.BooleanField(
        default=False,
        verbose_name=_("Can Create Services")
    )
    can_edit_services = models.BooleanField(
        default=False,
        verbose_name=_("Can Edit Services")
    )
    can_delete_services = models.BooleanField(
        default=False,
        verbose_name=_("Can Delete Services")
    )

    # === Sales ===
    can_checkout = models.BooleanField(
        default=False,
        verbose_name=_("Can Checkout")
    )
    can_edit_prices = models.BooleanField(
        default=False,
        verbose_name=_("Can Edit Prices")
    )
    can_void_invoices = models.BooleanField(
        default=False,
        verbose_name=_("Can Void Invoices")
    )
    can_view_all_sales = models.BooleanField(
        default=False,
        verbose_name=_("Can View All Sales")
    )

    # === Staff ===
    can_view_schedules = models.BooleanField(
        default=False,
        verbose_name=_("Can View Staff Schedules")
    )
    can_manage_staff = models.BooleanField(
        default=False,
        verbose_name=_("Can Manage Staff")
    )
    can_manage_permissions = models.BooleanField(
        default=False,
        verbose_name=_("Can Manage Permissions")
    )
    can_run_payroll = models.BooleanField(
        default=False,
        verbose_name=_("Can Run Payroll")
    )

    # === Inventory ===
    can_view_inventory = models.BooleanField(
        default=False,
        verbose_name=_("Can View Inventory")
    )
    can_create_products = models.BooleanField(
        default=False,
        verbose_name=_("Can Create Products")
    )
    can_import_bulk = models.BooleanField(
        default=False,
        verbose_name=_("Can Bulk Import")
    )
    can_bulk_operations = models.BooleanField(
        default=False,
        verbose_name=_("Can Perform Bulk Operations")
    )

    # === Data & Reports ===
    can_access_reports = models.BooleanField(
        default=False,
        verbose_name=_("Can Access Reports")
    )
    can_access_insights = models.BooleanField(
        default=False,
        verbose_name=_("Can Access Advanced Insights")
    )
    can_view_team_data = models.BooleanField(
        default=False,
        verbose_name=_("Can View All Team Data")
    )

    # === Setup ===
    can_edit_business_info = models.BooleanField(
        default=False,
        verbose_name=_("Can Edit Business Info")
    )
    can_manage_locations = models.BooleanField(
        default=False,
        verbose_name=_("Can Manage Locations")
    )
    can_manage_billing = models.BooleanField(
        default=False,
        verbose_name=_("Can Manage Billing")
    )

    objects = TenantAwareManager()

    def __str__(self):
        return f"{self.company.name} - Level {self.level}"

    class Meta:
        verbose_name = _("Company Role Permission")
        verbose_name_plural = _("Company Role Permissions")
        ordering = ['company', 'level']
        indexes = [
            models.Index(fields=['company', 'level']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'level'],
                name='unique_company_level_permission'
            )
        ]