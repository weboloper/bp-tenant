from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _

from tenant_subscriptions.models import TenantSubscription, SubscriptionHistory, SmsBalance, SmsTransaction
from tenant_subscriptions.services import SubscriptionService, NoActiveSubscription, SmsService
from system_subscriptions.models import SubscriptionPlan, SMSPackage
from tenants.api.permissions import IsCompanyMember
from .serializers import (
    TenantSubscriptionSerializer,
    SubscriptionPlanSerializer,
    SubscriptionHistorySerializer,
    SmsBalanceSerializer,
    SmsTransactionSerializer,
    SMSPackageSerializer
)


class TenantSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for tenant subscriptions

    Provides read-only access to subscriptions with custom actions:
    - my_subscription: Get current active subscription with limits
    - available_plans: List available plans for upgrade
    - history: Get subscription change history
    """
    serializer_class = TenantSubscriptionSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        """Filter subscriptions by current user's company"""
        if getattr(self.request, 'company', None):
            return TenantSubscription.objects.filter(
                tenant=self.request.company
            ).select_related('plan', 'tenant')
        return TenantSubscription.objects.none()

    @action(detail=False, methods=['get'], url_path='my-subscription')
    def my_subscription(self, request):
        """
        Get current active subscription with limits and usage

        Returns:
            - Subscription details
            - Plan features
            - Usage limits and current usage
            - Feature access flags
        """
        tenant = getattr(request, 'company', None)

        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscription = SubscriptionService.get_active_subscription(tenant)
            limits_info = SubscriptionService.check_subscription_limits(tenant)

            serializer = self.get_serializer(subscription)

            return Response({
                'subscription': serializer.data,
                'limits': limits_info
            })

        except NoActiveSubscription as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='available-plans')
    def available_plans(self, request):
        """
        List all available subscription plans for upgrade/change

        Returns list of active subscription plans with features
        """
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        serializer = SubscriptionPlanSerializer(plans, many=True)

        return Response({
            'plans': serializer.data
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get subscription change history for current tenant

        Returns list of subscription changes with old/new plan details
        """
        tenant = getattr(request, 'company', None)

        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        history = SubscriptionHistory.objects.filter(
            tenant=tenant
        ).select_related(
            'old_plan', 'new_plan', 'changed_by'
        ).order_by('-changed_at')

        serializer = SubscriptionHistorySerializer(history, many=True)

        return Response({
            'history': serializer.data
        })


class SmsBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SMS balance and transactions (moved from tenant_resources)

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
