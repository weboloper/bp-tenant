from django.db.models.signals import post_save
from django.dispatch import receiver
from tenants.models import Company
from .models import SmsBalance


@receiver(post_save, sender=Company)
def create_sms_balance(sender, instance, created, **kwargs):
    """
    Automatically create SMS balance for new companies
    """
    if created:
        SmsBalance.objects.get_or_create(
            tenant=instance,
            defaults={'balance': 0}
        )
