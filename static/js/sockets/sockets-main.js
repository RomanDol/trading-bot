// ===== ГЛАВНЫЙ МОДУЛЬ SOCKETS PAGE =====

document.addEventListener('DOMContentLoaded', function() {
    const { DOM } = window.TradingBotUI;
    
    // Инициализация
    function init() {
        window.SocketsColumns.loadColumnsConfig();
        setupEventHandlers();
        window.SocketsPagination.setupPaginationHandlers();
        window.SocketsAutoRefresh.setupAutoRefreshEvents();
        
        // Загружаем состояние пагинации
        const savedVisibility = localStorage.getItem('sockets_pagination_visible');
        if (savedVisibility === 'false') {
            document.getElementById('pagination-controls-top').style.display = 'none';
            document.getElementById('pagination-controls-bottom').style.display = 'none';
            document.getElementById('toggle-pagination-btn').classList.add('active');
        }
        
        window.SocketsColumns.updateColumnsPanel();
        window.SocketsColumns.createTableHeaders();
        window.SocketsTable.fetchSockets();
        
        if (window.SocketsAutoRefresh.isAutoRefresh()) {
            window.SocketsAutoRefresh.startAutoRefresh();
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
                localStorage.setItem('sockets_pagination_visible', 'true');
            } else {
                // Скрываем
                top.style.display = 'none';
                bottom.style.display = 'none';
                btn.classList.add('active');
                localStorage.setItem('sockets_pagination_visible', 'false');
            }
        });
        
        // Кнопка сброса колонок
        const resetBtn = DOM.get('reset-columns-btn');
        resetBtn.addEventListener('click', window.SocketsColumns.resetColumns);
        
        // Кнопка экспорта в Excel
        const exportBtn = DOM.get('export-btn');
        exportBtn.addEventListener('click', window.SocketsExport.exportToExcel);
        
        // Обработка формы фильтров
        const filterForm = document.querySelector('.filter-form');
        filterForm.addEventListener('submit', function(e) {
            // При применении фильтров сбрасываем на первую страницу
            const paginationState = window.SocketsPagination.getState();
            paginationState.currentPage = 1;
            window.SocketsPagination.setState(paginationState);
        });
    }
    
    // Запускаем инициализацию
    init();
    
    // Делаем функции доступными глобально для отладки
    window.SocketsPage = {
        fetchSockets: window.SocketsTable.fetchSockets,
        toggleAutoRefresh: window.SocketsAutoRefresh.toggleAutoRefresh,
        resetColumns: window.SocketsColumns.resetColumns,
        goToPage: window.SocketsPagination.goToPage,
        columnsConfig: () => window.SocketsColumns.getConfig(),
        autoRefresh: () => window.SocketsAutoRefresh.isAutoRefresh(),
        paginationState: () => window.SocketsPagination.getState(),
        reloadConfig: window.SocketsColumns.loadColumnsConfig
    };
});