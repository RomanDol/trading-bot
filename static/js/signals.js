function setPaginationLoading(isLoading) {
        if (!paginationState.isVisible) return; // Не обновляем если пагинация скрыта
        
        const paginationControls = [
            DOM.get('pagination-controls-top'),
            DOM.get('pagination-controls-bottom')
        ].filter(control => control && !control.classList.contains('hidden'));
        
        paginationControls.forEach(control => {
            if (isLoading) {
                control.style.opacity = '0.6';
                control.style.pointerEvents = 'none';
            } else {
                control.style.opacity = '1';
                control.style.pointerEvents = 'auto';
            }
        });
    }
    
    function togglePaginationVisibility() {
        paginationState.isVisible = !paginationState.isVisible;
        const btn = DOM.get('toggle-pagination-btn');
        const paginationControls = [
            DOM.get('pagination-controls-top'),
            DOM.get('pagination-controls-bottom')
        ];
        
        if (paginationState.isVisible) {
            btn.textContent = '📄 Hide Pagination';
            btn.classList.remove('active');
            paginationControls.forEach(control => {
                if (control) {
                    control.classList.remove('hidden');
                    control.style.display = 'flex'; // Принудительно показываем
                }
            });
            
            // Сохраняем состояние
            localStorage.setItem('pagination_visible', 'true');
        } else {
            btn.classList.add('active');
            paginationControls.forEach(control => {
                if (control) {
                    control.classList.add('hidden');
                    control.style.display = 'none'; // Принудительно скрываем
                }
            });
            
            // Сохраняем состояние
            localStorage.setItem('pagination_visible', 'false');
        }
    }
    
    function loadPaginationVisibility() {
        const savedVisibility = localStorage.getItem('pagination_visible');
        
        if (savedVisibility === 'false') {
            // Принудительно скрываем пагинацию
            paginationState.isVisible = false;
            const btn = DOM.get('toggle-pagination-btn');
            const paginationControls = [
                DOM.get('pagination-controls-top'),
                DOM.get('pagination-controls-bottom')
            ];
            
            btn.classList.add('active');
            paginationControls.forEach(control => {
                if (control) {
                    control.classList.add('hidden');
                    control.style.display = 'none';
                }
            });
            
        }
    }
            // ===== JAVASCRIPT ДЛЯ SIGNALS PAGE С ПАГИНАЦИЕЙ =====

document.addEventListener('DOMContentLoaded', function() {
    const { DOM, API, DateUtils, Notifications } = window.TradingBotUI;
    
    // Глобальные переменные
    let columnsConfig = {};
    let autoRefresh = true;
    let refreshInterval;
    let jsonColumns = new Set();
    
    // Состояние пагинации
    let paginationState = {
        currentPage: 1,
        totalPages: 1,
        limit: 50,
        totalCount: 0,
        hasNext: false,
        hasPrev: false,
        isVisible: true // Добавляем состояние видимости пагинации
    };
    
    // Инициализация
    function init() {
        loadColumnsConfig();
        setupEventHandlers();
        setupPaginationHandlers();
        
        // Загружаем состояние пагинации
        const savedVisibility = localStorage.getItem('pagination_visible');
        if (savedVisibility === 'false') {
            document.getElementById('pagination-controls-top').style.display = 'none';
            document.getElementById('pagination-controls-bottom').style.display = 'none';
            document.getElementById('toggle-pagination-btn').classList.add('active');
        }
        
        updateColumnsPanel();
        createTableHeaders();
        fetchSignals();
        
        if (autoRefresh) {
            startAutoRefresh();
        }
        
    }
    
    // Запускаем инициализацию
    init();
    
    // ===== КОНФИГУРАЦИЯ КОЛОНОК =====
    
    function loadColumnsConfig() {
        try {
            const appData = DOM.get('app-data');
            const configData = appData.getAttribute('data-columns-config');
            columnsConfig = JSON.parse(configData);
        } catch (e) {
            console.error('Ошибка загрузки конфигурации колонок:', e);
            columnsConfig = getDefaultColumnsConfig();
        }
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
            if (result.status === 'success') {
                console.log('✅ Конфигурация колонок сохранена');
            }
        } catch (e) {
            console.error('❌ Ошибка сохранения конфигурации:', e);
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
    
    // ===== ПАГИНАЦИЯ =====
    
    function setupPaginationHandlers() {
        // Настройка количества строк через поле ввода
        const rowsInput = DOM.get('rows-per-page-input');
        const applyBtn = DOM.get('apply-rows-btn');
        
        // Загружаем сохраненное значение из localStorage
        const savedLimit = localStorage.getItem('signals_rows_per_page');
        if (savedLimit) {
            paginationState.limit = parseInt(savedLimit);
            rowsInput.value = paginationState.limit;
        }
        
        applyBtn.addEventListener('click', function() {
            const newLimit = parseInt(rowsInput.value);
            if (newLimit >= 1 && newLimit <= 10000) {
                paginationState.limit = newLimit;
                paginationState.currentPage = 1; // Сбрасываем на первую страницу
                
                // Сохраняем в localStorage
                localStorage.setItem('signals_rows_per_page', newLimit);
                
                fetchSignals();
                Notifications.success(`Установлено ${newLimit} строк на странице`);
            } else {
                Notifications.error('Количество строк должно быть от 1 до 10000');
                rowsInput.value = paginationState.limit;
            }
        });
        
        // Применение по Enter
        rowsInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyBtn.click();
            }
        });
        
        // Кнопки навигации (верхние)
        DOM.get('first-page-btn').addEventListener('click', () => goToPage(1));
        DOM.get('prev-page-btn').addEventListener('click', () => goToPage(paginationState.currentPage - 1));
        DOM.get('next-page-btn').addEventListener('click', () => goToPage(paginationState.currentPage + 1));
        DOM.get('last-page-btn').addEventListener('click', () => goToPage(paginationState.totalPages));
        
        // Кнопки навигации (нижние)
        DOM.get('first-page-btn-bottom').addEventListener('click', () => goToPage(1));
        DOM.get('prev-page-btn-bottom').addEventListener('click', () => goToPage(paginationState.currentPage - 1));
        DOM.get('next-page-btn-bottom').addEventListener('click', () => goToPage(paginationState.currentPage + 1));
        DOM.get('last-page-btn-bottom').addEventListener('click', () => goToPage(paginationState.totalPages));
        
        // Ввод номера страницы
        const pageInputs = [DOM.get('current-page-input'), DOM.get('current-page-input-bottom')];
        pageInputs.forEach(input => {
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const page = parseInt(this.value);
                    if (page >= 1 && page <= paginationState.totalPages) {
                        goToPage(page);
                    } else {
                        this.value = paginationState.currentPage;
                        Notifications.error(`Страница должна быть от 1 до ${paginationState.totalPages}`);
                    }
                }
            });
            
            input.addEventListener('blur', function() {
                const page = parseInt(this.value);
                if (!page || page < 1 || page > paginationState.totalPages) {
                    this.value = paginationState.currentPage;
                }
            });
        });
    }
    
    function goToPage(page) {
        if (page < 1 || page > paginationState.totalPages) return;
        
        paginationState.currentPage = page;
        fetchSignals();
    }
    
    function updatePaginationUI() {
        // БЛОКИРУЕМ обновление UI если это автообновление
        if (window.isAutoRefreshing) {
            return; // Не обновляем UI при автообновлении
        }
        
        // Не обновляем UI если пагинация скрыта
        if (!paginationState.isVisible) return;
        
        // Обновляем поля ввода страницы
        const pageInputs = [DOM.get('current-page-input'), DOM.get('current-page-input-bottom')];
        pageInputs.forEach(input => {
            if (input) {
                input.value = paginationState.currentPage;
                input.max = paginationState.totalPages;
            }
        });
        
        // Обновляем общее количество страниц
        const totalSpans = [DOM.get('total-pages-span'), DOM.get('total-pages-span-bottom')];
        totalSpans.forEach(span => {
            if (span) {
                span.textContent = `of ${paginationState.totalPages}`;
            }
        });
        
        // Управляем состоянием кнопок
        const prevButtons = [DOM.get('first-page-btn'), DOM.get('prev-page-btn'), 
                           DOM.get('first-page-btn-bottom'), DOM.get('prev-page-btn-bottom')];
        const nextButtons = [DOM.get('next-page-btn'), DOM.get('last-page-btn'),
                           DOM.get('next-page-btn-bottom'), DOM.get('last-page-btn-bottom')];
        
        prevButtons.forEach(btn => {
            if (btn) btn.disabled = !paginationState.hasPrev;
        });
        
        nextButtons.forEach(btn => {
            if (btn) btn.disabled = !paginationState.hasNext;
        });
        
        // Обновляем поле ввода количества строк в настройках
        const rowsInput = DOM.get('rows-per-page-input');
        if (rowsInput) {
            rowsInput.value = paginationState.limit;
        }
    }
    
    // ===== УПРАВЛЕНИЕ ТАБЛИЦЕЙ =====
    
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
                console.log(`➕ Добавлена новая JSON колонка: ${field} (скрыта)`);
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






    // static/js/signals.js
    async function fetchSignals() {
        try {
            // показываем загрузку только при ручных запросах
            if (!window.isAutoRefreshing) {
                setPaginationLoading(true);
            }

            const params = new URLSearchParams(window.location.search);
            params.set('limit', paginationState.limit);
            params.set('page', paginationState.currentPage);

            const data = await API.get("/signals_data?" + params.toString());
            if (data.error) {
                console.error('API Error:', data.error);
                Notifications.error('Ошибка загрузки данных');
                return;
            }

            // обновляем параметры пагинации только при ручных запросах
            if (!window.isAutoRefreshing) {
                paginationState = {
                    currentPage: data.current_page || 1,
                    totalPages: data.total_pages || 1,
                    limit: data.limit || 50,
                    totalCount: data.total_count || 0,
                    hasNext: data.has_next || false,
                    hasPrev: data.has_prev || false
                };
            }

            analyzeAndCreateJsonColumns(data);
            const tableBody = DOM.get("signal-body");
            tableBody.innerHTML = "";

            data.rows.forEach(row => {
                const tr = DOM.create('tr');
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

            applyColumnVisibility();
            updatePaginationUI(); // сама функция игнорирует автообновления
        } catch (error) {
            console.error("Failed to fetch signals:", error);
            Notifications.error("Ошибка загрузки данных сигналов");
        } finally {
            if (!window.isAutoRefreshing) {
                setPaginationLoading(false);
            }
        }
    }









    
    function setCellValue(row, columnKey, data) {
        if (columnKey.startsWith('json_')) {
            const extraDataIndex = data.column_map['extra_data'];
            return getJsonValue(row, columnKey, extraDataIndex);
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
    
    function setPaginationLoading(isLoading) {
        const paginationControls = document.querySelectorAll('.pagination-controls');
        paginationControls.forEach(control => {
            if (isLoading) {
                control.classList.add('pagination-loading');
            } else {
                control.classList.remove('pagination-loading');
            }
        });
    }
    
    // ===== АВТООБНОВЛЕНИЕ =====
    
    function toggleAutoRefresh() {
        autoRefresh = !autoRefresh;
        const btn = DOM.get('refresh-btn');
        
        if (autoRefresh) {
            btn.classList.remove('active');
            startAutoRefresh();
        } else {
            btn.classList.add('active');
            stopAutoRefresh();
        }
    }
    
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(() => {
            // Помечаем что это автообновление
            window.isAutoRefreshing = true;
            
            // При автообновлении остаемся на текущей странице
            fetchSignals().finally(() => {
                // Снимаем флаг после завершения
                window.isAutoRefreshing = false;
            });
        }, 5000);
    }
    
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
    
    // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
    
    function setupEventHandlers() {
        // Кнопка настроек
        document.getElementById('settings-btn').addEventListener('click', function() {
            const panel = document.getElementById('settings-panel');
            const btn = this;
            
            if (panel.style.display === 'none' || panel.style.display === '') {
                panel.style.display = 'block';
                btn.classList.add('active');
            } else {
                panel.style.display = 'none';
                btn.classList.remove('active');
            }
        });
        
        // Кнопка скрытия пагинации
        document.getElementById('toggle-pagination-btn').addEventListener('click', function() {
            const top = document.getElementById('pagination-controls-top');
            const bottom = document.getElementById('pagination-controls-bottom');
            const btn = this;
            
            if (top.style.display === 'none') {
                // Показываем
                top.style.display = 'flex';
                bottom.style.display = 'flex';
                btn.classList.remove('active');
                localStorage.setItem('pagination_visible', 'true');
            } else {
                // Скрываем
                top.style.display = 'none';
                bottom.style.display = 'none';
                btn.classList.add('active');
                localStorage.setItem('pagination_visible', 'false');
            }
        });
        
        // Кнопка автообновления
        const refreshBtn = DOM.get('refresh-btn');
        refreshBtn.addEventListener('click', toggleAutoRefresh);
        
        // Кнопка сброса колонок
        const resetBtn = DOM.get('reset-columns-btn');
        resetBtn.addEventListener('click', resetColumns);
        
        // Кнопка экспорта в Excel
        const exportBtn = DOM.get('export-btn');
        exportBtn.addEventListener('click', exportToExcel);
        
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
        
        // Обработка формы фильтров
        const filterForm = document.querySelector('.filter-form');
        filterForm.addEventListener('submit', function(e) {
            // При применении фильтров сбрасываем на первую страницу
            paginationState.currentPage = 1;
        });
    }
    
    function toggleSettingsPanel() {
        const panel = DOM.get('settings-panel');
        const btn = DOM.get('settings-btn');
        
        if (panel.style.display === 'none' || panel.style.display === '') {
            panel.style.display = 'block';
            btn.classList.add('active');
        } else {
            panel.style.display = 'none';
            btn.classList.remove('active');
        }
    }
    
    // ===== ЭКСПОРТ В EXCEL =====
    
    async function exportToExcel() {
        try {
            Notifications.info('Подготовка Excel файла...');
            
            // Получаем текущие параметры фильтрации
            const params = new URLSearchParams(window.location.search);
            
            // Создаем ссылку для скачивания
            const exportUrl = '/export_excel?' + params.toString();
            
            // Создаем временную ссылку и кликаем по ней
            const link = document.createElement('a');
            link.href = exportUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            Notifications.success('Excel файл скачивается...');
            
        } catch (error) {
            console.error('Ошибка экспорта в Excel:', error);
            Notifications.error('Ошибка экспорта в Excel');
        }
    }
    
    // ===== УТИЛИТЫ =====
    
    function getCellValue(row, columnKey, data) {
        return setCellValue(row, columnKey, data);
    }
    
    // Делаем функции доступными глобально для отладки
    window.SignalsPage = {
        fetchSignals,
        toggleAutoRefresh,
        resetColumns,
        goToPage,
        columnsConfig: () => columnsConfig,
        autoRefresh: () => autoRefresh,
        paginationState: () => paginationState,
        reloadConfig: loadColumnsConfig
    };
});