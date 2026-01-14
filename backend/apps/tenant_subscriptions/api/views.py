from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _

from tenant_subscriptions.models import TenantSubscription, SubscriptionHistory
from tenant_subscriptions.services import SubscriptionService, NoActiveSubscription
from system_subscriptions.models import SubscriptionPlan
from tenants.api.permissions import IsCompanyMember
from .serializers import (
    TenantSubscriptionSerializer,
    SubscriptionPlanSerializer,
    SubscriptionHistorySerializer
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
