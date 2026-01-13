from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet for models using SoftDeleteMixin.
    Provides methods for soft delete operations.
    """
    def delete(self):
        """Soft delete - marks records as deleted instead of removing them."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently delete records from database."""
        return super().delete()

    def alive(self):
        """Returns only non-deleted records."""
        return self.filter(is_deleted=False)

    def deleted(self):
        """Returns only deleted records."""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """
    Manager for models using SoftDeleteMixin.
    By default, only returns non-deleted records.

    Usage:
        class MyModel(SoftDeleteMixin, models.Model):
            objects = SoftDeleteManager()
            all_objects = models.Manager()  # Access all records including deleted
    """
    def get_queryset(self):
        """Default queryset - excludes deleted records."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        """Returns all records including deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Returns only deleted records."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)


class TenantAwareQuerySet(models.QuerySet):
    """
    QuerySet for tenant-aware models.
    Provides methods for filtering by company.
    """
    def for_company(self, company):
        """Filter records for a specific company."""
        if company:
            return self.filter(company=company)
        return self.none()


class TenantAwareManager(models.Manager):
    """
    Manager for tenant-aware models.
    Provides company-based filtering methods.

    Usage:
        class MyModel(TenantAwareMixin, models.Model):
            objects = TenantAwareManager()
    """
    def get_queryset(self):
        """Default queryset."""
        return TenantAwareQuerySet(self.model, using=self._db)

    def for_company(self, company):
        """Explicitly filter by company."""
        return self.get_queryset().for_company(company)


class SoftDeleteTenantAwareQuerySet(SoftDeleteQuerySet):
    """
    QuerySet combining soft delete and tenant awareness.
    Provides both soft delete and company filtering methods.
    """
    def for_company(self, company):
        """Filter non-deleted records for a specific company."""
        if company:
            return self.filter(company=company, is_deleted=False)
        return self.none()


class SoftDeleteTenantAwareManager(models.Manager):
    """
    Manager combining soft delete and tenant awareness.
    By default, only returns non-deleted records.

    Usage:
        class MyModel(TenantAwareMixin, SoftDeleteMixin, models.Model):
            objects = SoftDeleteTenantAwareManager()
            all_objects = models.Manager()
    """
    def get_queryset(self):
        """Default queryset - excludes deleted records."""
        return SoftDeleteTenantAwareQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def for_company(self, company):
        """Filter non-deleted records for a specific company."""
        return self.get_queryset().filter(company=company)

    def all_with_deleted(self):
        """Returns all records including deleted ones."""
        return SoftDeleteTenantAwareQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Returns only deleted records."""
        return SoftDeleteTenantAwareQuerySet(self.model, using=self._db).filter(is_deleted=True)