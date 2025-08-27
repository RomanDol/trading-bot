"""
Flask веб-интерфейс для управления Trading Bot
Очищенная версия - только Dashboard и Control Panel
"""
from flask import Flask, render_template, request
from ui.auth import auth_manager
from ui.routes import route_handlers
from datetime import datetime

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

# ===== API МАРШРУТЫ (для интеграции с PostgREST) =====

@app.route('/api/realtime_data')
def realtime_data():
    """API для получения данных в реальном времени"""
    from core.binance_client import binance_client
    
    ws_stats = binance_client.get_websocket_stats()
    positions = binance_client.get_realtime_positions()
    balances = binance_client.get_realtime_balances()
    
    return jsonify({
        'websocket_status': {
            'connected': ws_stats.get('is_connected', False),
            'messages_received': ws_stats.get('messages_received', 0),
            'orders_tracked': ws_stats.get('orders_updated', 0),
            'last_message_time': ws_stats.get('last_message_time')
        },
        'positions': positions,
        'balances': balances,
        'timestamp': datetime.now().isoformat()
    })

# ===== ЗАГЛУШКИ ДЛЯ POSTGREST ИНТЕГРАЦИИ =====

@app.route('/admin')
def admin_redirect():
    """Перенаправление на PostgREST Admin"""
    return """
    <div style="padding: 20px; background: #111; color: #fff; font-family: monospace;">
        <h2>🚀 Database Admin</h2>
        <p>PostgREST Admin будет доступен по адресу:</p>
        <ul>
            <li><a href="http://localhost:3000" style="color: #00ff88;">PostgREST API</a></li>
            <li><a href="http://localhost:8080" style="color: #00ff88;">PostgREST Admin UI</a></li>
        </ul>
        <p><a href="/" style="color: #00ff88;">← Назад к Dashboard</a></p>
    </div>
    """

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI (Clean Version)...")
    print(f"👤 Пользователь: {auth_manager.username}")
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://localhost:8888")
    print("📊 Таблицы будут доступны через PostgREST Admin")
    
    app.run(host='0.0.0.0', port=8888, debug=True)