"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import os

DB_FILE = "signals.db"

class DatabaseManager:
    """Класс для управления базой данных сигналов"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        """Создает таблицы при первом запуске"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    action TEXT,
                    symbol TEXT,
                    quantity REAL,
                    result TEXT,
                    message TEXT,
                    code TEXT,
                    strategy TEXT,
                    extra_data TEXT
                )
            ''')
            
            # Добавляем колонку extra_data если её нет (для обратной совместимости)
            try:
                conn.execute('ALTER TABLE signals ADD COLUMN extra_data TEXT')
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
    
    def log_signal(self, 
                   action: str, 
                   symbol: str, 
                   quantity: float, 
                   result: str, 
                   message: str, 
                   strategy: str = '', 
                   extra_data: Optional[Dict[str, Any]] = None) -> int:
        """
        Записывает сигнал в БД
        
        Returns:
            int: ID созданной записи
        """
        # Сохраняем время в UTC без timezone конвертации
        utc_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Преобразуем extra_data в JSON строку
        extra_json = None
        if extra_data:
            try:
                extra_json = json.dumps(extra_data, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Ошибка сериализации extra_data: {e}")
                extra_json = str(extra_data)  # Fallback
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO signals (timestamp, action, symbol, quantity, result, message, code, strategy, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                utc_timestamp, action, symbol, quantity, result, message, '', strategy, extra_json
            ))
            
            signal_id = cursor.lastrowid
        
        extra_info = f" + {len(extra_data)} extra fields" if extra_data else ""
        print(f"💾 Сохранено в БД: {utc_timestamp} UTC - {action} {symbol} {quantity}{extra_info}")
        
        return signal_id
    
    def get_signals_count(self, filters: Optional[Dict[str, str]] = None) -> int:
        """
        Получает общее количество сигналов с применением фильтров
        
        Args:
            filters: Словарь с фильтрами
            
        Returns:
            int: Количество записей
        """
        if filters is None:
            filters = {}
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM signals"
            conditions = []
            params = []
            
            # Применяем те же фильтры что и в get_signals
            if filters.get('from_date'):
                conditions.append("DATE(timestamp) >= DATE(?)")
                params.append(filters['from_date'])
                
            if filters.get('to_date'):
                conditions.append("DATE(timestamp) <= DATE(?)")
                params.append(filters['to_date'])
                
            if filters.get('strategy'):
                conditions.append("strategy LIKE ?")
                params.append(f"%{filters['strategy']}%")
                
            if filters.get('action'):
                conditions.append("action = ?")
                params.append(filters['action'])
                
            if filters.get('symbol'):
                conditions.append("symbol LIKE ?")
                params.append(f"%{filters['symbol']}%")
                
            if filters.get('result'):
                conditions.append("result = ?")
                params.append(filters['result'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def get_signals(self, 
                    filters: Optional[Dict[str, str]] = None, 
                    limit: int = 200,
                    offset: int = 0) -> List[Tuple]:
        """
        Получает сигналы из БД с применением фильтров и пагинации
        
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
            query = f"SELECT {', '.join(columns)} FROM signals"
            conditions = []
            params = []
            
            # Применяем фильтры
            if filters.get('from_date'):
                conditions.append("DATE(timestamp) >= DATE(?)")
                params.append(filters['from_date'])
                
            if filters.get('to_date'):
                conditions.append("DATE(timestamp) <= DATE(?)")
                params.append(filters['to_date'])
                
            if filters.get('strategy'):
                conditions.append("strategy LIKE ?")
                params.append(f"%{filters['strategy']}%")
                
            if filters.get('action'):
                conditions.append("action = ?")
                params.append(filters['action'])
                
            if filters.get('symbol'):
                conditions.append("symbol LIKE ?")
                params.append(f"%{filters['symbol']}%")
                
            if filters.get('result'):
                conditions.append("result = ?")
                params.append(filters['result'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += f" ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_columns(self) -> List[str]:
        """Получает список колонок таблицы signals"""
        try:
            if not os.path.exists(self.db_file):
                print(f"⚠️ База данных {self.db_file} не найдена")
                return ['id', 'timestamp', 'action', 'symbol', 'quantity', 'result', 'message', 'code', 'strategy', 'extra_data']
                
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(signals)")
                columns = [col[1] for col in cursor.fetchall()]
                
            print(f"📋 Найдено колонок в БД: {len(columns)} - {columns}")
            return columns
            
        except Exception as e:
            print(f"❌ Ошибка получения колонок БД: {e}")
            return ['id', 'timestamp', 'action', 'symbol', 'quantity', 'result', 'message', 'code', 'strategy', 'extra_data']
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику по сигналам"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Общее количество сигналов
                cursor.execute("SELECT COUNT(*) FROM signals")
                stats['total_signals'] = cursor.fetchone()[0]
                
                # Успешные vs ошибки
                cursor.execute("SELECT result, COUNT(*) FROM signals GROUP BY result")
                result_stats = dict(cursor.fetchall())
                stats['success_count'] = result_stats.get('success', 0)
                stats['error_count'] = result_stats.get('error', 0)
                
                # Статистика по действиям
                cursor.execute("SELECT action, COUNT(*) FROM signals GROUP BY action ORDER BY COUNT(*) DESC")
                stats['action_stats'] = dict(cursor.fetchall())
                
                # Последний сигнал
                cursor.execute("SELECT timestamp FROM signals ORDER BY id DESC LIMIT 1")
                last_signal = cursor.fetchone()
                stats['last_signal'] = last_signal[0] if last_signal else None
                
            return stats
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_signals': 0,
                'success_count': 0,
                'error_count': 0,
                'action_stats': {},
                'last_signal': None
            }
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Получает уникальные значения для фильтров"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                options = {}
                
                # Получаем уникальные стратегии
                cursor.execute("SELECT DISTINCT strategy FROM signals WHERE strategy IS NOT NULL AND strategy != '' ORDER BY strategy")
                options['strategies'] = [row[0] for row in cursor.fetchall()]
                
                # Получаем уникальные действия
                cursor.execute("SELECT DISTINCT action FROM signals ORDER BY action")
                options['actions'] = [row[0] for row in cursor.fetchall()]
                
                # Получаем уникальные символы
                cursor.execute("SELECT DISTINCT symbol FROM signals ORDER BY symbol")
                options['symbols'] = [row[0] for row in cursor.fetchall()]
                
                # Получаем уникальные результаты
                cursor.execute("SELECT DISTINCT result FROM signals ORDER BY result")
                options['results'] = [row[0] for row in cursor.fetchall()]
                
                return options
                
        except Exception as e:
            print(f"❌ Ошибка получения опций фильтров: {e}")
            return {
                'strategies': [],
                'actions': ['ENTER_LONG', 'EXIT_LONG', 'ENTER_SHORT', 'EXIT_SHORT'],
                'symbols': [],
                'results': ['success', 'error']
            }

# Создаем глобальный экземпляр для использования в приложении
db_manager = DatabaseManager()

# Экспортируем функции для обратной совместимости
def log_signal(action, symbol, quantity, result, message, strategy='', extra_data=None):
    """Обратная совместимость с существующим кодом"""
    return db_manager.log_signal(action, symbol, quantity, result, message, strategy, extra_data)

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля database...")
    
    # Создаем тестовую запись
    db = DatabaseManager()
    signal_id = db.log_signal(
        action="ENTER_LONG",
        symbol="BTCUSDT",
        quantity=0.01,
        result="success",
        message="Test signal",
        strategy="test_strategy",
        extra_data={"test_field": "test_value", "price": 50000}
    )
    
    print(f"✅ Создан сигнал с ID: {signal_id}")
    
    # Получаем статистику
    stats = db.get_stats()
    print(f"📊 Статистика: {stats['total_signals']} сигналов")
    
    # Получаем колонки
    columns = db.get_columns()
    print(f"📋 Колонки: {columns}")
    
    # Тестируем пагинацию
    count = db.get_signals_count()
    print(f"📝 Общее количество записей: {count}")
    
    signals_page1 = db.get_signals(limit=10, offset=0)
    print(f"📄 Первая страница: {len(signals_page1)} записей")