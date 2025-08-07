"""
Модуль для управления конфигурацией колонок таблицы сигналов
Перенесено из columns_config.py
"""
import json
import os
from core.database import db_manager

COLUMNS_CONFIG_FILE = "columns_config.json"

# Настройки колонок по умолчанию
DEFAULT_COLUMNS = {
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
}

def load_columns_config():
    """Загружает конфигурацию колонок из файла"""
    try:
        if os.path.exists(COLUMNS_CONFIG_FILE):
            with open(COLUMNS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return sync_with_database(config)
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации колонок: {e}")
    
    return sync_with_database(DEFAULT_COLUMNS.copy())

def save_columns_config(config):
    """Сохраняет конфигурацию колонок в файл"""
    try:
        with open(COLUMNS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Конфигурация колонок сохранена")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения конфигурации колонок: {e}")
        return False

def sync_with_database(config):
    """Синхронизирует конфигурацию с реальными колонками БД"""
    db_columns = db_manager.get_columns()
    updated = False
    
    # Добавляем новые колонки из БД
    for col in db_columns:
        if col not in config:
            config[col] = {
                'name': col.replace('_', ' ').title(),
                'visible': True if col in ['id', 'timestamp', 'action', 'symbol'] else False,
                'order': len(config),
                'width': '100px'
            }
            updated = True
            print(f"➕ Добавлена новая колонка: {col}")
    
    # Удаляем колонки, которых нет в БД
    config_keys = list(config.keys())
    for col in config_keys:
        if col not in db_columns:
            del config[col]
            updated = True
            print(f"➖ Удалена колонка: {col}")
    
    if updated:
        save_columns_config(config)
        
    return config

def get_visible_columns(config):
    """Возвращает список видимых колонок в правильном порядке"""
    visible_columns = [
        (key, col_config) for key, col_config in config.items() 
        if col_config.get('visible', True)
    ]
    visible_columns.sort(key=lambda x: x[1].get('order', 999))
    return visible_columns

def reset_to_default():
    """Сбрасывает конфигурацию к настройкам по умолчанию"""
    config = sync_with_database(DEFAULT_COLUMNS.copy())
    save_columns_config(config)
    return config

if __name__ == "__main__":
    print("🧪 Тестирование UI модулей...")
    
    # Тест signals_handler
    data = get_signals_data(limit=5)
    print(f"📊 Получено записей: {data['total_found']}")
    
    # Тест columns_config  
    config = load_columns_config()
    print(f"📋 Конфигурация колонок: {len(config)} колонок")
    
    visible = get_visible_columns(config)
    print(f"👁️ Видимых колонок: {len(visible)}")