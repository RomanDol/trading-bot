"""
Модуль для управления конфигурацией колонок таблицы сокетов
"""
import json
import os
from core.sockets_database import sockets_db_manager

SOCKETS_COLUMNS_CONFIG_FILE = "sockets_columns_config.json"

# Настройки колонок по умолчанию для сокетов
DEFAULT_SOCKETS_COLUMNS = {
    'id': {'name': '#', 'visible': True, 'order': 0, 'width': '60px'},
    'timestamp': {'name': 'timestamp', 'visible': True, 'order': 1, 'width': '140px'},
    'event_type': {'name': 'event_type', 'visible': True, 'order': 2, 'width': '150px'},
    'symbol': {'name': 'symbol', 'visible': True, 'order': 3, 'width': '100px'},
    'order_id': {'name': 'order_id', 'visible': True, 'order': 4, 'width': '120px'},
    'status': {'name': 'status', 'visible': True, 'order': 5, 'width': '100px'},
    'raw_message': {'name': 'raw_message', 'visible': False, 'order': 6, 'width': '800px'}
}

def load_sockets_columns_config():
    """Загружает конфигурацию колонок сокетов из файла"""
    try:
        if os.path.exists(SOCKETS_COLUMNS_CONFIG_FILE):
            with open(SOCKETS_COLUMNS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Проверяем что конфигурация не пустая
                if config and len(config) > 0:
                    print(f"✅ Загружена конфигурация сокетов: {len(config)} колонок")
                    return config
                else:
                    print("⚠️ Конфигурационный файл сокетов пустой, создаем новый")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации колонок сокетов: {e}")
    
    print("🔧 Создаем конфигурацию сокетов по умолчанию")
    return sync_sockets_with_database(DEFAULT_SOCKETS_COLUMNS.copy())

def save_sockets_columns_config(config):
    """Сохраняет конфигурацию колонок сокетов в файл"""
    try:
        with open(SOCKETS_COLUMNS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Конфигурация колонок сокетов сохранена")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения конфигурации колонок сокетов: {e}")
        return False

def add_missing_sockets_columns_to_config(config):
    """Добавляет новые колонки из БД сокетов в существующую конфигурацию"""
    db_columns = sockets_db_manager.get_columns()
    updated = False
    
    # Добавляем ТОЛЬКО новые колонки из БД
    for col in db_columns:
        if col not in config:
            # Только основные колонки видимы по умолчанию
            is_visible = col in ['id', 'timestamp', 'event_type', 'symbol', 'order_id', 'status']
            
            config[col] = {
                'name': col,
                'visible': is_visible,
                'order': len(config),
                'width': '100px'
            }
            updated = True
            print(f"➕ Добавлена новая колонка сокета: {col} (visible: {is_visible})")
    
    return config, updated

def sync_sockets_with_database(config, auto_save=True):
    """Синхронизирует конфигурацию с реальными колонками БД сокетов"""
    db_columns = sockets_db_manager.get_columns()
    updated = False
    
    # Добавляем новые колонки из БД
    for col in db_columns:
        if col not in config:
            # Только основные колонки видимы по умолчанию
            is_visible = col in ['id', 'timestamp', 'event_type', 'symbol', 'order_id', 'status']
            
            config[col] = {
                'name': col,
                'visible': is_visible,
                'order': len(config),
                'width': '100px'
            }
            updated = True
            print(f"➕ Добавлена колонка сокета: {col} (visible: {is_visible})")
    
    # Удаляем колонки, которых нет в БД
    config_keys = list(config.keys())
    for col in config_keys:
        if col not in db_columns:
            del config[col]
            updated = True
            print(f"➖ Удалена колонка сокета: {col}")
    
    # Сохраняем только если есть изменения И разрешено автосохранение
    if updated and auto_save:
        save_sockets_columns_config(config)
        print("💾 Конфигурация сокетов автоматически создана")
        
    return config

def get_visible_sockets_columns(config):
    """Возвращает список видимых колонок сокетов в правильном порядке"""
    visible_columns = [
        (key, col_config) for key, col_config in config.items() 
        if col_config.get('visible', True)
    ]
    visible_columns.sort(key=lambda x: x[1].get('order', 999))
    return visible_columns

def reset_sockets_to_default():
    """Сбрасывает конфигурацию сокетов к настройкам по умолчанию"""
    config = sync_sockets_with_database(DEFAULT_SOCKETS_COLUMNS.copy())
    save_sockets_columns_config(config)
    return config

if __name__ == "__main__":
    print("🧪 Тестирование модуля sockets_columns_config...")
    
    # Тест загрузки конфигурации
    config = load_sockets_columns_config()
    print(f"📋 Конфигурация колонок сокетов: {len(config)} колонок")
    
    visible = get_visible_sockets_columns(config)
    print(f"👁️ Видимых колонок сокетов: {len(visible)}")
    
    # Тест сброса
    reset_config = reset_sockets_to_default()
    print(f"🔄 Сброшенная конфигурация: {len(reset_config)} колонок")