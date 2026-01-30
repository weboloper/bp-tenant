# business/services/provisioning.py

from django.db import transaction
from defaults.models import (

    DefaultPaymentMethod,

)
from business.models import (
    # Lookups

    PaymentMethod,

    # Settings
    BusinessSettings,

)


class TenantProvisioningService:
    """
    Service to provision default settings for new tenants.
    Called via signal when Company is created.
    """
    
    # Mapping: Platform Default Model -> Tenant Model
    LOOKUP_MAPPINGS = [
        (DefaultPaymentMethod, PaymentMethod, ['name', 'icon', 'order']),

    ]
    
    # Settings models that need to be created with defaults
    SETTINGS_MODELS = [
        BusinessSettings,
    ]
    
    @classmethod
    @transaction.atomic
    def provision(cls, company):
        """
        Provision all defaults for a new company.
        
        Args:
            company: Company instance
            
        Returns:
            dict: Summary of provisioned items
        """
        result = {
            'lookups': {},
            'settings': [],
        }
        
        # 1. Copy lookup tables
        for default_model, tenant_model, fields in cls.LOOKUP_MAPPINGS:
            count = cls._copy_lookup_defaults(company, default_model, tenant_model, fields)
            result['lookups'][tenant_model.__name__] = count
        
        # 2. Create settings with defaults
        for settings_model in cls.SETTINGS_MODELS:
            cls._create_settings(company, settings_model)
            result['settings'].append(settings_model.__name__)
        
        return result
    
    @classmethod
    def _copy_lookup_defaults(cls, company, default_model, tenant_model, fields):
        """
        Copy platform defaults to tenant lookup table.
        
        Args:
            company: Company instance
            default_model: Platform default model class
            tenant_model: Tenant model class
            fields: List of field names to copy
            
        Returns:
            int: Number of records created
        """
        defaults = default_model.objects.filter(is_active=True)
        created_count = 0
        
        for default in defaults:
            data = {field: getattr(default, field) for field in fields}
            data.update({
                'company': company,
                'is_system': True,
                'source_code': default.code,
                'is_active': True,
            })
            
            tenant_model.objects.create(**data)
            created_count += 1
        
        return created_count
    
    @classmethod
    def _create_settings(cls, company, settings_model):
        """
        Create settings with default values.
        Django model defaults will be used.
        
        Args:
            company: Company instance
            settings_model: Settings model class
        """
        settings_model.objects.get_or_create(company=company)
    
    @classmethod
    def provision_missing(cls, company):
        """
        Provision any missing defaults (for existing companies).
        Useful when new platform defaults are added.
        
        Args:
            company: Company instance
        """
        for default_model, tenant_model, fields in cls.LOOKUP_MAPPINGS:
            existing_codes = set(
                tenant_model.objects.filter(company=company, is_system=True)
                .values_list('source_code', flat=True)
            )
            
            new_defaults = default_model.objects.filter(
                is_active=True
            ).exclude(code__in=existing_codes)
            
            for default in new_defaults:
                data = {field: getattr(default, field) for field in fields}
                data.update({
                    'company': company,
                    'is_system': True,
                    'source_code': default.code,
                    'is_active': True,
                })
                tenant_model.objects.create(**data)