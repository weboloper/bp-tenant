from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import BusinessType, Company, Employee, CompanyRolePermission, Product


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


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'company',
        'position',
        'role_level',
        'status',
        'hire_date',
        'is_deleted'
    ]
    list_filter = [
        'status',
        'role_level',
        'is_deleted',
        'hire_date',
        'company'
    ]
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'company__name',
        'position',
        'department'
    ]
    raw_id_fields = ['user', 'company']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at', 'deleted_by']
    date_hierarchy = 'hire_date'

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'company', 'position', 'department')
        }),
        (_('Role & Status'), {
            'fields': ('role_level', 'status', 'hire_date')
        }),
        (_('Compensation'), {
            'fields': ('salary',),
            'classes': ('collapse',)
        }),
        (_('Soft Delete'), {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_employees', 'deactivate_employees']

    def activate_employees(self, request, queryset):
        updated = queryset.update(status=Employee.Status.ACTIVE)
        self.message_user(request, f'{updated} employees activated')
    activate_employees.short_description = _('Activate selected employees')

    def deactivate_employees(self, request, queryset):
        updated = queryset.update(status=Employee.Status.INACTIVE)
        self.message_user(request, f'{updated} employees deactivated')
    deactivate_employees.short_description = _('Deactivate selected employees')


@admin.register(CompanyRolePermission)
class CompanyRolePermissionAdmin(admin.ModelAdmin):
    list_display = ['company', 'level', 'get_level_display']
    list_filter = ['level']
    search_fields = ['company__name']
    raw_id_fields = ['company']

    fieldsets = (
        (_('Basic'), {
            'fields': ('company', 'level')
        }),
        (_('Bookings & Clients'), {
            'fields': (
                'can_book_appointments',
                'can_view_own_calendar',
                'can_view_all_calendars',
                'can_apply_discount',
                'can_view_client_contact',
                'can_download_clients',
            ),
            'classes': ('collapse',)
        }),
        (_('Services'), {
            'fields': (
                'can_view_services',
                'can_create_services',
                'can_edit_services',
                'can_delete_services',
            ),
            'classes': ('collapse',)
        }),
        (_('Sales'), {
            'fields': (
                'can_checkout',
                'can_edit_prices',
                'can_void_invoices',
                'can_view_all_sales',
            ),
            'classes': ('collapse',)
        }),
        (_('Staff'), {
            'fields': (
                'can_view_schedules',
                'can_manage_staff',
                'can_manage_permissions',
                'can_run_payroll',
            ),
            'classes': ('collapse',)
        }),
        (_('Inventory'), {
            'fields': (
                'can_view_inventory',
                'can_create_products',
                'can_import_bulk',
                'can_bulk_operations',
            ),
            'classes': ('collapse',)
        }),
        (_('Data & Reports'), {
            'fields': (
                'can_access_reports',
                'can_access_insights',
                'can_view_team_data',
            ),
            'classes': ('collapse',)
        }),
        (_('Setup'), {
            'fields': (
                'can_edit_business_info',
                'can_manage_locations',
                'can_manage_billing',
            ),
            'classes': ('collapse',)
        }),
    )

    def get_level_display(self, obj):
        return obj.get_level_display()
    get_level_display.short_description = _('Role Name')


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
