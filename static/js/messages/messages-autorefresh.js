// ===== МОДУЛЬ АВТООБНОВЛЕНИЯ СООБЩЕНИЙ =====

window.MessagesAutoRefresh = (function() {
    const { DOM } = window.TradingBotUI;
    
    let autoRefresh = true;
    let refreshInterval;
    let refreshIntervalMs = 5000; // 5 секунд по умолчанию
    
    function toggleAutoRefresh() {
        autoRefresh = !autoRefresh;
        const btn = DOM.get('refresh-btn');
        
        if (autoRefresh) {
            btn.classList.remove('active');
            startAutoRefresh();
            console.log('🔄 Автообновление сообщений включено');
        } else {
            btn.classList.add('active');
            stopAutoRefresh();
            console.log('⏸️ Автообновление сообщений отключено');
        }
        
        // Сохраняем состояние в localStorage
        localStorage.setItem('messages_auto_refresh', autoRefresh.toString());
    }
    
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        
        refreshInterval = setInterval(() => {
            // Помечаем что это автообновление
            window.isAutoRefreshing = true;
            
            // При автообновлении остаемся на текущей странице
            window.MessagesTable.fetchMessages().finally(() => {
                // Снимаем флаг после завершения
                window.isAutoRefreshing = false;
            });
        }, refreshIntervalMs);
        
        console.log(`⏰ Автообновление сообщений запущено (${refreshIntervalMs}ms)`);
    }
    
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
            console.log('🛑 Автообновление сообщений остановлено');
        }
    }
    
    function setRefreshInterval(intervalMs) {
        /**
         * Устанавливает интервал автообновления
         */
        if (intervalMs >= 1000 && intervalMs <= 60000) {
            refreshIntervalMs = intervalMs;
            
            // Если автообновление включено, перезапускаем с новым интервалом
            if (autoRefresh) {
                stopAutoRefresh();
                startAutoRefresh();
            }
            
            // Сохраняем в localStorage
            localStorage.setItem('messages_refresh_interval', intervalMs.toString());
            console.log(`⏱️ Интервал автообновления изменен на ${intervalMs}ms`);
        } else {
            console.warn('⚠️ Интервал должен быть от 1 до 60 секунд');
        }
    }
    
    function setupAutoRefreshEvents() {
        // Кнопка автообновления
        const refreshBtn = DOM.get('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', toggleAutoRefresh);
        }
        
        // Загружаем сохраненные настройки
        loadAutoRefreshSettings();
        
        // Останавливаем автообновление при уходе со страницы
        window.addEventListener('beforeunload', stopAutoRefresh);
        
        // Управление автообновлением в зависимости от видимости страницы
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopAutoRefresh();
                console.log('👁️ Страница скрыта - автообновление приостановлено');
            } else if (autoRefresh) {
                startAutoRefresh();
                console.log('👁️ Страница видна - автообновление возобновлено');
            }
        });
        
        // Останавливаем автообновление при потере интернет соединения
        window.addEventListener('online', function() {
            if (autoRefresh && !refreshInterval) {
                startAutoRefresh();
                console.log('🌐 Соединение восстановлено - автообновление возобновлено');
            }
        });
        
        window.addEventListener('offline', function() {
            stopAutoRefresh();
            console.log('📡 Нет соединения - автообновление приостановлено');
        });
    }
    
    function loadAutoRefreshSettings() {
        /**
         * Загружает сохраненные настройки автообновления
         */
        // Загружаем состояние автообновления
        const savedAutoRefresh = localStorage.getItem('messages_auto_refresh');
        if (savedAutoRefresh !== null) {
            autoRefresh = savedAutoRefresh === 'true';
        }
        
        // Загружаем интервал
        const savedInterval = localStorage.getItem('messages_refresh_interval');
        if (savedInterval) {
            const interval = parseInt(savedInterval);
            if (interval >= 1000 && interval <= 60000) {
                refreshIntervalMs = interval;
            }
        }
        
        // Обновляем UI
        const refreshBtn = DOM.get('refresh-btn');
        if (refreshBtn) {
            if (autoRefresh) {
                refreshBtn.classList.remove('active');
            } else {
                refreshBtn.classList.add('active');
            }
        }
        
        console.log(`⚙️ Настройки автообновления загружены: ${autoRefresh ? 'включено' : 'отключено'}, интервал: ${refreshIntervalMs}ms`);
    }
    
    function manualRefresh() {
        /**
         * Ручное обновление данных
         */
        console.log('🔄 Ручное обновление сообщений');
        
        // Временно отключаем флаг автообновления для показа загрузки
        window.isAutoRefreshing = false;
        
        return window.MessagesTable.fetchMessages();
    }
    
    function getRefreshStatus() {
        /**
         * Возвращает текущий статус автообновления
         */
        return {
            isActive: autoRefresh,
            interval: refreshIntervalMs,
            isRunning: refreshInterval !== null,
            nextRefresh: refreshInterval ? Date.now() + refreshIntervalMs : null
        };
    }
    
    function createRefreshIntervalSelector() {
        /**
         * Создает селектор интервала обновления (для будущего использования в настройках)
         */
        const intervals = [
            { value: 1000, label: '1 секунда' },
            { value: 2000, label: '2 секунды' },
            { value: 5000, label: '5 секунд' },
            { value: 10000, label: '10 секунд' },
            { value: 30000, label: '30 секунд' },
            { value: 60000, label: '1 минута' }
        ];
        
        const select = DOM.create('select', 'refresh-interval-select');
        intervals.forEach(interval => {
            const option = DOM.create('option');
            option.value = interval.value;
            option.textContent = interval.label;
            option.selected = interval.value === refreshIntervalMs;
            select.appendChild(option);
        });
        
        select.addEventListener('change', function() {
            const newInterval = parseInt(this.value);
            setRefreshInterval(newInterval);
        });
        
        return select;
    }
    
    // Публичный API модуля
    return {
        toggleAutoRefresh,
        startAutoRefresh,
        stopAutoRefresh,
        setupAutoRefreshEvents,
        manualRefresh,
        setRefreshInterval,
        getRefreshStatus,
        createRefreshIntervalSelector,
        isAutoRefresh: () => autoRefresh,
        setAutoRefresh: (value) => { 
            autoRefresh = value;
            localStorage.setItem('messages_auto_refresh', value.toString());
        }
    };
})();