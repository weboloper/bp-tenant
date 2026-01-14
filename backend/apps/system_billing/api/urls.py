"""
System Billing API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, InvoiceViewSet, SubscriptionPlanViewSet

app_name = 'system_billing'

router = DefaultRouter()
router.register('payments', PaymentViewSet, basename='payment')
router.register('invoices', InvoiceViewSet, basename='invoice')
router.register('plans', SubscriptionPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
]
