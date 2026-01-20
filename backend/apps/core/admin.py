from django.contrib import admin
from .models import BusinessType, GlobalSettings

@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['order', 'name']

@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Eğer zaten bir kayıt varsa eklemeye izin verme
        if self.model.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # Silmeye izin verme
        return False
        
    fieldsets = (
        ('System Status', {'fields': ('maintenance_mode',)}),
        ('General', {'fields': ('system_currency', 'support_email', 'contact_phone', 'website_url')}),
        ('Legal', {'fields': ('terms_url', 'privacy_url')}),
    )