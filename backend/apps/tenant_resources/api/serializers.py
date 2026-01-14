from rest_framework import serializers
from django.conf import settings
from tenant_resources.models import SmsBalance, SmsTransaction
from system_subscriptions.models import SMSPackage


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
        # Get base price from settings or default to 0.10
        base_price_per_sms = getattr(settings, 'SMS_BASE_PRICE', 0.10)
        total = obj.sms_credits + obj.bonus_credits
        if total > 0:
            actual_price_per_sms = obj.price / total
            savings = ((base_price_per_sms - actual_price_per_sms) / base_price_per_sms) * 100
            return round(max(0, savings), 1)
        return 0
