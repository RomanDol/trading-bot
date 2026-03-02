
import logging
from flask import Flask, jsonify, request, Response
from core.webhook_handler import webhook_handler
from core.order_restore import order_restore_manager
from datetime import datetime
import os
from dotenv import load_dotenv
from core.binance_symbols import binance_symbols_manager

# Setting up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


app = Flask(__name__)

# ===== MAIN ROUTES =====

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной endpoint для приема webhook сигналов"""
    print(f"Raw data: {request.data}")
    print(f"Content-Type: {request.content_type}")
    response_data, status_code = webhook_handler.process_webhook()
    return jsonify(response_data), status_code

@app.route('/api/restore_orders', methods=['POST'])
def restore_orders():
    data = request.get_json()
    success, message = order_restore_manager.restore_orders(data['start_date'], data['end_date'])
    return jsonify({'status': 'success' if success else 'error', 'message': message})



@app.route('/api/update_symbols', methods=['POST'])
def update_symbols():
    """Обновление списка символов Binance"""
    try:
        success, message = binance_symbols_manager.update_symbols()
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка обновления символов: {str(e)}'
        }), 500


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
    # Only the webhook remains unauthenticated for TradingView
    if request.path == '/webhook':
        return None
    return require_auth()


if __name__ == '__main__':
    print("🚀 Запуск Trading Bot с WebSocket мониторингом...")
    print("📡 WebSocket: Real-time мониторинг ордеров и позиций")
    print("📊 Webhook endpoint: http://localhost:5000/webhook")
    print("📈 Real-time позиции: http://localhost:5000/realtime_positions")
    print("🔧 WebSocket статистика: http://localhost:5000/websocket_stats")
    
    # REMOVED duplicate WebSocket initialization - it is now in binance_client.py
    print("📡 WebSocket инициализируется автоматически при импорте binance_client")
    
    app.run(host='0.0.0.0', port=5000, debug=False)