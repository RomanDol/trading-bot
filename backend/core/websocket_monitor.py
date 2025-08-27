"""
Исправленный WebSocket мониторинг для Binance Futures БЕЗ ДУБЛИРОВАНИЯ
"""
import json
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Set
import websocket
import requests
import queue
import hashlib

from .database import db_manager
from .sockets_database import sockets_db_manager
from .messages_database import messages_db_manager

logger = logging.getLogger(__name__)

class SimpleBinanceWebSocket:
    """Простой WebSocket мониторинг Binance БЕЗ ДУБЛИРОВАНИЯ"""
    
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
        
        # ИСПРАВЛЕНИЕ 1: Убираем множественные коллбэки
        self.order_callbacks = []
        self.position_callbacks = []
        
        # Данные
        self.current_positions = {}
        self.current_balances = {}
        
        # ИСПРАВЛЕНИЕ 2: Дедупликация сообщений
        self.processed_messages = set()  # Хэши обработанных сообщений
        self.message_cache_size = 1000   # Максимум хэшей в кэше
        
        # ИСПРАВЛЕНИЕ 3: Единственная очередь и поток
        self.order_queue = queue.Queue()
        self.order_processor_thread = None
        self._processor_lock = threading.Lock()
        
        # ИСПРАВЛЕНИЕ 4: Защита от повторного запуска
        self._start_lock = threading.Lock()
        self._started = False
        
        # Статистика
        self.stats = {
            'messages_received': 0,
            'messages_duplicated': 0,  # НОВОЕ: счетчик дубликатов
            'orders_updated': 0,
            'positions_updated': 0,
            'connection_time': None,
            'last_message_time': None,
            'reconnect_count': 0,
            'orders_queued': 0,
            'orders_processed': 0,
            'messages_saved_to_db': 0
        }

    def start(self):
        """Запускает WebSocket мониторинг (ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА)"""
        with self._start_lock:
            if self._started or self.is_running:
                logger.warning("⚠️ WebSocket уже запущен, игнорируем повторный вызов")
                return False
            
            self._started = True
            self.is_running = True
            
            logger.info("🚀 ПЕРВИЧНЫЙ запуск WebSocket мониторинга")
        
        # Запускаем обработчик очереди ОДИН РАЗ
        self._start_order_processor()
        
        # Запускаем основной WebSocket поток
        thread = threading.Thread(target=self._run_websocket, daemon=True, name="WebSocket-Main")
        thread.start()
        
        # Поток для поддержания listen_key
        keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True, name="WebSocket-Keepalive")
        keepalive_thread.start()
        
        logger.info("✅ WebSocket мониторинг запущен")
        return True

    def _generate_message_hash(self, raw_message: str) -> str:
        """Генерирует уникальный хэш для сообщения"""
        try:
            # Парсим JSON для извлечения ключевых полей
            data = json.loads(raw_message)
            
            # Создаем ключ для дедупликации на основе критичных полей
            if data.get('e') == 'ORDER_TRADE_UPDATE':
                order_data = data.get('o', {})
                dedup_key = f"ORDER:{order_data.get('i')}:{order_data.get('X')}:{order_data.get('T')}"
            elif data.get('e') == 'ACCOUNT_UPDATE':
                dedup_key = f"ACCOUNT:{data.get('E')}:{data.get('T')}"
            else:
                dedup_key = f"{data.get('e')}:{data.get('E')}"
            
            return hashlib.md5(dedup_key.encode()).hexdigest()
            
        except:
            # Fallback - хэш всего сообщения
            return hashlib.md5(raw_message.encode()).hexdigest()

    def _is_duplicate_message(self, message_hash: str) -> bool:
        """Проверяет является ли сообщение дубликатом"""
        if message_hash in self.processed_messages:
            return True
        
        # Добавляем хэш в кэш
        self.processed_messages.add(message_hash)
        
        # ИСПРАВЛЕНИЕ 5: Ограничиваем размер кэша
        if len(self.processed_messages) > self.message_cache_size:
            # Удаляем старые хэши (простейший LRU)
            old_hashes = list(self.processed_messages)[:100]
            for old_hash in old_hashes:
                self.processed_messages.discard(old_hash)
        
        return False

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
                
                # ИСПРАВЛЕНИЕ 6: Очищаем кэш дубликатов при переподключении
                self.processed_messages.clear()
                logger.info("🗑️ Кэш дубликатов очищен при переподключении")
                
                # Создаем WebSocket соединение
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                # Запускаем (блокирующий вызов)
                logger.info("🔌 Подключаение к WebSocket...")
                self.ws.run_forever()
                
            except Exception as e:
                logger.error(f"❌ Ошибка WebSocket: {e}")
                self.stats['reconnect_count'] += 1
                
                if self.is_running:
                    logger.info("🔄 Переподключение через 10 секунд...")
                    time.sleep(10)

    def _on_message(self, ws, message):
        """Получено сообщение с дедупликацией"""
        try:
            # ИСПРАВЛЕНИЕ 7: Дедупликация на самом раннем этапе
            message_hash = self._generate_message_hash(message)
            
            if self._is_duplicate_message(message_hash):
                self.stats['messages_duplicated'] += 1
                logger.debug(f"🔄 ДУБЛИКАТ пропущен (всего: {self.stats['messages_duplicated']})")
                return  # ПРОПУСКАЕМ ДУБЛИКАТ
            
            # Парсим сообщение
            data = json.loads(message)
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            event_type = data.get('e', 'UNKNOWN')
            
            # Сохраняем сообщение в базу сокетов ОДИН РАЗ
            self._save_socket_message_to_db(data, message)

            logger.info(f"📡 WebSocket получил: {event_type} (#{self.stats['messages_received']}, дубликатов: {self.stats['messages_duplicated']})")
            
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

    def _start_order_processor(self):
        """Запускает обработчик очереди ордеров (ТОЛЬКО ОДИН РАЗ)"""
        with self._processor_lock:
            if self.order_processor_thread and self.order_processor_thread.is_alive():
                logger.warning("⚠️ Обработчик очереди уже запущен")
                return
                
            self.order_processor_thread = threading.Thread(
                target=self._process_order_queue, 
                daemon=True,
                name="OrderProcessor"
            )
            self.order_processor_thread.start()
            logger.info("🔄 Обработчик очереди ордеров запущен")

    def _handle_order_update(self, data):
        """Обрабатывает обновления ордеров БЕЗ ДУБЛИРОВАНИЯ"""
        try:
            order = data.get('o', {})
            
            order_id = order.get('i')
            status = order.get('X')
            symbol = order.get('s')
            executed_qty = float(order.get('z', 0))
            avg_price = float(order.get('ap', 0))
            
            # ИСПРАВЛЕНИЕ 8: Проверяем что ордер еще не в очереди
            queue_items = []
            temp_queue = queue.Queue()
            
            # Проверяем очередь на наличие того же ордера
            duplicate_found = False
            while not self.order_queue.empty():
                try:
                    item = self.order_queue.get_nowait()
                    if item['order_id'] == order_id and item['status'] == status:
                        duplicate_found = True
                        logger.debug(f"🔄 Ордер {order_id}:{status} уже в очереди")
                    queue_items.append(item)
                except queue.Empty:
                    break
            
            # Возвращаем элементы в очередь
            for item in queue_items:
                self.order_queue.put(item)
            
            if duplicate_found:
                return  # Не добавляем дубликат в очередь
            
            # Определяем задержку
            if status == 'NEW':
                delay_seconds = 3
            elif status in ['PARTIALLY_FILLED', 'FILLED']:
                delay_seconds = 1
            else:
                delay_seconds = 2
            
            process_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            order_data = {
                'order_id': order_id,
                'status': status,
                'executed_qty': executed_qty,
                'avg_price': avg_price,
                'full_order_data': order,
                'process_time': process_time
            }
            
            # Добавляем в очередь
            try:
                self.order_queue.put_nowait(order_data)
                self.stats['orders_queued'] += 1
                logger.info(f"📋 Ордер {order_id}:{status} добавлен в очередь (задержка: {delay_seconds}с)")
                
            except queue.Full:
                logger.warning(f"⚠️ ОЧЕРЕДЬ ПЕРЕПОЛНЕНА - обрабатываем немедленно")
                self._update_order_in_database_direct(order_id, status, executed_qty, avg_price, order)
            
            # ИСПРАВЛЕНИЕ 9: Вызываем коллбэки ТОЛЬКО ОДИН РАЗ
            for callback in self.order_callbacks[:]:  # Копия списка
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"❌ Ошибка в order callback: {e}")
            
            self.stats['orders_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в _handle_order_update: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")

    def _process_order_queue(self):
        """Обрабатывает очередь ордеров"""
        logger.info(f"🔄 ЗАПУЩЕН ОБРАБОТЧИК ОЧЕРЕДИ ОРДЕРОВ (Thread: {threading.current_thread().name})")
        
        while self.is_running:
            try:
                # Ждем ордер из очереди
                order_data = self.order_queue.get(timeout=1)
                
                order_id = order_data.get('order_id')
                process_time = order_data.get('process_time')
                status = order_data.get('status')
                
                # Ждем до времени обработки
                now = datetime.now()
                if process_time > now:
                    sleep_time = (process_time - now).total_seconds()
                    if sleep_time > 0:
                        logger.debug(f"⏳ Ожидание {sleep_time:.1f}с для ордера {order_id}")
                        time.sleep(sleep_time)
                
                # Обрабатываем ордер
                logger.info(f"🚀 Обработка ордера {order_id}:{status}")
                
                self._update_order_in_database_direct(
                    order_data['order_id'],
                    order_data['status'], 
                    order_data['executed_qty'],
                    order_data['avg_price'],
                    order_data['full_order_data']
                )
                
                self.stats['orders_processed'] += 1
                self.order_queue.task_done()
                
                logger.info(f"✅ Ордер {order_id} обработан (всего: {self.stats['orders_processed']})")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в обработчике очереди: {e}")
                import traceback
                logger.error(f"💥 Traceback: {traceback.format_exc()}")

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
            
            # Вызываем коллбэки ОДИН РАЗ
            for callback in self.position_callbacks[:]:  # Копия списка
                try:
                    callback(self.current_positions)
                except Exception as e:
                    logger.error(f"❌ Ошибка в position callback: {e}")
            
            self.stats['positions_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки аккаунта: {e}")

    def _update_order_in_database_direct(self, order_id, status, executed_qty, avg_price, full_order_data):
        """Обновляет ордер в базе данных"""
        try:
            logger.info(f"🔍 Поиск ордера {order_id} в БД для обновления статуса {status}")
            
            with sqlite3.connect(db_manager.db_file) as conn:
                cursor = conn.cursor()
                
                # Поиск записи
                cursor.execute("""
                SELECT id, extra_data, message, result FROM signals 
                WHERE (extra_data LIKE ? OR extra_data LIKE ? OR message LIKE ?)
                ORDER BY id DESC LIMIT 5
                """, (f'%{order_id}%', f'%"orderId": {order_id}%', f'%{order_id}%'))
                
                results = cursor.fetchall()
                
                if not results:
                    logger.warning(f"⚠️ Ордер {order_id} не найден в БД")
                    return
                
                # Ищем подходящую запись
                target_record = None
                for record in results:
                    signal_id, extra_data_json, message_json, current_result = record
                    
                    # Проверяем extra_data
                    if extra_data_json:
                        try:
                            extra_data = json.loads(extra_data_json)
                            if str(extra_data.get('binance_order_id')) == str(order_id):
                                target_record = record
                                break
                        except:
                            pass
                    
                    # Проверяем message
                    if message_json:
                        try:
                            message_data = json.loads(message_json)
                            if str(message_data.get('orderId')) == str(order_id):
                                target_record = record
                                break
                        except:
                            pass
                
                if not target_record:
                    logger.warning(f"⚠️ Ордер {order_id} найден но не удалось распарсить")
                    return
                
                signal_id, extra_data_json, message_json, current_result = target_record
                
                # Обновляем extra_data
                try:
                    extra_data = json.loads(extra_data_json) if extra_data_json else {}
                except:
                    extra_data = {}
                
                # Добавляем WebSocket данные
                ws_update_data = {
                    'ws_status': status,
                    'ws_executed_qty': float(executed_qty),
                    'ws_avg_price': float(avg_price),
                    'ws_last_update': datetime.now().isoformat(),
                    'ws_update_count': extra_data.get('ws_update_count', 0) + 1
                }
                
                # Дополнительные поля
                if 'n' in full_order_data:
                    ws_update_data['ws_commission'] = float(full_order_data['n'])
                if 'rp' in full_order_data:
                    ws_update_data['ws_realized_profit'] = float(full_order_data['rp'])
                
                extra_data.update(ws_update_data)
                
                # Определяем результат
                new_result = current_result
                if status == 'FILLED':
                    new_result = 'success'
                elif status == 'PARTIALLY_FILLED':
                    new_result = 'partial'
                elif status in ['CANCELED', 'EXPIRED', 'REJECTED']:
                    new_result = 'error'
                elif status == 'NEW':
                    new_result = 'pending'
                
                # Обновляем в БД
                cursor.execute("""
                    UPDATE signals 
                    SET result = ?, extra_data = ?
                    WHERE id = ?
                """, (new_result, json.dumps(extra_data, ensure_ascii=False), signal_id))
                
                conn.commit()
                
                logger.info(f"✅ Обновлен сигнал #{signal_id}: {status} -> {new_result}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления БД: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")

    def _save_socket_message_to_db(self, data, raw_message):
        """Сохраняет WebSocket сообщение в базу данных сокетов"""
        try:
            event_type = data.get('e', 'UNKNOWN')
            symbol = None
            order_id = None
            status = None
            
            if event_type == 'ORDER_TRADE_UPDATE':
                order_data = data.get('o', {})
                symbol = order_data.get('s')
                order_id = str(order_data.get('i')) if order_data.get('i') else None
                status = order_data.get('X')
                
            elif event_type == 'ACCOUNT_UPDATE':
                account_data = data.get('a', {})
                positions = account_data.get('P', [])
                if positions:
                    symbol = positions[0].get('s')
            
            socket_id = sockets_db_manager.log_socket_message(
                event_type=event_type,
                symbol=symbol,
                order_id=order_id,
                status=status,
                raw_message=raw_message
            )
            
            self.stats['messages_saved_to_db'] += 1
            logger.debug(f"💾 Сокет сообщение #{socket_id} сохранено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сокет сообщения: {e}")


        # Также записываем в общую базу сообщений
        try:
            messages_db_manager.log_message(event_type, json.loads(raw_message))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось записать WebSocket сообщение в общую базу: {e}")




    def add_order_callback(self, callback):
        """Добавляет коллбэк для ордеров (ПРЕДОТВРАЩЕНИЕ ДУБЛИРОВАНИЯ)"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)
            logger.info(f"➕ Добавлен order callback ({len(self.order_callbacks)} всего)")
        else:
            logger.warning("⚠️ Order callback уже существует, пропускаем")

    def add_position_callback(self, callback):
        """Добавляет коллбэк для позиций (ПРЕДОТВРАЩЕНИЕ ДУБЛИРОВАНИЯ)"""
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
        stats['queue_size'] = self.order_queue.qsize()
        stats['cache_size'] = len(self.processed_messages)
        stats['duplicate_rate'] = round(
            (self.stats['messages_duplicated'] / max(1, self.stats['messages_received'])) * 100, 2
        )
        
        if self.stats['connection_time']:
            duration = datetime.now() - self.stats['connection_time']
            stats['connection_duration'] = str(duration).split('.')[0]
        
        return stats

    def stop(self):
        """Останавливает мониторинг"""
        logger.info("🛑 Остановка WebSocket мониторинга...")
        
        with self._start_lock:
            self._started = False
            
        self.is_running = False
        self.is_connected = False
        
        if self.ws:
            self.ws.close()
        
        # Ждем завершения очереди
        if not self.order_queue.empty():
            logger.info("⏳ Ожидание завершения обработки очереди...")
            try:
                self.order_queue.join()
            except:
                pass
        
        logger.info("✅ WebSocket мониторинг остановлен")