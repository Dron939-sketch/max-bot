// ========== script.js ==========
// Главный файл логики

const App = {
    userId: null,
    userName: 'Загрузка...',
    userData: {},
    userContext: null,
    testProgress: {},

    elements: {},

    async init() {
        console.log('🚀 Фреди: инициализация');
        
        this.cacheElements();
        await this.initUserId();
        await this.checkUserStatus();
        this.setupEventListeners();
    },

    cacheElements() {
        this.elements = {
            chatsPanel: document.getElementById('chatsPanel'),
            chatPanel: document.getElementById('chatPanel'),
            chatHeader: document.getElementById('chatHeader'),
            screenContainer: document.getElementById('screenContainer'),
            userName: document.getElementById('userName'),
            userStatus: document.getElementById('userStatus'),
            mobileMenuBtn: document.getElementById('mobileMenuBtn'),
            chatSearchInput: document.getElementById('chatSearchInput')
        };
    },

    async initUserId() {
        // Пытаемся получить из URL или localStorage
        const urlParams = new URLSearchParams(window.location.search);
        this.userId = urlParams.get('user_id') || urlParams.get('userId') || 
                      localStorage.getItem('fredi_user_id') || 'test_user_123';
        
        localStorage.setItem('fredi_user_id', this.userId);
        console.log('✅ userId:', this.userId);
    },

    async checkUserStatus() {
        try {
            // Получаем статус пользователя с сервера
            const status = await api.getUserStatus(this.userId);
            
            this.userName = status.user_name || 'друг';
            this.userData = status;
            
            // Обновляем имя в левой панели
            if (this.elements.userName) {
                this.elements.userName.textContent = this.userName;
            }
            
            console.log('📊 Статус:', status);
            
            // Определяем, какой экран показать
            if (status.first_visit || !status.context_complete) {
                // Первый вход или контекст не заполнен
                Onboarding.showScreen1(this.userName);
            } else if (!status.test_completed) {
                // Контекст есть, тест не пройден
                // Загружаем контекст
                this.userContext = { city: 'Москва', gender: 'male', age: 35 }; // заглушка
                Context.showCompleteScreen(this.userContext);
            } else {
                // Всё пройдено - показываем чат
                this.showMainChat();
            }
            
        } catch (error) {
            console.error('❌ Ошибка проверки статуса:', error);
            // В случае ошибки показываем онбординг
            Onboarding.showScreen1(this.userName);
        }
    },

    showMainChat() {
        console.log('💬 Показываем основной чат');
        // Здесь будет код для отображения полноценного чата
        // Пока просто заглушка
        this.elements.screenContainer.innerHTML = '<div style="padding: 20px; text-align: center;">Чат с ботом (будет реализован)</div>';
        this.elements.chatHeader.style.display = 'flex';
    },

    setupEventListeners() {
        // Мобильное меню
        if (this.elements.mobileMenuBtn) {
            this.elements.mobileMenuBtn.addEventListener('click', () => {
                this.elements.chatsPanel.classList.toggle('visible');
            });
        }
        
        // Поиск
        if (this.elements.chatSearchInput) {
            this.elements.chatSearchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('.chat-item').forEach(item => {
                    const name = item.querySelector('.chat-name')?.textContent.toLowerCase() || '';
                    item.style.display = name.includes(query) || query === '' ? 'flex' : 'none';
                });
            });
        }
    }
};

// Запуск при загрузке страницы
document.addEventListener('DOMContentLoaded', () => App.init());
