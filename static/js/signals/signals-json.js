// ===== МОДУЛЬ JSON КОЛОНОК =====

window.SignalsJSON = (function() {
    let jsonColumns = new Set();
    
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
        
        let configUpdated = false;
        const columnsConfig = window.SignalsColumns.getConfig();
        
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
                console.log(`➕ Добавлена новая JSON колонка: ${field} (скрыта)`);
            }
        });
        
        if (configUpdated) {
            window.SignalsColumns.setConfig(columnsConfig);
            window.SignalsColumns.updateColumnsPanel();
            window.SignalsColumns.saveColumnsConfig();
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
    
    // Публичный API модуля
    return {
        analyzeAndCreateJsonColumns,
        getJsonValue,
        formatExtraDataCell,
        formatJsonCell,
        getJsonColumns: () => jsonColumns
    };
})();