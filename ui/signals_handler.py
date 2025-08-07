"""
Модуль для обработки данных сигналов из базы данных для UI
Перенесено из signals_handler.py
"""
import json
from core.database import db_manager

def get_signals_data(filters=None, limit=200):
    """
    Получает данные сигналов из БД с применением фильтров
    """
    if filters is None:
        filters = {}
    
    try:
        # Получаем данные через database manager
        raw_rows = db_manager.get_signals(filters, limit)
        columns = db_manager.get_columns()
        
        # Обрабатываем данные
        processed_rows = process_signal_rows(raw_rows, columns)
        
        # Создаем маппинг колонок
        column_map = {col: idx for idx, col in enumerate(columns)}
        
        return {
            'rows': processed_rows,
            'columns': columns,
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

def process_signal_rows(raw_rows, db_columns):
    """Обрабатывает сырые данные из БД"""
    processed_rows = []
    
    for row in raw_rows:
        processed_row = list(row)
        
        # Обработка message колонки - разбиваем на части
        if 'message' in db_columns:
            message_index = db_columns.index('message')
            if processed_row[message_index]:
                message_parts = str(processed_row[message_index]).split(',')
                processed_row[message_index] = message_parts[0][:100] + ('...' if len(message_parts[0]) > 100 else '')
        
        processed_rows.append(processed_row)
    
    return processed_rows

def get_filter_options():
    """Получает уникальные значения для фильтров"""
    return db_manager.get_filter_options()

def get_signals_stats():
    """Получает статистику по сигналам"""
    return db_manager.get_stats()
