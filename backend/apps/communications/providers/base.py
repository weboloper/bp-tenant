"""
Base SMS Provider - Abstract base class for all SMS providers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import re


class SMSStatus(Enum):
    """SMS delivery status codes"""
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    REJECTED = 'rejected'
    EXPIRED = 'expired'
    UNKNOWN = 'unknown'


@dataclass
class SMSResult:
    """Result of a single SMS send operation"""
    success: bool
    message_id: Optional[str] = None
    status: SMSStatus = SMSStatus.PENDING
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    credits_used: int = 1
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message_id': self.message_id,
            'status': self.status.value,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'credits_used': self.credits_used,
            'raw_response': self.raw_response,
        }


@dataclass
class BulkSMSResult:
    """Result of a bulk SMS send operation"""
    success: bool
    batch_id: Optional[str] = None
    total: int = 0
    successful: int = 0
    failed: int = 0
    credits_used: int = 0
    results: List[SMSResult] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'batch_id': self.batch_id,
            'total': self.total,
            'successful': self.successful,
            'failed': self.failed,
            'credits_used': self.credits_used,
            'results': [r.to_dict() for r in self.results],
            'error_message': self.error_message,
        }


class BaseSMSProvider(ABC):
    """
    Abstract base class for SMS providers.

    All SMS providers (NetGSM, Twilio, etc.) must implement this interface.
    """

    # Turkish characters for SMS length calculation
    TURKISH_CHARS = set('çÇğĞıİöÖşŞüÜ')

    # SMS length limits
    GSM7_SINGLE_LIMIT = 160
    GSM7_CONCAT_LIMIT = 153
    UCS2_SINGLE_LIMIT = 70
    UCS2_CONCAT_LIMIT = 67

    @abstractmethod
    def send(
        self,
        phone: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> SMSResult:
        """
        Send a single SMS message.

        Args:
            phone: Recipient phone number (10 digits, no country code)
            message: Message content
            sender_id: Optional sender ID (alpha-numeric)

        Returns:
            SMSResult with send status
        """
        pass

    @abstractmethod
    def send_bulk(
        self,
        recipients: List[str],
        message: str,
        sender_id: Optional[str] = None
    ) -> BulkSMSResult:
        """
        Send SMS to multiple recipients.

        Args:
            recipients: List of phone numbers
            message: Message content (same for all)
            sender_id: Optional sender ID

        Returns:
            BulkSMSResult with batch status
        """
        pass

    @abstractmethod
    def get_delivery_report(self, message_id: str) -> SMSResult:
        """
        Get delivery status for a sent message.

        Args:
            message_id: Provider's message ID

        Returns:
            SMSResult with current status
        """
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance/credits from provider.

        Returns:
            Dict with balance info (provider-specific format)
        """
        pass

    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to standard format.

        Removes all non-digit characters and handles Turkish format.

        Args:
            phone: Raw phone number

        Returns:
            Normalized 10-digit phone number
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        # Handle Turkish formats
        if digits.startswith('90') and len(digits) == 12:
            digits = digits[2:]  # Remove country code
        elif digits.startswith('0') and len(digits) == 11:
            digits = digits[1:]  # Remove leading zero

        return digits

    def format_phone_for_provider(self, phone: str) -> str:
        """
        Format phone number for provider API.

        Override in subclass if provider needs specific format.

        Args:
            phone: Normalized phone number

        Returns:
            Formatted phone number for API
        """
        normalized = self.normalize_phone(phone)
        return f"90{normalized}"  # Turkish format with country code

    def has_turkish_chars(self, message: str) -> bool:
        """Check if message contains Turkish characters."""
        return bool(self.TURKISH_CHARS.intersection(set(message)))

    def calculate_credits(self, message: str) -> int:
        """
        Calculate how many SMS credits a message will use.

        Turkish characters reduce the character limit significantly.

        Args:
            message: Message content

        Returns:
            Number of SMS credits required
        """
        length = len(message)

        if self.has_turkish_chars(message):
            # UCS-2 encoding (Turkish chars)
            if length <= self.UCS2_SINGLE_LIMIT:
                return 1
            else:
                # Concatenated SMS
                return (length + self.UCS2_CONCAT_LIMIT - 1) // self.UCS2_CONCAT_LIMIT
        else:
            # GSM-7 encoding (ASCII)
            if length <= self.GSM7_SINGLE_LIMIT:
                return 1
            else:
                # Concatenated SMS
                return (length + self.GSM7_CONCAT_LIMIT - 1) // self.GSM7_CONCAT_LIMIT

    def validate_phone(self, phone: str) -> bool:
        """
        Validate phone number format.

        Args:
            phone: Phone number to validate

        Returns:
            True if valid Turkish mobile number
        """
        normalized = self.normalize_phone(phone)

        # Turkish mobile numbers start with 5 and are 10 digits
        if len(normalized) != 10:
            return False

        if not normalized.startswith('5'):
            return False

        return True

    def validate_message(self, message: str) -> bool:
        """
        Validate message content.

        Args:
            message: Message to validate

        Returns:
            True if message is valid
        """
        if not message or not message.strip():
            return False

        # Max 10 SMS parts (roughly 1530 chars for Turkish)
        if len(message) > 1530:
            return False

        return True
