// ===== ORDER HISTORY PAGE JAVASCRIPT =====

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('order-history-form');
    const loadButton = document.getElementById('load-button');
    const message = document.getElementById('message');
    
    // Устанавливаем сегодняшнюю дату по умолчанию
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('end-date').value = today;
    
    // Устанавливаем дату неделю назад для начальной даты
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    document.getElementById('start-date').value = weekAgo.toISOString().split('T')[0];
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        if (!startDate || !endDate) {
            showMessage('Заполните обе даты', 'error');
            return;
        }
        
        if (startDate > endDate) {
            showMessage('Начальная дата не может быть больше конечной', 'error');
            return;
        }
        
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
                  start_date: startDate,
                  end_date: endDate
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