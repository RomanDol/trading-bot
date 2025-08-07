"""
Маршруты Flask для веб-интерфейса управления ботом
"""
from flask import request, jsonify
import subprocess
from columns_config import load_columns_config, save_columns_config, reset_to_default
from signals_handler import get_signals_data, get_filter_options, get_signals_stats

SERVICE_NAME = "trading-bot"

def get_status():
    """Получает статус systemd сервиса"""
    try:
        result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], 
                              stdout=subprocess.PIPE, text=True, timeout=5)
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ Ошибка получения статуса сервиса: {e}")
        return "unknown"

def get_logs():
    """Получает логи сервиса"""
    try:
        return subprocess.getoutput(f"journalctl -u {SERVICE_NAME}.service -n 30 --no-pager")
    except Exception as e:
        print(f"❌ Ошибка получения логов: {e}")
        return f"Ошибка получения логов: {e}"

def control_service(action):
    """Управляет сервисом (start/stop/restart)"""
    if action not in ['start', 'stop', 'restart']:
        return False, f"Неизвестное действие: {action}"
    
    try:
        result = subprocess.run(["systemctl", action, SERVICE_NAME], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, f"Команда '{action}' выполнена успешно"
        else:
            return False, f"Ошибка выполнения '{action}': {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, f"Таймаут выполнения команды '{action}'"
    except Exception as e:
        return False, f"Ошибка выполнения '{action}': {e}"

def handle_dashboard():
    """Обработчик главной страницы"""
    return {
        'status': get_status(),
        'stats': get_signals_stats()
    }

def handle_control_post():
    """Обработчик POST запросов на странице управления"""
    action = request.form.get('action')
    logs = ''
    message = ''
    
    if action == 'logs':
        logs = get_logs()
    elif action in ['start', 'stop', 'restart']:
        success, msg = control_service(action)
        message = msg
    else:
        message = f"Неизвестное действие: {action}"
    
    return {
        'status': get_status(),
        'logs': logs,
        'message': message
    }

def handle_signals():
    """Обработчик страницы сигналов"""
    # Получаем параметры фильтрации из URL
    filters = {
        'from_date': request.args.get('from_date', ''),
        'to_date': request.args.get('to_date', ''),
        'action': request.args.get('action', ''),
        'symbol': request.args.get('symbol', ''),
        'result': request.args.get('result', ''),
        'strategy': request.args.get('strategy', '')
    }
    
    # Загружаем конфигурацию колонок
    columns_config = load_columns_config()
    
    # Получаем опции для фильтров
    filter_options = get_filter_options()
    
    return {
        'columns_config': columns_config,
        'filters': filters,
        'filter_options': filter_options
    }

def handle_signals_data():
    """API endpoint для получения данных сигналов"""
    try:
        # Получаем параметры фильтрации
        filters = {
            'from_date': request.args.get('from_date'),
            'to_date': request.args.get('to_date'),
            'action': request.args.get('action'),
            'symbol': request.args.get('symbol'),
            'result': request.args.get('result'),
            'strategy': request.args.get('strategy')
        }
        
        # Убираем пустые фильтры
        filters = {k: v for k, v in filters.items() if v}
        
        # Получаем данные
        data = get_signals_data(filters)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'rows': [],
            'columns': [],
            'column_map': {},
            'total_found': 0
        }), 500

def handle_save_columns_config():
    """API endpoint для сохранения конфигурации колонок"""
    try:
        config = request.get_json()
        
        if not config:
            return jsonify({'status': 'error', 'message': 'Отсутствуют данные'}), 400
        
        # Валидируем структуру конфигурации
        for key, col_config in config.items():
            required_fields = ['name', 'visible', 'order']
            if not all(field in col_config for field in required_fields):
                return jsonify({
                    'status': 'error', 
                    'message': f'Неверная структура конфигурации для колонки {key}'
                }), 400
        
        if save_columns_config(config):
            return jsonify({'status': 'success', 'message': 'Конфигурация сохранена'})
        else:
            return jsonify({'status': 'error', 'message': 'Ошибка сохранения'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_reset_columns():
    """API endpoint для сброса конфигурации колонок"""
    try:
        config = reset_to_default()
        return jsonify({
            'status': 'success', 
            'message': 'Конфигурация сброшена',
            'config': config
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_get_columns_config():
    """API endpoint для получения текущей конфигурации колонок"""
    try:
        config = load_columns_config()
        return jsonify({
            'status': 'success',
            'config': config
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Маппинг маршрутов для упрощения регистрации
ROUTE_HANDLERS = {
    'dashboard_get': handle_dashboard,
    'control_post': handle_control_post,
    'signals_get': handle_signals,
    'signals_data': handle_signals_data,
    'save_columns_config': handle_save_columns_config,
    'reset_columns': handle_reset_columns,
    'get_columns_config': handle_get_columns_config
}

if __name__ == "__main__":
    # Тестирование функций
    print("🧪 Тестирование модуля ui_routes...")
    
    print(f"📊 Статус сервиса: {get_status()}")
    
    dashboard_data = handle_dashboard()
    print(f"📈 Статистика дашборда: {dashboard_data['stats']['total_signals']} сигналов")
    
    signals_data = handle_signals()
    print(f"📋 Конфигурация колонок: {len(signals_data['columns_config'])} колонок")