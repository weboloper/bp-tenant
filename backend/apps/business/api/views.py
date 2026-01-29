from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.db.models import ProtectedError

from tenants.api.permissions import IsCompanyMember, IsCompanyAdmin
from billing.services.subscription import SubscriptionService, SubscriptionLimitExceeded

# Settings models
from business.models.settings import (
    BusinessSettings,

)

# Lookup models
from business.models.lookups import (

    PaymentMethod,

)

# Data models
from business.models.data import (
    Location,
    TaxRate,

)

from .serializers import (
    # Settings
    BusinessSettingsSerializer,

    # Lookups

    PaymentMethodSerializer,

    # Data
    LocationSerializer,
    LocationListSerializer,
    TaxRateSerializer,

)


# =============================================================================
# SETTINGS VIEWSETS (Singleton - GET/PATCH only)
# =============================================================================

class SingletonSettingsViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    Base viewset for singleton settings.

    GET  /settings/{type}/  - Retrieve settings
    PATCH /settings/{type}/ - Update settings

    No list, create, or delete actions.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]
    lookup_field = None  # Singleton - no lookup needed

    def get_object(self):
        """Get or create settings for current company"""
        return self.model_class.get_for_tenant(self.request.company)

    def retrieve(self, request, *args, **kwargs):
        """GET - Retrieve settings"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """PATCH - Update settings"""
        partial = kwargs.pop('partial', True)  # Always partial
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BusinessSettingsViewSet(SingletonSettingsViewSet):
    serializer_class = BusinessSettingsSerializer
    model_class = BusinessSettings



# =============================================================================
# LOOKUP VIEWSETS (System-protected + Custom)
# =============================================================================

class LookupViewSet(viewsets.ModelViewSet):
    """
    Base viewset for lookup tables with system protection.

    GET    /lookups/{type}/        - List all (system + custom)
    POST   /lookups/{type}/        - Create custom entry
    GET    /lookups/{type}/{id}/   - Retrieve entry
    PATCH  /lookups/{type}/{id}/   - Update (system: only order/is_active)
    DELETE /lookups/{type}/{id}/   - Delete (only custom entries)
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        if not self.request.company:
            return self.model_class.objects.none()
        return self.model_class.objects.filter(company=self.request.company)

    def perform_create(self, serializer):
        """Create custom entry (is_system=False)"""
        serializer.save(company=self.request.company, is_system=False)

    def perform_destroy(self, instance):
        """Only allow deleting custom entries"""
        if instance.is_system:
            raise PermissionDenied(_("System records cannot be deleted."))
        try:
            instance.delete()
        except ProtectedError:
            raise PermissionDenied(_("This record is in use and cannot be deleted."))


class PaymentMethodViewSet(LookupViewSet):
    serializer_class = PaymentMethodSerializer
    model_class = PaymentMethod



# =============================================================================
# DATA VIEWSETS (Full CRUD)
# =============================================================================

class TenantDataViewSet(viewsets.ModelViewSet):
    """Base viewset for tenant data models with full CRUD"""
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        if not self.request.company:
            return self.model_class.objects.none()
        return self.model_class.objects.filter(company=self.request.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.company)


class LocationViewSet(TenantDataViewSet):
    model_class = Location

    def get_serializer_class(self):
        if self.action == 'list':
            return LocationListSerializer
        return LocationSerializer

    def get_queryset(self):
        if not self.request.company:
            return Location.objects.none()
        return Location.objects.filter(
            company=self.request.company,
            is_deleted=False
        )

    def perform_create(self, serializer):
        """
        Create location with subscription limit check.

        Raises:
            PermissionDenied: If max_locations limit reached
        """
        try:
            SubscriptionService.enforce_location_limit(self.request.company)
        except SubscriptionLimitExceeded as e:
            raise PermissionDenied(detail=str(e))

        serializer.save(company=self.request.company)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active locations only"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = LocationListSerializer(queryset, many=True)
        return Response(serializer.data)


class TaxRateViewSet(TenantDataViewSet):
    serializer_class = TaxRateSerializer
    model_class = TaxRate

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this tax rate as default"""
        tax_rate = self.get_object()
        # Clear other defaults
        TaxRate.objects.filter(company=request.company, is_default=True).update(is_default=False)
        tax_rate.is_default = True
        tax_rate.save()
        serializer = self.get_serializer(tax_rate)
        return Response(serializer.data)
