// ===== МОДУЛЬ АВТООБНОВЛЕНИЯ =====

window.SignalsAutoRefresh = (function() {
    const { DOM } = window.TradingBotUI;
    
    let autoRefresh = true;
    let refreshInterval;
    
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
            window.SignalsTable.fetchSignals().finally(() => {
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
    
    function setupAutoRefreshEvents() {
        // Кнопка автообновления
        const refreshBtn = DOM.get('refresh-btn');
        refreshBtn.addEventListener('click', toggleAutoRefresh);
        
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
    }
    
    // Публичный API модуля
    return {
        toggleAutoRefresh,
        startAutoRefresh,
        stopAutoRefresh,
        setupAutoRefreshEvents,
        isAutoRefresh: () => autoRefresh,
        setAutoRefresh: (value) => { autoRefresh = value; }
    };
})();