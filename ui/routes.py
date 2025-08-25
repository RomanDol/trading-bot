"""
Маршруты Flask для веб-интерфейса управления ботом
"""
import json
import time
from flask import request, jsonify
import subprocess
from .columns_config import load_columns_config, save_columns_config, reset_to_default
from .signals_handler import get_signals_data, get_filter_options, get_signals_stats
from .routes_messages import messages_route_handlers

SERVICE_NAME = "trading-bot"

class RouteHandlers:
    """Класс с обработчиками маршрутов"""
    
    _status_cache = None
    _status_cache_time = 0
    _status_cache_duration = 5  # 5 секунд
    
    @staticmethod
    def get_status():
        """Получает статус systemd сервиса с кэшированием"""
        current_time = time.time()
        
        # Проверяем нужно ли обновить кэш
        cache_expired = (current_time - RouteHandlers._status_cache_time) > RouteHandlers._status_cache_duration
        
        if RouteHandlers._status_cache is None or cache_expired:
            try:
                result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], 
                                      stdout=subprocess.PIPE, text=True, timeout=5)
                RouteHandlers._status_cache = result.stdout.strip()
                RouteHandlers._status_cache_time = current_time
                print(f"🔄 Статус обновлен: {RouteHandlers._status_cache}")
            except Exception as e:
                print(f"❌ Ошибка получения статуса: {e}")
                RouteHandlers._status_cache = "unknown"
                RouteHandlers._status_cache_time = current_time
        
        return RouteHandlers._status_cache

    @staticmethod
    def get_logs():
        """Получает логи сервиса"""
        try:
            return subprocess.getoutput(f"journalctl -u {SERVICE_NAME}.service -n 30 --no-pager")
        except Exception as e:
            print(f"❌ Ошибка получения логов: {e}")
            return f"Ошибка получения логов: {e}"

    @staticmethod
    def control_service(action):
        """Управляет сервисом (start/stop/restart)"""
        if action not in ['start', 'stop', 'restart']:
            return False, f"Неизвестное действие: {action}"
        
        try:
            result = subprocess.run(["systemctl", action, SERVICE_NAME], 
                                  capture_output=True, text=True, timeout=10)
            RouteHandlers._status_cache = None
            RouteHandlers._status_cache_time = 0
            print(f"🗑️ Кэш статуса очищен после выполнения '{action}'")
            
            if result.returncode == 0:
                return True, f"Команда '{action}' выполнена успешно"
            else:
                return False, f"Ошибка выполнения '{action}': {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, f"Таймаут выполнения команды '{action}'"
        except Exception as e:
            return False, f"Ошибка выполнения '{action}': {e}"

    @staticmethod
    def handle_dashboard():
        """Обработчик главной страницы"""
        return {
            'stats': get_signals_stats()
        }

    @staticmethod
    def handle_control_post():
        """Обработчик POST запросов на странице управления"""
        action = request.form.get('action')
        logs = ''
        message = ''
        
        if action == 'logs':
            logs = RouteHandlers.get_logs()
        elif action in ['start', 'stop', 'restart']:
            success, msg = RouteHandlers.control_service(action)
            message = msg
        else:
            message = f"Неизвестное действие: {action}"
        
        return {
            'logs': logs,
            'message': message
        }

    @staticmethod
    def handle_signals():
        """Обработчик страницы сигналов"""
        # Получаем параметры фильтрации из URL
        filters = {
            'from_date': request.args.get('from_date', ''),
            'to_date': request.args.get('to_date', ''),
            'action': request.args.get('action', ''),
            'symbol': request.args.get('symbol', ''),
            'result': request.args.get('result', ''),
            'strategy': request.args.get('strategy', '')
        }
        
        # Загружаем конфигурацию колонок
        columns_config = load_columns_config()
        
        # Получаем опции для фильтров
        filter_options = get_filter_options()
        
        return {
            'columns_config': columns_config,
            'filters': filters,
            'filter_options': filter_options
        }

    @staticmethod
    def handle_signals_data():
        """API endpoint для получения данных сигналов с пагинацией"""
        try:
            # Получаем параметры фильтрации
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'action': request.args.get('action'),
                'symbol': request.args.get('symbol'),
                'result': request.args.get('result'),
                'strategy': request.args.get('strategy')
            }
            
            # Убираем пустые фильтры
            filters = {k: v for k, v in filters.items() if v}
            
            # Получаем параметры пагинации
            try:
                limit = int(request.args.get('limit', 50))  # По умолчанию 50 записей
                page = int(request.args.get('page', 1))     # По умолчанию первая страница
                
                # Валидируем параметры
                limit = max(10, min(limit, 1000))  # От 10 до 1000 записей
                page = max(1, page)                 # Минимум первая страница
                
                offset = (page - 1) * limit
                
            except (ValueError, TypeError):
                limit = 50
                page = 1
                offset = 0
            
            # Получаем данные с пагинацией
            data = get_signals_data(filters, limit, offset)
            
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
    def handle_save_columns_config():
        """API endpoint для сохранения конфигурации колонок"""
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
                        'message': f'Неверная структура конфигурации для колонки {key}'
                    }), 400
            
            if save_columns_config(config):
                return jsonify({'status': 'success', 'message': 'Конфигурация сохранена'})
            else:
                return jsonify({'status': 'error', 'message': 'Ошибка сохранения'}), 500
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_reset_columns():
        """API endpoint для сброса конфигурации колонок"""
        try:
            config = reset_to_default()
            return jsonify({
                'status': 'success', 
                'message': 'Конфигурация сброшена',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_export_excel():
        """API endpoint для экспорта данных в Excel"""
        try:
            from flask import make_response
            import io
            import xlsxwriter
            from datetime import datetime
            
            # Получаем параметры фильтрации (те же что и для обычного запроса)
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'action': request.args.get('action'),
                'symbol': request.args.get('symbol'),
                'result': request.args.get('result'),
                'strategy': request.args.get('strategy')
            }
            
            # Убираем пустые фильтры
            filters = {k: v for k, v in filters.items() if v}
            
            # Получаем ВСЕ данные (без лимита для экспорта)
            data = get_signals_data(filters, limit=10000, offset=0)
            
            # Получаем конфигурацию колонок
            columns_config = load_columns_config()
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Trading Signals')
            
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
            
            success_format = workbook.add_format({
                'border': 1,
                'font_color': 'green'
            })
            
            error_format = workbook.add_format({
                'border': 1,
                'font_color': 'red'
            })
            
            # Получаем видимые колонки в правильном порядке
            visible_columns = []
            for key, config in sorted(columns_config.items(), key=lambda x: x[1].get('order', 999)):
                if config.get('visible', False):
                    visible_columns.append((key, config))
            
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
                    elif key.startswith('json_'):
                        # Обработка JSON колонок
                        extra_data_index = data['column_map'].get('extra_data')
                        if extra_data_index is not None:
                            extra_data = row_data[extra_data_index]
                            if extra_data:
                                try:
                                    json_data = json.loads(extra_data)
                                    field_name = key.replace('json_', '')
                                    cell_value = json_data.get(field_name, '')
                                except:
                                    cell_value = ''
                            else:
                                cell_value = ''
                        else:
                            cell_value = ''
                    else:
                        cell_value = ''
                    
                    # Форматирование специальных колонок
                    if key == 'result':
                        if cell_value == 'success':
                            worksheet.write(row_num, col_num, '✅ success', success_format)
                        else:
                            worksheet.write(row_num, col_num, '❌ error', error_format)
                    elif key == 'timestamp':
                        # Форматируем дату
                        worksheet.write(row_num, col_num, str(cell_value), cell_format)
                    else:
                        worksheet.write(row_num, col_num, str(cell_value) if cell_value else '', cell_format)
                    
                    col_num += 1
                row_num += 1
            
            # Автоширина колонок
            for i, (key, config) in enumerate(visible_columns):
                worksheet.set_column(i, i, 15)
            
            workbook.close()
            output.seek(0)
            
            # Создаем имя файла с текущей датой и фильтрами
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filter_str = '_'.join([f"{k}-{v}" for k, v in filters.items()]) if filters else 'all'
            filename = f"trading_signals_{timestamp}_{filter_str}.xlsx"
            
            # Создаем ответ с файлом
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            print(f"📊 Экспорт в Excel: {row_num-1} строк, {len(visible_columns)} колонок")
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка экспорта в Excel: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_get_columns_config():
        """API endpoint для получения текущей конфигурации колонок"""
        try:
            config = load_columns_config()
            return jsonify({
                'status': 'success',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500











    # ===== ДОБАВИТЬ В КЛАСС RouteHandlers в ui/routes.py =====

    @staticmethod
    def handle_sockets():
        """Обработчик страницы сокетов"""
        # Получаем параметры фильтрации из URL
        filters = {
            'from_date': request.args.get('from_date', ''),
            'to_date': request.args.get('to_date', ''),
            'event_type': request.args.get('event_type', ''),
            'symbol': request.args.get('symbol', ''),
            'order_id': request.args.get('order_id', ''),
            'status': request.args.get('status', '')
        }
        
        # Загружаем конфигурацию колонок для сокетов
        from ui.sockets_columns_config import load_sockets_columns_config
        columns_config = load_sockets_columns_config()
        
        # Получаем опции для фильтров
        from ui.sockets_handler import get_sockets_filter_options
        filter_options = get_sockets_filter_options()
        
        return {
            'columns_config': columns_config,
            'filters': filters,
            'filter_options': filter_options
        }

    @staticmethod
    def handle_sockets_data():
        """API endpoint для получения данных сокетов с пагинацией"""
        try:
            # Получаем параметры фильтрации
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'event_type': request.args.get('event_type'),
                'symbol': request.args.get('symbol'),
                'order_id': request.args.get('order_id'),
                'status': request.args.get('status')
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
            from ui.sockets_handler import get_sockets_data
            data = get_sockets_data(filters, limit, offset)
            
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
    def handle_save_sockets_columns_config():
        """API endpoint для сохранения конфигурации колонок сокетов"""
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
                        'message': f'Неверная структура конфигурации для колонки сокета {key}'
                    }), 400
            
            from ui.sockets_columns_config import save_sockets_columns_config
            if save_sockets_columns_config(config):
                return jsonify({'status': 'success', 'message': 'Конфигурация сокетов сохранена'})
            else:
                return jsonify({'status': 'error', 'message': 'Ошибка сохранения сокетов'}), 500
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_reset_sockets_columns():
        """API endpoint для сброса конфигурации колонок сокетов"""
        try:
            from ui.sockets_columns_config import reset_sockets_to_default
            config = reset_sockets_to_default()
            return jsonify({
                'status': 'success', 
                'message': 'Конфигурация сокетов сброшена',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def handle_export_sockets_excel():
        """API endpoint для экспорта данных сокетов в Excel"""
        try:
            from flask import make_response
            import io
            import xlsxwriter
            from datetime import datetime
            
            # Получаем параметры фильтрации (те же что и для обычного запроса)
            filters = {
                'from_date': request.args.get('from_date'),
                'to_date': request.args.get('to_date'),
                'event_type': request.args.get('event_type'),
                'symbol': request.args.get('symbol'),
                'order_id': request.args.get('order_id'),
                'status': request.args.get('status')
            }
            
            # Убираем пустые фильтры
            filters = {k: v for k, v in filters.items() if v}
            
            # Получаем ВСЕ данные (без лимита для экспорта)
            from ui.sockets_handler import get_sockets_data
            data = get_sockets_data(filters, limit=10000, offset=0)
            
            # Получаем конфигурацию колонок
            from ui.sockets_columns_config import load_sockets_columns_config, get_visible_sockets_columns
            columns_config = load_sockets_columns_config()
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Socket Messages')
            
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
            visible_columns = get_visible_sockets_columns(columns_config)
            
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
                    elif key.startswith('socket_'):
                        # Обработка JSON колонок
                        raw_message_index = data['column_map'].get('raw_message')
                        if raw_message_index is not None:
                            raw_message = row_data[raw_message_index]
                            if raw_message:
                                try:
                                    import json
                                    json_data = json.loads(raw_message)
                                    field_name = key.replace('socket_', '')
                                    cell_value = json_data.get(field_name, '')
                                except:
                                    cell_value = ''
                            else:
                                cell_value = ''
                        else:
                            cell_value = ''
                    else:
                        cell_value = ''
                    
                    worksheet.write(row_num, col_num, str(cell_value) if cell_value else '', cell_format)
                    col_num += 1
                row_num += 1
            
            # Автоширина колонок
            for i, (key, config) in enumerate(visible_columns):
                worksheet.set_column(i, i, 15)
            
            workbook.close()
            output.seek(0)
            
            # Создаем имя файла с текущей датой и фильтрами
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filter_str = '_'.join([f"{k}-{v}" for k, v in filters.items()]) if filters else 'all'
            filename = f"socket_messages_{timestamp}_{filter_str}.xlsx"
            
            # Создаем ответ с файлом
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            print(f"📊 Экспорт сокетов в Excel: {row_num-1} строк, {len(visible_columns)} колонок")
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка экспорта сокетов в Excel: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500









# ===== MESSAGES ROUTES =====
    
    @staticmethod
    def handle_messages():
        """Обработчик страницы сообщений"""
        return messages_route_handlers.handle_messages()
    
    @staticmethod
    def handle_messages_data():
        """API endpoint для получения данных сообщений с пагинацией"""
        return messages_route_handlers.handle_messages_data()
    
    @staticmethod
    def handle_save_messages_columns_config():
        """API endpoint для сохранения конфигурации колонок сообщений"""
        return messages_route_handlers.handle_save_messages_columns_config()
    
    @staticmethod
    def handle_reset_messages_columns():
        """API endpoint для сброса конфигурации колонок сообщений"""
        return messages_route_handlers.handle_reset_messages_columns()
    
    @staticmethod
    def handle_export_messages_excel():
        """API endpoint для экспорта данных сообщений в Excel"""
        return messages_route_handlers.handle_export_messages_excel()
    
    @staticmethod
    def handle_get_messages_columns_config():
        """API endpoint для получения текущей конфигурации колонок сообщений"""
        return messages_route_handlers.handle_get_messages_columns_config()










# Создаем экземпляр для использования
route_handlers = RouteHandlers()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля routes...")
    
    print(f"📊 Статус сервиса: {route_handlers.get_status()}")
    
    dashboard_data = route_handlers.handle_dashboard()
    print(f"📈 Статистика дашборда: {dashboard_data['stats']['total_signals']} сигналов")
    
    signals_data = route_handlers.handle_signals()
    print(f"📋 Конфигурация колонок: {len(signals_data['columns_config'])} колонок")