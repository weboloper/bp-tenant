from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _

from tenant_resources.models import SmsBalance, SmsTransaction
from tenant_resources.services import SmsService
from system_subscriptions.models import SMSPackage
from tenants.api.permissions import IsCompanyMember
from .serializers import (
    SmsBalanceSerializer,
    SmsTransactionSerializer,
    SMSPackageSerializer
)


class SmsBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SMS balance and transactions

    Provides read-only access to SMS resources with custom actions:
    - my_balance: Get current SMS balance
    - transactions: Get transaction history
    - available_packages: List available SMS packages for purchase
    """
    serializer_class = SmsBalanceSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        """Filter SMS balance by current user's company"""
        if getattr(self.request, 'company', None):
            return SmsBalance.objects.filter(
                tenant=self.request.company
            ).select_related('tenant')
        return SmsBalance.objects.none()

    @action(detail=False, methods=['get'], url_path='my-balance')
    def my_balance(self, request):
        """
        Get current SMS balance for user's company

        Returns:
            - Current balance
            - Tenant information
            - Last update timestamp
        """
        tenant = getattr(request, 'company', None)

        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create balance
        balance, created = SmsBalance.objects.get_or_create(
            tenant=tenant,
            defaults={'balance': 0}
        )

        serializer = self.get_serializer(balance)

        return Response({
            'balance': serializer.data,
            'has_sufficient_balance': SmsService.has_sufficient_balance(tenant, required=1)
        })

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """
        Get SMS transaction history for current tenant

        Query params:
            - limit: Number of transactions to return (default: 50, max: 200)

        Returns list of SMS transactions ordered by newest first
        """
        tenant = getattr(request, 'company', None)

        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = SmsTransaction.objects.filter(
            tenant=tenant
        ).select_related(
            'payment', 'sms_package', 'created_by'
        ).order_by('-created_at')

        # Use standard DRF pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SmsTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SmsTransactionSerializer(queryset[:50], many=True)
        return Response({
            'transactions': serializer.data,
            'count': queryset.count()
        })

    @action(detail=False, methods=['get'], url_path='available-packages')
    def available_packages(self, request):
        """
        List all available SMS packages for purchase

        Returns list of active SMS packages ordered by featured status and sort order
        """
        packages = SMSPackage.objects.filter(
            is_active=True
        ).order_by('-is_featured', 'sort_order', 'price')

        serializer = SMSPackageSerializer(packages, many=True)

        return Response({
            'packages': serializer.data
        })
