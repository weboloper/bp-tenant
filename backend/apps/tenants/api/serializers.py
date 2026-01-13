from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from tenants.models import Company, Employee, Product


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


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for Employee model.
    Handles employee creation with business rule validation.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_username', 'user_email', 'company', 'company_name',
            'role_level', 'status', 'salary', 'hire_date', 'position', 'department',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'salary': {'write_only': True}  # Sensitive data
        }

    def validate_user(self, value):
        """Ensure user is not already employed elsewhere"""
        # Check if user already has active employment
        existing = Employee.objects.filter(
            user=value,
            is_deleted=False
        ).exclude(pk=self.instance.pk if self.instance else None)

        if existing.exists():
            raise serializers.ValidationError(
                _("This user is already employed at another company.")
            )

        return value

    def validate(self, attrs):
        """Additional validation logic"""
        user = attrs.get('user', self.instance.user if self.instance else None)
        company = attrs.get('company', self.instance.company if self.instance else None)

        if user and company:
            # Prevent making user both owner and employee of same company
            if company.owner == user:
                raise serializers.ValidationError(
                    _("Company owner cannot also be an employee. Owner has implicit admin access.")
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


class EmployeeListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for employee lists.
    Excludes sensitive data like salary.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'user_username', 'user_email', 'role_level', 'status',
            'position', 'department', 'hire_date'
        ]
