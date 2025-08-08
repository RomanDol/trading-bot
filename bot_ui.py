"""
Flask веб-интерфейс для управления Trading Bot
Упрощенная версия с выносом логики в модули
"""
from flask import Flask, render_template, request
from ui.auth import require_auth
from ui.routes import ROUTE_HANDLERS

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Поддержка UTF-8 в JSON

# ===== MIDDLEWARE =====

@app.before_request
def auth_middleware():
    """Middleware для проверки аутентификации"""
    return require_auth()

# ===== ОСНОВНЫЕ МАРШРУТЫ =====

@app.route('/')
def dashboard():
    """Главная страница - дашборд"""
    data = ROUTE_HANDLERS['dashboard_get']()
    return render_template('dashboard.html', **data)

@app.route('/control', methods=['GET', 'POST'])
def control():
    """Страница управления сервисом"""
    if request.method == 'POST':
        data = ROUTE_HANDLERS['control_post']()
    else:
        data = {'status': ROUTE_HANDLERS['dashboard_get']()['status'], 'logs': '', 'message': ''}
    
    return render_template('control.html', **data)

@app.route('/signals')
def signals():
    """Страница истории сигналов"""
    data = ROUTE_HANDLERS['signals_get']()
    return render_template('signals.html', **data)

# ===== API МАРШРУТЫ =====

@app.route('/signals_data')
def signals_data():
    """API: Получение данных сигналов (AJAX)"""
    return ROUTE_HANDLERS['signals_data']()

@app.route('/save_columns_config', methods=['POST'])
def save_columns_config():
    """API: Сохранение конфигурации колонок"""
    return ROUTE_HANDLERS['save_columns_config']()

@app.route('/reset_columns', methods=['POST'])
def reset_columns():
    """API: Сброс конфигурации колонок"""
    return ROUTE_HANDLERS['reset_columns']()

@app.route('/get_columns_config')
def get_columns_config():
    """API: Получение конфигурации колонок"""
    return ROUTE_HANDLERS['get_columns_config']()

@app.route('/export_excel')
def export_excel():
    """API: Экспорт данных в Excel"""
    return ROUTE_HANDLERS['export_excel']()

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
    from ui.auth import auth_manager
    
    print("🚀 Запуск Trading Bot UI...")
    print(f"👤 Пользователь: {auth_manager.username}")
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://localhost:8888")
    
    app.run(host='0.0.0.0', port=8888, debug=True)