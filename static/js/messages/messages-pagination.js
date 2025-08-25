// ===== МОДУЛЬ ПАГИНАЦИИ СООБЩЕНИЙ =====

window.MessagesPagination = (function() {
    const { DOM, Notifications } = window.TradingBotUI;
    
    // Состояние пагинации
    let paginationState = {
        currentPage: 1,
        totalPages: 1,
        limit: 50,
        totalCount: 0,
        hasNext: false,
        hasPrev: false,
        isVisible: true
    };
    
    function setupPaginationHandlers() {
        // Настройка количества строк через поле ввода
        const rowsInput = DOM.get('rows-per-page-input');
        const applyBtn = DOM.get('apply-rows-btn');
        
        // Загружаем сохраненное значение из localStorage
        const savedLimit = localStorage.getItem('messages_rows_per_page');
        if (savedLimit) {
            paginationState.limit = parseInt(savedLimit);
            rowsInput.value = paginationState.limit;
        }
        
        applyBtn.addEventListener('click', function() {
            const newLimit = parseInt(rowsInput.value);
            if (newLimit >= 1 && newLimit <= 10000) {
                paginationState.limit = newLimit;
                paginationState.currentPage = 1; // Сбрасываем на первую страницу
                
                // Сохраняем в localStorage
                localStorage.setItem('messages_rows_per_page', newLimit);
                
                window.MessagesTable.fetchMessages();
                Notifications.success(`Установлено ${newLimit} строк на странице`);
            } else {
                Notifications.error('Количество строк должно быть от 1 до 10000');
                rowsInput.value = paginationState.limit;
            }
        });
        
        // Применение по Enter
        rowsInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyBtn.click();
            }
        });
        
        // ОБЪЕДИНЕННЫЕ обработчики для кнопок пагинации
        const buttonHandlers = {
            'first-page-btn': () => goToPage(1),
            'first-page-btn-bottom': () => goToPage(1),
            'prev-page-btn': () => goToPage(paginationState.currentPage - 1),
            'prev-page-btn-bottom': () => goToPage(paginationState.currentPage - 1),
            'next-page-btn': () => goToPage(paginationState.currentPage + 1),
            'next-page-btn-bottom': () => goToPage(paginationState.currentPage + 1),
            'last-page-btn': () => goToPage(paginationState.totalPages),
            'last-page-btn-bottom': () => goToPage(paginationState.totalPages)
        };
        
        // Добавляем обработчики
        Object.entries(buttonHandlers).forEach(([buttonId, handler]) => {
            const button = DOM.get(buttonId);
            if (button) {
                button.addEventListener('click', handler);
            }
        });
        
        // ОБЪЕДИНЕННЫЕ обработчики для полей ввода страницы
        ['current-page-input', 'current-page-input-bottom'].forEach(inputId => {
            const input = DOM.get(inputId);
            if (input) {
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        const page = parseInt(this.value);
                        if (page >= 1 && page <= paginationState.totalPages) {
                            goToPage(page);
                        } else {
                            this.value = paginationState.currentPage;
                            Notifications.error(`Страница должна быть от 1 до ${paginationState.totalPages}`);
                        }
                    }
                });
                
                input.addEventListener('blur', function() {
                    const page = parseInt(this.value);
                    if (!page || page < 1 || page > paginationState.totalPages) {
                        this.value = paginationState.currentPage;
                    }
                });
            }
        });
    }
    
    function goToPage(page) {
        if (page < 1 || page > paginationState.totalPages) return;
        
        paginationState.currentPage = page;
        window.MessagesTable.fetchMessages();
    }
    
    function updatePaginationUI() {
        // ОБЪЕДИНЕНЫ элементы
        const elements = {
            pageInputs: ['current-page-input', 'current-page-input-bottom'],
            totalSpans: ['total-pages-span', 'total-pages-span-bottom'],
            prevButtons: ['first-page-btn', 'prev-page-btn', 'first-page-btn-bottom', 'prev-page-btn-bottom'],
            nextButtons: ['next-page-btn', 'last-page-btn', 'next-page-btn-bottom', 'last-page-btn-bottom']
        };
        
        // Обновляем поля ввода страницы
        elements.pageInputs.forEach(inputId => {
            const input = DOM.get(inputId);
            if (input) {
                input.value = paginationState.currentPage;
                input.max = paginationState.totalPages;
            }
        });
        
        // Обновляем общее количество страниц
        elements.totalSpans.forEach(spanId => {
            const span = DOM.get(spanId);
            if (span) {
                span.textContent = `of ${paginationState.totalPages}`;
            }
        });
        
        // Управляем состоянием кнопок
        elements.prevButtons.forEach(btnId => {
            const btn = DOM.get(btnId);
            if (btn) btn.disabled = !paginationState.hasPrev;
        });
        
        elements.nextButtons.forEach(btnId => {
            const btn = DOM.get(btnId);
            if (btn) btn.disabled = !paginationState.hasNext;
        });
        
        // Обновляем поле ввода количества строк в настройках
        const rowsInput = DOM.get('rows-per-page-input');
        if (rowsInput) {
            rowsInput.value = paginationState.limit;
        }
        
        // Обновляем информацию о количестве записей
        updatePaginationInfo();
    }
    
    function updatePaginationInfo() {
        /**
         * Обновляет информацию о текущих записях (например: "Показано 1-50 из 234")
         */
        const startRecord = ((paginationState.currentPage - 1) * paginationState.limit) + 1;
        const endRecord = Math.min(paginationState.currentPage * paginationState.limit, paginationState.totalCount);
        
        // Можно добавить индикатор количества записей в будущем
        console.log(`📊 Показано записи ${startRecord}-${endRecord} из ${paginationState.totalCount}`);
    }
    
    function setPaginationLoading(isLoading) {
        const paginationControls = document.querySelectorAll('.pagination-controls');
        paginationControls.forEach(control => {
            if (isLoading) {
                control.classList.add('pagination-loading');
            } else {
                control.classList.remove('pagination-loading');
            }
        });
    }
    
    function updatePaginationState(data) {
        paginationState.currentPage = data.current_page || 1;
        paginationState.totalPages = data.total_pages || 1;
        paginationState.limit = data.limit || 50;
        paginationState.totalCount = data.total_count || 0;
        paginationState.hasNext = data.has_next || false;
        paginationState.hasPrev = data.has_prev || false;
        
        // Логируем статистику
        console.log(`📄 Пагинация сообщений: страница ${paginationState.currentPage}/${paginationState.totalPages}, всего ${paginationState.totalCount} записей`);
    }
    
    function resetPagination() {
        /**
         * Сбрасывает пагинацию на первую страницу
         */
        paginationState.currentPage = 1;
        updatePaginationUI();
    }
    
    function getPaginationSummary() {
        /**
         * Возвращает краткую информацию о пагинации
         */
        return {
            currentPage: paginationState.currentPage,
            totalPages: paginationState.totalPages,
            totalCount: paginationState.totalCount,
            limit: paginationState.limit,
            startRecord: ((paginationState.currentPage - 1) * paginationState.limit) + 1,
            endRecord: Math.min(paginationState.currentPage * paginationState.limit, paginationState.totalCount)
        };
    }
    
    // Публичный API модуля
    return {
        setupPaginationHandlers,
        goToPage,
        updatePaginationUI,
        setPaginationLoading,
        updatePaginationState,
        resetPagination,
        getPaginationSummary,
        getState: () => paginationState,
        setState: (state) => { Object.assign(paginationState, state); }
    };
})();