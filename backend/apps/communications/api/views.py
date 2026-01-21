from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from communications.models import (
    OutboundMessage,
    Notification,
    MessageTemplate,
    NotificationTemplate,
    NotificationPreference,
    DeliveryLog,
)
from communications.services.messaging import MessagingService
from billing.services import SmsService, InsufficientSmsCredit
from tenants.api.permissions import IsCompanyMember
from .serializers import (
    SendSMSSerializer,
    BulkSMSSerializer,
    SMSCreditCalculateSerializer,
    SMSCreditCalculateResponseSerializer,
    OutboundMessageSerializer,
    OutboundMessageListSerializer,
    NotificationSerializer,
    NotificationListSerializer,
    NotificationMarkReadSerializer,
    MessageTemplateSerializer,
    NotificationTemplateSerializer,
    TemplateRenderSerializer,
    NotificationPreferenceSerializer,
    DeliveryLogSerializer,
)


# ============================================================================
# SMS ViewSet
# ============================================================================

class SMSViewSet(viewsets.GenericViewSet):
    """
    SMS operations ViewSet

    Endpoints:
    - POST /sms/send/          - Send single SMS
    - POST /sms/bulk/          - Send bulk SMS
    - GET  /sms/balance/       - Get SMS credit balance
    - POST /sms/calculate/     - Calculate credits for message
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_serializer_class(self):
        if self.action == 'send':
            return SendSMSSerializer
        elif self.action == 'bulk':
            return BulkSMSSerializer
        elif self.action == 'calculate':
            return SMSCreditCalculateSerializer
        return SendSMSSerializer

    @action(detail=False, methods=['post'])
    def send(self, request):
        """
        Send SMS to single recipient.

        POST /api/v1/communications/sms/send/
        {
            "phone": "+905551234567",
            "message": "Hello World",
            "message_type": "transactional",
            "sender_id": "MYCOMPANY"
        }
        """
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request, 'company', None)
        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            message = MessagingService.send_sms(
                tenant=tenant,
                phone=serializer.validated_data['phone'],
                message=serializer.validated_data['message'],
                message_type=serializer.validated_data.get('message_type', 'transactional'),
                sender_id=serializer.validated_data.get('sender_id'),
                user=request.user
            )

            return Response({
                'success': True,
                'message_id': message.id,
                'status': message.status,
                'credits_used': message.credits_used,
            }, status=status.HTTP_201_CREATED)

        except InsufficientSmsCredit as e:
            return Response({
                'success': False,
                'error': str(e),
                'balance': SmsService.get_balance(tenant)
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """
        Send SMS to multiple recipients.

        POST /api/v1/communications/sms/bulk/
        {
            "recipients": ["+905551234567", "+905559876543"],
            "message": "Hello World",
            "message_type": "promotional"
        }
        """
        serializer = BulkSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request, 'company', None)
        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = MessagingService.send_bulk_sms(
                tenant=tenant,
                recipients=serializer.validated_data['recipients'],
                message=serializer.validated_data['message'],
                message_type=serializer.validated_data.get('message_type', 'promotional'),
                sender_id=serializer.validated_data.get('sender_id'),
                user=request.user
            )

            return Response(result, status=status.HTTP_201_CREATED)

        except InsufficientSmsCredit as e:
            return Response({
                'success': False,
                'error': str(e),
                'balance': SmsService.get_balance(tenant)
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        Get current SMS credit balance.

        GET /api/v1/communications/sms/balance/
        """
        tenant = getattr(request, 'company', None)
        if not tenant:
            return Response(
                {'error': _('User is not associated with any company')},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'balance': SmsService.get_balance(tenant),
            'has_credits': SmsService.has_sufficient_balance(tenant, 1)
        })

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate credits needed for a message.

        POST /api/v1/communications/sms/calculate/
        {
            "message": "Hello World with Turkish chars: ğüşıöç"
        }
        """
        serializer = SMSCreditCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data['message']
        credits = MessagingService.calculate_message_credits(message)

        # Detect encoding
        has_turkish = any(c in message for c in 'ğüşıöçĞÜŞİÖÇ')
        encoding = 'unicode' if has_turkish else 'gsm7'
        chars_per_part = 70 if has_turkish else 160

        return Response({
            'credits': credits,
            'char_count': len(message),
            'parts': credits,
            'encoding': encoding,
            'chars_per_part': chars_per_part
        })


# ============================================================================
# OutboundMessage ViewSet
# ============================================================================

class OutboundMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Outbound messages (SMS/WhatsApp) ViewSet - Read only

    Endpoints:
    - GET /messages/            - List messages
    - GET /messages/{id}/       - Get message details
    - POST /messages/{id}/retry/ - Retry failed message
    - GET /messages/{id}/status/ - Check delivery status
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]
    filterset_fields = ['status', 'channel', 'message_type']
    search_fields = ['recipient_phone', 'content']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = getattr(self.request, 'company', None)
        if tenant:
            return OutboundMessage.objects.filter(company=tenant).select_related('company')
        return OutboundMessage.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return OutboundMessageListSerializer
        return OutboundMessageSerializer

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """
        Retry sending a failed message.

        POST /api/v1/communications/messages/{id}/retry/
        """
        message = self.get_object()

        if not message.can_retry:
            return Response({
                'error': _('This message cannot be retried'),
                'status': message.status,
                'retry_count': message.retry_count,
                'max_retries': message.max_retries
            }, status=status.HTTP_400_BAD_REQUEST)

        tenant = getattr(request, 'company', None)

        try:
            # Resend
            new_message = MessagingService.send_sms(
                tenant=tenant,
                phone=message.recipient_phone,
                message=message.content,
                message_type=message.message_type,
                user=request.user,
                metadata={'retry_of': message.id}
            )

            # Update original message
            message.retry_count += 1
            message.save()

            return Response({
                'success': True,
                'original_message_id': message.id,
                'new_message_id': new_message.id,
                'status': new_message.status
            })

        except InsufficientSmsCredit as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

    @action(detail=True, methods=['get'], url_path='status')
    def delivery_status(self, request, pk=None):
        """
        Check delivery status from provider.

        GET /api/v1/communications/messages/{id}/status/
        """
        message = self.get_object()
        updated_message = MessagingService.get_delivery_status(message)

        return Response({
            'message_id': updated_message.id,
            'status': updated_message.status,
            'sent_at': updated_message.sent_at,
            'delivered_at': updated_message.delivered_at,
            'error_message': updated_message.error_message
        })


# ============================================================================
# Notification ViewSet
# ============================================================================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User notifications ViewSet

    Endpoints:
    - GET /notifications/                - List user notifications
    - GET /notifications/{id}/           - Get notification details
    - POST /notifications/mark-read/     - Mark notifications as read
    - GET /notifications/unread-count/   - Get unread count
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'notification_type', 'priority']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(
            recipient_user=user
        ).select_related('sender_company', 'sender_user')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """
        Mark notifications as read.

        POST /api/v1/communications/notifications/mark-read/
        {
            "notification_ids": [1, 2, 3]  // Optional, if empty marks all as read
        }
        """
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get('notification_ids', [])
        queryset = self.get_queryset().exclude(status='read')

        if notification_ids:
            queryset = queryset.filter(id__in=notification_ids)

        count = queryset.update(
            status='read',
            read_at=timezone.now()
        )

        return Response({
            'marked_count': count
        })

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        Get unread notification count.

        GET /api/v1/communications/notifications/unread-count/
        """
        count = self.get_queryset().exclude(status='read').count()

        return Response({
            'unread_count': count
        })

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_single_read(self, request, pk=None):
        """
        Mark single notification as read.

        POST /api/v1/communications/notifications/{id}/mark-read/
        """
        notification = self.get_object()
        notification.mark_as_read()

        return Response({
            'success': True,
            'notification_id': notification.id,
            'read_at': notification.read_at
        })


# ============================================================================
# Template ViewSets
# ============================================================================

class MessageTemplateViewSet(viewsets.ModelViewSet):
    """
    Message templates ViewSet (SMS/WhatsApp)

    Endpoints:
    - GET /templates/messages/           - List templates
    - POST /templates/messages/          - Create template
    - GET /templates/messages/{id}/      - Get template
    - PUT /templates/messages/{id}/      - Update template
    - DELETE /templates/messages/{id}/   - Delete template
    - POST /templates/messages/{id}/render/ - Render template
    """
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    filterset_fields = ['is_active', 'sms_enabled', 'whatsapp_enabled']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']

    def get_queryset(self):
        tenant = getattr(self.request, 'company', None)
        if tenant:
            return MessageTemplate.objects.filter(company=tenant)
        return MessageTemplate.objects.none()

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'company', None)
        serializer.save(company=tenant)

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """
        Render template with context.

        POST /api/v1/communications/templates/messages/{id}/render/
        {
            "context": {"customer_name": "John", "date": "2024-01-15"},
            "channel": "sms"  // optional
        }
        """
        template = self.get_object()
        serializer = TemplateRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        context = serializer.validated_data['context']
        channel = serializer.validated_data.get('channel')

        if channel:
            rendered = template.render(channel, context)
            return Response({
                'channel': channel,
                'rendered': rendered
            })
        else:
            # Render all enabled channels
            result = {}
            for ch in template.get_enabled_channels():
                result[ch] = template.render(ch, context)
            return Response({'rendered': result})


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    Notification templates ViewSet

    Endpoints:
    - GET /templates/notifications/           - List templates
    - POST /templates/notifications/          - Create template
    - GET /templates/notifications/{id}/      - Get template
    - PUT /templates/notifications/{id}/      - Update template
    - DELETE /templates/notifications/{id}/   - Delete template
    - POST /templates/notifications/{id}/render/ - Render template
    """
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    filterset_fields = ['is_active', 'notification_type', 'is_system_template']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']

    def get_queryset(self):
        tenant = getattr(self.request, 'company', None)
        if tenant:
            # Include system templates + company templates
            return NotificationTemplate.objects.filter(
                models.Q(company=tenant) | models.Q(is_system_template=True)
            )
        return NotificationTemplate.objects.filter(is_system_template=True)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'company', None)
        serializer.save(company=tenant, is_system_template=False)

    def perform_update(self, serializer):
        # Don't allow editing system templates
        if serializer.instance.is_system_template:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("System templates cannot be modified"))
        serializer.save()

    def perform_destroy(self, instance):
        # Don't allow deleting system templates
        if instance.is_system_template:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("System templates cannot be deleted"))
        instance.delete()

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """
        Render notification template with context.

        POST /api/v1/communications/templates/notifications/{id}/render/
        {
            "context": {"customer_name": "John", "appointment_time": "14:00"}
        }
        """
        template = self.get_object()
        serializer = TemplateRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        context = serializer.validated_data['context']
        rendered = template.render(context)

        return Response({'rendered': rendered})


# ============================================================================
# Preference ViewSet
# ============================================================================

class NotificationPreferenceViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    User notification preferences ViewSet

    Endpoints:
    - GET /preferences/me/     - Get my preferences
    - PUT /preferences/me/     - Update my preferences
    - PATCH /preferences/me/   - Partial update preferences
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get or create preferences for current user"""
        preference, _ = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """
        Get or update current user's notification preferences.

        GET/PUT/PATCH /api/v1/communications/preferences/me/
        """
        preference = self.get_object()

        if request.method == 'GET':
            serializer = self.get_serializer(preference)
            return Response(serializer.data)

        partial = request.method == 'PATCH'
        serializer = self.get_serializer(preference, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


# ============================================================================
# Delivery Log ViewSet
# ============================================================================

class DeliveryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Delivery logs ViewSet - Read only

    Endpoints:
    - GET /logs/           - List delivery logs
    - GET /logs/{id}/      - Get log details
    """
    serializer_class = DeliveryLogSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    filterset_fields = ['status', 'channel', 'provider_name']
    search_fields = ['recipient', 'message_id']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = getattr(self.request, 'company', None)
        if tenant:
            return DeliveryLog.objects.filter(company=tenant)
        return DeliveryLog.objects.none()
