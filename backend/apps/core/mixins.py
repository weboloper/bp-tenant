from django.db import models
from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy as _


class TimestampMixin(models.Model):
    """
    Mixin to add timestamp fields to models.

    Provides created_at and updated_at fields that are automatically managed.
    This prevents repetition and maintains consistency across all models.

    Usage:
        class MyModel(TimestampMixin, models.Model):
            name = models.CharField(max_length=100)
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        abstract = True


class TenantAwareMixin(models.Model):
    """
    Mixin for models that belong to a specific tenant (company).

    Automatically adds a company foreign key with dynamic related_name
    to maintain proper relationships across different apps.

    Usage:
        class MyModel(TenantAwareMixin, models.Model):
            name = models.CharField(max_length=100)
            objects = TenantAwareManager()
    """
    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        verbose_name=_("Company"),
        help_text=_("The company this record belongs to")
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['company'])
        ]


class SoftDeleteMixin(models.Model):
    """
    Mixin to add soft delete functionality to models.

    Records are marked as deleted instead of being removed from database.
    This prevents data loss and maintains referential integrity.

    Usage:
        class MyModel(SoftDeleteMixin, models.Model):
            name = models.CharField(max_length=100)

            objects = SoftDeleteManager()
            all_objects = models.Manager()
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Deleted")
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted At")
    )
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_deleted_set',
        verbose_name=_("Deleted By")
    )

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, user=None):
        """
        Soft delete - mark as deleted instead of removing from database.

        Args:
            using: Database alias
            keep_parents: Keep parent models (Django standard)
            user: User who is deleting this record (optional)
        """
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def hard_delete(self, using=None, keep_parents=False):
        """
        Permanently delete from database.

        WARNING: This cannot be undone!
        """
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """
        Restore a soft-deleted record.

        Clears is_deleted, deleted_at, and deleted_by fields.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class SystemProtectedMixin(models.Model):
    """
    Mixin for lookup tables that can have system-protected entries.

    - is_system=True: Copied from platform defaults, cannot be deleted/edited
    - is_system=False: Created by tenant

    Usage:
        class PaymentMethod(TenantAwareMixin, SystemProtectedMixin, models.Model):
            name = models.CharField(max_length=100)
    """
    is_system = models.BooleanField(
        _("Is System"),
        default=False,
        editable=False,
        help_text=_("System records cannot be edited or deleted by tenant")
    )
    source_code = models.SlugField(
        _("Source Code"),
        max_length=50,
        blank=True,
        help_text=_("Reference to platform default (for system records)")
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # System records: only allow order change
        if self.pk and self.is_system:
            # Get original from DB
            original = self.__class__.objects.get(pk=self.pk)
            # Restore protected fields
            for field in self._get_protected_fields():
                setattr(self, field, getattr(original, field))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ProtectedError(
                _("System records cannot be deleted"),
                self
            )
        super().delete(*args, **kwargs)

    def _get_protected_fields(self):
        """Override in subclass to specify protected fields"""
        return ['name', 'is_system', 'source_code']


# =============================================================================
# VIEW MIXINS
# =============================================================================

class PlanFeatureRequiredMixin:
    """
    Mixin to check if the company's subscription plan has access to a module.

    Add this mixin to any view that requires a specific plan feature/module.
    The view will return 403 Forbidden if the company's plan doesn't include
    the required module.

    Usage:
        class ServiceListView(PlanFeatureRequiredMixin, ListAPIView):
            required_module = 'services'
            # ...

        class ProductDetailView(PlanFeatureRequiredMixin, RetrieveAPIView):
            required_module = 'products'
            # ...

    Available modules:
        - 'services': Service definition and management
        - 'products': Product management with stock tracking
        - 'pos': Point of sale
        - 'marketing': Campaigns and promotions
        - 'reports': Basic reports
        - 'advanced_reports': Detailed analytics
        - 'advanced_clients': Client segmentation, loyalty, referrals
        - 'advanced_permissions': Custom roles, detailed permissions
        - 'online_booking': Online appointment booking
        - 'multi_location': Multiple business locations
        - 'sms': SMS notifications
        - 'email': Email notifications
        - 'whatsapp': WhatsApp integration
        - 'google_calendar': Google Calendar sync
        - 'reserve_with_google': Reserve with Google
    """
    required_module = None  # Override in view

    def dispatch(self, request, *args, **kwargs):
        if self.required_module and hasattr(request, 'user') and request.user.is_authenticated:
            # Get company from user or request
            company = getattr(request.user, 'company', None)
            if not company:
                company = getattr(request, 'company', None)

            if company:
                # Check if company has active subscription with the required module
                subscription = getattr(company, 'subscription', None)
                if subscription and subscription.plan:
                    if not subscription.plan.has_module(self.required_module):
                        from rest_framework.response import Response
                        from rest_framework import status
                        return Response(
                            {
                                'detail': _(
                                    "Your plan doesn't include the %(module)s module. "
                                    "Please upgrade your subscription."
                                ) % {'module': self.required_module},
                                'code': 'plan_feature_required',
                                'required_module': self.required_module
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )

        return super().dispatch(request, *args, **kwargs)


class PlanLimitMixin:
    """
    Mixin to check plan limits before creating new resources.

    Add this mixin to CreateAPIView or similar views to enforce plan limits.

    Usage:
        class EmployeeCreateView(PlanLimitMixin, CreateAPIView):
            limit_name = 'employees'
            count_queryset = Employee.objects.all()  # or override get_current_count()
            # ...

    Available limits:
        - 'employees': Maximum team members
        - 'locations': Maximum business locations
        - 'appointments' or 'appointments_per_month': Monthly appointments
        - 'products': Maximum products
        - 'services': Maximum services
    """
    limit_name = None  # Override in view
    count_queryset = None  # Optional: QuerySet to count existing items

    def get_current_count(self, company):
        """
        Get current count of resources for the company.
        Override this method for custom counting logic.
        """
        if self.count_queryset is not None:
            return self.count_queryset.filter(company=company).count()
        return 0

    def check_plan_limit(self, request):
        """Check if the company can create more of this resource."""
        company = getattr(request.user, 'company', None)
        if not company:
            company = getattr(request, 'company', None)

        if not company or not self.limit_name:
            return True, None

        subscription = getattr(company, 'subscription', None)
        if not subscription or not subscription.plan:
            return True, None

        plan = subscription.plan
        current_count = self.get_current_count(company)

        if not plan.check_limit(self.limit_name, current_count):
            limit_value = plan.get_limit(self.limit_name)
            return False, {
                'detail': _(
                    "You have reached your plan limit for %(resource)s. "
                    "Your plan allows %(limit)s %(resource)s. Please upgrade your subscription."
                ) % {'resource': self.limit_name, 'limit': limit_value},
                'code': 'plan_limit_exceeded',
                'limit_name': self.limit_name,
                'limit_value': limit_value,
                'current_count': current_count
            }

        return True, None

    def create(self, request, *args, **kwargs):
        allowed, error_response = self.check_plan_limit(request)
        if not allowed:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(error_response, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)
