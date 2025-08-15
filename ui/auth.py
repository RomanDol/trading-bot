"""
Модуль для аутентификации веб-интерфейса
"""
import os
from flask import request, Response
from dotenv import load_dotenv

load_dotenv()

class AuthManager:
    """Класс для управления аутентификацией"""
    
    def __init__(self):
        self.username = os.getenv('UI_USERNAME')
        self.password = os.getenv('UI_PASSWORD')
    
    def check_auth(self, username: str, password: str) -> bool:
        """Проверка учетных данных"""
        return username == self.username and password == self.password
    
    def authenticate(self) -> Response:
        """Запрос аутентификации"""
        return Response(
            'Authentication required', 401,
            {'WWW-Authenticate': 'Basic realm="Trading Bot Login Required"'}
        )
    
    def require_auth(self) -> Response or None:
        """
        Middleware для проверки аутентификации
        
        Returns:
            Response or None: Response с запросом авторизации или None если авторизован
        """
        # Пропускаем статические файлы
        if request.path.startswith('/static/'):
            return None
        
        auth = request.authorization
        if not auth or not self.check_auth(auth.username, auth.password):
            return self.authenticate()
        
        return None

# Создаем глобальный экземпляр для использования в приложении
auth_manager = AuthManager()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля auth...")
    
    auth = AuthManager()
    print(f"👤 Пользователь: {auth.username}")
    print(f"🔐 Пароль: {'*' * len(auth.password)}")
    
    # Тест проверки учетных данных
    test_result = auth.check_auth('admin', '1234')
    print(f"✅ Тест авторизации: {test_result}")