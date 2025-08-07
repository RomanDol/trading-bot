"""
Модуль для обработки данных сигналов из базы данных
"""
import sqlite3
import pytz
from datetime import datetime
from columns_config import DB_FILE, get_db_columns

def get_signals_data(filters=None, limit=200):
    """
    Получает данные сигналов из БД с применением фильтров
    
    Args:
        filters (dict): Словарь с фильтрами
        limit (int): Максимальное количество записей
        
    Returns:
        dict: {'rows': [...], 'columns': [...], 'column_map': {...}}
    """
    if filters is None:
        filters = {}
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Получаем все колонки
        db_columns = get_db_columns()
        
        # Строим запрос
        query = f"SELECT {', '.join(db_columns)} FROM signals"
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
            
        query += f" ORDER BY id DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        raw_rows = cursor.fetchall()
        conn.close()
        
        # Обрабатываем данные
        processed_rows = process_signal_rows(raw_rows, db_columns)
        
        # Создаем маппинг колонок
        column_map = {col: idx for idx, col in enumerate(db_columns)}
        
        return {
            'rows': processed_rows,
            'columns': db_columns,
            'column_map': column_map,
            'total_found': len(processed_rows)
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения данных сигналов: {e}")
        return {
            'rows': [],
            'columns': [],
            'column_map': {},
            'total_found': 0,
            'error': str(e)
        }

# В signals_handler.py замените функцию process_signal_rows:

def process_signal_rows(raw_rows, db_columns):
    """
    Обрабатывает сырые данные из БД
    """
    processed_rows = []
    
    for row in raw_rows:
        processed_row = list(row)
        
        # НЕ ОБРАБАТЫВАЕМ timestamp здесь - оставляем как есть из БД
        # Обработка времени будет происходить только на фронтенде
        
        # Обработка message колонки - разбиваем на части
        if 'message' in db_columns:
            message_index = db_columns.index('message')
            if processed_row[message_index]:
                # Если message содержит несколько полей через запятую
                message_parts = str(processed_row[message_index]).split(',')
                processed_row[message_index] = message_parts[0][:100] + ('...' if len(message_parts[0]) > 100 else '')
        
        processed_rows.append(processed_row)
    
    return processed_rows


def get_filter_options():
    """
    Получает уникальные значения для фильтров
    
    Returns:
        dict: Словарь с опциями для фильтров
    """
    try:
        conn = sqlite3.connect(DB_FILE)
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
        
        conn.close()
        return options
        
    except Exception as e:
        print(f"❌ Ошибка получения опций фильтров: {e}")
        return {
            'strategies': [],
            'actions': ['ENTER_LONG', 'EXIT_LONG', 'ENTER_SHORT', 'EXIT_SHORT'],
            'symbols': [],
            'results': ['success', 'error']
        }

def get_signals_stats():
    """
    Получает статистику по сигналам
    
    Returns:
        dict: Статистика
    """
    try:
        conn = sqlite3.connect(DB_FILE)
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
        
        conn.close()
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

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля signals_handler...")
    
    # Тест получения данных
    data = get_signals_data(limit=5)
    print(f"📊 Получено записей: {data['total_found']}")
    print(f"📋 Колонок: {len(data['columns'])}")
    
    # Тест статистики
    stats = get_signals_stats()
    print(f"📈 Общее количество сигналов: {stats['total_signals']}")
    print(f"✅ Успешных: {stats['success_count']}")
    print(f"❌ Ошибок: {stats['error_count']}")




def get_json_fields_from_db():
    """Анализирует все JSON данные и возвращает уникальные поля"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Получаем все непустые extra_data
        cursor.execute("SELECT extra_data FROM signals WHERE extra_data IS NOT NULL AND extra_data != '{}'")
        rows = cursor.fetchall()
        conn.close()
        
        # Собираем все уникальные ключи из JSON
        all_keys = set()
        for row in rows:
            try:
                json_data = json.loads(row[0])
                all_keys.update(json_data.keys())
            except:
                continue
                
        return sorted(list(all_keys))
        
    except Exception as e:
        print(f"❌ Ошибка анализа JSON полей: {e}")
        return []

def get_signals_data_with_json_columns(filters=None, limit=200):
    """Получает данные с развернутыми JSON колонками"""
    # Получаем базовые данные
    base_data = get_signals_data(filters, limit)
    
    # Получаем все JSON поля
    json_fields = get_json_fields_from_db()
    
    if not json_fields:
        return base_data
    
    # Расширяем данные JSON полями
    enhanced_rows = []
    for row in base_data['rows']:
        enhanced_row = list(row)
        
        # Находим индекс extra_data
        if 'extra_data' in base_data['column_map']:
            extra_data_index = base_data['column_map']['extra_data']
            extra_data = row[extra_data_index]
            
            # Парсим JSON и добавляем поля
            json_values = {}
            if extra_data:
                try:
                    json_values = json.loads(extra_data)
                except:
                    pass
            
            # Добавляем значения для каждого JSON поля
            for field in json_fields:
                enhanced_row.append(json_values.get(field, ''))
        else:
            # Если нет extra_data, добавляем пустые значения
            for field in json_fields:
                enhanced_row.append('')
                
        enhanced_rows.append(enhanced_row)
    
    # Обновляем колонки и маппинг
    enhanced_columns = base_data['columns'] + [f"json_{field}" for field in json_fields]
    enhanced_column_map = base_data['column_map'].copy()
    
    # Добавляем маппинг для JSON полей
    base_column_count = len(base_data['columns'])
    for i, field in enumerate(json_fields):
        enhanced_column_map[f"json_{field}"] = base_column_count + i
    
    return {
        'rows': enhanced_rows,
        'columns': enhanced_columns,
        'column_map': enhanced_column_map,
        'total_found': len(enhanced_rows),
        'json_fields': json_fields
    }