// ===== ОБЩИЕ ФУНКЦИИ ДЛЯ ВСЕХ СТРАНИЦ =====

/**
 * Утилиты для работы с элементами DOM
 */
const DOM = {
    // Получение элемента по ID
    get: (id) => document.getElementById(id),
    
    // Получение элементов по селектору
    getAll: (selector) => document.querySelectorAll(selector),
    
    // Создание элемента
    create: (tag, className = '', textContent = '') => {
        const el = document.createElement(tag);
        if (className) el.className = className;
        if (textContent) el.textContent = textContent;
        return el;
    },
    
    // Показать/скрыть элемент
    toggle: (element) => {
        if (element.style.display === 'none' || element.style.display === '') {
            element.style.display = 'block';
        } else {
            element.style.display = 'none';
        }
    }
};

/**
 * Утилиты для работы с API
 */
const API = {
    // GET запрос
    get: async (url) => {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    },
    
    // POST запрос
    post: async (url, data = {}) => {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    }
};

/**
 * Утилиты для работы с датой и временем
 */
const DateUtils = {
    format: (dateString) => {
        try {
            if (!dateString) return '';
            
            // Создаем Date объект напрямую - он умеет парсить разные форматы
            const date = new Date(dateString);
            
            if (isNaN(date.getTime())) {
                return dateString;
            }
            
            // Форматируем с миллисекундами в локальном времени браузера
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const seconds = String(date.getSeconds()).padStart(2, '0');
            const milliseconds = String(date.getMilliseconds()).padStart(3, '0');
            
            return `${day}.${month}.${year} ${hours}:${minutes}:${seconds}.${milliseconds}`;
            
        } catch (e) {
            console.error('DateUtils.format error:', e, 'input:', dateString);
            return dateString || '';
        }
    },
    
    today: () => {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }
};

/**
 * Утилиты для уведомлений
 */
const Notifications = {
    // Показать уведомление (можно расширить позже)
    show: (message, type = 'info') => {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // TODO: Можно добавить toast уведомления
    },
    
    success: (message) => Notifications.show(message, 'success'),
    error: (message) => Notifications.show(message, 'error'),
    info: (message) => Notifications.show(message, 'info')
};

/**
 * Утилиты для работы с формами
 */
const Forms = {
    // Получение данных формы как объект
    getData: (formElement) => {
        const formData = new FormData(formElement);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        return data;
    },
    
    // Очистка формы
    clear: (formElement) => {
        formElement.reset();
    },
    
    // Отправка формы через AJAX
    submit: async (formElement, url) => {
        try {
            const data = Forms.getData(formElement);
            return await API.post(url, data);
        } catch (error) {
            Notifications.error('Ошибка отправки формы');
            throw error;
        }
    }
};

/**
 * Общие обработчики событий
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Trading Bot UI загружен');
    
    // Обработчик для кнопок "назад"
    const backButtons = DOM.getAll('.back-btn, [data-action="back"]');
    backButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            if (href && href !== '#') {
                window.location.href = href;
            } else {
                history.back();
            }
        });
    });
    
    // Автофокус на первый инпут в формах
    const firstInput = document.querySelector('input[type="text"], input[type="email"], textarea');
    if (firstInput && !firstInput.hasAttribute('readonly')) {
        firstInput.focus();
    }
});

/**
 * Экспорт для использования в других модулях
 */
window.TradingBotUI = {
    DOM,
    API,
    DateUtils,
    Notifications,
    Forms
};