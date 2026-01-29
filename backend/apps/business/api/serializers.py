from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

# Settings models
from business.models.settings import (
    BusinessSettings,

)

# Lookup models
from business.models.lookups import (

    PaymentMethod,

)

# Data models
from business.models.data import (
    Location,
    TaxRate,
)


# =============================================================================
# SETTINGS SERIALIZERS (Singleton per tenant)
# =============================================================================

class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        fields = [
            'id', 'currency', 'tax_calculation',
            'team_default_language', 'client_default_language',
            'facebook_url', 'instagram_url', 'twitter_url', 'website_url',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']



# =============================================================================
# LOOKUP SERIALIZERS (System-protected + Custom)
# =============================================================================

class SystemProtectedSerializerMixin:
    """Mixin for serializers with system-protected records"""

    def validate_name(self, value):
        """Prevent editing name of system records"""
        if self.instance and self.instance.is_system:
            if value != self.instance.name:
                raise serializers.ValidationError(
                    _("System records cannot be modified.")
                )
        return value


class PaymentMethodSerializer(SystemProtectedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'icon', 'order', 'is_active', 'is_system', 'created_at']
        read_only_fields = ['id', 'is_system', 'created_at']



# =============================================================================
# DATA SERIALIZERS (Full CRUD)
# =============================================================================

class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for location lists"""
    class Meta:
        model = Location
        fields = ['id', 'name', 'city', 'phone', 'is_active']


class LocationSerializer(serializers.ModelSerializer):
    """Full serializer for location detail/create/update"""
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'phone', 'email',
            'main_business_type', 'additional_business_types', 'other_business_type',
            'address_line1', 'address_line2', 'district', 'city', 'postcode', 'country',
            'latitude', 'longitude',
            'working_hours',
            'use_location_for_billing', 'billing_company_name',
            'billing_address', 'billing_city', 'billing_postcode', 'invoice_note',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = ['id', 'name', 'rate', 'is_default', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
