// ===== НАВИГАЦИЯ ===== 

document.addEventListener('DOMContentLoaded', function() {
    const burgerBtn = document.getElementById('burger-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const body = document.body;
    
    // Переключение мобильного меню
    function toggleMobileMenu() {
        const isOpen = mobileMenu.classList.contains('open');
        
        if (isOpen) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }
    
    function openMobileMenu() {
        mobileMenu.classList.add('open');
        burgerBtn.classList.add('active');
        body.classList.add('menu-open');
    }
    
    function closeMobileMenu() {
        mobileMenu.classList.remove('open');
        burgerBtn.classList.remove('active');
        body.classList.remove('menu-open');
    }
    
    // Обработчики событий
    if (burgerBtn) {
        burgerBtn.addEventListener('click', toggleMobileMenu);
    }
    
    // Закрытие меню при клике на пункт меню (только активные ссылки)
    const mobileNavItems = document.querySelectorAll('.mobile-nav-item:not(.disabled)');
    mobileNavItems.forEach(item => {
        item.addEventListener('click', () => {
            closeMobileMenu();
        });
    });
    
    // Закрытие меню при клике вне меню
    if (mobileMenu) {
        mobileMenu.addEventListener('click', function(e) {
            if (e.target === mobileMenu) {
                closeMobileMenu();
            }
        });
    }
    
    // Закрытие меню при нажатии Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
            closeMobileMenu();
        }
    });
    
    // Закрытие меню при изменении размера экрана (если перешли на desktop)
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && mobileMenu.classList.contains('open')) {
            closeMobileMenu();
        }
    });
    
    // Предотвращение скролла body когда меню открыто
    let scrollPosition = 0;
    
    const originalOpenMobileMenu = openMobileMenu;
    const originalCloseMobileMenu = closeMobileMenu;
    
    openMobileMenu = function() {
        scrollPosition = window.pageYOffset;
        body.style.position = 'fixed';
        body.style.top = `-${scrollPosition}px`;
        body.style.width = '100%';
        originalOpenMobileMenu();
    };
    
    closeMobileMenu = function() {
        body.style.position = '';
        body.style.top = '';
        body.style.width = '';
        window.scrollTo(0, scrollPosition);
        originalCloseMobileMenu();
    };
    
    console.log('🧭 Навигация инициализирована');
});