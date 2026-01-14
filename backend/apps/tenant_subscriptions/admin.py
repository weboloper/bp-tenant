from django.contrib import admin
from .models import TenantSubscription, SubscriptionHistory


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
