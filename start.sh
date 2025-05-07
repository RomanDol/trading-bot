#!/bin/bash

echo "🚀 Starting trading-bot Flask app with Gunicorn ..."

# Активируем виртуальное окружение с абсолютным путем
source /root/trading-bot/venv/bin/activate

# Запускаем Gunicorn
/root/trading-bot/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 app:app \
  --log-level info --access-logfile /root/trading-bot/logs/access.log
  --error-logfile /root/trading-bot/logs/error.log
