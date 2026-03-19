// ========== script.js ==========
// ТЕСТОВАЯ ВЕРСИЯ - ПРОВЕРКА ОТОБРАЖЕНИЯ

const App = {
    userId: 'test_user_123',
    userName: 'Александр',

    async init() {
        console.log('🚀 Фреди: инициализация');
        console.log('✅ screenContainer:', document.getElementById('screenContainer'));
        console.log('✅ onboardingScreen1:', document.getElementById('onboardingScreen1'));
        
        // Скрываем шапку чата
        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.style.display = 'none';
        
        // Обновляем имя в левой панели
        const userNameEl = document.getElementById('userName');
        if (userNameEl) userNameEl.textContent = this.userName;
        
        // Показываем первый экран
        this.showOnboardingScreen1();
    },

    showOnboardingScreen1() {
        const template = document.getElementById('onboardingScreen1');
        if (!template) {
            console.error('❌ Шаблон onboardingScreen1 не найден!');
            return;
        }
        
        // Клонируем шаблон
        const clone = document.importNode(template.content, true);
        
        // Подставляем имя
        const nameSpan = clone.querySelector('#userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = this.userName;
        
        // Вставляем в контейнер
        const container = document.getElementById('screenContainer');
        if (!container) {
            console.error('❌ Контейнер screenContainer не найден!');
            return;
        }
        
        container.innerHTML = '';
        container.appendChild(clone);
        
        console.log('✅ Экран 1 отображен');
        
        // Назначаем обработчики
        setTimeout(() => {
            const startBtn = document.getElementById('startTestBtn');
            const whoBtn = document.getElementById('whoAreYouBtn');
            
            if (startBtn) {
                startBtn.addEventListener('click', () => {
                    alert('🚀 Начинаем тест!');
                });
                console.log('✅ startTestBtn найден');
            } else {
                console.error('❌ startTestBtn не найден');
            }
            
            if (whoBtn) {
                whoBtn.addEventListener('click', () => {
                    this.showOnboardingScreen2();
                });
                console.log('✅ whoAreYouBtn найден');
            }
        }, 100);
    },

    showOnboardingScreen2() {
        const template = document.getElementById('onboardingScreen2');
        if (!template) {
            console.error('❌ Шаблон onboardingScreen2 не найден!');
            return;
        }
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        console.log('✅ Экран 2 отображен');
        
        setTimeout(() => {
            const letsGoBtn = document.getElementById('letsGoBtn');
            if (letsGoBtn) {
                letsGoBtn.addEventListener('click', () => {
                    alert('👌 Погнали!');
                });
            }
        }, 100);
    }
};

// Запуск
document.addEventListener('DOMContentLoaded', () => App.init());
