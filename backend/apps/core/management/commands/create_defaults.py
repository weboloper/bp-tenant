"""
Create platform default data
Usage: python manage.py create_defaults
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from system.models import DefaultPaymentMethod


class Command(BaseCommand):
    help = 'Create platform default data'

    def handle(self, *args, **options):

        self.create_payment_methods()

        self.stdout.write(
            self.style.SUCCESS('Successfully created all platform defaults')
        )

    
    def create_payment_methods(self):
        methods = [
            {'name': 'Cash', 'code': 'cash', 'icon': 'mdi-cash', 'order': 1},
            {'name': 'Credit Card', 'code': 'credit_card', 'icon': 'mdi-credit-card', 'order': 2},
            {'name': 'Debit Card', 'code': 'debit_card', 'icon': 'mdi-credit-card-outline', 'order': 3},
            {'name': 'Bank Transfer', 'code': 'bank_transfer', 'icon': 'mdi-bank-transfer', 'order': 4},
            {'name': 'Mobile Payment', 'code': 'mobile_payment', 'icon': 'mdi-cellphone', 'order': 5},
            {'name': 'Gift Card', 'code': 'gift_card', 'icon': 'mdi-gift', 'order': 6},
        ]
        created = 0
        for method in methods:
            _, is_created = DefaultPaymentMethod.objects.get_or_create(
                code=method['code'],
                defaults=method
            )
            if is_created:
                created += 1
        self.stdout.write(f'  Payment methods: {created} created')

