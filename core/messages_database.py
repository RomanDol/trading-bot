"""
Модуль для работы с базой данных PostgreSQL для всех сообщений (стратегии, API, WebSocket)
"""
import psycopg2
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'messages',
    'user': 'postgres',
    'password': 'password'
}

class MessagesDatabaseManager:
    """Класс для управления базой данных всех сообщений"""
    
    def __init__(self, db_config: dict = DB_CONFIG):
        self.db_config = db_config
        self.init_db()
    
    def get_connection(self):
        """Создает подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def init_db(self):
        """Создает таблицы при первом запуске"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу для всех сообщений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS all_messages (
                        id SERIAL PRIMARY KEY,
                        time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        type VARCHAR(100) NOT NULL,
                        message JSONB NOT NULL
                    )
                ''')
                
                # Создаем индексы для быстрого поиска
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_time ON all_messages(time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_type ON all_messages(type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_message_gin ON all_messages USING gin(message)')
                
                conn.commit()
                logger.info("✅ База данных сообщений инициализирована")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise
    
    def log_message(self, message_type: str, message_data: Dict[str, Any]) -> int:
        """
        Записывает сообщение в БД
        
        Args:
            message_type: Тип сообщения (значение поля "e" из JSON)
            message_data: Данные сообщения в виде словаря
            
        Returns:
            int: ID созданной записи
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO all_messages (type, message)
                    VALUES (%s, %s)
                    RETURNING id
                ''', (message_type, json.dumps(message_data, ensure_ascii=False)))
                
                message_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"💾 Сообщение #{message_id} сохранено: {message_type}")
                return message_id
                
        except Exception as e:
            logger.error(f"❌ Ошибка записи сообщения: {e}")
            raise
    
    def get_messages_count(self, filters: Optional[Dict[str, str]] = None) -> int:
        """
        Получает общее количество сообщений с применением фильтров
        
        Args:
            filters: Словарь с фильтрами
            
        Returns:
            int: Количество записей
        """
        if filters is None:
            filters = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT COUNT(*) FROM all_messages"
                conditions = []
                params = []
                
                # Применяем фильтры
                if filters.get('from_date'):
                    conditions.append("DATE(time) >= %s")
                    params.append(filters['from_date'])
                    
                if filters.get('to_date'):
                    conditions.append("DATE(time) <= %s")
                    params.append(filters['to_date'])
                    
                if filters.get('type'):
                    conditions.append("type = %s")
                    params.append(filters['type'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                    
                cursor.execute(query, params)
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета сообщений: {e}")
            return 0
    
    def get_messages(self, 
                    filters: Optional[Dict[str, str]] = None, 
                    limit: int = 200,
                    offset: int = 0) -> List[Tuple]:
        """
        Получает сообщения из БД с применением фильтров и пагинации
        
        Args:
            filters: Словарь с фильтрами
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            
        Returns:
            List[Tuple]: Список записей
        """
        if filters is None:
            filters = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем все колонки
                columns = self.get_columns()
                query = f"SELECT {', '.join(columns)} FROM all_messages"
                conditions = []
                params = []
                
                # Применяем фильтры
                if filters.get('from_date'):
                    conditions.append("DATE(time) >= %s")
                    params.append(filters['from_date'])
                    
                if filters.get('to_date'):
                    conditions.append("DATE(time) <= %s")
                    params.append(filters['to_date'])
                    
                if filters.get('type'):
                    conditions.append("type = %s")
                    params.append(filters['type'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                    
                query += f" ORDER BY id DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения сообщений: {e}")
            return []
    
    def get_columns(self) -> List[str]:
        """Получает список колонок таблицы all_messages"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'all_messages' 
                    ORDER BY ordinal_position
                """)
                columns = [col[0] for col in cursor.fetchall()]
                
            logger.info(f"📋 Найдено колонок в БД сообщений: {len(columns)} - {columns}")
            return columns
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения колонок БД сообщений: {e}")
            return ['id', 'time', 'type', 'message']
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Получает уникальные значения для фильтров"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                options = {}
                
                # Получаем уникальные типы сообщений
                cursor.execute("SELECT DISTINCT type FROM all_messages ORDER BY type")
                options['types'] = [row[0] for row in cursor.fetchall()]
                
                return options
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения опций фильтров сообщений: {e}")
            return {
                'types': []
            }
    
    def create_test_data(self):
        """Создает две тестовые записи"""
        logger.info("🧪 Создание тестовых сообщений...")
        
        # Тестовое сообщение от стратегии
        strategy_message = {
            "e": "STRATEGY_SIGNAL",
            "action": "ENTER_LONG",
            "symbol": "BTCUSDT",
            "quantity": 0.001,
            "strategy": "test_strategy",
            "auth_key": "***",
            "timestamp": datetime.now().isoformat()
        }
        
        # Тестовое сообщение от Binance API
        binance_api_message = {
            "e": "BINANCE_API",
            "orderId": 123456789,
            "symbol": "BTCUSDT",
            "status": "FILLED",
            "side": "BUY",
            "type": "MARKET",
            "executedQty": "0.001",
            "avgPrice": "50000.00",
            "origQty": "0.001",
            "updateTime": int(datetime.now().timestamp() * 1000)
        }
        
        try:
            # Сохраняем тестовые сообщения
            strategy_id = self.log_message("STRATEGY_SIGNAL", strategy_message)
            binance_id = self.log_message("BINANCE_API", binance_api_message)
            
            logger.info(f"✅ Созданы тестовые сообщения: #{strategy_id}, #{binance_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания тестовых данных: {e}")
    
    def clear_test_data(self):
        """Очищает все данные из таблицы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE all_messages RESTART IDENTITY")
                conn.commit()
            logger.info("🗑️ Все данные сообщений удалены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")

# Создаем глобальный экземпляр для использования в приложении
messages_db_manager = MessagesDatabaseManager()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля messages_database...")
    
    try:
        db = MessagesDatabaseManager()
        
        # Очищаем старые данные
        db.clear_test_data()
        
        # Создаем тестовые данные
        db.create_test_data()
        
        # Получаем статистику
        total_count = db.get_messages_count()
        print(f"📊 Всего сообщений: {total_count}")
        
        # Получаем колонки
        columns = db.get_columns()
        print(f"📋 Колонки: {columns}")
        
        # Тестируем получение сообщений
        messages = db.get_messages(limit=5, offset=0)
        print(f"📄 Первые сообщения: {len(messages)} записей")
        
        # Тестируем фильтры
        filter_options = db.get_filter_options()
        print(f"🔍 Опции фильтров: {filter_options}")
        
        print("✅ Тестирование завершено успешно")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()