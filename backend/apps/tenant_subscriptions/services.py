from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from .models import TenantSubscription, SubscriptionHistory, SmsBalance, SmsTransaction


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
                    'max_employee': subscription.plan.max_employee,
                    'max_locations': subscription.plan.max_locations,
                    'max_appointments_per_month': subscription.plan.max_appointments_per_month,
                },
                'usage': {
                    'current_employees': tenant.employee_count,
                    'current_locations': getattr(tenant, 'locations', None).count() if hasattr(tenant, 'locations') else 0,
                },
                'features': subscription.plan.features,
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
            max_allowed = subscription.plan.max_employee

            # 0 means unlimited
            if max_allowed == 0:
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
            return subscription.plan.has_feature(feature_name)
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
                    'limit': subscription.plan.max_employee,
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


class InsufficientSmsCredit(Exception):
    """Raised when tenant doesn't have enough SMS credits"""
    pass


class SmsService:
    """Service for managing SMS credits"""

    @staticmethod
    @transaction.atomic
    def add_credits(tenant, amount, payment=None, package=None, user=None, description=""):
        """
        Add SMS credits to tenant balance

        Args:
            tenant: Company instance
            amount: Number of credits to add (positive integer)
            payment: Payment instance (optional)
            package: SMSPackage instance (optional)
            user: User who made the transaction (optional)
            description: Transaction description (optional)

        Returns:
            SmsBalance instance
        """
        balance, created = SmsBalance.objects.select_for_update().get_or_create(
            tenant=tenant,
            defaults={'balance': 0}
        )

        balance.balance += amount
        balance.save()

        SmsTransaction.objects.create(
            tenant=tenant,
            transaction_type='purchase',
            amount=amount,
            balance_after=balance.balance,
            payment=payment,
            sms_package=package,
            created_by=user,
            description=description or f"Purchased {amount} SMS credits"
        )

        return balance

    @staticmethod
    @transaction.atomic
    def deduct_credit(tenant, description="SMS sent", metadata=None, user=None):
        """
        Deduct 1 SMS credit from tenant balance

        Args:
            tenant: Company instance
            description: Transaction description
            metadata: Additional data (dict)
            user: User who made the transaction (optional)

        Returns:
            SmsBalance instance

        Raises:
            InsufficientSmsCredit: If balance is insufficient
        """
        try:
            balance = SmsBalance.objects.select_for_update().get(tenant=tenant)
        except SmsBalance.DoesNotExist:
            raise InsufficientSmsCredit(_("SMS balance not found"))

        if balance.balance < 1:
            raise InsufficientSmsCredit(
                _("Insufficient SMS credits. Current balance: %(balance)s") % {'balance': balance.balance}
            )

        balance.balance -= 1
        balance.save()

        SmsTransaction.objects.create(
            tenant=tenant,
            transaction_type='usage',
            amount=-1,
            balance_after=balance.balance,
            created_by=user,
            description=description,
            metadata=metadata or {}
        )

        return balance

    @staticmethod
    def get_balance(tenant):
        """
        Get current SMS balance for tenant

        Args:
            tenant: Company instance

        Returns:
            int: Current balance (0 if not exists)
        """
        try:
            balance = SmsBalance.objects.get(tenant=tenant)
            return balance.balance
        except SmsBalance.DoesNotExist:
            return 0

    @staticmethod
    def has_sufficient_balance(tenant, required=1):
        """
        Check if tenant has sufficient SMS credits

        Args:
            tenant: Company instance
            required: Number of credits required (default: 1)

        Returns:
            bool: True if balance >= required
        """
        current = SmsService.get_balance(tenant)
        return current >= required

    @staticmethod
    @transaction.atomic
    def deduct_credits_bulk(tenant, amount, description="SMS sent", metadata=None, user=None):
        """
        Deduct multiple SMS credits in a single transaction.

        More efficient than calling deduct_credit() in a loop.

        Args:
            tenant: Company instance
            amount: Number of credits to deduct (positive integer)
            description: Transaction description
            metadata: Additional data (dict)
            user: User who made the transaction (optional)

        Returns:
            SmsBalance instance

        Raises:
            InsufficientSmsCredit: If balance is insufficient
        """
        if amount <= 0:
            raise ValueError(_("Amount must be positive"))

        try:
            balance = SmsBalance.objects.select_for_update().get(tenant=tenant)
        except SmsBalance.DoesNotExist:
            raise InsufficientSmsCredit(_("SMS balance not found"))

        if balance.balance < amount:
            raise InsufficientSmsCredit(
                _("Insufficient SMS credits. Required: %(required)s, Current: %(balance)s") % {
                    'required': amount,
                    'balance': balance.balance
                }
            )

        balance.balance -= amount
        balance.save()

        SmsTransaction.objects.create(
            tenant=tenant,
            transaction_type='usage',
            amount=-amount,
            balance_after=balance.balance,
            created_by=user,
            description=description,
            metadata=metadata or {}
        )

        return balance

    @staticmethod
    @transaction.atomic
    def refund_credit(tenant, amount, reason="", user=None):
        """
        Refund SMS credits to tenant

        Args:
            tenant: Company instance
            amount: Number of credits to refund (positive integer)
            reason: Refund reason
            user: Admin user performing refund

        Returns:
            SmsBalance instance
        """
        balance, created = SmsBalance.objects.select_for_update().get_or_create(
            tenant=tenant,
            defaults={'balance': 0}
        )

        balance.balance += amount
        balance.save()

        SmsTransaction.objects.create(
            tenant=tenant,
            transaction_type='refund',
            amount=amount,
            balance_after=balance.balance,
            created_by=user,
            description=reason or f"Refunded {amount} SMS credits"
        )

        return balance
