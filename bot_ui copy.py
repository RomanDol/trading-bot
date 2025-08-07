from flask import Flask, render_template, request, Response, jsonify
import subprocess
import sqlite3
import os
from dotenv import load_dotenv
import pytz
from datetime import datetime

load_dotenv()

app = Flask(__name__)
SERVICE_NAME = "trading-bot"
DB_FILE = "signals.db"

def get_status():
    result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], stdout=subprocess.PIPE, text=True)
    return result.stdout.strip()

def get_logs():
    return subprocess.getoutput(f"journalctl -u {SERVICE_NAME}.service -n 30 --no-pager")

# 🏠 Main dashboard page
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# 🎛️ Control panel page
@app.route('/control', methods=['GET', 'POST'])
def control():
    logs = ''
    if request.method == 'POST':
        action = request.form['action']
        if action in ['start', 'stop', 'restart']:
            subprocess.run(["systemctl", action, SERVICE_NAME])
        elif action == 'logs':
            logs = get_logs()
    
    return render_template('control.html', status=get_status(), logs=logs)

# 📊 Signals history page
@app.route('/signals')
def signals():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    action_filter = request.args.get('action')
    symbol_filter = request.args.get('symbol')
    result_filter = request.args.get('result')
    strategy_filter = request.args.get('strategy')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT id, timestamp, action, symbol, quantity, result, strategy, message FROM signals"
    conditions = []
    params = []
    
    if from_date:
        conditions.append("DATE(timestamp) >= DATE(?)")
        params.append(from_date)
    if to_date:
        conditions.append("DATE(timestamp) <= DATE(?)")
        params.append(to_date)
    if strategy_filter:
        conditions.append("strategy = ?")
        params.append(strategy_filter)
    if action_filter:
        conditions.append("action = ?")
        params.append(action_filter)
    if symbol_filter:
        conditions.append("symbol = ?")
        params.append(symbol_filter)
    if result_filter:
        conditions.append("result = ?")
        params.append(result_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT 200"

    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    conn.close()

    parsed_rows = []
    utc = pytz.utc
    london = pytz.timezone("Europe/London")

    for row in raw_rows:
        try:
            naive_dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
            utc_dt = utc.localize(naive_dt)
            local_dt = utc_dt.astimezone(london)
            local_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print("[Timezone ERROR]", e)
            local_time = row[1]

        parts = row[7].split(",", maxsplit=25)
        parsed_rows.append([row[0], local_time, row[2], row[3], row[4], row[5], row[6], *parts])

    return render_template('signals.html', 
        rows=parsed_rows,
        from_date_filter=from_date or '', 
        to_date_filter=to_date or '',
        action_filter=action_filter or '', 
        symbol_filter=symbol_filter or '',
        result_filter=result_filter or '', 
        strategy_filter=strategy_filter or ''
    )

# 📊 API endpoint for live signals data
@app.route('/signals_data')
def signals_data():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    action_filter = request.args.get('action')
    symbol_filter = request.args.get('symbol')
    result_filter = request.args.get('result')
    strategy_filter = request.args.get('strategy')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT id, timestamp, action, symbol, quantity, result, strategy, message FROM signals"
    conditions = []
    params = []
    
    if from_date:
        conditions.append("DATE(timestamp) >= DATE(?)")
        params.append(from_date)
    if to_date:
        conditions.append("DATE(timestamp) <= DATE(?)")
        params.append(to_date)
    if strategy_filter:
        conditions.append("strategy = ?")
        params.append(strategy_filter)
    if action_filter:
        conditions.append("action = ?")
        params.append(action_filter)
    if symbol_filter:
        conditions.append("symbol = ?")
        params.append(symbol_filter)
    if result_filter:
        conditions.append("result = ?")
        params.append(result_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT 200"

    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    conn.close()

    parsed = []
    utc = pytz.utc
    london = pytz.timezone("Europe/London")

    for row in raw_rows:
        try:
            naive_dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
            utc_dt = utc.localize(naive_dt)
            local_dt = utc_dt.astimezone(london)
            local_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            local_time = row[1]

        parts = row[7].split(",", maxsplit=25)
        parsed.append([row[0], local_time, row[2], row[3], row[4], row[5], row[6], *parts])

    return jsonify(parsed)

# 🔐 Authentication
USERNAME = os.getenv('UI_USERNAME')
PASSWORD = os.getenv('UI_PASSWORD')

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.before_request
def require_auth():
    if request.path.startswith('/static/'):
        return
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)