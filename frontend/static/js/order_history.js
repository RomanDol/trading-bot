// ===== ORDER HISTORY PAGE JAVASCRIPT =====

document.addEventListener('DOMContentLoaded', function() {
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