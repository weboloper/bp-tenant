"""
Tenants app signals.

Note: Default permission creation has been moved to staff.signals
to avoid circular imports between tenants and staff modules.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='tenants.Company')
def provision_tenant_defaults(sender, instance, created, **kwargs):
    """
    Provision default settings when a new company is created.
    """
    if created:
        from tenants.services.provisioning import TenantProvisioningService
        TenantProvisioningService.provision(instance)
