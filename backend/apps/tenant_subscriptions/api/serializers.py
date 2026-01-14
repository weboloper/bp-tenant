from rest_framework import serializers
from system_subscriptions.models import SubscriptionPlan
from tenant_subscriptions.models import TenantSubscription, SubscriptionHistory


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
