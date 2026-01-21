from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantSubscriptionViewSet,
    SmsBalanceViewSet,
    PaymentViewSet,
    InvoiceViewSet,
    SubscriptionPlanViewSet,
)

app_name = 'billing'

router = DefaultRouter()
router.register(r'subscriptions', TenantSubscriptionViewSet, basename='subscription')
router.register(r'sms', SmsBalanceViewSet, basename='sms')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'plans', SubscriptionPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
]
