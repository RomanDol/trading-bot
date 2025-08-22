// ===== МОДУЛЬ JSON КОЛОНОК СОКЕТОВ =====

window.SocketsJSON = (function() {
    let jsonColumns = new Set();
    
    function analyzeAndCreateJsonColumns(data) {
        // Обрабатываем raw_message для socket_* колонок
        const rawMessageIndex = data.column_map['raw_message'];
        if (rawMessageIndex !== undefined) {
            analyzeJsonField(data, rawMessageIndex, 'socket_');
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
        const columnsConfig = window.SocketsColumns.getConfig();
        
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
                console.log(`➕ Добавлена ${prefix}колонка сокета: ${field}`);
            }
        });
        
        if (configUpdated) {
            window.SocketsColumns.setConfig(columnsConfig);
            window.SocketsColumns.updateColumnsPanel();
            window.SocketsColumns.saveColumnsConfig();
        }
    }
    
    function getFieldDisplayName(field, prefix) {
        if (prefix === 'socket_') {
            // Оставляем оригинальные названия полей как есть
            return field;
        }
        return field;
    }
    
    function getJsonValue(row, jsonField, sourceIndex) {
        const sourceData = row[sourceIndex];
        if (!sourceData) return null;
        
        try {
            const jsonData = JSON.parse(sourceData);
            const fieldName = jsonField.replace(/^(socket_)/, '');
            return jsonData[fieldName];
        } catch (e) {
            return null;
        }
    }
    
    function formatRawMessageCell(td, cellValue) {
        if (cellValue) {
            try {
                const messageData = JSON.parse(cellValue);
                const entries = Object.entries(messageData);
                if (entries.length > 0) {
                    td.innerHTML = entries
                        .slice(0, 5) // Показываем только первые 5 полей
                        .map(([key, value]) => `<small><strong>${key}:</strong> ${value}</small>`)
                        .join('<br>');
                    td.title = JSON.stringify(messageData, null, 2);
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
        formatRawMessageCell,
        formatJsonCell,
        getJsonColumns: () => jsonColumns
    };
})();