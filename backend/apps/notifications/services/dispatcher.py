# notifications/services/dispatcher.py

import logging
from typing import Optional, Dict, Any, List, Union
from django.conf import settings
from django.db import transaction

from notifications.models import NotificationTemplate, NotificationPreference
from notifications.constants import Channel, NotificationType
from notifications.channels import get_channel
from providers.registry import get_email_backend, get_sms_backend

logger = logging.getLogger(__name__)


# =============================================================================
# LOW-LEVEL SEND FUNCTIONS (direct provider access)
# =============================================================================

def send_email(to: str, subject: str, body: str, sync: bool = False, **kwargs) -> Any:
    """
    Send email. Uses Celery if CELERY_ENABLED=True, otherwise sync.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (HTML or plain text)
        sync: Force synchronous sending (default: False)
        **kwargs: Additional backend-specific options

    Returns:
        Task result (async) or send result (sync)
    """
    if getattr(settings, 'CELERY_ENABLED', False) and not sync:
        from notifications.tasks import send_email_task
        return send_email_task.delay(to, subject, body, **kwargs)
    else:
        backend = get_email_backend()
        return backend.send(to=to, subject=subject, body=body, **kwargs)


def send_sms(to: str, message: str, sync: bool = False, **kwargs) -> Any:
    """
    Send SMS. Uses Celery if CELERY_ENABLED=True, otherwise sync.

    Args:
        to: Recipient phone number
        message: SMS message content
        sync: Force synchronous sending (default: False)
        **kwargs: Additional backend-specific options

    Returns:
        Task result (async) or send result (sync)
    """
    if getattr(settings, 'CELERY_ENABLED', False) and not sync:
        from notifications.tasks import send_sms_task
        return send_sms_task.delay(to, message, **kwargs)
    else:
        backend = get_sms_backend()
        return backend.send(to=to, message=message, **kwargs)


# =============================================================================
# NOTIFICATION DISPATCHER (template-based)
# =============================================================================


class NotificationDispatcher:
    """
    Central notification dispatcher - TEK ENTRY POINT
    
    Usage:
        notify(
            code="appointment_reminder",
            tenant=company,
            recipient=client,
            context={"date": "15 Ocak", "time": "14:00"}
        )
    """
    
    @classmethod
    def notify(
        cls,
        code: str,
        tenant,
        recipient,  # Client veya User
        context: Dict[str, Any],
        channels: Optional[List[str]] = None,
        sent_by=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send notification through appropriate channels
        
        Args:
            code: Template code (e.g., "appointment_reminder")
            tenant: Company instance
            recipient: Client or User instance
            context: Template variables
            channels: Override channels (optional, uses template if None)
            sent_by: User who triggered notification
            
        Returns:
            {
                "success": bool,
                "channels": {
                    "sms": {"success": bool, ...},
                    "email": {"success": bool, ...},
                    "in_app": {"success": bool, ...}
                }
            }
        """
        # Get template (tenant override first, then system)
        template = cls._get_template(code, tenant)
        
        if not template:
            logger.warning(f"Template not found: {code}")
            return {'success': False, 'error': f'Template not found: {code}'}
        
        # Determine channels
        if channels:
            active_channels = [c for c in channels if c in template.get_enabled_channels()]
        else:
            active_channels = template.get_enabled_channels()
        
        if not active_channels:
            return {'success': False, 'error': 'No active channels'}
        
        # Determine recipient type and info
        recipient_info = cls._resolve_recipient(recipient)
        
        results = {'channels': {}}
        any_success = False
        
        for channel in active_channels:
            # Check if we can send via this channel
            if not cls._can_send(channel, recipient_info):
                results['channels'][channel] = {
                    'success': False,
                    'error': f'Cannot send {channel} to this recipient'
                }
                continue
            
            # Render template for this channel
            rendered = template.render(channel, context)
            
            if not rendered:
                results['channels'][channel] = {
                    'success': False,
                    'error': 'Template rendering failed'
                }
                continue
            
            # Get channel instance and send
            channel_instance = get_channel(channel)
            
            result = cls._send_via_channel(
                channel=channel,
                channel_instance=channel_instance,
                recipient_info=recipient_info,
                rendered=rendered,
                template=template,
                tenant=tenant,
                sent_by=sent_by,
                **kwargs
            )
            
            results['channels'][channel] = result
            if result.get('success'):
                any_success = True
        
        results['success'] = any_success
        return results
    
    @classmethod
    def notify_user(
        cls,
        user,
        notification_type: str,
        title: str,
        message: str,
        tenant=None,
        sender_user=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Direct in-app notification to user (without template)
        
        For simple notifications where template is overkill
        """
        channel_instance = get_channel(Channel.IN_APP)
        
        return channel_instance.send(
            recipient=user,
            content={'title': title, 'message': message},
            tenant=tenant,
            sender_user=sender_user,
            notification_type=notification_type,
            **kwargs
        )
    
    @classmethod
    def notify_tenant_users(
        cls,
        tenant,
        notification_type: str,
        title: str,
        message: str,
        exclude_user=None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Send in-app notification to all tenant users
        """
        from tenants.models import CompanyMembership
        
        memberships = CompanyMembership.objects.filter(
            company=tenant,
            is_active=True
        ).select_related('user')
        
        results = []
        for membership in memberships:
            if exclude_user and membership.user == exclude_user:
                continue
            
            result = cls.notify_user(
                user=membership.user,
                notification_type=notification_type,
                title=title,
                message=message,
                tenant=tenant,
                **kwargs
            )
            results.append(result)
        
        return results
    
    @classmethod
    def system_notify_user(
        cls,
        user,
        notification_type: str,
        title: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        System → User notification
        """
        return cls.notify_user(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            tenant=None,  # System
            **kwargs
        )
    
    # ===== PRIVATE METHODS =====
    
    @classmethod
    def _get_template(cls, code: str, tenant) -> Optional[NotificationTemplate]:
        """Get template with tenant override support"""
        # Try tenant-specific first
        template = NotificationTemplate.objects.filter(
            company=tenant,
            code=code,
            is_active=True
        ).first()
        
        if template:
            return template
        
        # Fall back to system template
        return NotificationTemplate.objects.filter(
            company__isnull=True,
            code=code,
            is_active=True
        ).first()
    
    @classmethod
    def _resolve_recipient(cls, recipient) -> Dict[str, Any]:
        """
        Extract recipient info from Client or User
        """
        # Check if it's a Client
        if hasattr(recipient, 'phone') and hasattr(recipient, 'email') and hasattr(recipient, 'full_name'):
            # It's a Client
            return {
                'type': 'client',
                'instance': recipient,
                'phone': str(recipient.phone) if recipient.phone else None,
                'email': recipient.email,
                'name': recipient.full_name,
                'user': recipient.user if hasattr(recipient, 'user') else None
            }
        
        # It's a User
        return {
            'type': 'user',
            'instance': recipient,
            'phone': getattr(recipient, 'phone', None),
            'email': recipient.email,
            'name': recipient.get_full_name() or recipient.username,
            'user': recipient
        }
    
    @classmethod
    def _can_send(cls, channel: str, recipient_info: Dict) -> bool:
        """Check if we can send via this channel"""
        if channel == Channel.SMS:
            return bool(recipient_info.get('phone'))
        elif channel == Channel.EMAIL:
            return bool(recipient_info.get('email'))
        elif channel == Channel.IN_APP:
            # Only users can receive in-app
            return recipient_info.get('user') is not None
        return False
    
    @classmethod
    def _send_via_channel(
        cls,
        channel: str,
        channel_instance,
        recipient_info: Dict,
        rendered: Dict,
        template: NotificationTemplate,
        tenant,
        sent_by,
        **kwargs
    ) -> Dict[str, Any]:
        """Send through specific channel"""
        
        if channel == Channel.SMS:
            return channel_instance.send(
                recipient=recipient_info['phone'],
                content=rendered,
                tenant=tenant,
                client=recipient_info['instance'] if recipient_info['type'] == 'client' else None,
                sent_by=sent_by,
                notification_type=template.notification_type,
                **kwargs
            )
        
        elif channel == Channel.EMAIL:
            return channel_instance.send(
                recipient=recipient_info['email'],
                content=rendered,
                tenant=tenant,
                client=recipient_info['instance'] if recipient_info['type'] == 'client' else None,
                sent_by=sent_by,
                notification_type=template.notification_type,
                **kwargs
            )
        
        elif channel == Channel.IN_APP:
            user = recipient_info.get('user')
            if not user:
                return {'success': False, 'error': 'No user for in-app'}
            
            return channel_instance.send(
                recipient=user,
                content=rendered,
                tenant=tenant,
                sender_user=sent_by,
                notification_type=template.notification_type,
                priority=template.default_priority,
                **kwargs
            )
        
        return {'success': False, 'error': f'Unknown channel: {channel}'}


# Convenience function
def notify(
    code: str,
    tenant,
    recipient,
    context: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    Shortcut for NotificationDispatcher.notify()
    
    Usage:
        from notifications.services import notify
        
        notify(
            code="appointment_reminder",
            tenant=company,
            recipient=client,
            context={"date": "15 Ocak", "time": "14:00"}
        )
    """
    return NotificationDispatcher.notify(
        code=code,
        tenant=tenant,
        recipient=recipient,
        context=context,
        **kwargs
    )