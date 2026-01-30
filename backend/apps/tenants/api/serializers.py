from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from tenants.models import Company, Product


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Company model.
    Handles company creation and updates with business rule validation.
    """
    employee_count = serializers.ReadOnlyField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'business_type', 'description', 'is_active',
            'employee_count', 'is_owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def get_is_owner(self, obj):
        """Check if current user is the owner"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.owner == request.user
        return False

    def validate(self, attrs):
        """Validate: User can only own one active company"""
        request = self.context.get('request')

        # Only validate on creation (not update)
        if not self.instance and request and request.user:
            # Check if user already owns an active company
            existing = request.user.owned_companies.filter(
                is_deleted=False
            ).exists()

            if existing:
                raise serializers.ValidationError(
                    _("You already own a company. Please delete your existing company first.")
                )

        return attrs

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Product model.
    Simple serializer with company automatically set from request.
    """
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'company', 'company_name', 'name', 'description',
            'price', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['company', 'created_at', 'updated_at']