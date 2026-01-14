from django.apps import AppConfig


class TenantSubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenant_subscriptions'
    verbose_name = 'Tenant Subscriptions'

    def ready(self):
        import tenant_subscriptions.signals  # noqa
