from django.apps import AppConfig


class TenantResourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenant_resources"
    verbose_name = "Tenant Resources"

    def ready(self):
        import tenant_resources.signals  # noqa
