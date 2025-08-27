"""
Flask веб-интерфейс для управления Trading Bot
Работает из папки frontend/ с доступом к core модулям
"""
import sys
import os

# КРИТИЧЕСКИ ВАЖНО: Добавляем путь к корневой директории для импорта core
# Это позволяет импортировать core модули из frontend/bot_ui.py
sys.path.insert(0, '/root/trading-bot')

from flask import Flask, render_template, request, jsonify
from datetime import datetime
from ui.auth import auth_manager
from ui.routes import route_handlers

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Поддержка UTF-8 в JSON

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ВСЕХ ШАБЛОНОВ =====

@app.context_processor
def inject_globals():
    """Внедряет глобальные переменные во все шаблоны"""
    return {
        'status': route_handlers.get_status()
    }

# ===== MIDDLEWARE =====

@app.before_request
def auth_middleware():
    """Middleware для проверки аутентификации"""
    return auth_manager.require_auth()

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/', endpoint='dashboard')
def dashboard():
    """Главная страница - дашборд"""
    data = route_handlers.handle_dashboard()
    return render_template('dashboard.html', **data)

@app.route('/control', methods=['GET', 'POST'], endpoint='control')
def control():
    """Страница управления сервисом"""
    if request.method == 'POST':
        data = route_handlers.handle_control_post()
    else:
        data = {
            'logs': '', 
            'message': ''
        }
    
    return render_template('control.html', **data)


# ===== ФИЛЬТРЫ JINJA2 =====

@app.template_filter('tojsonfilter')
def tojson_filter(obj):
    """Фильтр для преобразования объекта в JSON для JavaScript"""
    import json
    return json.dumps(obj, ensure_ascii=False)

# ===== ОБРАБОТЧИКИ ОШИБОК =====

@app.errorhandler(404)
def not_found(error):
    """Обработчик 404 ошибки"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Страница не найдена"), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибки"""
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Внутренняя ошибка сервера"), 500



@app.route('/dashboard_realtime')
def dashboard_realtime():
    """Dashboard с real-time данными"""
    data = route_handlers.handle_dashboard()
    
    # Добавляем WebSocket статус
    from core.binance_client import binance_client
    ws_stats = binance_client.get_websocket_stats()
    data['websocket_status'] = ws_stats.get('is_connected', False)
    data['realtime_positions'] = binance_client.get_realtime_positions()
    
    return render_template('dashboard.html', **data)

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI...")
    print(f"👤 Пользователь: {auth_manager.username}")
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://49.12.233.74:8888")
    print(f"📂 Рабочая директория: {os.getcwd()}")
    
    app.run(host='0.0.0.0', port=8888, debug=False)