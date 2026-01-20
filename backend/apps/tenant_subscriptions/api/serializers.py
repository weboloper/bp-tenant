from rest_framework import serializers
from django.conf import settings
from system_subscriptions.models import SubscriptionPlan, SMSPackage
from tenant_subscriptions.models import TenantSubscription, SubscriptionHistory, SmsBalance, SmsTransaction


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price', 'billing_cycle',
            'max_employee', 'max_locations', 'max_appointments_per_month',
            'features', 'is_active'
        ]

    def get_features(self, obj):
        """Get all available features as a dict"""
        return obj.features


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
            'start_date', 'expires_at', 'is_expired',
            'original_price', 'discounted_price', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']

    def get_is_expired(self, obj):
        """Check if subscription is expired"""
        from django.utils import timezone
        return obj.expires_at < timezone.now() if obj.expires_at else False


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription change history"""
    old_plan_name = serializers.CharField(source='old_plan.name', read_only=True)
    new_plan_name = serializers.CharField(source='new_plan.name', read_only=True)
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


# SMS Serializers (moved from tenant_resources)

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
            return round(obj.price / total, 4)
        return 0

    def get_total_credits(self, obj):
        """Get total credits (base + bonus)"""
        return obj.sms_credits + obj.bonus_credits

    def get_savings_percent(self, obj):
        """Calculate savings compared to base price"""
        base_price_per_sms = getattr(settings, 'SMS_BASE_PRICE', 0.10)
        total = obj.sms_credits + obj.bonus_credits
        if total > 0:
            actual_price_per_sms = obj.price / total
            savings = ((base_price_per_sms - actual_price_per_sms) / base_price_per_sms) * 100
            return round(max(0, savings), 1)
        return 0
