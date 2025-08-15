"""
Главное Flask приложение для приема webhook сигналов и торговли
Очищенная версия без обратной совместимости
"""
import logging
from flask import Flask, jsonify
from core.webhook_handler import webhook_handler

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

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot Webhook Server...")
    print("📡 Webhook endpoint: http://localhost:5000/webhook")
    print("💚 Health check: http://localhost:5000/health")
    
    app.run(host='0.0.0.0', port=5000, debug=False)