from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from core.models import BusinessType
from core.mixins import SoftDeleteMixin, TimestampMixin, TenantAwareMixin
from core.managers import SoftDeleteManager, TenantAwareManager


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


class Company(SoftDeleteMixin, TimestampMixin, models.Model):
    """
    Company (Tenant) model.
    Represents a company in the multi-tenant system.

    Each company has an owner and can have multiple related data
    through TenantAwareMixin in other models.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_companies',
        verbose_name=_("Owner"),
        help_text=_("The user who owns and manages this company")
    )
    name = models.CharField(max_length=255, verbose_name=_("Company Name"))
    business_type = models.ForeignKey(
        BusinessType,
        on_delete=models.PROTECT,
        verbose_name=_("Business Type"),
        related_name='companies',
        help_text=_("Business type cannot be deleted if companies are using it")
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Inactive companies cannot be accessed")
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    @property
    def active_employees(self):
        """Get all active employees (excluding soft-deleted)"""
        return self.employees.filter(
            status=Employee.Status.ACTIVE,
            is_deleted=False
        )

    @property
    def employee_count(self):
        """Count of active employees"""
        return self.active_employees.count()

    def has_employee(self, user):
        """Check if user is an employee of this company"""
        return self.employees.filter(
            user=user,
            is_deleted=False
        ).exists()

    def get_employee(self, user):
        """Get employee record for user, or None if not found"""
        try:
            return self.employees.get(user=user, is_deleted=False)
        except Employee.DoesNotExist:
            return None

    def is_owner(self, user):
        """Check if user is the owner of this company"""
        return self.owner == user

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ["name"]
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['is_active', 'is_deleted']),
        ]


class Employee(SoftDeleteMixin, TimestampMixin, models.Model):
    """
    Employee model.
    Represents a user working at a company (not the owner).

    Business Rules:
    - One user can only be an employee at ONE company (enforced by OneToOneField)
    - Company owner cannot also be an employee of the same company
    - Soft delete enabled to maintain employment history
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        ON_LEAVE = 'on_leave', _('On Leave')
        TERMINATED = 'terminated', _('Terminated')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employment',
        verbose_name=_("User"),
        help_text=_("The user account for this employee")
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name=_("Company"),
        help_text=_("The company this employee works for")
    )
    role_level = models.IntegerField(
        choices=RoleLevel.choices,
        default=RoleLevel.BASIC,
        validators=[
            MinValueValidator(RoleLevel.BASIC),
            MaxValueValidator(RoleLevel.HIGH)  # Max level is HIGH (4), not OWNER
        ],
        verbose_name=_("Role Level"),
        help_text=_("Employee role level (1-4). Owner is not an employee.")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_("Employment Status")
    )
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Salary"),
        help_text=_("Monthly salary (optional, sensitive data)")
    )
    hire_date = models.DateField(
        verbose_name=_("Hire Date"),
        help_text=_("Date when employee was hired")
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Position/Title"),
        help_text=_("Job title or position")
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Department")
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        """Override save to enforce business rules"""
        # Prevent owner from being an employee of their own company
        if self.company.owner == self.user:
            raise ValidationError(
                _("Company owner cannot be an employee. Owner has implicit admin access.")
            )
        super().save(*args, **kwargs)

    def is_admin(self):
        """Check if employee has admin/owner level role"""
        return self.role_level >= RoleLevel.HIGH  # HIGH or OWNER level

    def is_active_employee(self):
        """Check if employee is active and not soft-deleted"""
        return self.status == self.Status.ACTIVE and not self.is_deleted

    def has_permission(self, permission_field):
        """
        Check if employee has a specific permission.

        Args:
            permission_field: Permission field name (e.g., 'can_book_appointments')

        Returns:
            Boolean

        Usage:
            if employee.has_permission('can_book_appointments'):
                # Allow booking
        """
        # Owner has all permissions
        if self.company.is_owner(self.user):
            return True

        try:
            perms = CompanyRolePermission.objects.get(
                company=self.company,
                level=self.role_level
            )
            return getattr(perms, permission_field, False)
        except CompanyRolePermission.DoesNotExist:
            return False

    def get_permissions(self):
        """
        Get CompanyRolePermission object for this employee's role level.

        Returns:
            CompanyRolePermission instance or None

        Usage:
            perms = employee.get_permissions()
            if perms and perms.can_view_all_calendars:
                # Show all calendars
        """
        try:
            return CompanyRolePermission.objects.get(
                company=self.company,
                level=self.role_level
            )
        except CompanyRolePermission.DoesNotExist:
            return None

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.get_role_level_display()})"

    class Meta:
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        ordering = ['hire_date']
        indexes = [
            models.Index(fields=['company', 'status', 'is_deleted']),
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['role_level', 'status']),
        ]
        constraints = [
            # Enforce: One user can only be employee at ONE active company
            # OneToOneField already enforces this, but adding constraint for safety
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_deleted=False),
                name='unique_active_employee_per_user'
            )
        ]


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


class Product(TenantAwareMixin, TimestampMixin, models.Model):
    """
    Product model.
    Represents a product belonging to a specific company (tenant).

    Hard delete - no soft delete for products.
    """
    # company field comes from TenantAwareMixin
    # created_at, updated_at come from TimestampMixin

    name = models.CharField(max_length=255, verbose_name=_("Product Name"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    objects = TenantAwareManager()

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', '-created_at']),
        ]
