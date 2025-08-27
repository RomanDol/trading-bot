// ===== static/js/universal/universal-table.js =====
/**
 * НАСТОЯЩИЙ универсальный ридер таблиц
 * Работает с любыми колонками, определяет типы данных автоматически
 */

window.UniversalTable = (function() {
    'use strict';
    
    let config = {
        tableType: '',
        columnsConfig: {},
        currentPage: 1,
        totalPages: 1,
        limit: 50,
        isAutoRefresh: false,
        autoRefreshInterval: null,
        jsonDisplayMode: 'inline'
    };
    
    // ===== ИНИЦИАЛИЗАЦИЯ =====
    
    function init() {
        console.log('Инициализация универсальной таблицы...');
        
        loadConfigFromDOM();
        setupEventHandlers();
        createDynamicFilterForm();
        createTableHeaders();
        fetchTableData();
        loadSavedSettings();
        
        console.log(`Универсальная таблица инициализирована для типа: ${config.tableType}`);
    }
    
    function loadConfigFromDOM() {
        const appData = document.getElementById('app-data');
        if (appData) {
            config.tableType = appData.dataset.tableType || '';
            config.columnsConfig = JSON.parse(appData.dataset.columnsConfig || '{}');
        }
    }
    
    function loadSavedSettings() {
        const savedJsonMode = localStorage.getItem(`${config.tableType}_json_display_mode`);
        if (savedJsonMode) {
            config.jsonDisplayMode = savedJsonMode;
        }
        
        const savedAutoRefresh = localStorage.getItem(`${config.tableType}_auto_refresh`);
        if (savedAutoRefresh === 'true') {
            startAutoRefresh();
        }
    }
    
    // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
    
    function setupEventHandlers() {
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', toggleSettingsPanel);
        }
        
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', toggleAutoRefresh);
        }
        
        const toggleJsonBtn = document.getElementById('toggle-json-format-btn');
        if (toggleJsonBtn) {
            toggleJsonBtn.addEventListener('click', toggleGlobalJsonFormat);
        }
        
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportToExcel);
        }
        
        setupPaginationHandlers();
    }
    
    function setupPaginationHandlers() {
        const paginationButtons = [
            { id: 'first-page-btn', action: () => goToPage(1) },
            { id: 'prev-page-btn', action: () => goToPage(config.currentPage - 1) },
            { id: 'next-page-btn', action: () => goToPage(config.currentPage + 1) },
            { id: 'last-page-btn', action: () => goToPage(config.totalPages) }
        ];
        
        paginationButtons.forEach(btn => {
            const element = document.getElementById(btn.id);
            if (element) {
                element.addEventListener('click', btn.action);
            }
        });
    }
    
    // ===== АВТОМАТИЧЕСКИЕ ФИЛЬТРЫ =====
    
    function createDynamicFilterForm() {
        const filterForm = document.getElementById('filter-form');
        if (!filterForm) return;
        
        filterForm.innerHTML = '';
        
        const urlParams = new URLSearchParams(window.location.search);
        
        // Получаем первую строку данных для определения типов колонок
        const visibleColumns = getVisibleColumns();
        
        visibleColumns.forEach(columnKey => {
            const filterType = detectColumnType(columnKey);
            if (filterType === 'json') return; // Пропускаем JSON колонки
            
            const input = createFilterInput(columnKey, filterType, urlParams);
            if (input) {
                filterForm.appendChild(input);
            }
        });
        
        // Кнопки
        const submitBtn = document.createElement('button');
        submitBtn.type = 'submit';
        submitBtn.className = 'btn';
        submitBtn.textContent = 'Search';
        filterForm.appendChild(submitBtn);
        
        const clearBtn = document.createElement('a');
        clearBtn.href = window.location.pathname;
        clearBtn.className = 'btn';
        clearBtn.textContent = 'Clear';
        filterForm.appendChild(clearBtn);
    }
    
    function detectColumnType(columnKey) {
        // Определяем тип колонки по её названию
        const lowerKey = columnKey.toLowerCase();
        
        if (lowerKey.includes('date') || lowerKey.includes('time') || lowerKey === 'timestamp') {
            return 'date';
        }
        if (lowerKey.includes('message') || lowerKey.includes('data') || lowerKey.includes('raw_')) {
            return 'json';
        }
        if (lowerKey.includes('id') || lowerKey.includes('quantity') || lowerKey.includes('count')) {
            return 'number';
        }
        
        return 'text';
    }
    
    function createFilterInput(columnKey, filterType, urlParams) {
        const input = document.createElement('input');
        input.name = columnKey;
        input.placeholder = columnKey;
        input.value = urlParams.get(columnKey) || '';
        input.className = 'filter-input';
        
        switch (filterType) {
            case 'date':
                input.type = 'date';
                break;
            case 'number':
                input.type = 'number';
                input.placeholder = `${columnKey} (number)`;
                break;
            default:
                input.type = 'text';
                break;
        }
        
        return input;
    }
    
    // ===== СОЗДАНИЕ ТАБЛИЦЫ =====
    
    function createTableHeaders() {
        const headerRow = document.getElementById('table-header');
        if (!headerRow) return;
        
        headerRow.innerHTML = '';
        
        const visibleColumns = getVisibleColumns();
        
        visibleColumns.forEach(columnKey => {
            const th = document.createElement('th');
            // СОХРАНЯЕМ ОРИГИНАЛЬНОЕ НАЗВАНИЕ КОЛОНКИ
            th.textContent = columnKey;
            th.dataset.column = columnKey;
            headerRow.appendChild(th);
        });
    }
    
    // ===== РАБОТА С ДАННЫМИ =====
    
    function fetchTableData() {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set('limit', config.limit);
        urlParams.set('page', config.currentPage);
        
        const url = `/${config.tableType}/data?${urlParams}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    renderTableData(data.data);
                    updatePaginationInfo(data);
                } else {
                    console.error('Ошибка загрузки данных:', data.message);
                }
            })
            .catch(error => {
                console.error('Ошибка запроса:', error);
            });
    }
    
    function renderTableData(data) {
        const tbody = document.getElementById('table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!data || data.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = getVisibleColumns().length;
            cell.className = 'text-center text-muted';
            cell.textContent = 'No data available';
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }
        
        const visibleColumns = getVisibleColumns();
        
        data.forEach(rowData => {
            const row = document.createElement('tr');
            
            visibleColumns.forEach(columnKey => {
                const cell = document.createElement('td');
                cell.dataset.column = columnKey;
                
                const cellValue = getCellValue(rowData, columnKey);
                formatCell(cell, cellValue, columnKey);
                
                row.appendChild(cell);
            });
            
            tbody.appendChild(row);
        });
    }
    
    function getCellValue(rowData, columnKey) {
        if (Array.isArray(rowData)) {
            const visibleColumns = getVisibleColumns();
            const columnIndex = visibleColumns.indexOf(columnKey);
            return columnIndex !== -1 ? rowData[columnIndex] : '';
        }
        return rowData[columnKey] || '';
    }
    
    function formatCell(cell, cellValue, columnKey) {
        // Универсальное форматирование только по содержимому
        if (isJsonContent(cellValue)) {
            formatJsonCell(cell, cellValue);
        } else if (isDateContent(cellValue)) {
            cell.textContent = formatDateTime(cellValue);
        } else {
            cell.textContent = cellValue || '';
        }
    }
    
    // ===== УНИВЕРСАЛЬНОЕ ОПРЕДЕЛЕНИЕ ТИПОВ =====
    
    function isJsonContent(cellValue) {
        if (!cellValue || typeof cellValue !== 'string') return false;
        
        const trimmed = cellValue.trim();
        if (!((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
              (trimmed.startsWith('[') && trimmed.endsWith(']')))) {
            return false;
        }
        
        try {
            JSON.parse(trimmed);
            return true;
        } catch {
            return false;
        }
    }
    
    function isDateContent(cellValue) {
        if (!cellValue || typeof cellValue !== 'string') return false;
        
        // Проверяем формат даты
        const datePattern = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/;
        return datePattern.test(cellValue);
    }
    
    function formatJsonCell(cell, cellValue) {
        cell.setAttribute('data-original-value', cellValue);
        cell.classList.add('json-cell');
        
        try {
            const jsonData = JSON.parse(cellValue);
            const jsonContainer = document.createElement('div');
            jsonContainer.className = 'json-container';
            
            let formattedContent;
            
            if (config.jsonDisplayMode === 'column') {
                formattedContent = JSON.stringify(jsonData, null, 2);
                formattedContent = formattedContent.replace(/^\{\s*/, '').replace(/\s*\}$/, '');
                jsonContainer.style.whiteSpace = 'pre-wrap';
                jsonContainer.style.maxWidth = '300px';
            } else {
                if (typeof jsonData === 'object' && !Array.isArray(jsonData)) {
                    const entries = Object.entries(jsonData);
                    formattedContent = entries
                        .map(([key, value]) => `"${key}": ${JSON.stringify(value)}`)
                        .join(', ');
                } else {
                    formattedContent = JSON.stringify(jsonData);
                }
                jsonContainer.style.whiteSpace = 'nowrap';
                cell.title = JSON.stringify(jsonData, null, 2);
            }
            
            jsonContainer.textContent = formattedContent;
            cell.innerHTML = '';
            cell.appendChild(jsonContainer);
            
        } catch (e) {
            cell.textContent = cellValue.substring(0, 200) + (cellValue.length > 200 ? '...' : '');
        }
    }
    
    function toggleGlobalJsonFormat() {
        config.jsonDisplayMode = config.jsonDisplayMode === 'inline' ? 'column' : 'inline';
        localStorage.setItem(`${config.tableType}_json_display_mode`, config.jsonDisplayMode);
        
        // Применяем ко всем JSON ячейкам
        const jsonCells = document.querySelectorAll('.json-cell');
        jsonCells.forEach(cell => {
            const originalValue = cell.getAttribute('data-original-value');
            if (originalValue) {
                formatJsonCell(cell, originalValue);
            }
        });
        
        console.log(`JSON формат переключен на "${config.jsonDisplayMode}"`);
    }
    
    // ===== УТИЛИТЫ =====
    
    function formatDateTime(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            return date.toLocaleString('ru-RU', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return dateStr;
        }
    }
    
    function getVisibleColumns() {
        return Object.entries(config.columnsConfig)
            .filter(([, settings]) => settings.visible)
            .sort(([,a], [,b]) => (a.order || 999) - (b.order || 999))
            .map(([columnKey]) => columnKey);
    }
    
    function toggleSettingsPanel() {
        const panel = document.getElementById('settings-panel');
        const btn = document.getElementById('settings-btn');
        
        if (panel.style.display === 'none' || panel.style.display === '') {
            panel.style.display = 'block';
            btn.classList.add('active');
        } else {
            panel.style.display = 'none';
            btn.classList.remove('active');
        }
    }
    
    function toggleAutoRefresh() {
        if (config.isAutoRefresh) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    }
    
    function startAutoRefresh() {
        config.isAutoRefresh = true;
        config.autoRefreshInterval = setInterval(fetchTableData, 5000);
        
        const btn = document.getElementById('refresh-btn');
        if (btn) {
            btn.textContent = 'Pause';
            btn.classList.add('auto-refresh-active');
        }
        
        localStorage.setItem(`${config.tableType}_auto_refresh`, 'true');
    }
    
    function stopAutoRefresh() {
        config.isAutoRefresh = false;
        if (config.autoRefreshInterval) {
            clearInterval(config.autoRefreshInterval);
            config.autoRefreshInterval = null;
        }
        
        const btn = document.getElementById('refresh-btn');
        if (btn) {
            btn.textContent = 'Refresh';
            btn.classList.remove('auto-refresh-active');
        }
        
        localStorage.setItem(`${config.tableType}_auto_refresh`, 'false');
    }
    
    function goToPage(page) {
        if (page < 1 || page > config.totalPages) return;
        
        config.currentPage = page;
        fetchTableData();
    }
    
    function updatePaginationInfo(data) {
        config.totalPages = data.total_pages || 1;
        
        const totalSpan = document.getElementById('total-pages-span');
        if (totalSpan) totalSpan.textContent = `of ${config.totalPages}`;
        
        const hasNext = data.has_next;
        const hasPrev = data.has_prev;
        
        const nextBtn = document.getElementById('next-page-btn');
        const prevBtn = document.getElementById('prev-page-btn');
        const firstBtn = document.getElementById('first-page-btn');
        const lastBtn = document.getElementById('last-page-btn');
        
        if (nextBtn) nextBtn.disabled = !hasNext;
        if (lastBtn) lastBtn.disabled = !hasNext;
        if (prevBtn) prevBtn.disabled = !hasPrev;
        if (firstBtn) firstBtn.disabled = !hasPrev;
    }
    
    function exportToExcel() {
        const urlParams = new URLSearchParams(window.location.search);
        window.location.href = `/${config.tableType}/export_excel?${urlParams}`;
    }
    
    // ===== ПУБЛИЧНЫЙ API =====
    
    return {
        init,
        fetchTableData,
        toggleGlobalJsonFormat
    };
    
})();