"""
Главное Flask приложение для приема webhook сигналов и торговли
Очищенная версия без обратной совместимости
"""
import logging
from flask import Flask, jsonify
from core.webhook_handler import webhook_handler
from datetime import datetime

# ✅ Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ✅ Создание Flask приложения
app = Flask(__name__)

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной endpoint для приема webhook сигналов"""
    response_data, status_code = webhook_handler.process_webhook()
    return jsonify(response_data), status_code

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'trading-bot'}





@app.route('/realtime_positions')
def realtime_positions():
    """API для получения позиций в реальном времени"""
    from core.binance_client import binance_client
    positions = binance_client.get_realtime_positions()
    return jsonify({
        'positions': positions,
        'total_positions': len(positions),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/websocket_stats')
def websocket_stats():
    """Статистика WebSocket соединения"""
    from core.binance_client import binance_client
    stats = binance_client.get_websocket_stats()
    return jsonify(stats)

@app.route('/health_extended')
def health_extended():
    """Расширенная проверка здоровья системы"""
    from core.binance_client import binance_client
    from core.database import db_manager
    
    ws_stats = binance_client.get_websocket_stats()
    
    return jsonify({
        'status': 'ok',
        'service': 'trading-bot',
        'websocket': {
            'connected': ws_stats.get('is_connected', False),
            'messages_received': ws_stats.get('messages_received', 0),
            'connection_duration': ws_stats.get('connection_duration')
        },
        'database': {
            'accessible': True,
            'total_signals': db_manager.get_signals_count()
        }
    })







if __name__ == '__main__':
    print("🚀 Запуск Trading Bot с WebSocket мониторингом...")
    print("📡 WebSocket: Real-time мониторинг ордеров и позиций")
    print("📊 Webhook endpoint: http://localhost:5000/webhook")
    print("📈 Real-time позиции: http://localhost:5000/realtime_positions")
    print("🔧 WebSocket статистика: http://localhost:5000/websocket_stats")
    
    app.run(host='0.0.0.0', port=5000, debug=False)