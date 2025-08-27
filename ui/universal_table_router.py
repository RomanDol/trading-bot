# ===== ui/universal_table_router.py =====
"""
Универсальный роутер для всех типов таблиц
Заменяет дублирование кода для signals, sockets, messages
"""
import os
import json
from flask import request, jsonify, render_template, make_response
from typing import Dict, Any, List, Optional

class TableConfig:
    """Конфигурация таблицы"""
    
    def __init__(self, 
                 table_type: str,
                 db_manager,
                 default_columns: Dict[str, Any],
                 config_file: str,
                 template_name: str,
                 page_title: str,
                 data_fetcher_func,
                 filter_options_func=None,
                 excel_export_func=None):
        self.table_type = table_type
        self.db_manager = db_manager
        self.default_columns = default_columns
        self.config_file = config_file
        self.template_name = template_name
        self.page_title = page_title
        self.data_fetcher_func = data_fetcher_func
        self.filter_options_func = filter_options_func
        self.excel_export_func = excel_export_func

class UniversalTableRouter:
    """Универсальный роутер для всех типов таблиц"""
    
    def __init__(self):
        self.tables: Dict[str, TableConfig] = {}
        
    def register_table(self, table_config: TableConfig):
        """Регистрирует конфигурацию таблицы"""
        self.tables[table_config.table_type] = table_config
        print(f"✅ Зарегистрирована таблица: {table_config.table_type}")
    
    def load_columns_config(self, table_type: str) -> Dict[str, Any]:
        """Универсальная загрузка конфигурации колонок"""
        if table_type not in self.tables:
            raise ValueError(f"Неизвестный тип таблицы: {table_type}")
            
        config = self.tables[table_type]
        
        try:
            if os.path.exists(config.config_file):
                with open(config.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    if loaded_config and len(loaded_config) > 0:
                        print(f"✅ Загружена конфигурация {table_type}: {len(loaded_config)} колонок")
                        return loaded_config
                    else:
                        print(f"⚠️ Конфигурационный файл {table_type} пустой, создаем новый")
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации {table_type}: {e}")
        
        print(f"🔧 Создаем конфигурацию {table_type} по умолчанию")
        return self._sync_with_database(table_type, config.default_columns.copy())
    
    def save_columns_config(self, table_type: str, columns_config: Dict[str, Any]) -> bool:
        """Универсальное сохранение конфигурации колонок"""
        if table_type not in self.tables:
            return False
            
        config = self.tables[table_type]
        
        try:
            with open(config.config_file, 'w', encoding='utf-8') as f:
                json.dump(columns_config, f, indent=2, ensure_ascii=False)
            print(f"✅ Конфигурация {table_type} сохранена")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения конфигурации {table_type}: {e}")
            return False
    
    def _sync_with_database(self, table_type: str, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Синхронизация конфигурации с реальными колонками БД"""
        config = self.tables[table_type]
        
        try:
            db_columns = config.db_manager.get_columns()
            updated = False
            
            # Добавляем новые колонки из БД
            for col in db_columns:
                if col not in default_config:
                    is_visible = col in ['id', 'timestamp', 'time', 'action', 'symbol', 'quantity', 'result', 'strategy', 'type', 'event_type', 'status']
                    
                    default_config[col] = {
                        'name': col.replace('_', ' ').title(),
                        'visible': is_visible,
                        'order': len(default_config),
                        'width': '120px'
                    }
                    updated = True
            
            # Удаляем колонки которых нет в БД
            existing_cols = list(default_config.keys())
            for col in existing_cols:
                if col not in db_columns:
                    del default_config[col]
                    updated = True
            
            if updated:
                self.save_columns_config(table_type, default_config)
                print(f"🔄 Конфигурация {table_type} синхронизирована с БД")
                
        except Exception as e:
            print(f"⚠️ Ошибка синхронизации {table_type} с БД: {e}")
        
        return default_config
    
    def reset_to_default(self, table_type: str) -> Dict[str, Any]:
        """Сброс конфигурации к настройкам по умолчанию"""
        if table_type not in self.tables:
            raise ValueError(f"Неизвестный тип таблицы: {table_type}")
            
        config = self.tables[table_type]
        default_config = self._sync_with_database(table_type, config.default_columns.copy())
        
        try:
            if os.path.exists(config.config_file):
                os.remove(config.config_file)
            self.save_columns_config(table_type, default_config)
            print(f"🔄 Конфигурация {table_type} сброшена к умолчанию")
        except Exception as e:
            print(f"❌ Ошибка сброса конфигурации {table_type}: {e}")
        
        return default_config
    
    def get_visible_columns(self, table_type: str) -> List[str]:
        """Получает список видимых колонок в правильном порядке"""
        config = self.load_columns_config(table_type)
        
        # Сортируем по порядку и фильтруем видимые
        sorted_columns = sorted(config.items(), key=lambda x: x[1].get('order', 999))
        return [col for col, settings in sorted_columns if settings.get('visible', False)]
    
    # ===== FLASK ROUTE HANDLERS =====
    
    def handle_table_page(self, table_type: str):
        """Универсальный обработчик страницы таблицы"""
        if table_type not in self.tables:
            return {"error": "Unknown table type"}
            
        config = self.tables[table_type]
        
        # Получаем параметры фильтрации из URL
        filters = {}
        for key in request.args.keys():
            value = request.args.get(key, '').strip()
            if value:
                filters[key] = value
        
        # Загружаем конфигурацию колонок
        columns_config = self.load_columns_config(table_type)
        
        # Получаем опции для фильтров если есть функция
        filter_options = {}
        if config.filter_options_func:
            try:
                filter_options = config.filter_options_func()
            except Exception as e:
                print(f"⚠️ Ошибка получения опций фильтров для {table_type}: {e}")
        
        return {
            'table_type': table_type,
            'page_title': config.page_title,
            'columns_config': columns_config,
            'filters': filters,
            'filter_options': filter_options
        }
    
    def handle_table_data(self, table_type: str):
        """Универсальный API endpoint для получения данных таблицы"""
        if table_type not in self.tables:
            return jsonify({'error': 'Unknown table type'}), 404
            
        config = self.tables[table_type]
        
        try:
            # Получаем параметры фильтрации
            filters = {}
            for key in request.args.keys():
                if key not in ['limit', 'page']:
                    value = request.args.get(key)
                    if value:
                        filters[key] = value
            
            # Получаем параметры пагинации
            limit = max(10, min(int(request.args.get('limit', 50)), 1000))
            page = max(1, int(request.args.get('page', 1)))
            offset = (page - 1) * limit
            
            # Получаем данные через зарегистрированную функцию
            data_result = config.data_fetcher_func(filters, limit, offset)
            
            return jsonify({
                'status': 'success',
                'data': data_result['data'],
                'total': data_result['total'],
                'page': page,
                'total_pages': (data_result['total'] + limit - 1) // limit,
                'has_next': offset + limit < data_result['total'],
                'has_prev': page > 1
            })
            
        except Exception as e:
            print(f"❌ Ошибка получения данных {table_type}: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_save_columns_config(self, table_type: str):
        """Универсальный API endpoint для сохранения конфигурации колонок"""
        try:
            config_data = request.json
            if not config_data:
                return jsonify({'status': 'error', 'message': 'Нет данных конфигурации'}), 400
            
            success = self.save_columns_config(table_type, config_data)
            
            if success:
                return jsonify({'status': 'success', 'message': f'Конфигурация {table_type} сохранена'})
            else:
                return jsonify({'status': 'error', 'message': f'Ошибка сохранения конфигурации {table_type}'}), 500
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_reset_columns(self, table_type: str):
        """Универсальный API endpoint для сброса конфигурации колонок"""
        try:
            config = self.reset_to_default(table_type)
            return jsonify({
                'status': 'success', 
                'message': f'Конфигурация {table_type} сброшена',
                'config': config
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_get_columns_config(self, table_type: str):
        """Универсальный API endpoint для получения конфигурации колонок"""
        try:
            config = self.load_columns_config(table_type)
            return jsonify({'status': 'success', 'config': config})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_export_excel(self, table_type: str):
        """Универсальный API endpoint для экспорта в Excel"""
        if table_type not in self.tables:
            return jsonify({'error': 'Unknown table type'}), 404
            
        config = self.tables[table_type]
        
        if not config.excel_export_func:
            return jsonify({'error': 'Export not supported for this table'}), 400
        
        try:
            return config.excel_export_func(request, self.load_columns_config(table_type))
        except Exception as e:
            print(f"❌ Ошибка экспорта {table_type} в Excel: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

# Создаем глобальный экземпляр
universal_table_router = UniversalTableRouter()

if __name__ == "__main__":
    print("🧪 Тестирование универсального роутера таблиц...")
    print("✅ Модуль успешно загружен")