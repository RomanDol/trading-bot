"""
Модули веб-интерфейса Trading Bot
"""

from .auth import auth_manager
from .routes import route_handlers

__all__ = [
    'auth_manager',
    'route_handlers'
]
