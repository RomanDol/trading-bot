#!/bin/bash

echo "🧹 ПОЛНАЯ ОЧИСТКА Trading Bot от табличного фронтенда..."

# Создаем backup
echo "💾 Создаем backup..."
git add .
git commit -m "Backup before complete UI cleanup for PostgREST integration" || echo "Nothing to commit"

# ===== УДАЛЯЕМ TEMPLATE ФАЙЛЫ =====
echo "🗑️ Удаляем template файлы таблиц..."
rm -f templates/signals.html
rm -f templates/sockets.html 
rm -f templates/messages.html

# ===== УДАЛЯЕМ CSS ФАЙЛЫ ТАБЛИЦ =====
echo "🎨 Удаляем CSS файлы таблиц..."
rm -f static/css/pages/signals.css
rm -f static/css/pages/sockets.css
rm -f static/css/pages/messages.css

# ===== УДАЛЯЕМ JAVASCRIPT ФАЙЛЫ ТАБЛИЦ =====
echo "📜 Удаляем JavaScript файлы таблиц..."

# Signals JS
rm -rf static/js/signals/
rm -f static/js/signals/signals-columns.js
rm -f static/js/signals/signals-pagination.js
rm -f static/js/signals/signals-json.js
rm -f static/js/signals/signals-autorefresh.js
rm -f static/js/signals/signals-export.js
rm -f static/js/signals/signals-table.js
rm -f static/js/signals/signals-main.js

# Sockets JS
rm -rf static/js/sockets/
rm -f static/js/sockets/sockets-columns.js
rm -f static/js/sockets/sockets-pagination.js
rm -f static/js/sockets/sockets-json.js
rm -f static/js/sockets/sockets-autorefresh.js
rm -f static/js/sockets/sockets-export.js
rm -f static/js/sockets/sockets-table.js
rm -f static/js/sockets/sockets-main.js

# Messages JS
rm -rf static/js/messages/
rm -f static/js/messages/messages-columns.js
rm -f static/js/messages/messages-pagination.js
rm -f static/js/messages/messages-json.js
rm -f static/js/messages/messages-autorefresh.js
rm -f static/js/messages/messages-export.js
rm -f static/js/messages/messages-table.js
rm -f static/js/messages/messages-main.js

# ===== УДАЛЯЕМ UI МОДУЛИ ТАБЛИЦ =====
echo "🔧 Удаляем UI модули таблиц..."
rm -f ui/signals_handler.py
rm -f ui/sockets_handler.py
rm -f ui/messages_handler.py
rm -f ui/columns_config.py
rm -f ui/sockets_columns_config.py
rm -f ui/messages_columns_config.py
rm -f ui/routes_messages.py

# ===== УДАЛЯЕМ КОНФИГУРАЦИОННЫЕ ФАЙЛЫ =====
echo "⚙️ Удаляем конфигурационные файлы таблиц..."
rm -f columns_config.json
rm -f sockets_columns_config.json
rm -f messages_columns_config.json

# ===== УДАЛЯЕМ ЛИШНИЕ CSS (если есть) =====
echo "🎨 Удаляем лишние CSS компоненты таблиц..."
rm -f static/css/pages/universal-tables.css

echo ""
echo "✅ ВСЕ ТАБЛИЧНЫЕ ФАЙЛЫ УДАЛЕНЫ!"
echo ""
echo "📝 Теперь нужно заменить основные файлы:"
echo "   1. bot_ui.py"
echo "   2. templates/base.html"  
echo "   3. ui/routes.py"
echo "   4. ui/__init__.py"
echo ""
echo "🚀 После этого запускаем установку PostgREST"