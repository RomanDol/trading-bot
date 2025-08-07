import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from binance.um_futures import UMFutures
from dotenv import load_dotenv
import re
from precision import adjust_quantity, load_step_sizes
import logging
import json

# ✅ Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ✅ Загрузка переменных среды
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = UMFutures(key=api_key, secret=api_secret)
SIGNAL_KEY = os.getenv("SIGNAL_KEY")

app = Flask(__name__)
DB_FILE = "signals.db"




# ✅ Создание таблицы при первом запуске
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                symbol TEXT,
                quantity REAL,
                result TEXT,
                message TEXT,
                code TEXT,
                strategy TEXT
            )
        ''')

init_db()
load_step_sizes()






def log_signal(action, symbol, quantity, result, message, strategy='', extra_data=None):
    """Записывает сигнал в БД с временем в UTC и дополнительными данными"""
    from datetime import datetime
    
    # Сохраняем время в UTC без timezone конвертации
    utc_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Преобразуем extra_data в JSON строку
    extra_json = None
    if extra_data:
        try:
            extra_json = json.dumps(extra_data, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Ошибка сериализации extra_data: {e}")
            extra_json = str(extra_data)  # Fallback
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO signals (timestamp, action, symbol, quantity, result, message, code, strategy, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            utc_timestamp, action, symbol, quantity, result, message, '', strategy, extra_json
        ))
    
    extra_info = f" + {len(extra_data)} extra fields" if extra_data else ""
    print(f"💾 Сохранено в БД: {utc_timestamp} UTC - {action} {symbol} {quantity}{extra_info}")






def open_position(symbol, side, quantity):
    logger.info(f"📤 Sending order with params: {{'symbol': {symbol}, 'side': {'BUY' if side == 'LONG' else 'SELL'}, 'type': 'MARKET', 'quantity': {quantity}, 'positionSide': {side}}}")
    try:
        response = client.new_order(
            symbol=symbol,
            side='BUY' if side == 'LONG' else 'SELL',
            type='MARKET',
            quantity=quantity,
            positionSide='LONG' if side == 'LONG' else 'SHORT'
        )
        logger.info(f"✅ Order placed: {response}")
        return True, "Order placed successfully"
    except Exception as e:
        logger.error(f"❌ Binance error: {e}")
        return False, str(e)





def close_position(symbol, side, quantity):
    try:
        response = client.new_order(
            symbol=symbol,
            side='SELL' if side == 'LONG' else 'BUY',
            type='MARKET',
            quantity=quantity,
            positionSide='LONG' if side == 'LONG' else 'SHORT'
        )
        logger.info(f"✅ Close order: {response}")
        return True, "Order closed successfully"
    except Exception as e:
        logger.error(f"❌ Binance error: {e}")
        return False, str(e)




def check_position_mode():
    try:
        mode = client.get_position_mode()
        logger.info(f"🔍 Hedge mode status (dualSidePosition): {mode}")
    except Exception as e:
        logger.error(f"❌ Failed to check position mode: {e}")





@app.route('/webhook', methods=['POST'])
def webhook():
    check_position_mode()
    data = request.get_json()
    logger.info(f"🔔 Webhook received: {data}")

    if not data or 'auth_key' not in data:
        return jsonify({"status": "error", "message": "Missing auth_key"}), 403
    if data['auth_key'] != SIGNAL_KEY:
        return jsonify({"status": "error", "message": "Invalid auth_key"}), 403
    if 'action' not in data or 'symbol' not in data or 'quantity' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # Извлекаем основные поля
    action = data['action']
    symbol = data['symbol']
    quantity_raw = float(data['quantity'])
    quantity = adjust_quantity(symbol, quantity_raw)
    strategy = data.get('strategy', '')

    # Извлекаем ВСЕ дополнительные поля (любые кроме основных и служебных)
    CORE_FIELDS = {'auth_key', 'action', 'symbol', 'quantity', 'strategy'}
    extra_data = {k: v for k, v in data.items() if k not in CORE_FIELDS}
    
    # Если есть дополнительные поля, логируем их
    if extra_data:
        logger.info(f"📋 Extra fields: {extra_data}")

    # Выполняем торговые операции
    if action == 'ENTER_LONG':
        success, msg = open_position(symbol, 'LONG', quantity)
    elif action == 'EXIT_LONG':
        success, msg = close_position(symbol, 'LONG', quantity)
    elif action == 'ENTER_SHORT':
        success, msg = open_position(symbol, 'SHORT', quantity)
    elif action == 'EXIT_SHORT':
        success, msg = close_position(symbol, 'SHORT', quantity)
    else:
        success, msg = False, '❓ Unknown action'

    logger.info(f"📌 STRATEGY: {strategy}")

    # Сохраняем в БД с дополнительными полями (если есть)
    log_signal(action, symbol, quantity, 'success' if success else 'error', msg, strategy, extra_data if extra_data else None)

    return jsonify({'status': 'ok' if success else 'error', 'message': msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




def extract_code(message):
    match = re.search(r'\(\d+,\s*(-?\d+)', message)
    return match.group(1) if match else 'n/a'

def extract_msg(message):
    match = re.search(r'"([^"]+?)"\s*,\s*{', message)
    return match.group(1) if match else message[:120] + '...'
