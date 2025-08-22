// ===== МОДУЛЬ КОНФИГУРАЦИИ КОЛОНОК СОКЕТОВ =====

window.SocketsColumns = (function() {
    const { DOM, API, Notifications } = window.TradingBotUI;
    
    let columnsConfig = {};
    
    function loadColumnsConfig() {
        try {
            const appData = DOM.get('app-data');
            const configData = appData.getAttribute('data-columns-config');
            columnsConfig = JSON.parse(configData);
        } catch (e) {
            console.error('Ошибка загрузки конфигурации колонок сокетов:', e);
            columnsConfig = getDefaultColumnsConfig();
        }
    }
    
    function getDefaultColumnsConfig() {
        return {
            'id': {'name': '#', 'visible': true, 'order': 0},
            'timestamp': {'name': 'timestamp', 'visible': true, 'order': 1},
            'event_type': {'name': 'event_type', 'visible': true, 'order': 2},
            'symbol': {'name': 'symbol', 'visible': true, 'order': 3},
            'order_id': {'name': 'order_id', 'visible': true, 'order': 4},
            'status': {'name': 'status', 'visible': true, 'order': 5},
            'raw_message': {'name': 'raw_message', 'visible': false, 'order': 6}
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
            const result = await API.post('/sockets/save_columns_config', columnsConfig);
            if (result.status === 'success') {
                console.log('✅ Конфигурация колонок сокетов сохранена');
            }
        } catch (e) {
            console.error('❌ Ошибка сохранения конфигурации сокетов:', e);
        }
    }
    
    async function resetColumns() {
        try {
            const result = await API.post('/sockets/reset_columns');
            if (result.status === 'success') {
                columnsConfig = result.config;
                updateColumnsPanel();
                applyColumnVisibility();
                await window.SocketsTable.fetchSockets();
                Notifications.success('Конфигурация колонок сокетов сброшена');
            }
        } catch (e) {
            console.error('Ошибка сброса конфигурации сокетов:', e);
            Notifications.error('Ошибка сброса конфигурации сокетов');
        }
    }
    
    function createTableHeaders() {
        const headerRow = DOM.get('table-header');
        headerRow.innerHTML = '';
        
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
    
    // Публичный API модуля
    return {
        loadColumnsConfig,
        updateColumnsPanel,
        resetColumns,
        createTableHeaders,
        applyColumnVisibility,
        saveColumnsConfig,
        getConfig: () => columnsConfig,
        setConfig: (config) => { columnsConfig = config; }
    };
})();