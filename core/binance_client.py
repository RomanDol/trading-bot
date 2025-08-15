"""
Модуль для работы с Binance Futures API
"""
import os
import math
import logging
from typing import Tuple, Dict, Any
from binance.um_futures import UMFutures
from dotenv import load_dotenv

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
            
            success_msg = f"Ордер #{order_id} исполнен: {filled_qty} @ {avg_price}"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Ошибка размещения ордера: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
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
            
            success_msg = f"Позиция закрыта #{order_id}: {filled_qty} @ {avg_price}"
            return True, success_msg
            
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