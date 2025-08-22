// ===== МОДУЛЬ ЭКСПОРТА СОКЕТОВ В EXCEL =====

window.SocketsExport = (function() {
    const { Notifications } = window.TradingBotUI;
    
    async function exportToExcel() {
        try {
            Notifications.info('Подготовка Excel файла сокетов...');
            
            // Получаем текущие параметры фильтрации
            const params = new URLSearchParams(window.location.search);
            
            // Создаем ссылку для скачивания
            const exportUrl = '/sockets/export_excel?' + params.toString();
            
            // Создаем временную ссылку и кликаем по ней
            const link = document.createElement('a');
            link.href = exportUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            Notifications.success('Excel файл сокетов скачивается...');
            
        } catch (error) {
            console.error('Ошибка экспорта сокетов в Excel:', error);
            Notifications.error('Ошибка экспорта сокетов в Excel');
        }
    }
    
    // Публичный API модуля
    return {
        exportToExcel
    };
})();