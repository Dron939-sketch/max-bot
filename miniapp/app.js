// ============================================
// ЛИЧНЫЙ КАБИНЕТ - КОНСОРЦИУМ ФРЕДИ
// Версия 2.0 - полная интеграция с челленджами, уведомлениями, двойниками
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
        
        // Модули
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
        
        // Модули консорциума
        this.allModules = [
            { id: 'strategy', name: '🎯 Стратегия', icon: '🎯', color: '#4CAF50', requiresTest: true, description: 'Построение планов и достижение целей', weakVector: 'sb' },
            { id: 'reputation', name: '🏆 Репутация', icon: '🏆', color: '#FF9800', requiresTest: true, description: 'Управление впечатлением и авторитетом', weakVector: 'chv' },
            { id: 'goals', name: '📊 Цели', icon: '📊', color: '#2196F3', requiresTest: true, description: 'Ваши цели и задачи', weakVector: null },
            { id: 'entertainment', name: '🎮 Развлечения', icon: '🎮', color: '#9C27B0', requiresTest: false, description: 'Идеи для отдыха', weakVector: null },
            { id: 'psychology', name: '🧠 Психология', icon: '🧠', color: '#E91E63', requiresTest: true, description: 'Глубинные паттерны', weakVector: 'ub' },
            { id: 'habits', name: '🔄 Привычки', icon: '🔄', color: '#00BCD4', requiresTest: true, description: 'Полезные привычки', weakVector: null },
            { id: 'communication', name: '💬 Общение', icon: '💬', color: '#3F51B5', requiresTest: false, description: 'Советы по общению', weakVector: 'chv' },
            { id: 'finance', name: '💰 Финансы', icon: '💰', color: '#FFC107', requiresTest: true, description: 'Управление деньгами', weakVector: 'tf' },
            { id: 'health', name: '❤️ Здоровье', icon: '❤️', color: '#F44336', requiresTest: false, description: 'Забота о себе', weakVector: null },
            { id: 'creativity', name: '🎨 Творчество', icon: '🎨', color: '#FF6B6B', requiresTest: false, description: 'Вдохновение и идеи', weakVector: null }
        ];
        
        this.init();
    }
    
    async init() {
        console.log('🎯 Инициализация личного кабинета...');
        
        if (!this.userId) {
            this.showError('Не удалось идентифицировать пользователя');
            return;
        }
        
        await this.loadUserData();
        this.renderDashboard();
        this.initVoiceInput();
        
        // Инициализация дополнительных модулей после загрузки данных
        if (this.isTestCompleted) {
            await this.initChallenges();
            await this.initPsychometricDoubles();
            await this.initNotifications();
        }
    }
    
    // ============================================
    // ЗАГРУЗКА ДАННЫХ
    // ============================================
    
    async loadUserData() {
        try {
            // 1. Получаем статус пользователя
            const statusResponse = await fetch(`/api/user-status?user_id=${this.userId}`);
            const status = await statusResponse.json();
            
            this.isTestCompleted = status.test_completed || status.has_profile;
            this.profileCode = status.profile_code;
            
            // 2. Загружаем имя пользователя из БД
            try {
                const userDataResponse = await fetch(`/api/user-data?user_id=${this.userId}`);
                const userData = await userDataResponse.json();
                if (userData && userData.user_name) {
                    this.userName = userData.user_name;
                    console.log('👤 Имя пользователя загружено из БД:', this.userName);
                }
            } catch (nameError) {
                console.warn('Не удалось загрузить имя из БД:', nameError);
            }
            
            // 3. Если имя всё ещё не загружено, пробуем из MAX.WebApp
            if (this.userName === 'Друг' && window.MAX?.WebApp?.initDataUnsafe?.user?.first_name) {
                this.userName = window.MAX.WebApp.initDataUnsafe.user.first_name;
                console.log('👤 Имя получено из MAX.WebApp:', this.userName);
            }
            
            // 4. Если тест пройден, загружаем полные данные профиля
            if (status.has_profile || status.has_interpretation) {
                const profileResponse = await fetch(`/api/get-profile?user_id=${this.userId}`);
                const profile = await profileResponse.json();
                this.userData = profile;
            }
            
            // 5. Загружаем статистику
            try {
                const statsResponse = await fetch(`/api/user-full-status?user_id=${this.userId}`);
                const stats = await statsResponse.json();
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
    // ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ
    // ============================================
    
    async initChallenges() {
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
        try {
            // Загружаем профиль пользователя для поиска двойников
            const profileResponse = await fetch(`/api/get-profile?user_id=${this.userId}`);
            const profileData = await profileResponse.json();
            
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
        const personalizedModules = this.getPersonalizedModules();
        
        container.innerHTML = `
            <div class="dashboard-container">
                <!-- Верхняя панель с профилем -->
                <div class="dashboard-header">
                    <div class="user-welcome">
                        <div class="user-avatar" id="avatarContainer"></div>
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
                
                <!-- Голосовой ввод -->
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
                
                <!-- Модули-ярлыки -->
                <div class="modules-grid" id="modulesGrid">
                    ${personalizedModules.map(module => `
                        <div class="module-card" data-module="${module.id}" style="border-left-color: ${module.color}">
                            <div class="module-icon">${module.icon}</div>
                            <div class="module-name">${module.name}</div>
                            <div class="module-desc">${module.description || ''}</div>
                        </div>
                    `).join('')}
                </div>
                
                <!-- Быстрые действия -->
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
                
                <!-- Всплывающее окно для сообщений -->
                <div class="floating-message" id="floatingMessage" style="display: none;">
                    <div class="floating-message-content">
                        <div class="floating-message-text" id="floatingMessageText"></div>
                        <div class="floating-message-close" id="floatingMessageClose">✕</div>
                    </div>
                </div>
            </div>
        `;
        
        this.attachDashboardEvents();
        this.initAnimatedAvatar();
    }
    
    // ============================================
    // АНИМИРОВАННЫЙ АВАТАР
    // ============================================
    
    async initAnimatedAvatar() {
        if (!window.AnimatedAvatar) return;
        
        try {
            const profileResponse = await fetch(`/api/get-profile?user_id=${this.userId}`);
            const profileData = await profileResponse.json();
            
            this.animatedAvatar = new AnimatedAvatar(this.userId, this.userName, profileData);
            const avatarCanvas = await this.animatedAvatar.init();
            
            const avatarContainer = document.getElementById('avatarContainer');
            if (avatarContainer) {
                avatarContainer.innerHTML = '';
                avatarContainer.appendChild(avatarCanvas);
            }
            
            this.animatedAvatar.onAvatarClick = () => {
                const moods = ['happy', 'thoughtful', 'energetic'];
                const randomMood = moods[Math.floor(Math.random() * moods.length)];
                this.animatedAvatar.setMood(randomMood);
                setTimeout(() => this.animatedAvatar.setMood('neutral'), 3000);
            };
        } catch (error) {
            console.warn('Ошибка инициализации аватара:', error);
        }
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
    // ПЕРСОНАЛИЗАЦИЯ
    // ============================================
    
    getPersonalizedModules() {
        if (!this.isTestCompleted) {
            return [
                { id: 'test', name: '🧪 Пройти тест', icon: '🧪', color: '#FF9800', description: 'Узнайте свой профиль' },
                { id: 'entertainment', name: '🎮 Развлечения', icon: '🎮', color: '#9C27B0', description: 'Идеи для досуга' },
                { id: 'communication', name: '💬 Общение', icon: '💬', color: '#3F51B5', description: 'Советы по общению' }
            ];
        }
        
        const profileScores = this.extractProfileScores();
        const modules = [];
        
        if (profileScores.sb < 3) {
            modules.push({ id: 'strategy', name: '🎯 Стратегия', icon: '🎯', color: '#4CAF50', description: 'Укрепляем границы' });
        }
        if (profileScores.tf < 3) {
            modules.push({ id: 'finance', name: '💰 Финансы', icon: '💰', color: '#FFC107', description: 'Развиваем финансовое мышление' });
        }
        if (profileScores.ub < 3) {
            modules.push({ id: 'psychology', name: '🧠 Психология', icon: '🧠', color: '#E91E63', description: 'Глубинные паттерны' });
        }
        if (profileScores.chv < 3) {
            modules.push({ id: 'communication', name: '💬 Общение', icon: '💬', color: '#3F51B5', description: 'Улучшаем отношения' });
        }
        
        const commonModules = [
            { id: 'goals', name: '📊 Цели', icon: '📊', color: '#2196F3', description: 'Ваши цели и задачи' },
            { id: 'habits', name: '🔄 Привычки', icon: '🔄', color: '#00BCD4', description: 'Полезные привычки' },
            { id: 'entertainment', name: '🎮 Развлечения', icon: '🎮', color: '#9C27B0', description: 'Идеи для отдыха' },
            { id: 'health', name: '❤️ Здоровье', icon: '❤️', color: '#F44336', description: 'Забота о себе' }
        ];
        
        modules.push(...commonModules);
        const unique = modules.filter((v, i, a) => a.findIndex(t => t.id === v.id) === i);
        return unique.slice(0, 9);
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
    
    // ============================================
    // ОБРАБОТЧИКИ СОБЫТИЙ
    // ============================================
    
    attachDashboardEvents() {
        document.querySelectorAll('.module-card').forEach(card => {
            card.addEventListener('click', () => this.handleModuleClick(card.dataset.module));
        });
        
        document.querySelectorAll('.quick-action').forEach(action => {
            action.addEventListener('click', () => this.handleQuickAction(action.dataset.action));
        });
        
        const voiceBtn = document.getElementById('dashboardVoiceBtn');
        if (voiceBtn) this.setupVoiceButton(voiceBtn);
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
    // ГОЛОСОВОЙ ВВОД
    // ============================================
    
    setupVoiceButton(button) {
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let recordingStartTime = null;
        let timerInterval = null;
        
        const voiceStatus = document.getElementById('voiceStatusDashboard');
        const timerEl = document.getElementById('dashboardRecordingTimer');
        
        const startRecording = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = async () => {
                    stream.getTracks().forEach(track => track.stop());
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    await this.sendVoiceToServer(audioBlob);
                    
                    if (timerInterval) clearInterval(timerInterval);
                    if (voiceStatus) voiceStatus.style.display = 'none';
                    button.classList.remove('recording');
                    button.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-text">Нажмите и говорите</span>';
                };
                
                mediaRecorder.start(1000);
                isRecording = true;
                recordingStartTime = Date.now();
                
                button.classList.add('recording');
                button.innerHTML = '<span class="voice-icon">⏹️</span><span class="voice-text">Отпустите для отправки</span>';
                if (voiceStatus) voiceStatus.style.display = 'flex';
                
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
                this.showFloatingMessage('Не удалось получить доступ к микрофону', 'error');
            }
        };
        
        const stopRecording = () => {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                if (timerInterval) clearInterval(timerInterval);
            }
        };
        
        button.addEventListener('mousedown', startRecording);
        button.addEventListener('mouseup', stopRecording);
        button.addEventListener('mouseleave', stopRecording);
        
        button.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); });
        button.addEventListener('touchend', (e) => { e.preventDefault(); stopRecording(); });
    }
    
    async sendVoiceToServer(audioBlob) {
        this.showFloatingMessage('Распознаю речь...', 'info');
        
        const formData = new FormData();
        formData.append('user_id', this.userId);
        formData.append('voice', audioBlob, 'voice.webm');
        
        try {
            const response = await fetch('/api/voice/process', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (result.recognized_text) {
                    this.showFloatingMessage(`Вы сказали: ${result.recognized_text}`, 'success');
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
            this.showFloatingMessage('Ошибка отправки голоса', 'error');
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
        
        if (this.challengeManager) {
            this.challengeManager.onQuestionAsked();
        }
    }
    
    handleQuickAction(actionType) {
        switch(actionType) {
            case 'mode': this.showModeSelection(); break;
            case 'profile': this.showProfile(); break;
            case 'thoughts': this.showPsychologistThought(); break;
            case 'goals': this.showGoals(); break;
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
        
        setTimeout(() => floatingMsg.style.display = 'none', 5000);
        
        const closeBtn = document.getElementById('floatingMessageClose');
        if (closeBtn) closeBtn.onclick = () => floatingMsg.style.display = 'none';
    }
    
    // ============================================
    // API ВЫЗОВЫ
    // ============================================
    
    async sendQuestionToBot(question) {
        try {
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    message: question,
                    mode: this.mode
                })
            });
            
            const result = await response.json();
            if (result.success && result.response) {
                this.showFloatingMessage(result.response, 'info');
                if (result.audio_url) this.playAudioResponse(result.audio_url);
            }
        } catch (error) {
            console.error('Send question error:', error);
        }
    }
    
    showModeSelection() {
        if (window.api && window.api.showModeSelection) {
            window.api.showModeSelection();
        } else {
            this.showFloatingMessage('Выберите режим: 🔮 КОУЧ | 🧠 ПСИХОЛОГ | ⚡ ТРЕНЕР', 'info');
        }
    }
    
    showProfile() {
        if (window.api && window.api.showProfile) {
            window.api.showProfile();
        } else {
            this.showFloatingMessage('Загружаю ваш психологический портрет...', 'info');
            window.location.hash = '#profile';
        }
    }
    
    showPsychologistThought() {
        if (window.api && window.api.showThoughts) {
            window.api.showThoughts();
        } else {
            this.showFloatingMessage('Генерирую мысли психолога...', 'info');
            window.location.hash = '#thoughts';
        }
    }
    
    showGoals() {
        if (window.api && window.api.showGoals) {
            window.api.showGoals();
        } else {
            this.showFloatingMessage('Загружаю ваши цели...', 'info');
            window.location.hash = '#goals';
        }
    }
    
    startTest() {
        if (window.api && window.api.startTest) {
            window.api.startTest();
        } else {
            window.location.hash = '#test';
        }
    }
    
    showSkipMessage() {
        this.showFloatingMessage('Тест поможет лучше понять вас и подобрать персональные рекомендации. Вернётесь к нему позже?', 'info');
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
    
    // ============================================
    // ЧАТ С ДВОЙНИКОМ
    // ============================================
    
    showChatModal(double) {
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
        const replies = [
            `Привет! Рад познакомиться! У нас ${double.compatibility.score}% совместимости!`,
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
    
    initVoiceInput() {
        window.startVoiceRecording = () => {
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) voiceBtn.dispatchEvent(new Event('mousedown'));
        };
    }
}

window.FrediDashboard = FrediDashboard;
