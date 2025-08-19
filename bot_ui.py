"""
Flask веб-интерфейс для управления Trading Bot
Очищенная версия без обратной совместимости
"""
from flask import Flask, render_template, request
from ui.auth import auth_manager
from ui.routes import route_handlers

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Поддержка UTF-8 в JSON

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ВСЕХ ШАБЛОНОВ =====

@app.context_processor
def inject_globals():
    """Внедряет глобальные переменные во все шаблоны"""
    return {
        'status': route_handlers.get_status()
    }

# ===== MIDDLEWARE =====

@app.before_request
def auth_middleware():
    """Middleware для проверки аутентификации"""
    return auth_manager.require_auth()

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/', endpoint='dashboard')
def dashboard():
    """Главная страница - дашборд"""
    data = route_handlers.handle_dashboard()
    return render_template('dashboard.html', **data)

@app.route('/control', methods=['GET', 'POST'], endpoint='control')
def control():
    """Страница управления сервисом"""
    if request.method == 'POST':
        data = route_handlers.handle_control_post()
    else:
        data = {
            'logs': '', 
            'message': ''
        }
    
    return render_template('control.html', **data)

@app.route('/signals', endpoint='signals')
def signals():
    """Страница истории сигналов"""
    data = route_handlers.handle_signals()
    return render_template('signals.html', **data)

# ===== API МАРШРУТЫ =====

@app.route('/signals_data')
def signals_data():
    """API: Получение данных сигналов (AJAX)"""
    return route_handlers.handle_signals_data()

@app.route('/save_columns_config', methods=['POST'])
def save_columns_config():
    """API: Сохранение конфигурации колонок"""
    return route_handlers.handle_save_columns_config()

@app.route('/reset_columns', methods=['POST'])
def reset_columns():
    """API: Сброс конфигурации колонок"""
    return route_handlers.handle_reset_columns()

@app.route('/get_columns_config')
def get_columns_config():
    """API: Получение конфигурации колонок"""
    return route_handlers.handle_get_columns_config()

@app.route('/export_excel')
def export_excel():
    """API: Экспорт данных в Excel"""
    return route_handlers.handle_export_excel()

# ===== ФИЛЬТРЫ JINJA2 =====

@app.template_filter('tojsonfilter')
def tojson_filter(obj):
    """Фильтр для преобразования объекта в JSON для JavaScript"""
    import json
    return json.dumps(obj, ensure_ascii=False)

# ===== ОБРАБОТЧИКИ ОШИБОК =====

@app.errorhandler(404)
def not_found(error):
    """Обработчик 404 ошибки"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Страница не найдена"), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибки"""
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Внутренняя ошибка сервера"), 500

if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI...")
    print(f"👤 Пользователь: {auth_manager.username}")
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://localhost:8888")
    
    app.run(host='0.0.0.0', port=8888, debug=True)
