from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from staff.models import Employee


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
