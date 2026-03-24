// ============================================
// ЛИЧНЫЙ КАБИНЕТ - КОНСОРЦИУМ ФРЕДИ
// Версия 3.5 - УНИВЕРСАЛЬНЫЙ ГОЛОСОВОЙ ВВОД
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
        
        // Голосовой ввод
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingTimer = null;
        this.recordingStartTime = null;
        this.recognition = null;
        this.voiceMethod = null; // 'mediaRecorder' или 'speechRecognition'
        
        // Детекция WEBVIEW
        this.isWebView = /; wv\)/.test(navigator.userAgent) || 
                         /WebView/.test(navigator.userAgent) ||
                         (window.MAX && window.MAX.WebApp);
        
        // Базовые модули консорциума
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
        
        this.initPromise = this.init();
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    async init() {
        console.log('🎯 Инициализация личного кабинета...');
        console.log('📱 Режим WebView:', this.isWebView);
        
        let attempts = 0;
        const maxAttempts = 50;
        
        while (!window.api && attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 100));
            attempts++;
            if (attempts % 10 === 0) {
                console.log(`⏳ Ожидание window.api... ${attempts * 100}мс`);
            }
        }
        
        if (!window.api) {
            console.error('❌ window.api не загружен!');
            this.showError('Не удалось загрузить API. Проверьте соединение.');
            return;
        }
        
        console.log('✅ window.api доступен');
        
        if (!this.userId) {
            this.showError('Не удалось идентифицировать пользователя.');
            return;
        }
        
        try {
            await this.loadUserData();
            
            if (!this.isTestCompleted) {
                console.log('📝 Профиль не найден, показываем экран теста');
                this.renderTestRequiredScreen();
                return;
            }
            
            await this.loadProfileData();
            await this.loadPsychologistThought();
            this.renderDashboard();
            this.initVoiceInput();
            this.detectVoiceMethod();
            
            if (this.isTestCompleted) {
                await this.initAnimatedAvatar();
            }
        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
            this.showError('Ошибка загрузки данных. Попробуйте позже.');
        }
    }
    
    // ============================================
    // ОПРЕДЕЛЕНИЕ ДОСТУПНОГО МЕТОДА ГОЛОСА
    // ============================================
    
    detectVoiceMethod() {
        // Проверяем Web Speech API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const hasSpeechRecognition = !!SpeechRecognition;
        
        // Проверяем MediaRecorder
        const hasMediaRecorder = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
        
        console.log('🎤 Доступные методы голоса:');
        console.log('   Web Speech API:', hasSpeechRecognition);
        console.log('   MediaRecorder:', hasMediaRecorder);
        console.log('   WebView:', this.isWebView);
        
        // Приоритет: MediaRecorder (более надёжный), затем SpeechRecognition
        if (hasMediaRecorder) {
            this.voiceMethod = 'mediaRecorder';
            console.log('✅ Выбран метод: MediaRecorder (запись + сервер)');
        } else if (hasSpeechRecognition) {
            this.voiceMethod = 'speechRecognition';
            this.initSpeechRecognition();
            console.log('✅ Выбран метод: Web Speech API (распознавание на устройстве)');
        } else {
            this.voiceMethod = 'none';
            console.log('⚠️ Голосовой ввод не поддерживается');
        }
        
        // Показываем подсказку в WebView
        if (this.isWebView && this.voiceMethod !== 'mediaRecorder') {
            this.showVoiceHint();
        }
    }
    
    showVoiceHint() {
        setTimeout(() => {
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) {
                const hint = document.createElement('div');
                hint.className = 'voice-hint-bubble';
                hint.innerHTML = '🎤 Для голосового ввода нажмите ⋮ → "Открыть в браузере"';
                hint.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);background:#ff9800;color:white;padding:8px 16px;border-radius:20px;font-size:12px;white-space:nowrap;z-index:1000;';
                voiceBtn.parentNode.style.position = 'relative';
                voiceBtn.parentNode.appendChild(hint);
                setTimeout(() => hint.remove(), 5000);
            }
        }, 1000);
    }
    
    // ============================================
    // WEB SPEECH API
    // ============================================
    
    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return false;
        
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'ru-RU';
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;
        
        this.recognition.onstart = () => {
            console.log('🎤 Web Speech API: запись начата');
            this.isRecording = true;
            this.showVoiceStatus('🎤 Слушаю...', 'recording');
        };
        
        this.recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            console.log('🎤 Распознано:', text);
            this.hideVoiceStatus();
            this.showFloatingMessage(`📝 Вы сказали: ${text}`, 'success');
            this.sendQuestionToBot(text);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Web Speech API error:', event.error);
            this.hideVoiceStatus();
            if (event.error === 'not-allowed') {
                this.showFloatingMessage('❌ Разрешите доступ к микрофону в настройках телефона', 'error');
            } else {
                this.showFloatingMessage('❌ Не удалось распознать речь', 'error');
            }
            this.isRecording = false;
        };
        
        this.recognition.onend = () => {
            this.isRecording = false;
            this.hideVoiceStatus();
        };
        
        return true;
    }
    
    startSpeechRecognition() {
        if (this.recognition && !this.isRecording) {
            try {
                this.recognition.start();
            } catch (e) {
                console.error('Ошибка запуска SpeechRecognition:', e);
                this.fallbackToMediaRecorder();
            }
        }
    }
    
    // ============================================
    // MEDIA RECORDER (запись + сервер)
    // ============================================
    
    setupMediaRecorder(button) {
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let recordingStartTime = null;
        let timerInterval = null;
        let stream = null;
        
        const voiceStatus = document.getElementById('voiceStatusDashboard');
        const timerEl = document.getElementById('dashboardRecordingTimer');
        
        const isSamsung = /Samsung|SM-|GT-|SHV-|SCH-|SPH-/.test(navigator.userAgent);
        
        const startRecording = async () => {
            try {
                console.log('🎤 MediaRecorder: запрос доступа...');
                
                if (isSamsung) {
                    this.showFloatingMessage('🔊 На Samsung: проверьте разрешения в настройках MAX', 'info');
                }
                
                stream = null;
                
                // Пробуем через MAX WebApp
                if (window.MAX && window.MAX.WebApp && window.MAX.WebApp.getUserMedia) {
                    try {
                        stream = await window.MAX.WebApp.getUserMedia({ audio: true });
                        console.log('✅ Доступ через MAX');
                    } catch (e) {
                        console.warn('MAX getUserMedia не сработал:', e);
                    }
                }
                
                // Стандартный Web API
                if (!stream) {
                    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    console.log('✅ Доступ через Web API');
                }
                
                // Определяем MIME тип
                let mimeType = '';
                const mimeTypes = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/3gpp'];
                for (const type of mimeTypes) {
                    if (MediaRecorder.isTypeSupported(type)) {
                        mimeType = type;
                        break;
                    }
                }
                console.log('📱 MIME тип:', mimeType || 'default');
                
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
                        this.showFloatingMessage('❌ Запись слишком короткая. Поговорите дольше.', 'error');
                        isRecording = false;
                        return;
                    }
                    
                    await this.sendVoiceToServer(audioBlob);
                    isRecording = false;
                };
                
                // Для Samsung меньше интервал
                const interval = isSamsung ? 500 : 1000;
                mediaRecorder.start(interval);
                isRecording = true;
                recordingStartTime = Date.now();
                
                // Обновляем UI
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
                }, 200);
                
                setTimeout(() => {
                    if (isRecording) stopRecording();
                }, 30000);
                
            } catch (error) {
                console.error('MediaRecorder error:', error);
                let errorMessage = '❌ Не удалось получить доступ к микрофону.';
                
                if (isSamsung) {
                    errorMessage = '🔊 На Samsung:\n1. Настройки → Приложения → MAX\n2. Разрешения → Микрофон → Разрешить\n3. Вернитесь и нажмите 🎤';
                } else if (error.name === 'NotAllowedError') {
                    errorMessage = '❌ Разрешение на микрофон отклонено. Проверьте настройки.';
                }
                
                this.showFloatingMessage(errorMessage, 'error');
                this._resetVoiceUI(button, voiceStatus, timerInterval);
                
                // Пробуем SpeechRecognition как fallback
                if (this.voiceMethod === 'speechRecognition') {
                    this.showFloatingMessage('🔄 Пробуем другой способ...', 'info');
                    this.startSpeechRecognition();
                }
            }
        };
        
        const stopRecording = () => {
            if (mediaRecorder && isRecording && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                isRecording = false;
                if (timerInterval) clearInterval(timerInterval);
            }
        };
        
        button.onmousedown = startRecording;
        button.onmouseup = stopRecording;
        button.onmouseleave = stopRecording;
        
        button.ontouchstart = (e) => { e.preventDefault(); startRecording(); };
        button.ontouchend = (e) => { e.preventDefault(); stopRecording(); };
    }
    
    fallbackToMediaRecorder() {
        this.voiceMethod = 'mediaRecorder';
        const voiceBtn = document.getElementById('dashboardVoiceBtn');
        if (voiceBtn) {
            this.setupMediaRecorder(voiceBtn);
        }
        this.showFloatingMessage('🔄 Переключено на запись голоса', 'info');
    }
    
    // ============================================
    // ГОЛОСОВОЙ ВВОД (универсальный)
    // ============================================
    
    setupVoiceButton(button) {
        if (this.voiceMethod === 'mediaRecorder') {
            this.setupMediaRecorder(button);
        } else if (this.voiceMethod === 'speechRecognition') {
            button.onclick = () => {
                if (!this.isRecording) {
                    this.startSpeechRecognition();
                } else {
                    this.recognition?.stop();
                }
            };
            button.onmousedown = null;
            button.ontouchstart = null;
        } else {
            button.disabled = true;
            button.style.opacity = '0.5';
            button.title = 'Голосовой ввод не поддерживается';
            this.showFloatingMessage('🎤 Голосовой ввод не поддерживается. Используйте текстовый ввод.', 'info');
        }
    }
    
    _resetVoiceUI(button, voiceStatus, timerInterval) {
        if (button) {
            button.classList.remove('recording');
            button.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-text">Нажмите и говорите</span>';
        }
        if (voiceStatus) voiceStatus.style.display = 'none';
        if (timerInterval) clearInterval(timerInterval);
    }
    
    showVoiceStatus(message, type) {
        const statusDiv = document.getElementById('voiceStatusDashboard');
        if (statusDiv) {
            statusDiv.style.display = 'flex';
            const textSpan = statusDiv.querySelector('.recording-text');
            if (textSpan) textSpan.textContent = message;
        }
    }
    
    hideVoiceStatus() {
        const statusDiv = document.getElementById('voiceStatusDashboard');
        if (statusDiv) statusDiv.style.display = 'none';
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
                    await this.sendQuestionToBot(result.recognized_text);
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
            this.showFloatingMessage('❌ Ошибка отправки голоса', 'error');
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
    // ЗАГРУЗКА ДАННЫХ ИЗ БД
    // ============================================
    
    async loadUserData() {
        try {
            console.log('🔍 Загрузка данных для user_id:', this.userId);
            
            const status = await window.api.request(`/api/user-status?user_id=${this.userId}`);
            console.log('📊 Статус пользователя:', status);
            
            this.isTestCompleted = status.test_completed === true || 
                                   status.has_profile === true || 
                                   status.has_interpretation === true;
            this.profileCode = status.profile_code;
            
            console.log('📌 isTestCompleted:', this.isTestCompleted);
            console.log('📌 profileCode:', this.profileCode);
            
            if (!status.has_profile && !status.test_completed) {
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
                }
            }
            
            try {
                const userData = await window.api.request(`/api/user-data?user_id=${this.userId}`);
                if (userData && userData.user_name) {
                    this.userName = userData.user_name;
                    console.log('👤 Имя пользователя:', this.userName);
                }
            } catch (nameError) {
                console.warn('Не удалось загрузить имя из БД:', nameError);
            }
            
            if (this.isTestCompleted) {
                const profile = await window.api.request(`/api/get-profile?user_id=${this.userId}`);
                this.userData = profile;
                console.log('📊 Профиль загружен');
            }
            
            console.log('✅ loadUserData завершён, isTestCompleted:', this.isTestCompleted);
            
        } catch (error) {
            console.error('❌ Ошибка загрузки данных:', error);
            this.isTestCompleted = false;
        }
    }
    
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
            this.profileText = 'Ошибка загрузки профиля.';
        }
    }
    
    async loadPsychologistThought() {
        try {
            const response = await window.api.request(`/api/thought?user_id=${this.userId}`);
            this.psychologistThought = response.thought || 'Мысли психолога еще не сгенерированы.';
            console.log('✅ Мысли психолога загружены');
        } catch (error) {
            console.error('Ошибка загрузки мыслей психолога:', error);
            this.psychologistThought = 'Мысли психолога пока недоступны.';
        }
    }
    
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
            sb: 'Работа с реакцией на давление и страхи.',
            tf: 'Проработка денежных блоков.',
            ub: 'Развитие системного мышления.',
            chv: 'Исцеление привязанности.'
        };
        
        return growthPoints[weakest] || 'Исследование себя.';
    }
    
    renderTestRequiredScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
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
            </div>
        `;
        
        const startBtn = document.getElementById('startTestBtn');
        if (startBtn) startBtn.onclick = () => this.startTest();
    }
    
    renderDashboard() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        
        if (!this.isTestCompleted) {
            this.renderTestRequiredScreen();
            return;
        }
        
        this.renderMainDashboard(container);
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
    // ПЕРСОНАЛИЗАЦИЯ
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
            strategy: '🎯 Стратегия: Давайте разберем ваши цели и построим план действий.',
            reputation: '🏆 Репутация: Расскажите, что вас беспокоит?',
            goals: '📊 Цели: Какая цель для вас сейчас главная?',
            entertainment: '🎮 Развлечения: Что вас расслабляет?',
            psychology: '🧠 Психология: Что происходит в вашем внутреннем мире?',
            habits: '🔄 Привычки: Какую привычку хотите сформировать?',
            communication: '💬 Общение: Что хочется улучшить?',
            finance: '💰 Финансы: Как у вас с деньгами?',
            health: '❤️ Здоровье: Как вы заботитесь о себе?',
            creativity: '🎨 Творчество: Что мешает творить?'
        };
        
        const message = messages[moduleId] || `Расскажите о теме "${moduleId}"`;
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
            this.showFloatingMessage('❌ Ошибка отправки вопроса', 'error');
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
    
    startTest() {
        window.location.hash = '#test';
    }
    
    showError(message) {
        const container = document.getElementById('screenContainer');
        if (container) {
            container.innerHTML = `
                <div class="dashboard-error">
                    <div class="error-icon">⚠️</div>
                    <div class="error-title">Ошибка</div>
                    <div class="error-text">${message}</div>
                    <button class="test-required-btn" onclick="location.reload()">🔄 ПОВТОРИТЬ</button>
                </div>
            `;
        }
    }
    
    initVoiceInput() {
        window.startVoiceRecording = () => {
            const voiceBtn = document.getElementById('dashboardVoiceBtn');
            if (voiceBtn) {
                if (this.voiceMethod === 'mediaRecorder') {
                    voiceBtn.dispatchEvent(new Event('mousedown'));
                } else if (this.voiceMethod === 'speechRecognition') {
                    voiceBtn.click();
                }
            }
        };
    }
    
    showCustomGoalInput() {
        const goal = prompt('Сформулируйте свою цель своими словами:');
        if (goal?.trim()) {
            this.showFloatingMessage(`Цель принята: "${goal}"`, 'success');
        }
    }
    
    async initAnimatedAvatar() {
        if (!window.AnimatedAvatar) {
            console.warn('AnimatedAvatar не загружен');
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
    
    async initChallenges() {
        if (!window.ChallengeManager) return;
        try {
            this.challengeManager = new ChallengeManager(this.userId, this.userData);
            await this.challengeManager.init();
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
        }
        
        this.attachChallengeEvents();
    }
    
    attachChallengeEvents() {
        document.querySelectorAll('.challenge-item').forEach(item => {
            item.addEventListener('click', () => {
                const challengeId = item.dataset.challengeId;
                const challenge = this.challengeManager?.dailyChallenges?.find(c => c.id === challengeId) ||
                                 this.challengeManager?.weeklyChallenges?.find(c => c.id === challengeId);
                if (challenge && !challenge.completed) {
                    this.showFloatingMessage(challenge.description, 'info');
                }
            });
        });
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM загружен, создаём FrediDashboard');
    window.dashboard = new FrediDashboard();
});

window.FrediDashboard = FrediDashboard;
