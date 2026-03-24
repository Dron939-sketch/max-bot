// ============================================
// ЛИЧНЫЙ КАБИНЕТ - КОНСОРЦИУМ ФРЕДИ
// Версия 3.5 - ПОЛНАЯ (с улучшенной стабильностью и кэшированием)
// ============================================

class CacheManager {
    constructor() {
        this.cache = new Map();
        this.ttl = 5 * 60 * 1000; // 5 минут
    }
    
    get(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.ttl) {
            console.log(`📦 Cache hit: ${key}`);
            return cached.data;
        }
        return null;
    }
    
    set(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
        console.log(`💾 Cache set: ${key}`);
    }
    
    clear(key) {
        if (key) {
            this.cache.delete(key);
            console.log(`🗑️ Cache cleared: ${key}`);
        } else {
            this.cache.clear();
            console.log(`🗑️ Cache cleared all`);
        }
    }
}

class FrediDashboard {
    constructor() {
        // Получаем user_id из maxContext (уже установлен в index.html)
        this.userId = window.maxContext?.user_id || localStorage.getItem('fredi_user_id');
        this.userData = null;
        this.userName = window.maxContext?.user_name || 'Друг';
        this.isTestCompleted = false;
        this.profileCode = null;
        this.mode = 'coach';
        this.currentScreen = 'dashboard';
        this.daysActive = 3;
        this.sessionsCount = 12;
        this.profileText = null;
        this.psychologistThought = null;
        this.refreshInterval = null;
        
        // Кэш-менеджер
        this.cache = new CacheManager();
        
        // Модули улучшений
        this.challengeManager = null;
        this.notificationManager = null;
        this.psychometric = null;
        this.animatedAvatar = null;
        
        // Состояние голосовой записи
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingTimer = null;
        this.recordingStartTime = null;
        
        // Детекция WEBVIEW
        this.isWebView = /; wv\)/.test(navigator.userAgent) || 
                         /WebView/.test(navigator.userAgent) ||
                         (window.MAX && window.MAX.WebApp);
        
        // Базовые модули консорциума (всегда доступны)
        this.allModules = [
            { id: 'strategy', name: '🎯 Стратегия', icon: '🎯', color: '#4CAF50', description: 'Построение планов и достижение целей' },
            { id: 'reputation', name: '🏆 Репутация', icon: '🏆', color: '#FF9800', description: 'Управление впечатлением и авторитетом' },
            { id: 'goals', name: '📊 Цели', icon: '📊', color: '#2196F3', description: 'Ваши цели и задачи' },
            { id: 'entertainment', name: '🎮 Развлечения', icon: '🎮', color: '#9C27B0', description: 'Идеи для отдыха' },
            { id: 'psychology', name: '🧠 Психология', icon: '🧠', color: '#E91E63', description: 'Глубинные паттерны' },
            { id: 'habits', name: '🔄 Привычки', icon: '🔄', color: '#00BCD4', description: 'Полезные привычки' },
            { id: 'communication', name: '💬 Общение', icon: '💬', color: '#3F51B5', description: 'Советы по общению' },
            { id: 'finance', name: '💰 Финансы', icon: '💰', color: '#FFC107', description: 'Управление деньгами' },
            { id: 'health', name: '❤️ Здоровье', icon: '❤️', color: '#F44336', description: 'Забота о себе' },
            { id: 'creativity', name: '🎨 Творчество', icon: '🎨', color: '#FF6B6B', description: 'Вдохновение и идеи' }
        ];
        
        // Откладываем инициализацию
        this.initPromise = this.init();
        
        // Слушаем события сети
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Обработка deep links
        this.handleDeepLinks();
    }
    
    // ============================================
    // ОБРАБОТКА СОБЫТИЙ СЕТИ
    // ============================================
    
    handleOnline() {
        console.log('🟢 Соединение восстановлено');
        this.showFloatingMessage('✅ Соединение восстановлено', 'success');
        setTimeout(() => this.refreshData(), 1000);
    }
    
    handleOffline() {
        console.log('🔴 Потеря соединения');
        this.showFloatingMessage('⚠️ Нет интернета. Проверьте соединение.', 'error');
    }
    
    // ============================================
    // ОБРАБОТКА DEEP LINKS
    // ============================================
    
    handleDeepLinks() {
        if (window.location.hash) {
            const hash = window.location.hash.substring(1);
            console.log('🔗 Deep link:', hash);
            
            setTimeout(() => {
                if (hash === 'test') {
                    this.startTest();
                } else if (hash === 'profile') {
                    if (this.isTestCompleted) {
                        this.renderProfileScreen();
                    }
                } else if (hash === 'thoughts') {
                    if (this.isTestCompleted) {
                        this.renderPsychologistThoughtScreen();
                    }
                } else if (hash === 'goals') {
                    if (this.isTestCompleted) {
                        this.renderGoalsScreen();
                    }
                }
            }, 1500);
        }
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ С ОЖИДАНИЕМ API
    // ============================================
    
    async init() {
        console.log('🎯 Инициализация личного кабинета...');
        console.log('📱 Режим WebView:', this.isWebView);
        console.log('👤 user_id:', this.userId);
        console.log('👤 user_name:', this.userName);
        
        // Проверяем наличие API
        if (!window.api) {
            console.error('❌ window.api не загружен!');
            this.showError('Не удалось загрузить API. Проверьте соединение и перезагрузите страницу.');
            return;
        }
        
        // Ждем загрузки API
        let attempts = 0;
        const maxAttempts = 50;
        
        while (!window.api.baseUrl && attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 100));
            attempts++;
            if (attempts % 10 === 0) {
                console.log(`⏳ Ожидание window.api.baseUrl... ${attempts * 100}мс`);
            }
        }
        
        console.log('✅ window.api доступен');
        
        if (!this.userId) {
            console.error('❌ Нет user_id!');
            this.showError('Не удалось идентифицировать пользователя. Пожалуйста, откройте приложение через MAX.');
            return;
        }
        
        try {
            await this.loadUserData();
            await this.loadProfileData();
            await this.loadPsychologistThought();
            this.renderDashboard();
            this.initVoiceInput();
            this.startAutoRefresh();
            
            if (this.isTestCompleted) {
                await this.initAnimatedAvatar();
                await this.initChallenges();
                await this.initPsychometricDoubles();
            }
        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
            this.showError('Ошибка загрузки данных. Попробуйте обновить страницу.');
        }
    }
    
    // ============================================
    // ЗАГРУЗКА ДАННЫХ
    // ============================================
    
    async loadUserData(forceRefresh = false) {
        try {
            console.log('🔍 Загрузка данных для user_id:', this.userId);
            
            // Проверяем кэш
            const cached = this.cache.get(`user_status_${this.userId}`);
            if (cached && !forceRefresh) {
                console.log('📦 Используем кэшированные данные статуса');
                this.isTestCompleted = cached.isTestCompleted;
                this.profileCode = cached.profileCode;
                return;
            }
            
            const status = await window.api.request(`/api/user-status?user_id=${this.userId}`);
            console.log('📊 Статус пользователя:', status);
            
            this.isTestCompleted = status.test_completed === true || 
                                   status.has_profile === true || 
                                   status.has_interpretation === true ||
                                   (status.profile_code && status.profile_code !== '');
            
            this.profileCode = status.profile_code;
            
            console.log('📌 isTestCompleted:', this.isTestCompleted);
            console.log('📌 profileCode:', this.profileCode);
            
            // Сохраняем в кэш
            this.cache.set(`user_status_${this.userId}`, {
                isTestCompleted: this.isTestCompleted,
                profileCode: this.profileCode,
                timestamp: Date.now()
            });
            
            // Если профиля нет в памяти — загружаем из БД
            if (!status.has_profile && !status.test_completed && !status.has_interpretation) {
                console.log('🔄 Профиль не найден в памяти, загружаем из БД...');
                
                const loadResult = await window.api.request('/api/force-load-user', {
                    method: 'POST',
                    body: JSON.stringify({ user_id: this.userId })
                });
                
                console.log('📦 Результат force-load:', loadResult);
                
                if (loadResult.success && loadResult.has_profile) {
                    console.log('✅ Профиль загружен из БД!');
                    this.isTestCompleted = true;
                    this.profileCode = loadResult.profile_code;
                    this.cache.set(`user_status_${this.userId}`, {
                        isTestCompleted: this.isTestCompleted,
                        profileCode: this.profileCode
                    });
                }
            }
            
            // Загружаем имя пользователя
            try {
                const userData = await window.api.request(`/api/user-data?user_id=${this.userId}`);
                if (userData && userData.user_name && userData.user_name !== 'друг') {
                    this.userName = userData.user_name;
                    console.log('👤 Имя пользователя:', this.userName);
                }
            } catch (nameError) {
                console.warn('Не удалось загрузить имя из БД:', nameError);
            }
            
            // Если тест пройден, загружаем полный профиль
            if (this.isTestCompleted) {
                const profile = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
                this.userData = profile;
                console.log('📊 Профиль загружен');
                this.cache.set(`user_profile_${this.userId}`, profile);
            }
            
            console.log('✅ loadUserData завершён, isTestCompleted:', this.isTestCompleted);
            
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
            this.isTestCompleted = false;
            this.renderTestRequiredScreen(document.getElementById('screenContainer'));
        }
    }
    
    // ============================================
    // ЗАГРУЗКА ПРОФИЛЯ
    // ============================================
    
    async loadProfileData(forceRefresh = false) {
        try {
            const cached = this.cache.get(`profile_text_${this.userId}`);
            if (cached && !forceRefresh) {
                console.log('📦 Используем кэшированный текст профиля');
                this.profileText = cached;
                return;
            }
            
            const response = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
            
            if (response.ai_generated_profile) {
                this.profileText = response.ai_generated_profile;
            } else if (response.profile_data) {
                this.profileText = this.formatProfileText(response);
            } else {
                this.profileText = 'Профиль пока не сформирован. Пройдите тест.';
            }
            
            this.cache.set(`profile_text_${this.userId}`, this.profileText);
            console.log('✅ Профиль загружен');
        } catch (error) {
            console.error('Ошибка загрузки профиля:', error);
            this.profileText = 'Ошибка загрузки профиля. Попробуйте позже.';
        }
    }
    
    // ============================================
    // ЗАГРУЗКА МЫСЛЕЙ ПСИХОЛОГА
    // ============================================
    
    async loadPsychologistThought(forceRefresh = false) {
        try {
            const cached = this.cache.get(`thought_${this.userId}`);
            if (cached && !forceRefresh) {
                console.log('📦 Используем кэшированные мысли психолога');
                this.psychologistThought = cached;
                return;
            }
            
            const response = await window.api.request(`/api/thought?user_id=${this.userId}`);
            this.psychologistThought = response.thought || 'Мысли психолога еще не сгенерированы. Пройдите тест для получения персонального анализа.';
            this.cache.set(`thought_${this.userId}`, this.psychologistThought);
            console.log('✅ Мысли психолога загружены');
        } catch (error) {
            console.error('Ошибка загрузки мыслей психолога:', error);
            this.psychologistThought = 'Мысли психолога пока недоступны. Попробуйте позже.';
        }
    }
    
    // ============================================
    // ОБНОВЛЕНИЕ ДАННЫХ
    // ============================================
    
    async refreshData() {
        console.log('🔄 Обновление данных...');
        this.showFloatingMessage('🔄 Обновление данных...', 'info');
        
        try {
            await this.loadUserData(true);
            await this.loadProfileData(true);
            await this.loadPsychologistThought(true);
            this.renderDashboard();
            this.showFloatingMessage('✅ Данные обновлены', 'success');
        } catch (error) {
            console.error('Ошибка обновления:', error);
            this.showFloatingMessage('❌ Ошибка обновления данных', 'error');
        }
    }
    
    startAutoRefresh(interval = 300000) { // 5 минут
        if (this.refreshInterval) clearInterval(this.refreshInterval);
        
        this.refreshInterval = setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.refreshData();
            }
        }, interval);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    // ============================================
    // ОЧИСТКА РЕСУРСОВ
    // ============================================
    
    destroy() {
        console.log('🧹 Очистка ресурсов...');
        
        this.stopAutoRefresh();
        
        // Останавливаем запись голоса
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
        }
        
        // Очищаем таймеры
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        // Очищаем анимации
        if (this.animatedAvatar) {
            this.animatedAvatar.destroy();
        }
        
        // Очищаем кэш
        this.cache.clear();
        
        console.log('✅ Ресурсы очищены');
    }
    
    // ============================================
    // ФОРМАТИРОВАНИЕ ТЕКСТА
    // ============================================
    
    formatProfileText(data) {
        const profile = data.profile_data || {};
        const profileCode = profile.display_name || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
        const perceptionType = data.perception_type || 'не определен';
        const thinkingLevel = data.thinking_level || 5;
        
        return `
            <div class="profile-section">
                <h3>🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ</h3>
                <p><strong>Профиль:</strong> ${profileCode}</p>
                <p><strong>Тип восприятия:</strong> ${perceptionType}</p>
                <p><strong>Уровень мышления:</strong> ${thinkingLevel}/9</p>
            </div>
            <div class="profile-section">
                <h4>📊 ВАШИ ВЕКТОРЫ:</h4>
                <p>• Реакция на давление (СБ): ${profile.sb_level || 4}/6</p>
                <p>• Отношение к деньгам (ТФ): ${profile.tf_level || 4}/6</p>
                <p>• Понимание мира (УБ): ${profile.ub_level || 4}/6</p>
                <p>• Отношения с людьми (ЧВ): ${profile.chv_level || 4}/6</p>
            </div>
            <div class="profile-section">
                <h4>🎯 ТОЧКА РОСТА:</h4>
                <p>${this.getGrowthPoint(profile)}</p>
            </div>
        `;
    }
    
    getGrowthPoint(profile) {
        const scores = {
            sb: profile.sb_level || 4,
            tf: profile.tf_level || 4,
            ub: profile.ub_level || 4,
            chv: profile.chv_level || 4
        };
        
        const weakest = Object.entries(scores).sort((a, b) => a[1] - b[1])[0]?.[0] || 'sb';
        
        const growthPoints = {
            sb: 'Работа с реакцией на давление и страхи. Учитесь говорить "нет" и защищать свои границы.',
            tf: 'Проработка денежных блоков и развитие финансового мышления.',
            ub: 'Развитие системного мышления и поиск глубинных смыслов.',
            chv: 'Исцеление привязанности и развитие навыков здорового общения.'
        };
        
        return growthPoints[weakest] || 'Исследование себя и своих паттернов.';
    }
    
    // ============================================
    // ОТРИСОВКА ДАШБОРДА
    // ============================================
    
    renderDashboard() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        if (!this.isTestCompleted) {
            this.renderTestRequiredScreen(container);
            return;
        }
        
        this.renderMainDashboard(container);
    }
    
    renderTestRequiredScreen(container) {
        container.innerHTML = `
            <div class="dashboard-test-required">
                <div class="test-required-icon">🧠</div>
                <div class="test-required-title">Пройдите тест</div>
                <div class="test-required-text">
                    Привет, ${this.userName}! Я пока не знаком с вами.<br><br>
                    Чтобы я мог подобрать для вас персональные модули и рекомендации,<br>
                    нужно пройти психологическое тестирование.<br><br>
                    Это займёт всего 15 минут и поможет:<br>
                    • Понять ваш психологический профиль<br>
                    • Подобрать стратегии под ваш тип мышления<br>
                    • Создать персонализированный консорциум<br><br>
                    Готовы познакомиться?
                </div>
                <button class="test-required-btn" id="startTestBtn">🚀 ПРОЙТИ ТЕСТ</button>
                <button class="test-required-btn secondary" id="skipTestBtn">⏭ ПОЗЖЕ</button>
            </div>
        `;
        
        const startBtn = document.getElementById('startTestBtn');
        if (startBtn) startBtn.onclick = () => this.startTest();
        
        const skipBtn = document.getElementById('skipTestBtn');
        if (skipBtn) skipBtn.onclick = () => this.showSkipMessage();
    }
    
    renderMainDashboard(container) {
        const modulesToShow = this.getPersonalizedModules();
        
        container.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <div class="user-welcome">
                        <div class="user-avatar" id="avatarContainer">${this.getUserAvatar()}</div>
                        <div class="user-info">
                            <div class="user-name">${this.userName}</div>
                            <div class="user-profile">${this.profileCode || 'СБ-4_ТФ-4_УБ-4_ЧВ-4'}</div>
                        </div>
                    </div>
                    <div class="user-stats">
                        <div class="stat-item">
                            <span class="stat-value">${this.daysActive}</span>
                            <span class="stat-label">дней с вами</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${this.sessionsCount}</span>
                            <span class="stat-label">сессий</span>
                        </div>
                    </div>
                </div>
                
                <div class="voice-input-dashboard" id="voiceInputDashboard">
                    <button class="voice-record-btn-large" id="dashboardVoiceBtn">
                        <span class="voice-icon">🎤</span>
                        <span class="voice-text">Нажмите и говорите</span>
                    </button>
                    <div class="voice-status-dashboard" id="voiceStatusDashboard" style="display: none;">
                        <span class="recording-pulse"></span>
                        <span class="recording-text">Запись...</span>
                        <span class="recording-timer" id="dashboardRecordingTimer">0s</span>
                    </div>
                </div>
                
                <div class="modules-grid" id="modulesGrid">
                    ${modulesToShow.map(module => `
                        <div class="module-card" data-module="${module.id}" style="border-left-color: ${module.color}">
                            <div class="module-icon">${module.icon}</div>
                            <div class="module-name">${module.name}</div>
                            <div class="module-desc">${module.description || ''}</div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="quick-actions">
                    <div class="quick-actions-title">⚡ Быстрые действия</div>
                    <div class="quick-actions-grid">
                        <div class="quick-action" data-action="mode">
                            <span class="action-icon">⚙️</span>
                            <span class="action-name">Сменить режим</span>
                        </div>
                        <div class="quick-action" data-action="profile">
                            <span class="action-icon">🧠</span>
                            <span class="action-name">Мой портрет</span>
                        </div>
                        <div class="quick-action" data-action="thoughts">
                            <span class="action-icon">💭</span>
                            <span class="action-name">Мысли психолога</span>
                        </div>
                        <div class="quick-action" data-action="goals">
                            <span class="action-icon">🎯</span>
                            <span class="action-name">Мои цели</span>
                        </div>
                    </div>
                </div>
                
                <div class="floating-message" id="floatingMessage" style="display: none;">
                    <div class="floating-message-content">
                        <div class="floating-message-text" id="floatingMessageText"></div>
                        <div class="floating-message-close" id="floatingMessageClose">✕</div>
                    </div>
                </div>
            </div>
        `;
        
        this.attachDashboardEvents();
    }
    
    // ============================================
    // ЭКРАНЫ
    // ============================================
    
    renderProfileScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div class="final-profile-container">
                <div class="final-profile-content">
                    <div class="profile-header">
                        <div class="profile-emoji">🧠</div>
                        <h2 class="profile-title">ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ</h2>
                    </div>
                    <div class="profile-text" id="profileText">
                        ${this.formatTextForDisplay(this.profileText || 'Загрузка профиля...')}
                    </div>
                    <div class="profile-buttons">
                        <button class="onboarding-btn primary" id="backToDashboardBtn">◀️ НАЗАД</button>
                        <button class="onboarding-btn secondary" id="refreshProfileBtn">🔄 ОБНОВИТЬ</button>
                    </div>
                </div>
            </div>
        `;
        
        const backBtn = document.getElementById('backToDashboardBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
        
        const refreshBtn = document.getElementById('refreshProfileBtn');
        if (refreshBtn) refreshBtn.onclick = async () => {
            await this.loadProfileData(true);
            this.renderProfileScreen();
        };
    }
    
    renderPsychologistThoughtScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div class="thought-result-container">
                <div class="thought-result-content">
                    <div class="thought-header">
                        <div class="thought-emoji">🧠</div>
                        <h2 class="thought-title">МЫСЛИ ПСИХОЛОГА</h2>
                    </div>
                    <div class="thought-text" id="thoughtText">
                        ${this.formatTextForDisplay(this.psychologistThought || 'Загрузка...')}
                    </div>
                    <div class="thought-buttons">
                        <button class="onboarding-btn secondary" id="backToDashboardFromThoughtBtn">◀️ НАЗАД</button>
                        <button class="onboarding-btn secondary" id="refreshThoughtBtn">🔄 ОБНОВИТЬ</button>
                    </div>
                </div>
            </div>
        `;
        
        const backBtn = document.getElementById('backToDashboardFromThoughtBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
        
        const refreshBtn = document.getElementById('refreshThoughtBtn');
        if (refreshBtn) refreshBtn.onclick = async () => {
            await this.loadPsychologistThought(true);
            this.renderPsychologistThoughtScreen();
        };
    }
    
    renderGoalsScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        const goals = this.getGoalsForDisplay();
        
        container.innerHTML = `
            <div class="choose-goal-container">
                <div class="choose-goal-content">
                    <h2 class="choose-goal-title">🎯 ВАШИ ЦЕЛИ</h2>
                    <div class="goal-description">
                        ${this.userName}, вот цели, которые подобраны под ваш профиль:
                    </div>
                    <div class="goals-list" id="goalsList">
                        ${goals.map(goal => `
                            <div class="goal-item" data-goal-id="${goal.id}">
                                <div class="goal-name">${goal.emoji || '🎯'} ${goal.name}</div>
                                <div class="goal-time">⏱ ${goal.time}</div>
                                <div class="goal-difficulty">${this.getDifficultyEmoji(goal.difficulty)} ${goal.difficulty}</div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="custom-goal">
                        <button class="onboarding-btn secondary" id="customGoalBtn">✏️ Сформулирую сам</button>
                    </div>
                    <div class="goal-back">
                        <button class="onboarding-btn secondary" id="backToDashboardFromGoalBtn">◀️ НАЗАД</button>
                    </div>
                </div>
            </div>
        `;
        
        document.querySelectorAll('.goal-item').forEach(item => {
            item.addEventListener('click', () => {
                this.showFloatingMessage('Цель выбрана! Скоро появится план достижения.', 'success');
            });
        });
        
        const customBtn = document.getElementById('customGoalBtn');
        if (customBtn) customBtn.onclick = () => this.showCustomGoalInput();
        
        const backBtn = document.getElementById('backToDashboardFromGoalBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
    }
    
    renderModeSelectionScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div class="choose-mode-container">
                <div class="choose-mode-content">
                    <h2 class="choose-mode-title">⚙️ ВЫБЕРИТЕ РЕЖИМ</h2>
                    <div class="mode-description">
                        Слушай, я могу быть разным. Хочешь конкретики — давай определимся.
                    </div>
                    <div class="mode-cards" id="modeCards">
                        <div class="mode-card ${this.mode === 'coach' ? 'active' : ''}" data-mode="coach">
                            <div class="mode-emoji">🔮</div>
                            <div class="mode-name">КОУЧ</div>
                            <div class="mode-desc">Помогаю найти ответы внутри себя</div>
                        </div>
                        <div class="mode-card ${this.mode === 'psychologist' ? 'active' : ''}" data-mode="psychologist">
                            <div class="mode-emoji">🧠</div>
                            <div class="mode-name">ПСИХОЛОГ</div>
                            <div class="mode-desc">Исследую глубинные паттерны</div>
                        </div>
                        <div class="mode-card ${this.mode === 'trainer' ? 'active' : ''}" data-mode="trainer">
                            <div class="mode-emoji">⚡</div>
                            <div class="mode-name">ТРЕНЕР</div>
                            <div class="mode-desc">Даю чёткие инструменты и задачи</div>
                        </div>
                    </div>
                    <div class="mode-back">
                        <button class="onboarding-btn secondary" id="backToDashboardFromModeBtn">◀️ НАЗАД</button>
                    </div>
                </div>
            </div>
        `;
        
        document.querySelectorAll('.mode-card').forEach(card => {
            card.addEventListener('click', async () => {
                const mode = card.dataset.mode;
                this.mode = mode;
                await this.saveMode(mode);
                this.showFloatingMessage(`Режим ${card.querySelector('.mode-name').textContent} активирован!`, 'success');
                this.renderDashboard();
            });
        });
        
        const backBtn = document.getElementById('backToDashboardFromModeBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
    }
    
    // ============================================
    // ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    // ============================================
    
    getPersonalizedModules() {
        return this.allModules;
    }
    
    extractProfileScores() {
        const defaultScores = { sb: 4, tf: 4, ub: 4, chv: 4 };
        if (!this.userData || !this.userData.profile_data) return defaultScores;
        
        return {
            sb: this.userData.profile_data.sb_level || 4,
            tf: this.userData.profile_data.tf_level || 4,
            ub: this.userData.profile_data.ub_level || 4,
            chv: this.userData.profile_data.chv_level || 4
        };
    }
    
    getGoalsForDisplay() {
        const scores = this.extractProfileScores();
        const weakest = Object.entries(scores).sort((a, b) => a[1] - b[1])[0]?.[0] || 'sb';
        
        const goalsMap = {
            sb: [
                { id: 'fear_work', name: 'Проработать страхи', time: '3-4 недели', difficulty: 'medium', emoji: '🛡️' },
                { id: 'boundaries', name: 'Научиться защищать границы', time: '2-3 недели', difficulty: 'medium', emoji: '🔒' }
            ],
            tf: [
                { id: 'money_blocks', name: 'Проработать денежные блоки', time: '3-4 недели', difficulty: 'medium', emoji: '💰' },
                { id: 'income_growth', name: 'Увеличить доход', time: '4-6 недель', difficulty: 'hard', emoji: '📈' }
            ],
            ub: [
                { id: 'meaning', name: 'Найти смысл', time: '4-6 недель', difficulty: 'hard', emoji: '🎯' },
                { id: 'system_thinking', name: 'Развить системное мышление', time: '3-5 недель', difficulty: 'medium', emoji: '🧩' }
            ],
            chv: [
                { id: 'relations', name: 'Улучшить отношения', time: '4-6 недель', difficulty: 'hard', emoji: '💕' },
                { id: 'attachment', name: 'Проработать привязанность', time: '5-7 недель', difficulty: 'hard', emoji: '🪢' }
            ]
        };
        
        const general = [
            { id: 'purpose', name: 'Найти предназначение', time: '5-7 недель', difficulty: 'hard', emoji: '🌟' },
            { id: 'balance', name: 'Обрести баланс', time: '4-6 недель', difficulty: 'medium', emoji: '⚖️' }
        ];
        
        const weakGoals = goalsMap[weakest] || goalsMap.sb;
        return [...weakGoals, ...general].slice(0, 5);
    }
    
    getDifficultyEmoji(difficulty) {
        const emojis = { easy: '🟢', medium: '🟡', hard: '🔴' };
        return emojis[difficulty] || '⚪';
    }
    
    getUserName() {
        return this.userName;
    }
    
    getUserAvatar() {
        const name = this.getUserName();
        const initial = name.charAt(0).toUpperCase();
        return `<div class="avatar-initial">${initial}</div>`;
    }
    
    formatTextForDisplay(text) {
        if (!text) return '';
        return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
    
    // ============================================
    // 🎤 ГОЛОСОВОЙ ВВОД (ПОЛНАЯ РАБОЧАЯ ВЕРСИЯ)
    // ============================================
    
    setupVoiceButton(button) {
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let recordingStartTime = null;
        let timerInterval = null;
        let stream = null;
        
        const voiceStatus = document.getElementById('voiceStatusDashboard');
        const timerEl = document.getElementById('dashboardRecordingTimer');
        
        const startRecording = async () => {
            try {
                console.log('🎤 Запрос доступа к микрофону...');
                
                stream = null;
                
                // Пробуем через MAX WebApp
                if (window.MAX && window.MAX.WebApp && window.MAX.WebApp.getUserMedia) {
                    try {
                        stream = await window.MAX.WebApp.getUserMedia({ audio: true });
                        console.log('✅ Доступ через MAX.WebApp');
                    } catch (e) {
                        console.warn('MAX getUserMedia failed:', e);
                    }
                }
                
                // Стандартный Web API
                if (!stream) {
                    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    console.log('✅ Доступ через Web API');
                }
                
                let mimeType = '';
                const mimeTypes = ['audio/webm', 'audio/mp4', 'audio/ogg'];
                for (const type of mimeTypes) {
                    if (MediaRecorder.isTypeSupported(type)) {
                        mimeType = type;
                        break;
                    }
                }
                
                mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = async () => {
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        stream = null;
                    }
                    
                    if (audioChunks.length === 0) {
                        this.showFloatingMessage('❌ Не удалось записать голос', 'error');
                        isRecording = false;
                        return;
                    }
                    
                    const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
                    
                    if (audioBlob.size < 5000) {
                        this.showFloatingMessage('❌ Запись слишком короткая', 'error');
                        isRecording = false;
                        return;
                    }
                    
                    await this.sendVoiceToServer(audioBlob);
                    isRecording = false;
                };
                
                mediaRecorder.start(1000);
                isRecording = true;
                recordingStartTime = Date.now();
                
                button.classList.add('recording');
                button.innerHTML = '<span class="voice-icon">⏹️</span><span class="voice-text">Отпустите</span>';
                if (voiceStatus) voiceStatus.style.display = 'flex';
                if (timerEl) timerEl.textContent = '0s';
                
                timerInterval = setInterval(() => {
                    if (isRecording && recordingStartTime) {
                        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                        if (timerEl) timerEl.textContent = `${elapsed}s`;
                        if (elapsed >= 30) stopRecording();
                    }
                }, 1000);
                
                setTimeout(() => {
                    if (isRecording) stopRecording();
                }, 30000);
                
            } catch (error) {
                console.error('Microphone error:', error);
                this.showFloatingMessage('❌ Не удалось получить доступ к микрофону', 'error');
                this._resetVoiceUI(button, voiceStatus, timerInterval);
            }
        };
        
        const stopRecording = () => {
            if (mediaRecorder && isRecording && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                isRecording = false;
                if (timerInterval) clearInterval(timerInterval);
            }
        };
        
        const cancelRecording = () => {
            if (mediaRecorder && isRecording) {
                mediaRecorder.onstop = null;
                mediaRecorder.stop();
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                    stream = null;
                }
                isRecording = false;
                if (timerInterval) clearInterval(timerInterval);
                this.showFloatingMessage('Запись отменена', 'info');
            }
            this._resetVoiceUI(button, voiceStatus, timerInterval);
        };
        
        // Очищаем старые обработчики
        button.removeEventListener('mousedown', startRecording);
        button.removeEventListener('mouseup', stopRecording);
        button.removeEventListener('mouseleave', stopRecording);
        button.removeEventListener('touchstart', startRecording);
        button.removeEventListener('touchend', stopRecording);
        
        // Добавляем новые
        button.addEventListener('mousedown', startRecording);
        button.addEventListener('mouseup', stopRecording);
        button.addEventListener('mouseleave', stopRecording);
        
        button.addEventListener('touchstart', (e) => { 
            e.preventDefault(); 
            startRecording(); 
        }, { passive: false });
        
        button.addEventListener('touchend', (e) => { 
            e.preventDefault(); 
            stopRecording(); 
        }, { passive: false });
    }
    
    _resetVoiceUI(button, voiceStatus, timerInterval) {
        if (button) {
            button.classList.remove('recording');
            button.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-text">Нажмите и говорите</span>';
        }
        if (voiceStatus) voiceStatus.style.display = 'none';
        if (timerInterval) clearInterval(timerInterval);
    }
    
    async sendVoiceToServer(audioBlob) {
        this.showFloatingMessage('🎤 Распознаю речь...', 'info');
        
        const formData = new FormData();
        formData.append('user_id', this.userId);
        formData.append('voice', audioBlob, 'voice.webm');
        
        const loadingToast = this.showLoadingToast('Распознавание речи...');
        
        try {
            const response = await fetch(`${window.api.baseUrl}/api/voice/process`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (loadingToast) loadingToast.remove();
            
            if (result.success) {
                if (result.recognized_text) {
                    this.showFloatingMessage(`📝 Вы сказали: ${result.recognized_text}`, 'success');
                    const questionInput = document.getElementById('questionInput');
                    if (questionInput) {
                        questionInput.value = result.recognized_text;
                        const sendBtn = document.getElementById('sendQuestionBtn');
                        if (sendBtn && result.recognized_text.length > 3) {
                            setTimeout(() => sendBtn.click(), 500);
                        }
                    }
                }
                if (result.answer) {
                    this.showFloatingMessage(result.answer, 'info');
                    this.playAudioResponse(result.audio_url);
                }
            } else {
                this.showFloatingMessage(result.error || 'Не удалось распознать речь', 'error');
            }
        } catch (error) {
            console.error('Send voice error:', error);
            if (loadingToast) loadingToast.remove();
            this.showFloatingMessage('❌ Ошибка отправки голоса', 'error');
        }
    }
    
    showLoadingToast(message) {
        const toast = document.createElement('div');
        toast.className = 'floating-message loading';
        toast.innerHTML = `
            <div class="floating-message-content">
                <div class="loading-spinner-small">🧠</div>
                <div class="floating-message-text">${message}</div>
            </div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);
        return toast;
    }
    
    playAudioResponse(audioUrl) {
        if (!audioUrl) return;
        const audio = document.getElementById('hiddenAudioPlayer');
        if (audio) {
            audio.src = audioUrl;
            audio.play().catch(e => console.warn('Audio play error:', e));
        }
    }
    
    // ============================================
    // ОБРАБОТЧИКИ СОБЫТИЙ
    // ============================================
    
    attachDashboardEvents() {
        document.querySelectorAll('.module-card').forEach(card => {
            card.addEventListener('click', () => {
                const moduleId = card.dataset.module;
                this.handleModuleClick(moduleId);
            });
        });
        
        document.querySelectorAll('.quick-action').forEach(action => {
            action.addEventListener('click', () => {
                const actionType = action.dataset.action;
                this.handleQuickAction(actionType);
            });
        });
        
        const voiceBtn = document.getElementById('dashboardVoiceBtn');
        if (voiceBtn) {
            this.setupVoiceButton(voiceBtn);
        }
    }
    
    handleQuickAction(actionType) {
        switch(actionType) {
            case 'mode': this.renderModeSelectionScreen(); break;
            case 'profile': this.renderProfileScreen(); break;
            case 'thoughts': this.renderPsychologistThoughtScreen(); break;
            case 'goals': this.renderGoalsScreen(); break;
        }
    }
    
    handleModuleClick(moduleId) {
        const messages = {
            strategy: '🎯 Стратегия: Давайте разберем ваши цели и построим план действий. Что для вас сейчас самое важное?',
            reputation: '🏆 Репутация: Ваша репутация формируется из того, как вы взаимодействуете с миром. Расскажите, что вас беспокоит?',
            goals: '📊 Цели: Ваши цели — это компас. Какая цель для вас сейчас главная?',
            entertainment: '🎮 Развлечения: Отдых так же важен, как и работа. Что вас расслабляет и вдохновляет?',
            psychology: '🧠 Психология: Давайте исследуем глубинные паттерны. Что происходит в вашем внутреннем мире?',
            habits: '🔄 Привычки: Маленькие действия каждый день создают большие изменения. Какую привычку хотите сформировать?',
            communication: '💬 Общение: Как строятся ваши отношения с людьми? Что хочется улучшить?',
            finance: '💰 Финансы: Деньги — это энергия. Как у вас с этим сейчас?',
            health: '❤️ Здоровье: Тело и психика связаны. Как вы заботитесь о себе?',
            creativity: '🎨 Творчество: Творчество — это способ самовыражения. Что мешает творить?'
        };
        
        const message = messages[moduleId] || `Расскажите подробнее о теме "${moduleId}"`;
        this.showFloatingMessage(message, 'info');
        this.sendQuestionToBot(message);
    }
    
    async sendQuestionToBot(question) {
        try {
            const result = await window.api.request('/api/chat/message', {
                method: 'POST',
                body: JSON.stringify({
                    user_id: this.userId,
                    message: question,
                    mode: this.mode
                })
            });
            
            if (result.success && result.response) {
                this.showFloatingMessage(result.response, 'info');
                if (result.audio_url) {
                    this.playAudioResponse(result.audio_url);
                }
            }
        } catch (error) {
            console.error('Send question error:', error);
            this.showFloatingMessage('❌ Ошибка отправки вопроса. Попробуйте позже.', 'error');
        }
    }
    
    async saveMode(mode) {
        try {
            await window.api.request('/api/save-mode', {
                method: 'POST',
                body: JSON.stringify({ user_id: this.userId, mode })
            });
        } catch (error) {
            console.error('Ошибка сохранения режима:', error);
        }
    }
    
    // ============================================
    // ВСПЛЫВАЮЩИЕ СООБЩЕНИЯ
    // ============================================
    
    showFloatingMessage(text, type = 'info') {
        const floatingMsg = document.getElementById('floatingMessage');
        const textEl = document.getElementById('floatingMessageText');
        
        if (!floatingMsg || !textEl) {
            console.warn('Floating message elements not found');
            return;
        }
        
        textEl.innerHTML = text;
        floatingMsg.className = `floating-message ${type}`;
        floatingMsg.style.display = 'block';
        
        setTimeout(() => {
            floatingMsg.style.display = 'none';
        }, 5000);
        
        const closeBtn = document.getElementById('floatingMessageClose');
        if (closeBtn) {
            closeBtn.onclick = () => floatingMsg.style.display = 'none';
        }
    }
    
    showError(message) {
        const container = document.getElementById('screenContainer');
        if (container) {
            container.innerHTML = `
                <div class="dashboard-error">
                    <div class="error-icon">⚠️</div>
                    <div class="error-title">Ошибка</div>
                    <div class="error-text">${message}</div>
                    <button class="onboarding-btn primary" id="retryInitBtn" style="margin-top: 24px;">🔄 ПОВТОРИТЬ</button>
                </div>
            `;
            
            const retryBtn = document.getElementById('retryInitBtn');
            if (retryBtn) retryBtn.onclick = () => location.reload();
        }
    }
    
    startTest() {
        window.location.hash = '#test';
        // Отправляем событие для навигации
        window.dispatchEvent(new CustomEvent('navigate', { detail: { screen: 'test' } }));
    }
    
    showSkipMessage() {
        this.showFloatingMessage('Тест поможет лучше понять вас и подобрать персональные рекомендации.', 'info');
    }
    
    showCustomGoalInput() {
        const goal = prompt('Сформулируйте свою цель своими словами:');
        if (goal?.trim()) {
            this.showFloatingMessage(`Цель принята: "${goal}"`, 'success');
        }
    }
    
    initVoiceInput() {
        window.startVoiceRecording = () => {
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) voiceBtn.dispatchEvent(new Event('mousedown'));
        };
    }
    
    // ============================================
    // АНИМИРОВАННЫЙ АВАТАР
    // ============================================
    
    async initAnimatedAvatar() {
        if (!window.AnimatedAvatar) {
            console.warn('AnimatedAvatar не загружен, использую обычный аватар');
            this._showFallbackAvatar();
            return;
        }
        
        try {
            const profileData = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
            
            this.animatedAvatar = new AnimatedAvatar(this.userId, this.userName, profileData);
            const avatarCanvas = await this.animatedAvatar.init();
            
            this.animatedAvatar.setSize(80, 80);
            
            const avatarContainer = document.getElementById('avatarContainer');
            if (avatarContainer) {
                avatarContainer.innerHTML = '';
                avatarContainer.appendChild(avatarCanvas);
            }
            
            this.animatedAvatar.onAvatarClick = () => {
                const moods = ['happy', 'thoughtful', 'energetic'];
                const randomMood = moods[Math.floor(Math.random() * moods.length)];
                this.animatedAvatar.setMood(randomMood);
                setTimeout(() => this.animatedAvatar.setMood('neutral'), 2000);
                this.showFloatingMessage('Привет! Как настроение?', 'info');
            };
            
            console.log('✅ Анимированный аватар инициализирован');
            
        } catch (error) {
            console.error('Ошибка инициализации аватара:', error);
            this._showFallbackAvatar();
        }
    }
    
    _showFallbackAvatar() {
        const avatarContainer = document.getElementById('avatarContainer');
        if (avatarContainer) {
            avatarContainer.innerHTML = this.getUserAvatar();
        }
    }
    
    // ============================================
    // ЧЕЛЛЕНДЖИ
    // ============================================
    
    async initChallenges() {
        if (!window.ChallengeManager) {
            console.warn('ChallengeManager не загружен');
            return;
        }
        
        try {
            this.challengeManager = new ChallengeManager(this.userId, this.userData);
            await this.challengeManager.init();
            
            this.challengeManager.addListener((event, data) => {
                if (event === 'level_up') {
                    this.showFloatingMessage(`🎉 Уровень ${data.level} достигнут!`, 'success');
                } else if (event === 'challenge_completed') {
                    this.showFloatingMessage(`🏆 Выполнен челлендж: ${data.name}`, 'success');
                }
            });
            
            this.renderChallengesWidget();
        } catch (error) {
            console.error('Ошибка инициализации челленджей:', error);
        }
    }
    
    renderChallengesWidget() {
        if (!this.challengeManager) return;
        
        const widgetHtml = this.challengeManager.renderWidget();
        const container = document.querySelector('.dashboard-container');
        if (!container) return;
        
        const existingWidget = document.querySelector('.challenges-widget');
        if (existingWidget) existingWidget.remove();
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = widgetHtml;
        const widget = tempDiv.firstElementChild;
        
        const modulesGrid = document.querySelector('.modules-grid');
        if (modulesGrid) {
            modulesGrid.parentNode.insertBefore(widget, modulesGrid.nextSibling);
        } else {
            container.appendChild(widget);
        }
        
        this.attachChallengeEvents();
    }
    
    attachChallengeEvents() {
        document.querySelectorAll('.challenge-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const challengeId = item.dataset.challengeId;
                const challenge = this.challengeManager?.dailyChallenges.find(c => c.id === challengeId) ||
                                 this.challengeManager?.weeklyChallenges.find(c => c.id === challengeId) ||
                                 this.challengeManager?.specialChallenges.find(c => c.id === challengeId);
                if (challenge && !challenge.completed) {
                    this.showFloatingMessage(challenge.description, 'info');
                }
            });
        });
    }
    
    // ============================================
    // ПСИХОМЕТРИЧЕСКИЕ ДВОЙНИКИ
    // ============================================
    
    async initPsychometricDoubles() {
        if (!window.PsychometricDoubles) {
            console.warn('PsychometricDoubles не загружен');
            return;
        }
        
        try {
            const profileData = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
            
            const userProfile = {
                sb: profileData.profile_data?.sb_level || 4,
                tf: profileData.profile_data?.tf_level || 4,
                ub: profileData.profile_data?.ub_level || 4,
                chv: profileData.profile_data?.chv_level || 4
            };
            
            this.psychometric = new PsychometricDoubles(this.userId, userProfile);
            await this.psychometric.init();
            
            this.renderDoublesSection();
        } catch (error) {
            console.error('Ошибка инициализации двойников:', error);
        }
    }
    
    renderDoublesSection() {
        if (!this.psychometric || this.psychometric.doubles.length === 0) return;
        
        const doublesSection = document.createElement('div');
        doublesSection.className = 'doubles-section';
        doublesSection.innerHTML = `
            <div class="doubles-header">
                <div class="doubles-title">
                    <span class="doubles-title-emoji">👥</span>
                    Психометрические двойники
                </div>
                <button class="doubles-refresh" id="refreshDoublesBtn">🔄</button>
            </div>
            <div class="doubles-list" id="doublesList">
                ${this.psychometric.doubles.map(d => {
                    const compatibility = this.psychometric.calculateCompatibility(
                        this.psychometric.userProfile, 
                        d.profile
                    );
                    return this.psychometric.renderDoubleCard(d, compatibility);
                }).join('')}
            </div>
        `;
        
        const container = document.querySelector('.dashboard-container');
        if (container) {
            const existing = document.querySelector('.doubles-section');
            if (existing) existing.remove();
            
            const challengesWidget = document.querySelector('.challenges-widget');
            if (challengesWidget) {
                challengesWidget.parentNode.insertBefore(doublesSection, challengesWidget.nextSibling);
            } else {
                container.appendChild(doublesSection);
            }
        }
        
        this.attachDoublesEvents();
    }
    
    attachDoublesEvents() {
        const refreshBtn = document.getElementById('refreshDoublesBtn');
        if (refreshBtn) {
            refreshBtn.onclick = async () => {
                const listContainer = document.getElementById('doublesList');
                if (listContainer) listContainer.innerHTML = '<div class="doubles-empty">🔍 Обновление списка...</div>';
                await this.psychometric.findDoubles();
                this.renderDoublesSection();
            };
        }
        
        document.querySelectorAll('.double-message-btn').forEach(btn => {
            btn.onclick = (e) => {
                const doubleId = btn.dataset.doubleId;
                const double = this.psychometric.doubles.find(d => d.id == doubleId);
                if (double) this.showChatModal(double);
            };
        });
        
        document.querySelectorAll('.double-details-btn').forEach(btn => {
            btn.onclick = (e) => {
                const doubleId = btn.dataset.doubleId;
                const double = this.psychometric.doubles.find(d => d.id == doubleId);
                if (double) this.showDoubleProfile(double);
            };
        });
    }
    
    showChatModal(double) {
        if (!this.psychometric) return;
        
        const modalHtml = this.psychometric.renderChatModal(double);
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);
        
        const closeBtn = document.getElementById('closeChatModal');
        if (closeBtn) closeBtn.onclick = () => modalContainer.remove();
        
        const sendBtn = document.getElementById('sendChatMessage');
        const input = document.getElementById('chatMessageInput');
        
        const sendMessage = async () => {
            const message = input.value.trim();
            if (!message) return;
            
            const messagesList = document.getElementById('messagesList');
            if (messagesList) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message user-message';
                messageDiv.innerHTML = `<div class="message-bubble">${message}</div><div class="message-time">только что</div>`;
                messagesList.appendChild(messageDiv);
                messagesList.scrollTop = messagesList.scrollHeight;
            }
            
            input.value = '';
            const success = await this.psychometric.sendMessage(double.id, message);
            
            if (success) {
                setTimeout(() => this.addBotReply(double, messagesList), 1000);
            }
        };
        
        if (sendBtn) sendBtn.onclick = sendMessage;
        if (input) input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        
        modalContainer.querySelector('.modal-overlay').onclick = (e) => {
            if (e.target === modalContainer.querySelector('.modal-overlay')) modalContainer.remove();
        };
    }
    
    addBotReply(double, messagesList) {
        const compatibility = this.psychometric?.calculateCompatibility(
            this.psychometric.userProfile, 
            double.profile
        ) || { score: 85 };
        
        const replies = [
            `Привет! Рад познакомиться! У нас ${compatibility.score}% совместимости!`,
            `Ого, у нас очень похожий профиль! Как у тебя дела?`,
            `Здорово, что нас свела система! Расскажи, как у тебя дела?`,
            `Привет-привет! Смотрю на твой профиль — мы очень похожи. Как проходит твой день?`
        ];
        
        const randomReply = replies[Math.floor(Math.random() * replies.length)];
        const replyDiv = document.createElement('div');
        replyDiv.className = 'message bot-message';
        replyDiv.innerHTML = `<div class="message-bubble">${randomReply}</div><div class="message-time">только что</div>`;
        messagesList.appendChild(replyDiv);
        messagesList.scrollTop = messagesList.scrollHeight;
    }
    
    showDoubleProfile(double) {
        this.showFloatingMessage(`👤 ${double.first_name} ${double.last_name || ''}\n📊 Профиль: ${double.profile_code}`, 'info');
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM загружен, создаём FrediDashboard');
    window.dashboard = new FrediDashboard();
});

window.FrediDashboard = FrediDashboard;
