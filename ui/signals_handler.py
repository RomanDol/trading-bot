# ===== ui/signals_handler.py =====
"""
Модуль для обработки данных сигналов из базы данных для UI
Перенесено из signals_handler.py
"""
import json
import math
from core.database import db_manager

def get_signals_data(filters=None, limit=200, offset=0):
    """
    Получает данные сигналов из БД с применением фильтров и пагинации
    
    Args:
        filters: Словарь с фильтрами
        limit: Количество записей на страницу
        offset: Смещение для пагинации
    """
    if filters is None:
        filters = {}
    
    try:
        # Получаем общее количество записей для пагинации
        total_count = db_manager.get_signals_count(filters)
        
        # Получаем данные с лимитом и смещением
        raw_rows = db_manager.get_signals(filters, limit, offset)
        columns = db_manager.get_columns()
        
        # Обрабатываем данные БЕЗ разбивки message
        processed_rows = process_signal_rows(raw_rows, columns)
        
        # Создаем маппинг колонок
        column_map = {col: idx for idx, col in enumerate(columns)}
        
        # Вычисляем информацию о пагинации
        total_pages = math.ceil(total_count / limit) if limit > 0 else 1
        current_page = (offset // limit) + 1 if limit > 0 else 1
        
        return {
            'rows': processed_rows,
            'columns': columns,
            'column_map': column_map,
            'total_found': len(processed_rows),
            'total_count': total_count,
            'current_page': current_page,
            'total_pages': total_pages,
            'has_next': current_page < total_pages,
            'has_prev': current_page > 1,
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения данных сигналов: {e}")
        return {
            'rows': [],
            'columns': [],
            'column_map': {},
            'total_found': 0,
            'total_count': 0,
            'current_page': 1,
            'total_pages': 1,
            'has_next': False,
            'has_prev': False,
            'limit': limit,
            'offset': offset,
            'error': str(e)
        }

def process_signal_rows(raw_rows, db_columns):
    """
    Обрабатывает сырые данные из БД
    УБРАНА логика разбивки message - теперь показываем полное сообщение
    """
    processed_rows = []
    
    for row in raw_rows:
        # Просто конвертируем row в список без изменений
        processed_row = list(row)
        processed_rows.append(processed_row)
    
    return processed_rows

def get_filter_options():
    """Получает уникальные значения для фильтров"""
    return db_manager.get_filter_options()

def get_signals_stats():
    """Получает статистику по сигналам"""
    return db_manager.get_stats()