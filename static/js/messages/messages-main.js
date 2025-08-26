// ===== ГЛАВНЫЙ МОДУЛЬ MESSAGES PAGE =====

document.addEventListener('DOMContentLoaded', function() {
    const { DOM } = window.TradingBotUI;
    
    // Инициализация
    function init() {
        console.log('🚀 Инициализация страницы сообщений...');
        
        // Загружаем конфигурацию колонок
        window.MessagesColumns.loadColumnsConfig();
        
        // Настраиваем обработчики событий
        setupEventHandlers();
        
        // Инициализируем модули
        window.MessagesPagination.setupPaginationHandlers();
        window.MessagesAutoRefresh.setupAutoRefreshEvents();
        
        // Загружаем состояние пагинации из localStorage
        loadPaginationVisibility();
        
        // Обновляем UI
        window.MessagesColumns.updateColumnsPanel();
        window.MessagesColumns.createTableHeaders();
        
        // Загружаем данные
        window.MessagesTable.fetchMessages();
        
        // Запускаем автообновление если включено
        if (window.MessagesAutoRefresh.isAutoRefresh()) {
            window.MessagesAutoRefresh.startAutoRefresh();
        }
        
        console.log('✅ Страница сообщений инициализирована');
    }
    
    function setupEventHandlers() {
        // Кнопка настроек
        const settingsBtn = DOM.get('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', function() {
                const panel = DOM.get('settings-panel');
                const btn = this;
                
                if (panel.style.display === 'none' || panel.style.display === '') {
                    panel.style.display = 'block';
                    btn.classList.add('active');
                    console.log('⚙️ Панель настроек сообщений открыта');
                } else {
                    panel.style.display = 'none';
                    btn.classList.remove('active');
                    console.log('⚙️ Панель настроек сообщений закрыта');
                }
            });
        }
        
        // Кнопка скрытия пагинации
        const togglePaginationBtn = DOM.get('toggle-pagination-btn');
        if (togglePaginationBtn) {
            togglePaginationBtn.addEventListener('click', function() {
                togglePaginationVisibility();
            });
        }
        
        // Кнопка сброса колонок
        const resetBtn = DOM.get('reset-columns-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                if (confirm('Сбросить конфигурацию колонок к настройкам по умолчанию?')) {
                    window.MessagesColumns.resetColumns();
                }
            });
        }
        
        // Кнопка экспорта в Excel
        const exportBtn = DOM.get('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function(e) {
                // Проверяем если зажат Shift - открываем расширенное меню
                if (e.shiftKey) {
                    window.MessagesExport.openExportMenu();
                } else {
                    window.MessagesExport.exportToExcel();
                }
            });
            
            // Добавляем tooltip
            exportBtn.title = 'Экспорт в Excel (Shift+Click для расширенных опций)';
        }
       
         const toggleMessageFormatBtn = DOM.get('toggle-message-format-btn');
         if (toggleMessageFormatBtn) {
            toggleMessageFormatBtn.addEventListener('click', function() {
                  window.MessagesTable.toggleMessageFormat();
                  console.log('🔄 Переключен формат отображения сообщений');
            });
         }
        
        // Обработка формы фильтров
        const filterForm = document.querySelector('.filter-form');
        if (filterForm) {
            filterForm.addEventListener('submit', function(e) {
                console.log('🔍 Применение фильтров сообщений');
                
                // При применении фильтров сбрасываем на первую страницу
                const paginationState = window.MessagesPagination.getState();
                paginationState.currentPage = 1;
                window.MessagesPagination.setState(paginationState);
            });
        }
        
        // Горячие клавиши
        setupHotkeys();
        
        // Обработчики для мобильных устройств
        setupMobileHandlers();
    }
    
    function loadPaginationVisibility() {
        /**
         * Загружает состояние видимости пагинации из localStorage
         */
        const savedVisibility = localStorage.getItem('messages_pagination_visible');
        if (savedVisibility === 'false') {
            const topPagination = DOM.get('pagination-controls-top');
            const bottomPagination = DOM.get('pagination-controls-bottom');
            const toggleBtn = DOM.get('toggle-pagination-btn');
            
            if (topPagination) topPagination.style.display = 'none';
            if (bottomPagination) bottomPagination.style.display = 'none';
            if (toggleBtn) toggleBtn.classList.add('active');
            
            console.log('👁️ Пагинация скрыта (из localStorage)');
        }
    }
    
    function togglePaginationVisibility() {
        /**
         * Переключает видимость пагинации
         */
        const topPagination = DOM.get('pagination-controls-top');
        const bottomPagination = DOM.get('pagination-controls-bottom');
        const toggleBtn = DOM.get('toggle-pagination-btn');
        
        if (topPagination && bottomPagination && toggleBtn) {
            if (topPagination.style.display === 'none') {
                // Показываем
                topPagination.style.display = 'flex';
                bottomPagination.style.display = 'flex';
                toggleBtn.classList.remove('active');
                localStorage.setItem('messages_pagination_visible', 'true');
                console.log('👁️ Пагинация показана');
            } else {
                // Скрываем
                topPagination.style.display = 'none';
                bottomPagination.style.display = 'none';
                toggleBtn.classList.add('active');
                localStorage.setItem('messages_pagination_visible', 'false');
                console.log('👁️ Пагинация скрыта');
            }
        }
    }
    
    function setupHotkeys() {
        /**
         * Настраивает горячие клавиши
         */
        document.addEventListener('keydown', function(e) {
            // Игнорируем если фокус в поле ввода
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch(e.key.toLowerCase()) {
                case 'r':
                    // R - обновить данные
                    if (!e.ctrlKey && !e.shiftKey) {
                        e.preventDefault();
                        window.MessagesAutoRefresh.manualRefresh();
                        console.log('⌨️ Горячая клавиша: Обновление данных');
                    }
                    break;
                    
                case 's':
                    // S - показать/скрыть настройки
                    if (!e.ctrlKey && !e.shiftKey) {
                        e.preventDefault();
                        DOM.get('settings-btn')?.click();
                        console.log('⌨️ Горячая клавиша: Настройки');
                    }
                    break;
                    
                case 'e':
                    // E - экспорт (Shift+E для расширенного меню)
                    if (!e.ctrlKey) {
                        e.preventDefault();
                        if (e.shiftKey) {
                            window.MessagesExport.openExportMenu();
                            console.log('⌨️ Горячая клавиша: Расширенный экспорт');
                        } else {
                            window.MessagesExport.exportToExcel();
                            console.log('⌨️ Горячая клавиша: Экспорт');
                        }
                    }
                    break;
                    
                case 'p':
                    // P - показать/скрыть пагинацию
                    if (!e.ctrlKey && !e.shiftKey) {
                        e.preventDefault();
                        togglePaginationVisibility();
                        console.log('⌨️ Горячая клавиша: Пагинация');
                    }
                    break;
                    
                case 'a':
                    // A - переключить автообновление
                    if (!e.ctrlKey && !e.shiftKey) {
                        e.preventDefault();
                        window.MessagesAutoRefresh.toggleAutoRefresh();
                        console.log('⌨️ Горячая клавиша: Автообновление');
                    }
                    break;
            }
        });
        
        console.log('⌨️ Горячие клавиши настроены: R=обновить, S=настройки, E=экспорт, P=пагинация, A=автообновление');
    }
    
    function setupMobileHandlers() {
        /**
         * Настраивает обработчики для мобильных устройств
         */
        // Свайп для обновления данных
        let touchStartY = 0;
        let touchEndY = 0;
        
        document.addEventListener('touchstart', function(e) {
            touchStartY = e.changedTouches[0].screenY;
        });
        
        document.addEventListener('touchend', function(e) {
            touchEndY = e.changedTouches[0].screenY;
            handleSwipe();
        });
        
        function handleSwipe() {
            const swipeDistance = touchStartY - touchEndY;
            const minSwipeDistance = 50;
            
            if (Math.abs(swipeDistance) > minSwipeDistance) {
                // Свайп вниз = обновить данные
                if (swipeDistance < 0 && window.scrollY === 0) {
                    window.MessagesAutoRefresh.manualRefresh();
                    console.log('📱 Свайп: Обновление данных');
                }
            }
        }
    }
    
    function getPageStatus() {
        /**
         * Возвращает текущий статус страницы (для отладки)
         */
        return {
            autoRefresh: window.MessagesAutoRefresh.getRefreshStatus(),
            pagination: window.MessagesPagination.getPaginationSummary(),
            export: window.MessagesExport.getExportStatistics(),
            columns: {
                total: Object.keys(window.MessagesColumns.getConfig()).length,
                visible: Object.values(window.MessagesColumns.getConfig())
                    .filter(config => config.visible).length
            }
        };
    }
    
    function showHelpModal() {
        /**
         * Показывает модальное окно с помощью (для будущего использования)
         */
        const helpContent = `
            <h3>📖 Справка по странице сообщений</h3>
            
            <h4>⌨️ Горячие клавиши:</h4>
            <ul>
                <li><kbd>R</kbd> - Обновить данные</li>
                <li><kbd>S</kbd> - Показать/скрыть настройки</li>
                <li><kbd>E</kbd> - Экспорт в Excel</li>
                <li><kbd>Shift+E</kbd> - Расширенный экспорт</li>
                <li><kbd>P</kbd> - Показать/скрыть пагинацию</li>
                <li><kbd>A</kbd> - Переключить автообновление</li>
            </ul>
            
            <h4>🔍 Фильтрация:</h4>
            <ul>
                <li>Используйте поля фильтров для поиска сообщений</li>
                <li>Доступны фильтры по типу и дате</li>
            </ul>
            
            <h4>📊 Колонки:</h4>
            <ul>
                <li>Настройте видимые колонки в панели настроек</li>
                <li>JSON поля создаются автоматически</li>
            </ul>
        `;
        
        // Здесь можно добавить модальное окно
        console.log('📖 Справка:', helpContent);
    }
    
    // Запускаем инициализацию
    init();
    
    // Делаем функции доступными глобально для отладки
    window.MessagesPage = {
        fetchMessages: window.MessagesTable.fetchMessages,
        toggleAutoRefresh: window.MessagesAutoRefresh.toggleAutoRefresh,
        resetColumns: window.MessagesColumns.resetColumns,
        goToPage: window.MessagesPagination.goToPage,
        exportToExcel: window.MessagesExport.exportToExcel,
        getPageStatus,
        showHelpModal,
        
        // Доступ к модулям
        columns: window.MessagesColumns,
        pagination: window.MessagesPagination,
        autoRefresh: window.MessagesAutoRefresh,
        export: window.MessagesExport,
        json: window.MessagesJSON,
        table: window.MessagesTable
    };
    
    console.log('🌟 Страница сообщений полностью загружена и готова к использованию');
    console.log('💡 Используйте window.MessagesPage для доступа к функциям из консоли');
});