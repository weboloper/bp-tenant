from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from tenants.models import Company, Employee, Product
from .serializers import (
    CompanySerializer,
    EmployeeSerializer,
    EmployeeListSerializer,
    ProductSerializer
)
from .permissions import (
    IsCompanyOwner,
    IsCompanyAdmin,
    IsCompanyMember,
    CanManageEmployees
)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company management.

    Users can only see/manage their own company.
    A user can only own one active company at a time.
    """
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """User can only see/manage their own company"""
        return Company.objects.filter(
            owner=self.request.user,
            is_deleted=False
        )

    def get_permissions(self):
        """
        Owner can update/delete their company.
        Any authenticated user can create (with validation).
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsCompanyOwner()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Set owner to current user when creating company"""
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current user's company.

        GET /api/v1/tenants/companies/current/
        """
        company = request.company
        if not company:
            return Response(
                {'detail': _('You do not have access to any company.')},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def list_all(self, request):
        """
        List all companies (admin only).
        Superusers/staff can see all companies including deleted ones.

        GET /api/v1/tenants/companies/list_all/
        """
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'detail': _('You do not have permission to perform this action.')},
                status=status.HTTP_403_FORBIDDEN
            )

        can_bypass = getattr(settings, 'SUPERUSER_BYPASS_TENANT', True)
        if not can_bypass:
            return Response(
                {'detail': _('Superuser bypass is disabled.')},
                status=status.HTTP_403_FORBIDDEN
            )

        # Show all companies including deleted ones
        queryset = Company.all_objects.all().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def select(self, request, pk=None):
        """
        Select a company to impersonate (admin only).
        Sets the company in session for admin users.

        POST /api/v1/tenants/companies/{id}/select/
        """
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'detail': _('You do not have permission to perform this action.')},
                status=status.HTTP_403_FORBIDDEN
            )

        can_bypass = getattr(settings, 'SUPERUSER_BYPASS_TENANT', True)
        if not can_bypass:
            return Response(
                {'detail': _('Superuser bypass is disabled.')},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Allow access to deleted companies for admin
            company = Company.all_objects.get(pk=pk)
            request.session['selected_company_id'] = company.id

            serializer = self.get_serializer(company)
            return Response({
                'detail': _('Successfully selected company.'),
                'company': serializer.data,
                'is_impersonating': True
            })
        except Company.DoesNotExist:
            return Response(
                {'detail': _('Company not found.')},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def clear_selection(self, request):
        """
        Clear selected company (admin only).
        Removes company selection from session.

        POST /api/v1/tenants/companies/clear_selection/
        """
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'detail': _('You do not have permission to perform this action.')},
                status=status.HTTP_403_FORBIDDEN
            )

        if 'selected_company_id' in request.session:
            del request.session['selected_company_id']

        return Response({
            'detail': _('Company selection cleared.'),
            'is_impersonating': False
        })


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Employee management.

    Only company admins (owner or admin employees) can manage employees.
    Automatically scoped to user's company.
    """
    permission_classes = [IsAuthenticated, CanManageEmployees]

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail/create"""
        if self.action == 'list':
            return EmployeeListSerializer
        return EmployeeSerializer

    def get_queryset(self):
        """Filter employees by user's company"""
        if not self.request.company:
            return Employee.objects.none()

        return Employee.objects.filter(
            company=self.request.company,
            is_deleted=False
        ).select_related('user', 'company')

    def perform_create(self, serializer):
        """Set company to current user's company"""
        serializer.save(company=self.request.company)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's employment record.

        GET /api/v1/tenants/employees/me/
        """
        try:
            if hasattr(request.user, 'employment'):
                employment = request.user.employment
                if not employment.is_deleted:
                    serializer = self.get_serializer(employment)
                    return Response(serializer.data)
        except Employee.DoesNotExist:
            pass

        return Response(
            {'detail': _('You are not an employee at any company.')},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active employees of user's company.

        GET /api/v1/tenants/employees/active/
        """
        if not request.company:
            return Response(
                {'detail': _('No company access.')},
                status=status.HTTP_404_NOT_FOUND
            )

        queryset = self.get_queryset().filter(status=Employee.Status.ACTIVE)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def list_all(self, request):
        """
        List all employees across all companies (admin only).

        GET /api/v1/tenants/employees/list_all/
        """
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'detail': _('You do not have permission to perform this action.')},
                status=status.HTTP_403_FORBIDDEN
            )

        can_bypass = getattr(settings, 'SUPERUSER_BYPASS_TENANT', True)
        if not can_bypass:
            return Response(
                {'detail': _('Superuser bypass is disabled.')},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = Employee.all_objects.all().select_related('user', 'company').order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product management.

    Automatically scoped to user's company.
    All company members (owner or employees) can view products.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        """Products are automatically filtered by company"""
        if not self.request.company:
            return Product.objects.none()

        return Product.objects.for_company(self.request.company)

    def perform_create(self, serializer):
        """Auto-set company from request"""
        serializer.save(company=self.request.company)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active products.

        GET /api/v1/tenants/products/active/
        """
        if not request.company:
            return Response(
                {'detail': _('No company access.')},
                status=status.HTTP_404_NOT_FOUND
            )

        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def list_all(self, request):
        """
        List all products across all companies (admin only).

        GET /api/v1/tenants/products/list_all/
        """
        if not (request.user.is_superuser or request.user.is_staff):
            return Response(
                {'detail': _('You do not have permission to perform this action.')},
                status=status.HTTP_403_FORBIDDEN
            )

        can_bypass = getattr(settings, 'SUPERUSER_BYPASS_TENANT', True)
        if not can_bypass:
            return Response(
                {'detail': _('Superuser bypass is disabled.')},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = Product.objects.all().select_related('company').order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
