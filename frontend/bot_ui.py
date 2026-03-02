import sys

from flask import Flask, render_template, request, jsonify
from ui.auth import auth_manager
from ui.routes import route_handlers
import os
from dotenv import load_dotenv
import socket 

load_dotenv()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False



@app.before_request
def auth_middleware():
    
    if request.path.startswith('/api/'):
        return None
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
    

@app.route('/api/update_symbols', methods=['POST'])
def update_symbols_proxy():
    try:
        import requests
        
        auth = request.authorization
        
        response = requests.post(
            'http://localhost:5000/api/update_symbols',
            timeout=30,
            auth=(auth.username, auth.password)
        )
        
        return response.json(), response.status_code
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@app.context_processor
def inject_globals():
    return {
        'status': route_handlers.get_status(),
        'server_host': os.getenv('SERVER_HOST', 'localhost'),
        'grafana_url': os.getenv('GRAFANA_URL', '/grafana/'),
        'server_name': os.getenv('SERVER_NAME')
    }
        
if __name__ == '__main__':
    print("🚀 Запуск Trading Bot UI...")
    print(f"👤 Пользователь: {auth_manager.username}")  
    print(f"🔐 Пароль: {'*' * len(auth_manager.password)}")
    print(f"🌐 Адрес: http://49.12.233.74:8888")
   
    
    app.run(host='0.0.0.0', port=8888, debug=True)

