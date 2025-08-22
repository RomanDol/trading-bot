#!/usr/bin/env python3
"""
Скрипт для ручного создания тестовых данных сокетов
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.sockets_database import SocketsDatabaseManager

def main():
    print("🚀 Создание базы данных сокетов и добавление тестовых записей...")
    
    # Создаем экземпляр базы данных (автоматически создаст таблицу)
    db = SocketsDatabaseManager()
    
    print("✅ База данных и таблица созданы")
    
    # Создаем первую тестовую запись - ORDER_TRADE_UPDATE
    print("\n📝 Добавляем первую запись: ORDER_TRADE_UPDATE")
    
    # Время 5 минут назад
    time1 = datetime.utcnow() - timedelta(minutes=5)
    
    order_update_message = {
        "e": "ORDER_TRADE_UPDATE",
        "E": int(time1.timestamp() * 1000),
        "T": int(time1.timestamp() * 1000),
        "o": {
            "s": "BTCUSDT",
            "c": "web_1234567890",
            "S": "BUY",
            "o": "MARKET",
            "f": "GTC",
            "q": "0.001",
            "p": "0",
            "ap": "45250.50",
            "sp": "0",
            "x": "TRADE",
            "X": "FILLED",
            "i": 1234567890,
            "l": "0.001",
            "z": "0.001", 
            "L": "45250.50",
            "n": "0.0451",
            "N": "USDT",
            "T": int(time1.timestamp() * 1000),
            "t": 987654321,
            "I": 1111111111,
            "w": True,
            "m": False,
            "M": False,
            "O": int(time1.timestamp() * 1000),
            "Z": "45.25",
            "Y": "45.25",
            "Q": "45.25",
            "ps": "LONG",
            "rp": "0"
        }
    }
    
    # Добавляем первую запись
    socket_id1 = db.log_socket_message(
        event_type="ORDER_TRADE_UPDATE",
        symbol="BTCUSDT",
        order_id="1234567890",
        status="FILLED",
        raw_message=json.dumps(order_update_message, ensure_ascii=False)
    )
    
    print(f"✅ Добавлена запись #{socket_id1}")
    
    # Создаем вторую тестовую запись - ACCOUNT_UPDATE
    print("\n📝 Добавляем вторую запись: ACCOUNT_UPDATE")
    
    # Время 3 минуты назад
    time2 = datetime.utcnow() - timedelta(minutes=3)
    
    account_update_message = {
        "e": "ACCOUNT_UPDATE",
        "E": int(time2.timestamp() * 1000),
        "T": int(time2.timestamp() * 1000),
        "a": {
            "m": "ORDER",
            "B": [
                {
                    "a": "USDT",
                    "wb": "9954.75",
                    "cw": "9954.75",
                    "bc": "0"
                }
            ],
            "P": [
                {
                    "s": "BTCUSDT",
                    "pa": "0.001",
                    "ep": "45250.50",
                    "cr": "45.25",
                    "up": "12.35",
                    "mt": "cross",
                    "iw": "0",
                    "ps": "LONG",
                    "ma": "USDT"
                }
            ]
        }
    }
    
    # Добавляем вторую запись
    socket_id2 = db.log_socket_message(
        event_type="ACCOUNT_UPDATE",
        symbol="BTCUSDT",
        order_id=None,  # У ACCOUNT_UPDATE нет order_id
        status=None,    # У ACCOUNT_UPDATE нет status
        raw_message=json.dumps(account_update_message, ensure_ascii=False)
    )
    
    print(f"✅ Добавлена запись #{socket_id2}")
    
    # Показываем статистику
    print(f"\n📊 Итоговая статистика:")
    total_count = db.get_sockets_count()
    print(f"   📡 Всего сообщений: {total_count}")
    
    # Показываем все записи
    print(f"\n📄 Все записи в базе:")
    messages = db.get_socket_messages(limit=10, offset=0)
    
    for i, msg in enumerate(messages, 1):
        id_val, timestamp, event_type, symbol, order_id, status, raw_message = msg
        print(f"   {i}. ID:{id_val} | {timestamp} | {event_type} | {symbol} | {order_id} | {status}")
    
    print(f"\n💡 Теперь можете открыть http://localhost:8888/sockets для просмотра данных")
    print("✅ Готово!")

if __name__ == "__main__":
    main()