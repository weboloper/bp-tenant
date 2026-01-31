# providers/sms/__init__.py

from typing import TYPE_CHECKING
from django.conf import settings
from .base import BaseSMSProvider, SMSResult, BulkSMSResult, SMSStatus

if TYPE_CHECKING:
    from .base import BaseSMSProvider

def get_sms_provider() -> BaseSMSProvider:
    """
    Factory function - Aktif SMS provider'ı döndürür

    Provider configuration is managed via SMSProviderConfig model in database.
    """
    from providers.models import SMSProviderConfig

    # Get default active provider from database
    config = SMSProviderConfig.objects.filter(is_default=True, is_active=True).first()
    
    if not config:
        # Fallback to mock in development
        if settings.DEBUG:
            from .mock import MockSMSProvider
            return MockSMSProvider()
        raise ValueError("No active SMS provider configured")
    
    if config.provider == 'netgsm':
        from .netgsm import NetGSMProvider
        return NetGSMProvider(
            username=config.credentials.get('username'),
            password=config.credentials.get('password'),
            sender_id=config.credentials.get('sender_id')
        )
    elif config.provider == 'twilio':
        from .twilio import TwilioProvider
        return TwilioProvider(
            account_sid=config.credentials.get('account_sid'),
            auth_token=config.credentials.get('auth_token'),
            from_number=config.credentials.get('from_number')
        )
    elif config.provider == 'mock':
        from .mock import MockSMSProvider
        return MockSMSProvider()
    
    raise ValueError(f"Unknown SMS provider: {config.provider}")

__all__ = [
    'get_sms_provider',
    'BaseSMSProvider',
    'SMSResult', 
    'BulkSMSResult',
    'SMSStatus',
]