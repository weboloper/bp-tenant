from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SmsBalanceViewSet

app_name = 'tenant_resources_api'

router = DefaultRouter()
router.register(r'sms', SmsBalanceViewSet, basename='sms')

urlpatterns = [
    path('', include(router.urls)),
]
