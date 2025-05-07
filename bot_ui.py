
from flask import Flask, render_template_string, request, redirect, url_for, Response, jsonify
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

UI_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>Trading Bot UI</title></head>
<body style="background:#111;color:white;font-family:sans-serif;text-align:center;padding:40px;">
    <h1>🚀 Trading Bot Control Panel</h1>
    <p>Service status: <b style="color:{{ 'lime' if status == 'active' else 'red' }}">{{ status }}</b></p>
    <form method="post" style="margin-bottom:20px;">
        <button name="action" value="start">▶️ Start</button>
        <button name="action" value="stop">⏹ Stop</button>
        <button name="action" value="restart">🔁 Restart</button>
        <button name="action" value="logs">📄 Show Logs</button>
    </form>
    <a href="/signals" style="color:cyan;">📋 View Signal History</a>
    {% if logs %}
    <h3>📄 Last 30 Log Lines</h3>
    <pre style="text-align:left;background:#222;padding:20px;border-radius:8px;max-width:900px;margin:auto;overflow-x:auto;">{{ logs }}</pre>
    {% endif %}
</body></html>'''

TABLE_TEMPLATE = '''<!DOCTYPE html>
<html><head><title>Signal History</title>
<style>
body { background: #111; color: white; font-family: sans-serif; padding: 30px; }
h1 { text-align: center; }
.scroll-table { max-height: 70vh; overflow: auto; }
table { width: 100%; border-collapse: collapse; min-width: 1000px; font-size: 13px; }
th, td { padding: 6px; text-align: left; white-space: nowrap; }
th { background: #333; } tr:nth-child(even) { background: #222; } tr:nth-child(odd) { background: #1a1a1a; }
</style>
<script>
async function fetchSignals() {
    const params = new URLSearchParams(window.location.search);
    const res = await fetch("/signals_data?" + params.toString());
    const rows = await res.json();
    const tableBody = document.getElementById("signal-body");
    tableBody.innerHTML = "";
    rows.forEach((row) => {
        const tr = document.createElement("tr");
        row.forEach((cell, j) => {
            const td = document.createElement("td");

            if (j === 0) {
                // 👇 Преобразуем timestamp из UTC в локальное время
                const utcDate = new Date(cell + " UTC");
                td.textContent = utcDate.toLocaleString(); // можно указать локаль и формат
            } else if (j === 5) {
                td.textContent = cell === "success" ? "✅ success" : "❌ error";
                td.style.color = cell === "success" ? "lime" : "red";
            } else {
                td.textContent = cell;
            }

            tr.appendChild(td);
        });



        tableBody.appendChild(tr);
    });
}
setInterval(fetchSignals, 3000);
window.onload = fetchSignals;
</script>
</head>
<body>
<h1>📋 Signal History (Live)</h1>
<div class="scroll-table"><table>
<thead><tr>
<th>#</th><th>Time</th><th>Action</th><th>Symbol</th><th>Qty</th><th>Result</th><th>Strategy</th>
{% for i in range(1, 26) %}<th>Field {{ i }}</th>{% endfor %}
</tr></thead>
<tbody id="signal-body">
{% for row in rows %}
<tr>
  {% for cell in row %}
    <td style="color:{{ 'lime' if loop.index == 6 and cell == 'success' else ('red' if loop.index == 6 and cell == 'error' else '') }}">{{ cell }}</td>
  {% endfor %}
</tr>
{% endfor %}
</tbody>
</table></div>
<p style="text-align:center;margin-top:20px;">
<a href="/" style="color:cyan;">⬅ Back to Control Panel</a></p>
<form method="get" style="text-align:center;margin-bottom:20px;">
    <input name="strategy" placeholder="Strategy" value="{{ strategy_filter }}" style="width:120px;">
    <input name="action" placeholder="Action" value="{{ action_filter }}" style="width:120px;">
    <input name="symbol" placeholder="Symbol" value="{{ symbol_filter }}" style="width:120px;">
    <input name="result" placeholder="Result" value="{{ result_filter }}" style="width:120px;">
    <input name="from_date" type="date" value="{{ from_date_filter }}" style="width:140px;">
    <input name="to_date" type="date" value="{{ to_date_filter }}" style="width:140px;">
    <button type="submit">🔍 Filter</button>
    <a href="/signals" style="color:gray;margin-left:20px;">🧹 Reset</a>
</form>

</body></html>'''

def get_status():
    result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], stdout=subprocess.PIPE, text=True)
    return result.stdout.strip()

def get_logs():
    return subprocess.getoutput(f"journalctl -u {SERVICE_NAME}.service -n 30 --no-pager")

@app.route('/', methods=['GET', 'POST'])
def index():
    logs = ''
    if request.method == 'POST':
        action = request.form['action']
        if action in ['start', 'stop', 'restart']:
            subprocess.run(["systemctl", action, SERVICE_NAME])
        elif action == 'logs':
            logs = get_logs()
    return render_template_string(UI_TEMPLATE, status=get_status(), logs=logs)

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

    return render_template_string(TABLE_TEMPLATE, rows=parsed_rows,
    from_date_filter=from_date or '',
    to_date_filter=to_date or '',

    action_filter=action_filter or '',
    symbol_filter=symbol_filter or '',
    result_filter=result_filter or '',
    strategy_filter=strategy_filter or '')


from datetime import datetime, timedelta
import pytz

from datetime import datetime
import pytz

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
            utc_dt = utc.localize(naive_dt)               # мы точно говорим, что это UTC
            local_dt = utc_dt.astimezone(london)          # конвертируем в Лондон
            local_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[DEBUG] row timestamp: {row[1]} → {local_time} | strategy: {row[6]}")

        except Exception as e:
            local_time = row[1]

        parts = row[7].split(",", maxsplit=25)
        parsed.append([row[0], local_time, row[2], row[3], row[4], row[5], row[6], *parts])

    return jsonify(parsed)




USERNAME = os.getenv('UI_USERNAME', 'admin')
PASSWORD = os.getenv('UI_PASSWORD', '1234')

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
