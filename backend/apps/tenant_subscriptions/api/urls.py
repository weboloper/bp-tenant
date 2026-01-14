from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantSubscriptionViewSet

app_name = 'tenant_subscriptions_api'

router = DefaultRouter()
router.register(r'subscriptions', TenantSubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
]
