# ===== ui/__init__.py =====
"""
Модули веб-интерфейса Trading Bot
"""

from .auth import auth_manager, require_auth
from .routes import route_handlers, ROUTE_HANDLERS

__all__ = [
    'auth_manager',
    'require_auth',
    'route_handlers',
    'ROUTE_HANDLERS'
]