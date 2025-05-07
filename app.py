import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from binance.um_futures import UMFutures
from dotenv import load_dotenv
import re
from precision import adjust_quantity, load_step_sizes

# Загрузка переменных среды
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = UMFutures(key=api_key, secret=api_secret)

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


# ✅ Запись сигнала в БД
def log_signal(action, symbol, quantity, result, message, strategy=''):
    import pytz
    tz = pytz.timezone("Europe/London")  # или другая зона, если ты не в UK
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO signals (timestamp, action, symbol, quantity, result, message, code, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, action, symbol, quantity, result, message, '', strategy
        ))



def open_position(symbol, side, quantity):
    print("📤 Sending order with params:", {
        'symbol': symbol,
        'side': 'BUY' if side == 'LONG' else 'SELL',
        'type': 'MARKET',
        'quantity': quantity,
        'positionSide': 'LONG' if side == 'LONG' else 'SHORT'
    })
    try:
        response = client.new_order(
            symbol=symbol,
            side='BUY' if side == 'LONG' else 'SELL',
            type='MARKET',
            quantity=quantity,
            positionSide='LONG' if side == 'LONG' else 'SHORT'
        )
        print("✅ Order placed:", response)
        return True, "Order placed successfully"
    except Exception as e:
        print("❌ Binance error:", e)
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
        print("✅ Close order:", response)
        return True, "Order closed successfully"
    except Exception as e:
        print("❌ Binance error:", e)
        return False, str(e)

def check_position_mode():
    try:
        mode = client.get_position_mode()
        print("🔍 Hedge mode status (dualSidePosition):", mode)
    except Exception as e:
        print("❌ Failed to check position mode:", e)

@app.route('/webhook', methods=['POST'])
def webhook():
    check_position_mode()
    data = request.get_json()
    print("🔔 Webhook received:", data)

    if not data or 'action' not in data or 'symbol' not in data or 'quantity' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    quantity_raw = float(data['quantity'])
    quantity = adjust_quantity(data['symbol'], quantity_raw)


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

    print("📌 STRATEGY:", data.get('strategy'))

    strategy = data.get('strategy', '')
    log_signal(action, symbol, quantity, 'success' if success else 'error', msg, strategy)

    return jsonify({'status': 'ok' if success else 'error', 'message': msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


def extract_code(message):
    match = re.search(r'\(\d+,\s*(-?\d+)', message)
    return match.group(1) if match else 'n/a'

def extract_msg(message):
    match = re.search(r'"([^"]+?)"\s*,\s*{', message)
    return match.group(1) if match else message[:120] + '...'