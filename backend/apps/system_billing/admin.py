from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Payment, Invoice


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
