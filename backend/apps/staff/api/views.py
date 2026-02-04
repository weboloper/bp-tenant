from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from staff.models import Employee
from core.mixins import PlanLimitMixin
from .serializers import (
    EmployeeSerializer,
    EmployeeListSerializer,
)
from .permissions import CanManageEmployees


class EmployeeViewSet(PlanLimitMixin, viewsets.ModelViewSet):
    """
    ViewSet for Employee management.

    Only company admins (owner or admin employees) can manage employees.
    Automatically scoped to user's company.
    """
    permission_classes = [IsAuthenticated, CanManageEmployees]
    limit_name = 'employees'
    count_queryset = Employee.objects.all()

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

        GET /api/v1/staff/employees/me/
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

        GET /api/v1/staff/employees/active/
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

        GET /api/v1/staff/employees/list_all/
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
