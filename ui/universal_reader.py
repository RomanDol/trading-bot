# ===== ui/universal_reader.py =====
"""
НАСТОЯЩИЙ универсальный ридер таблиц
Один код для всех таблиц без исключений
"""
import os
import json
from flask import request, jsonify, render_template

class UniversalTableReader:
    """Единственный ридер для всех таблиц"""
    
    def __init__(self):
        # Карта таблиц к их обработчикам данных и БД
        self.table_handlers = {
            'signals': {
                'data_func': self._get_signals_data,
                'db_manager': None
            },
            'messages': {
                'data_func': self._get_messages_data,
                'db_manager': None
            },
            'sockets': {
                'data_func': self._get_sockets_data, 
                'db_manager': None
            }
        }
    
    def handle_table_page(self, table_type: str):
        """ОДИН обработчик для всех типов таблиц"""
        if table_type not in self.table_handlers:
            return {'error': f'Unknown table type: {table_type}'}
        
        # Получаем фильтры из URL
        filters = {k: v for k, v in request.args.items() if v.strip()}
        
        # Загружаем конфигурацию (или создаем базовую)
        config = self._load_config(table_type)
        
        return {
            'table_type': table_type,
            'page_title': self._get_page_title(table_type),
            'columns_config': config,
            'filters': filters,
            'filter_options': {}
        }
    
    def handle_table_data(self, table_type: str):
        """ОДИН обработчик данных для всех таблиц"""
        if table_type not in self.table_handlers:
            return jsonify({'error': 'Unknown table type'}), 404
        
        try:
            # Получаем параметры
            filters = {k: v for k, v in request.args.items() 
                      if k not in ['limit', 'page'] and v}
            limit = max(10, min(int(request.args.get('limit', 50)), 1000))
            page = max(1, int(request.args.get('page', 1)))
            offset = (page - 1) * limit
            
            # Получаем данные через ЕДИНУЮ функцию
            data = self.table_handlers[table_type]['data_func'](filters, limit, offset)
            
            return jsonify({
                'status': 'success',
                'data': data['rows'],
                'total': data['total'],
                'page': page,
                'total_pages': (data['total'] + limit - 1) // limit,
                'has_next': offset + limit < data['total'],
                'has_prev': page > 1
            })
            
        except Exception as e:
            print(f"Ошибка получения данных {table_type}: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_save_config(self, table_type: str):
        """ОДИН обработчик сохранения конфигов"""
        try:
            config_data = request.json
            if not config_data:
                return jsonify({'status': 'error', 'message': 'No config data'}), 400
            
            config_path = f"configs/{table_type}.json"
            os.makedirs('configs', exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return jsonify({'status': 'success', 'message': f'Config saved for {table_type}'})
            
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _load_config(self, table_type: str):
        """Загружает конфиг или создает базовый из БД"""
        config_path = f"configs/{table_type}.json"
        
        # Пытаемся загрузить существующий конфиг
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config:
                        print(f"Загружен конфиг {table_type}: {len(config)} колонок")
                        return config
            except Exception as e:
                print(f"Ошибка загрузки конфига {table_type}: {e}")
        
        # Создаем базовый конфиг из БД
        print(f"Создается базовый конфиг {table_type}")
        return self._create_basic_config(table_type)
    
    def _create_basic_config(self, table_type: str):
        """Создает базовую конфигурацию из колонок БД"""
        try:
            # Получаем колонки из БД
            columns = self._get_db_columns(table_type)
            
            config = {}
            for i, col in enumerate(columns):
                config[col] = {
                    'name': col,
                    'visible': True,
                    'order': i,
                    'width': '120px'
                }
            
            print(f"Создан базовый конфиг: {len(config)} колонок")
            return config
            
        except Exception as e:
            print(f"Ошибка создания базового конфига: {e}")
            return {}
    
    def _get_db_columns(self, table_type: str):
        """Получает список колонок из БД для любой таблицы"""
        try:
            if table_type == 'signals':
                from core.database import db_manager
                return db_manager.get_columns()
            elif table_type == 'messages':
                from core.messages_database import messages_db_manager
                return messages_db_manager.get_columns()
            elif table_type == 'sockets':
                from core.sockets_database import sockets_db_manager
                return sockets_db_manager.get_columns()
            else:
                return []
        except Exception as e:
            print(f"Ошибка получения колонок {table_type}: {e}")
            return []
    
    def _get_signals_data(self, filters, limit, offset):
        """Получение данных signals"""
        from ui.signals_handler import get_signals_data
        result = get_signals_data(filters, limit, offset)
        return {
            'rows': result.get('rows', []),
            'total': result.get('total_count', 0)
        }
    
    def _get_messages_data(self, filters, limit, offset):
        """Получение данных messages"""
        from ui.messages_handler import get_messages_data
        result = get_messages_data(filters, limit, offset)
        return {
            'rows': result.get('rows', []),
            'total': result.get('total_count', 0)
        }
    
    def _get_sockets_data(self, filters, limit, offset):
        """Получение данных sockets"""
        try:
            from ui.sockets_handler import get_sockets_data
            result = get_sockets_data(filters, limit, offset)
            return {
                'rows': result.get('rows', []),
                'total': result.get('total_count', 0)
            }
        except Exception as e:
            print(f"Ошибка получения sockets данных: {e}")
            return {'rows': [], 'total': 0}
    
    def _get_page_title(self, table_type: str):
        """Возвращает заголовок страницы"""
        titles = {
            'signals': 'Trading Signals',
            'messages': 'All Messages', 
            'sockets': 'WebSocket Messages'
        }
        return titles.get(table_type, table_type.title())

# Создаем ЕДИНСТВЕННЫЙ экземпляр
universal_reader = UniversalTableReader()
