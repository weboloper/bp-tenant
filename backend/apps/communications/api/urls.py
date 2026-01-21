from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SMSViewSet,
    OutboundMessageViewSet,
    NotificationViewSet,
    MessageTemplateViewSet,
    NotificationTemplateViewSet,
    NotificationPreferenceViewSet,
    DeliveryLogViewSet,
)

app_name = 'communications'

router = DefaultRouter()
router.register(r'sms', SMSViewSet, basename='sms')
router.register(r'messages', OutboundMessageViewSet, basename='message')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'message-templates', MessageTemplateViewSet, basename='message-template')
router.register(r'notification-templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')
router.register(r'delivery-logs', DeliveryLogViewSet, basename='delivery-log')

urlpatterns = [
    path('', include(router.urls)),
]
