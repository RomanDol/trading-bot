// ===== JAVASCRIPT ДЛЯ SIGNALS PAGE =====

document.addEventListener('DOMContentLoaded', function() {
    const { DOM, API, DateUtils, Notifications } = window.TradingBotUI;
    
    // Глобальные переменные
    let columnsConfig = {};
    let autoRefresh = true;
    let refreshInterval;
    let jsonColumns = new Set();
    
    // Инициализация
    init();
    
    function init() {
        loadColumnsConfig();
        setupEventHandlers();
        updateColumnsPanel();
        createTableHeaders();
        fetchSignals();
        
        if (autoRefresh) {
            startAutoRefresh();
        }
        
        console.log('📊 Signals page инициализирован');
    }
    
    // ===== КОНФИГУРАЦИЯ КОЛОНОК =====
    
    function loadColumnsConfig() {
        try {
            const appData = DOM.get('app-data');
            const configData = appData.getAttribute('data-columns-config');
            columnsConfig = JSON.parse(configData);
        } catch (e) {
            console.error('Ошибка загрузки конфигурации колонок:', e);
            // Резервная конфигурация
            columnsConfig = getDefaultColumnsConfig();
        }
        console.log('Загружена конфигурация колонок:', columnsConfig);
    }
    
    function getDefaultColumnsConfig() {
        return {
            'id': {'name': '#', 'visible': true, 'order': 0},
            'timestamp': {'name': 'Time', 'visible': true, 'order': 1},
            'action': {'name': 'Action', 'visible': true, 'order': 2},
            'symbol': {'name': 'Symbol', 'visible': true, 'order': 3},
            'quantity': {'name': 'Qty', 'visible': true, 'order': 4},
            'result': {'name': 'Result', 'visible': true, 'order': 5},
            'strategy': {'name': 'Strategy', 'visible': true, 'order': 6}
        };
    }
    
    function updateColumnsPanel() {
        const grid = DOM.get('columns-grid');
        grid.innerHTML = '';
        
        Object.entries(columnsConfig).forEach(([key, config]) => {
            const item = DOM.create('div', 'column-item');
            
            const checkbox = DOM.create('input');
            checkbox.type = 'checkbox';
            checkbox.checked = config.visible;
            checkbox.onchange = function() {
                updateColumnVisibility(key, this.checked);
            };
            
            const label = DOM.create('span', '', config.name);
            
            const orderInput = DOM.create('input');
            orderInput.type = 'number';
            orderInput.value = config.order;
            orderInput.min = '0';
            orderInput.max = '20';
            orderInput.onchange = function() {
                updateColumnOrder(key, this.value);
            };
            
            item.appendChild(checkbox);
            item.appendChild(label);
            item.appendChild(orderInput);
            grid.appendChild(item);
        });
    }
    
    function updateColumnVisibility(columnKey, isVisible) {
        columnsConfig[columnKey].visible = isVisible;
        applyColumnVisibility();
        saveColumnsConfig();
    }
    
    function updateColumnOrder(columnKey, order) {
        columnsConfig[columnKey].order = parseInt(order);
        applyColumnVisibility();
        saveColumnsConfig();
    }
    
    async function saveColumnsConfig() {
        try {
            const result = await API.post('/save_columns_config', columnsConfig);
            if (result.status !== 'success') {
                console.error('Ошибка сохранения:', result.message);
            }
        } catch (e) {
            console.error('Ошибка сохранения конфигурации:', e);
        }
    }
    
    async function resetColumns() {
        try {
            const result = await API.post('/reset_columns');
            if (result.status === 'success') {
                columnsConfig = result.config;
                updateColumnsPanel();
                applyColumnVisibility();
                await fetchSignals();
                Notifications.success('Конфигурация колонок сброшена');
            }
        } catch (e) {
            console.error('Ошибка сброса конфигурации:', e);
            Notifications.error('Ошибка сброса конфигурации');
        }
    }
    
    // ===== УПРАВЛЕНИЕ ТАБЛИЦЕЙ =====
    
    function createTableHeaders() {
        const headerRow = DOM.get('table-header');
        headerRow.innerHTML = '';
        
        // Сортируем колонки по порядку
        const sortedColumns = Object.entries(columnsConfig)
            .sort((a, b) => a[1].order - b[1].order);
        
        sortedColumns.forEach(([key, config]) => {
            const th = DOM.create('th');
            th.setAttribute('data-column', key);
            th.textContent = config.name;
            
            if (!config.visible) {
                th.classList.add('hidden-column');
            }
            
            headerRow.appendChild(th);
        });
    }
    
    function applyColumnVisibility() {
        createTableHeaders();
        
        // Обновляем ячейки данных
        Object.entries(columnsConfig).forEach(([key, config]) => {
            const elements = document.querySelectorAll('[data-column="' + key + '"]');
            elements.forEach(el => {
                if (config.visible) {
                    el.classList.remove('hidden-column');
                } else {
                    el.classList.add('hidden-column');
                }
            });
        });
    }
    
    // ===== JSON КОЛОНКИ =====
    
    function analyzeAndCreateJsonColumns(data) {
        const extraDataIndex = data.column_map['extra_data'];
        if (extraDataIndex === undefined) return;
        
        const newJsonFields = new Set();
        data.rows.forEach(row => {
            const extraData = row[extraDataIndex];
            if (extraData) {
                try {
                    const jsonData = JSON.parse(extraData);
                    Object.keys(jsonData).forEach(key => newJsonFields.add(key));
                } catch (e) {}
            }
        });
        
        // Добавляем новые поля в конфигурацию
        let configUpdated = false;
        newJsonFields.forEach(field => {
            const jsonKey = `json_${field}`;
            if (!columnsConfig[jsonKey]) {
                columnsConfig[jsonKey] = {
                    name: field,
                    visible: false,
                    order: Object.keys(columnsConfig).length
                };
                jsonColumns.add(jsonKey);
                configUpdated = true;
            }
        });
        
        if (configUpdated) {
            updateColumnsPanel();
            saveColumnsConfig();
        }
    }
    
    function getJsonValue(row, jsonField, extraDataIndex) {
        const extraData = row[extraDataIndex];
        if (!extraData) return null;
        
        try {
            const jsonData = JSON.parse(extraData);
            const fieldName = jsonField.replace('json_', '');
            return jsonData[fieldName];
        } catch (e) {
            return null;
        }
    }
    
    // ===== ЗАГРУЗКА ДАННЫХ =====
    
    async function fetchSignals() {
        try {
            const params = new URLSearchParams(window.location.search);
            const data = await API.get("/signals_data?" + params.toString());
            
            if (data.error) {
                console.error('API Error:', data.error);
                return;
            }
            
            // Анализируем и создаем JSON колонки
            analyzeAndCreateJsonColumns(data);
            
            const tableBody = DOM.get("signal-body");
            tableBody.innerHTML = "";
            
            data.rows.forEach((row) => {
                const tr = DOM.create('tr');
                
                // Создаем ячейки в порядке конфигурации
                const sortedColumns = Object.entries(columnsConfig)
                    .sort((a, b) => a[1].order - b[1].order);
                    
                sortedColumns.forEach(([columnKey, config]) => {
                    const td = DOM.create('td');
                    td.setAttribute('data-column', columnKey);
                    
                    let cellValue = getCellValue(row, columnKey, data);
                    formatCell(td, cellValue, columnKey);
                    
                    tr.appendChild(td);
                });
                
                tableBody.appendChild(tr);
            });
            
            applyColumnVisibility();
                
        } catch (error) {
            console.error("Failed to fetch signals:", error);
            Notifications.error("Ошибка загрузки данных сигналов");
        }
    }
    
    function getCellValue(row, columnKey, data) {
        if (columnKey.startsWith('json_')) {
            // Обработка JSON колонок
            const extraDataIndex = data.column_map['extra_data'];
            return getJsonValue(row, columnKey, extraDataIndex);
        } else {
            // Обычные колонки
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
            formatExtraDataCell(td, cellValue);
        } else if (columnKey.startsWith('json_')) {
            formatJsonCell(td, cellValue);
        } else {
            td.textContent = cellValue || '';
        }
    }
    
    function formatExtraDataCell(td, cellValue) {
        if (cellValue) {
            try {
                const extraData = JSON.parse(cellValue);
                const entries = Object.entries(extraData);
                if (entries.length > 0) {
                    td.innerHTML = entries
                        .map(([key, value]) => `<small><strong>${key}:</strong> ${value}</small>`)
                        .join('<br>');
                    td.title = JSON.stringify(extraData, null, 2);
                } else {
                    td.textContent = '';
                }
            } catch (e) {
                td.textContent = cellValue.substring(0, 50) + (cellValue.length > 50 ? '...' : '');
            }
        } else {
            td.textContent = '';
        }
    }
    
    function formatJsonCell(td, cellValue) {
        if (cellValue !== null && cellValue !== undefined && cellValue !== '') {
            if (typeof cellValue === 'boolean') {
                td.textContent = cellValue ? '✅' : '❌';
            } else if (Array.isArray(cellValue)) {
                td.textContent = cellValue.join(', ');
                td.title = JSON.stringify(cellValue);
            } else if (typeof cellValue === 'object') {
                td.textContent = JSON.stringify(cellValue);
                td.title = JSON.stringify(cellValue, null, 2);
            } else {
                td.textContent = String(cellValue);
            }
        } else {
            td.innerHTML = '<span class="json-empty">-</span>';
        }
    }
    
    // ===== АВТООБНОВЛЕНИЕ =====
    
    function toggleAutoRefresh() {
        autoRefresh = !autoRefresh;
        const btn = DOM.get('refresh-btn');
        
        if (autoRefresh) {
            btn.textContent = '⏸️ Pause';
            btn.classList.remove('active');
            startAutoRefresh();
            console.log('🔄 Автообновление запущено');
        } else {
            btn.textContent = '⏸️ Pause';
            btn.classList.add('active');
            stopAutoRefresh();
            console.log('⏸️ Автообновление на паузе');
        }
    }
    
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(fetchSignals, 3000);
    }
    
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
    
    // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
    
    function setupEventHandlers() {
        // Кнопка конфигурации колонок
        const columnsBtn = DOM.get('columns-btn');
        columnsBtn.addEventListener('click', toggleColumnsPanel);
        
        // Кнопка автообновления
        const refreshBtn = DOM.get('refresh-btn');
        refreshBtn.addEventListener('click', toggleAutoRefresh);
        
        // Кнопка сброса колонок
        const resetBtn = DOM.get('reset-columns-btn');
        resetBtn.addEventListener('click', resetColumns);
        
        // Останавливаем автообновление при уходе со страницы
        window.addEventListener('beforeunload', stopAutoRefresh);
        
        // Управление автообновлением в зависимости от видимости страницы
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopAutoRefresh();
            } else if (autoRefresh) {
                startAutoRefresh();
            }
        });
    }
    
    function toggleColumnsPanel() {
        const panel = DOM.get('columns-panel');
        const btn = DOM.get('columns-btn');
        
        if (panel.style.display === 'none' || panel.style.display === '') {
            panel.style.display = 'block';
            btn.classList.add('active');
        } else {
            panel.style.display = 'none';
            btn.classList.remove('active');
        }
    }
    
    // ===== ЭКСПОРТ ДЛЯ ОТЛАДКИ =====
    
    // Делаем функции доступными глобально для отладки
    window.SignalsPage = {
        fetchSignals,
        toggleAutoRefresh,
        resetColumns,
        toggleColumnsPanel,
        columnsConfig: () => columnsConfig,
        autoRefresh: () => autoRefresh
    };
});