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
import threading
import traceback
import queue
from datetime import timedelta

from .database import db_manager
from .sockets_database import sockets_db_manager

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
        
        # ДОБАВЛЕНО: Очередь для отложенной обработки ордеров
        self.order_queue = queue.Queue()
        self.order_processor_thread = None
        
        # Статистика
        self.stats = {
            'messages_received': 0,
            'orders_updated': 0,
            'positions_updated': 0,
            'connection_time': None,
            'last_message_time': None,
            'reconnect_count': 0,
            'orders_queued': 0,        # ДОБАВЛЕНО
            'orders_processed': 0,      # ДОБАВЛЕНО
            'messages_saved_to_db': 0   # ДОБАВЛЕНО: счетчик сохраненных сообщений
        }

    def start(self):
        """Запускает WebSocket мониторинг"""
        if self.is_running:
            logger.warning("WebSocket уже запущен")
            return
        
        self.is_running = True
        
        # ДОБАВЛЕНО: Запускаем обработчик очереди ордеров
        self._start_order_processor()
        
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
        """Получено сообщение с детальным логированием"""
        try:
            # Парсим сообщение
            data = json.loads(message)
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            event_type = data.get('e', 'UNKNOWN')
            
            # Сохраняем сообщение в базу сокетов
            self._save_socket_message_to_db(data, message)

            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВСЕХ ТИПОВ СООБЩЕНИЙ
            logger.info(f"📡 WebSocket получил: {event_type}")
            logger.info(f"📄 RAW сообщение: {message}")

            
            if event_type == 'ORDER_TRADE_UPDATE':
                order_data = data.get('o', {})
                
                # ЛОГИРУЕМ ВСЕ ПОЛЯ ОРДЕРА
                logger.info(f"🎯 ДЕТАЛИ ОРДЕРА:")
                logger.info(f"   orderId (i): {order_data.get('i', 'N/A')}")
                logger.info(f"   symbol (s): {order_data.get('s', 'N/A')}")
                logger.info(f"   status (X): {order_data.get('X', 'N/A')}")
                logger.info(f"   side (S): {order_data.get('S', 'N/A')}")
                logger.info(f"   executedQty (z): {order_data.get('z', 'N/A')}")
                logger.info(f"   avgPrice (ap): {order_data.get('ap', 'N/A')}")
                logger.info(f"   origQty (q): {order_data.get('q', 'N/A')}")
                logger.info(f"   price (p): {order_data.get('p', 'N/A')}")
                logger.info(f"   commission (n): {order_data.get('n', 'N/A')}")
                logger.info(f"   commissionAsset (N): {order_data.get('N', 'N/A')}")
                logger.info(f"   realizedProfit (rp): {order_data.get('rp', 'N/A')}")
                logger.info(f"   orderType (o): {order_data.get('o', 'N/A')}")
                logger.info(f"   timeInForce (f): {order_data.get('f', 'N/A')}")
                logger.info(f"   workingType (wt): {order_data.get('wt', 'N/A')}")
                logger.info(f"   eventTime (T): {order_data.get('T', 'N/A')}")
                logger.info(f"   orderTradeTime (T): {order_data.get('T', 'N/A')}")
                
                # Вызываем обработку
                logger.info(f"🔄 Передаём ордер на обработку...")
                self._handle_order_update(data)
                
            elif event_type == 'ACCOUNT_UPDATE':
                account_data = data.get('a', {})
                
                # ЛОГИРУЕМ ДЕТАЛИ АККАУНТА
                logger.info(f"💰 ДЕТАЛИ АККАУНТА:")
                logger.info(f"   eventType: {data.get('e', 'N/A')}")
                logger.info(f"   eventTime: {data.get('E', 'N/A')}")
                logger.info(f"   transactionTime: {data.get('T', 'N/A')}")
                
                # Балансы
                balances = account_data.get('B', [])
                logger.info(f"   📊 Балансы ({len(balances)} активов):")
                for bal in balances[:3]:  # Показываем первые 3
                    asset = bal.get('a', 'N/A')
                    wallet_balance = bal.get('wb', 'N/A')
                    cross_balance = bal.get('cw', 'N/A')
                    logger.info(f"      {asset}: wallet={wallet_balance}, cross={cross_balance}")
                
                # Позиции
                positions = account_data.get('P', [])
                active_positions = [p for p in positions if float(p.get('pa', 0)) != 0]
                logger.info(f"   🎯 Позиции: всего={len(positions)}, активных={len(active_positions)}")
                for pos in active_positions:
                    symbol = pos.get('s', 'N/A')
                    amount = pos.get('pa', 'N/A')
                    side = pos.get('ps', 'N/A')
                    entry_price = pos.get('ep', 'N/A')
                    pnl = pos.get('up', 'N/A')
                    logger.info(f"      {symbol}: {side} {amount} @ {entry_price} (PnL: {pnl})")
                
                self._handle_account_update(data)
                
            elif event_type == 'listenKeyExpired':
                logger.warning("⚠️ Listen key истёк - переподключение...")
                self.ws.close()
                
            else:
                # ЛОГИРУЕМ НЕИЗВЕСТНЫЕ ТИПЫ СООБЩЕНИЙ
                logger.info(f"🔸 НЕИЗВЕСТНЫЙ ТИП СОБЫТИЯ: {event_type}")
                logger.info(f"📋 Доступные ключи: {list(data.keys())}")
                logger.info(f"📄 Полное сообщение: {json.dumps(data, indent=2)}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            logger.error(f"📄 Сырое сообщение: {message}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            logger.error(f"📄 Сообщение: {message}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")





    def _handle_order_update(self, data):
        """Обрабатывает обновления ордеров с детальным логированием"""
        try:
            order = data.get('o', {})
            
            order_id = order.get('i')
            status = order.get('X')
            symbol = order.get('s')
            side = order.get('S')
            executed_qty = float(order.get('z', 0))
            avg_price = float(order.get('ap', 0))
            
            logger.info(f"📊 ОБРАБОТКА ОРДЕРА:")
            logger.info(f"   🎯 OrderID: {order_id}")
            logger.info(f"   📈 Symbol: {symbol}")
            logger.info(f"   🔄 Status: {status}")
            logger.info(f"   ↗️ Side: {side}")
            logger.info(f"   💰 ExecutedQty: {executed_qty}")
            logger.info(f"   💵 AvgPrice: {avg_price}")
            
            # Определяем задержку
            if status == 'NEW':
                delay_seconds = 3
            elif status in ['PARTIALLY_FILLED', 'FILLED']:
                delay_seconds = 1
            else:
                delay_seconds = 2
            
            logger.info(f"⏰ Задержка для статуса '{status}': {delay_seconds} секунд")
            
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
                queue_size = self.order_queue.qsize()
                logger.info(f"📋 Ордер {order_id} ДОБАВЛЕН В ОЧЕРЕДЬ")
                logger.info(f"   ⏰ Задержка: {delay_seconds} секунд")
                logger.info(f"   📊 Размер очереди: {queue_size}")
                logger.info(f"   🕐 Время обработки: {process_time.strftime('%H:%M:%S')}")
                
            except queue.Full:
                logger.warning(f"⚠️ ОЧЕРЕДЬ ПЕРЕПОЛНЕНА - обрабатываем немедленно")
                self._update_order_in_database_direct(order_id, status, executed_qty, avg_price, order)
            
            # Коллбэки
            for callback in self.order_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"❌ Ошибка в order callback: {e}")
            
            self.stats['orders_updated'] += 1
            logger.info(f"✅ Ордер {order_id} обработан (всего обработано: {self.stats['orders_updated']})")
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в _handle_order_update: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")



    def _on_error(self, ws, error):
        """Ошибка WebSocket"""
        logger.error(f"❌ WebSocket ошибка: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket закрыт"""
        self.is_connected = False
        logger.warning(f"⚠️ WebSocket закрыт: код={close_status_code}, сообщение={close_msg}")
        
        # ИСПРАВЛЕНИЕ: Попытка переподключения
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
            
            # Вызываем коллбэки
            for callback in self.position_callbacks:
                try:
                    callback(self.current_positions)
                except:
                    pass
            
            self.stats['positions_updated'] += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки аккаунта: {e}")
    

    def _update_order_in_database_direct(self, order_id, status, executed_qty, avg_price, full_order_data):
        """Обновляет ордер в базе данных"""
        logger.info(f"🔍 ПОИСК ОРДЕРА {order_id} В БАЗЕ ДАННЫХ")
        logger.info(f"   📊 Статус: {status}")
        logger.info(f"   💰 ExecutedQty: {executed_qty}")
        logger.info(f"   💵 AvgPrice: {avg_price}")
        try:
            logger.info(f"🔍 Ищем ордер {order_id} в БД...") 
            
            # Ищем запись в БД
            with sqlite3.connect(db_manager.db_file) as conn:
                cursor = conn.cursor()
                
                # ИСПРАВЛЕНИЕ 1: Более простой поиск без JSON_EXTRACT
                # Ищем по вхождению order_id в extra_data или message
                cursor.execute("""
                SELECT id, extra_data, message, result FROM signals 
                WHERE (extra_data LIKE ? OR extra_data LIKE ? OR message LIKE ?)
                ORDER BY id DESC LIMIT 5
                """, (f'%{order_id}%', f'%"orderId": {order_id}%', f'%{order_id}%'))
                
                results = cursor.fetchall()
                
                if not results:
                    logger.warning(f"⚠️ Ордер {order_id} не найден в БД")
                    return
                
                # Ищем наиболее подходящую запись
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
                    
                    # Проверяем message (для старых записей)
                    if message_json:
                        try:
                            message_data = json.loads(message_json)
                            if str(message_data.get('orderId')) == str(order_id):
                                target_record = record
                                break
                        except:
                            pass
                
                if not target_record:
                    logger.warning(f"⚠️ Ордер {order_id} найден в БД, но не удалось распарсить данные")
                    return
                
                signal_id, extra_data_json, message_json, current_result = target_record
                
                # Парсим extra_data
                try:
                    extra_data = json.loads(extra_data_json) if extra_data_json else {}
                except:
                    extra_data = {}
                
                # ИСПРАВЛЕНИЕ 2: Добавляем более детальные WebSocket данные
                ws_update_data = {
                    'ws_status': status,
                    'ws_executed_qty': float(executed_qty),
                    'ws_avg_price': float(avg_price),
                    'ws_last_update': datetime.now().isoformat(),
                    'ws_update_count': extra_data.get('ws_update_count', 0) + 1
                }
                
                # Добавляем дополнительные поля из WebSocket если есть
                if 'n' in full_order_data:  # commission
                    ws_update_data['ws_commission'] = float(full_order_data['n'])
                if 'rp' in full_order_data:  # realized profit
                    ws_update_data['ws_realized_profit'] = float(full_order_data['rp'])
                if 'ap' in full_order_data and float(full_order_data['ap']) > 0:
                    ws_update_data['ws_avg_price'] = float(full_order_data['ap'])
                
                # Обновляем extra_data
                extra_data.update(ws_update_data)
                
                # ИСПРАВЛЕНИЕ 3: Улучшенное определение результата
                new_result = current_result  # По умолчанию оставляем текущий
                
                if status == 'FILLED':
                    new_result = 'success'
                elif status == 'PARTIALLY_FILLED':
                    new_result = 'partial'
                elif status in ['CANCELED', 'EXPIRED', 'REJECTED']:
                    new_result = 'error'
                elif status == 'NEW':
                    new_result = 'pending'
                
                # Сохраняем обратно в БД
                cursor.execute("""
                    UPDATE signals 
                    SET result = ?, extra_data = ?
                    WHERE id = ?
                """, (new_result, json.dumps(extra_data, ensure_ascii=False), signal_id))
                
                conn.commit()
                
                logger.info(f"✅ Обновлен сигнал #{signal_id}: {status} -> {new_result}")
                logger.debug(f"📊 WebSocket данные: executed={executed_qty}, avg_price={avg_price}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления БД: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")

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
        stats['queue_size'] = self.order_queue.qsize()  # ДОБАВЛЕНО
        
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
        
        if not self.order_queue.empty():
            logger.info("⏳ Ожидание завершения обработки очереди...")
            try:
                self.order_queue.join()
            except:
                pass


    def _start_order_processor(self):
        """Запускает обработчик очереди ордеров"""
        if self.order_processor_thread and self.order_processor_thread.is_alive():
            return
            
        self.order_processor_thread = threading.Thread(target=self._process_order_queue, daemon=True)
        self.order_processor_thread.start()
        logger.info("🔄 Обработчик очереди ордеров запущен")



    def _process_order_queue(self):
        """Обрабатывает очередь ордеров с детальным логированием"""
        logger.info(f"🔄 ЗАПУЩЕН ОБРАБОТЧИК ОЧЕРЕДИ ОРДЕРОВ")
        
        while self.is_running:
            try:
                # Ждем ордер из очереди
                logger.debug(f"⏳ Ожидание ордера из очереди...")
                order_data = self.order_queue.get(timeout=1)
                
                order_id = order_data.get('order_id')
                process_time = order_data.get('process_time')
                status = order_data.get('status')
                
                logger.info(f"📦 ИЗВЛЕЧЕН ОРДЕР ИЗ ОЧЕРЕДИ:")
                logger.info(f"   🎯 OrderID: {order_id}")
                logger.info(f"   🔄 Status: {status}")
                logger.info(f"   🕐 Запланированное время: {process_time.strftime('%H:%M:%S.%f')[:-3]}")
                
                # Ждем до времени обработки
                now = datetime.now()
                if process_time > now:
                    sleep_time = (process_time - now).total_seconds()
                    if sleep_time > 0:
                        logger.info(f"⏳ ОЖИДАНИЕ {sleep_time:.1f} секунд до обработки ордера {order_id}")
                        time.sleep(sleep_time)
                
                # Обрабатываем ордер
                actual_time = datetime.now()
                logger.info(f"🚀 НАЧИНАЕМ ОБРАБОТКУ ОРДЕРА {order_id}")
                logger.info(f"   🕐 Фактическое время: {actual_time.strftime('%H:%M:%S.%f')[:-3]}")
                
                self._update_order_in_database_direct(
                    order_data['order_id'],
                    order_data['status'], 
                    order_data['executed_qty'],
                    order_data['avg_price'],
                    order_data['full_order_data']
                )
                
                self.stats['orders_processed'] += 1
                self.order_queue.task_done()
                
                logger.info(f"✅ ОРДЕР {order_id} ОБРАБОТАН УСПЕШНО")
                logger.info(f"📊 Статистика: обработано={self.stats['orders_processed']}, в очереди={self.order_queue.qsize()}")
                
            except queue.Empty:
                # Таймаут - это нормально
                continue
            except Exception as e:
                logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в обработчике очереди: {e}")
                import traceback
                logger.error(f"💥 Traceback: {traceback.format_exc()}")


    def _save_socket_message_to_db(self, data, raw_message):
        """Сохраняет WebSocket сообщение в базу данных сокетов"""
        try:
            event_type = data.get('e', 'UNKNOWN')
            symbol = None
            order_id = None
            status = None
            
            # Извлекаем данные в зависимости от типа события
            if event_type == 'ORDER_TRADE_UPDATE':
                order_data = data.get('o', {})
                symbol = order_data.get('s')
                order_id = str(order_data.get('i')) if order_data.get('i') else None
                status = order_data.get('X')
                
            elif event_type == 'ACCOUNT_UPDATE':
                # Для ACCOUNT_UPDATE берем первый символ из позиций
                account_data = data.get('a', {})
                positions = account_data.get('P', [])
                if positions:
                    symbol = positions[0].get('s')
            
            # Сохраняем в базу сокетов
            socket_id = sockets_db_manager.log_socket_message(
                event_type=event_type,
                symbol=symbol,
                order_id=order_id,
                status=status,
                raw_message=raw_message
            )
            
            # Увеличиваем счетчик сохраненных сообщений
            self.stats['messages_saved_to_db'] += 1
            
            logger.debug(f"💾 Сокет сообщение сохранено в БД: ID #{socket_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сокет сообщения в БД: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")
