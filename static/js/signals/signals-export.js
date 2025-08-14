// ===== МОДУЛЬ ЭКСПОРТА В EXCEL =====

window.SignalsExport = (function() {
    const { Notifications } = window.TradingBotUI;
    
    async function exportToExcel() {
        try {
            Notifications.info('Подготовка Excel файла...');
            
            // Получаем текущие параметры фильтрации
            const params = new URLSearchParams(window.location.search);
            
            // Создаем ссылку для скачивания
            const exportUrl = '/export_excel?' + params.toString();
            
            // Создаем временную ссылку и кликаем по ней
            const link = document.createElement('a');
            link.href = exportUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            Notifications.success('Excel файл скачивается...');
            
        } catch (error) {
            console.error('Ошибка экспорта в Excel:', error);
            Notifications.error('Ошибка экспорта в Excel');
        }
    }
    
    // Публичный API модуля
    return {
        exportToExcel
    };
})();