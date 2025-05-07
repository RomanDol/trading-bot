# Trading Bot Webhook Server

Flask-приложение для приёма webhook-сигналов (например, от TradingView) и исполнения ордеров на Binance Futures через API.

## 📦 Возможности

- Поддержка LONG/SHORT ордеров
- Работа в Hedge режиме (dualSidePosition)
- Автоматическая подгонка количества под тикер Binance
- Логирование сигналов в SQLite-базу
- Запуск через systemd + Gunicorn
- Простая web-интерфейс-таблица (bot_ui.py)

## 🚀 Установка

```bash
git clone https://github.com/your_username/trading-bot.git
cd trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
