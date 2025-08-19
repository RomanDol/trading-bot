// ===== МОДУЛЬ JSON КОЛОНОК =====

window.SignalsJSON = (function() {
    let jsonColumns = new Set();
    
    function analyzeAndCreateJsonColumns(data) {
        // Обрабатываем extra_data для webhook_* колонок
        const extraDataIndex = data.column_map['extra_data'];
        if (extraDataIndex !== undefined) {
            analyzeJsonField(data, extraDataIndex, 'webhook_');
        }
        
        // Обрабатываем message для binance_* колонок
        const messageIndex = data.column_map['message'];
        if (messageIndex !== undefined) {
            analyzeJsonField(data, messageIndex, 'binance_');
        }
    }
    
    function analyzeJsonField(data, fieldIndex, prefix) {
        const newJsonFields = new Set();
        data.rows.forEach(row => {
            const jsonData = row[fieldIndex];
            if (jsonData) {
                try {
                    const parsedData = JSON.parse(jsonData);
                    Object.keys(parsedData).forEach(key => newJsonFields.add(key));
                } catch (e) {
                    // Не JSON - пропускаем
                }
            }
        });
        
        let configUpdated = false;
        const columnsConfig = window.SignalsColumns.getConfig();
        
        newJsonFields.forEach(field => {
            const columnKey = `${prefix}${field}`;
            if (!columnsConfig[columnKey]) {
                columnsConfig[columnKey] = {
                    name: getFieldDisplayName(field, prefix),
                    visible: false,
                    order: Object.keys(columnsConfig).length
                };
                jsonColumns.add(columnKey);
                configUpdated = true;
                console.log(`➕ Добавлена ${prefix}колонка: ${field}`);
            }
        });
        
        if (configUpdated) {
            window.SignalsColumns.setConfig(columnsConfig);
            window.SignalsColumns.updateColumnsPanel();
            window.SignalsColumns.saveColumnsConfig();
        }
    }
    
    function getFieldDisplayName(field, prefix) {
        if (prefix === 'binance_') {
            const binanceNames = {
                'orderId': 'Order ID',
                'executedQty': 'Executed Qty',
                'avgPrice': 'Avg Price',
                'status': 'Status',
                'error': 'Error',
                'error_message': 'Error Message',
                'error_code': 'Error Code'
            };
            return binanceNames[field] || field;
        } else if (prefix === 'webhook_') {
            return field.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        return field;
    }
    
    function getJsonValue(row, jsonField, sourceIndex) {
        const sourceData = row[sourceIndex];
        if (!sourceData) return null;
        
        try {
            const jsonData = JSON.parse(sourceData);
            const fieldName = jsonField.replace(/^(webhook_|binance_)/, '');
            return jsonData[fieldName];
        } catch (e) {
            return null;
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
    
    return {
        analyzeAndCreateJsonColumns,
        getJsonValue,
        formatExtraDataCell,
        formatJsonCell,
        getJsonColumns: () => jsonColumns
    };
})();