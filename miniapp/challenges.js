// ============================================
// ЧЕЛЛЕНДЖИ И КВЕСТЫ
// Версия 1.0 - Геймификация личного кабинета
// ============================================

class ChallengeManager {
    constructor(userId, profileData = null) {
        this.userId = userId;
        this.profileData = profileData;
        this.challenges = [];
        this.activeChallenges = [];
        this.completedChallenges = [];
        this.userStats = {
            level: 1,
            xp: 0,
            xpToNextLevel: 100,
            streak: 0,
            bestStreak: 0,
            totalCompleted: 0
        };
        this.dailyChallenges = [];
        this.weeklyChallenges = [];
        this.specialChallenges = [];
        
        this.isLoading = false;
        this.listeners = [];
        
        this.init();
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    async init() {
        console.log('🏆 Инициализация системы челленджей...');
        await this.loadUserStats();
        await this.loadChallenges();
        await this.checkDailyReset();
        this.startStreakTimer();
        console.log('✅ Система челленджей загружена');
        return this;
    }
    
    async loadUserStats() {
        try {
            const response = await fetch(`/api/challenge/stats?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.userStats = data.stats;
            }
        } catch (error) {
            console.warn('Ошибка загрузки статистики:', error);
            // Загружаем из localStorage
            const saved = localStorage.getItem(`challenge_stats_${this.userId}`);
            if (saved) {
                this.userStats = JSON.parse(saved);
            }
        }
    }
    
    async loadChallenges() {
        try {
            const response = await fetch(`/api/challenges?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.challenges = data.challenges;
                this.activeChallenges = data.active || [];
                this.completedChallenges = data.completed || [];
                this.dailyChallenges = data.daily || [];
                this.weeklyChallenges = data.weekly || [];
                this.specialChallenges = data.special || [];
            }
        } catch (error) {
            console.warn('Ошибка загрузки челленджей:', error);
            this.loadLocalChallenges();
        }
    }
    
    loadLocalChallenges() {
        // Локальные челленджи (резерв)
        this.dailyChallenges = [
            {
                id: 'daily_1',
                name: '📝 Утренняя рефлексия',
                description: 'Запишите 3 мысли, которые пришли вам этим утром',
                xp: 10,
                type: 'daily',
                icon: '📝',
                progress: 0,
                target: 1,
                completed: false
            },
            {
                id: 'daily_2',
                name: '🎯 Одна цель на день',
                description: 'Сформулируйте одну цель на сегодня',
                xp: 15,
                type: 'daily',
                icon: '🎯',
                progress: 0,
                target: 1,
                completed: false
            },
            {
                id: 'daily_3',
                name: '💬 Задать вопрос',
                description: 'Задайте вопрос Фреди',
                xp: 20,
                type: 'daily',
                icon: '💬',
                progress: 0,
                target: 1,
                completed: false
            }
        ];
        
        this.weeklyChallenges = [
            {
                id: 'weekly_1',
                name: '🧠 5 дней осознанности',
                description: 'Выполняйте ежедневную рефлексию 5 дней подряд',
                xp: 100,
                type: 'weekly',
                icon: '🧠',
                progress: 0,
                target: 5,
                completed: false
            },
            {
                id: 'weekly_2',
                name: '💪 3 новых навыка',
                description: 'Изучите 3 новых психологических концепции',
                xp: 75,
                type: 'weekly',
                icon: '💪',
                progress: 0,
                target: 3,
                completed: false
            }
        ];
        
        this.specialChallenges = [
            {
                id: 'special_1',
                name: '🌟 Первый тест',
                description: 'Пройдите психологическое тестирование',
                xp: 50,
                type: 'special',
                icon: '🌟',
                progress: this.profileData ? 1 : 0,
                target: 1,
                completed: !!this.profileData
            },
            {
                id: 'special_2',
                name: '🎯 Первая цель',
                description: 'Выберите свою первую цель',
                xp: 30,
                type: 'special',
                icon: '🎯',
                progress: 0,
                target: 1,
                completed: false
            }
        ];
    }
    
    // ============================================
    // ПРОГРЕСС И XP
    // ============================================
    
    async addXP(amount, challengeId = null) {
        this.userStats.xp += amount;
        this.userStats.totalCompleted++;
        
        // Проверяем повышение уровня
        let leveledUp = false;
        while (this.userStats.xp >= this.userStats.xpToNextLevel) {
            this.userStats.xp -= this.userStats.xpToNextLevel;
            this.userStats.level++;
            this.userStats.xpToNextLevel = Math.floor(this.userStats.xpToNextLevel * 1.2);
            leveledUp = true;
        }
        
        // Сохраняем
        await this.saveStats();
        
        // Уведомляем
        this.notifyListeners('xp_gained', { amount, total: this.userStats.xp, leveledUp });
        
        if (leveledUp) {
            this.notifyListeners('level_up', { level: this.userStats.level });
        }
        
        if (challengeId) {
            await this.updateChallengeProgress(challengeId, 1);
        }
        
        return leveledUp;
    }
    
    async updateChallengeProgress(challengeId, increment = 1) {
        // Ищем во всех списках
        const allChallenges = [...this.dailyChallenges, ...this.weeklyChallenges, ...this.specialChallenges];
        const challenge = allChallenges.find(c => c.id === challengeId);
        
        if (challenge && !challenge.completed) {
            challenge.progress = Math.min(challenge.target, challenge.progress + increment);
            
            if (challenge.progress >= challenge.target && !challenge.completed) {
                challenge.completed = true;
                await this.addXP(challenge.xp, null);
                this.notifyListeners('challenge_completed', challenge);
                this.showCompletionNotification(challenge);
            }
            
            await this.saveChallenges();
            this.notifyListeners('challenge_updated', challenge);
        }
    }
    
    // ============================================
    // СТРИКИ (серии)
    // ============================================
    
    startStreakTimer() {
        // Проверяем стрик каждый день
        const lastCheck = localStorage.getItem(`streak_last_check_${this.userId}`);
        const today = new Date().toDateString();
        
        if (lastCheck !== today) {
            // Проверяем, была ли активность вчера
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            
            const hadActivity = localStorage.getItem(`streak_activity_${this.userId}_${yesterday.toDateString()}`);
            
            if (hadActivity) {
                this.userStats.streak++;
                if (this.userStats.streak > this.userStats.bestStreak) {
                    this.userStats.bestStreak = this.userStats.streak;
                }
            } else {
                this.userStats.streak = 0;
            }
            
            localStorage.setItem(`streak_last_check_${this.userId}`, today);
            this.saveStats();
        }
        
        // Проверяем каждые 6 часов
        setInterval(() => {
            this.checkDailyReset();
        }, 6 * 60 * 60 * 1000);
    }
    
    async recordActivity() {
        const today = new Date().toDateString();
        localStorage.setItem(`streak_activity_${this.userId}_${today}`, 'true');
        
        // Бонус за активность
        if (!localStorage.getItem(`streak_bonus_${this.userId}_${today}`)) {
            await this.addXP(5);
            localStorage.setItem(`streak_bonus_${this.userId}_${today}`, 'true');
        }
        
        this.notifyListeners('activity_recorded', { streak: this.userStats.streak });
    }
    
    // ============================================
    // ДНЕВНОЙ СБРОС
    // ============================================
    
    async checkDailyReset() {
        const lastReset = localStorage.getItem(`daily_reset_${this.userId}`);
        const today = new Date().toDateString();
        
        if (lastReset !== today) {
            // Сбрасываем ежедневные челленджи
            for (const challenge of this.dailyChallenges) {
                if (!challenge.completed) {
                    challenge.progress = 0;
                }
                challenge.completed = false;
            }
            
            // Обновляем список ежедневных челленджей
            await this.refreshDailyChallenges();
            
            localStorage.setItem(`daily_reset_${this.userId}`, today);
            await this.saveChallenges();
            this.notifyListeners('daily_reset', this.dailyChallenges);
        }
    }
    
    async refreshDailyChallenges() {
        // Здесь можно запросить новые челленджи с сервера
        // Пока используем локальные
        this.dailyChallenges = [
            {
                id: `daily_${Date.now()}_1`,
                name: '📝 Утренняя рефлексия',
                description: 'Запишите 3 мысли, которые пришли вам этим утром',
                xp: 10,
                type: 'daily',
                icon: '📝',
                progress: 0,
                target: 1,
                completed: false
            },
            {
                id: `daily_${Date.now()}_2`,
                name: '🎯 Одна цель на день',
                description: 'Сформулируйте одну цель на сегодня',
                xp: 15,
                type: 'daily',
                icon: '🎯',
                progress: 0,
                target: 1,
                completed: false
            },
            {
                id: `daily_${Date.now()}_3`,
                name: '💬 Задать вопрос',
                description: 'Задайте вопрос Фреди',
                xp: 20,
                type: 'daily',
                icon: '💬',
                progress: 0,
                target: 1,
                completed: false
            }
        ];
    }
    
    // ============================================
    // СОХРАНЕНИЕ
    // ============================================
    
    async saveStats() {
        try {
            await fetch('/api/challenge/stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    stats: this.userStats
                })
            });
        } catch (error) {
            // Сохраняем локально
            localStorage.setItem(`challenge_stats_${this.userId}`, JSON.stringify(this.userStats));
        }
    }
    
    async saveChallenges() {
        try {
            await fetch('/api/challenges/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    daily: this.dailyChallenges,
                    weekly: this.weeklyChallenges,
                    special: this.specialChallenges
                })
            });
        } catch (error) {
            // Сохраняем локально
            localStorage.setItem(`challenges_${this.userId}`, JSON.stringify({
                daily: this.dailyChallenges,
                weekly: this.weeklyChallenges,
                special: this.specialChallenges
            }));
        }
    }
    
    // ============================================
    // ОТРИСОВКА
    // ============================================
    
    renderWidget() {
        const xpProgress = (this.userStats.xp / this.userStats.xpToNextLevel) * 100;
        
        return `
            <div class="challenges-widget">
                <div class="widget-header">
                    <div class="widget-title">
                        <span class="widget-icon">🏆</span>
                        Челленджи
                    </div>
                    <div class="level-info">
                        Уровень ${this.userStats.level}
                    </div>
                </div>
                
                <div class="xp-bar-container">
                    <div class="xp-bar">
                        <div class="xp-progress" style="width: ${xpProgress}%"></div>
                    </div>
                    <div class="xp-text">${this.userStats.xp} / ${this.userStats.xpToNextLevel} XP</div>
                </div>
                
                <div class="streak-info">
                    <span class="streak-icon">🔥</span>
                    <span class="streak-value">${this.userStats.streak}</span>
                    <span class="streak-label">дней подряд</span>
                    <span class="best-streak">Рекорд: ${this.userStats.bestStreak}</span>
                </div>
                
                <div class="challenges-list">
                    <div class="challenge-section">
                        <div class="section-title">📅 Ежедневные</div>
                        ${this.dailyChallenges.map(c => this._renderChallengeItem(c)).join('')}
                    </div>
                    
                    <div class="challenge-section">
                        <div class="section-title">📆 Еженедельные</div>
                        ${this.weeklyChallenges.map(c => this._renderChallengeItem(c)).join('')}
                    </div>
                    
                    <div class="challenge-section">
                        <div class="section-title">⭐ Особые</div>
                        ${this.specialChallenges.map(c => this._renderChallengeItem(c)).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    _renderChallengeItem(challenge) {
        const progressPercent = (challenge.progress / challenge.target) * 100;
        const completedClass = challenge.completed ? 'completed' : '';
        
        return `
            <div class="challenge-item ${completedClass}" data-challenge-id="${challenge.id}">
                <div class="challenge-icon">${challenge.icon}</div>
                <div class="challenge-info">
                    <div class="challenge-name">${challenge.name}</div>
                    <div class="challenge-desc">${challenge.description}</div>
                    <div class="challenge-progress-bar">
                        <div class="challenge-progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <div class="challenge-progress-text">${challenge.progress}/${challenge.target}</div>
                </div>
                <div class="challenge-xp">+${challenge.xp} XP</div>
                ${challenge.completed ? '<div class="challenge-complete-badge">✅</div>' : ''}
            </div>
        `;
    }
    
    // ============================================
    // УВЕДОМЛЕНИЯ
    // ============================================
    
    showCompletionNotification(challenge) {
        // Создаём уведомление
        const notification = document.createElement('div');
        notification.className = 'challenge-notification';
        notification.innerHTML = `
            <div class="notification-icon">🏆</div>
            <div class="notification-content">
                <div class="notification-title">Челлендж выполнен!</div>
                <div class="notification-text">${challenge.name} +${challenge.xp} XP</div>
            </div>
            <button class="notification-close">✕</button>
        `;
        
        document.body.appendChild(notification);
        
        // Анимация появления
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Авто-закрытие через 4 секунды
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 4000);
        
        // Кнопка закрытия
        notification.querySelector('.notification-close').onclick = () => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        };
    }
    
    // ============================================
    // СОБЫТИЯ
    // ============================================
    
    addListener(callback) {
        this.listeners.push(callback);
    }
    
    notifyListeners(event, data) {
        this.listeners.forEach(cb => cb(event, data));
    }
    
    // ============================================
    // ИНТЕГРАЦИЯ С ПРИЛОЖЕНИЕМ
    // ============================================
    
    async onQuestionAsked() {
        // Обновляем прогресс ежедневного челленджа
        const dailyQuestion = this.dailyChallenges.find(c => c.id.includes('daily_3'));
        if (dailyQuestion && !dailyQuestion.completed) {
            await this.updateChallengeProgress(dailyQuestion.id, 1);
        }
        
        // Записываем активность для стрика
        await this.recordActivity();
    }
    
    async onGoalSelected() {
        const specialGoal = this.specialChallenges.find(c => c.id === 'special_2');
        if (specialGoal && !specialGoal.completed) {
            await this.updateChallengeProgress(specialGoal.id, 1);
        }
    }
    
    async onTestCompleted() {
        const specialTest = this.specialChallenges.find(c => c.id === 'special_1');
        if (specialTest && !specialTest.completed) {
            await this.updateChallengeProgress(specialTest.id, 1);
        }
        
        // Бонус за прохождение теста
        await this.addXP(50);
    }
    
    // ============================================
    // СТАТИСТИКА
    // ============================================
    
    getStats() {
        return {
            level: this.userStats.level,
            xp: this.userStats.xp,
            xpToNext: this.userStats.xpToNextLevel,
            streak: this.userStats.streak,
            bestStreak: this.userStats.bestStreak,
            totalCompleted: this.userStats.totalCompleted,
            dailyCompleted: this.dailyChallenges.filter(c => c.completed).length,
            weeklyCompleted: this.weeklyChallenges.filter(c => c.completed).length,
            specialCompleted: this.specialChallenges.filter(c => c.completed).length
        };
    }
}

// Глобальный экспорт
window.ChallengeManager = ChallengeManager;

console.log('✅ Модуль челленджей загружен');
