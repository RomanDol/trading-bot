#!/bin/bash

echo "🧹 Начинаем очистку Trading Bot от табличного фронтенда..."

# Создаем backup
echo "💾 Создаем backup..."
git add .
git commit -m "Backup before UI cleanup for PostgREST integration" || echo "Nothing to commit"

# Удаляем template файлы таблиц
echo "🗑️ Удаляем template файлы..."
rm -f templates/signals.html
rm -f templates/sockets.html 
rm -f templates/messages.html

# Удаляем CSS файлы таблиц
echo "🎨 Удаляем CSS файлы..."
rm -f static/css/pages/signals.css
rm -f static/css/pages/sockets.css
rm -f static/css/pages/messages.css

# Удаляем UI модули таблиц
echo "🔧 Удаляем UI модули..."
rm -f ui/signals_handler.py
rm -f ui/sockets_handler.py
rm -f ui/messages_handler.py
rm -f ui/columns_config.py
rm -f ui/sockets_columns_config.py
rm -f ui/messages_columns_config.py
rm -f ui/routes_messages.py

# Удаляем конфигурационные файлы
echo "⚙️ Удаляем конфигурационные файлы..."
rm -f columns_config.json
rm -f sockets_columns_config.json
rm -f messages_columns_config.json

echo "✅ Файлы удалены. Теперь нужно отредактировать код..."
echo "📝 Следующий шаг: отредактировать bot_ui.py, templates/base.html, ui/routes.py"