// ============================================
// ЛИЧНЫЙ КАБИНЕТ - КОНСОРЦИУМ ФРЕДИ
// Версия 3.2 - УНИВЕРСАЛЬНАЯ (веб + мобильный MAX)
// ============================================

class FrediDashboard {
    constructor() {
        this.userId = window.maxContext?.user_id || localStorage.getItem('fredi_user_id');
        this.userData = null;
        this.userName = 'Друг';
        this.isTestCompleted = false;
        this.profileCode = null;
        this.mode = 'coach';
        this.currentScreen = 'dashboard';
        this.daysActive = 3;
        this.sessionsCount = 12;
        this.profileText = null;
        this.psychologistThought = null;
        
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
        
        // Откладываем инициализацию до загрузки API
        this.initPromise = this.init();
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ С ОЖИДАНИЕМ API
    // ============================================
    
    async init() {
        console.log('🎯 Инициализация личного кабинета...');
        console.log('📱 Режим WebView:', this.isWebView);
        
        // ✅ ЖДЁМ ЗАГРУЗКИ API (до 5 секунд, проверяем каждые 100мс)
        let attempts = 0;
        const maxAttempts = 50; // 5 секунд
        
        while (!window.api && attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 100));
            attempts++;
            if (attempts % 10 === 0) {
                console.log(`⏳ Ожидание window.api... ${attempts * 100}мс`);
            }
        }
        
        if (!window.api) {
            console.error('❌ window.api не загружен!');
            this.showError('Не удалось загрузить API. Проверьте соединение и перезагрузите страницу.');
            return;
        }
        
        console.log('✅ window.api доступен');
        
        if (!this.userId) {
            this.showError('Не удалось идентифицировать пользователя. Пожалуйста, откройте приложение через MAX.');
            return;
        }
        
        try {
            await this.loadUserData();
            await this.loadProfileData();
            await this.loadPsychologistThought();
            this.renderDashboard();
            this.initVoiceInput();
            
            if (this.isTestCompleted) {
                await this.initAnimatedAvatar();
            }
        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
            this.showError('Ошибка загрузки данных. Попробуйте обновить страницу.');
        }
    }
    
    // ============================================
    // ПРОВЕРКА ПОДДЕРЖКИ МИКРОФОНА
    // ============================================
    
    checkMicrophoneSupport() {
        if (window.MAX && window.MAX.WebApp) {
            console.log('✅ MAX WebApp доступен');
            if (window.MAX.WebApp.isMediaSupported && window.MAX.WebApp.isMediaSupported('audio')) {
                console.log('✅ MAX поддерживает аудио');
                return true;
            }
            if (window.MAX.WebApp.getUserMedia) {
                console.log('✅ MAX имеет getUserMedia');
                return true;
            }
        }
        
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('⚠️ getUserMedia не поддерживается в этом браузере');
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) {
                voiceBtn.disabled = true;
                voiceBtn.style.opacity = '0.5';
                voiceBtn.title = 'Голосовой ввод не поддерживается в этом браузере';
            }
            return false;
        }
        
        console.log('✅ Микрофон поддерживается через Web API');
        return true;
    }
    
    // ============================================
    // ЗАПРОС РАЗРЕШЕНИЯ НА МИКРОФОН
    // ============================================
    
    async requestMicrophonePermission() {
        try {
            console.log('🎤 Проверка доступа к микрофону...');
            
            let stream = null;
            
            if (window.MAX && window.MAX.WebApp && window.MAX.WebApp.getUserMedia) {
                try {
                    stream = await window.MAX.WebApp.getUserMedia({ audio: true });
                    console.log('✅ Микрофон доступен через MAX');
                } catch (e) {
                    console.warn('MAX getUserMedia не сработал:', e);
                }
            }
            
            if (!stream) {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('✅ Микрофон доступен через Web API');
            }
            
            stream.getTracks().forEach(track => track.stop());
            return true;
            
        } catch (error) {
            console.error('❌ Ошибка доступа к микрофону:', error);
            
            if (error.name === 'NotAllowedError') {
                this.showMicrophoneInstructions();
            } else if (error.name === 'NotFoundError') {
                this.showFloatingMessage('❌ Микрофон не найден. Подключите гарнитуру.', 'error');
            } else {
                this.showFloatingMessage('❌ Не удалось получить доступ к микрофону', 'error');
            }
            return false;
        }
    }
    
    showMicrophoneInstructions() {
        const isAndroid = /Android/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        
        let instructions = '';
        
        if (isAndroid) {
            instructions = `
🔊 <b>ВКЛЮЧИТЕ МИКРОФОН В MAX</b>
<br><br>
1️⃣ Закройте чат с ботом
<br>
2️⃣ Откройте <b>Настройки</b> телефона
<br>
3️⃣ Перейдите в <b>Приложения</b> → <b>MAX</b>
<br>
4️⃣ Нажмите <b>Разрешения</b>
<br>
5️⃣ Включите <b>Микрофон</b> → <b>Разрешить</b>
<br><br>
6️⃣ Вернитесь в чат и нажмите 🎤 ещё раз
            `;
        } else if (isIOS) {
            instructions = `
🎤 <b>ВКЛЮЧИТЕ МИКРОФОН В MAX</b>
<br><br>
1️⃣ Закройте чат с ботом
<br>
2️⃣ Откройте <b>Настройки</b> iPhone
<br>
3️⃣ Прокрутите вниз → найдите <b>MAX</b>
<br>
4️⃣ Включите переключатель <b>Микрофон</b>
<br><br>
5️⃣ Вернитесь в чат и нажмите 🎤 ещё раз
            `;
        } else {
            instructions = `
🎤 <b>НУЖЕН ДОСТУП К МИКРОФОНУ</b>
<br><br>
В настройках приложения MAX разрешите доступ к микрофону.
<br><br>
Затем вернитесь и нажмите 🎤 ещё раз.
            `;
        }
        
        const modal = document.createElement('div');
        modal.className = 'microphone-modal';
        modal.innerHTML = `
            <div class="microphone-modal-content">
                <div style="font-size:48px;margin-bottom:16px;">🎤</div>
                <h3 style="margin:0 0 12px 0;">Нужен доступ к микрофону</h3>
                <div style="color:var(--max-text-secondary,#8e9aa6);line-height:1.6;text-align:left;font-size:14px;">
                    ${instructions}
                </div>
                <div style="display:flex;gap:12px;margin-top:28px;">
                    <button id="microphoneRetryBtn" class="modal-btn primary">🔄 ПРОВЕРИТЬ</button>
                    <button id="microphoneCloseBtn" class="modal-btn secondary">📱 ЗАКРЫТЬ</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('microphoneRetryBtn')?.addEventListener('click', () => {
            modal.remove();
            this.requestMicrophonePermission();
        });
        document.getElementById('microphoneCloseBtn')?.addEventListener('click', () => modal.remove());
    }
    
    // ============================================
    // ЗАГРУЗКА ДАННЫХ
    // ============================================
    
    async loadUserData() {
        try {
            // Запрос статуса
            const status = await window.api.request(`/api/user-status?user_id=${this.userId}`);
            
            // Если профиля нет в памяти — загружаем из БД
            if (!status.has_profile && !status.test_completed) {
                console.log('🔄 Профиль не найден в памяти, загружаем из БД...');
                
                const loadResult = await window.api.request('/api/force-load-user', {
                    method: 'POST',
                    body: JSON.stringify({ user_id: this.userId })
                });
                
                if (loadResult.success && loadResult.has_profile) {
                    console.log('✅ Профиль загружен из БД!');
                    const newStatus = await window.api.request(`/api/user-status?user_id=${this.userId}`);
                    this.isTestCompleted = newStatus.test_completed || newStatus.has_profile;
                    this.profileCode = newStatus.profile_code;
                } else {
                    this.isTestCompleted = false;
                    console.log('❌ Профиль не найден в БД');
                }
            } else {
                this.isTestCompleted = status.test_completed || status.has_profile;
                this.profileCode = status.profile_code;
            }
            
            // Загружаем имя пользователя
            try {
                const userData = await window.api.request(`/api/user-data?user_id=${this.userId}`);
                if (userData && userData.user_name) {
                    this.userName = userData.user_name;
                    console.log('👤 Имя пользователя загружено из БД:', this.userName);
                }
            } catch (nameError) {
                console.warn('Не удалось загрузить имя из БД:', nameError);
            }
            
            // Если имя не загрузилось, пробуем из MAX.WebApp
            if (this.userName === 'Друг' && window.MAX?.WebApp?.initDataUnsafe?.user?.first_name) {
                this.userName = window.MAX.WebApp.initDataUnsafe.user.first_name;
                console.log('👤 Имя получено из MAX.WebApp:', this.userName);
            }
            
            // Если тест пройден, загружаем полный профиль
            if (this.isTestCompleted) {
                const profile = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
                this.userData = profile;
            }
            
            // Загружаем статистику
            try {
                const stats = await window.api.request(`/api/user-full-status?user_id=${this.userId}`);
                if (stats.days_active) this.daysActive = stats.days_active;
                if (stats.sessions_count) this.sessionsCount = stats.sessions_count;
            } catch (statsError) {
                console.warn('Не удалось загрузить статистику:', statsError);
            }
            
            console.log('📊 Данные пользователя:', { 
                userId: this.userId, 
                userName: this.userName,
                testCompleted: this.isTestCompleted,
                profileCode: this.profileCode
            });
            
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
            this.isTestCompleted = false;
        }
    }
    
    // ============================================
    // ЗАГРУЗКА ПРОФИЛЯ
    // ============================================
    
    async loadProfileData() {
        try {
            const response = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
            
            if (response.ai_generated_profile) {
                this.profileText = response.ai_generated_profile;
            } else if (response.profile_data) {
                this.profileText = this.formatProfileText(response);
            } else {
                this.profileText = 'Профиль пока не сформирован. Пройдите тест.';
            }
            
            console.log('✅ Профиль загружен');
        } catch (error) {
            console.error('Ошибка загрузки профиля:', error);
            this.profileText = 'Ошибка загрузки профиля. Попробуйте позже.';
        }
    }
    
    // ============================================
    // ЗАГРУЗКА МЫСЛЕЙ ПСИХОЛОГА
    // ============================================
    
    async loadPsychologistThought() {
        try {
            const response = await window.api.request(`/api/thought?user_id=${this.userId}`);
            this.psychologistThought = response.thought || 'Мысли психолога еще не сгенерированы. Пройдите тест для получения персонального анализа.';
            console.log('✅ Мысли психолога загружены');
        } catch (error) {
            console.error('Ошибка загрузки мыслей психолога:', error);
            this.psychologistThought = 'Мысли психолога пока недоступны. Попробуйте позже.';
        }
    }
    
    // ============================================
    // ФОРМАТИРОВАНИЕ ТЕКСТА ПРОФИЛЯ
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
    // ИНИЦИАЛИЗАЦИЯ АНИМИРОВАННОГО АВАТАРА
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
    // ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ УЛУЧШЕНИЙ
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
    
    async initNotifications() {
        if (!window.NotificationManager) {
            console.warn('NotificationManager не загружен');
            return;
        }
        
        try {
            this.notificationManager = new NotificationManager(this.userId, this.userName);
            await this.notificationManager.init();
        } catch (error) {
            console.error('Ошибка инициализации уведомлений:', error);
        }
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
                    </div>
                </div>
            </div>
        `;
        
        const backBtn = document.getElementById('backToDashboardBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
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
                    </div>
                </div>
            </div>
        `;
        
        const backBtn = document.getElementById('backToDashboardFromThoughtBtn');
        if (backBtn) backBtn.onclick = () => this.renderDashboard();
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
                        <div class="mode-card" data-mode="coach">
                            <div class="mode-emoji">🔮</div>
                            <div class="mode-name">КОУЧ</div>
                            <div class="mode-desc">Помогаю найти ответы внутри себя</div>
                        </div>
                        <div class="mode-card" data-mode="psychologist">
                            <div class="mode-emoji">🧠</div>
                            <div class="mode-name">ПСИХОЛОГ</div>
                            <div class="mode-desc">Исследую глубинные паттерны</div>
                        </div>
                        <div class="mode-card" data-mode="trainer">
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
    // ВИДЖЕТЫ
    // ============================================
    
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
    
    // ============================================
    // ПЕРСОНАЛИЗАЦИЯ МОДУЛЕЙ
    // ============================================
    
    getPersonalizedModules() {
        return this.allModules;
    }
    
    extractProfileScores() {
        const defaultScores = { sb: 4, tf: 4, ub: 4, chv: 4 };
        
        if (!this.userData || !this.userData.profile_data) {
            return defaultScores;
        }
        
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
    
    getDaysActive() {
        return this.daysActive;
    }
    
    getSessionsCount() {
        return this.sessionsCount;
    }
    
    formatTextForDisplay(text) {
        if (!text) return '';
        return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
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
    
    // ============================================
    // 🎤 ГОЛОСОВОЙ ВВОД
    // ============================================
    
    setupVoiceButton(button) {
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let recordingStartTime = null;
        let timerInterval = null;
        
        const voiceStatus = document.getElementById('voiceStatusDashboard');
        const timerEl = document.getElementById('dashboardRecordingTimer');
        
        const isSamsung = /Samsung|SM-|GT-|SHV-|SCH-|SPH-/.test(navigator.userAgent);
        
        if (isSamsung || this.isWebView) {
            console.log('📱 Обнаружен Samsung/WebView, применяем специальные настройки');
            this.showFloatingMessage('🔊 Нажмите разрешить, когда приложение запросит доступ к микрофону', 'info');
        }
        
        const startRecording = async () => {
            try {
                console.log('🎤 Запрос доступа к микрофону...');
                
                let stream = null;
                let mimeType = '';
                
                if (window.MAX && window.MAX.WebApp && window.MAX.WebApp.getUserMedia) {
                    try {
                        console.log('🎤 Пробуем через MAX WebApp...');
                        stream = await window.MAX.WebApp.getUserMedia({ 
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true,
                                sampleRate: 16000
                            } 
                        });
                        console.log('✅ Доступ к микрофону через MAX');
                    } catch (e) {
                        console.warn('MAX getUserMedia не сработал:', e);
                        if (isSamsung) {
                            this.showFloatingMessage('🔊 На Samsung: проверьте разрешения в настройках MAX', 'info');
                        }
                    }
                }
                
                if (!stream) {
                    try {
                        console.log('🎤 Пробуем через Web API...');
                        const constraints = {
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true,
                                sampleRate: 16000,
                                channelCount: 1
                            }
                        };
                        
                        stream = await navigator.mediaDevices.getUserMedia(constraints).catch(async () => {
                            console.log('🎤 Пробуем без параметров...');
                            return await navigator.mediaDevices.getUserMedia({ audio: true });
                        });
                        
                        console.log('✅ Доступ к микрофону через Web API');
                    } catch (webError) {
                        console.error('Web API ошибка:', webError);
                        throw webError;
                    }
                }
                
                const mimeTypes = [
                    'audio/webm',
                    'audio/mp4',
                    'audio/ogg',
                    'audio/3gpp',
                    'audio/mpeg'
                ];
                
                for (const type of mimeTypes) {
                    if (MediaRecorder.isTypeSupported(type)) {
                        mimeType = type;
                        break;
                    }
                }
                
                console.log('📱 Используем MIME тип:', mimeType || 'default');
                
                const options = mimeType ? { mimeType } : {};
                mediaRecorder = new MediaRecorder(stream, options);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = async () => {
                    stream.getTracks().forEach(track => track.stop());
                    
                    let audioBlob;
                    const finalMimeType = mimeType || 'audio/webm';
                    
                    if (audioChunks.length > 0) {
                        audioBlob = new Blob(audioChunks, { type: finalMimeType });
                    } else {
                        console.warn('⚠️ Нет аудиоданных');
                        this.showFloatingMessage('❌ Не удалось записать голос. Попробуйте еще раз.', 'error');
                        this._resetVoiceUI(button, voiceStatus, timerInterval);
                        return;
                    }
                    
                    if (audioBlob.size < 5000) {
                        console.warn('⚠️ Аудиофайл слишком маленький:', audioBlob.size);
                        this.showFloatingMessage('❌ Запись слишком короткая. Поговорите дольше.', 'error');
                        this._resetVoiceUI(button, voiceStatus, timerInterval);
                        return;
                    }
                    
                    await this.sendVoiceToServer(audioBlob);
                    this._resetVoiceUI(button, voiceStatus, timerInterval);
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
                
                setTimeout(() => { if (isRecording) stopRecording(); }, 30000);
                
            } catch (error) {
                console.error('Microphone error:', error);
                
                let errorMessage = '❌ Не удалось получить доступ к микрофону.';
                
                if (isSamsung) {
                    errorMessage = '🔊 На Samsung:\n\n1. Настройки телефона → Приложения → MAX\n2. Разрешения → Микрофон → Разрешить\n3. Вернитесь и нажмите 🎤';
                } else if (error.name === 'NotAllowedError' || error.message?.includes('permission')) {
                    if (this.isWebView) {
                        errorMessage = '🔊 РАЗРЕШИТЕ ДОСТУП К МИКРОФОНУ В MAX:\n\n1. Закройте чат\n2. Настройки телефона → Приложения → MAX\n3. Разрешения → Микрофон → Разрешить\n4. Вернитесь и нажмите 🎤';
                    } else {
                        errorMessage = '❌ Разрешение на использование микрофона отклонено.\n\nПроверьте настройки разрешений.';
                    }
                } else if (error.name === 'NotFoundError') {
                    errorMessage = '❌ Микрофон не найден. Подключите гарнитуру.';
                } else if (error.name === 'NotReadableError') {
                    errorMessage = '❌ Микрофон занят другим приложением.';
                }
                
                this.showFloatingMessage(errorMessage, 'error');
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
        
        button.removeEventListener('mousedown', startRecording);
        button.removeEventListener('mouseup', stopRecording);
        button.removeEventListener('mouseleave', stopRecording);
        button.removeEventListener('touchstart', startRecording);
        button.removeEventListener('touchend', stopRecording);
        
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
        
        try {
            const response = await fetch(`${window.api.baseUrl}/api/voice/process`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
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
            this.showFloatingMessage('❌ Ошибка отправки голоса. Попробуйте позже.', 'error');
        }
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
    // ОБРАБОТЧИКИ МОДУЛЕЙ
    // ============================================
    
    handleQuickAction(actionType) {
        if (this.animatedAvatar) {
            this.animatedAvatar.setMood('happy');
            setTimeout(() => this.animatedAvatar.setMood('neutral'), 1500);
        }
        
        switch(actionType) {
            case 'mode':
                this.renderModeSelectionScreen();
                break;
            case 'profile':
                this.renderProfileScreen();
                break;
            case 'thoughts':
                this.renderPsychologistThoughtScreen();
                break;
            case 'goals':
                this.renderGoalsScreen();
                break;
        }
    }
    
    handleModuleClick(moduleId) {
        if (this.animatedAvatar) {
            this.animatedAvatar.setMood('thoughtful');
            setTimeout(() => this.animatedAvatar.setMood('neutral'), 1500);
        }
        
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
        
        if (this.challengeManager) {
            this.challengeManager.onQuestionAsked();
        }
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
        
        if (!floatingMsg || !textEl) return;
        
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
    
    // ============================================
    // ЧАТ С ДВОЙНИКОМ
    // ============================================
    
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
    
    // ============================================
    // ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    // ============================================
    
    startTest() {
        window.location.hash = '#test';
    }
    
    showSkipMessage() {
        this.showFloatingMessage('Тест поможет лучше понять вас и подобрать персональные рекомендации.', 'info');
    }
    
    showError(message) {
        const container = document.getElementById('screenContainer');
        if (container) {
            container.innerHTML = `
                <div class="dashboard-error">
                    <div class="error-icon">⚠️</div>
                    <div class="error-title">Ошибка</div>
                    <div class="error-text">${message}</div>
                </div>
            `;
        }
    }
    
    initVoiceInput() {
        window.startVoiceRecording = () => {
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) voiceBtn.dispatchEvent(new Event('mousedown'));
        };
    }
    
    showCustomGoalInput() {
        const goal = prompt('Сформулируйте свою цель своими словами:');
        if (goal?.trim()) {
            this.showFloatingMessage(`Цель принята: "${goal}"`, 'success');
        }
    }
}

// Инициализация при загрузке страницы
// НЕ СОЗДАЁМ dashboard СРАЗУ — ждём DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM загружен, создаём FrediDashboard');
    window.dashboard = new FrediDashboard();
});

window.FrediDashboard = FrediDashboard;
