from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import BusinessType


@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['order', 'name']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'icon')
        }),
        (_('Display Settings'), {
            'fields': ('is_active', 'order')
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_types', 'deactivate_types']

    def activate_types(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} business types activated')
    activate_types.short_description = _('Activate selected business types')

    def deactivate_types(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} business types deactivated')
    deactivate_types.short_description = _('Deactivate selected business types')
