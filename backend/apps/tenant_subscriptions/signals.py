from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from tenants.models import Company
from system_subscriptions.models import SubscriptionPlan
from .models import TenantSubscription, SmsBalance


@receiver(post_save, sender=Company)
def create_default_subscription_and_sms_balance(sender, instance, created, **kwargs):
    """
    Automatically create default subscription for new companies
    """
    if created:
        # Get or create Free/Basic plan
        default_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'price': 0,
                'billing_cycle': 'monthly',
                'max_employee': 2,
                'max_locations': 1,
                'max_appointments_per_month': 100,
                'has_online_booking': True,
                'has_sms_notifications': False,
                'has_analytics': False,
                'is_active': True,
            }
        )

        # Create subscription (1 year trial)
        TenantSubscription.objects.create(
            tenant=instance,
            plan=default_plan,
            status='active',
            expires_at=timezone.now() + timedelta(days=365),
            original_price=default_plan.price,
            discounted_price=default_plan.price,
            notes='Automatically created trial subscription'
        )

        # Create SMS balance for the company
        SmsBalance.objects.get_or_create(
            tenant=instance,
            defaults={'balance': 0}
        )
