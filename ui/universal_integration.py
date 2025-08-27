# ===== ui/universal_integration.py =====
"""
from .signals_handler import get_signals_data
Интеграция универсальной системы таблиц с существующими обработчиками
"""
import io
import xlsxwriter
from datetime import datetime
from flask import make_response
from .universal_table_router import universal_table_router, TableConfig
from .signals_handler import get_signals_data, get_filter_options
from .messages_handler import get_messages_data

def setup_universal_tables():
    """Настройка всех типов таблиц в универсальной системе"""
    
    # ===== SIGNALS TABLE =====
    from core.database import db_manager
    from .signals_handler import get_signals_data, get_filter_options
    
    signals_config = TableConfig(
        table_type='signals',
        db_manager=db_manager,
        default_columns={
            'id': {'name': '#', 'visible': True, 'order': 0, 'width': '60px'},
            'timestamp': {'name': 'Time', 'visible': True, 'order': 1, 'width': '140px'},
            'action': {'name': 'Action', 'visible': True, 'order': 2, 'width': '100px'},
            'symbol': {'name': 'Symbol', 'visible': True, 'order': 3, 'width': '100px'},
            'quantity': {'name': 'Qty', 'visible': True, 'order': 4, 'width': '80px'},
            'result': {'name': 'Result', 'visible': True, 'order': 5, 'width': '100px'},
            'strategy': {'name': 'Strategy', 'visible': True, 'order': 6, 'width': '120px'},
            'message': {'name': 'Message', 'visible': False, 'order': 7, 'width': '200px'},
            'code': {'name': 'Code', 'visible': False, 'order': 8, 'width': '80px'},
            'extra_data': {'name': 'Extra Data', 'visible': False, 'order': 9, 'width': '100px'}
        },
        config_file='columns_config.json',
        template_name='universal_table.html',
        page_title='Trading Signals',
        data_fetcher_func=adapt_signals_data,
        filter_options_func=get_filter_options,
        excel_export_func=create_signals_excel_export
    )
    
    universal_table_router.register_table(signals_config)
    
    # ===== SOCKETS TABLE =====
    from core.sockets_database import sockets_db_manager
    from .sockets_handler import get_sockets_data, get_sockets_filter_options
    
    sockets_config = TableConfig(
        table_type='sockets',
        db_manager=sockets_db_manager,
        default_columns={
            'id': {'name': '#', 'visible': True, 'order': 0, 'width': '60px'},
            'timestamp': {'name': 'timestamp', 'visible': True, 'order': 1, 'width': '140px'},
            'event_type': {'name': 'event_type', 'visible': True, 'order': 2, 'width': '150px'},
            'symbol': {'name': 'symbol', 'visible': True, 'order': 3, 'width': '100px'},
            'order_id': {'name': 'order_id', 'visible': True, 'order': 4, 'width': '120px'},
            'status': {'name': 'status', 'visible': True, 'order': 5, 'width': '100px'},
            'raw_message': {'name': 'raw_message', 'visible': False, 'order': 6, 'width': '800px'}
        },
        config_file='sockets_columns_config.json',
        template_name='universal_table.html',
        page_title='WebSocket Messages',
        data_fetcher_func=adapt_sockets_data,
        filter_options_func=get_sockets_filter_options,
        excel_export_func=create_sockets_excel_export
    )
    
    universal_table_router.register_table(sockets_config)
    
    # ===== MESSAGES TABLE =====
    from core.messages_database import messages_db_manager
    from .messages_handler import get_messages_data, get_messages_filter_options
    
    messages_config = TableConfig(
        table_type='messages',
        db_manager=messages_db_manager,
        default_columns={
            'id': {'name': '#', 'visible': True, 'order': 0, 'width': '60px'},
            'time': {'name': 'Time', 'visible': True, 'order': 1, 'width': '140px'},
            'type': {'name': 'Type', 'visible': True, 'order': 2, 'width': '150px'},
            'message': {'name': 'Message', 'visible': True, 'order': 3, 'width': '800px'}
        },
        config_file='messages_columns_config.json',
        template_name='universal_table.html',
        page_title='All Messages',
        data_fetcher_func=adapt_messages_data,
        filter_options_func=get_messages_filter_options,
        excel_export_func=create_messages_excel_export
    )
    
    universal_table_router.register_table(messages_config)
    
    print("✅ Универсальные таблицы настроены: signals, sockets, messages")

# ===== ФУНКЦИИ ЭКСПОРТА В EXCEL =====

def create_signals_excel_export(request, columns_config):
    """Экспорт сигналов в Excel"""
    try:
        from .signals_handler import get_signals_data
        
        # Получаем параметры фильтрации
        filters = {k: v for k, v in request.args.items() if k not in ['limit', 'page'] and v}
        
        # Получаем ВСЕ данные (без лимита для экспорта)
        data = get_signals_data(filters, limit=10000, offset=0)
        
        return create_excel_response(
            data=data['data'],
            columns_config=columns_config,
            filename_prefix='trading_signals',
            filters=filters,
            sheet_name='Signals'
        )
    except Exception as e:
        print(f"❌ Ошибка экспорта signals в Excel: {e}")
        raise

def create_sockets_excel_export(request, columns_config):
    """Экспорт сокетов в Excel"""
    try:
        from .sockets_handler import get_sockets_data
        
        filters = {k: v for k, v in request.args.items() if k not in ['limit', 'page'] and v}
        data = get_sockets_data(filters, limit=10000, offset=0)
        
        return create_excel_response(
            data=data['data'],
            columns_config=columns_config,
            filename_prefix='socket_messages',
            filters=filters,
            sheet_name='Sockets'
        )
    except Exception as e:
        print(f"❌ Ошибка экспорта sockets в Excel: {e}")
        raise

def create_messages_excel_export(request, columns_config):
    """Экспорт сообщений в Excel"""
    try:
        from .messages_handler import get_messages_data
        
        filters = {k: v for k, v in request.args.items() if k not in ['limit', 'page'] and v}
        data = get_messages_data(filters, limit=10000, offset=0)
        
        return create_excel_response(
            data=data['data'],
            columns_config=columns_config,
            filename_prefix='all_messages',
            filters=filters,
            sheet_name='Messages'
        )
    except Exception as e:
        print(f"❌ Ошибка экспорта messages в Excel: {e}")
        raise

def create_excel_response(data, columns_config, filename_prefix, filters, sheet_name):
    """Универсальная функция создания Excel файла"""
    
    # Получаем видимые колонки в правильном порядке
    visible_columns = []
    sorted_columns = sorted(columns_config.items(), key=lambda x: x[1].get('order', 999))
    
    for column_key, column_settings in sorted_columns:
        if column_settings.get('visible', False):
            visible_columns.append({
                'key': column_key,
                'name': column_settings.get('name', column_key),
                'width': column_settings.get('width', '120px')
            })
    
    # Создаем Excel файл в памяти
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet(sheet_name)
    
    # Стили для Excel
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#333333',
        'font_color': 'white',
        'border': 1,
        'text_wrap': True,
        'valign': 'vcenter'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'text_wrap': True,
        'valign': 'top'
    })
    
    date_format = workbook.add_format({
        'border': 1,
        'num_format': 'yyyy-mm-dd hh:mm:ss'
    })
    
    json_format = workbook.add_format({
        'border': 1,
        'text_wrap': True,
        'font_name': 'Courier New',
        'font_size': 9
    })
    
    # Записываем заголовки
    col_num = 0
    for column in visible_columns:
        worksheet.write(0, col_num, column['name'], header_format)
        
        # Устанавливаем ширину колонки
        width = int(column['width'].replace('px', '')) / 8  # Примерное преобразование px в символы
        worksheet.set_column(col_num, col_num, width)
        
        col_num += 1
    
    # Записываем данные
    row_num = 1
    for row_data in data:
        col_num = 0
        
        for column in visible_columns:
            cell_value = get_cell_value_for_export(row_data, column['key'], visible_columns)
            
            # Выбираем формат в зависимости от типа данных
            if column['key'] in ['timestamp', 'time'] and cell_value:
                try:
                    if isinstance(cell_value, str):
                        from datetime import datetime
                        dt = datetime.fromisoformat(cell_value.replace('Z', '+00:00'))
                        worksheet.write_datetime(row_num, col_num, dt, date_format)
                    else:
                        worksheet.write(row_num, col_num, cell_value, cell_format)
                except:
                    worksheet.write(row_num, col_num, cell_value, cell_format)
            
            elif is_json_cell_value(cell_value):
                # JSON данные - форматируем для лучшей читаемости
                try:
                    import json
                    formatted_json = json.dumps(json.loads(cell_value), indent=2, ensure_ascii=False)
                    worksheet.write(row_num, col_num, formatted_json, json_format)
                except:
                    worksheet.write(row_num, col_num, cell_value, json_format)
            
            else:
                worksheet.write(row_num, col_num, cell_value or '', cell_format)
            
            col_num += 1
        
        row_num += 1
    
    # Закрываем workbook
    workbook.close()
    output.seek(0)
    
    # Создаем имя файла
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filter_str = '_'.join([f"{k}-{v}" for k, v in filters.items()]) if filters else 'all'
    filename = f"{filename_prefix}_{timestamp}_{filter_str}.xlsx"
    
    # Создаем ответ с файлом
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    print(f"📊 Экспорт в Excel: {row_num-1} строк, {len(visible_columns)} колонок")
    
    return response

def get_cell_value_for_export(row_data, column_key, visible_columns):
    """Получает значение ячейки для экспорта"""
    if isinstance(row_data, list):
        # Данные в виде массива
        column_keys = [col['key'] for col in visible_columns]
        column_index = column_keys.index(column_key) if column_key in column_keys else -1
        return row_data[column_index] if column_index != -1 and column_index < len(row_data) else ''
    else:
        # Данные в виде объекта
        return row_data.get(column_key, '')

def is_json_cell_value(cell_value):
    """Проверяет, является ли значение JSON"""
    if not cell_value or not isinstance(cell_value, str):
        return False
    
    cell_value = cell_value.strip()
    return (cell_value.startswith('{') and cell_value.endswith('}')) or \
           (cell_value.startswith('[') and cell_value.endswith(']'))

if __name__ == "__main__":
    print("🧪 Тестирование универсальной интеграции...")
    setup_universal_tables()
    print("✅ Интеграция настроена")
from .messages_handler import get_messages_data
def adapt_messages_data(filters, limit, offset):
    """Адаптер для messages данных"""
    result = get_messages_data(filters, limit, offset)
    return {
        'data': result.get('rows', []),
        'total': result.get('total_count', 0)
    }

def adapt_sockets_data(filters, limit, offset):
    """Адаптер для sockets данных"""
    try:
        from ui.sockets_handler import get_sockets_data
        result = get_sockets_data(filters, limit, offset)
        return {
            'data': result.get('rows', []),
            'total': result.get('total_count', 0)
        }
    except Exception as e:
        print(f"Ошибка sockets адаптера: {e}")
        return {'data': [], 'total': 0}

def adapt_signals_data(filters, limit, offset):
    """Адаптер для signals данных"""
    result = get_signals_data(filters, limit, offset)
    return {
        'data': result.get('rows', []),
        'total': result.get('total_count', 0)
    }
