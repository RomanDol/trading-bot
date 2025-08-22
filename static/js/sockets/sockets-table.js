// ===== МОДУЛЬ ТАБЛИЦЫ И ЗАГРУЗКИ ДАННЫХ СОКЕТОВ =====

window.SocketsTable = (function() {
    const { DOM, API, DateUtils, Notifications } = window.TradingBotUI;
    
    async function fetchSockets() {
        try {
            // показываем загрузку только при ручных запросах
            if (!window.isAutoRefreshing) {
                window.SocketsPagination.setPaginationLoading(true);
            }

            const paginationState = window.SocketsPagination.getState();
            const params = new URLSearchParams(window.location.search);
            params.set('limit', paginationState.limit);
            params.set('page', paginationState.currentPage);

            const data = await API.get("/sockets/data?" + params.toString());
            if (data.error) {
                console.error('API Error:', data.error);
                Notifications.error('Ошибка загрузки данных сокетов');
                return;
            }

            // ВСЕГДА обновляем параметры пагинации
            window.SocketsPagination.updatePaginationState(data);

            window.SocketsJSON.analyzeAndCreateJsonColumns(data);
            const tableBody = DOM.get("socket-body");
            tableBody.innerHTML = "";

            data.rows.forEach(row => {
                const tr = DOM.create('tr');
                const columnsConfig = window.SocketsColumns.getConfig();
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

            window.SocketsColumns.applyColumnVisibility();
            window.SocketsPagination.updatePaginationUI();
        } catch (error) {
            console.error("Failed to fetch sockets:", error);
            Notifications.error("Ошибка загрузки данных сокетов");
        } finally {
            if (!window.isAutoRefreshing) {
                window.SocketsPagination.setPaginationLoading(false);
            }
        }
    }
    
    function getCellValue(row, columnKey, data) {
        if (columnKey.startsWith('socket_')) {
            const rawMessageIndex = data.column_map['raw_message'];
            return window.SocketsJSON.getJsonValue(row, columnKey, rawMessageIndex);
        } else {
            const columnIndex = data.column_map[columnKey];
            return columnIndex !== undefined ? row[columnIndex] : '';
        }
    }
    
    function formatCell(td, cellValue, columnKey) {
        if (columnKey === 'timestamp') {
            // Используем DateUtils.format который правильно обрабатывает UTC -> локальное время
            td.textContent = DateUtils.format(cellValue);
        } else if (columnKey === 'status') {
            td.textContent = cellValue || '';
            // Добавляем классы для стилизации статусов
            if (cellValue) {
                const statusClass = `status-${cellValue.toLowerCase().replace('_', '-')}`;
                td.className = statusClass;
            }
        } else if (columnKey === 'raw_message') {
            window.SocketsJSON.formatRawMessageCell(td, cellValue);
        } else if (columnKey.startsWith('socket_')) {
            window.SocketsJSON.formatJsonCell(td, cellValue);
        } else {
            td.textContent = cellValue || '';
        }
    }
    
    // Публичный API модуля
    return {
        fetchSockets,
        getCellValue,
        formatCell
    };
})();