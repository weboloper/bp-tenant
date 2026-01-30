from django.contrib import admin
from .models import (
    DefaultPaymentMethod,
)


class BaseDefaultAdmin(admin.ModelAdmin):
    """Base admin for platform defaults"""
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active']


@admin.register(DefaultPaymentMethod)
class DefaultPaymentMethodAdmin(BaseDefaultAdmin):
    list_display = ['name', 'code', 'icon', 'order', 'is_active']

