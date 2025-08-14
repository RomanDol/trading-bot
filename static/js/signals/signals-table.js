// ===== МОДУЛЬ ТАБЛИЦЫ И ЗАГРУЗКИ ДАННЫХ =====

window.SignalsTable = (function() {
    const { DOM, API, DateUtils, Notifications } = window.TradingBotUI;
    
    async function fetchSignals() {
        try {
            // показываем загрузку только при ручных запросах
            if (!window.isAutoRefreshing) {
                window.SignalsPagination.setPaginationLoading(true);
            }

            const paginationState = window.SignalsPagination.getState();
            const params = new URLSearchParams(window.location.search);
            params.set('limit', paginationState.limit);
            params.set('page', paginationState.currentPage);

            const data = await API.get("/signals_data?" + params.toString());
            if (data.error) {
                console.error('API Error:', data.error);
                Notifications.error('Ошибка загрузки данных');
                return;
            }

            // ВСЕГДА обновляем параметры пагинации
            window.SignalsPagination.updatePaginationState(data);

            window.SignalsJSON.analyzeAndCreateJsonColumns(data);
            const tableBody = DOM.get("signal-body");
            tableBody.innerHTML = "";

            data.rows.forEach(row => {
                const tr = DOM.create('tr');
                const columnsConfig = window.SignalsColumns.getConfig();
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

            window.SignalsColumns.applyColumnVisibility();
            window.SignalsPagination.updatePaginationUI();
        } catch (error) {
            console.error("Failed to fetch signals:", error);
            Notifications.error("Ошибка загрузки данных сигналов");
        } finally {
            if (!window.isAutoRefreshing) {
                window.SignalsPagination.setPaginationLoading(false);
            }
        }
    }
    
    function getCellValue(row, columnKey, data) {
        if (columnKey.startsWith('json_')) {
            const extraDataIndex = data.column_map['extra_data'];
            return window.SignalsJSON.getJsonValue(row, columnKey, extraDataIndex);
        } else {
            const columnIndex = data.column_map[columnKey];
            return columnIndex !== undefined ? row[columnIndex] : '';
        }
    }
    
    function formatCell(td, cellValue, columnKey) {
        if (columnKey === 'timestamp') {
            td.textContent = DateUtils.format(cellValue);
        } else if (columnKey === 'result') {
            td.textContent = cellValue === "success" ? "✅ success" : "❌ error";
            td.className = cellValue === "success" ? "status-success" : "status-error";
        } else if (columnKey === 'extra_data') {
            window.SignalsJSON.formatExtraDataCell(td, cellValue);
        } else if (columnKey.startsWith('json_')) {
            window.SignalsJSON.formatJsonCell(td, cellValue);
        } else {
            td.textContent = cellValue || '';
        }
    }
    
    // Публичный API модуля
    return {
        fetchSignals,
        getCellValue,
        formatCell
    };
})();