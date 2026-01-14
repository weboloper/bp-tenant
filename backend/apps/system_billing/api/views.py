"""
System Billing API Views
"""

from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from system_billing.models import Payment, Invoice
from system_billing.services import IyzicoService
from system_subscriptions.models import SubscriptionPlan
from tenant_subscriptions.models import TenantSubscription
from .serializers import (
    PaymentSerializer,
    InvoiceSerializer,
    SubscriptionPlanSerializer,
    IyzicoCheckoutInitializeSerializer,
    ManualPaymentCreateSerializer,
)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Payment ViewSet

    list: Get payment history for current tenant
    retrieve: Get payment details
    create_iyzico_checkout: Initialize iyzico checkout form
    create_manual_payment: Create manual payment (bank transfer/EFT)
    iyzico_callback: Handle iyzico callback
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'payment_type', 'payment_method']
    search_fields = ['gateway_transaction_id', 'bank_reference']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filter payments by current user's tenant.
        Staff users can see all payments.
        """
        user = self.request.user

        if user.is_staff:
            return Payment.objects.all()

        # Get user's tenant
        if not hasattr(user, 'profile') or not user.profile.company:
            return Payment.objects.none()

        return Payment.objects.filter(tenant=user.profile.company)

    @action(detail=False, methods=['post'], url_path='subscription/checkout')
    def create_iyzico_checkout(self, request):
        """
        Initialize iyzico checkout form for subscription purchase.

        POST /api/v1/billing/payments/subscription/checkout/
        {
            "subscription_plan_id": 1,
            "billing_cycle": "monthly",
            "buyer_name": "John",
            "buyer_surname": "Doe",
            "buyer_email": "john@example.com",
            "buyer_phone": "+905555555555",
            "buyer_identity_number": "11111111111",
            "buyer_address": "Address here",
            "buyer_city": "Istanbul",
            "buyer_country": "Turkey",
            "enabled_installments": [1, 2, 3, 6]
        }

        Returns:
        {
            "payment_id": 123,
            "checkout_form_content": "<script>...</script>",
            "status": "pending"
        }
        """
        serializer = IyzicoCheckoutInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get user's tenant
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.company:
            raise PermissionDenied("User does not belong to any company")

        tenant = user.profile.company

        # Get subscription plan
        plan = get_object_or_404(
            SubscriptionPlan,
            id=serializer.validated_data['subscription_plan_id'],
            is_active=True
        )

        # Calculate amount based on billing cycle
        billing_cycle = serializer.validated_data['billing_cycle']
        if billing_cycle == 'yearly':
            # Apply discount for yearly (if applicable)
            amount = plan.price * 12  # You can apply discount here
        else:
            amount = plan.price

        # Create pending payment record
        payment = Payment.objects.create(
            tenant=tenant,
            payment_type='subscription',
            payment_method='iyzico',
            amount=amount,
            currency='TRY',
            status='pending',
            gateway_name='iyzico',
            notes=f"Subscription: {plan.name} ({billing_cycle})"
        )

        # Initialize iyzico checkout
        iyzico = IyzicoService()

        # Prepare buyer info
        buyer_info = {
            'id': tenant.id,
            'name': serializer.validated_data['buyer_name'],
            'surname': serializer.validated_data['buyer_surname'],
            'email': serializer.validated_data['buyer_email'],
            'phone': serializer.validated_data['buyer_phone'],
            'identity_number': serializer.validated_data['buyer_identity_number'],
            'address': serializer.validated_data['buyer_address'],
            'city': serializer.validated_data['buyer_city'],
            'country': serializer.validated_data.get('buyer_country', 'Turkey'),
        }

        if serializer.validated_data.get('buyer_zip_code'):
            buyer_info['zip_code'] = serializer.validated_data['buyer_zip_code']

        # Prepare basket items
        basket_items = [
            IyzicoService.format_basket_item(
                item_id=f"plan_{plan.id}",
                name=f"{plan.name} - {billing_cycle}",
                category='Subscription',
                price=amount,
                item_type='VIRTUAL'
            )
        ]

        # Generate callback URL
        callback_url = request.build_absolute_uri('/api/v1/billing/payments/iyzico/callback/')

        # Initialize checkout
        result = iyzico.initialize_checkout(
            amount=amount,
            currency='TRY',
            buyer_info=buyer_info,
            basket_items=basket_items,
            callback_url=callback_url,
            conversation_id=f"payment_{payment.id}",
            enabled_installments=serializer.validated_data.get('enabled_installments', [1])
        )

        if not result.success:
            payment.status = 'failed'
            payment.save()
            return Response({
                'error': result.error_message,
                'payment_id': payment.id
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update payment with iyzico token
        payment.gateway_token = result.token
        payment.gateway_data = {
            'conversation_id': f"payment_{payment.id}",
        }
        payment.metadata = result.data
        payment.save()

        return Response({
            'payment_id': payment.id,
            'checkout_form_content': result.checkout_form_content,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='subscription/manual')
    def create_manual_payment(self, request):
        """
        Create manual payment (bank transfer/EFT).

        POST /api/v1/billing/payments/subscription/manual/
        {
            "subscription_plan_id": 1,
            "payment_method": "bank_transfer",
            "bank_reference": "REF123456",
            "payment_proof": <file>,
            "notes": "Paid via bank transfer"
        }

        Returns:
        {
            "payment_id": 124,
            "status": "pending",
            "message": "Payment submitted. Awaiting admin approval."
        }
        """
        serializer = ManualPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get user's tenant
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.company:
            raise PermissionDenied("User does not belong to any company")

        tenant = user.profile.company

        # Get subscription plan
        plan = get_object_or_404(
            SubscriptionPlan,
            id=serializer.validated_data['subscription_plan_id'],
            is_active=True
        )

        # Create pending payment
        payment = Payment.objects.create(
            tenant=tenant,
            payment_type='subscription',
            payment_method=serializer.validated_data['payment_method'],
            amount=plan.price,
            currency='TRY',
            status='pending',
            gateway_name='manual',
            bank_reference=serializer.validated_data.get('bank_reference', ''),
            payment_proof=serializer.validated_data.get('payment_proof'),
            notes=serializer.validated_data.get('notes', '')
        )

        return Response({
            'payment_id': payment.id,
            'status': 'pending',
            'message': 'Payment submitted. Awaiting admin approval.',
            'amount': str(payment.amount),
            'currency': payment.currency
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='iyzico/callback')
    def iyzico_callback(self, request):
        """
        Handle iyzico callback after payment completion.

        GET /api/v1/billing/payments/iyzico/callback/?token=xxx

        This endpoint is called by iyzico after user completes payment.
        """
        token = request.query_params.get('token')

        if not token:
            return Response({
                'error': 'Token parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find payment by token
        try:
            payment = Payment.objects.get(gateway_token=token)
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Retrieve payment result from iyzico
        iyzico = IyzicoService()
        result = iyzico.retrieve_checkout_result(
            token=token,
            conversation_id=payment.gateway_data.get('conversation_id')
        )

        # Update payment based on result
        payment.metadata = result.data

        if result.success:
            payment_status = result.data.get('status')

            if payment_status == 'SUCCESS':
                payment.status = 'completed'
                payment.gateway_transaction_id = result.transaction_id
                payment.gateway_data.update({
                    'fraud_status': result.data.get('fraudStatus'),
                    'payment_items': result.data.get('paymentItems', [])
                })

                # Activate subscription
                if payment.subscription:
                    payment.subscription.status = 'active'
                    payment.subscription.save()

            elif payment_status == 'FAILURE':
                payment.status = 'failed'
            else:
                payment.status = 'pending'

            payment.save()

            # Redirect to success/failure page (frontend URL)
            redirect_url = f"{settings.FRONTEND_URL}/billing/payment-result/{payment.id}/"
            return Response({
                'success': True,
                'payment_id': payment.id,
                'status': payment.status,
                'redirect_url': redirect_url
            })
        else:
            payment.status = 'failed'
            payment.save()

            return Response({
                'success': False,
                'payment_id': payment.id,
                'error': result.error_message
            }, status=status.HTTP_400_BAD_REQUEST)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Invoice ViewSet

    list: Get invoices for current tenant
    retrieve: Get invoice details
    download: Download invoice file
    """

    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['invoice_type', 'invoice_date']
    search_fields = ['invoice_number', 'tax_number', 'company_title']
    ordering_fields = ['invoice_date', 'created_at']
    ordering = ['-invoice_date']

    def get_queryset(self):
        """
        Filter invoices by current user's tenant.
        Staff users can see all invoices.
        """
        user = self.request.user

        if user.is_staff:
            return Invoice.objects.all()

        # Get user's tenant
        if not hasattr(user, 'profile') or not user.profile.company:
            return Invoice.objects.none()

        return Invoice.objects.filter(payment__tenant=user.profile.company)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download invoice file.

        GET /api/v1/billing/invoices/{id}/download/
        """
        invoice = self.get_object()

        if not invoice.invoice_file:
            return Response({
                'error': 'Invoice file not available'
            }, status=status.HTTP_404_NOT_FOUND)

        # Return file URL (frontend will handle actual download)
        return Response({
            'invoice_number': invoice.invoice_number,
            'file_url': request.build_absolute_uri(invoice.invoice_file.url)
        })


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Subscription Plan ViewSet (public read-only)

    list: Get available subscription plans
    retrieve: Get plan details
    """

    serializer_class = SubscriptionPlanSerializer
    permission_classes = []  # Public access
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    filterset_fields = ['billing_cycle']
    ordering = ['price']
