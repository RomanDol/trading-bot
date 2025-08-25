// ===== МОДУЛЬ ЭКСПОРТА СООБЩЕНИЙ В EXCEL =====

window.MessagesExport = (function() {
    const { Notifications } = window.TradingBotUI;
    
    async function exportToExcel() {
        try {
            Notifications.info('Подготовка Excel файла сообщений...');
            
            // Получаем текущие параметры фильтрации
            const params = new URLSearchParams(window.location.search);
            
            // Добавляем информацию о текущих настройках колонок
            const columnsConfig = window.MessagesColumns.getConfig();
            const visibleColumns = Object.entries(columnsConfig)
                .filter(([_, config]) => config.visible)
                .length;
            
            console.log(`📊 Экспорт ${visibleColumns} видимых колонок сообщений`);
            
            // Создаем ссылку для скачивания
            const exportUrl = '/messages/export_excel?' + params.toString();
            
            // Показываем прогресс
            showExportProgress();
            
            // Создаем временную ссылку и кликаем по ней
            const link = document.createElement('a');
            link.href = exportUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Скрываем прогресс через некоторое время
            setTimeout(() => {
                hideExportProgress();
                Notifications.success('Excel файл сообщений скачивается...');
            }, 2000);
            
        } catch (error) {
            console.error('Ошибка экспорта сообщений в Excel:', error);
            hideExportProgress();
            Notifications.error('Ошибка экспорта сообщений в Excel');
        }
    }
    
    function showExportProgress() {
        /**
         * Показывает индикатор прогресса экспорта
         */
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.classList.add('btn--loading');
            exportBtn.setAttribute('data-original-text', exportBtn.textContent);
            exportBtn.textContent = '⏳ Экспорт...';
        }
    }
    
    function hideExportProgress() {
        /**
         * Скрывает индикатор прогресса экспорта
         */
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.classList.remove('btn--loading');
            const originalText = exportBtn.getAttribute('data-original-text');
            if (originalText) {
                exportBtn.textContent = originalText;
                exportBtn.removeAttribute('data-original-text');
            } else {
                exportBtn.textContent = '📊';
            }
        }
    }
    
    async function exportFilteredData(customFilters = {}) {
        /**
         * Экспорт с кастомными фильтрами
         */
        try {
            Notifications.info('Подготовка отфильтрованных данных...');
            
            // Объединяем текущие фильтры с кастомными
            const currentParams = new URLSearchParams(window.location.search);
            const params = new URLSearchParams();
            
            // Добавляем текущие параметры
            for (const [key, value] of currentParams) {
                params.set(key, value);
            }
            
            // Добавляем кастомные фильтры
            Object.entries(customFilters).forEach(([key, value]) => {
                if (value) {
                    params.set(key, value);
                }
            });
            
            const exportUrl = '/messages/export_excel?' + params.toString();
            
            showExportProgress();
            
            const link = document.createElement('a');
            link.href = exportUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            setTimeout(() => {
                hideExportProgress();
                Notifications.success('Отфильтрованные данные экспортированы');
            }, 2000);
            
        } catch (error) {
            console.error('Ошибка экспорта отфильтрованных данных:', error);
            hideExportProgress();
            Notifications.error('Ошибка экспорта данных');
        }
    }
    
    function exportByMessageType(messageType) {
        /**
         * Экспорт сообщений определенного типа
         */
        return exportFilteredData({ type: messageType });
    }
    
    function exportByDateRange(fromDate, toDate) {
        /**
         * Экспорт сообщений за определенный период
         */
        const filters = {};
        if (fromDate) filters.from_date = fromDate;
        if (toDate) filters.to_date = toDate;
        
        return exportFilteredData(filters);
    }
    
    function createExportMenu() {
        /**
         * Создает расширенное меню экспорта (для будущего использования)
         */
        const menu = document.createElement('div');
        menu.className = 'export-menu';
        menu.style.display = 'none';
        menu.innerHTML = `
            <div class="export-menu-content">
                <h4>📊 Параметры экспорта</h4>
                
                <div class="export-option">
                    <label>
                        <input type="radio" name="export-scope" value="current" checked>
                        Текущие данные (с учетом фильтров)
                    </label>
                </div>
                
                <div class="export-option">
                    <label>
                        <input type="radio" name="export-scope" value="all">
                        Все сообщения (без фильтров)
                    </label>
                </div>
                
                <div class="export-option">
                    <label>
                        <input type="radio" name="export-scope" value="custom">
                        Настраиваемый экспорт
                    </label>
                </div>
                
                <div class="export-custom-options" style="display: none;">
                    <h5>Фильтры:</h5>
                    <label>Тип сообщения:</label>
                    <select name="export-type">
                        <option value="">Все типы</option>
                        <option value="STRATEGY_SIGNAL">Сигналы стратегии</option>
                        <option value="BINANCE_API">Binance API</option>
                        <option value="ORDER_TRADE_UPDATE">Обновления ордеров</option>
                        <option value="ACCOUNT_UPDATE">Обновления аккаунта</option>
                    </select>
                    
                    <label>Период:</label>
                    <input type="date" name="export-from-date" placeholder="От">
                    <input type="date" name="export-to-date" placeholder="До">
                </div>
                
                <div class="export-actions">
                    <button class="btn btn--primary" onclick="window.MessagesExport.executeExport()">
                        📊 Экспортировать
                    </button>
                    <button class="btn btn--secondary" onclick="window.MessagesExport.closeExportMenu()">
                        ❌ Отмена
                    </button>
                </div>
            </div>
        `;
        
        // Обработчик для показа кастомных опций
        const customRadio = menu.querySelector('input[value="custom"]');
        const customOptions = menu.querySelector('.export-custom-options');
        
        menu.addEventListener('change', function(e) {
            if (e.target.name === 'export-scope') {
                customOptions.style.display = e.target.value === 'custom' ? 'block' : 'none';
            }
        });
        
        return menu;
    }
    
    function executeExport() {
        /**
         * Выполняет экспорт согласно выбранным параметрам в меню
         */
        const menu = document.querySelector('.export-menu');
        if (!menu) return;
        
        const scope = menu.querySelector('input[name="export-scope"]:checked')?.value;
        
        if (scope === 'all') {
            // Экспорт всех данных
            exportFilteredData({});
        } else if (scope === 'custom') {
            // Кастомный экспорт
            const type = menu.querySelector('select[name="export-type"]')?.value;
            const fromDate = menu.querySelector('input[name="export-from-date"]')?.value;
            const toDate = menu.querySelector('input[name="export-to-date"]')?.value;
            
            const filters = {};
            if (type) filters.type = type;
            if (fromDate) filters.from_date = fromDate;
            if (toDate) filters.to_date = toDate;
            
            exportFilteredData(filters);
        } else {
            // Текущие данные
            exportToExcel();
        }
        
        closeExportMenu();
    }
    
    function openExportMenu() {
        /**
         * Открывает расширенное меню экспорта
         */
        let menu = document.querySelector('.export-menu');
        if (!menu) {
            menu = createExportMenu();
            document.body.appendChild(menu);
        }
        
        menu.style.display = 'block';
    }
    
    function closeExportMenu() {
        /**
         * Закрывает меню экспорта
         */
        const menu = document.querySelector('.export-menu');
        if (menu) {
            menu.style.display = 'none';
        }
    }
    
    function getExportStatistics() {
        /**
         * Возвращает статистику для экспорта
         */
        const paginationSummary = window.MessagesPagination.getPaginationSummary();
        const columnsConfig = window.MessagesColumns.getConfig();
        const visibleColumns = Object.entries(columnsConfig)
            .filter(([_, config]) => config.visible);
        
        return {
            totalRecords: paginationSummary.totalCount,
            visibleColumns: visibleColumns.length,
            currentFilters: new URLSearchParams(window.location.search).toString(),
            exportTimestamp: new Date().toISOString()
        };
    }
    
    // Публичный API модуля
    return {
        exportToExcel,
        exportFilteredData,
        exportByMessageType,
        exportByDateRange,
        openExportMenu,
        closeExportMenu,
        executeExport,
        getExportStatistics,
        showExportProgress,
        hideExportProgress
    };
})();