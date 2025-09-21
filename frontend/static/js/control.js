// ===== JAVASCRIPT ДЛЯ CONTROL PANEL =====

document.addEventListener('DOMContentLoaded', function() {
    if (!window.TradingBotUI) {
        return;
    }
    
    const { DOM, Notifications } = window.TradingBotUI;
    
    const controlForm = DOM.get('control-form');
    if (!controlForm) {
        return;
    }
    const buttons = controlForm.querySelectorAll('button[name="action"]');
    
    // Обработчик отправки формы
    controlForm.addEventListener('submit', function(e) {
        const clickedButton = e.submitter;
        const action = clickedButton.value;
        
        // Показываем состояние загрузки
        setLoadingState(true, action);
        
        // Уведомляем пользователя
        switch(action) {
            case 'start':
                Notifications.info('Запуск сервиса...');
                break;
            case 'stop':
                Notifications.info('Остановка сервиса...');
                break;
            case 'restart':
                Notifications.info('Перезапуск сервиса...');
                break;
            case 'logs':
                Notifications.info('Загрузка логов...');
                break;
        }
    });
    
    // Функция для управления состоянием загрузки
    function setLoadingState(isLoading, action = null) {
        buttons.forEach(button => {
            if (isLoading) {
                button.disabled = true;
                if (button.value === action) {
                    button.classList.add('loading');
                    const originalText = button.textContent;
                    button.setAttribute('data-original-text', originalText);
                    
                    switch(action) {
                        case 'start':
                            button.textContent = '⏳ Starting...';
                            break;
                        case 'stop':
                            button.textContent = '⏳ Stopping...';
                            break;
                        case 'restart':
                            button.textContent = '⏳ Restarting...';
                            break;
                        case 'logs':
                            button.textContent = '⏳ Loading...';
                            break;
                    }
                }
            } else {
                button.disabled = false;
                button.classList.remove('loading');
                const originalText = button.getAttribute('data-original-text');
                if (originalText) {
                    button.textContent = originalText;
                }
            }
        });
    }
    
    // Функция для выполнения действий через AJAX (для будущего использования)
    async function performAction(action) {
        try {
            setLoadingState(true, action);
            
            const formData = new FormData();
            formData.append('action', action);
            
            const response = await fetch('/control', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                Notifications.success(`Действие "${action}" выполнено успешно`);
                // Обновляем страницу для отображения результата
                window.location.reload();
            } else {
                throw new Error('Ошибка сервера');
            }
        } catch (error) {
            Notifications.error(`Ошибка выполнения действия: ${error.message}`);
        } finally {
            setLoadingState(false);
        }
    }
    
    // Автообновление статуса сервиса каждые 10 секунд
    let statusUpdateInterval;
    
    function startStatusUpdates() {
        statusUpdateInterval = setInterval(async () => {
            try {
                const response = await fetch('/control');
                const html = await response.text();
                
                // Парсим HTML для извлечения статуса
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const statusElement = doc.querySelector('.sv_st');
                
                if (statusElement) {
                    const currentStatusElement = document.querySelector('.sv_st');
                    if (currentStatusElement && statusElement.innerHTML !== currentStatusElement.innerHTML) {
                        currentStatusElement.innerHTML = statusElement.innerHTML;
                        Notifications.info('Статус сервиса обновлен');
                    }
                }
            } catch (error) {
                console.error('Ошибка обновления статуса:', error);
            }
        }, 10000);
    }
    
    function stopStatusUpdates() {
        if (statusUpdateInterval) {
            clearInterval(statusUpdateInterval);
        }
    }
    
    // Запускаем автообновление статуса
    startStatusUpdates();
    
    // Останавливаем автообновление при уходе со страницы
    window.addEventListener('beforeunload', stopStatusUpdates);
    
    // Обработка фокуса/потери фокуса окна для оптимизации
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopStatusUpdates();
        } else {
            startStatusUpdates();
        }
    });
    
    console.log('🎛️ Control Panel инициализирован');
});