# ===== ui/universal_integration_simple.py =====
"""
Упрощенная интеграция - все колонки по умолчанию из БД
"""
from .universal_table_router import universal_table_router, TableConfig
from .signals_handler import get_signals_data, get_filter_options
from .messages_handler import get_messages_data

def setup_universal_tables():
    """Настройка таблиц без дефолтных настроек"""
    
    # SIGNALS с правильным db_manager
    from core.database import db_manager
    signals_config = TableConfig(
        table_type='signals',
        db_manager=db_manager,  # Исправлено
        default_columns={},
        config_file='configs/signals.json',
        template_name='universal_table.html',
        page_title='Trading Signals',
        data_fetcher_func=adapt_signals_data,
        filter_options_func=get_filter_options
    )
    universal_table_router.register_table(signals_config)
    
    # MESSAGES с правильным db_manager
    from core.messages_database import messages_db_manager
    messages_config = TableConfig(
        table_type='messages',
        db_manager=messages_db_manager,  # Исправлено
        default_columns={},
        config_file='configs/messages.json',
        template_name='universal_table.html', 
        page_title='All Messages',
        data_fetcher_func=adapt_messages_data
    )
    universal_table_router.register_table(messages_config)
    
    print("✅ Упрощенные таблицы настроены: signals, messages")

def adapt_signals_data(filters, limit, offset):
    """Адаптер для signals"""
    result = get_signals_data(filters, limit, offset)
    return {
        'data': result.get('rows', []),
        'columns': result.get('columns', []),
        'total': result.get('total_count', 0)
    }

def adapt_messages_data(filters, limit, offset):
    """Адаптер для messages"""
    result = get_messages_data(filters, limit, offset)
    return {
        'data': result.get('rows', []),
        'columns': result.get('columns', []),
        'total': result.get('total_count', 0)
    }

    # SOCKETS с правильным db_manager
    try:
        from core.sockets_database import sockets_db_manager
        from ui.sockets_handler import get_sockets_data
        
        sockets_config = TableConfig(
            table_type='sockets',
            db_manager=sockets_db_manager,
            default_columns={},
            config_file='configs/sockets.json',
            template_name='universal_table.html',
            page_title='WebSocket Messages',
            data_fetcher_func=adapt_sockets_data
        )
        universal_table_router.register_table(sockets_config)
        print("✅ Sockets таблица добавлена")
    except Exception as e:
        print(f"⚠️ Не удалось настроить sockets: {e}")

def adapt_sockets_data(filters, limit, offset):
    """Адаптер для sockets"""
    from ui.sockets_handler import get_sockets_data
    result = get_sockets_data(filters, limit, offset)
    return {
        'data': result.get('rows', []),
        'columns': result.get('columns', []),
        'total': result.get('total_count', 0)
    }
