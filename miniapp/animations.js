// ============================================
// АНИМАЦИИ ПОЯВЛЕНИЯ
// Версия 1.3 - Исправлена ошибка setupViewTransitions
// ============================================

class AnimationManager {
    constructor(options = {}) {
        this.options = {
            rootMargin: '0px 0px -50px 0px',
            threshold: 0.1,
            animationDuration: 0.4,
            staggerDelay: 0.05,
            ...options
        };
        
        this.observer = null;
        this.animatedElements = new Map();
        this.animationsInProgress = new Set();
        this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.isInitialized = false;
        
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    init() {
        if (this.isInitialized) return;
        this.isInitialized = true;
        
        console.log('✨ Инициализация менеджера анимаций...');
        
        if (this.isReducedMotion) {
            console.log('⚠️ Уменьшенная анимация (prefers-reduced-motion)');
            return;
        }
        
        try {
            this.setupIntersectionObserver();
            
            // ✅ ПРОВЕРКА: вызываем setupViewTransitions только если метод существует
            if (typeof this.setupViewTransitions === 'function') {
                this.setupViewTransitions();
            } else {
                console.log('ℹ️ View Transitions не настроены (метод setupViewTransisions отсутствует)');
            }
            
            this.injectStyles();
            console.log('✅ Менеджер анимаций готов');
        } catch (error) {
            console.error('❌ Ошибка инициализации анимаций:', error);
        }
    }
    
    // ============================================
    // НАСТРОЙКА VIEW TRANSITIONS API
    // ============================================
    
    setupViewTransitions() {
        // Проверяем, что метод существует и браузер поддерживает View Transitions
        if (typeof document.startViewTransition !== 'function') {
            console.log('⚠️ View Transitions API не поддерживается в этом браузере');
            return;
        }
        
        // Добавляем обработчики для элементов с атрибутом data-transition
        // Используем делегирование событий, чтобы обрабатывать динамически добавленные элементы
        document.body.addEventListener('click', (e) => {
            const transitionElement = e.target.closest('[data-transition]');
            if (transitionElement) {
                e.preventDefault();
                const target = transitionElement.dataset.transition;
                if (target) {
                    document.startViewTransition(() => {
                        window.location.hash = target;
                    });
                }
            }
        });
        
        // Слушаем изменения hash для плавных переходов
        window.addEventListener('hashchange', () => {
            if (document.startViewTransition) {
                document.startViewTransition(() => {
                    this.handleHashChange();
                });
            } else {
                this.handleHashChange();
            }
        });
        
        console.log('✅ View Transitions настроены');
    }
    
    handleHashChange() {
        // Обработка смены хэша
        const hash = window.location.hash.slice(1);
        
        // Проверяем существование нужных функций
        if (hash === 'profile') {
            if (window.dashboard && typeof window.dashboard.renderProfileScreen === 'function') {
                window.dashboard.renderProfileScreen();
            } else if (window.dashboard && typeof window.dashboard.renderProfile === 'function') {
                window.dashboard.renderProfile();
            }
        } else if (hash === 'thoughts') {
            if (window.dashboard && typeof window.dashboard.renderPsychologistThoughtScreen === 'function') {
                window.dashboard.renderPsychologistThoughtScreen();
            } else if (window.dashboard && typeof window.dashboard.renderThoughts === 'function') {
                window.dashboard.renderThoughts();
            }
        } else if (hash === 'goals') {
            if (window.dashboard && typeof window.dashboard.renderGoalsScreen === 'function') {
                window.dashboard.renderGoalsScreen();
            } else if (window.dashboard && typeof window.dashboard.renderGoals === 'function') {
                window.dashboard.renderGoals();
            }
        } else if (hash === 'test') {
            if (window.Test && typeof window.Test.start === 'function') {
                window.Test.start();
            }
        } else if (hash === 'dashboard' || !hash) {
            if (window.dashboard && typeof window.dashboard.renderDashboard === 'function') {
                window.dashboard.renderDashboard();
            }
        }
    }
    
    showDashboardScreen() {
        if (window.dashboard && typeof window.dashboard.renderDashboard === 'function') {
            window.dashboard.renderDashboard();
        }
    }
    
    showProfileScreen() {
        if (window.dashboard && typeof window.dashboard.renderProfileScreen === 'function') {
            window.dashboard.renderProfileScreen();
        } else if (window.dashboard && typeof window.dashboard.renderProfile === 'function') {
            window.dashboard.renderProfile();
        }
    }
    
    showThoughtsScreen() {
        if (window.dashboard && typeof window.dashboard.renderPsychologistThoughtScreen === 'function') {
            window.dashboard.renderPsychologistThoughtScreen();
        } else if (window.dashboard && typeof window.dashboard.renderThoughts === 'function') {
            window.dashboard.renderThoughts();
        }
    }
    
    showGoalsScreen() {
        if (window.dashboard && typeof window.dashboard.renderGoalsScreen === 'function') {
            window.dashboard.renderGoalsScreen();
        } else if (window.dashboard && typeof window.dashboard.renderGoals === 'function') {
            window.dashboard.renderGoals();
        }
    }
    
    showTestScreen() {
        if (window.Test && typeof window.Test.start === 'function') {
            window.Test.start();
        }
    }
    
    // ============================================
    // INJECT CSS СТИЛИ
    // ============================================
    
    injectStyles() {
        // Проверяем, не добавлены ли уже стили
        if (document.getElementById('animation-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'animation-styles';
        style.textContent = `
            /* Базовые анимации */
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @keyframes fadeInDown {
                from {
                    opacity: 0;
                    transform: translateY(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @keyframes fadeInLeft {
                from {
                    opacity: 0;
                    transform: translateX(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes fadeInRight {
                from {
                    opacity: 0;
                    transform: translateX(30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes scaleIn {
                from {
                    opacity: 0;
                    transform: scale(0.9);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }
            
            @keyframes bounceIn {
                0% {
                    opacity: 0;
                    transform: scale(0.3);
                }
                50% {
                    opacity: 1;
                    transform: scale(1.05);
                }
                70% {
                    transform: scale(0.9);
                }
                100% {
                    transform: scale(1);
                }
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-100%);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes rotateIn {
                from {
                    opacity: 0;
                    transform: rotate(-180deg) scale(0.5);
                }
                to {
                    opacity: 1;
                    transform: rotate(0) scale(1);
                }
            }
            
            @keyframes glitchIn {
                0% {
                    opacity: 0;
                    transform: translate(0, 0);
                }
                20% {
                    transform: translate(-2px, 2px);
                }
                40% {
                    transform: translate(2px, -2px);
                }
                60% {
                    transform: translate(-1px, 1px);
                }
                80% {
                    transform: translate(1px, -1px);
                }
                100% {
                    opacity: 1;
                    transform: translate(0, 0);
                }
            }
            
            @keyframes blurIn {
                from {
                    opacity: 0;
                    filter: blur(10px);
                }
                to {
                    opacity: 1;
                    filter: blur(0);
                }
            }
            
            /* Классы анимаций */
            .animate-fade-in { animation: fadeIn 0.4s ease forwards; }
            .animate-fade-in-up { animation: fadeInUp 0.5s cubic-bezier(0.2, 0.9, 0.3, 1.1) forwards; }
            .animate-fade-in-down { animation: fadeInDown 0.5s ease forwards; }
            .animate-fade-in-left { animation: fadeInLeft 0.5s ease forwards; }
            .animate-fade-in-right { animation: fadeInRight 0.5s ease forwards; }
            .animate-scale-in { animation: scaleIn 0.4s cubic-bezier(0.34, 1.2, 0.64, 1) forwards; }
            .animate-bounce-in { animation: bounceIn 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards; }
            .animate-slide-in { animation: slideIn 0.5s ease forwards; }
            .animate-rotate-in { animation: rotateIn 0.5s ease forwards; }
            .animate-glitch-in { animation: glitchIn 0.5s ease forwards; }
            .animate-blur-in { animation: blurIn 0.4s ease forwards; }
            
            /* Задержки */
            .delay-1 { animation-delay: 0.05s; }
            .delay-2 { animation-delay: 0.1s; }
            .delay-3 { animation-delay: 0.15s; }
            .delay-4 { animation-delay: 0.2s; }
            .delay-5 { animation-delay: 0.25s; }
            .delay-6 { animation-delay: 0.3s; }
            .delay-7 { animation-delay: 0.35s; }
            .delay-8 { animation-delay: 0.4s; }
            .delay-9 { animation-delay: 0.45s; }
            .delay-10 { animation-delay: 0.5s; }
            
            /* Анимация при наведении */
            .hover-lift { transition: transform 0.2s ease, box-shadow 0.2s ease; }
            .hover-lift:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2); }
            .hover-scale { transition: transform 0.2s ease; }
            .hover-scale:hover { transform: scale(1.05); }
            .hover-glow { transition: box-shadow 0.2s ease, filter 0.2s ease; }
            .hover-glow:hover { filter: drop-shadow(0 0 8px #248bf2); }
            
            /* Анимация пульсации */
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.9; }
            }
            .animate-pulse { animation: pulse 1.5s ease-in-out infinite; }
            
            /* Анимация для лоадера */
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .animate-spin { animation: spin 1s linear infinite; }
            
            /* Анимация для уведомлений */
            @keyframes slideInRight {
                from { opacity: 0; transform: translateX(100%); }
                to { opacity: 1; transform: translateX(0); }
            }
            .animate-slide-in-right { animation: slideInRight 0.3s ease forwards; }
            
            /* Анимация для модальных окон */
            @keyframes modalIn {
                from { opacity: 0; transform: scale(0.9) translateY(-20px); }
                to { opacity: 1; transform: scale(1) translateY(0); }
            }
            .animate-modal-in { animation: modalIn 0.3s cubic-bezier(0.34, 1.2, 0.64, 1) forwards; }
            
            /* Анимация для перехода между экранами */
            @keyframes screenTransition {
                from { opacity: 0; transform: translateX(20px); }
                to { opacity: 1; transform: translateX(0); }
            }
            .animate-screen-transition { animation: screenTransition 0.3s ease forwards; }
            
            /* Анимация для удаления */
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
            .animate-fade-out { animation: fadeOut 0.3s ease forwards; }
            
            @keyframes slideOutLeft {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(-100%); opacity: 0; }
            }
            .animate-slide-out-left { animation: slideOutLeft 0.3s ease forwards; }
            
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            .animate-slide-out-right { animation: slideOutRight 0.3s ease forwards; }
            
            @keyframes scaleOut {
                from { transform: scale(1); opacity: 1; }
                to { transform: scale(0.8); opacity: 0; }
            }
            .animate-scale-out { animation: scaleOut 0.3s ease forwards; }
            
            /* Состояние до анимации */
            .animation-ready {
                opacity: 0;
                visibility: visible;
            }
            
            .animation-complete {
                opacity: 1;
            }
            
            /* Скелетон для загрузки */
            .skeleton {
                background: linear-gradient(
                    90deg,
                    rgba(255, 255, 255, 0.1) 0%,
                    rgba(255, 255, 255, 0.2) 50%,
                    rgba(255, 255, 255, 0.1) 100%
                );
                background-size: 200% 100%;
                animation: skeletonLoading 1.5s infinite;
                border-radius: 8px;
            }
            
            @keyframes skeletonLoading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    // ============================================
    // INTERSECTION OBSERVER
    // ============================================
    
    setupIntersectionObserver() {
        this.observer = new IntersectionObserver(
            (entries) => this.handleIntersect(entries),
            {
                rootMargin: this.options.rootMargin,
                threshold: this.options.threshold
            }
        );
        
        // Наблюдаем за существующими элементами
        this.observeElements('[data-animate]');
        this.observeElements('.animate-on-scroll');
        
        // Наблюдаем за новыми элементами через MutationObserver
        this.setupMutationObserver();
    }
    
    setupMutationObserver() {
        const mutationObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.observeElements('[data-animate]', node);
                            this.observeElements('.animate-on-scroll', node);
                        }
                    });
                }
            });
        });
        
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    observeElements(selector, context = document) {
        const elements = context.querySelectorAll(selector);
        elements.forEach(el => {
            if (!this.animatedElements.has(el)) {
                this.animatedElements.set(el, {
                    animation: el.dataset.animate || 'fade-in-up',
                    delay: parseFloat(el.dataset.animateDelay) || 0,
                    duration: parseFloat(el.dataset.animateDuration) || this.options.animationDuration,
                    triggered: false
                });
                this.observer.observe(el);
            }
        });
    }
    
    handleIntersect(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const data = this.animatedElements.get(el);
                
                if (data && !data.triggered) {
                    this.animateElement(el, data);
                    data.triggered = true;
                    this.animatedElements.set(el, data);
                    this.observer.unobserve(el);
                }
            }
        });
    }
    
    animateElement(element, config) {
        const animationClass = this.getAnimationClass(config.animation);
        const delay = config.delay || 0;
        const duration = config.duration || this.options.animationDuration;
        
        element.style.opacity = '0';
        element.style.animation = 'none';
        
        // Force reflow
        void element.offsetHeight;
        
        element.style.animation = `${animationClass} ${duration}s cubic-bezier(0.2, 0.9, 0.3, 1.1) forwards`;
        if (delay > 0) {
            element.style.animationDelay = `${delay}s`;
        }
        element.style.opacity = '1';
        
        this.animationsInProgress.add(element);
        
        const onFinish = () => {
            this.animationsInProgress.delete(element);
            element.removeEventListener('animationend', onFinish);
        };
        
        element.addEventListener('animationend', onFinish, { once: true });
    }
    
    getAnimationClass(animationType) {
        const mapping = {
            'fade-in': 'animate-fade-in',
            'fade-in-up': 'animate-fade-in-up',
            'fade-in-down': 'animate-fade-in-down',
            'fade-in-left': 'animate-fade-in-left',
            'fade-in-right': 'animate-fade-in-right',
            'scale-in': 'animate-scale-in',
            'bounce-in': 'animate-bounce-in',
            'slide-in': 'animate-slide-in',
            'rotate-in': 'animate-rotate-in',
            'glitch-in': 'animate-glitch-in',
            'blur-in': 'animate-blur-in'
        };
        
        return mapping[animationType] || 'animate-fade-in-up';
    }
    
    // ============================================
    // МЕТОДЫ ДЛЯ РУЧНОЙ АНИМАЦИИ
    // ============================================
    
    async animateElementNow(element, animationType = 'fade-in-up', duration = 0.4, delay = 0) {
        if (!element) return;
        
        const animationClass = this.getAnimationClass(animationType);
        
        element.style.opacity = '0';
        element.style.animation = 'none';
        
        // Force reflow
        void element.offsetHeight;
        
        element.style.animation = `${animationClass} ${duration}s cubic-bezier(0.2, 0.9, 0.3, 1.1) forwards`;
        if (delay > 0) {
            element.style.animationDelay = `${delay}s`;
        }
        element.style.opacity = '1';
        
        return new Promise(resolve => {
            const onFinish = () => {
                element.removeEventListener('animationend', onFinish);
                resolve();
            };
            element.addEventListener('animationend', onFinish, { once: true });
        });
    }
    
    animateList(items, animationType = 'fade-in-up', staggerDelay = 0.05) {
        const promises = [];
        items.forEach((item, index) => {
            const delay = index * staggerDelay;
            promises.push(this.animateElementNow(item, animationType, 0.4, delay));
        });
        return Promise.all(promises);
    }
    
    // ============================================
    // СТАГГЕР АНИМАЦИЯ ДЛЯ ГРИДОВ
    // ============================================
    
    animateGrid(gridSelector, itemSelector, animationType = 'scale-in') {
        const grid = document.querySelector(gridSelector);
        if (!grid) return;
        
        const items = grid.querySelectorAll(itemSelector);
        this.animateList(Array.from(items), animationType, 0.05);
    }
    
    // ============================================
    // АНИМАЦИЯ ПРИ УДАЛЕНИИ
    // ============================================
    
    async removeWithAnimation(element, animationType = 'fade-out') {
        if (!element) return;
        
        const animationClass = this.getRemoveAnimationClass(animationType);
        element.style.animation = `${animationClass} 0.3s ease forwards`;
        
        await new Promise(resolve => {
            element.addEventListener('animationend', () => {
                if (element.parentNode) {
                    element.remove();
                }
                resolve();
            }, { once: true });
        });
    }
    
    getRemoveAnimationClass(animationType) {
        const mapping = {
            'fade-out': 'animate-fade-out',
            'slide-out-left': 'animate-slide-out-left',
            'slide-out-right': 'animate-slide-out-right',
            'scale-out': 'animate-scale-out'
        };
        
        return mapping[animationType] || 'animate-fade-out';
    }
    
    // ============================================
    // ПЕРЕХОД МЕЖДУ ЭКРАНАМИ
    // ============================================
    
    async transitionScreen(oldScreen, newScreen, direction = 'forward') {
        if (oldScreen) {
            const exitAnimation = direction === 'forward' ? 'slide-out-left' : 'slide-out-right';
            await this.removeWithAnimation(oldScreen, exitAnimation);
        }
        
        if (newScreen) {
            newScreen.classList.add('animate-screen-transition');
        }
        return newScreen;
    }
    
    // ============================================
    // АНИМАЦИЯ ДЛЯ МОДАЛЬНЫХ ОКОН
    // ============================================
    
    async showModal(modalElement) {
        if (!modalElement) return;
        
        modalElement.style.display = 'flex';
        modalElement.classList.add('animate-modal-in');
        
        return new Promise(resolve => {
            modalElement.addEventListener('animationend', () => {
                resolve();
            }, { once: true });
        });
    }
    
    async hideModal(modalElement) {
        if (!modalElement) return;
        
        modalElement.style.animation = 'fade-out 0.2s ease forwards';
        
        return new Promise(resolve => {
            modalElement.addEventListener('animationend', () => {
                modalElement.style.display = 'none';
                modalElement.style.animation = '';
                resolve();
            }, { once: true });
        });
    }
    
    // ============================================
    // ПРОГРЕСС-БАР АНИМАЦИЯ
    // ============================================
    
    animateProgressBar(barElement, targetPercent, duration = 0.8) {
        if (!barElement) return;
        
        const startWidth = parseFloat(barElement.style.width) || 0;
        const diff = targetPercent - startWidth;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = (currentTime - startTime) / 1000;
            const progress = Math.min(1, elapsed / duration);
            const easeOutCubic = 1 - Math.pow(1 - progress, 3);
            const currentWidth = startWidth + diff * easeOutCubic;
            
            barElement.style.width = `${currentWidth}%`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    // ============================================
    // АНИМАЦИЯ ЧИСЕЛ (СЧЁТЧИК)
    // ============================================
    
    animateNumber(element, startValue, endValue, duration = 1, format = (v) => Math.round(v)) {
        if (!element) return;
        
        const startTime = performance.now();
        const diff = endValue - startValue;
        
        const animate = (currentTime) => {
            const elapsed = (currentTime - startTime) / 1000;
            const progress = Math.min(1, elapsed / duration);
            const easeOutCubic = 1 - Math.pow(1 - progress, 3);
            const currentValue = startValue + diff * easeOutCubic;
            
            element.textContent = format(currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    // ============================================
    // СКЕЛЕТОН ДЛЯ ЗАГРУЗКИ
    // ============================================
    
    showSkeleton(container, skeletonTemplate) {
        if (!container) return;
        container.innerHTML = skeletonTemplate;
    }
    
    hideSkeleton(container, content) {
        if (!container) return;
        container.innerHTML = content;
        this.refresh();
    }
    
    // ============================================
    // УТИЛИТЫ
    // ============================================
    
    refresh() {
        this.observeElements('[data-animate]');
        this.observeElements('.animate-on-scroll');
    }
    
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
        this.animatedElements.clear();
        this.animationsInProgress.clear();
        console.log('🗑️ Менеджер анимаций уничтожен');
    }
}

// ============================================
// КЛАСС ДЛЯ СТАГГЕР-АНИМАЦИЙ
// ============================================

class StaggerAnimation {
    constructor(containerSelector, itemSelector, options = {}) {
        this.container = document.querySelector(containerSelector);
        this.itemSelector = itemSelector;
        this.items = this.container ? Array.from(this.container.querySelectorAll(itemSelector)) : [];
        this.options = {
            animation: 'fade-in-up',
            staggerDelay: 0.05,
            duration: 0.4,
            ...options
        };
    }
    
    async play() {
        for (let i = 0; i < this.items.length; i++) {
            const item = this.items[i];
            const delay = i * this.options.staggerDelay;
            
            await new Promise(resolve => {
                setTimeout(() => {
                    this.animateItem(item);
                    resolve();
                }, delay * 1000);
            });
        }
    }
    
    animateItem(item) {
        const animationClass = this.getAnimationClass();
        item.style.opacity = '0';
        item.style.animation = `${animationClass} ${this.options.duration}s cubic-bezier(0.2, 0.9, 0.3, 1.1) forwards`;
        item.style.opacity = '1';
    }
    
    getAnimationClass() {
        const mapping = {
            'fade-in': 'animate-fade-in',
            'fade-in-up': 'animate-fade-in-up',
            'scale-in': 'animate-scale-in',
            'bounce-in': 'animate-bounce-in'
        };
        return mapping[this.options.animation] || 'animate-fade-in-up';
    }
    
    refresh() {
        if (this.container) {
            this.items = Array.from(this.container.querySelectorAll(this.itemSelector));
        }
    }
}

// ============================================
// ГЛОБАЛЬНЫЙ ЭКСПОРТ
// ============================================

window.AnimationManager = AnimationManager;
window.StaggerAnimation = StaggerAnimation;

console.log('✅ Модуль анимаций загружен (версия 1.3)');
