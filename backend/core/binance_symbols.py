"""
Модуль для работы с таблицей binance_symbols
"""
import requests
import psycopg2
import psycopg2.extras
import logging
import os
from typing import Tuple, Dict, Any
from dotenv import load_dotenv
from decimal import Decimal

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

class BinanceSymbolsManager:
    """Класс для управления списком символов Binance"""
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com"
    
    def get_connection(self):
        """Создает подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def clear_table(self):
        """Очищает таблицу binance_symbols"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE binance_symbols RESTART IDENTITY")
                conn.commit()
            logger.info("🗑️ Таблица binance_symbols очищена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки таблицы: {e}")
            raise
    
    def fetch_symbols_from_binance(self) -> Tuple[bool, Any]:
        """
        Загружает список символов из Binance API
        
        Returns:
            Tuple[bool, Any]: (успех, данные или сообщение об ошибке)
        """
        try:
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get('symbols', [])
                logger.info(f"✅ Получено {len(symbols)} символов из Binance API")
                return True, symbols
            else:
                error_msg = f"Binance API error: {response.status_code}"
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
    
    def save_symbols_to_db(self, symbols: list) -> Tuple[bool, str]:
        """
        Сохраняет символы в таблицу binance_symbols
        
        Args:
            symbols: Список символов от Binance API
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                saved_count = 0
                for symbol_data in symbols:
                    try:
                        symbol = symbol_data.get('symbol')
                        
                        # Извлекаем notional из фильтров
                        notional = None
                        filters = symbol_data.get('filters', [])
                        for f in filters:
                            if f.get('filterType') == 'MIN_NOTIONAL':
                                notional = Decimal(str(f.get('notional', 0)))
                                break
                        
                        # Сохраняем в базу
                        cursor.execute("""
                            INSERT INTO binance_symbols (symbol, notional, msg_data)
                            VALUES (%s, %s, %s)
                        """, (symbol, notional, psycopg2.extras.Json(symbol_data)))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка сохранения символа {symbol_data.get('symbol')}: {e}")
                        continue
                
                conn.commit()
                
                success_msg = f"Сохранено {saved_count} из {len(symbols)} символов"
                logger.info(f"💾 {success_msg}")
                return True, success_msg
                
        except Exception as e:
            error_msg = f"Ошибка сохранения в базу данных: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def update_symbols(self) -> Tuple[bool, str]:
        """
        Основная функция обновления списка символов
        
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            logger.info("🔄 Начало обновления списка символов")
            
            # Шаг 1: Очищаем таблицу
            self.clear_table()
            
            # Шаг 2: Загружаем данные из Binance
            success, data = self.fetch_symbols_from_binance()
            if not success:
                return False, f"Ошибка загрузки из Binance: {data}"
            
            # Шаг 3: Сохраняем в базу
            if not data:
                return True, "Символы не найдены"
            
            success, message = self.save_symbols_to_db(data)
            if not success:
                return False, message
            
            final_msg = f"Обновление завершено успешно. {message}"
            logger.info(f"✅ {final_msg}")
            return True, final_msg
            
        except Exception as e:
            error_msg = f"Критическая ошибка обновления: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return False, error_msg

# Создаем глобальный экземпляр для использования в приложении
binance_symbols_manager = BinanceSymbolsManager()