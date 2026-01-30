from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Employee, CompanyRolePermission


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
