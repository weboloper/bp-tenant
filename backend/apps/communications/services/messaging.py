"""
Messaging Service - High-level SMS/messaging operations

Integrates with:
- SMS providers (NetGSM, Mock)
- Tenant SMS credits (billing.SmsService)
- Message logging (OutboundMessage model)
"""
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from communications.models import OutboundMessage
from communications.providers import (
    BaseSMSProvider,
    NetGSMProvider,
    MockSMSProvider,
    SMSResult,
    BulkSMSResult,
    SMSStatus
)
from billing.services import SmsService, InsufficientSmsCredit

logger = logging.getLogger(__name__)


class MessagingService:
    """
    High-level messaging service.

    Handles:
    - Provider selection (NetGSM vs Mock)
    - Credit management (check & deduct)
    - Message logging
    - Error handling
    """

    @staticmethod
    def get_provider() -> BaseSMSProvider:
        """
        Get appropriate SMS provider based on settings.

        Returns:
            SMS provider instance (NetGSM or Mock)
        """
        use_mock = getattr(settings, 'USE_MOCK_SMS', settings.DEBUG)
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'mock')

        if use_mock or sms_provider == 'mock':
            logger.debug("Using MockSMSProvider")
            return MockSMSProvider()
        else:
            logger.debug("Using NetGSMProvider")
            return NetGSMProvider()

    @classmethod
    @transaction.atomic
    def send_sms(
        cls,
        tenant,
        phone: str,
        message: str,
        message_type: str = 'transactional',
        sender_id: Optional[str] = None,
        notification=None,
        metadata: Optional[Dict[str, Any]] = None,
        user=None
    ) -> OutboundMessage:
        """
        Send SMS to a single recipient.

        Handles credit checking, deduction, and message logging.

        Args:
            tenant: Company instance
            phone: Recipient phone number
            message: Message content
            message_type: 'transactional', 'promotional', 'otp', 'notification'
            sender_id: Optional sender ID override
            notification: Optional linked Notification
            metadata: Additional data to store
            user: User who initiated the send

        Returns:
            OutboundMessage instance

        Raises:
            InsufficientSmsCredit: If tenant doesn't have enough credits
        """
        provider = cls.get_provider()

        # Calculate credits needed
        credits_needed = provider.calculate_credits(message)

        # Check credits
        if not SmsService.has_sufficient_balance(tenant, credits_needed):
            raise InsufficientSmsCredit(
                f"Yetersiz SMS kredisi. Gerekli: {credits_needed}, "
                f"Mevcut: {SmsService.get_balance(tenant)}"
            )

        # Create message record
        outbound_msg = OutboundMessage.objects.create(
            company=tenant,
            recipient_phone=provider.normalize_phone(phone),
            recipient_name='',
            content=message,
            channel='sms',
            message_type=message_type,
            status='pending',
            credits_used=credits_needed,
            notification=notification,
            metadata=metadata or {}
        )

        # Send via provider
        result = provider.send(phone, message, sender_id)

        # Update message record
        outbound_msg.provider_message_id = result.message_id or ''
        outbound_msg.provider_response = result.raw_response or {}

        if result.success:
            outbound_msg.status = 'sent'
            outbound_msg.sent_at = timezone.now()

            # Deduct credits in single transaction
            SmsService.deduct_credits_bulk(
                tenant=tenant,
                amount=credits_needed,
                description=f"SMS sent to {phone}" + (f" ({credits_needed} parts)" if credits_needed > 1 else ""),
                metadata={'message_id': outbound_msg.id},
                user=user
            )

            logger.info(f"SMS sent successfully to {phone}, ID: {result.message_id}")
        else:
            outbound_msg.status = 'failed'
            outbound_msg.error_message = result.error_message or ''
            logger.error(f"SMS send failed to {phone}: {result.error_message}")

        outbound_msg.save()
        return outbound_msg

    @classmethod
    @transaction.atomic
    def send_bulk_sms(
        cls,
        tenant,
        recipients: List[str],
        message: str,
        message_type: str = 'promotional',
        sender_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user=None
    ) -> Dict[str, Any]:
        """
        Send SMS to multiple recipients.

        Args:
            tenant: Company instance
            recipients: List of phone numbers
            message: Message content
            message_type: Message type
            sender_id: Optional sender ID override
            metadata: Additional data
            user: User who initiated the send

        Returns:
            Dict with batch results

        Raises:
            InsufficientSmsCredit: If tenant doesn't have enough credits
        """
        provider = cls.get_provider()

        # Calculate total credits needed
        credits_per_msg = provider.calculate_credits(message)
        total_credits = credits_per_msg * len(recipients)

        # Check credits
        if not SmsService.has_sufficient_balance(tenant, total_credits):
            raise InsufficientSmsCredit(
                f"Yetersiz SMS kredisi. Gerekli: {total_credits}, "
                f"Mevcut: {SmsService.get_balance(tenant)}"
            )

        # Send via provider
        result = provider.send_bulk(recipients, message, sender_id)

        # Create message records for successful sends
        messages_created = []
        for i, phone in enumerate(recipients):
            status = 'sent' if result.success else 'failed'
            if result.results and len(result.results) > i:
                status = 'sent' if result.results[i].success else 'failed'

            outbound_msg = OutboundMessage.objects.create(
                company=tenant,
                recipient_phone=provider.normalize_phone(phone),
                content=message,
                channel='sms',
                message_type=message_type,
                status=status,
                credits_used=credits_per_msg if status == 'sent' else 0,
                provider_message_id=result.batch_id or '',
                sent_at=timezone.now() if status == 'sent' else None,
                metadata={'batch_id': result.batch_id, **(metadata or {})}
            )
            messages_created.append(outbound_msg)

        # Deduct credits for successful sends in single transaction
        if result.credits_used > 0:
            SmsService.deduct_credits_bulk(
                tenant=tenant,
                amount=result.credits_used,
                description=f"Bulk SMS to {result.successful} recipients (batch: {result.batch_id})",
                metadata={'batch_id': result.batch_id, 'total': result.total, 'successful': result.successful},
                user=user
            )

        logger.info(
            f"Bulk SMS completed. Batch: {result.batch_id}, "
            f"Success: {result.successful}/{result.total}"
        )

        return {
            'success': result.success,
            'batch_id': result.batch_id,
            'total': result.total,
            'successful': result.successful,
            'failed': result.failed,
            'credits_used': result.credits_used,
            'messages': [m.id for m in messages_created]
        }

    @classmethod
    def get_delivery_status(cls, message: OutboundMessage) -> OutboundMessage:
        """
        Update delivery status for a sent message.

        Args:
            message: OutboundMessage to check

        Returns:
            Updated OutboundMessage
        """
        if not message.provider_message_id:
            return message

        provider = cls.get_provider()
        result = provider.get_delivery_report(message.provider_message_id)

        if result.success:
            # Map status
            status_map = {
                SMSStatus.PENDING: 'pending',
                SMSStatus.SENT: 'sent',
                SMSStatus.DELIVERED: 'delivered',
                SMSStatus.FAILED: 'failed',
                SMSStatus.REJECTED: 'rejected',
            }

            new_status = status_map.get(result.status, message.status)

            if new_status != message.status:
                message.status = new_status
                if new_status == 'delivered':
                    message.delivered_at = timezone.now()
                message.save()

                logger.info(
                    f"Message {message.id} status updated: {new_status}"
                )

        return message

    @classmethod
    def get_provider_balance(cls) -> Dict[str, Any]:
        """
        Get SMS provider account balance.

        Returns:
            Dict with provider balance info
        """
        provider = cls.get_provider()
        return provider.get_balance()

    @classmethod
    def calculate_message_credits(cls, message: str) -> int:
        """
        Calculate credits needed for a message.

        Args:
            message: Message content

        Returns:
            Number of credits required
        """
        provider = cls.get_provider()
        return provider.calculate_credits(message)

    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """
        Validate a phone number.

        Args:
            phone: Phone number to validate

        Returns:
            True if valid
        """
        provider = cls.get_provider()
        return provider.validate_phone(phone)
