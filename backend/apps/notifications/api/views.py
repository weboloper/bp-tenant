# notifications/api/views.py

from rest_framework import viewsets, views, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationPreference,
    OutboundMessage,
)
from notifications.services import notify, NotificationDispatcher
from notifications.constants import Channel
from core.mixins import PlanFeatureRequiredMixin

from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    MarkReadSerializer,
    OutboundMessageSerializer,
    OutboundMessageListSerializer,
    NotificationTemplateSerializer,
    NotificationTemplateListSerializer,
    NotificationPreferenceSerializer,
    SendNotificationSerializer,
    SendDirectSMSSerializer,
    SendDirectEmailSerializer,
    SMSBalanceSerializer,
    SMSCalculateSerializer,
    SMSCalculateResponseSerializer,
)


# ==================== NOTIFICATION ====================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User's in-app notifications

    list: Get all notifications for current user
    retrieve: Get notification detail
    mark_read: Mark notifications as read
    unread_count: Get count of unread notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender_company', 'sender_user')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark notifications as read"""
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get('notification_ids', [])

        qs = self.get_queryset().filter(is_read=False)
        if notification_ids:
            qs = qs.filter(id__in=notification_ids)

        count = qs.update(is_read=True, read_at=timezone.now())

        return Response({'marked_count': count})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark single notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'success': True})


# ==================== OUTBOUND MESSAGE ====================

class OutboundMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Tenant's outbound message history (SMS/Email)

    list: Get all outbound messages for tenant
    retrieve: Get message detail
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OutboundMessageSerializer

    def get_queryset(self):
        # Tenant filtering via middleware/mixin
        qs = OutboundMessage.objects.all()

        # Apply filters
        channel = self.request.query_params.get('channel')
        status_filter = self.request.query_params.get('status')
        client_id = self.request.query_params.get('client_id')

        if channel:
            qs = qs.filter(channel=channel)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if client_id:
            qs = qs.filter(client_id=client_id)

        return qs.select_related('client', 'sent_by').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return OutboundMessageListSerializer
        return OutboundMessageSerializer


# ==================== TEMPLATE ====================

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    Tenant notification templates CRUD

    Templates with company=null are system defaults (read-only).
    Tenant can create overrides with same code.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        # Get tenant from request (set by middleware)
        tenant = getattr(self.request, 'tenant', None)

        # Show system templates + tenant templates
        return NotificationTemplate.objects.filter(
            Q(company__isnull=True) | Q(company=tenant)
        ).order_by('code')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationTemplateListSerializer
        return NotificationTemplateSerializer

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(company=tenant)

    def perform_update(self, serializer):
        # Prevent editing system templates
        if serializer.instance.company is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot edit system templates")
        serializer.save()

    def perform_destroy(self, instance):
        # Prevent deleting system templates
        if instance.company is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot delete system templates")
        instance.delete()


# ==================== PREFERENCE ====================

class PreferenceView(views.APIView):
    """
    User notification preferences

    GET: Get current preferences
    PUT/PATCH: Update preferences
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(pref)
        return Response(serializer.data)

    def put(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(pref, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            pref, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ==================== SEND NOTIFICATION ====================

class SendNotificationView(views.APIView):
    """
    Send notification using template

    POST: Send notification via notify()
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Tenant context required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = notify(
            code=serializer.validated_data['code'],
            tenant=tenant,
            recipient=serializer.validated_data['recipient'],
            context=serializer.validated_data.get('context', {}),
            channels=serializer.validated_data.get('channels'),
            sent_by=request.user
        )

        return Response(result)


class SendDirectSMSView(PlanFeatureRequiredMixin, views.APIView):
    """Send SMS directly without template"""
    permission_classes = [permissions.IsAuthenticated]
    required_module = 'sms'

    def post(self, request):
        serializer = SendDirectSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Tenant context required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from notifications.channels import get_channel
        from clients.models import Client

        client = None
        client_id = serializer.validated_data.get('client_id')
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                pass

        channel = get_channel(Channel.SMS)
        result = channel.send(
            recipient=serializer.validated_data['phone'],
            content={'content': serializer.validated_data['message']},
            tenant=tenant,
            client=client,
            sent_by=request.user,
            notification_type='custom'
        )

        return Response(result)


class SendDirectEmailView(PlanFeatureRequiredMixin, views.APIView):
    """Send email directly without template"""
    permission_classes = [permissions.IsAuthenticated]
    required_module = 'email'

    def post(self, request):
        serializer = SendDirectEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Tenant context required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from notifications.channels import get_channel
        from clients.models import Client

        client = None
        client_id = serializer.validated_data.get('client_id')
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                pass

        channel = get_channel(Channel.EMAIL)
        result = channel.send(
            recipient=serializer.validated_data['email'],
            content={
                'subject': serializer.validated_data['subject'],
                'body_text': serializer.validated_data['body_text'],
                'body_html': serializer.validated_data.get('body_html', ''),
            },
            tenant=tenant,
            client=client,
            sent_by=request.user,
            notification_type='custom'
        )

        return Response(result)


# ==================== SMS UTILITIES ====================

class SMSBalanceView(views.APIView):
    """Get SMS balance for tenant"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Tenant context required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from billing.services import SmsService
        from providers.sms import get_sms_provider

        # Tenant credits
        tenant_credits = SmsService.get_balance(tenant)

        # Provider balance (optional)
        try:
            provider = get_sms_provider()
            provider_balance = provider.get_balance()
        except Exception:
            provider_balance = {'error': 'Could not fetch provider balance'}

        return Response({
            'tenant_credits': tenant_credits,
            'provider_balance': provider_balance
        })


class SMSCalculateView(views.APIView):
    """Calculate SMS credits for a message"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SMSCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data['message']

        from providers.sms import get_sms_provider

        provider = get_sms_provider()
        credits = provider.calculate_credits(message)

        # Check for Turkish characters
        turkish_chars = set('çÇğĞıİöÖşŞüÜ')
        has_turkish = bool(turkish_chars.intersection(set(message)))

        return Response({
            'message_length': len(message),
            'credits_needed': credits,
            'encoding': 'UCS2' if has_turkish else 'GSM7',
            'has_turkish_chars': has_turkish
        })
