from rest_framework import serializers
from django.conf import settings
from billing.models import (
    SubscriptionPlan, SMSPackage,
    TenantSubscription, SubscriptionHistory,
    SmsBalance, SmsTransaction,
    Payment, Invoice
)


# ============================================================================
# Subscription Plan Serializers
# ============================================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    features = serializers.SerializerMethodField()
    billing_cycle_display = serializers.CharField(source='get_billing_cycle_display', read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price', 'billing_cycle', 'billing_cycle_display',
            'max_employee', 'max_locations', 'max_appointments_per_month',
            'has_online_booking', 'has_sms_notifications', 'has_analytics',
            'features', 'is_active'
        ]

    def get_features(self, obj):
        """Get all available features as a dict"""
        return obj.features


# ============================================================================
# Tenant Subscription Serializers
# ============================================================================

class TenantSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for tenant subscriptions"""
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        source='plan',
        write_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = TenantSubscription
        fields = [
            'id', 'tenant', 'plan', 'plan_id', 'status', 'status_display',
            'started_at', 'expires_at', 'is_expired',
            'original_price', 'discounted_price', 'notes'
        ]
        read_only_fields = ['tenant']

    def get_is_expired(self, obj):
        """Check if subscription is expired"""
        from django.utils import timezone
        return obj.expires_at < timezone.now() if obj.expires_at else False


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription change history"""
    old_plan_name = serializers.CharField(source='old_plan.name', read_only=True, allow_null=True)
    new_plan_name = serializers.CharField(source='new_plan.name', read_only=True, allow_null=True)
    changed_by_name = serializers.CharField(
        source='changed_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SubscriptionHistory
        fields = [
            'id', 'tenant', 'old_plan', 'old_plan_name',
            'new_plan', 'new_plan_name', 'changed_by',
            'changed_by_name', 'reason', 'changed_at'
        ]
        read_only_fields = ['tenant', 'changed_at']


# ============================================================================
# SMS Serializers
# ============================================================================

class SmsBalanceSerializer(serializers.ModelSerializer):
    """Serializer for SMS balance"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = SmsBalance
        fields = [
            'id', 'tenant', 'tenant_name', 'balance',
            'last_updated'
        ]
        read_only_fields = ['tenant', 'balance', 'last_updated']


class SmsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for SMS transactions"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    sms_package_name = serializers.CharField(
        source='sms_package.display_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SmsTransaction
        fields = [
            'id', 'tenant', 'tenant_name', 'transaction_type',
            'transaction_type_display', 'amount', 'balance_after',
            'payment', 'sms_package', 'sms_package_name',
            'created_by', 'created_by_name', 'description',
            'metadata', 'created_at'
        ]
        read_only_fields = [
            'tenant', 'balance_after', 'created_by', 'created_at'
        ]


class SMSPackageSerializer(serializers.ModelSerializer):
    """Serializer for SMS packages"""
    price_per_sms = serializers.SerializerMethodField()
    total_credits = serializers.SerializerMethodField()
    savings_percent = serializers.SerializerMethodField()

    class Meta:
        model = SMSPackage
        fields = [
            'id', 'name', 'display_name', 'description',
            'sms_credits', 'bonus_credits', 'total_credits',
            'price', 'price_per_sms', 'savings_percent',
            'is_active', 'is_featured', 'sort_order'
        ]

    def get_price_per_sms(self, obj):
        """Calculate price per SMS"""
        total = obj.sms_credits + obj.bonus_credits
        if total > 0:
            return round(float(obj.price) / total, 4)
        return 0

    def get_total_credits(self, obj):
        """Get total credits (base + bonus)"""
        return obj.sms_credits + obj.bonus_credits

    def get_savings_percent(self, obj):
        """Calculate savings compared to base price"""
        base_price_per_sms = getattr(settings, 'SMS_BASE_PRICE', 0.10)
        total = obj.sms_credits + obj.bonus_credits
        if total > 0:
            actual_price_per_sms = float(obj.price) / total
            savings = ((base_price_per_sms - actual_price_per_sms) / base_price_per_sms) * 100
            return round(max(0, savings), 1)
        return 0


# ============================================================================
# Payment Serializers
# ============================================================================

class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer for list/detail views"""

    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    subscription_plan = serializers.CharField(
        source='subscription.plan.name',
        read_only=True,
        allow_null=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'payment_type',
            'payment_type_display',
            'payment_method',
            'payment_method_display',
            'amount',
            'currency',
            'status',
            'status_display',
            'gateway_name',
            'gateway_transaction_id',
            'subscription',
            'subscription_plan',
            'bank_reference',
            'approved_by',
            'approved_at',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'tenant',
            'gateway_transaction_id',
            'approved_by',
            'approved_at',
            'created_at',
            'updated_at',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Invoice serializer"""

    payment_amount = serializers.DecimalField(
        source='payment.amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    tenant_name = serializers.CharField(source='payment.tenant.name', read_only=True)
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    invoice_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id',
            'payment',
            'payment_amount',
            'tenant_name',
            'invoice_type',
            'invoice_type_display',
            'invoice_number',
            'invoice_date',
            'invoice_file',
            'invoice_file_url',
            'tax_office',
            'tax_number',
            'company_title',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_invoice_file_url(self, obj):
        """Get full URL for invoice file"""
        if obj.invoice_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.invoice_file.url)
            return obj.invoice_file.url
        return None


# ============================================================================
# iyzico Checkout Serializers
# ============================================================================

class IyzicoCheckoutInitializeSerializer(serializers.Serializer):
    """Serializer for iyzico checkout initialization"""

    subscription_plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'])

    # Buyer information
    buyer_name = serializers.CharField(max_length=50)
    buyer_surname = serializers.CharField(max_length=50)
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(max_length=20, help_text="Format: +905XXXXXXXXX")
    buyer_identity_number = serializers.CharField(
        max_length=11,
        help_text="TC Kimlik No or Tax Number (11 digits)"
    )
    buyer_address = serializers.CharField(max_length=255)
    buyer_city = serializers.CharField(max_length=100)
    buyer_country = serializers.CharField(max_length=100, default='Turkey')
    buyer_zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Optional fields
    enabled_installments = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=lambda: [1],
        help_text="Allowed installment counts (e.g. [1, 2, 3, 6])"
    )

    def validate_subscription_plan_id(self, value):
        """Check if subscription plan exists and is active"""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Subscription plan not found or inactive")

    def validate_buyer_identity_number(self, value):
        """Validate TC Kimlik No format"""
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("Identity number must be 11 digits")
        return value

    def validate_buyer_phone(self, value):
        """Validate phone number format"""
        # Remove spaces and dashes
        phone = value.replace(' ', '').replace('-', '')

        if not phone.startswith('+90'):
            raise serializers.ValidationError("Phone must start with +90")

        if len(phone) != 13:  # +90 + 10 digits
            raise serializers.ValidationError("Phone must be +90 followed by 10 digits")

        return phone


class ManualPaymentCreateSerializer(serializers.Serializer):
    """Serializer for manual payment creation (bank transfer/EFT)"""

    subscription_plan_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=['bank_transfer', 'eft'])
    bank_reference = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Bank transaction reference number"
    )
    payment_proof = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Upload payment receipt (image or PDF)"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional notes about the payment"
    )

    def validate_subscription_plan_id(self, value):
        """Check if subscription plan exists and is active"""
        try:
            SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Subscription plan not found or inactive")

    def validate_payment_proof(self, value):
        """Validate file size and type"""
        if value:
            # Max 5MB
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size must be less than 5MB")

            # Allowed types
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "File type must be JPEG, PNG, or PDF"
                )

        return value
