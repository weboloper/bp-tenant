from django.contrib import admin
from .models import BusinessType, PaymentMethod

@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'is_system', 'is_active', 'order']
    list_filter = ['is_system', 'is_active', 'company']
    search_fields = ['name', 'company__name']
    ordering = ['order', 'name']
    
    def get_readonly_fields(self, request, obj=None):
        # Sistem kayıtları değiştirilemez (is_system=True ise)
        if obj and obj.is_system:
            return ['name', 'is_system', 'source_code', 'company']
        return ['is_system', 'source_code']
