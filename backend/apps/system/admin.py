from django.contrib import admin
from .models import BusinessType, DefaultPaymentMethod


@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']


@admin.register(DefaultPaymentMethod)
class DefaultPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'name']
