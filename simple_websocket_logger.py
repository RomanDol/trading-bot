#!/usr/bin/env python3
"""
Простой WebSocket логгер - записывает каждое сообщение в отдельную строку
"""

import os
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv
import websocket
import requests

# Загружаем переменные окружения
load_dotenv()

class SimpleWebSocketLogger:
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        
        if not self.api_key:
            print("❌ BINANCE_API_KEY не найден в .env файле")
            sys.exit(1)
        
        self.base_url = "https://fapi.binance.com"
        self.ws_base_url = "wss://fstream.binance.com"
        self.listen_key = None
        self.ws = None
        
        # Создаем файл лога
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"websocket_messages.log"
        
        print(f"🚀 WebSocket Logger запущен")
        print(f"📁 Файл лога: {self.log_file}")
        print(f"💡 Нажмите Ctrl+C для остановки")
        print("-" * 50)
        
        # Обработчик сигнала для Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Обработчик Ctrl+C"""
        print(f"\n🛑 Получен сигнал остановки")
        print(f"📁 Все сообщения сохранены в: {self.log_file}")
        sys.exit(0)
    
    def get_listen_key(self):
        """Получает listen key"""
        try:
            response = requests.post(
                f"{self.base_url}/fapi/v1/listenKey",
                headers={"X-MBX-APIKEY": self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                self.listen_key = response.json()['listenKey']
                print(f"✅ Listen key получен")
                return True
            else:
                print(f"❌ Ошибка получения listen key: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def on_open(self, ws):
        """WebSocket открыт"""
        print(f"🟢 WebSocket подключен в {datetime.now()}")
    
    def on_message(self, ws, message):
        """Получено сообщение - просто записываем в файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Записываем в файл: время + сообщение
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {message}\n")
        
        print(f"📨 {timestamp} | Сообщение записано")
    
    def on_error(self, ws, error):
        """Ошибка WebSocket"""
        print(f"❌ WebSocket ошибка: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket закрыт"""
        print(f"🔴 WebSocket закрыт: {close_status_code}")
    
    def start(self):
        """Запуск логгера"""
        if not self.get_listen_key():
            return
        
        ws_url = f"{self.ws_base_url}/ws/{self.listen_key}"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Запускаем (блокирующий вызов)
        self.ws.run_forever()

if __name__ == "__main__":
    logger = SimpleWebSocketLogger()
    logger.start()