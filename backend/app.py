"""
Главное Flask приложение для приема webhook сигналов и торговли
"""
import logging
from flask import Flask, jsonify, request, Response
from core.webhook_handler import webhook_handler
from core.order_restore import order_restore_manager
from datetime import datetime
import os
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной endpoint для приема webhook сигналов"""
    response_data, status_code = webhook_handler.process_webhook()
    return jsonify(response_data), status_code



@app.route('/api/restore_orders', methods=['POST'])
def restore_orders():
    data = request.get_json()
    success, message = order_restore_manager.restore_orders(data['start_date'], data['end_date'])
    return jsonify({'status': 'success' if success else 'error', 'message': message})


def check_auth(username, password):
    return username == os.getenv('UI_USERNAME') and password == os.getenv('UI_PASSWORD')

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Trading Bot API"'}
    )

def require_auth():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    return None

@app.before_request
def auth_middleware():
    # Только webhook остается без аутентификации для TradingView
    if request.path == '/webhook':
        return None
    return require_auth()

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot с WebSocket мониторингом...")
    print("📡 WebSocket: Real-time мониторинг ордеров и позиций")
    print("📊 Webhook endpoint: http://localhost:5000/webhook")
    print("📈 Real-time позиции: http://localhost:5000/realtime_positions")
    print("🔧 WebSocket статистика: http://localhost:5000/websocket_stats")
    
    print("🔧 Принудительная инициализация WebSocket...")
    try:
        from core.binance_client import binance_client
        if hasattr(binance_client, '_ensure_websocket_initialized'):
            success = binance_client._ensure_websocket_initialized()
            if success:
                print("✅ WebSocket инициализирован успешно!")
            else:
                print("❌ Не удалось инициализировать WebSocket")
        else:
            print("⚠️ Метод _ensure_websocket_initialized не найден")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации WebSocket: {e}")
        import traceback
        traceback.print_exc()
    
    app.run(host='0.0.0.0', port=5000, debug=False)