# ===== bot_ui.py =====
"""
Flask веб-интерфейс с НАСТОЯЩИМ универсальным ридером таблиц
"""
from flask import Flask, render_template, request
from ui.auth import auth_manager
from ui.routes import route_handlers
from ui.universal_reader import universal_reader

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.context_processor
def inject_globals():
    return {'status': route_handlers.get_status()}

@app.before_request
def auth_middleware():
    return auth_manager.require_auth()

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/', endpoint='dashboard')
def dashboard():
    data = route_handlers.handle_dashboard()
    return render_template('dashboard.html', **data)

@app.route('/control', methods=['GET', 'POST'], endpoint='control')
def control():
    if request.method == 'POST':
        data = route_handlers.handle_control_post()
    else:
        data = {'logs': '', 'message': ''}
    return render_template('control.html', **data)

# ===== УНИВЕРСАЛЬНЫЙ РИДЕР ДЛЯ ВСЕХ ТАБЛИЦ =====

@app.route('/<table_type>', methods=['GET'])
def universal_table(table_type):
    """ОДИН маршрут для всех таблиц"""
    data = universal_reader.handle_table_page(table_type)
    if 'error' in data:
        return render_template('error.html', 
                             error_code=404, 
                             error_message=data['error']), 404
    return render_template('universal_table.html', **data)

@app.route('/<table_type>/data')
def universal_table_data(table_type):
    """ОДИН API endpoint для данных всех таблиц"""
    return universal_reader.handle_table_data(table_type)

@app.route('/<table_type>/save_columns_config', methods=['POST'])
def universal_save_config(table_type):
    """ОДИН API endpoint для сохранения конфигов всех таблиц"""
    return universal_reader.handle_save_config(table_type)

# ===== ОБРАТНАЯ СОВМЕСТИМОСТЬ (старые URL) =====

@app.route('/signals_data')
def signals_data_old():
    """Старый URL signals_data"""
    return universal_reader.handle_table_data('signals')

@app.route('/save_columns_config', methods=['POST'])
def save_columns_config_old():
    """Старый URL save_columns_config"""
    return universal_reader.handle_save_config('signals')

# ===== УТИЛИТЫ =====

@app.template_filter('tojsonfilter')
def tojson_filter(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Страница не найдена"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Внутренняя ошибка сервера"), 500

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI с универсальным ридером...")
    print(f"👤 Пользователь: {auth_manager.username}")
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://localhost:8888")
    print("📊 Универсальные таблицы: signals, messages, sockets")
    print("🔗 URL: /<table_type> - работает для любой таблицы")
    
    app.run(host='0.0.0.0', port=8888, debug=True)