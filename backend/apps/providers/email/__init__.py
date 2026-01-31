# providers/email/__init__.py
from typing import TYPE_CHECKING
from django.conf import settings

if TYPE_CHECKING:
    from .base import BaseEmailProvider


def get_email_provider() -> 'BaseEmailProvider':
    """
    Factory function - Aktif Email provider'ı döndürür

    Provider configuration is managed via EmailProviderConfig model in database.
    """
    from providers.models import EmailProviderConfig

    # Get default active provider from database
    config = EmailProviderConfig.objects.filter(is_default=True, is_active=True).first()
    
    if not config:
        if settings.DEBUG:
            from .mock import MockEmailProvider
            return MockEmailProvider()
        raise ValueError("No active Email provider configured")
    
    if config.provider == 'smtp':
        from .smtp import SMTPProvider
        return SMTPProvider(
            host=config.credentials.get('host'),
            port=config.credentials.get('port'),
            username=config.credentials.get('username'),
            password=config.credentials.get('password'),
            use_tls=config.credentials.get('use_tls', True),
            default_from=config.settings.get('from_email'),
            default_from_name=config.settings.get('from_name')
        )
    elif config.provider == 'sendgrid':
        from .sendgrid import SendgridProvider
        return SendgridProvider(**config.credentials, **config.settings)
    elif config.provider == 'mock':
        from .mock import MockEmailProvider
        return MockEmailProvider()
    
    raise ValueError(f"Unknown Email provider: {config.provider}")

from .base import BaseEmailProvider, EmailResult, EmailStatus

__all__ = [
    'get_email_provider',
    'BaseEmailProvider',
    'EmailResult',
    'EmailStatus',
]