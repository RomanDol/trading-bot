"""
WebSocket мониторинг для Binance Futures
"""
import json
import logging
import threading
import time
import sqlite3
from datetime import datetime
from typing import Dict, Any, Callable
import websocket
import requests

from .database import db_manager

logger = logging.getLogger(__name__)

class SimpleBinanceWebSocket:
    """Простой WebSocket мониторинг Binance"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"
        self.ws_base_url = "wss://fstream.binance.com"
        
        # WebSocket соединение
        self.ws = None
        self.listen_key = None
        self.is_connected = False
        self.is_running = False
        
        # Коллбэки
        self.order_callbacks = []
        self.position_callbacks = []
        
        # Данные
        self.current_positions = {}
        self.current_balances = {}
        
        # Статистика
        self.stats = {
            'messages_received': 0,
            'orders_updated': 0,
            'positions_updated': 0,
            'connection_time': None,
            'last_message_time': None,
            'reconnect_count': 0
        }
    
    def start(self):
        """Запускает WebSocket мониторинг"""
        if self.is_running:
            logger.warning("WebSocket уже запущен")
            return
        
        self.is_running = True
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_websocket, daemon=True)
        thread.start()
        
        # Поток для поддержания listen_key
        keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        keepalive_thread.start()
        
        logger.info("🚀 WebSocket мониторинг запущен")
    
    def _run_websocket(self):
        """Основной цикл WebSocket"""
        while self.is_running:
            try:
                # Получаем listen key
                self._get_listen_key()
                
                if not self.listen_key:
                    logger.error("❌ Не удалось получить listen key")
                    time.sleep(30)
                    continue
                
                # Создаем WebSocket URL
                ws_url = f"{self.ws_base_url}/ws/{self.listen_key}"
                
                # Создаем WebSocket соединение
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                # Запускаем (блокирующий вызов)
                self.ws.run_forever()
                
            except Exception as e:
                logger.error(f"❌ Ошибка WebSocket: {e}")
                self.stats['reconnect_count'] += 1
                
                if self.is_running:
                    logger.info("🔄 Переподключение через 10 секунд...")
                    time.sleep(10)
    
    def _get_listen_key(self):
        """Получает listen key от Binance"""
        try:
            response = requests.post(
                f"{self.base_url}/fapi/v1/listenKey",
                headers={"X-MBX-APIKEY": self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                self.listen_key = response.json()['listenKey']
                logger.info("✅ Listen key получен")
            else:
                logger.error(f"❌ Ошибка получения listen key: {response.status_code}")
                self.listen_key = None
                
        except Exception as e:
            logger.error(f"❌ Исключение при получении listen key: {e}")
            self.listen_key = None
    
    def _keepalive_loop(self):
        """Поддерживает listen key активным"""
        while self.is_running:
            try:
                time.sleep(30 * 60)  # Каждые 30 минут
                
                if self.listen_key and self.is_running:
                    response = requests.put(
                        f"{self.base_url}/fapi/v1/listenKey",
                        headers={"X-MBX-APIKEY": self.api_key},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.debug("✅ Listen key обновлен")
                    else:
                        logger.warning(f"⚠️ Не удалось обновить listen key: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка keepalive: {e}")
    
    def _on_open(self, ws):
        """WebSocket открыт"""
        self.is_connected = True
        self.stats['connection_time'] = datetime.now()
        logger.info("✅ WebSocket соединение установлено")
    
    def _on_message(self, ws, message):
        """Получено сообщение"""
        try:
            data = json.loads(message)
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            event_type = data.get('e')


            logger.info(f"📡 WebSocket получил: {event_type}")
            if event_type == 'ORDER_TRADE_UPDATE':
                  order_data = data.get('o', {})
                  order_id = order_data.get('i')
                  status = order_data.get('X')
                  symbol = order_data.get('s')
                  logger.info(f"🎯 Ордер обновление: {order_id} {symbol} {status}")
            


            
            if event_type == 'ORDER_TRADE_UPDATE':
                self._handle_order_update(data)
            elif event_type == 'ACCOUNT_UPDATE':
                self._handle_account_update(data)
            elif event_type == 'listenKeyExpired':
                logger.warning("⚠️ Listen key истек")
                self.ws.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    def _handle_order_update(self, data):
        """Обрабатывает обновления ордеров"""
        try:
            order = data.get('o', {})
            
            order_id = order.get('i')
            status = order.get('X')
            symbol = order.get('s')
            side = order.get('S')
            executed_qty = float(order.get('z', 0))
            avg_price = float(order.get('ap', 0))
            
            logger.info(f"📊 Ордер {order_id}: {symbol} {side} {status}")
            
            # Обновляем в БД
            self._update_order_in_database(order_id, status, executed_qty, avg_price, order)
            
            # Вызываем коллбэки
            for callback in self.order_callbacks:
                try:
                    callback(order)
                except:
                    pass
            
            self.stats['orders_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки ордера: {e}")
    
    def _handle_account_update(self, data):
        """Обрабатывает обновления аккаунта"""
        try:
            account = data.get('a', {})
            
            # Позиции
            positions = account.get('P', [])
            for pos in positions:
                symbol = pos.get('s')
                amount = float(pos.get('pa', 0))
                
                if amount != 0:
                    self.current_positions[symbol] = {
                        'symbol': symbol,
                        'amount': amount,
                        'entry_price': float(pos.get('ep', 0)),
                        'unrealized_pnl': float(pos.get('up', 0)),
                        'position_side': pos.get('ps')
                    }
                elif symbol in self.current_positions:
                    del self.current_positions[symbol]
            
            # Балансы
            balances = account.get('B', [])
            for bal in balances:
                asset = bal.get('a')
                wallet_balance = float(bal.get('wb', 0))
                self.current_balances[asset] = {
                    'wallet_balance': wallet_balance,
                    'cross_wallet_balance': float(bal.get('cw', 0))
                }
            
            # Вызываем коллбэки
            for callback in self.position_callbacks:
                try:
                    callback(self.current_positions)
                except:
                    pass
            
            self.stats['positions_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки аккаунта: {e}")
    
    def _update_order_in_database(self, order_id, status, executed_qty, avg_price, full_order_data):
        """Обновляет ордер в базе данных"""
        try:
            logger.info(f"🔍 Ищем ордер {order_id} в БД...") 
            # Ищем запись в БД
            with sqlite3.connect(db_manager.db_file) as conn:
                cursor = conn.cursor()
                
                # Попробуем найти как строку И как число
                cursor.execute("""
                  SELECT id, extra_data, result FROM signals 
                  WHERE JSON_EXTRACT(extra_data, '$.binance_order_id') = ? 
                     OR JSON_EXTRACT(extra_data, '$.binance_order_id') = ?
                  ORDER BY id DESC LIMIT 1
                """, (str(order_id), int(order_id)))
                
                result = cursor.fetchone()
                
                if result:
                    signal_id, extra_data_json, current_result = result
                    
                    # Парсим extra_data
                    try:
                        extra_data = json.loads(extra_data_json) if extra_data_json else {}
                    except:
                        extra_data = {}
                    
                    # Обновляем данными из WebSocket
                    extra_data.update({
                        'ws_status': status,
                        'ws_executed_qty': executed_qty,
                        'ws_avg_price': avg_price,
                        'ws_last_update': datetime.now().isoformat(),
                        'ws_commission': float(full_order_data.get('n', 0)),
                        'ws_realized_profit': float(full_order_data.get('rp', 0))
                    })
                    
                    # Определяем новый результат
                    if status == 'FILLED':
                        new_result = 'success'
                    elif status == 'PARTIALLY_FILLED':
                        new_result = 'partial'
                    elif status in ['CANCELED', 'EXPIRED']:
                        new_result = 'error'
                    else:
                        new_result = current_result
                    
                    # Сохраняем обратно в БД
                    cursor.execute("""
                        UPDATE signals 
                        SET result = ?, extra_data = ?
                        WHERE id = ?
                    """, (new_result, json.dumps(extra_data, ensure_ascii=False), signal_id))
                    
                    logger.info(f"📝 Обновлен сигнал #{signal_id}: {status}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления БД: {e}")
    
    def _on_error(self, ws, error):
        """Ошибка WebSocket"""
        logger.error(f"❌ WebSocket ошибка: {error}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket закрыт"""
        self.is_connected = False
        logger.warning(f"⚠️ WebSocket закрыт: {close_status_code}")
    
    def add_order_callback(self, callback):
        """Добавляет коллбэк для ордеров"""
        self.order_callbacks.append(callback)
    
    def add_position_callback(self, callback):
        """Добавляет коллбэк для позиций"""
        self.position_callbacks.append(callback)
    
    def get_positions(self):
        """Возвращает текущие позиции"""
        return self.current_positions.copy()
    
    def get_balances(self):
        """Возвращает текущие балансы"""
        return self.current_balances.copy()
    
    def get_stats(self):
        """Возвращает статистику"""
        stats = self.stats.copy()
        stats['is_connected'] = self.is_connected
        stats['is_running'] = self.is_running
        
        if self.stats['connection_time']:
            duration = datetime.now() - self.stats['connection_time']
            stats['connection_duration'] = str(duration).split('.')[0]
        
        return stats
    
    def stop(self):
        """Останавливает мониторинг"""
        logger.info("🛑 Остановка WebSocket мониторинга...")
        self.is_running = False
        self.is_connected = False
        
        if self.ws:
            self.ws.close()