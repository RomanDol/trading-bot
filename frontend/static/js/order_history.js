// ===== ORDER HISTORY PAGE JAVASCRIPT =====

document.addEventListener('DOMContentLoaded', function() {
    // ===== UPDATE SYMBOLS SECTION =====
    const updateSymbolsBtn = document.getElementById('update-symbols-btn');
    const symbolsMessage = document.getElementById('symbols-message');
    
    if (updateSymbolsBtn) {
        updateSymbolsBtn.addEventListener('click', async function() {
            // Показываем состояние загрузки
            updateSymbolsBtn.disabled = true;
            updateSymbolsBtn.textContent = '⏳ Обновляем...';
            hideSymbolsMessage();
            
            try {
                const response = await fetch('/api/update_symbols', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (response.ok && result.status === 'success') {
                    showSymbolsMessage(result.message || 'Символы успешно обновлены', 'success');
                } else {
                    showSymbolsMessage(result.message || 'Ошибка обновления символов', 'error');
                }
                
            } catch (error) {
                showSymbolsMessage('Ошибка соединения с сервером', 'error');
            } finally {
                updateSymbolsBtn.disabled = false;
                updateSymbolsBtn.textContent = '🔄 Update Symbols List';
            }
        });
    }
    
    function showSymbolsMessage(text, type) {
        symbolsMessage.textContent = text;
        symbolsMessage.className = `message message--${type}`;
        symbolsMessage.style.display = 'block';
    }
    
    function hideSymbolsMessage() {
        symbolsMessage.style.display = 'none';
    }
    
    function getAuthCredentials() {
        // Извлекаем credentials из текущей сессии браузера
        // Браузер автоматически отправляет Basic Auth заголовки
        const auth = document.cookie.split('; ')
            .find(row => row.startsWith('auth='));
        
        if (auth) {
            return auth.split('=')[1];
        }
        
        // Fallback - просим браузер использовать сохраненные credentials
        return '';
    }
    
    // ===== ORDER HISTORY SECTION (существующий код) =====
    const form = document.getElementById('order-history-form');
    const loadButton = document.getElementById('load-button');
    const message = document.getElementById('message');
    
    // Устанавливаем даты по умолчанию
    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(today.getDate() - 7);

    const todayStr = today.toISOString().split('T')[0];
    const weekAgoStr = weekAgo.toISOString().split('T')[0];

    document.getElementById('start-datetime').value = weekAgoStr + 'T00:00';
    document.getElementById('end-datetime').value = todayStr + 'T23:59';
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const startDate = document.getElementById('start-datetime').value;
        const endDate = document.getElementById('end-datetime').value;

        if (!startDate || !endDate) {
            showMessage('Заполните обе даты', 'error');
            return;
        }

        if (startDate > endDate) {
            showMessage('Начальная дата не может быть больше конечной', 'error');
            return;
        }

        // Преобразуем формат для backend
        const formattedStartDate = startDate.replace('T', ' ') + ':00';
        const formattedEndDate = endDate.replace('T', ' ') + ':00';
        
        // Показываем состояние загрузки
        loadButton.disabled = true;
        loadButton.textContent = '⏳ Загружаем...';
        hideMessage();
        
        try {
            const response = await fetch('/api/restore_orders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start_date: formattedStartDate,
                    end_date: formattedEndDate
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showMessage(result.message || 'Ордера успешно загружены', 'success');
            } else {
                showMessage(result.message || 'Ошибка загрузки ордеров', 'error');
            }
            
        } catch (error) {
            showMessage('Ошибка соединения с сервером', 'error');
        } finally {
            loadButton.disabled = false;
            loadButton.textContent = '📥 Загрузить';
        }
    });
    
    function showMessage(text, type) {
        message.textContent = text;
        message.className = `message message--${type}`;
        message.style.display = 'block';
    }
    
    function hideMessage() {
        message.style.display = 'none';
    }
});