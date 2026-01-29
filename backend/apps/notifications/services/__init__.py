# notifications/services/__init__.py

from .dispatcher import NotificationDispatcher, notify

__all__ = [
    'NotificationDispatcher',
    'notify',
]
