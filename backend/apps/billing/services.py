"""
Billing services for subscription and SMS management.
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import Optional
from datetime import timedelta

from billing.models import (
    SmsBalance, SmsTransaction, Payment,
    TenantSubscription, SubscriptionPlan, SMSPackage
)


class SmsService:
    """Service for managing SMS credits and transactions"""

    @staticmethod
    def get_or_create_balance(tenant):
        """Get or create SMS balance for tenant"""
        balance, created = SmsBalance.objects.get_or_create(
            tenant=tenant,
            defaults={'balance': 0}
        )
        return balance

    @staticmethod
    @transaction.atomic
    def add_credits(tenant, amount: int, payment=None, package=None, user=None, description=''):
        """
        Add SMS credits to tenant balance.

        Args:
            tenant: Tenant company instance
            amount: Number of SMS credits to add
            payment: Related Payment instance (optional)
            package: Related SMSPackage instance (optional)
            user: User who performed this action (optional)
            description: Transaction description (optional)

        Returns:
            Updated balance amount
        """
        balance = SmsService.get_or_create_balance(tenant)
        return balance.add_credits(
            amount=amount,
            description=description,
            user=user,
            payment=payment,
            sms_package=package
        )

    @staticmethod
    @transaction.atomic
    def deduct_credits(tenant, amount: int, user=None, description=''):
        """
        Deduct SMS credits from tenant balance.

        Args:
            tenant: Tenant company instance
            amount: Number of SMS credits to deduct
            user: User who performed this action (optional)
            description: Transaction description (optional)

        Returns:
            Updated balance amount

        Raises:
            ValueError: If insufficient credits
        """
        balance = SmsService.get_or_create_balance(tenant)
        return balance.deduct_credits(
            amount=amount,
            description=description,
            user=user
        )

    @staticmethod
    def check_balance(tenant) -> int:
        """
        Check SMS balance for tenant.

        Returns:
            Current balance amount
        """
        balance = SmsService.get_or_create_balance(tenant)
        return balance.balance

    @staticmethod
    def has_sufficient_credits(tenant, required_amount: int) -> bool:
        """
        Check if tenant has sufficient SMS credits.

        Args:
            tenant: Tenant company instance
            required_amount: Required number of credits

        Returns:
            True if tenant has enough credits
        """
        current_balance = SmsService.check_balance(tenant)
        return current_balance >= required_amount


class SubscriptionService:
    """Service for managing tenant subscriptions"""

    @staticmethod
    @transaction.atomic
    def create_subscription(tenant, plan: SubscriptionPlan, duration_months: int = 1,
                          discounted_price: Optional[Decimal] = None, notes: str = ''):
        """
        Create a new subscription for tenant.

        Args:
            tenant: Tenant company instance
            plan: SubscriptionPlan instance
            duration_months: Subscription duration in months (default: 1)
            discounted_price: Optional discounted price (if None, uses plan price)
            notes: Additional notes (optional)

        Returns:
            TenantSubscription instance
        """
        # Calculate expiration date
        expires_at = timezone.now() + timedelta(days=30 * duration_months)

        # Create subscription
        subscription = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            status='pending',  # Will be activated when payment is completed
            expires_at=expires_at,
            original_price=plan.price,
            discounted_price=discounted_price or plan.price,
            notes=notes
        )

        # Give welcome bonus SMS if plan has it
        if plan.welcome_sms_bonus > 0:
            SmsService.add_credits(
                tenant=tenant,
                amount=plan.welcome_sms_bonus,
                description=f"Welcome bonus from {plan.name} plan"
            )

        return subscription

    @staticmethod
    @transaction.atomic
    def activate_subscription(subscription: TenantSubscription):
        """Activate a pending subscription"""
        subscription.status = 'active'
        subscription.save()

    @staticmethod
    def get_active_subscription(tenant) -> Optional[TenantSubscription]:
        """Get tenant's active subscription"""
        try:
            return TenantSubscription.objects.get(tenant=tenant, status='active')
        except TenantSubscription.DoesNotExist:
            return None

    @staticmethod
    def check_subscription_status(tenant) -> dict:
        """
        Check tenant subscription status and limits.

        Returns:
            Dict with subscription info and limits
        """
        subscription = SubscriptionService.get_active_subscription(tenant)

        if not subscription:
            return {
                'has_subscription': False,
                'plan': None,
                'status': None,
                'expires_at': None,
            }

        return {
            'has_subscription': True,
            'plan': subscription.plan,
            'status': subscription.status,
            'expires_at': subscription.expires_at,
            'max_employees': subscription.plan.max_employees,
            'max_products': subscription.plan.max_products,
        }


class PaymentService:
    """Service for managing payments"""

    @staticmethod
    @transaction.atomic
    def create_sms_payment(tenant, package: SMSPackage, payment_method: str = 'iyzico') -> Payment:
        """
        Create a payment for SMS package purchase.

        Args:
            tenant: Tenant company instance
            package: SMSPackage instance
            payment_method: Payment method (default: 'iyzico')

        Returns:
            Payment instance
        """
        payment = Payment.objects.create(
            tenant=tenant,
            payment_type='sms_package',
            payment_method=payment_method,
            amount=package.price,
            currency='TRY',
            status='pending',
            sms_package=package,
            gateway_name=payment_method
        )

        return payment

    @staticmethod
    @transaction.atomic
    def create_subscription_payment(tenant, subscription: TenantSubscription,
                                   payment_method: str = 'iyzico') -> Payment:
        """
        Create a payment for subscription.

        Args:
            tenant: Tenant company instance
            subscription: TenantSubscription instance
            payment_method: Payment method (default: 'iyzico')

        Returns:
            Payment instance
        """
        payment = Payment.objects.create(
            tenant=tenant,
            payment_type='subscription',
            payment_method=payment_method,
            amount=subscription.discounted_price,
            currency='TRY',
            status='pending',
            subscription=subscription,
            gateway_name=payment_method
        )

        return payment

    @staticmethod
    @transaction.atomic
    def complete_payment(payment: Payment, gateway_transaction_id: str = None,
                        gateway_data: dict = None):
        """
        Mark payment as completed and activate related services.

        Args:
            payment: Payment instance
            gateway_transaction_id: Transaction ID from payment gateway
            gateway_data: Additional data from payment gateway
        """
        payment.status = 'completed'
        if gateway_transaction_id:
            payment.gateway_transaction_id = gateway_transaction_id
        if gateway_data:
            payment.gateway_data = gateway_data
        payment.save()

        # Activate subscription
        if payment.payment_type == 'subscription' and payment.subscription:
            SubscriptionService.activate_subscription(payment.subscription)

        # Add SMS credits
        elif payment.payment_type == 'sms_package' and payment.sms_package:
            total_credits = payment.sms_package.get_total_credits()
            SmsService.add_credits(
                tenant=payment.tenant,
                amount=total_credits,
                payment=payment,
                package=payment.sms_package,
                description=f"Purchased {payment.sms_package.display_name}"
            )
