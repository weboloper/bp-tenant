from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import SmsBalance, SmsTransaction


@admin.register(SmsBalance)
class SmsBalanceAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'balance_display', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['tenant__name']
    raw_id_fields = ['tenant']
    readonly_fields = ['last_updated']

    def balance_display(self, obj):
        color = 'green' if obj.balance > 100 else 'orange' if obj.balance > 10 else 'red'
        return format_html(
            '<strong style="color: {};">{} SMS</strong>',
            color,
            obj.balance
        )
    balance_display.short_description = _('Balance')

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of balance records
        return False


@admin.register(SmsTransaction)
class SmsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'tenant',
        'transaction_type',
        'amount_display',
        'balance_after',
        'created_at',
        'created_by'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['tenant__name', 'description']
    raw_id_fields = ['tenant', 'payment', 'sms_package', 'created_by']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('Transaction Details'), {
            'fields': (
                'tenant',
                'transaction_type',
                'amount',
                'balance_after'
            )
        }),
        (_('References'), {
            'fields': ('payment', 'sms_package'),
            'classes': ('collapse',)
        }),
        (_('Additional Info'), {
            'fields': ('description', 'metadata'),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        color = 'green' if obj.amount > 0 else 'red'
        sign = '+' if obj.amount > 0 else ''
        return format_html(
            '<strong style="color: {};">{}{}</strong>',
            color,
            sign,
            obj.amount
        )
    amount_display.short_description = _('Amount')

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion for admin adjustments
        if obj and obj.transaction_type == 'admin_adjustment':
            return True
        return False
