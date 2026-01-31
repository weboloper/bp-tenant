from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from core.mixins import SoftDeleteMixin, TimestampMixin, TenantAwareMixin
from core.managers import SoftDeleteManager, TenantAwareManager
from system.models import BusinessType

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
        # Lazy import to avoid circular dependency
        from staff.models import Employee
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
        # Lazy import to avoid circular dependency
        from staff.models import Employee
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
