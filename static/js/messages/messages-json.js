// ===== МОДУЛЬ JSON КОЛОНОК СООБЩЕНИЙ =====

window.MessagesJSON = (function() {
    let jsonColumns = new Set();
    
    function analyzeAndCreateJsonColumns(data) {
        // Обрабатываем message колонку для json_* колонок
        const messageIndex = data.column_map['message'];
        if (messageIndex !== undefined) {
            analyzeJsonField(data, messageIndex, 'json_');
        }
    }
    
    function analyzeJsonField(data, fieldIndex, prefix) {
        const newJsonFields = new Set();
        data.rows.forEach(row => {
            const jsonData = row[fieldIndex];
            if (jsonData) {
                try {
                    const parsedData = JSON.parse(jsonData);
                    Object.keys(parsedData).forEach(key => {
                        // Исключаем слишком сложные вложенные объекты для колонок
                        if (typeof parsedData[key] !== 'object' || parsedData[key] === null) {
                            newJsonFields.add(key);
                        } else if (Array.isArray(parsedData[key]) && parsedData[key].length < 10) {
                            // Добавляем небольшие массивы
                            newJsonFields.add(key);
                        }
                    });
                } catch (e) {
                    // Не JSON - пропускаем
                }
            }
        });
        
        let configUpdated = false;
        const columnsConfig = window.MessagesColumns.getConfig();
        
        newJsonFields.forEach(field => {
            const columnKey = `${prefix}${field}`;
            if (!columnsConfig[columnKey]) {
                columnsConfig[columnKey] = {
                    name: getFieldDisplayName(field, prefix),
                    visible: isFieldVisibleByDefault(field),
                    order: Object.keys(columnsConfig).length
                };
                jsonColumns.add(columnKey);
                configUpdated = true;
                console.log(`➕ Добавлена ${prefix}колонка сообщений: ${field} (visible: ${columnsConfig[columnKey].visible})`);
            }
        });
        
        if (configUpdated) {
            window.MessagesColumns.setConfig(columnsConfig);
            window.MessagesColumns.updateColumnsPanel();
            window.MessagesColumns.saveColumnsConfig();
        }
    }
    
    function getFieldDisplayName(field, prefix) {
        // Специальные названия для известных полей
        const specialNames = {
            'e': 'Event Type',
            'E': 'Event Time', 
            'T': 'Transaction Time',
            's': 'Symbol',
            'c': 'Client Order ID',
            'S': 'Side',
            'o': 'Order Type',
            'q': 'Quantity',
            'p': 'Price',
            'i': 'Order ID',
            'X': 'Order Status',
            'x': 'Execution Type',
            'z': 'Cumulative Filled Qty',
            'L': 'Last Executed Price',
            'l': 'Last Executed Qty',
            'n': 'Commission Amount',
            'N': 'Commission Asset',
            'action': 'Action',
            'symbol': 'Symbol',
            'quantity': 'Quantity',
            'strategy': 'Strategy',
            'auth_key': 'Auth Key',
            'timestamp': 'Timestamp',
            'orderId': 'Order ID',
            'status': 'Status',
            'side': 'Side',
            'type': 'Type',
            'executedQty': 'Executed Qty',
            'avgPrice': 'Avg Price',
            'origQty': 'Original Qty',
            'updateTime': 'Update Time'
        };
        
        return specialNames[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    function isFieldVisibleByDefault(field) {
        // Поля которые показываем по умолчанию
        const visibleFields = [
            'action', 'symbol', 'quantity', 'status', 'side', 'type', 
            'orderId', 'executedQty', 'avgPrice', 'strategy'
        ];
        
        return visibleFields.includes(field);
    }
    
    function getJsonValue(row, jsonField, sourceIndex) {
        const sourceData = row[sourceIndex];
        if (!sourceData) return null;
        
        try {
            const jsonData = JSON.parse(sourceData);
            const fieldName = jsonField.replace(/^(json_)/, '');
            return jsonData[fieldName];
        } catch (e) {
            return null;
        }
    }
    
    function formatJsonCell(td, cellValue) {
        if (cellValue !== null && cellValue !== undefined && cellValue !== '') {
            if (typeof cellValue === 'boolean') {
                td.textContent = cellValue ? '✅ Yes' : '❌ No';
                td.className = cellValue ? 'json-boolean-true' : 'json-boolean-false';
                
            } else if (Array.isArray(cellValue)) {
                if (cellValue.length === 0) {
                    td.innerHTML = '<span class="json-empty">[]</span>';
                } else if (cellValue.length <= 3) {
                    td.textContent = cellValue.join(', ');
                } else {
                    td.textContent = `[${cellValue.length} items]`;
                }
                td.title = JSON.stringify(cellValue);
                
            } else if (typeof cellValue === 'object') {
                const entries = Object.entries(cellValue);
                if (entries.length === 0) {
                    td.innerHTML = '<span class="json-empty">{}</span>';
                } else if (entries.length === 1) {
                    const [key, value] = entries[0];
                    td.innerHTML = `<small><strong>${key}:</strong> ${value}</small>`;
                } else {
                    td.innerHTML = `<small>{${entries.length} fields}</small>`;
                }
                td.title = JSON.stringify(cellValue, null, 2);
                
            } else if (typeof cellValue === 'string') {
                // Специальная обработка для разных типов строк
                if (cellValue.length > 50) {
                    td.textContent = cellValue.substring(0, 50) + '...';
                    td.title = cellValue;
                } else {
                    td.textContent = cellValue;
                }
                
                // Добавляем CSS классы для специальных значений
                if (isNumericString(cellValue)) {
                    td.classList.add('json-numeric');
                } else if (isTimestampString(cellValue)) {
                    td.classList.add('json-timestamp');
                }
                
            } else if (typeof cellValue === 'number') {
                // Форматируем числа
                if (cellValue > 1000000) {
                    // Большие числа (возможно timestamp)
                    if (cellValue > 1000000000000) {
                        // Timestamp в миллисекундах
                        const date = new Date(cellValue);
                        td.textContent = date.toLocaleString();
                        td.title = `Timestamp: ${cellValue}`;
                        td.classList.add('json-timestamp');
                    } else {
                        td.textContent = cellValue.toLocaleString();
                        td.classList.add('json-large-number');
                    }
                } else {
                    td.textContent = String(cellValue);
                    td.classList.add('json-number');
                }
                
            } else {
                td.textContent = String(cellValue);
            }
        } else {
            td.innerHTML = '<span class="json-empty">-</span>';
        }
    }
    
    function isNumericString(str) {
        return /^\d+(\.\d+)?$/.test(str);
    }
    
    function isTimestampString(str) {
        return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(str);
    }
    
    function getJsonFieldType(value) {
        if (value === null || value === undefined) return 'null';
        if (typeof value === 'boolean') return 'boolean';
        if (typeof value === 'number') return 'number';
        if (typeof value === 'string') {
            if (isNumericString(value)) return 'numeric-string';
            if (isTimestampString(value)) return 'timestamp';
            return 'string';
        }
        if (Array.isArray(value)) return 'array';
        if (typeof value === 'object') return 'object';
        return 'unknown';
    }
    
    function createJsonPreview(jsonData) {
        /**
         * Создает краткий превью JSON объекта для отображения
         */
        try {
            const parsed = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
            const entries = Object.entries(parsed);
            
            if (entries.length === 0) return '{}';
            if (entries.length <= 2) {
                return entries.map(([key, value]) => {
                    const shortValue = String(value).substring(0, 20);
                    return `${key}: ${shortValue}`;
                }).join(', ');
            }
            
            return `{${entries.length} fields: ${entries.slice(0, 2).map(([key]) => key).join(', ')}, ...}`;
            
        } catch (e) {
            return String(jsonData).substring(0, 50);
        }
    }
    
    return {
        analyzeAndCreateJsonColumns,
        getJsonValue,
        formatJsonCell,
        getFieldDisplayName,
        isFieldVisibleByDefault,
        getJsonFieldType,
        createJsonPreview,
        getJsonColumns: () => jsonColumns
    };
})();