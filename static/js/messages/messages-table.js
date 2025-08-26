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
        } else if (messageType.includes('ORDER_TRADE_UPDATE')) {
            return 'type-order_upd';
        } else if (messageType.includes('ACCOUNT_UPDATE')) {
            return 'type-account_upd';
        } else if (messageType.includes('TRADE_LITE')) {
            return 'type-trade_lt';
      //   } else if (messageType.includes('ORDER_TRADE_UPDATE') || messageType.includes('ACCOUNT_UPDATE')) {
      //       return 'type-websocket';
        } else {
            return 'type-unknown';
        }
    }
    
   function formatMessageCell(td, cellValue) {
      // Сохраняем оригинальное значение для переключения режимов
      td.setAttribute('data-original-value', cellValue);
      
      if (cellValue) {
         try {
               const jsonData = JSON.parse(cellValue);
               const jsonContainer = DOM.create('div', 'json-message');
               
               let formattedContent;
               
               if (messageDisplayMode === 'column') {
                  // Режим столбца - используем JSON.stringify с отступами для ВСЕХ уровней
                  formattedContent = JSON.stringify(jsonData, null, 2);
                  // Убираем ТОЛЬКО внешние фигурные скобки
                  formattedContent = formattedContent.replace(/^\{\s*/, '').replace(/\s*\}$/, '');
                  
                  jsonContainer.style.whiteSpace = 'pre-wrap';
                  jsonContainer.style.width = 'max-content';
               } else {
                  // Режим строки - все в одну строку БЕЗ внешних скобок
                  const entries = Object.entries(jsonData);
                  formattedContent = entries
                     .map(([key, value]) => `"${key}": ${JSON.stringify(value)}`)
                     .join(', ');
                  
                  jsonContainer.style.whiteSpace = 'nowrap';
                  jsonContainer.style.width = 'max-content';
               }
               
               jsonContainer.textContent = formattedContent;
               // Добавляем tooltip только в режиме строки
               if (messageDisplayMode === 'inline') {
                  td.title = JSON.stringify(jsonData, null, 2);
               } else {
                  td.title = ''; // Убираем tooltip в режиме колонок
               }
               
               // Очищаем и добавляем контейнер
               td.innerHTML = '';
               td.appendChild(jsonContainer);
            
               
         } catch (e) {
               td.textContent = cellValue.substring(0, 200) + (cellValue.length > 200 ? '...' : '');
               if (messageDisplayMode === 'inline') {
                  td.title = cellValue;
               } else {
                  td.title = '';
               }
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
   
   // Переменная для отслеживания режима отображения
   let messageDisplayMode = 'inline'; // 'inline' или 'column'

   function toggleMessageFormat() {
      messageDisplayMode = messageDisplayMode === 'inline' ? 'column' : 'inline';
      
      // Обновляем все ячейки message
      const messageCells = document.querySelectorAll('td[data-column="message"]');
      messageCells.forEach(cell => {
         const cellValue = cell.getAttribute('data-original-value');
         if (cellValue) {
               formatMessageCell(cell, cellValue);
         }
      });
      
      // НОВЫЙ ПОДХОД - пересоздание контейнера
      const container = document.querySelector('.messages-table-container');
      const parent = container.parentElement;
      const table = container.querySelector('table');
      
      // Удаляем контейнер из DOM
      parent.removeChild(container);
      
      // Создаем новый контейнер
      const newContainer = document.createElement('div');
      newContainer.className = 'scroll-table messages-table-container';
      newContainer.appendChild(table);
      
      // Вставляем обратно
      parent.appendChild(newContainer);
      
      // Обновляем иконку кнопки
      const toggleBtn = document.getElementById('toggle-message-format-btn');
      if (toggleBtn) {
         toggleBtn.textContent = messageDisplayMode === 'inline' ? '↕️' : '↔️';
      }
   }

    
    // Публичный API модуля
    return {
        fetchMessages,
        getCellValue,
        formatCell,
        formatMessageCell,
        getTypeClass,
        getMessageTypeIcon,
        toggleMessageFormat
        
    };
})();