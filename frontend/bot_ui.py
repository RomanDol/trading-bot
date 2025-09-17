import sys
# import os  # Удалить если не нужен getcwd()

from flask import Flask, render_template, request, jsonify
from ui.auth import auth_manager
from ui.routes import route_handlers

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.context_processor
def inject_globals():
    return {'status': route_handlers.get_status()}

@app.before_request
def auth_middleware():
    return auth_manager.require_auth()

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

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="Страница не найдена"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="Внутренняя ошибка сервера"), 500

@app.route('/order_history', endpoint='order_history')
def order_history():
    return render_template('order_history.html')

@app.route('/api/restore_orders', methods=['POST'])
def restore_orders_api():
    try:
        import requests
        
        data = request.get_json()
        auth = request.authorization
        
        response = requests.post(
            'http://localhost:5000/api/restore_orders', 
            json=data, 
            timeout=30,
            auth=(auth.username, auth.password)
        )
        
        return response.json(), response.status_code
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
        
if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI...")
    print(f"👤 Пользователь: {auth_manager.username}")  
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://49.12.233.74:8888")
    # Убрали print с os.getcwd()
    
    app.run(host='0.0.0.0', port=8888, debug=True)

