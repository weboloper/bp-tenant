from django.db import transaction
from django.utils.translation import gettext_lazy as _
from billing.models import SmsBalance, SmsTransaction


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
