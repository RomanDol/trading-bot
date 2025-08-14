// ===== ГЛАВНЫЙ МОДУЛЬ SIGNALS PAGE =====

document.addEventListener('DOMContentLoaded', function() {
    const { DOM } = window.TradingBotUI;
    
    // Инициализация
    function init() {
        window.SignalsColumns.loadColumnsConfig();
        setupEventHandlers();
        window.SignalsPagination.setupPaginationHandlers();
        window.SignalsAutoRefresh.setupAutoRefreshEvents();
        
        // Загружаем состояние пагинации
        const savedVisibility = localStorage.getItem('pagination_visible');
        if (savedVisibility === 'false') {
            document.getElementById('pagination-controls-top').style.display = 'none';
            document.getElementById('pagination-controls-bottom').style.display = 'none';
            document.getElementById('toggle-pagination-btn').classList.add('active');
        }
        
        window.SignalsColumns.updateColumnsPanel();
        window.SignalsColumns.createTableHeaders();
        window.SignalsTable.fetchSignals();
        
        if (window.SignalsAutoRefresh.isAutoRefresh()) {
            window.SignalsAutoRefresh.startAutoRefresh();
        }
    }
    
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
        
        // Кнопка сброса колонок
        const resetBtn = DOM.get('reset-columns-btn');
        resetBtn.addEventListener('click', window.SignalsColumns.resetColumns);
        
        // Кнопка экспорта в Excel
        const exportBtn = DOM.get('export-btn');
        exportBtn.addEventListener('click', window.SignalsExport.exportToExcel);
        
        // Обработка формы фильтров
        const filterForm = document.querySelector('.filter-form');
        filterForm.addEventListener('submit', function(e) {
            // При применении фильтров сбрасываем на первую страницу
            const paginationState = window.SignalsPagination.getState();
            paginationState.currentPage = 1;
            window.SignalsPagination.setState(paginationState);
        });
    }
    
    // Запускаем инициализацию
    init();
    
    // Делаем функции доступными глобально для отладки
    window.SignalsPage = {
        fetchSignals: window.SignalsTable.fetchSignals,
        toggleAutoRefresh: window.SignalsAutoRefresh.toggleAutoRefresh,
        resetColumns: window.SignalsColumns.resetColumns,
        goToPage: window.SignalsPagination.goToPage,
        columnsConfig: () => window.SignalsColumns.getConfig(),
        autoRefresh: () => window.SignalsAutoRefresh.isAutoRefresh(),
        paginationState: () => window.SignalsPagination.getState(),
        reloadConfig: window.SignalsColumns.loadColumnsConfig
    };
});