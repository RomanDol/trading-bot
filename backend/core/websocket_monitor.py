"""
WebSocket мониторинг для Binance Futures БЕЗ SQLite БАЗ
Сохраняет только в PostgreSQL с фильтрацией
"""
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Set
import websocket
import requests
import queue
import hashlib

from .messages_database import messages_db_manager

logger = logging.getLogger(__name__)

class SimpleBinanceWebSocket:
    """Простой WebSocket мониторинг Binance БЕЗ SQLite"""
    
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
        
        # Дедупликация сообщений
        self.processed_messages = set()  
        self.message_cache_size = 1000   
        
        # Защита от повторного запуска
        self._start_lock = threading.Lock()
        self._started = False
        
        # Статистика
        self.stats = {
            'messages_received': 0,
            'messages_duplicated': 0,
            'orders_updated': 0,
            'positions_updated': 0,
            'connection_time': None,
            'last_message_time': None,
            'reconnect_count': 0,
            'messages_saved_to_db': 0
        }

        self.last_ping_time = None
        self.recovery_active = False
        self.recovery_thread = None
        self.monitor_thread = None

    def _on_ping(self, ws, payload):
        """Получен ping от сервера"""
        self.last_ping_time = datetime.now()
        
        # Логирование
        with open('logs/ping_log.txt', 'a') as f:
            f.write(f"{self.last_ping_time}: PING received\n")
        
        # Останавливаем восстановление если оно было активно
        if self.recovery_active:
            self.stop_recovery()
            logger.info("WebSocket восстановлен - остановка автовосстановления")
        
        

    def start(self):
        """Запускает WebSocket мониторинг"""
        with self._start_lock:
            if self._started or self.is_running:
                logger.warning("⚠️ WebSocket уже запущен, игнорируем повторный вызов")
                return False
            
            self._started = True
            self.is_running = True
            
            logger.info("🚀 Запуск WebSocket мониторинга")
        
        # Запускаем основной WebSocket поток
        thread = threading.Thread(target=self._run_websocket, daemon=True, name="WebSocket-Main")
        thread.start()
        
        # Поток для поддержания listen_key
        keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True, name="WebSocket-Keepalive")
        keepalive_thread.start()

        self.monitor_thread = threading.Thread(target=self._monitor_ping, daemon=True, name="WebSocket-PingMonitor")
        self.monitor_thread.start()
        
        logger.info("✅ WebSocket мониторинг запущен")
        return True



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
                
                # Очищаем кэш дубликатов при переподключении
                self.processed_messages.clear()
                logger.info("🗑️ Кэш дубликатов очищен при переподключении")
                
                # Создаем WebSocket соединение
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_ping=self._on_ping
                )
                
                # Запускаем (блокирующий вызов)
                logger.info("🔌 Подключение к WebSocket...")
                self.ws.run_forever()
                
            except Exception as e:
                logger.error(f"❌ Ошибка WebSocket: {e}")
                self.stats['reconnect_count'] += 1
                
                if self.is_running:
                    logger.info("🔄 Переподключение через 10 секунд...")
                    time.sleep(10)


    def _on_message(self, ws, message):
        """Получено сообщение с упрощенной дедупликацией"""
        try:
            # Простая дедупликация по полному сообщению
            message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
            
            if message_hash in self.processed_messages:
                self.stats['messages_duplicated'] += 1
                logger.debug(f"🔄 ДУБЛИКАТ пропущен (всего: {self.stats['messages_duplicated']})")
                return  # ПРОПУСКАЕМ ДУБЛИКАТ
            
            # Добавляем в кэш
            self.processed_messages.add(message_hash)
            
            # Ограничиваем размер кэша
            if len(self.processed_messages) > self.message_cache_size:
                old_hashes = list(self.processed_messages)[:100]
                for old_hash in old_hashes:
                    self.processed_messages.discard(old_hash)
            
            # Парсим сообщение
            data = json.loads(message)
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            event_type = data.get('e', 'UNKNOWN')
            
            logger.info(f"📡 WebSocket получил: {event_type} (#{self.stats['messages_received']}, дубликатов: {self.stats['messages_duplicated']})")

            # Сохраняем сообщение в PostgreSQL ТОЛЬКО если прошло фильтрацию
            if self._should_save_message(event_type, data):
                self._save_message_to_db(data, message)
            
            if event_type == 'ORDER_TRADE_UPDATE':
                order_data = data.get('o', {})
                order_id = order_data.get('i')
                status = order_data.get('X')
                
                logger.info(f"🎯 Ордер #{order_id}: {status}")
                self._handle_order_update(data)
                
            elif event_type == 'ACCOUNT_UPDATE':
                logger.info(f"💰 Обновление аккаунта")
                self._handle_account_update(data)
                
            elif event_type == 'listenKeyExpired':
                logger.warning("⚠️ Listen key истёк - переподключение...")
                self.ws.close()
                
            else:
                logger.info(f"🔸 Неизвестный тип события: {event_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")


    def _should_save_message(self, event_type, data):
        """Определяет нужно ли сохранять сообщение в базу"""
        # Пропускаем TRADE_LITE
        if event_type == 'TRADE_LITE':
            return False
        
        # ORDER_TRADE_UPDATE только со статусом FILLED
        if event_type == 'ORDER_TRADE_UPDATE':
            order_data = data.get('o', {})
            status = order_data.get('X', '')
            
            if status == 'NEW':
                return False
        
        return True

    def _save_message_to_db(self, data, raw_message):
        """Сохраняет WebSocket сообщение в PostgreSQL"""
        try:
            event_type = data.get('e', 'UNKNOWN')
            
            # Сохраняем исходные данные без изменений
            messages_db_manager.log_message(event_type, data)
            
            self.stats['messages_saved_to_db'] += 1
            logger.debug(f"💾 WebSocket сообщение {event_type} сохранено в PostgreSQL")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения WebSocket сообщения: {e}")

    def _handle_order_update(self, data):
        """Обрабатывает обновления ордеров"""
        try:
            order = data.get('o', {})
            
            order_id = order.get('i')
            status = order.get('X')
            symbol = order.get('s')
            executed_qty = float(order.get('z', 0))
            avg_price = float(order.get('ap', 0))
            
            logger.info(f"📊 Ордер обновлен: {order_id} {symbol} {status}")
            
            # Вызываем коллбэки
            for callback in self.order_callbacks[:]:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"❌ Ошибка в order callback: {e}")
            
            self.stats['orders_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_order_update: {e}")

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
            for callback in self.position_callbacks[:]:
                try:
                    callback(self.current_positions)
                except Exception as e:
                    logger.error(f"❌ Ошибка в position callback: {e}")
            
            self.stats['positions_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки аккаунта: {e}")

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

    def _on_error(self, ws, error):
        """Ошибка WebSocket"""
        logger.error(f"❌ WebSocket ошибка: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket закрыт"""
        self.is_connected = False
        logger.warning(f"⚠️ WebSocket закрыт: код={close_status_code}")
        
        if self.is_running:
            logger.info("🔄 Попытка переподключения через 5 секунд...")
            time.sleep(5)

    def add_order_callback(self, callback):
        """Добавляет коллбэк для ордеров"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)
            logger.info(f"➕ Добавлен order callback ({len(self.order_callbacks)} всего)")
        else:
            logger.warning("⚠️ Order callback уже существует, пропускаем")

    def add_position_callback(self, callback):
        """Добавляет коллбэк для позиций"""
        if callback not in self.position_callbacks:
            self.position_callbacks.append(callback)
            logger.info(f"➕ Добавлен position callback ({len(self.position_callbacks)} всего)")
        else:
            logger.warning("⚠️ Position callback уже существует, пропускаем")

    def get_positions(self):
        """Возвращает текущие позиции"""
        return self.current_positions.copy()

    def get_balances(self):
        """Возвращает текущие балансы"""
        return self.current_balances.copy()

    def get_stats(self):
        """Возвращает расширенную статистику"""
        stats = self.stats.copy()
        stats['is_connected'] = self.is_connected
        stats['is_running'] = self.is_running
        stats['cache_size'] = len(self.processed_messages)
        stats['duplicate_rate'] = round(
            (self.stats['messages_duplicated'] / max(1, self.stats['messages_received'])) * 100, 2
        )
        
        if self.stats['connection_time']:
            duration = datetime.now() - self.stats['connection_time']
            stats['connection_duration'] = str(duration).split('.')[0]
        
        return stats





    def _monitor_ping(self):
        """Мониторинг ping каждые 5 минут"""
        while self.is_running:
            try:
                time.sleep(300)  # 5 минут
                
                if not self.is_running:
                    break

                    logger.warning(f"=== Проверка ping, last_ping_time = {self.last_ping_time} ===")

                
                # Проверяем время последнего ping
                # self.last_ping_time = datetime.now() - timedelta(minutes=10)
                if self.last_ping_time:
                    time_since_ping = datetime.now() - self.last_ping_time
                    
                    if time_since_ping.total_seconds() > 300:  # 5 минут
                        logger.warning(f"Нет ping уже {time_since_ping.total_seconds():.0f} секунд")
                        
                        if not self.recovery_active:
                            self.start_recovery()
                    else:
                        logger.debug(f"Ping OK - последний {time_since_ping.total_seconds():.0f} секунд назад")
                else:
                    logger.warning("Ping еще не получен с момента запуска")
                    # Если WebSocket работает больше 5 минут без ping
                    if hasattr(self.stats, 'connection_time') and self.stats['connection_time']:
                        connection_duration = datetime.now() - self.stats['connection_time']
                        if connection_duration.total_seconds() > 300:
                            if not self.recovery_active:
                                self.start_recovery()
                                
            except Exception as e:
                logger.error(f"Ошибка в мониторе ping: {e}")

    def start_recovery(self):
        logger.warning("=== ВЫЗОВ start_recovery() ===")
        """Запуск автовосстановления через order_history"""
        if self.recovery_active:
            logger.warning("=== recovery_active уже True, выходим ===")
            return
        
        self.recovery_active = True
        logger.info("Запуск автовосстановления данных - WebSocket неактивен")
        
        self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True, name="WebSocket-Recovery")
        self.recovery_thread.start()

    def stop_recovery(self):
        """Остановка автовосстановления"""
        self.recovery_active = False
        logger.info("Автовосстановление остановлено")

    def _recovery_loop(self):
        logger.warning("=== ЗАПУСК _recovery_loop ===")
        """Цикл восстановления данных"""
        first_recovery = True
        
        while self.recovery_active and self.is_running:
            try:
                # Первое восстановление - за 15 минут
                if first_recovery:
                    minutes_back = 15
                    first_recovery = False
                    logger.info(f"Первое восстановление за последние {minutes_back} минут")
                else:
                    minutes_back = 2
                    logger.info(f"Восстановление за последние {minutes_back} минут")
                
                # Вычисляем даты
                end_date = datetime.now()
                start_date = end_date - timedelta(minutes=minutes_back)
                
                # Импортируем и вызываем восстановление
                try:
                    logger.warning("=== Пытаемся импортировать order_restore_manager ===")
                    from .order_restore import order_restore_manager
                    logger.warning("=== Импорт успешен ===")
                    success, message = order_restore_manager.restore_orders(
                        start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    
                    if success:
                        logger.info(f"Восстановление успешно: {message}")
                    else:
                        logger.warning(f"Ошибка восстановления: {message}")
                        
                except Exception as e:
                    logger.error(f"Критическая ошибка восстановления: {e}")
                
                # Ждем минуту до следующего восстановления
                if self.recovery_active:
                    time.sleep(60)
                    
            except Exception as e:
                logger.error(f"Ошибка в цикле восстановления: {e}")
                time.sleep(60)





    def stop(self):
        """Останавливает мониторинг"""
        logger.info("Остановка WebSocket мониторинга...")
        
        with self._start_lock:
            self._started = False
            
        self.is_running = False
        self.is_connected = False
        
        # Остановить восстановление
        self.stop_recovery()
        
        if self.ws:
            self.ws.close()
        
        logger.info("WebSocket мониторинг остановлен")