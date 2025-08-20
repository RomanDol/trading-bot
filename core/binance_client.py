"""
Модуль для работы с Binance Futures API
"""
import os
import math
import logging
from typing import Tuple, Dict, Any
from binance.um_futures import UMFutures
from dotenv import load_dotenv
import json
import threading

from .websocket_monitor import SimpleBinanceWebSocket

# Настройка логирования
logger = logging.getLogger(__name__)

load_dotenv()

class BinanceClient:
    """Класс для работы с Binance Futures API"""
    
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY и BINANCE_API_SECRET должны быть установлены в .env файле")
        
        self.client = UMFutures(key=self.api_key, secret=self.api_secret)
        self.symbol_step_cache = {}
        
        # Загружаем stepSize для всех символов при инициализации
        self._load_step_sizes()
    
    def _load_step_sizes(self):
        """Загружает stepSize из exchangeInfo один раз"""
        try:
            info = self.client.exchange_info()
            for symbol_info in info["symbols"]:
                symbol = symbol_info["symbol"]
                for filter_info in symbol_info["filters"]:
                    if filter_info["filterType"] == "LOT_SIZE":
                        self.symbol_step_cache[symbol] = float(filter_info["stepSize"])
                        break
            
            logger.info(f"✅ Загружено {len(self.symbol_step_cache)} stepSize для символов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки stepSize: {e}")
            # В случае ошибки используем базовые значения
            self.symbol_step_cache = {}
    
    def adjust_quantity(self, symbol: str, qty: float) -> float:
        """Округляет quantity по stepSize для конкретного символа"""
        step = self.symbol_step_cache.get(symbol)
        if not step:
            logger.warning(f"⚠️ stepSize для {symbol} не найден, используем 3 знака")
            return round(qty, 3)
        
        # Вычисляем количество знаков после запятой для данного stepSize
        precision = abs(int(round(math.log10(step))))
        adjusted_qty = round(qty, precision)
        
        logger.debug(f"📐 {symbol}: {qty} -> {adjusted_qty} (step: {step}, precision: {precision})")
        return adjusted_qty
    
    def check_position_mode(self) -> Dict[str, Any]:
        """Проверяет режим позиций (Hedge/One-way)"""
        try:
            mode = self.client.get_position_mode()
            logger.info(f"🔍 Hedge mode status (dualSidePosition): {mode}")
            return mode
        except Exception as e:
            logger.error(f"❌ Failed to check position mode: {e}")
            return {}
    
    def open_position(self, symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
        """
        Открывает позицию
        
        Args:
            symbol: Торговый символ (например, BTCUSDT)
            side: Направление позиции ('LONG' или 'SHORT')
            quantity: Количество
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            # Подгоняем количество под требования Binance
            adjusted_quantity = self.adjust_quantity(symbol, quantity)
            
            # Определяем параметры ордера
            order_side = 'BUY' if side == 'LONG' else 'SELL'
            position_side = 'LONG' if side == 'LONG' else 'SHORT'
            
            logger.info(f"📤 Отправка ордера: {symbol} {order_side} {adjusted_quantity} (позиция: {position_side})")
            
            response = self.client.new_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=adjusted_quantity,
                positionSide=position_side
            )
            
            logger.info(f"✅ Ордер размещен: {response}")
            
            # Извлекаем полезную информацию из ответа
            order_id = response.get('orderId', 'N/A')
            filled_qty = response.get('executedQty', adjusted_quantity)
            avg_price = response.get('avgPrice', 'N/A')
            
            return True, json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка размещения ордера: {e}")
            
            error_data = {
                "error": True,
                "error_message": str(e),
                "symbol": symbol,
                "side": order_side,
                "position_side": position_side
            }
            
            return False, json.dumps(error_data, ensure_ascii=False)
    
    def close_position(self, symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
        """
        Закрывает позицию
        
        Args:
            symbol: Торговый символ
            side: Направление закрываемой позиции ('LONG' или 'SHORT')
            quantity: Количество для закрытия
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            # Подгоняем количество под требования Binance
            adjusted_quantity = self.adjust_quantity(symbol, quantity)
            
            # Определяем параметры ордера (противоположные открытию)
            order_side = 'SELL' if side == 'LONG' else 'BUY'
            position_side = 'LONG' if side == 'LONG' else 'SHORT'
            
            logger.info(f"📤 Закрытие позиции: {symbol} {order_side} {adjusted_quantity} (позиция: {position_side})")
            
            response = self.client.new_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=adjusted_quantity,
                positionSide=position_side
            )
            
            logger.info(f"✅ Позиция закрыта: {response}")
            
            # Извлекаем информацию из ответа
            order_id = response.get('orderId', 'N/A')
            filled_qty = response.get('executedQty', adjusted_quantity)
            avg_price = response.get('avgPrice', 'N/A')
            
            return True, json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"Ошибка закрытия позиции: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def get_account_info(self) -> Dict[str, Any]:
        """Получает информацию об аккаунте"""
        try:
            account_info = self.client.account()
            return account_info
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об аккаунте: {e}")
            return {}
    
    def get_positions(self) -> list:
        """Получает текущие позиции"""
        try:
            positions = self.client.get_position_risk()
            # Фильтруем только позиции с ненулевым размером
            active_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
            return active_positions
        except Exception as e:
            logger.error(f"❌ Ошибка получения позиций: {e}")
            return []

# Создаем глобальный экземпляр для использования в приложении
binance_client = BinanceClient()




# ===== WEBSOCKET ИНТЕГРАЦИЯ =====
from .websocket_monitor import SimpleBinanceWebSocket
import threading
import atexit

class BinanceClientWithWebSocket(BinanceClient):
    """Binance клиент с WebSocket мониторингом"""
    
    def __init__(self):
        super().__init__()
        self.ws_monitor = None
        self._init_attempted = False
        
        # ИСПРАВЛЕНИЕ: Принудительная инициализация
        self._ensure_websocket_initialized()
    
    def _ensure_websocket_initialized(self):
        """Обеспечивает инициализацию WebSocket"""
        if self._init_attempted:
            return
            
        self._init_attempted = True
        
        try:
            logger.info("🚀 Принудительная инициализация WebSocket...")
            self._start_websocket()
        except Exception as e:
            logger.error(f"❌ Ошибка принудительной инициализации: {e}")
    
    def _start_websocket(self):
        """Запускает WebSocket мониторинг"""
        try:
            logger.info("🔧 Создание WebSocket monitor...")
            
            self.ws_monitor = SimpleBinanceWebSocket(self.api_key, self.api_secret)
            
            # Добавляем коллбэки
            self.ws_monitor.add_order_callback(self._on_order_update)
            self.ws_monitor.add_position_callback(self._on_position_update)
            
            # Запускаем в отдельном потоке
            self.ws_monitor.start()
            
            # Регистрируем очистку при завершении
            atexit.register(self._cleanup_websocket)
            
            logger.info("✅ WebSocket мониторинг запущен успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска WebSocket: {e}")
            import traceback
            logger.error(f"💥 Traceback: {traceback.format_exc()}")
            self.ws_monitor = None
    
    def _cleanup_websocket(self):
        """Очистка WebSocket при завершении"""
        if self.ws_monitor:
            try:
                self.ws_monitor.stop()
                logger.info("🛑 WebSocket остановлен")
            except:
                pass
    
    def _on_order_update(self, order_data):
        """Коллбэк для обновлений ордеров"""
        symbol = order_data.get('s')
        status = order_data.get('X')
        order_id = order_data.get('i')
        logger.info(f"📞 WebSocket коллбэк: ордер {order_id} {symbol} -> {status}")
    
    def _on_position_update(self, positions):
        """Коллбэк для обновлений позиций"""
        active_positions = len([p for p in positions.values() if p.get('amount', 0) != 0])
        logger.debug(f"📊 WebSocket коллбэк: {active_positions} активных позиций")
    
    def get_realtime_positions(self):
        """Получает позиции в реальном времени"""
        self._ensure_websocket_initialized()
        if self.ws_monitor:
            return self.ws_monitor.get_positions()
        return {}
    
    def get_realtime_balances(self):
        """Получает балансы в реальном времени"""
        self._ensure_websocket_initialized()
        if self.ws_monitor:
            return self.ws_monitor.get_balances()
        return {}
    
    def get_websocket_stats(self):
        """Получает статистику WebSocket"""
        self._ensure_websocket_initialized()
        if self.ws_monitor:
            return self.ws_monitor.get_stats()
        return {"is_connected": False, "error": "WebSocket not initialized"}

# ИСПРАВЛЕНИЕ: Создание глобального экземпляра с обработкой ошибок
def create_binance_client():
    """Фабрика для создания Binance клиента"""
    try:
        logger.info("🏗️ Создание BinanceClientWithWebSocket...")
        client = BinanceClientWithWebSocket()
        logger.info("✅ BinanceClientWithWebSocket создан успешно")
        return client
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания WebSocket клиента: {e}")
        logger.warning("🔄 Fallback на обычный BinanceClient...")
        
        try:
            client = BinanceClient()
            logger.info("✅ Обычный BinanceClient создан как fallback")
            return client
        except Exception as e2:
            logger.error(f"❌ Критическая ошибка создания клиента: {e2}")
            raise

# Создаем глобальный экземпляр
binance_client = create_binance_client()

# ИСПРАВЛЕНИЕ: Принудительная инициализация при импорте
def force_websocket_init():
    """Принудительная инициализация WebSocket при импорте"""
    if hasattr(binance_client, '_ensure_websocket_initialized'):
        binance_client._ensure_websocket_initialized()

# Вызываем принудительную инициализацию
force_websocket_init()

logger.info(f"🎯 Binance клиент готов: {type(binance_client).__name__}")

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля binance_client...")
    
    try:
        client = BinanceClient()
        
        # Тест подгонки количества
        test_qty = client.adjust_quantity("BTCUSDT", 0.12345678)
        print(f"✅ Подгонка количества: 0.12345678 -> {test_qty}")
        
        # Тест проверки режима позиций
        mode = client.check_position_mode()
        print(f"✅ Режим позиций: {mode}")
        
        # Тест получения позиций (только если есть API ключи)
        positions = client.get_positions()
        print(f"✅ Активных позиций: {len(positions)}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        print("💡 Убедитесь, что API ключи настроены в .env файле")