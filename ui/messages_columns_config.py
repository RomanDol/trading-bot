"""
Модуль для управления конфигурацией колонок таблицы сообщений
"""
import json
import os
from core.messages_database import messages_db_manager

MESSAGES_COLUMNS_CONFIG_FILE = "messages_columns_config.json"

# Настройки колонок по умолчанию для сообщений
DEFAULT_MESSAGES_COLUMNS = {
    'id': {'name': '#', 'visible': True, 'order': 0, 'width': '60px'},
    'time': {'name': 'Time', 'visible': True, 'order': 1, 'width': '140px'},
    'type': {'name': 'Type', 'visible': True, 'order': 2, 'width': '150px'},
    'message': {'name': 'Message', 'visible': True, 'order': 3, 'width': '800px'}
}

def load_messages_columns_config():
    """Загружает конфигурацию колонок сообщений из файла"""
    try:
        if os.path.exists(MESSAGES_COLUMNS_CONFIG_FILE):
            with open(MESSAGES_COLUMNS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Проверяем что конфигурация не пустая
                if config and len(config) > 0:
                    print(f"✅ Загружена конфигурация сообщений: {len(config)} колонок")
                    return config
                else:
                    print("⚠️ Конфигурационный файл сообщений пустой, создаем новый")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации колонок сообщений: {e}")
    
    print("🔧 Создаем конфигурацию сообщений по умолчанию")
    return sync_messages_with_database(DEFAULT_MESSAGES_COLUMNS.copy())

def save_messages_columns_config(config):
    """Сохраняет конфигурацию колонок сообщений в файл"""
    try:
        with open(MESSAGES_COLUMNS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Конфигурация колонок сообщений сохранена")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения конфигурации колонок сообщений: {e}")
        return False

def add_missing_messages_columns_to_config(config):
    """Добавляет новые колонки из БД сообщений в существующую конфигурацию"""
    db_columns = messages_db_manager.get_columns()
    updated = False
    
    # Добавляем ТОЛЬКО новые колонки из БД
    for col in db_columns:
        if col not in config:
            # Все основные колонки видимы по умолчанию
            is_visible = col in ['id', 'time', 'type', 'message']
            
            config[col] = {
                'name': col.replace('_', ' ').title(),
                'visible': is_visible,
                'order': len(config),
                'width': '100px'
            }
            updated = True
            print(f"➕ Добавлена новая колонка сообщений: {col} (visible: {is_visible})")
    
    return config, updated

def sync_messages_with_database(config, auto_save=True):
    """Синхронизирует конфигурацию с реальными колонками БД сообщений"""
    db_columns = messages_db_manager.get_columns()
    updated = False
    
    # Добавляем новые колонки из БД
    for col in db_columns:
        if col not in config:
            # Все основные колонки видимы по умолчанию
            is_visible = col in ['id', 'time', 'type', 'message']
            
            config[col] = {
                'name': col.replace('_', ' ').title(),
                'visible': is_visible,
                'order': len(config),
                'width': '100px'
            }
            updated = True
            print(f"➕ Добавлена колонка сообщений: {col} (visible: {is_visible})")
    
    # Удаляем колонки, которых нет в БД
    config_keys = list(config.keys())
    for col in config_keys:
        if col not in db_columns:
            del config[col]
            updated = True
            print(f"➖ Удалена колонка сообщений: {col}")
    
    # Сохраняем только если есть изменения И разрешено автосохранение
    if updated and auto_save:
        save_messages_columns_config(config)
        print("💾 Конфигурация сообщений автоматически создана")
        
    return config

def get_visible_messages_columns(config):
    """Возвращает список видимых колонок сообщений в правильном порядке"""
    visible_columns = [
        (key, col_config) for key, col_config in config.items() 
        if col_config.get('visible', True)
    ]
    visible_columns.sort(key=lambda x: x[1].get('order', 999))
    return visible_columns

def reset_messages_to_default():
    """Сбрасывает конфигурацию сообщений к настройкам по умолчанию"""
    config = sync_messages_with_database(DEFAULT_MESSAGES_COLUMNS.copy())
    save_messages_columns_config(config)
    return config

if __name__ == "__main__":
    print("🧪 Тестирование модуля messages_columns_config...")
    
    # Тест загрузки конфигурации
    config = load_messages_columns_config()
    print(f"📋 Конфигурация колонок сообщений: {len(config)} колонок")
    
    visible = get_visible_messages_columns(config)
    print(f"👁️ Видимых колонок сообщений: {len(visible)}")
    
    # Тест сброса
    reset_config = reset_messages_to_default()
    print(f"🔄 Сброшенная конфигурация: {len(reset_config)} колонок")