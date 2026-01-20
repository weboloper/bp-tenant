import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tenants.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()

# Get companies and their owners
companies = Company.objects.filter(name__in=['Company A', 'Company B'])
owners = list(companies.values_list('owner_id', flat=True))
employees_ids = []
for company in companies:
    employees_ids.extend(company.employees.values_list('user_id', flat=True))

# Delete companies
companies.delete()

# Delete owners and employees
User.objects.filter(id__in=owners + list(employees_ids)).delete()
User.objects.filter(email='nocompany@test.com').delete()

print("Cleaned up test data successfully")
