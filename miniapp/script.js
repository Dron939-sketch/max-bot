// ========== script.js ==========
// ПОЛНАЯ ВЕРСИЯ С ПРАВИЛЬНОЙ ЛОГИКОЙ

const App = {
    userId: 'test_user_123',
    userName: 'Александр',
    userData: {},
    userContext: null,
    testProgress: {},

    async init() {
        console.log('🚀 Фреди: инициализация');
        
        // Скрываем шапку чата
        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.style.display = 'none';
        
        // Обновляем имя в левой панели
        const userNameEl = document.getElementById('userName');
        if (userNameEl) userNameEl.textContent = this.userName;
        
        // Получаем статус пользователя с сервера
        await this.checkUserStatus();
    },

    async checkUserStatus() {
        try {
            // Здесь должен быть запрос к вашему API
            // Пока используем тестовые данные
            const status = {
                first_visit: true,
                context_complete: false,
                test_completed: false
            };
            
            if (status.first_visit || !status.context_complete) {
                this.showOnboardingScreen1();
            } else if (!status.test_completed) {
                // Контекст есть, тест не пройден
                if (typeof Context !== 'undefined') {
                    Context.showCompleteScreen(this.userContext);
                } else {
                    this.showOnboardingScreen1();
                }
            } else {
                // Всё пройдено - показываем чат
                this.showMainChat();
            }
            
        } catch (error) {
            console.error('Ошибка:', error);
            this.showOnboardingScreen1();
        }
    },

    showOnboardingScreen1() {
        const template = document.getElementById('onboardingScreen1');
        if (!template) {
            console.error('❌ Шаблон onboardingScreen1 не найден!');
            return;
        }
        
        const clone = document.importNode(template.content, true);
        
        const nameSpan = clone.querySelector('#userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = this.userName;
        
        const container = document.getElementById('screenContainer');
        if (!container) {
            console.error('❌ Контейнер screenContainer не найден!');
            return;
        }
        
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            const startBtn = document.getElementById('startTestBtn');
            const whoBtn = document.getElementById('whoAreYouBtn');
            
            if (startBtn) {
                startBtn.addEventListener('click', () => {
                    if (typeof Context !== 'undefined') {
                        Context.startCollection();
                    } else {
                        alert('Функция сбора контекста временно недоступна');
                    }
                });
            }
            
            if (whoBtn) {
                whoBtn.addEventListener('click', () => {
                    this.showOnboardingScreen2();
                });
            }
        }, 100);
    },

    showOnboardingScreen2() {
        const template = document.getElementById('onboardingScreen2');
        if (!template) return;
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            const letsGoBtn = document.getElementById('letsGoBtn');
            if (letsGoBtn) {
                letsGoBtn.addEventListener('click', () => {
                    if (typeof Context !== 'undefined') {
                        Context.startCollection();
                    } else {
                        alert('Начинаем тест!');
                    }
                });
            }
        }, 100);
    },

    showMainChat() {
        console.log('💬 Показываем основной чат');
        document.getElementById('screenContainer').innerHTML = 
            '<div style="padding: 20px; text-align: center;">Чат с ботом будет здесь</div>';
        document.getElementById('chatHeader').style.display = 'flex';
    }
};

// Запуск
document.addEventListener('DOMContentLoaded', () => App.init());
