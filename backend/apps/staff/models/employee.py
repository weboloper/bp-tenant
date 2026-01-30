from django.db import models
from core.mixins import SoftDeleteMixin, TimestampMixin, TenantAwareMixin
from core.managers import SoftDeleteManager, TenantAwareManager
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from tenants.models import Company
from .permissions import RoleLevel, CompanyRolePermission

# Create your models here.

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