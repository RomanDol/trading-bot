"""
Модуль для работы с базой данных WebSocket сообщений
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import os
import random

DB_FILE = "sockets.db"

class SocketsDatabaseManager:
    """Класс для управления базой данных сокетов"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        """Создает таблицы при первом запуске"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS socket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    symbol TEXT,
                    order_id TEXT,
                    status TEXT,
                    raw_message TEXT
                )
            ''')
            
            # Создаем индексы для быстрого поиска
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON socket_messages(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON socket_messages(event_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON socket_messages(symbol)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_order_id ON socket_messages(order_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON socket_messages(status)')
    
    def log_socket_message(self, 
                          event_type: str,
                          symbol: str = None,
                          order_id: str = None,
                          status: str = None,
                          raw_message: str = None) -> int:
        """
        Записывает сокет сообщение в БД
        
        Returns:
            int: ID созданной записи
        """
        # Сохраняем время в UTC
        utc_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO socket_messages (timestamp, event_type, symbol, order_id, status, raw_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                utc_timestamp, event_type, symbol, order_id, status, raw_message
            ))
            
            socket_id = cursor.lastrowid
        
        print(f"📡 Сохранено сокет сообщение: {utc_timestamp} UTC - {event_type} {symbol} {order_id}")
        
        return socket_id
    
    def get_sockets_count(self, filters: Optional[Dict[str, str]] = None) -> int:
        """
        Получает общее количество сокет сообщений с применением фильтров
        
        Args:
            filters: Словарь с фильтрами
            
        Returns:
            int: Количество записей
        """
        if filters is None:
            filters = {}
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM socket_messages"
            conditions = []
            params = []
            
            # Применяем фильтры
            if filters.get('from_date'):
                conditions.append("DATE(timestamp) >= DATE(?)")
                params.append(filters['from_date'])
                
            if filters.get('to_date'):
                conditions.append("DATE(timestamp) <= DATE(?)")
                params.append(filters['to_date'])
                
            if filters.get('event_type'):
                conditions.append("event_type = ?")
                params.append(filters['event_type'])
                
            if filters.get('symbol'):
                conditions.append("symbol LIKE ?")
                params.append(f"%{filters['symbol']}%")
                
            if filters.get('order_id'):
                conditions.append("order_id LIKE ?")
                params.append(f"%{filters['order_id']}%")
                
            if filters.get('status'):
                conditions.append("status = ?")
                params.append(filters['status'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def get_socket_messages(self, 
                           filters: Optional[Dict[str, str]] = None, 
                           limit: int = 200,
                           offset: int = 0) -> List[Tuple]:
        """
        Получает сокет сообщения из БД с применением фильтров и пагинации
        
        Args:
            filters: Словарь с фильтрами
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            
        Returns:
            List[Tuple]: Список записей
        """
        if filters is None:
            filters = {}
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # Получаем все колонки
            columns = self.get_columns()
            query = f"SELECT {', '.join(columns)} FROM socket_messages"
            conditions = []
            params = []
            
            # Применяем фильтры
            if filters.get('from_date'):
                conditions.append("DATE(timestamp) >= DATE(?)")
                params.append(filters['from_date'])
                
            if filters.get('to_date'):
                conditions.append("DATE(timestamp) <= DATE(?)")
                params.append(filters['to_date'])
                
            if filters.get('event_type'):
                conditions.append("event_type = ?")
                params.append(filters['event_type'])
                
            if filters.get('symbol'):
                conditions.append("symbol LIKE ?")
                params.append(f"%{filters['symbol']}%")
                
            if filters.get('order_id'):
                conditions.append("order_id LIKE ?")
                params.append(f"%{filters['order_id']}%")
                
            if filters.get('status'):
                conditions.append("status = ?")
                params.append(filters['status'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += f" ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_columns(self) -> List[str]:
        """Получает список колонок таблицы socket_messages"""
        try:
            if not os.path.exists(self.db_file):
                print(f"⚠️ База данных сокетов {self.db_file} не найдена")
                return ['id', 'timestamp', 'event_type', 'symbol', 'order_id', 'status', 'raw_message']
                
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(socket_messages)")
                columns = [col[1] for col in cursor.fetchall()]
                
            print(f"📋 Найдено колонок в БД сокетов: {len(columns)} - {columns}")
            return columns
            
        except Exception as e:
            print(f"❌ Ошибка получения колонок БД сокетов: {e}")
            return ['id', 'timestamp', 'event_type', 'symbol', 'order_id', 'status', 'raw_message']
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Получает уникальные значения для фильтров"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                options = {}
                
                # Получаем уникальные типы событий
                cursor.execute("SELECT DISTINCT event_type FROM socket_messages WHERE event_type IS NOT NULL ORDER BY event_type")
                options['event_types'] = [row[0] for row in cursor.fetchall()]
                
                # Получаем уникальные символы
                cursor.execute("SELECT DISTINCT symbol FROM socket_messages WHERE symbol IS NOT NULL ORDER BY symbol")
                options['symbols'] = [row[0] for row in cursor.fetchall()]
                
                # Получаем уникальные статусы
                cursor.execute("SELECT DISTINCT status FROM socket_messages WHERE status IS NOT NULL ORDER BY status")
                options['statuses'] = [row[0] for row in cursor.fetchall()]
                
                return options
                
        except Exception as e:
            print(f"❌ Ошибка получения опций фильтров сокетов: {e}")
            return {
                'event_types': ['ORDER_TRADE_UPDATE', 'ACCOUNT_UPDATE'],
                'symbols': [],
                'statuses': ['NEW', 'FILLED', 'PARTIALLY_FILLED', 'CANCELED']
            }
    
    def create_test_data(self, count: int = 100):
        """Создает тестовые данные для демонстрации"""
        print(f"🧪 Создание {count} тестовых сокет сообщений...")
        
        # Тестовые данные
        event_types = ['ORDER_TRADE_UPDATE', 'ACCOUNT_UPDATE', 'listenKeyExpired']
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
        statuses = ['NEW', 'FILLED', 'PARTIALLY_FILLED', 'CANCELED', 'REJECTED']
        
        # Создаем записи за последние 7 дней
        base_time = datetime.utcnow()
        
        for i in range(count):
            # Случайное время в последние 7 дней
            random_minutes = random.randint(0, 7 * 24 * 60)
            msg_time = base_time - timedelta(minutes=random_minutes)
            
            event_type = random.choice(event_types)
            symbol = random.choice(symbols) if event_type != 'listenKeyExpired' else None
            order_id = str(random.randint(1000000000, 9999999999)) if event_type == 'ORDER_TRADE_UPDATE' else None
            status = random.choice(statuses) if event_type == 'ORDER_TRADE_UPDATE' else None
            
            # Создаем raw_message в зависимости от типа события
            if event_type == 'ORDER_TRADE_UPDATE':
                raw_message = {
                    "e": "ORDER_TRADE_UPDATE",
                    "E": int(msg_time.timestamp() * 1000),
                    "T": int(msg_time.timestamp() * 1000),
                    "o": {
                        "s": symbol,
                        "c": f"web_{order_id}",
                        "S": random.choice(['BUY', 'SELL']),
                        "o": "MARKET",
                        "f": "GTC",
                        "q": str(round(random.uniform(0.001, 1.0), 3)),
                        "p": "0",
                        "ap": str(round(random.uniform(20000, 80000), 2)),
                        "sp": "0",
                        "x": random.choice(['NEW', 'TRADE']),
                        "X": status,
                        "i": int(order_id),
                        "l": str(round(random.uniform(0.001, 1.0), 3)),
                        "z": str(round(random.uniform(0.001, 1.0), 3)),
                        "L": str(round(random.uniform(20000, 80000), 2)),
                        "n": str(round(random.uniform(0.1, 5.0), 4)),
                        "N": "USDT",
                        "T": int(msg_time.timestamp() * 1000),
                        "t": random.randint(100000000, 999999999),
                        "I": random.randint(1000000000, 9999999999),
                        "w": True,
                        "m": random.choice([True, False]),
                        "M": random.choice([True, False]),
                        "O": int(msg_time.timestamp() * 1000),
                        "Z": str(round(random.uniform(100, 5000), 2)),
                        "Y": str(round(random.uniform(100, 5000), 2)),
                        "Q": str(round(random.uniform(100, 5000), 2)),
                        "W": int(msg_time.timestamp() * 1000),
                        "V": "NONE",
                        "u": random.randint(1, 4),
                        "ut": "COMMISSION",
                        "si": 0,
                        "ss": 0,
                        "ps": random.choice(['BOTH', 'LONG', 'SHORT']),
                        "rp": str(round(random.uniform(-50, 50), 4))
                    }
                }
            elif event_type == 'ACCOUNT_UPDATE':
                raw_message = {
                    "e": "ACCOUNT_UPDATE",
                    "E": int(msg_time.timestamp() * 1000),
                    "T": int(msg_time.timestamp() * 1000),
                    "a": {
                        "m": "ORDER",
                        "B": [
                            {
                                "a": "USDT",
                                "wb": str(round(random.uniform(1000, 50000), 2)),
                                "cw": str(round(random.uniform(1000, 50000), 2)),
                                "bc": "0"
                            }
                        ],
                        "P": [
                            {
                                "s": symbol,
                                "pa": str(round(random.uniform(-1, 1), 3)),
                                "ep": str(round(random.uniform(20000, 80000), 2)),
                                "cr": str(round(random.uniform(100, 5000), 2)),
                                "up": str(round(random.uniform(-100, 100), 4)),
                                "mt": "cross",
                                "iw": "0",
                                "ps": random.choice(['BOTH', 'LONG', 'SHORT']),
                                "ma": "USDT"
                            }
                        ]
                    }
                }
            else:  # listenKeyExpired
                raw_message = {
                    "e": "listenKeyExpired",
                    "E": int(msg_time.timestamp() * 1000)
                }
            
            # Сохраняем в БД
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO socket_messages (timestamp, event_type, symbol, order_id, status, raw_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    msg_time.strftime("%Y-%m-%d %H:%M:%S"),
                    event_type,
                    symbol,
                    order_id,
                    status,
                    json.dumps(raw_message, ensure_ascii=False)
                ))
        
        print(f"✅ Создано {count} тестовых сокет сообщений")
    
    def clear_test_data(self):
        """Очищает все данные из таблицы"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM socket_messages")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='socket_messages'")
            conn.commit()
        print("🗑️ Все данные сокетов удалены")

# Создаем глобальный экземпляр для использования в приложении
sockets_db_manager = SocketsDatabaseManager()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля sockets_database...")
    
    db = SocketsDatabaseManager()
    
    # Очищаем старые данные
    db.clear_test_data()
    
    # Создаем тестовые данные
    db.create_test_data(50)
    
    # Получаем статистику
    total_count = db.get_sockets_count()
    print(f"📊 Всего сообщений: {total_count}")
    
    # Получаем колонки
    columns = db.get_columns()
    print(f"📋 Колонки: {columns}")
    
    # Тестируем пагинацию
    messages = db.get_socket_messages(limit=5, offset=0)
    print(f"📄 Первые 5 сообщений: {len(messages)} записей")
    
    # Тестируем фильтры
    filter_options = db.get_filter_options()
    print(f"🔍 Опции фильтров: {filter_options}")
    
    # Тестируем фильтрацию
    filtered_messages = db.get_socket_messages({'event_type': 'ORDER_TRADE_UPDATE'}, limit=3)
    print(f"📊 Отфильтрованные сообщения: {len(filtered_messages)} записей")