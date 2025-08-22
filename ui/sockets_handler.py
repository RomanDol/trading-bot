"""
Модуль для обработки данных сокетов из базы данных для UI
"""
import json
import math
from core.sockets_database import sockets_db_manager

def get_sockets_data(filters=None, limit=200, offset=0):
    """
    Получает данные сокетов из БД с применением фильтров и пагинации
    
    Args:
        filters: Словарь с фильтрами
        limit: Количество записей на страницу
        offset: Смещение для пагинации
    """
    if filters is None:
        filters = {}
    
    try:
        # Получаем общее количество записей для пагинации
        total_count = sockets_db_manager.get_sockets_count(filters)
        
        # Получаем данные с лимитом и смещением
        raw_rows = sockets_db_manager.get_socket_messages(filters, limit, offset)
        columns = sockets_db_manager.get_columns()
        
        # Обрабатываем данные
        processed_rows = process_socket_rows(raw_rows, columns)
        
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
        print(f"❌ Ошибка получения данных сокетов: {e}")
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

def process_socket_rows(raw_rows, db_columns):
    """
    Обрабатывает сырые данные из БД сокетов
    """
    processed_rows = []
    
    for row in raw_rows:
        # Просто конвертируем row в список без изменений
        processed_row = list(row)
        processed_rows.append(processed_row)
    
    return processed_rows

def get_sockets_filter_options():
    """Получает уникальные значения для фильтров сокетов"""
    return sockets_db_manager.get_filter_options()

def get_sockets_stats():
    """Получает статистику по сокетам"""
    try:
        total_count = sockets_db_manager.get_sockets_count()
        filter_options = sockets_db_manager.get_filter_options()
        
        return {
            'total_messages': total_count,
            'event_types_count': len(filter_options.get('event_types', [])),
            'symbols_count': len(filter_options.get('symbols', [])),
            'statuses_count': len(filter_options.get('statuses', []))
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики сокетов: {e}")
        return {
            'total_messages': 0,
            'event_types_count': 0,
            'symbols_count': 0,
            'statuses_count': 0
        }