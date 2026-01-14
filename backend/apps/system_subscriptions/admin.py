from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import SubscriptionPlan, SMSPackage


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'billing_cycle', 'is_active', 'created_at']
    list_filter = ['billing_cycle', 'is_active', 'has_online_booking', 'has_sms_notifications', 'has_analytics']
    search_fields = ['name']
    readonly_fields = ['created_at']


@admin.register(SMSPackage)
class SMSPackageAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'sms_credits', 'price', 'is_active', 'is_featured', 'sort_order', 'created_at']
    list_filter = ['is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'get_price_per_sms_display', 'get_total_credits_display']
    ordering = ['sort_order', 'sms_credits']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'display_name', 'description')
        }),
        (_('Pricing & Credits'), {
            'fields': ('sms_credits', 'price', 'bonus_credits', 'get_price_per_sms_display', 'get_total_credits_display')
        }),
        (_('Display Settings'), {
            'fields': ('is_active', 'is_featured', 'sort_order')
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_packages', 'deactivate_packages', 'feature_packages', 'unfeature_packages']

    def get_price_per_sms_display(self, obj):
        price_per_sms = obj.get_price_per_sms()
        return format_html('<strong>{:.4f} TL</strong>', price_per_sms)
    get_price_per_sms_display.short_description = _('Price per SMS')

    def get_total_credits_display(self, obj):
        total_credits = obj.get_total_credits()
        return format_html(
            '<strong>{}</strong> ({} + {} bonus)',
            total_credits,
            obj.sms_credits or 0,
            obj.bonus_credits or 0
        )
    get_total_credits_display.short_description = _('Total Credits')

    def activate_packages(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} SMS packages activated')
    activate_packages.short_description = _('Activate selected packages')

    def deactivate_packages(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} SMS packages deactivated')
    deactivate_packages.short_description = _('Deactivate selected packages')

    def feature_packages(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} SMS packages marked as featured')
    feature_packages.short_description = _('Mark as featured')

    def unfeature_packages(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} SMS packages unmarked as featured')
    unfeature_packages.short_description = _('Remove featured status')


# TenantSubscriptionAdmin moved to tenant_subscriptions/admin.py
