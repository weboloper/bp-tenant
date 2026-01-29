from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from billing.models import TenantSubscription, SubscriptionHistory


class SubscriptionLimitExceeded(Exception):
    """Raised when tenant exceeds subscription limits"""
    pass


class NoActiveSubscription(Exception):
    """Raised when tenant has no active subscription"""
    pass


class SubscriptionService:
    """Service for managing tenant subscriptions and limits"""

    @staticmethod
    def get_active_subscription(tenant):
        """
        Get active subscription for tenant

        Args:
            tenant: Company instance

        Returns:
            TenantSubscription instance

        Raises:
            NoActiveSubscription: If no active subscription exists
        """
        try:
            return TenantSubscription.objects.select_related('plan').get(
                tenant=tenant,
                status='active'
            )
        except TenantSubscription.DoesNotExist:
            raise NoActiveSubscription(
                _("No active subscription found for this company")
            )

    @staticmethod
    def check_subscription_limits(tenant):
        """
        Get subscription limits and current usage

        Args:
            tenant: Company instance

        Returns:
            dict: Subscription limits and usage
        """
        try:
            subscription = SubscriptionService.get_active_subscription(tenant)

            return {
                'is_active': True,
                'plan_name': subscription.plan.name,
                'expires_at': subscription.expires_at,
                'limits': {
                    'max_employees': subscription.plan.max_employees,
                },
                'usage': {
                    'current_employees': tenant.employee_count,
                    'current_locations': getattr(tenant, 'locations', None).count() if hasattr(tenant, 'locations') else 0,
                },
                'features': {
                    'inventory': subscription.plan.has_inventory,
                },
            }
        except NoActiveSubscription:
            return {
                'is_active': False,
                'error': 'No active subscription'
            }

    @staticmethod
    def can_add_employee(tenant):
        """
        Check if tenant can add more employees

        Args:
            tenant: Company instance

        Returns:
            bool: True if can add, False otherwise
        """
        try:
            subscription = SubscriptionService.get_active_subscription(tenant)
            max_allowed = subscription.plan.max_employees

            # 0 or None means unlimited
            if not max_allowed:
                return True

            current_count = tenant.employee_count
            return current_count < max_allowed

        except NoActiveSubscription:
            return False

    @staticmethod
    def can_add_location(tenant):
        """
        Check if tenant can add more locations

        Args:
            tenant: Company instance

        Returns:
            bool: True if can add, False otherwise
        """
        try:
            subscription = SubscriptionService.get_active_subscription(tenant)
            max_allowed = subscription.plan.max_locations

            # 0 means unlimited
            if max_allowed == 0:
                return True

            current_count = getattr(tenant, 'locations', None).count() if hasattr(tenant, 'locations') else 0
            return current_count < max_allowed

        except NoActiveSubscription:
            return False

    @staticmethod
    def check_feature_access(tenant, feature_name):
        """
        Check if tenant has access to specific feature

        Args:
            tenant: Company instance
            feature_name: str (e.g., 'sms_notifications', 'api_access')

        Returns:
            bool: True if feature is enabled
        """
        try:
            subscription = SubscriptionService.get_active_subscription(tenant)
            return subscription.plan.has_module(feature_name)
        except NoActiveSubscription:
            return False

    @staticmethod
    @transaction.atomic
    def change_plan(tenant, new_plan, changed_by=None, reason=""):
        """
        Change subscription plan and record history

        Args:
            tenant: Company instance
            new_plan: SubscriptionPlan instance
            changed_by: User who initiated the change
            reason: Reason for plan change

        Returns:
            TenantSubscription instance
        """
        subscription = SubscriptionService.get_active_subscription(tenant)
        old_plan = subscription.plan

        # Create history record
        SubscriptionHistory.objects.create(
            tenant=tenant,
            old_plan=old_plan,
            new_plan=new_plan,
            changed_by=changed_by,
            reason=reason
        )

        # Update subscription
        subscription.plan = new_plan
        subscription.original_price = new_plan.price
        subscription.discounted_price = new_plan.price
        subscription.save()

        return subscription

    @staticmethod
    @transaction.atomic
    def renew_subscription(tenant, extend_days=30):
        """
        Extend subscription expiration date

        Args:
            tenant: Company instance
            extend_days: Number of days to extend

        Returns:
            TenantSubscription instance
        """
        subscription = SubscriptionService.get_active_subscription(tenant)
        subscription.expires_at = subscription.expires_at + timedelta(days=extend_days)
        subscription.save()

        return subscription

    @staticmethod
    def is_subscription_expired(tenant):
        """
        Check if subscription is expired

        Args:
            tenant: Company instance

        Returns:
            bool: True if expired
        """
        try:
            subscription = TenantSubscription.objects.get(tenant=tenant)
            return subscription.expires_at < timezone.now()
        except TenantSubscription.DoesNotExist:
            return True

    @staticmethod
    @transaction.atomic
    def enforce_employee_limit(tenant):
        """
        Raise exception if adding employee would exceed limit

        Args:
            tenant: Company instance

        Raises:
            SubscriptionLimitExceeded: If limit would be exceeded
        """
        if not SubscriptionService.can_add_employee(tenant):
            subscription = SubscriptionService.get_active_subscription(tenant)
            raise SubscriptionLimitExceeded(
                _("Employee limit (%(limit)s) exceeded for plan '%(plan)s'. Please upgrade your plan.") % {
                    'limit': subscription.plan.max_employees,
                    'plan': subscription.plan.name
                }
            )

    @staticmethod
    @transaction.atomic
    def enforce_location_limit(tenant):
        """
        Raise exception if adding location would exceed limit

        Args:
            tenant: Company instance

        Raises:
            SubscriptionLimitExceeded: If limit would be exceeded
        """
        if not SubscriptionService.can_add_location(tenant):
            subscription = SubscriptionService.get_active_subscription(tenant)
            raise SubscriptionLimitExceeded(
                _("Location limit (%(limit)s) exceeded for plan '%(plan)s'. Please upgrade your plan.") % {
                    'limit': subscription.plan.max_locations,
                    'plan': subscription.plan.name
                }
            )
