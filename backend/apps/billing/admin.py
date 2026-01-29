from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from billing.models import (
    SubscriptionPlan, SMSPackage,
    TenantSubscription, SubscriptionHistory,
    SmsBalance, SmsTransaction,
    Payment, Invoice
)


# ============================================================================
# Subscription Plan Admin
# ============================================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'billing_cycle', 'is_active', 'created_at']
    list_filter = ['billing_cycle', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at']


# ============================================================================
# SMS Package Admin
# ============================================================================

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


# ============================================================================
# Tenant Subscription Admin
# ============================================================================

@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'plan', 'status', 'started_at', 'expires_at', 'auto_renew']
    list_filter = ['status', 'auto_renew', 'started_at']
    search_fields = ['tenant__name', 'plan__name']
    date_hierarchy = 'started_at'
    raw_id_fields = ['tenant', 'plan']
    readonly_fields = ['started_at']


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'old_plan', 'new_plan', 'changed_at', 'changed_by']
    list_filter = ['changed_at']
    search_fields = ['tenant__name', 'old_plan__name', 'new_plan__name']
    date_hierarchy = 'changed_at'
    raw_id_fields = ['tenant', 'old_plan', 'new_plan', 'changed_by']
    readonly_fields = ['changed_at']


# ============================================================================
# SMS Balance & Transaction Admin
# ============================================================================

@admin.register(SmsBalance)
class SmsBalanceAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'balance', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['tenant__name']
    raw_id_fields = ['tenant']
    readonly_fields = ['last_updated']


@admin.register(SmsTransaction)
class SmsTransactionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'transaction_type', 'amount', 'balance_after', 'created_at', 'created_by']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['tenant__name', 'description']
    date_hierarchy = 'created_at'
    raw_id_fields = ['tenant', 'payment', 'sms_package', 'created_by']
    readonly_fields = ['created_at', 'balance_after']


# ============================================================================
# Payment Admin
# ============================================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tenant',
        'payment_type',
        'amount',
        'currency',
        'payment_method',
        'status',
        'created_at',
        'requires_approval_tag'
    ]
    list_filter = [
        'status',
        'payment_type',
        'payment_method',
        'created_at',
        ('approved_at', admin.EmptyFieldListFilter),
    ]
    search_fields = [
        'tenant__name',
        'gateway_transaction_id',
        'bank_reference',
        'gateway_name'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'gateway_transaction_id',
        'gateway_token',
        'gateway_data'
    ]
    raw_id_fields = ['tenant', 'subscription', 'approved_by']

    actions = ['approve_manual_payments']

    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'tenant',
                'payment_type',
                'payment_method',
                'amount',
                'currency',
                'status',
            )
        }),
        (_('Gateway Integration'), {
            'fields': (
                'gateway_name',
                'gateway_transaction_id',
                'gateway_token',
                'gateway_data',
            ),
            'classes': ('collapse',),
        }),
        (_('Relationships'), {
            'fields': (
                'subscription',
                'sms_package',
            )
        }),
        (_('Manual Payment Details'), {
            'fields': (
                'bank_reference',
                'payment_proof',
            ),
            'classes': ('collapse',),
        }),
        (_('Approval'), {
            'fields': (
                'approved_by',
                'approved_at',
            )
        }),
        (_('Additional Information'), {
            'fields': (
                'notes',
                'metadata',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def approve_manual_payments(self, request, queryset):
        """Bulk approve manual payments"""
        approved_count = 0
        errors = []

        for payment in queryset:
            try:
                if payment.requires_approval():
                    payment.approve(request.user)
                    approved_count += 1
            except Exception as e:
                errors.append(f"Payment {payment.id}: {str(e)}")

        if approved_count > 0:
            self.message_user(
                request,
                _("%(count)d payment(s) approved successfully") % {'count': approved_count},
                level='success'
            )

        if errors:
            self.message_user(
                request,
                _("Errors: %(errors)s") % {'errors': ', '.join(errors)},
                level='error'
            )

    approve_manual_payments.short_description = _("Approve selected manual payments")

    def requires_approval_tag(self, obj):
        """Display visual indicator for payments requiring approval"""
        if obj.requires_approval():
            return format_html(
                '<span style="color: orange; font-weight: bold;">⏳ {}</span>',
                _('Needs Approval')
            )
        elif obj.status == 'completed' and obj.approved_by:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                _('Approved')
            )
        elif obj.status == 'completed':
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                _('Completed')
            )
        return format_html(
            '<span style="color: gray;">{}</span>',
            obj.get_status_display()
        )

    requires_approval_tag.short_description = _('Approval Status')


# ============================================================================
# Invoice Admin
# ============================================================================

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'invoice_number',
        'payment',
        'invoice_type',
        'invoice_date',
        'created_at',
        'download_link'
    ]
    list_filter = ['invoice_type', 'invoice_date', 'created_at']
    search_fields = [
        'invoice_number',
        'payment__tenant__name',
        'tax_number',
        'company_title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    raw_id_fields = ['payment', 'created_by']

    fieldsets = (
        (_('Invoice Information'), {
            'fields': (
                'payment',
                'invoice_type',
                'invoice_number',
                'invoice_date',
                'invoice_file'
            )
        }),
        (_('Tax Information'), {
            'fields': (
                'tax_office',
                'tax_number',
                'company_title'
            ),
            'classes': ('collapse',),
        }),
        (_('Audit'), {
            'fields': (
                'created_by',
                'notes',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',),
        }),
    )

    def download_link(self, obj):
        """Display download link for invoice file"""
        if obj.invoice_file:
            return format_html(
                '<a href="{}" target="_blank">📄 Download</a>',
                obj.invoice_file.url
            )
        return '-'

    download_link.short_description = _('Invoice File')

    def save_model(self, request, obj, form, change):
        """Automatically set created_by on creation"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
