from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import BusinessType, Company, Product

@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['order', 'name']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'owner',
        'business_type',
        'is_active',
        'employee_count_display',
        'created_at'
    ]
    list_filter = ['is_active', 'is_deleted', 'business_type', 'created_at']
    search_fields = ['name', 'owner__username', 'owner__email']
    raw_id_fields = ['owner', 'business_type']
    readonly_fields = ['created_at', 'updated_at', 'employee_count_display', 'deleted_at', 'deleted_by']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('owner', 'name', 'business_type', 'description')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_deleted', 'deleted_at', 'deleted_by')
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at', 'employee_count_display'),
            'classes': ('collapse',)
        }),
    )

    def employee_count_display(self, obj):
        count = obj.employee_count
        return format_html(
            '<strong>{}</strong> active employees',
            count
        )
    employee_count_display.short_description = _('Employees')

    actions = ['activate_companies', 'deactivate_companies']

    def activate_companies(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} companies activated')
    activate_companies.short_description = _('Activate selected companies')

    def deactivate_companies(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} companies deactivated')
    deactivate_companies.short_description = _('Deactivate selected companies')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'company']
    search_fields = ['name', 'company__name', 'description']
    raw_id_fields = ['company']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Product Information'), {
            'fields': ('company', 'name', 'description', 'price')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_products', 'deactivate_products']

    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated')
    activate_products.short_description = _('Activate selected products')

    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated')
    deactivate_products.short_description = _('Deactivate selected products')
