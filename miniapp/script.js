// ========== script.js ==========
// ПОЛНАЯ ВЕРСИЯ МИНИ-ПРИЛОЖЕНИЯ
// С ПРОВЕРКОЙ ПРОФИЛЯ ПРИ ВХОДЕ + ГОЛОСОВЫЕ СООБЩЕНИЯ + ТЕСТ

const App = {
    userId: null,
    userName: 'Загрузка...',
    userData: {},
    userContext: {
        city: null,
        gender: null,
        age: null
    },
    testProgress: {},
    profileData: null,
    currentMode: 'coach',
    psychologistThought: null,
    currentGoals: [],
    recognition: null,
    smartQuestions: [],
    isRecording: false,

    // ========== ИНИЦИАЛИЗАЦИЯ ==========
    async init() {
        console.log('🚀 Фреди: инициализация');
        
        // 🔥 ПОЛУЧАЕМ USER_ID ИЗ maxContext (устанавливается в index.html)
        if (window.maxContext && window.maxContext.user_id) {
            this.userId = window.maxContext.user_id;
            console.log('👤 Получен ID от MAX:', this.userId);
        }
        
        // Если нет из maxContext, пробуем из localStorage
        if (!this.userId) {
            const savedUserId = localStorage.getItem('fredi_user_id');
            if (savedUserId) {
                this.userId = savedUserId;
                console.log('💾 Загружен user_id из localStorage:', this.userId);
            }
        }
        
        // Если нет user_id — показываем ошибку и не продолжаем
if (!this.userId) {
    console.error('❌ Нет user_id! Приложение должно открываться через MAX.');
    const container = document.getElementById('screenContainer');
    if (container) {
        container.innerHTML = `
            <div class="login-screen">
                <div class="login-icon">🔐</div>
                <div class="login-title">Ошибка входа</div>
                <div class="login-text">
                    Не удалось идентифицировать пользователя.<br>
                    Пожалуйста, откройте приложение через MAX.
                </div>
                <button class="login-btn" onclick="location.reload()">🔄 ПОВТОРИТЬ</button>
            </div>
        `;
    }
    return;
}
        
        // Сохраняем в localStorage
        localStorage.setItem('fredi_user_id', this.userId);
        
        // Загружаем сохраненное имя
        this.loadUserName();
        
        // Скрываем шапку чата
        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.style.display = 'none';
        
        // Обновляем имя в левой панели
        this.updateUserNameInUI();
        
        // Загружаем данные пользователя с сервера
        await this.loadUserDataFromServer();
        
        // Получаем статус пользователя
        await this.checkUserStatus();
        
        // Показываем модальное окно для ввода имени если нужно
        this.checkAndShowNameModal();
        
        // Добавляем обработчики для левой панели
        this.setupEventListeners();
        
        // Инициализируем Web Speech API
        this.initSpeechRecognition();
        
        // 🔥 ОПОВЕЩАЕМ MAX, ЧТО ПРИЛОЖЕНИЕ ЗАГРУЖЕНО
        if (window.MAX && window.MAX.WebApp) {
            window.MAX.WebApp.ready();
            window.MAX.WebApp.expand();
        }
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
    },
    
    // ========== ЗАГРУЗКА ДАННЫХ С СЕРВЕРА ==========
    async loadUserDataFromServer() {
        try {
            const status = await this.apiCall('/api/user-status', {
                user_id: this.userId
            });
            
            if (status.success) {
                if (status.profile_data) {
                    this.profileData = status.profile_data;
                    console.log('📊 Загружен профиль:', this.profileData);
                }
                if (status.communication_mode) {
                    this.currentMode = status.communication_mode;
                }
                if (status.user_name) {
                    this.userName = status.user_name;
                    this.saveUserName(status.user_name);
                }
            }
        } catch (error) {
            console.warn('Ошибка загрузки данных с сервера:', error);
        }
    },
    
    // ========== API ВЫЗОВЫ (ИСПРАВЛЕНО) ==========
async apiCall(endpoint, params = {}, method = 'GET') {
    // ✅ ИСПРАВЛЕНО: используем window.API_BASE_URL из конфигурации
    const baseUrl = window.API_BASE_URL || '';
    
    // Формируем полный URL
    let url;
    if (baseUrl) {
        url = `${baseUrl}${endpoint}`;
    } else {
        url = new URL(endpoint, window.location.origin).toString();
    }
    
    // Добавляем параметры для GET
    if (method === 'GET' && Object.keys(params).length > 0) {
        const urlObj = new URL(url);
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                urlObj.searchParams.append(key, params[key]);
            }
        });
        url = urlObj.toString();
    }
    
    const options = {
        method: method,
        headers: { 'Content-Type': 'application/json' }
    };
    
    if (method !== 'GET' && Object.keys(params).length > 0) {
        options.body = JSON.stringify(params);
    }
    
    console.log(`📡 API ${method} ${url}`);
    
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (!response.ok) {
            console.error(`HTTP Error ${response.status}:`, data);
            return { success: false, error: data.error || `HTTP ${response.status}` };
        }
        
        return data;
    } catch (error) {
        console.error(`API Error ${endpoint}:`, error);
        return { success: false, error: error.message };
    }
},

async sendQuestionToServer(question) {
    return this.apiCall('/api/chat/message', {
        user_id: this.userId,
        message: question,
        mode: this.currentMode
    }, 'POST');
},

async saveModeToServer(mode) {
    return this.apiCall('/api/save-mode', {
        user_id: this.userId,
        mode: mode
    }, 'POST');
},

async getPsychologistThoughtFromServer() {
    const response = await this.apiCall('/api/thought', {
        user_id: this.userId
    });
    return response.thought;
},

async getSmartQuestionsFromServer() {
    const response = await this.apiCall('/api/smart-questions', {
        user_id: this.userId
    });
    return response.questions || [];
},
    
    // ========== УПРАВЛЕНИЕ ИМЕНЕМ ==========
    loadUserName() {
        const savedName = localStorage.getItem('userName');
        
        if (savedName && savedName !== 'Гость') {
            this.userName = savedName;
        } else if (window.maxContext?.user_name) {
            this.userName = window.maxContext.user_name;
            localStorage.setItem('userName', this.userName);
        } else {
            this.userName = 'Гость';
        }
    },
    
    saveUserName(name) {
        if (name && name.trim() !== '') {
            const trimmedName = name.trim();
            this.userName = trimmedName;
            localStorage.setItem('userName', trimmedName);
            this.updateUserNameInUI();
            return true;
        }
        return false;
    },
    
    updateUserNameInUI() {
        const userNameEl = document.getElementById('userName');
        if (userNameEl) userNameEl.textContent = this.userName;
        
        const userStatus = document.getElementById('userStatus');
        if (userStatus) {
            userStatus.textContent = this.userName === 'Гость' ? '👤 войдите' : '🧠 онлайн';
        }
        
        const nameSpan = document.getElementById('userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = this.userName;
        
        const goalUserName = document.getElementById('goalUserName');
        if (goalUserName) goalUserName.textContent = this.userName;
        
        const avatarImg = document.getElementById('userAvatar');
        if (avatarImg) {
            const firstLetter = this.userName.charAt(0).toUpperCase();
            avatarImg.src = `https://ui-avatars.com/api/?name=${firstLetter}&background=248bf2&color=fff&size=64`;
        }
    },
    
    showNameModal() {
        const oldModal = document.getElementById('nameModal');
        if (oldModal) oldModal.remove();
        
        const modal = document.createElement('div');
        modal.id = 'nameModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content glass-panel">
                <h2 class="modal-title">👋 Как вас зовут?</h2>
                <p class="modal-subtitle">Введите ваше имя для персонализации</p>
                <div class="input-group">
                    <input type="text" id="userNameInput" class="modal-input" placeholder="Ваше имя" maxlength="30">
                    <button onclick="App.handleNameSubmit()" class="modal-btn primary">Сохранить</button>
                </div>
                <button onclick="App.closeNameModal()" class="modal-btn secondary">Позже</button>
            </div>
        `;
        
        if (!document.getElementById('modalStyles')) {
            const style = document.createElement('style');
            style.id = 'modalStyles';
            style.textContent = `
                .modal {
                    display: flex;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.7);
                    backdrop-filter: blur(5px);
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }
                .modal-content {
                    width: 90%;
                    max-width: 320px;
                    padding: 24px;
                    border-radius: 30px;
                    text-align: center;
                    background: var(--max-panel-bg);
                    border: 1px solid var(--glass-border);
                }
                .modal-title {
                    font-size: 24px;
                    margin-bottom: 8px;
                    color: var(--max-text);
                }
                .modal-subtitle {
                    color: var(--max-text-secondary);
                    margin-bottom: 20px;
                }
                .modal-input {
                    flex: 1;
                    padding: 12px 16px;
                    background: var(--glass-bg);
                    border: 1px solid var(--glass-border);
                    border-radius: 30px;
                    color: var(--max-text);
                }
                .modal-btn {
                    width: 100%;
                    padding: 12px;
                    border-radius: 30px;
                    cursor: pointer;
                    margin-bottom: 8px;
                }
                .modal-btn.primary { background: var(--max-blue); color: white; }
                .modal-btn.secondary { background: transparent; color: var(--max-text); border: 1px solid var(--glass-border); }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(modal);
        setTimeout(() => document.getElementById('userNameInput')?.focus(), 100);
    },
    
    handleNameSubmit() {
        const input = document.getElementById('userNameInput');
        if (!input) return;
        const name = input.value.trim();
        if (name) {
            this.saveUserName(name);
            this.closeNameModal();
        } else {
            alert('Пожалуйста, введите ваше имя');
        }
    },
    
    closeNameModal() {
        const modal = document.getElementById('nameModal');
        if (modal) modal.remove();
    },
    
    checkAndShowNameModal() {
        const savedName = localStorage.getItem('userName');
        if (!savedName || savedName === 'Гость') {
            setTimeout(() => this.showNameModal(), 1500);
        }
    },
    
    // ========== ПРОВЕРКА СТАТУСА ==========
    async checkUserStatus() {
        if (this.profileData) {
            await this.showFinalProfile();
            return;
        }
        
        const hasContext = this.userContext.city || this.userContext.gender || this.userContext.age;
        if (!hasContext) {
            this.showOnboardingScreen1();
        } else {
            this.showCompleteScreen();
        }
    },
    
    // ========== ЭКРАНЫ ОНБОРДИНГА И КОНТЕКСТА ==========
    showOnboardingScreen1() {
        const template = document.getElementById('onboardingScreen1');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        const nameSpan = clone.querySelector('#userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = this.userName;
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            document.getElementById('startTestBtn')?.addEventListener('click', () => this.showContextScreen('city'));
            document.getElementById('whoAreYouBtn')?.addEventListener('click', () => this.showOnboardingScreen2());
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
            document.getElementById('letsGoBtn')?.addEventListener('click', () => this.showContextScreen('city'));
        }, 100);
    },
    
    showContextScreen(type) {
        const templates = {
            city: 'contextCityScreen',
            gender: 'contextGenderScreen',
            age: 'contextAgeScreen'
        };
        const template = document.getElementById(templates[type] || 'contextCityScreen');
        if (!template) return;
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            if (type === 'city') {
                const submitBtn = document.getElementById('submitCityBtn');
                const input = document.getElementById('cityInput');
                const skipBtn = document.getElementById('skipContextBtn');
                submitBtn?.addEventListener('click', () => {
                    const city = input?.value.trim();
                    if (city) {
                        this.userContext.city = city;
                        this.showContextScreen('gender');
                    } else alert('Введите название города');
                });
                input?.addEventListener('keypress', e => { if (e.key === 'Enter') submitBtn?.click(); });
                skipBtn?.addEventListener('click', () => this.showContextScreen('gender'));
            }
            
            if (type === 'gender') {
                document.getElementById('genderMaleBtn')?.addEventListener('click', () => {
                    this.userContext.gender = 'male';
                    this.showContextScreen('age');
                });
                document.getElementById('genderFemaleBtn')?.addEventListener('click', () => {
                    this.userContext.gender = 'female';
                    this.showContextScreen('age');
                });
                document.getElementById('skipGenderBtn')?.addEventListener('click', () => this.showContextScreen('age'));
            }
            
            if (type === 'age') {
                const submitBtn = document.getElementById('submitAgeBtn');
                const input = document.getElementById('ageInput');
                const skipBtn = document.getElementById('skipAgeBtn');
                submitBtn?.addEventListener('click', () => {
                    const age = parseInt(input?.value);
                    if (age && age > 0 && age < 120) {
                        this.userContext.age = age;
                        this.showCompleteScreen();
                    } else alert('Введите корректный возраст');
                });
                input?.addEventListener('keypress', e => { if (e.key === 'Enter') submitBtn?.click(); });
                skipBtn?.addEventListener('click', () => this.showCompleteScreen());
            }
        }, 100);
    },
    
    showCompleteScreen() {
        const template = document.getElementById('contextCompleteScreen');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        
        const citySpan = clone.querySelector('#infoCity');
        if (citySpan) citySpan.textContent = this.userContext.city || 'не указан';
        const genderSpan = clone.querySelector('#infoGender');
        if (genderSpan) {
            let genderText = 'не указан';
            if (this.userContext.gender === 'male') genderText = 'Мужчина';
            if (this.userContext.gender === 'female') genderText = 'Женщина';
            genderSpan.textContent = genderText;
        }
        const ageSpan = clone.querySelector('#infoAge');
        if (ageSpan) ageSpan.textContent = this.userContext.age || 'не указан';
        const weatherSpan = clone.querySelector('#infoWeather');
        if (weatherSpan) weatherSpan.style.display = 'none';
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            document.getElementById('startRealTestBtn')?.addEventListener('click', () => {
                if (typeof Test !== 'undefined') {
                    Test.init(this.userId);
                    Test.start();
                } else alert('Тест будет запущен!');
            });
            document.getElementById('whatTestGivesBtn')?.addEventListener('click', () => this.showBenefitsScreen());
            document.getElementById('askQuestionPreBtn')?.addEventListener('click', () => this.showMainChat());
        }, 100);
    },
    
    showBenefitsScreen() {
        const template = document.getElementById('benefitsScreen');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        setTimeout(() => {
            document.getElementById('startTestFromBenefitsBtn')?.addEventListener('click', () => {
                if (typeof Test !== 'undefined') {
                    Test.init(this.userId);
                    Test.start();
                } else alert('Тест будет запущен!');
            });
            document.getElementById('backToContextBtn')?.addEventListener('click', () => this.showCompleteScreen());
        }, 100);
    },
    
    // ========== ЭКРАНЫ ПОСЛЕ ТЕСТА ==========
    async showFinalProfile() {
        console.log('📊 Показываем финальный профиль');
        const template = document.getElementById('finalProfileScreen');
        if (!template) return;
        
        const clone = document.importNode(template.content, true);
        const profileTextDiv = clone.querySelector('#profileText');
        
        if (this.profileData) {
            const profileCode = this.profileData.display_name || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
            const scores = this.profileData.scores || {};
            profileTextDiv.innerHTML = `
                <div class="profile-section"><h3>🧠 Твой профиль: ${profileCode}</h3></div>
                <div class="profile-section"><h4>🎭 Восприятие</h4><p>${this.getPerceptionDescription()}</p></div>
                <div class="profile-section"><h4>💭 Мышление</h4><p>${this.getThinkingDescription()}</p></div>
                <div class="profile-section"><h4>⚡ Поведение</h4><p>${this.getBehaviorDescription(scores)}</p></div>
                <div class="profile-section"><h4>🎯 Точка роста</h4><p>${this.getGrowthPoint(scores)}</p></div>
            `;
        } else {
            profileTextDiv.innerHTML = `<p>🧠 Психологический портрет формируется...</p><p>Пройдите тест, чтобы получить полный анализ.</p>`;
        }
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.style.display = 'flex';
        
        const botStatus = document.getElementById('botStatus');
        if (botStatus) {
            const modeNames = { coach: '🔮 коуч', psychologist: '🧠 психолог', trainer: '⚡ тренер' };
            botStatus.textContent = modeNames[this.currentMode] || '🧠 психолог';
        }
        
        setTimeout(() => {
            document.getElementById('psychologistThoughtBtn')?.addEventListener('click', () => this.showPsychologistThought());
            document.getElementById('askQuestionBtn')?.addEventListener('click', () => this.showAskQuestionScreen());
            document.getElementById('chooseGoalBtn')?.addEventListener('click', () => this.showChooseGoalScreen());
            document.getElementById('chooseModeBtn')?.addEventListener('click', () => this.showChooseModeScreen());
            
            const smartQuestionsBtn = document.createElement('button');
            smartQuestionsBtn.className = 'onboarding-btn secondary';
            smartQuestionsBtn.textContent = '❓ УМНЫЕ ВОПРОСЫ';
            smartQuestionsBtn.addEventListener('click', () => this.showSmartQuestions());
            document.querySelector('.profile-buttons')?.appendChild(smartQuestionsBtn);
        }, 100);
    },
    
    getPerceptionDescription() {
        const perceptionType = this.profileData?.perception_type || 'СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ';
        const descriptions = {
            'СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ': 'Ты тонко чувствуешь настроение окружающих. Часто ориентируешься на мнение других.',
            'ИНТРОВЕРТИРОВАННЫЙ': 'Твой внутренний мир богаче внешнего. Ты много рефлексируешь, анализируешь.',
            'СИМВОЛИЧЕСКИЙ': 'Ты видишь знаки и смыслы там, где другие видят случайности.',
            'МАТЕРИАЛИСТИЧНЫЙ': 'Ты ценишь факты, доказательства, практичность.'
        };
        return descriptions[perceptionType] || descriptions['СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ'];
    },
    
    getThinkingDescription() {
        const thinkingLevel = this.profileData?.thinking_level || 5;
        if (thinkingLevel <= 3) return 'Ты склонен к быстрым, интуитивным решениям.';
        if (thinkingLevel <= 6) return 'Ты умеешь анализировать, видишь причинно-следственные связи.';
        return 'Твоё мышление системное, ты видишь сложные взаимосвязи.';
    },
    
    getBehaviorDescription(scores) {
        const sb = scores['СБ'] || 3;
        const tf = scores['ТФ'] || 3;
        const ub = scores['УБ'] || 3;
        const chv = scores['ЧВ'] || 3;
        let desc = '';
        if (sb <= 2) desc += '• Давление выбивает из колеи. ';
        else if (sb >= 4) desc += '• Спокоен под давлением. ';
        if (tf <= 2) desc += '• С деньгами сложно. ';
        else if (tf >= 4) desc += '• Деньги — инструмент. ';
        if (ub <= 2) desc += '• Мир кажется хаотичным. ';
        else if (ub >= 4) desc += '• Видишь системность. ';
        if (chv <= 2) desc += '• Отношения напрягают. ';
        else if (chv >= 4) desc += '• Ценишь людей. ';
        return desc || 'Сбалансированный профиль, есть куда расти.';
    },
    
    getGrowthPoint(scores) {
        const vectors = ['СБ', 'ТФ', 'УБ', 'ЧВ'];
        let minVector = 'СБ';
        let minValue = 5;
        for (const v of vectors) {
            const val = scores[v] || 3;
            if (val < minValue) { minValue = val; minVector = v; }
        }
        const growthPoints = {
            'СБ': 'Работа с реакцией на давление и страхи.',
            'ТФ': 'Проработка денежных блоков.',
            'УБ': 'Развитие системного мышления.',
            'ЧВ': 'Исцеление привязанности.'
        };
        return growthPoints[minVector] || 'Исследование себя и своих паттернов.';
    },
    
    // ========== ЭКРАН "ЗАДАТЬ ВОПРОС" ==========
    showAskQuestionScreen() {
        const template = document.getElementById('askQuestionScreen');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            const sendBtn = document.getElementById('sendQuestionBtn');
            const questionInput = document.getElementById('questionInput');
            const voiceRecordBtn = document.getElementById('voiceRecordBtn');
            const backBtn = document.getElementById('backToProfileBtn');
            
            sendBtn?.addEventListener('click', async () => {
                const question = questionInput?.value.trim();
                if (question) await this.sendQuestion(question);
                if (questionInput) questionInput.value = '';
            });
            questionInput?.addEventListener('keypress', e => { if (e.key === 'Enter') sendBtn?.click(); });
            voiceRecordBtn?.addEventListener('click', () => this.startVoiceRecognition());
            backBtn?.addEventListener('click', () => this.showFinalProfile());
        }, 100);
    },
    
    // ========== ЭКРАН "ВЫБРАТЬ ЦЕЛЬ" ==========
    async showChooseGoalScreen() {
        const template = document.getElementById('chooseGoalScreen');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        
        clone.querySelector('#goalUserName').textContent = this.userName;
        if (this.profileData) {
            clone.querySelector('#profileCode').textContent = this.profileData.display_name || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
        }
        const modeNames = { coach: '🔮 КОУЧ', psychologist: '🧠 ПСИХОЛОГ', trainer: '⚡ ТРЕНЕР' };
        clone.querySelector('#modeCode').textContent = modeNames[this.currentMode] || '🔮 КОУЧ';
        
        const goals = this.getGoalsForProfile();
        const goalsList = clone.querySelector('#goalsList');
        if (goalsList) {
            goalsList.innerHTML = goals.map(goal => `
                <div class="goal-item" data-goal-id="${goal.id}">
                    <div class="goal-name">${goal.emoji || '🎯'} ${goal.name}</div>
                    <div class="goal-time">⏱ ${goal.time}</div>
                    <div class="goal-difficulty">${this.getDifficultyEmoji(goal.difficulty)} ${goal.difficulty}</div>
                </div>
            `).join('');
            setTimeout(() => {
                goalsList.querySelectorAll('.goal-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const goal = goals.find(g => g.id === item.dataset.goalId);
                        if (goal) this.selectGoal(goal);
                    });
                });
            }, 100);
        }
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            document.getElementById('customGoalBtn')?.addEventListener('click', () => this.showCustomGoalInput());
            document.getElementById('backToProfileFromGoalBtn')?.addEventListener('click', () => this.showFinalProfile());
        }, 100);
    },
    
    getGoalsForProfile() {
        const scores = this.profileData?.scores || { СБ: 3, ТФ: 3, УБ: 3, ЧВ: 3 };
        let weakest = 'СБ', weakestValue = 5;
        for (const [key, val] of Object.entries(scores)) {
            if (val < weakestValue) { weakestValue = val; weakest = key; }
        }
        
        const goalsDb = {
            coach: {
                weak: {
                    'СБ': [{ id: 'fear_work', name: 'Проработать страхи', time: '3-4 недели', difficulty: 'medium', emoji: '🛡️' }],
                    'ТФ': [{ id: 'money_blocks', name: 'Проработать денежные блоки', time: '3-4 недели', difficulty: 'medium', emoji: '💰' }],
                    'УБ': [{ id: 'meaning', name: 'Найти смысл', time: '4-6 недель', difficulty: 'hard', emoji: '🎯' }],
                    'ЧВ': [{ id: 'relations', name: 'Улучшить отношения', time: '4-6 недель', difficulty: 'hard', emoji: '💕' }]
                },
                general: [{ id: 'purpose', name: 'Найти предназначение', time: '5-7 недель', difficulty: 'hard', emoji: '🌟' }]
            }
        };
        const modeDb = goalsDb[this.currentMode] || goalsDb.coach;
        const goals = [];
        if (modeDb.weak?.[weakest]) goals.push(...modeDb.weak[weakest]);
        if (modeDb.general) goals.push(...modeDb.general);
        return goals.slice(0, 6);
    },
    
    getDifficultyEmoji(difficulty) {
        const emojis = { easy: '🟢', medium: '🟡', hard: '🔴' };
        return emojis[difficulty] || '⚪';
    },
    
    selectGoal(goal) {
        alert(`Цель выбрана: ${goal.name}\n\nВремя: ${goal.time}\n\nСкоро появится подробный план достижения!`);
    },
    
    showCustomGoalInput() {
        const goal = prompt('Сформулируйте свою цель своими словами:');
        if (goal?.trim()) alert(`Цель принята: "${goal}"\n\nСкоро появится план достижения!`);
    },
    
    // ========== ЭКРАН "ВЫБРАТЬ РЕЖИМ" ==========
    showChooseModeScreen() {
        const template = document.getElementById('chooseModeScreen');
        if (!template) return;
        const clone = document.importNode(template.content, true);
        if (this.profileData) {
            clone.querySelector('#modeProfileCode').textContent = this.profileData.display_name || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
        }
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            const modeCards = document.querySelectorAll('.mode-card');
            const backBtn = document.getElementById('backToProfileFromModeBtn');
            modeCards.forEach(card => {
                card.addEventListener('click', () => {
                    modeCards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    this.setMode(card.dataset.mode);
                });
            });
            backBtn?.addEventListener('click', () => this.showFinalProfile());
        }, 100);
    },
    
    async setMode(mode) {
        this.currentMode = mode;
        const modeNames = { coach: '🔮 КОУЧ', psychologist: '🧠 ПСИХОЛОГ', trainer: '⚡ ТРЕНЕР' };
        const botStatus = document.getElementById('botStatus');
        if (botStatus) botStatus.textContent = modeNames[mode] || '🧠 психолог';
        await this.saveModeToServer(mode);
        alert(`Режим ${modeNames[mode]} активирован!`);
        this.showFinalProfile();
    },
    
    // ========== ЭКРАН "МЫСЛИ ПСИХОЛОГА" ==========
    async showPsychologistThought() {
        const loadingTemplate = document.getElementById('psychologistThoughtLoadingScreen');
        if (loadingTemplate) {
            const clone = document.importNode(loadingTemplate.content, true);
            const container = document.getElementById('screenContainer');
            container.innerHTML = '';
            container.appendChild(clone);
        }
        
        try {
            let thought = await this.getPsychologistThoughtFromServer();
            if (!thought || thought === 'Мысли психолога еще не сгенерированы.') {
                thought = this.generateMockThought();
            }
            this.showPsychologistThoughtResult(thought);
        } catch (error) {
            this.showPsychologistThoughtResult('Не удалось сгенерировать мысли психолога. Попробуйте позже.');
        }
    },
    
    generateMockThought() {
        const scores = this.profileData?.scores || { СБ: 3, ТФ: 3, УБ: 3, ЧВ: 3 };
        const weakVectors = [];
        for (const [key, val] of Object.entries(scores)) {
            if (val <= 2.5) weakVectors.push(key);
        }
        let thought = `🧠 ${this.userName}, я проанализировал твой профиль.\n\n`;
        if (weakVectors.includes('СБ')) thought += `Я вижу, что давление и конфликты выводят тебя из равновесия. Это твоя чувствительность.\n\n`;
        if (weakVectors.includes('ТФ')) thought += `С деньгами у тебя особая история. Они связаны с ценностью себя.\n\n`;
        if (weakVectors.includes('УБ')) thought += `Ты часто ищешь систему в хаосе. Иногда стоит просто быть.\n\n`;
        if (weakVectors.includes('ЧВ')) thought += `В отношениях ты ищешь баланс между близостью и свободой.\n\n`;
        thought += `Твой главный вызов — увидеть, как твои особенности становятся твоей суперсилой.`;
        return thought;
    },
    
    showPsychologistThoughtResult(thought) {
        const resultTemplate = document.getElementById('psychologistThoughtResultScreen');
        if (!resultTemplate) return;
        const clone = document.importNode(resultTemplate.content, true);
        clone.querySelector('#thoughtText').innerHTML = thought.replace(/\n/g, '<br>');
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            document.getElementById('backToProfileFromThoughtBtn')?.addEventListener('click', () => this.showFinalProfile());
            document.getElementById('askQuestionFromThoughtBtn')?.addEventListener('click', () => this.showAskQuestionScreen());
        }, 100);
    },
    
    // ========== ГОЛОСОВОЙ ВВОД ==========
    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('⚠️ Web Speech API не поддерживается');
            return;
        }
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'ru-RU';
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;
        
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.showVoiceStatus('🎤 Слушаю...');
        };
        this.recognition.onresult = async (event) => {
            const text = event.results[0][0].transcript;
            this.showVoiceStatus(`📝 Вы сказали: ${text}`);
            await this.sendQuestion(text);
            this.hideVoiceStatus();
        };
        this.recognition.onerror = () => {
            this.showVoiceStatus('❌ Ошибка распознавания');
            setTimeout(() => this.hideVoiceStatus(), 2000);
            this.isRecording = false;
        };
        this.recognition.onend = () => {
            this.isRecording = false;
            this.hideVoiceStatus();
        };
        console.log('🎤 Web Speech API инициализирован');
    },
    
    showVoiceStatus(message) {
        let statusDiv = document.getElementById('voiceStatus');
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'voiceStatus';
            statusDiv.style.cssText = `position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:var(--max-blue,#248bf2);color:white;padding:10px20px;border-radius:30px;z-index:1000;white-space:nowrap;`;
            document.body.appendChild(statusDiv);
        }
        statusDiv.textContent = message;
        statusDiv.style.display = 'block';
    },
    
    hideVoiceStatus() {
        const statusDiv = document.getElementById('voiceStatus');
        if (statusDiv) statusDiv.style.display = 'none';
    },
    
    startVoiceRecognition() {
        if (this.recognition && !this.isRecording) {
            try { this.recognition.start(); }
            catch (e) { this.showVoiceStatus('❌ Попробуйте еще раз'); setTimeout(() => this.hideVoiceStatus(), 2000); }
        } else if (!this.recognition) {
            alert('Ваш браузер не поддерживает голосовой ввод.');
        }
    },
    
    // ========== УМНЫЕ ВОПРОСЫ ==========
    async showSmartQuestions() {
        let questions = await this.getSmartQuestionsFromServer();
        if (!questions?.length) questions = this.generateLocalSmartQuestions();
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = `
            <div class="smart-questions-container">
                <div class="smart-questions-header"><div class="smart-questions-emoji">❓</div>
                <h2 class="smart-questions-title">УМНЫЕ ВОПРОСЫ</h2>
                <p class="smart-questions-desc">Выберите вопрос или напишите свой</p></div>
                <div class="smart-questions-list" id="smartQuestionsList">
                    ${questions.map(q => `<div class="smart-question-item" data-question="${this.escapeHtml(q)}">
                        <span class="smart-question-emoji">💭</span>
                        <span class="smart-question-text">${this.escapeHtml(q)}</span>
                    </div>`).join('')}
                </div>
                <div class="smart-questions-input">
                    <div class="input-group">
                        <input type="text" id="smartQuestionInput" class="smart-question-input" placeholder="Или напишите свой вопрос...">
                        <button id="sendSmartQuestionBtn" class="smart-question-submit">➡️</button>
                    </div>
                </div>
                <div class="smart-questions-back">
                    <button class="onboarding-btn secondary" id="backFromSmartQuestionsBtn">◀️ НАЗАД</button>
                </div>
            </div>
        `;
        
        this.addSmartQuestionsStyles();
        
        document.querySelectorAll('.smart-question-item').forEach(item => {
            item.addEventListener('click', async () => {
                await this.sendQuestion(item.dataset.question);
            });
        });
        
        const sendBtn = document.getElementById('sendSmartQuestionBtn');
        const input = document.getElementById('smartQuestionInput');
        sendBtn?.addEventListener('click', async () => {
            const question = input?.value.trim();
            if (question) await this.sendQuestion(question);
            if (input) input.value = '';
        });
        input?.addEventListener('keypress', e => { if (e.key === 'Enter') sendBtn?.click(); });
        
        document.getElementById('backFromSmartQuestionsBtn')?.addEventListener('click', () => this.showFinalProfile());
    },
    
    generateLocalSmartQuestions() {
        const scores = this.profileData?.scores || { СБ: 3, ТФ: 3, УБ: 3, ЧВ: 3 };
        const questions = [];
        const tf = scores['ТФ'] || 3;
        const sb = scores['СБ'] || 3;
        if (tf <= 2) questions.push('Как начать зарабатывать, если нет денег?');
        else if (tf <= 4) questions.push('Как увеличить доход без новых вложений?');
        if (sb <= 2) questions.push('Как перестать бояться конфликтов?');
        else if (sb <= 4) questions.push('Как защищать границы без агрессии?');
        questions.push('С чего начать изменения?', 'Что мне делать с этой ситуацией?');
        return questions.slice(0, 5);
    },
    
    addSmartQuestionsStyles() {
        if (document.getElementById('smartQuestionsStyles')) return;
        const style = document.createElement('style');
        style.id = 'smartQuestionsStyles';
        style.textContent = `
            .smart-questions-container { padding: 20px; overflow-y: auto; height: 100%; }
            .smart-questions-header { text-align: center; margin-bottom: 24px; }
            .smart-questions-emoji { font-size: 48px; }
            .smart-questions-title { font-size: 22px; margin-bottom: 8px; color: var(--max-text); }
            .smart-questions-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
            .smart-question-item { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 20px; padding: 14px 18px; cursor: pointer; display: flex; gap: 12px; }
            .smart-question-item:hover { border-color: var(--max-blue); transform: translateX(4px); }
            .smart-question-input { flex: 1; padding: 14px 18px; background: var(--glass-bg); border-radius: 30px; color: var(--max-text); }
            .smart-question-submit { width: 48px; height: 48px; border-radius: 50%; background: var(--max-blue); color: white; }
            .smart-questions-back { text-align: center; margin-top: 16px; }
        `;
        document.head.appendChild(style);
    },
    
    // ========== ЧАТ ==========
    async sendQuestion(question) {
        const container = document.getElementById('screenContainer');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'thought-loading-container';
        loadingDiv.innerHTML = `<div class="thought-loading-content"><div class="loading-spinner">🤔</div><div class="loading-text">Думаю над ответом...</div></div>`;
        const originalContent = container.innerHTML;
        container.innerHTML = '';
        container.appendChild(loadingDiv);
        
        try {
            const result = await this.sendQuestionToServer(question);
            container.innerHTML = originalContent;
            
            const messagesList = document.getElementById('messagesList');
            if (messagesList) {
                const userMessage = document.createElement('div');
                userMessage.className = 'message user-message';
                userMessage.innerHTML = `<div class="message-bubble"><div class="message-text">${this.escapeHtml(question)}</div><div class="message-time">только что</div></div>`;
                messagesList.appendChild(userMessage);
                
                const botMessage = document.createElement('div');
                botMessage.className = 'message bot-message';
                botMessage.innerHTML = `<div class="message-bubble"><div class="message-text">${this.escapeHtml(result.response || 'Я вас слушаю. Расскажите подробнее.')}</div><div class="message-time">только что</div></div>`;
                messagesList.appendChild(botMessage);
                
                document.querySelector('.messages-container')?.scrollTo({ top: document.querySelector('.messages-container').scrollHeight });
            } else {
                alert(result.response);
            }
        } catch (error) {
            console.error('Ошибка:', error);
            container.innerHTML = originalContent;
            alert('Извините, произошла ошибка. Попробуйте позже.');
        }
    },
    
    // ========== ОСНОВНОЙ ЧАТ ==========
    showMainChat() {
        console.log('💬 Показываем основной чат');
        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.style.display = 'flex';
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = `
            <div class="messages-container">
                <div class="messages-list" id="messagesList">
                    <div class="message bot-message">
                        <div class="message-bubble">
                            <div class="message-text">Привет, ${this.userName}! Чем могу помочь?</div>
                            <div class="message-time">только что</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="input-panel">
                <button class="attach-btn" id="attachBtn">📎</button>
                <div class="message-input-wrapper">
                    <input type="text" class="message-input" placeholder="Сообщение..." id="messageInput">
                    <button class="send-btn" id="sendMessageBtn">➡️</button>
                </div>
                <button class="voice-btn" id="voiceBtn">🎤</button>
            </div>
        `;
        
        if (!document.getElementById('chatStyles')) {
            const style = document.createElement('style');
            style.id = 'chatStyles';
            style.textContent = `
                .messages-container { flex: 1; overflow-y: auto; padding: 16px; height: calc(100vh - 120px); }
                .messages-list { display: flex; flex-direction: column; gap: 12px; }
                .message { display: flex; width: 100%; }
                .message.user-message { justify-content: flex-end; }
                .message.bot-message { justify-content: flex-start; }
                .message-bubble { max-width: 80%; padding: 12px 16px; border-radius: 18px; }
                .user-message .message-bubble { background: var(--max-message-user, #2b5278); border-bottom-right-radius: 4px; }
                .bot-message .message-bubble { background: var(--max-message-bot, #1f2c38); border-bottom-left-radius: 4px; }
                .message-text { font-size: 15px; line-height: 1.4; }
                .message-time { font-size: 10px; color: var(--max-text-secondary); margin-top: 4px; text-align: right; }
                .input-panel { padding: 12px 16px; background: var(--max-panel-bg); border-top: 1px solid var(--max-border); display: flex; gap: 8px; align-items: center; }
                .attach-btn, .voice-btn { width: 40px; height: 40px; border-radius: 50%; background: var(--glass-bg); border: none; color: var(--max-text); font-size: 20px; cursor: pointer; }
                .message-input-wrapper { flex: 1; display: flex; gap: 8px; background: var(--glass-bg); border-radius: 24px; padding: 4px 4px 4px 16px; }
                .message-input { flex: 1; background: transparent; border: none; color: var(--max-text); font-size: 16px; outline: none; padding: 8px 0; }
                .send-btn { width: 36px; height: 36px; border-radius: 50%; background: var(--max-blue); border: none; color: white; font-size: 18px; cursor: pointer; }
            `;
            document.head.appendChild(style);
        }
        
        setTimeout(() => {
            const sendBtn = document.getElementById('sendMessageBtn');
            const messageInput = document.getElementById('messageInput');
            const messagesList = document.getElementById('messagesList');
            const voiceBtn = document.getElementById('voiceBtn');
            
            const sendMessage = async () => {
                const text = messageInput?.value.trim();
                if (text) {
                    const userMessage = document.createElement('div');
                    userMessage.className = 'message user-message';
                    userMessage.innerHTML = `<div class="message-bubble"><div class="message-text">${this.escapeHtml(text)}</div><div class="message-time">только что</div></div>`;
                    messagesList.appendChild(userMessage);
                    if (messageInput) messageInput.value = '';
                    document.querySelector('.messages-container')?.scrollTo({ top: document.querySelector('.messages-container').scrollHeight });
                    await this.sendQuestion(text);
                }
            };
            
            sendBtn?.addEventListener('click', sendMessage);
            messageInput?.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });
            voiceBtn?.addEventListener('click', () => this.startVoiceRecognition());
        }, 100);
    },
    
    setupEventListeners() {
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const chatsPanel = document.getElementById('chatsPanel');
        mobileMenuBtn?.addEventListener('click', () => chatsPanel?.classList.toggle('visible'));
        
        document.getElementById('userMiniProfile')?.addEventListener('click', () => this.showNameModal());
        document.getElementById('newChatBtn')?.addEventListener('click', () => alert('Новая переписка будет доступна позже'));
    },
    
    showContextMenu() { console.log('Контекстное меню'); },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
window.App = App;
