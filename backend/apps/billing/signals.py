from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from tenants.models import Company
from billing.models import SubscriptionPlan, TenantSubscription, SmsBalance, SmsTransaction
from core.constants import DEFAULT_TRIAL_DAYS
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Company)
def create_default_subscription_and_sms_balance(sender, instance, created, **kwargs):
    """
    Automatically create default subscription and SMS balance for new companies.

    - Trial period: from core.constants.DEFAULT_TRIAL_DAYS
    - Welcome SMS bonus: from SubscriptionPlan.welcome_sms_bonus
    """
    if created:
        # Get the default plan (active plan with lowest sort_order)
        default_plan = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order').first()

        if not default_plan:
            logger.warning(f"No active subscription plan found. Tenant {instance.name} (ID: {instance.id}) created without subscription.")
            return

        # Create subscription with trial period
        TenantSubscription.objects.create(
            tenant=instance,
            plan=default_plan,
            status='active',
            expires_at=timezone.now() + timedelta(days=DEFAULT_TRIAL_DAYS),
            original_price=default_plan.price,
            discounted_price=default_plan.price,
            notes=f'Automatically created trial subscription ({DEFAULT_TRIAL_DAYS} days)'
        )

        # Get welcome bonus from plan
        welcome_bonus = default_plan.welcome_sms_bonus

        # Create SMS balance with welcome bonus
        _, balance_created = SmsBalance.objects.get_or_create(
            tenant=instance,
            defaults={'balance': welcome_bonus}
        )

        # Record bonus transaction if newly created
        if balance_created and welcome_bonus > 0:
            SmsTransaction.objects.create(
                tenant=instance,
                transaction_type='bonus',
                amount=welcome_bonus,
                balance_after=welcome_bonus,
                description='Hoşgeldin SMS bonusu / Welcome SMS bonus'
            )
