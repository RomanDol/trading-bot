// ===== МОДУЛЬ ТАБЛИЦЫ И ЗАГРУЗКИ ДАННЫХ СООБЩЕНИЙ =====

window.MessagesTable = (function() {
    const { DOM, API, DateUtils, Notifications } = window.TradingBotUI;
    
    async function fetchMessages() {
        try {
            // показываем загрузку только при ручных запросах
            if (!window.isAutoRefreshing) {
                window.MessagesPagination.setPaginationLoading(true);
            }

            const paginationState = window.MessagesPagination.getState();
            const params = new URLSearchParams(window.location.search);
            params.set('limit', paginationState.limit);
            params.set('page', paginationState.currentPage);

            const data = await API.get("/messages/data?" + params.toString());
            if (data.error) {
                console.error('API Error:', data.error);
                Notifications.error('Ошибка загрузки данных сообщений');
                return;
            }

            // ВСЕГДА обновляем параметры пагинации
            window.MessagesPagination.updatePaginationState(data);

            // Анализируем JSON поля в сообщениях для динамических колонок
            window.MessagesJSON.analyzeAndCreateJsonColumns(data);
            
            const tableBody = DOM.get("message-body");
            tableBody.innerHTML = "";

            data.rows.forEach(row => {
                const tr = DOM.create('tr');
                const columnsConfig = window.MessagesColumns.getConfig();
                const sortedColumns = Object.entries(columnsConfig)
                    .sort((a, b) => a[1].order - b[1].order);

                sortedColumns.forEach(([columnKey, config]) => {
                    const td = DOM.create('td');
                    td.setAttribute('data-column', columnKey);
                    formatCell(td, getCellValue(row, columnKey, data), columnKey);
                    tr.appendChild(td);
                });

                tableBody.appendChild(tr);
            });

            window.MessagesColumns.applyColumnVisibility();
            window.MessagesPagination.updatePaginationUI();
            
        } catch (error) {
            console.error("Failed to fetch messages:", error);
            Notifications.error("Ошибка загрузки данных сообщений");
        } finally {
            if (!window.isAutoRefreshing) {
                window.MessagesPagination.setPaginationLoading(false);
            }
        }
    }
    
    function getCellValue(row, columnKey, data) {
        if (columnKey.startsWith('json_')) {
            // Динамические JSON поля из message колонки
            const messageIndex = data.column_map['message'];
            return window.MessagesJSON.getJsonValue(row, columnKey, messageIndex);
        } else {
            // Обычные колонки из базы данных
            const columnIndex = data.column_map[columnKey];
            return columnIndex !== undefined ? row[columnIndex] : '';
        }
    }
    
    function formatCell(td, cellValue, columnKey) {
        if (columnKey === 'time') {
            // Форматируем время - PostgreSQL возвращает ISO строку
            td.textContent = DateUtils.format(cellValue);
            
        } else if (columnKey === 'type') {
            // Форматируем тип сообщения с цветовой индикацией
            td.textContent = cellValue || '';
            
            // Добавляем CSS классы для стилизации разных типов
            if (cellValue) {
                const typeClass = getTypeClass(cellValue);
                td.className = typeClass;
            }
            
        } else if (columnKey === 'message') {
            // Форматируем JSON сообщение
            formatMessageCell(td, cellValue);
            
        } else if (columnKey.startsWith('json_')) {
            // Динамические JSON поля
            window.MessagesJSON.formatJsonCell(td, cellValue);
            
        } else {
            // Обычные поля
            td.textContent = cellValue || '';
        }
    }
    
    function getTypeClass(messageType) {
        /**
         * Возвращает CSS класс для типа сообщения
         */
        if (messageType.includes('STRATEGY')) {
            return 'type-strategy';
        } else if (messageType.includes('BINANCE')) {
            return 'type-binance';
        } else if (messageType.includes('ORDER_TRADE_UPDATE') || messageType.includes('ACCOUNT_UPDATE')) {
            return 'type-websocket';
        } else {
            return 'type-unknown';
        }
    }
    
    function formatMessageCell(td, cellValue) {
        /**
         * Специальное форматирование для колонки message (JSON)
         */
        if (cellValue) {
            try {
                // Пытаемся распарсить JSON
                const jsonData = JSON.parse(cellValue);
                
                // Создаем красиво отформатированный JSON
                const formattedJson = JSON.stringify(jsonData, null, 2);
                
                // Создаем контейнер для JSON
                const jsonContainer = DOM.create('div', 'json-message');
                jsonContainer.textContent = formattedJson;
                
                // Добавляем tooltip с полным содержимым
                td.title = formattedJson;
                td.appendChild(jsonContainer);
                
                // Если JSON слишком длинный, сокращаем отображение
                if (formattedJson.length > 500) {
                    const shortJson = formattedJson.substring(0, 500) + '...';
                    jsonContainer.textContent = shortJson;
                }
                
            } catch (e) {
                // Если не JSON, показываем как обычный текст
                td.textContent = cellValue.substring(0, 200) + (cellValue.length > 200 ? '...' : '');
                td.title = cellValue;
            }
        } else {
            td.textContent = '';
        }
    }
    
    function highlightJsonField(jsonString, fieldName) {
        /**
         * Подсвечивает определенное поле в JSON строке (для будущего использования)
         */
        try {
            const jsonData = JSON.parse(jsonString);
            if (jsonData[fieldName] !== undefined) {
                const regex = new RegExp(`"${fieldName}"\\s*:\\s*"?([^",}]+)"?`, 'gi');
                return jsonString.replace(regex, `<mark>"${fieldName}": "$1"</mark>`);
            }
        } catch (e) {
            // Игнорируем ошибки парсинга
        }
        return jsonString;
    }
    
    function getMessageTypeIcon(messageType) {
        /**
         * Возвращает иконку для типа сообщения
         */
        const typeIcons = {
            'STRATEGY_SIGNAL': '🎯',
            'BINANCE_API': '💱',
            'ORDER_TRADE_UPDATE': '📊',
            'ACCOUNT_UPDATE': '💰',
            'listenKeyExpired': '🔑'
        };
        
        return typeIcons[messageType] || '📨';
    }
    
    function addMessageTypeIcon(td, messageType) {
        /**
         * Добавляет иконку к типу сообщения
         */
        const icon = getMessageTypeIcon(messageType);
        const currentText = td.textContent;
        td.innerHTML = `${icon} ${currentText}`;
    }
    
    // Публичный API модуля
    return {
        fetchMessages,
        getCellValue,
        formatCell,
        formatMessageCell,
        getTypeClass,
        getMessageTypeIcon
    };
})();