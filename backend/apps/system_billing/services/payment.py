from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from system_billing.models import Payment, Invoice
from tenant_subscriptions.services import SubscriptionService
from tenant_resources.services import SmsService
from system_subscriptions.models import SubscriptionPlan, SMSPackage


class PaymentProcessingError(Exception):
    """Raised when payment processing fails"""
    pass


class PaymentService:
    """
    Service for processing payments

    Handles:
    - Subscription plan payments
    - SMS package purchases
    - Invoice generation
    - Payment status tracking
    """

    @staticmethod
    @transaction.atomic
    def process_subscription_payment(
        tenant,
        plan,
        payment_method,
        amount,
        user=None,
        transaction_id=None,
        metadata=None
    ):
        """
        Process subscription plan payment and upgrade tenant

        Args:
            tenant: Company instance
            plan: SubscriptionPlan instance to upgrade to
            payment_method: Payment method used (e.g., 'credit_card', 'bank_transfer')
            amount: Payment amount (Decimal)
            user: User making the payment (optional)
            transaction_id: External payment gateway transaction ID (optional)
            metadata: Additional payment metadata (dict, optional)

        Returns:
            tuple: (Payment instance, TenantSubscription instance)

        Raises:
            PaymentProcessingError: If payment processing fails
        """
        try:
            # Validate plan
            if not isinstance(plan, SubscriptionPlan) or not plan.is_active:
                raise PaymentProcessingError(_("Invalid or inactive subscription plan"))

            # Create payment record
            payment = Payment.objects.create(
                tenant=tenant,
                amount=amount,
                payment_method=payment_method,
                payment_type='subscription',
                status='completed',
                transaction_id=transaction_id or f"SUB-{timezone.now().timestamp()}",
                metadata=metadata or {},
                paid_by=user
            )

            # Create invoice
            invoice = Invoice.objects.create(
                payment=payment,
                tenant=tenant,
                invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{payment.id}",
                invoice_type='subscription',
                subtotal=amount,
                tax_amount=Decimal('0.00'),
                total_amount=amount,
                status='paid',
                issued_at=timezone.now(),
                paid_at=timezone.now()
            )

            # Upgrade subscription
            subscription = SubscriptionService.change_plan(
                tenant=tenant,
                new_plan=plan,
                changed_by=user,
                reason=f"Subscription payment processed (Invoice: {invoice.invoice_number})"
            )

            # Extend subscription based on billing cycle
            if plan.billing_cycle == 'monthly':
                extend_days = 30
            elif plan.billing_cycle == 'yearly':
                extend_days = 365
            elif plan.billing_cycle == 'quarterly':
                extend_days = 90
            else:
                extend_days = 30  # Default to monthly

            subscription = SubscriptionService.renew_subscription(
                tenant=tenant,
                extend_days=extend_days
            )

            return payment, subscription

        except Exception as e:
            raise PaymentProcessingError(
                _("Failed to process subscription payment: %(error)s") % {'error': str(e)}
            )

    @staticmethod
    @transaction.atomic
    def process_sms_payment(
        tenant,
        package,
        payment_method,
        amount,
        user=None,
        transaction_id=None,
        metadata=None
    ):
        """
        Process SMS package purchase and add credits to tenant

        Args:
            tenant: Company instance
            package: SMSPackage instance to purchase
            payment_method: Payment method used
            amount: Payment amount (Decimal)
            user: User making the payment (optional)
            transaction_id: External payment gateway transaction ID (optional)
            metadata: Additional payment metadata (dict, optional)

        Returns:
            tuple: (Payment instance, SmsBalance instance)

        Raises:
            PaymentProcessingError: If payment processing fails
        """
        try:
            # Validate package
            if not isinstance(package, SMSPackage) or not package.is_active:
                raise PaymentProcessingError(_("Invalid or inactive SMS package"))

            # Create payment record
            payment = Payment.objects.create(
                tenant=tenant,
                amount=amount,
                payment_method=payment_method,
                payment_type='sms_package',
                status='completed',
                transaction_id=transaction_id or f"SMS-{timezone.now().timestamp()}",
                metadata=metadata or {},
                paid_by=user
            )

            # Create invoice
            invoice = Invoice.objects.create(
                payment=payment,
                tenant=tenant,
                invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{payment.id}",
                invoice_type='sms_package',
                subtotal=amount,
                tax_amount=Decimal('0.00'),
                total_amount=amount,
                status='paid',
                issued_at=timezone.now(),
                paid_at=timezone.now()
            )

            # Calculate total credits (base + bonus)
            total_credits = package.sms_credits + package.bonus_sms

            # Add SMS credits
            balance = SmsService.add_credits(
                tenant=tenant,
                amount=total_credits,
                payment=payment,
                package=package,
                user=user,
                description=f"Purchased {package.display_name} (Invoice: {invoice.invoice_number})"
            )

            return payment, balance

        except Exception as e:
            raise PaymentProcessingError(
                _("Failed to process SMS payment: %(error)s") % {'error': str(e)}
            )

    @staticmethod
    def get_payment_status(payment_id):
        """
        Get payment status by ID

        Args:
            payment_id: Payment instance ID

        Returns:
            dict: Payment status information

        Raises:
            Payment.DoesNotExist: If payment not found
        """
        payment = Payment.objects.select_related('tenant', 'paid_by').get(id=payment_id)

        return {
            'id': payment.id,
            'tenant': payment.tenant.name,
            'amount': payment.amount,
            'payment_method': payment.payment_method,
            'payment_type': payment.payment_type,
            'status': payment.status,
            'transaction_id': payment.transaction_id,
            'created_at': payment.created_at,
            'metadata': payment.metadata
        }

    @staticmethod
    def get_tenant_invoices(tenant, invoice_type=None, status=None):
        """
        Get invoices for a tenant

        Args:
            tenant: Company instance
            invoice_type: Filter by invoice type (optional)
            status: Filter by status (optional)

        Returns:
            QuerySet: Invoice queryset
        """
        invoices = Invoice.objects.filter(tenant=tenant).select_related('payment')

        if invoice_type:
            invoices = invoices.filter(invoice_type=invoice_type)

        if status:
            invoices = invoices.filter(status=status)

        return invoices.order_by('-issued_at')
