from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# Settings models
from .models.settings import (
    BusinessSettings,
)

# Lookup models
from .models.lookups import (
    PaymentMethod,
)

# Data models
from .models.entities import (
    Location,
    TaxRate,
)


# =============================================================================
# SETTINGS ADMINS (Singleton per tenant)
# =============================================================================

class TenantSettingsAdmin(admin.ModelAdmin):
    """Base admin for singleton settings"""
    list_display = ['company', 'updated_at']
    list_filter = ['company']
    search_fields = ['company__name']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        # Settings are created via signals, not manually
        return False


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(TenantSettingsAdmin):
    list_display = ['company', 'currency', 'tax_calculation', 'updated_at']
    fieldsets = (
        (_('Company'), {'fields': ('company',)}),
        (_('Currency & Tax'), {'fields': ('currency', 'tax_calculation')}),
        (_('Language'), {'fields': ('team_default_language', 'client_default_language')}),
        (_('Social Links'), {'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'website_url')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


# =============================================================================
# LOOKUP ADMINS (System-protected + Custom)
# =============================================================================

class TenantLookupAdmin(admin.ModelAdmin):
    """Base admin for lookup tables with system protection"""
    list_display = ['name', 'company', 'is_system', 'order', 'is_active']
    list_filter = ['company', 'is_system', 'is_active']
    search_fields = ['name', 'company__name']
    ordering = ['company', 'order', 'name']
    list_editable = ['order', 'is_active']
    readonly_fields = ['is_system', 'source_code', 'created_at', 'updated_at']

    def get_readonly_fields(self, request, obj=None):
        """Make name readonly for system records"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_system:
            readonly.extend(['name'])
        return readonly


@admin.register(PaymentMethod)
class PaymentMethodAdmin(TenantLookupAdmin):
    list_display = ['name', 'company', 'icon', 'is_system', 'order', 'is_active']



# =============================================================================
# DATA ADMINS (Full CRUD)
# =============================================================================

class TenantDataAdmin(admin.ModelAdmin):
    """Base admin for tenant data models"""
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'company__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Location)
class LocationAdmin(TenantDataAdmin):
    list_display = ['name', 'company', 'city', 'phone', 'is_active']
    list_filter = ['company', 'is_active', 'city', 'country']
    search_fields = ['name', 'company__name', 'city', 'address_line1']
    fieldsets = (
        (_('Basic'), {'fields': ('company', 'name', 'is_active')}),
        (_('Contact'), {'fields': ('phone', 'email')}),
        (_('Business Type'), {'fields': ('main_business_type', 'additional_business_types', 'other_business_type')}),
        (_('Address'), {'fields': (
            'address_line1', 'address_line2', 'district', 'city', 'postcode', 'country'
        )}),
        (_('Coordinates'), {'fields': ('latitude', 'longitude'), 'classes': ('collapse',)}),
        (_('Working Hours'), {'fields': ('working_hours',)}),
        (_('Billing'), {
            'fields': (
                'use_location_for_billing', 'billing_company_name',
                'billing_address', 'billing_city', 'billing_postcode', 'invoice_note'
            ),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(TaxRate)
class TaxRateAdmin(TenantDataAdmin):
    list_display = ['name', 'company', 'rate', 'is_default', 'is_active']
    list_filter = ['company', 'is_active', 'is_default']