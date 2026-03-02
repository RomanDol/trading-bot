# 🤖 Binance Futures Trading Bot

A production-ready automated trading system that receives webhook signals (e.g. from TradingView), validates and executes orders on Binance Futures, and monitors positions in real time via WebSocket.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)
![Binance](https://img.shields.io/badge/Binance-Futures_API-F0B90B?logo=binance)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📐 Architecture

```
TradingView Alert
      │
      ▼ POST /webhook
┌─────────────────┐       ┌──────────────────┐
│   Flask Backend │──────▶│  Binance Futures  │
│   (Gunicorn)    │◀──────│       API         │
└────────┬────────┘       └──────────────────┘
         │  write                  ▲
         ▼                         │ WebSocket stream
┌─────────────────┐       ┌──────────────────┐
│   PostgreSQL    │◀──────│ WebSocket Monitor │
│   (messages,    │       │ (order updates,   │
│  order_history) │       │  account events)  │
└────────┬────────┘       └──────────────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│  Flask Frontend │       │     Grafana       │
│   (Bot UI)      │       │   (Prometheus +   │
│   port 8888     │       │  node-exporter)   │
└─────────────────┘       └──────────────────┘
```

---

## ✨ Features

- **Webhook signal processing** — receives and validates JSON signals from TradingView or any HTTP client
- **Hedge mode support** — works with Binance `dualSidePosition` (LONG/SHORT independent positions)
- **Automatic quantity adjustment** — rounds order size to Binance `stepSize` per symbol
- **Real-time WebSocket monitoring** — tracks order fills and account updates via Binance User Data Stream
- **Deduplication** — MD5-based message deduplication prevents double-processing of WebSocket events
- **Auto-recovery** — if WebSocket goes silent for 5+ minutes, the bot polls `allOrders` REST API to fill the gap
- **PostgreSQL logging** — all strategy signals and Binance API responses stored in a single `all_messages` table (JSONB)
- **Order history restore** — restore historical orders from Binance API for any date range
- **Web UI** — Flask-based control panel for service management, log viewing, and trading tools
- **Monitoring** — Prometheus + Grafana + node-exporter + postgres-exporter via Docker Compose
- **Basic Auth** — all endpoints (except `/webhook`) are protected with HTTP Basic Authentication

---

## 🗂️ Project Structure

```
trading-bot/
├── backend/
│   ├── app.py                   # Flask application & routes
│   ├── requirements.txt
│   └── core/
│       ├── binance_client.py    # Binance Futures API client + WebSocket init
│       ├── binance_symbols.py   # Sync exchange symbols to PostgreSQL
│       ├── messages_database.py # PostgreSQL manager for all_messages table
│       ├── order_restore.py     # Restore order history from Binance REST API
│       ├── webhook_handler.py   # Validate & execute incoming signals
│       └── websocket_monitor.py # Binance User Data Stream listener
├── frontend/
│   ├── bot_ui.py                # Flask UI application
│   ├── templates/               # Jinja2 HTML templates
│   ├── static/
│   │   ├── css/                 # Modular CSS (variables, layout, components)
│   │   └── js/                  # Page-specific JavaScript
│   └── ui/
│       ├── auth.py              # Basic Auth middleware
│       └── routes.py            # Route handlers (systemd control, logs)
├── monitoring/
│   ├── docker-compose.yml       # Prometheus + Grafana + exporters
│   └── prometheus.yml
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Binance Futures account with API key (Futures permissions required)
- `systemd` (for service management via UI) or manual process management

### 1. Clone & install

```bash
git clone https://github.com/your_username/trading-bot.git
cd trading-bot

python3 -m venv venv
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in all required variables (see [Environment Variables](#environment-variables)).

### 3. Initialize the database

The app creates tables automatically on first run. Make sure your PostgreSQL instance is running and the credentials in `.env` are correct.

Required tables (created automatically):
- `all_messages` — all signals and WebSocket events
- `order_history` — restored Binance order history
- `binance_symbols` — exchange symbol metadata

### 4. Run the backend

```bash
cd backend
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

> ⚠️ Use `workers=1` — the WebSocket monitor is a singleton and must not be duplicated across workers.

### 5. Run the frontend UI

```bash
cd frontend
python bot_ui.py
# or
gunicorn -w 1 -b 0.0.0.0:8888 bot_ui:app
```

### 6. Start monitoring stack (optional)

```bash
cd monitoring
docker compose up -d
```

Grafana will be available at `http://localhost:3000`.

---

## 🔗 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/webhook` | ❌ | Receive trading signal |
| `POST` | `/api/restore_orders` | ✅ | Restore order history from Binance |
| `POST` | `/api/update_symbols` | ✅ | Sync Binance symbol list to DB |

### Webhook payload

```json
{
  "auth_key": "your_signal_key",
  "action": "ENTER_LONG",
  "symbol": "BTCUSDT",
  "quantity": "0.01",
  "strategy": "my_strategy",
  "strId": "abc123456"
}
```

**Supported actions:** `ENTER_LONG`, `EXIT_LONG`, `ENTER_SHORT`, `EXIT_SHORT`

**`strId` logic:**
- `ENTER_*` — signal is ignored if an open order with this ID already exists
- `EXIT_*` — signal is ignored if no matching order is found in the database

---

## ⚙️ Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Webhook authentication
SIGNAL_KEY=your_secret_signal_key

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=messages
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password

# Web UI credentials
UI_USERNAME=admin
UI_PASSWORD=your_ui_password

# UI configuration
SERVER_HOST=localhost
SERVER_NAME=MyBot
GRAFANA_URL=http://localhost:3000
```

---

## 🔒 Security Notes

- The `/webhook` endpoint is intentionally left without HTTP Basic Auth — TradingView does not support it. Authentication is handled via `auth_key` in the payload.
- All other API endpoints require HTTP Basic Auth.
- Never commit your `.env` file. It is listed in `.gitignore`.

---

## 🛠️ Technical Highlights

### WebSocket deduplication
Binance User Data Stream can occasionally deliver duplicate messages. Each incoming message is hashed with MD5 and checked against an in-memory cache (capped at 1000 entries) before processing.

### Auto-recovery
A dedicated `_monitor_ping` thread checks that the WebSocket receives pings at least every 5 minutes. If the connection goes silent, the recovery loop starts polling `GET /fapi/v1/allOrders` every minute and writes results to `order_history`, ensuring no fills are missed.

### Hedge mode
All orders are placed with explicit `positionSide` (`LONG` or `SHORT`), compatible with Binance Hedge Mode (`dualSidePosition=true`).

### stepSize precision
On startup, the client fetches `exchangeInfo` once and caches `LOT_SIZE.stepSize` for every symbol. Quantities are rounded to the correct decimal precision before every order.

---

## 📊 Database Schema

### `all_messages`
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `time` | TIMESTAMPTZ | Record timestamp |
| `type` | VARCHAR | Event type (`STRATEGY_SIGNAL`, `ORDER_TRADE_UPDATE`, etc.) |
| `message` | JSONB | Full event payload |

### `order_history`
| Column | Type | Description |
|--------|------|-------------|
| `orderid` | BIGINT | Binance order ID |
| `symbol` | VARCHAR | Trading pair |
| `side` | VARCHAR | `BUY` / `SELL` |
| `positionside` | VARCHAR | `LONG` / `SHORT` |
| `status` | VARCHAR | Order status |
| `executedqty` | DECIMAL | Filled quantity |
| `avgprice` | DECIMAL | Average fill price |
| `updatetime` | TIMESTAMP | Last update time |
| `raw_msg` | TEXT | Full JSON from Binance |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Python, Flask, Gunicorn |
| Trading | binance-futures-connector, websocket-client |
| Database | PostgreSQL, psycopg2 |
| Frontend | Flask, Jinja2, vanilla JS/CSS |
| Monitoring | Prometheus, Grafana, node-exporter |
| Infrastructure | systemd, Docker Compose |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.