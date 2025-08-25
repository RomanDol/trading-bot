"""
Маршруты Flask для работы с сообщениями (messages)
"""
import json
from flask import request, jsonify
from .messages_columns_config import (
    load_messages_columns_config, 
    save_messages_columns_config, 
    reset_messages_to_default,
    get_visible_messages_columns
)
from .messages_handler import get_messages_data, get_messages_filter_options, get_messages_stats

class MessagesRouteHandlers:
    """Класс с обработчиками маршрутов для сообщений"""
    
    @staticmethod
    def handle_messages():
        """Обработчик страницы сообщений"""
        # Получаем параметры фильтрации из URL
        filters = {
            'from_date': request.args.get('from_date', ''),
            'to_date': request.args.get('to_date', ''),
            'type': request.args.get('type', '')
        }
        
        # Загружаем конфигурацию колонок для сообщений
        columns_config = load_messages_columns_config()
        
        # Получаем опции для фильтров
        filter_options = get_messages_filter_options()
        
        return {
            'columns_config': columns_config,
            'filters': filters,
            'filter_options': filter_options
        }

    @staticmethod
    def handle_messages_data():
        """API endpoint для получения данных сообщений с пагинацией"""
        try:
            # Получаем параметры фильтрации
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'type': request.args.get('type')
            }
            
            # Убираем пустые фильтры
            filters = {k: v for k, v in filters.items() if v}
            
            # Получаем параметры пагинации
            try:
                limit = int(request.args.get('limit', 50))
                page = int(request.args.get('page', 1))
                
                # Валидируем параметры
                limit = max(10, min(limit, 1000))
                page = max(1, page)
                
                offset = (page - 1) * limit
                
            except (ValueError, TypeError):
                limit = 50
                page = 1
                offset = 0
            
            # Получаем данные с пагинацией
            data = get_messages_data(filters, limit, offset)
            
            return jsonify(data)
            
        except Exception as e:
            return jsonify({
                'error': str(e),
                'rows': [],
                'columns': [],
                'column_map': {},
                'total_found': 0,
                'total_count': 0,
                'current_page': 1,
                'total_pages': 1,
                'has_next': False,
                'has_prev': False,
                'limit': 50,
                'offset': 0
            }), 500

    @staticmethod
    def handle_save_messages_columns_config():
        """API endpoint для сохранения конфигурации колонок сообщений"""
        try:
            config = request.get_json()
            
            if not config:
                return jsonify({'status': 'error', 'message': 'Отсутствуют данные'}), 400
            
            # Валидируем структуру конфигурации
            for key, col_config in config.items():
                required_fields = ['name', 'visible', 'order']
                if not all(field in col_config for field in required_fields):
                    return jsonify({
                        'status': 'error', 
                        'message': f'Неверная структура конфигурации для колонки сообщений {key}'
                    }), 400
            
            if save_messages_columns_config(config):
                return jsonify({'status': 'success', 'message': 'Конфигурация сообщений сохранена'})
            else:
                return jsonify({'status': 'error', 'message': 'Ошибка сохранения сообщений'}), 500
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_reset_messages_columns():
        """API endpoint для сброса конфигурации колонок сообщений"""
        try:
            config = reset_messages_to_default()
            return jsonify({
                'status': 'success', 
                'message': 'Конфигурация сообщений сброшена',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_export_messages_excel():
        """API endpoint для экспорта данных сообщений в Excel"""
        try:
            from flask import make_response
            import io
            import xlsxwriter
            from datetime import datetime
            
            # Получаем параметры фильтрации (те же что и для обычного запроса)
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'type': request.args.get('type')
            }
            
            # Убираем пустые фильтры
            filters = {k: v for k, v in filters.items() if v}
            
            # Получаем ВСЕ данные (без лимита для экспорта)
            data = get_messages_data(filters, limit=10000, offset=0)
            
            # Получаем конфигурацию колонок
            columns_config = load_messages_columns_config()
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('All Messages')
            
            # Стили для Excel
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#333333',
                'font_color': 'white',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'left'
            })
            
            # Получаем видимые колонки в правильном порядке
            visible_columns = get_visible_messages_columns(columns_config)
            
            # Записываем заголовки
            col_num = 0
            for key, config in visible_columns:
                worksheet.write(0, col_num, config['name'], header_format)
                col_num += 1
            
            # Записываем данные
            row_num = 1
            for row_data in data['rows']:
                col_num = 0
                for key, config in visible_columns:
                    # Получаем значение для этой колонки
                    if key in data['column_map']:
                        cell_value = row_data[data['column_map'][key]]
                    else:
                        cell_value = ''
                    
                    # Специальная обработка для колонки message (JSON)
                    if key == 'message' and cell_value:
                        try:
                            # Если это JSON строка, форматируем её красиво
                            if isinstance(cell_value, str):
                                parsed_json = json.loads(cell_value)
                                cell_value = json.dumps(parsed_json, ensure_ascii=False, indent=2)
                        except:
                            pass  # Если не JSON, оставляем как есть
                    
                    worksheet.write(row_num, col_num, str(cell_value) if cell_value else '', cell_format)
                    col_num += 1
                row_num += 1
            
            # Автоширина колонок
            for i, (key, config) in enumerate(visible_columns):
                if key == 'message':
                    worksheet.set_column(i, i, 50)  # Широкая колонка для JSON
                elif key == 'time':
                    worksheet.set_column(i, i, 20)  # Средняя для времени
                else:
                    worksheet.set_column(i, i, 15)  # Стандартная ширина
            
            workbook.close()
            output.seek(0)
            
            # Создаем имя файла с текущей датой и фильтрами
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filter_str = '_'.join([f"{k}-{v}" for k, v in filters.items()]) if filters else 'all'
            filename = f"all_messages_{timestamp}_{filter_str}.xlsx"
            
            # Создаем ответ с файлом
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            print(f"📊 Экспорт сообщений в Excel: {row_num-1} строк, {len(visible_columns)} колонок")
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка экспорта сообщений в Excel: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_get_messages_columns_config():
        """API endpoint для получения текущей конфигурации колонок сообщений"""
        try:
            config = load_messages_columns_config()
            return jsonify({
                'status': 'success',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

# Создаем экземпляр для использования
messages_route_handlers = MessagesRouteHandlers()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля routes_messages...")
    
    messages_data = messages_route_handlers.handle_messages()
    print(f"📋 Конфигурация колонок сообщений: {len(messages_data['columns_config'])} колонок")
    print(f"🔍 Опции фильтров: {messages_data['filter_options']}")