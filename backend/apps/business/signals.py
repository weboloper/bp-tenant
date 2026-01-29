# business/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from tenants.models import Company
from business.services.provisioning import TenantProvisioningService


@receiver(post_save, sender=Company)
def provision_tenant_defaults(sender, instance, created, **kwargs):
    """
    Provision default settings when a new company is created.
    """
    if created:
        TenantProvisioningService.provision(instance)