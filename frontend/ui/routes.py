from flask import request, jsonify
"""
Маршруты Flask для веб-интерфейса управления ботом
Очищенная версия - только Dashboard и Control Panel
"""
import time
import subprocess
from backend.core.database import db_manager
from flask import request
SERVICE_NAME = "trading-bot"

class RouteHandlers:
    """Класс с обработчиками маршрутов"""
    
    _status_cache = None
    _status_cache_time = 0
    _status_cache_duration = 5  # 5 секунд
    
    @staticmethod
    def get_status():
        """Получает статус systemd сервиса с кэшированием"""
        current_time = time.time()
        
        # Проверяем нужно ли обновить кэш
        cache_expired = (current_time - RouteHandlers._status_cache_time) > RouteHandlers._status_cache_duration
        
        if RouteHandlers._status_cache is None or cache_expired:
            try:
                result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], 
                                      stdout=subprocess.PIPE, text=True, timeout=5)
                RouteHandlers._status_cache = result.stdout.strip()
                RouteHandlers._status_cache_time = current_time
                print(f"🔄 Статус обновлен: {RouteHandlers._status_cache}")
            except Exception as e:
                print(f"❌ Ошибка получения статуса: {e}")
                RouteHandlers._status_cache = "unknown"
                RouteHandlers._status_cache_time = current_time
        
        return RouteHandlers._status_cache

    @staticmethod
    def get_logs():
        """Получает логи сервиса"""
        try:
            return subprocess.getoutput(f"journalctl -u {SERVICE_NAME}.service -n 30 --no-pager")
        except Exception as e:
            print(f"❌ Ошибка получения логов: {e}")
            return f"Ошибка получения логов: {e}"

    @staticmethod
    def control_service(action):
        """Управляет сервисом (start/stop/restart)"""
        if action not in ['start', 'stop', 'restart']:
            return False, f"Неизвестное действие: {action}"
        
        try:
            result = subprocess.run(["systemctl", action, SERVICE_NAME], 
                                  capture_output=True, text=True, timeout=10)
            RouteHandlers._status_cache = None
            RouteHandlers._status_cache_time = 0
            print(f"🗑️ Кэш статуса очищен после выполнения '{action}'")
            
            if result.returncode == 0:
                return True, f"Команда '{action}' выполнена успешно"
            else:
                return False, f"Ошибка выполнения '{action}': {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, f"Таймаут выполнения команды '{action}'"
        except Exception as e:
            print(f"❌ Ошибка управления сервисом: {e}")
            return False, f"Исключение: {e}"

    @staticmethod
    def handle_dashboard():
        """Обработчик главной страницы"""
        try:
            stats = db_manager.get_stats()
            return {
                'stats': stats,
                'status': RouteHandlers.get_status()
            }
        except Exception as e:
            print(f"❌ Ошибка получения данных дашборда: {e}")
            return {
                'stats': {},
                'status': 'unknown',
                'error': str(e)
            }

    @staticmethod
    def handle_control_post():
        """Обработчик POST запросов страницы управления"""
        action = request.form.get('action')
        
        if action in ['start', 'stop', 'restart']:
            success, message = RouteHandlers.control_service(action)
        else:
            success, message = False, f"Неизвестное действие: {action}"
        
        logs = RouteHandlers.get_logs()
        
        return {
            'logs': logs,
            'message': message,
            'success': success
        }

# Создаем экземпляр для использования в приложении
route_handlers = RouteHandlers()