"""
Модуль для обработки данных сообщений из базы данных PostgreSQL для UI
"""
import json
import math
from core.messages_database import messages_db_manager

def get_messages_data(filters=None, limit=200, offset=0):
    """
    Получает данные сообщений из PostgreSQL БД с применением фильтров и пагинации
    
    Args:
        filters: Словарь с фильтрами
        limit: Количество записей на страницу
        offset: Смещение для пагинации
    """
    if filters is None:
        filters = {}
    
    try:
        # Получаем общее количество записей для пагинации
        total_count = messages_db_manager.get_messages_count(filters)
        
        # Получаем данные с лимитом и смещением
        raw_rows = messages_db_manager.get_messages(filters, limit, offset)
        columns = messages_db_manager.get_columns()
        
        # Обрабатываем данные
        processed_rows = process_message_rows(raw_rows, columns)
        
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
        print(f"❌ Ошибка получения данных сообщений: {e}")
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

def process_message_rows(raw_rows, db_columns):
    """
    Обрабатывает сырые данные из PostgreSQL БД
    """
    processed_rows = []
    
    for row in raw_rows:
        # Конвертируем row в список
        # PostgreSQL возвращает tuple, нам нужен список для модификации
        processed_row = list(row)
        
        # Особая обработка для PostgreSQL timestamp
        if len(processed_row) >= 2 and processed_row[1]:  # time колонка
            # PostgreSQL возвращает datetime объект, конвертируем в строку
            if hasattr(processed_row[1], 'isoformat'):
                processed_row[1] = processed_row[1].isoformat()
        
        # Особая обработка для JSONB message колонки
        if len(processed_row) >= 4 and processed_row[3]:  # message колонка
            # PostgreSQL JSONB может возвращать dict, конвертируем в JSON строку
            if isinstance(processed_row[3], dict):
                processed_row[3] = json.dumps(processed_row[3], ensure_ascii=False)
        
        processed_rows.append(processed_row)
    
    return processed_rows

def get_messages_filter_options():
    """Получает уникальные значения для фильтров сообщений"""
    return messages_db_manager.get_filter_options()

def get_messages_stats():
    """Получает статистику по сообщениям"""
    try:
        total_count = messages_db_manager.get_messages_count()
        filter_options = messages_db_manager.get_filter_options()
        
        # Получаем статистику по типам
        type_stats = {}
        for msg_type in filter_options.get('types', []):
            type_count = messages_db_manager.get_messages_count({'type': msg_type})
            type_stats[msg_type] = type_count
        
        return {
            'total_messages': total_count,
            'types_count': len(filter_options.get('types', [])),
            'type_stats': type_stats
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики сообщений: {e}")
        return {
            'total_messages': 0,
            'types_count': 0,
            'type_stats': {}
        }