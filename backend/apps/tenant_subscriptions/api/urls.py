from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantSubscriptionViewSet, SmsBalanceViewSet

app_name = 'tenant_subscriptions_api'

router = DefaultRouter()
router.register(r'subscriptions', TenantSubscriptionViewSet, basename='subscription')
router.register(r'sms', SmsBalanceViewSet, basename='sms')

urlpatterns = [
    path('', include(router.urls)),
]
