#!/bin/bash

echo "🚀 Starting trading-bot Flask app with Gunicorn ..."

# Активируем виртуальное окружение
source /home/trader/trading-bot/venv/bin/activate

# Запускаем Gunicorn с логами
/home/trader/trading-bot/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 app:app \
  --reload \
  --log-level info \
  --access-logfile /home/trader/trading-bot/logs/access.log \
  --error-logfile /home/trader/trading-bot/logs/error.log
