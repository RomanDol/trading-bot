#!/bin/bash

echo "🔧 БЕЗОПАСНОЕ разделение Trading Bot по папкам..."
echo "📍 Текущая директория: /root/trading-bot"

# ===== СОЗДАЕМ BACKUP =====
echo "💾 Создаем backup..."
systemctl stop trading-bot
systemctl stop trading-bot-ui
git add .
git commit -m "Backup before safe restructure" || echo "Nothing to commit"

# ===== СОЗДАЕМ СТРУКТУРУ ПАПОК =====
echo "📁 Создаем структуру папок..."
mkdir -p backend
mkdir -p frontend

# ===== КОПИРУЕМ (НЕ ПЕРЕМЕЩАЕМ!) BACKEND =====
echo "🔧 Копируем backend файлы..."
cp app.py backend/
cp -r core backend/
cp .env backend/
cp requirements.txt backend/
cp start.sh backend/
cp -r logs backend/ 2>/dev/null || mkdir -p backend/logs

# Создаем отдельное виртуальное окружение для backend
echo "🐍 Создаем venv для backend..."
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
deactivate

# ===== КОПИРУЕМ FRONTEND =====  
echo "🎨 Копируем frontend файлы..."
cp bot_ui.py frontend/
cp -r ui frontend/
cp -r templates frontend/
cp -r static frontend/
cp .env frontend/  # UI тоже может нужны переменные среды

# Создаем venv для frontend  
echo "🎨 Создаем venv для frontend..."
python3 -m venv frontend/venv
source frontend/venv/bin/activate
pip install Flask python-dotenv requests
deactivate

# ===== ОБНОВЛЯЕМ SYSTEMD СЕРВИСЫ =====
echo "⚙️ Обновляем systemd сервисы..."

# Обновляем trading-bot.service для backend
sudo tee /etc/systemd/system/trading-bot.service << 'EOF'
[Unit]
Description=Trading Bot Webhook Server (Backend)
After=network.target

[Service]
User=root
WorkingDirectory=/root/trading-bot/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/root/trading-bot/backend/venv/bin/gunicorn --workers 1 --bind 0.0.0.0:5000 app:app --log-level info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Создаем новый frontend start скрипт
cat > frontend/start_frontend.sh << 'EOF'
#!/bin/bash
cd /root/trading-bot/frontend
source venv/bin/activate
export PYTHONPATH="/root/trading-bot:$PYTHONPATH"
python3 bot_ui.py
EOF
chmod +x frontend/start_frontend.sh

# Обновляем trading-bot-ui.service для frontend
sudo tee /etc/systemd/system/trading-bot-ui.service << 'EOF'
[Unit]
Description=Trading Bot UI (Frontend)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/trading-bot/frontend
Environment=PYTHONPATH=/root/trading-bot
ExecStart=/root/trading-bot/frontend/start_frontend.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем конфигурацию systemd
sudo systemctl daemon-reload

echo ""
echo "✅ БЕЗОПАСНОЕ разделение завершено!"
echo ""
echo "📁 Новая структура:"
echo "   /root/trading-bot/backend/  - app.py + core/"
echo "   /root/trading-bot/frontend/ - bot_ui.py + ui/ + templates/ + static/"
echo "   /root/trading-bot/          - оригинальные файлы сохранены"
echo ""
echo "🎯 Тестирование:"
echo "   systemctl start trading-bot     # Backend на :5000"
echo "   systemctl start trading-bot-ui  # Frontend на :8888"
echo ""
echo "⚠️ ВАЖНО: Если что-то сломается, оригинальные файлы остались в корне!"