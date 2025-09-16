"""
Модуль для восстановления истории ордеров из Binance API
"""
import os
import time
import hmac
import hashlib
import requests
import logging
from datetime import datetime
from urllib.parse import urlencode
from typing import Dict, Any, Tuple
from dotenv import load_dotenv
import psycopg2
from decimal import Decimal
import json
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DATABASE', 'messages'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

class OrderRestoreManager:
    """Класс для восстановления истории ордеров"""
    
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY и BINANCE_API_SECRET должны быть установлены в .env файле")
        
        self.base_url = "https://fapi.binance.com"
    
    def get_connection(self):
        """Создает подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def clear_order_history_table(self):
        """Очищает таблицу order_history"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE order_history RESTART IDENTITY")
                conn.commit()
            logger.info("🗑️ Таблица order_history очищена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки таблицы order_history: {e}")
            raise
    
    def _create_signature(self, params: Dict[str, Any]) -> str:
        """Создает подпись для Binance API"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(), 
            query_string.encode(), 
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def fetch_orders_from_binance(self, start_time: int, end_time: int) -> Tuple[bool, Any]:
        """
        Загружает ордера из Binance API
        
        Args:
            start_time: Timestamp начала периода в миллисекундах
            end_time: Timestamp конца периода в миллисекундах
            
        Returns:
            Tuple[bool, Any]: (успех, данные или сообщение об ошибке)
        """
        try:
            params = {
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000,
                'timestamp': int(time.time() * 1000),
                'recvWindow': 5000
            }
            
            # Создаем подпись
            signature = self._create_signature(params)
            
            # Выполняем запрос
            query_string = urlencode(params)
            url = f"{self.base_url}/fapi/v1/allOrders?{query_string}&signature={signature}"
            
            headers = {'X-MBX-APIKEY': self.api_key}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                orders = response.json()
                logger.info(f"✅ Получено {len(orders)} ордеров из Binance API")
                return True, orders
            else:
                error_msg = f"Binance API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('msg', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "Timeout при запросе к Binance API"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Ошибка запроса к Binance API: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def save_orders_to_db(self, orders: list) -> Tuple[bool, str]:
        """
        Сохраняет ордера в таблицу order_history
        
        Args:
            orders: Список ордеров от Binance API
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                saved_count = 0
                for order in orders:
                    try:
                        # Извлекаем данные согласно структуре таблицы
                        updatetime_ms = order.get('updateTime')
                        updatetime = datetime.fromtimestamp(updatetime_ms / 1000) if updatetime_ms else None
                        symbol = order.get('symbol')
                        status = order.get('status')
                        executedqty = Decimal(str(order.get('executedQty', 0)))
                        avgprice = Decimal(str(order.get('avgPrice', 0)))
                        cumquote = Decimal(str(order.get('cumQuote', 0)))
                        order_type = order.get('type')
                        side = order.get('side')
                        positionside = order.get('positionSide')
                        orderid = order.get('orderId')
                        clientorderid = order.get('clientOrderId')
                        raw_msg = json.dumps(order, ensure_ascii=False)
                        
                        cursor.execute("""
                            INSERT INTO order_history 
                            (updatetime, symbol, status, executedqty, avgprice, cumquote, 
                             type, side, positionside, orderid, clientorderid, raw_msg)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (updatetime, symbol, status, executedqty, avgprice, cumquote,
                              order_type, side, positionside, orderid, clientorderid, raw_msg))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка сохранения ордера {order.get('orderId')}: {e}")
                        continue
                
                conn.commit()
                
                success_msg = f"Сохранено {saved_count} из {len(orders)} ордеров"
                logger.info(f"💾 {success_msg}")
                return True, success_msg
                
        except Exception as e:
            error_msg = f"Ошибка сохранения в базу данных: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def restore_orders(self, start_date: str, end_date: str) -> Tuple[bool, str]:
        """
        Основная функция восстановления ордеров
        
        Args:
            start_date: Дата начала в формате 'YYYY-MM-DD'
            end_date: Дата конца в формате 'YYYY-MM-DD'
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            # Конвертируем даты в timestamps
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            
            start_time = int(start_dt.timestamp() * 1000)
            end_time = int(end_dt.timestamp() * 1000)
            
            logger.info(f"🔄 Начало восстановления ордеров: {start_date} - {end_date}")
            
            # Шаг 1: Очищаем таблицу
            self.clear_order_history_table()
            
            # Шаг 2: Загружаем данные из Binance
            success, data = self.fetch_orders_from_binance(start_time, end_time)
            if not success:
                return False, f"Ошибка загрузки из Binance: {data}"
            
            # Шаг 3: Сохраняем в базу
            if not data:  # Пустой список
                return True, "За указанный период ордеров не найдено"
            
            success, message = self.save_orders_to_db(data)
            if not success:
                return False, message
            
            final_msg = f"Восстановление завершено успешно. {message}"
            logger.info(f"✅ {final_msg}")
            return True, final_msg
            
        except ValueError as e:
            error_msg = f"Неверный формат даты: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Критическая ошибка восстановления: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return False, error_msg

# Создаем глобальный экземпляр для использования в приложении
order_restore_manager = OrderRestoreManager()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля order_restore...")
    
    try:
        manager = OrderRestoreManager()
        
        # Тест восстановления за вчерашний день
        yesterday = datetime.now().strftime('%Y-%m-%d')
        
        success, message = manager.restore_orders(yesterday, yesterday)
        
        if success:
            print(f"✅ Тест успешен: {message}")
        else:
            print(f"❌ Тест неудачен: {message}")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()