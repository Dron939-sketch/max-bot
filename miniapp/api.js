// ============================================
// API КЛАСС ДЛЯ РАБОТЫ С СЕРВЕРОМ
// Версия 2.1 - добавлены методы для новых модулей
// ============================================

class FrediAPI {
    constructor() {
        this.baseUrl = '';
        this.userId = null;
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 минут кэш
    }
    
    setUserId(userId) {
        this.userId = userId;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        const config = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }
    
    getCacheKey(endpoint, params) {
        return `${endpoint}:${JSON.stringify(params)}`;
    }
    
    isCacheValid(cached) {
        return cached && (Date.now() - cached.timestamp) < this.cacheTTL;
    }
    
    // ===== СТАТУС ПОЛЬЗОВАТЕЛЯ =====
    async getUserStatus(userId) {
        const cacheKey = this.getCacheKey('/user-status', { userId });
        const cached = this.cache.get(cacheKey);
        if (this.isCacheValid(cached)) {
            return cached.data;
        }
        
        const data = await this.request(`/api/user-status?user_id=${userId}`);
        this.cache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    }
    
    async getUserFullStatus(userId) {
        return this.getUserStatus(userId);
    }
    
    // ===== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ =====
    async getUserProfile(userId) {
        const data = await this.request(`/api/get-profile?user_id=${userId}`);
        return data;
    }
    
    async getTestInterpretation(userId) {
        const data = await this.request(`/api/get-test-interpretation?user_id=${userId}`);
        return data;
    }
    
    // ===== ТЕСТ =====
    async saveTestResults(userId, results) {
        const data = await this.request('/api/save-test-results', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, results })
        });
        return data;
    }
    
    async getTestQuestion(userId, stage, index) {
        const data = await this.request(`/api/test/question?user_id=${userId}&stage=${stage}&index=${index}`);
        return data;
    }
    
    async submitTestAnswer(userId, stage, index, answer, option) {
        const data = await this.request('/api/test/answer', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, stage, question_index: index, answer, option })
        });
        return data;
    }
    
    // ===== ЧАТ =====
    async sendQuestion(userId, message, mode = null) {
        const data = await this.request('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, message, mode })
        });
        return data;
    }
    
    async sendChatAction(userId, action, data = {}) {
        const response = await this.request('/api/chat/action', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, action, data })
        });
        return response;
    }
    
    // ===== МЫСЛИ ПСИХОЛОГА =====
    async getPsychologistThought(userId) {
        const data = await this.request(`/api/thought?user_id=${userId}`);
        return data.thought;
    }
    
    // ===== ИДЕИ НА ВЫХОДНЫЕ =====
    async getWeekendIdeas(userId) {
        const data = await this.request(`/api/ideas?user_id=${userId}`);
        return data.ideas || [];
    }
    
    // ===== РЕЖИМЫ =====
    async getAvailableModes() {
        const data = await this.request('/api/modes');
        return data.modes || [];
    }
    
    async saveCommunicationMode(userId, mode) {
        const data = await this.request('/api/save-mode', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, mode })
        });
        return data;
    }
    
    // ===== ЦЕЛИ =====
    async getDynamicGoals(userId, mode = 'coach') {
        const data = await this.request(`/api/goals?user_id=${userId}&mode=${mode}`);
        return data.goals || [];
    }
    
    // ===== УМНЫЕ ВОПРОСЫ =====
    async getSmartQuestions(userId) {
        const data = await this.request(`/api/smart-questions?user_id=${userId}`);
        return data.questions || [];
    }
    
    // ===== КОНТЕКСТ =====
    async saveContext(userId, contextData) {
        const data = await this.request('/api/save-context', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, context: contextData })
        });
        return data;
    }
    
    async getUserContext(userId) {
        const data = await this.request(`/api/user-context?user_id=${userId}`);
        return data;
    }
    
    // ===== ИСТОРИЯ ЧАТА =====
    async getChatHistory(userId, limit = 50) {
        const data = await this.request(`/api/chat/history?user_id=${userId}&limit=${limit}`);
        return data.history || [];
    }
    
    // ===== ГОЛОСОВЫЕ ФУНКЦИИ =====
    async sendVoiceMessage(userId, audioBlob) {
        const formData = new FormData();
        formData.append('user_id', userId);
        formData.append('voice', audioBlob, 'voice.webm');
        
        try {
            const response = await fetch('/api/voice/process', {
                method: 'POST',
                body: formData
            });
            return await response.json();
        } catch (error) {
            console.error('Voice API Error:', error);
            throw error;
        }
    }
    
    async textToSpeech(text, mode = 'coach') {
        const response = await this.request('/api/tts', {
            method: 'POST',
            body: JSON.stringify({ text, mode })
        });
        return response;
    }
    
    // ===== СТАТИСТИКА =====
    async getUserStats(userId) {
        const data = await this.request(`/api/user-stats?user_id=${userId}`);
        return data;
    }
    
    async getUserLogs(userId) {
        const data = await this.request(`/api/logs/${userId}`);
        return data;
    }
    
    // ===== СИНХРОНИЗАЦИЯ =====
    async syncUserData(userId, data) {
        const response = await this.request('/api/sync', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, data })
        });
        return response;
    }
    
    // ===== ПРОВЕРКА СТАТУСА MAX API =====
    async checkMaxApiStatus() {
        const data = await this.request('/api/max-status');
        return data;
    }
    
    // ===== ОТПРАВКА СООБЩЕНИЯ ЧЕРЕЗ MAX =====
    async sendMessageViaMax(userId, text, keyboard = null) {
        const data = await this.request('/api/send-message', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, text, keyboard })
        });
        return data;
    }
    
    // ============================================
    // НОВЫЕ МЕТОДЫ ДЛЯ ЧЕЛЛЕНДЖЕЙ
    // ============================================
    
    async getChallenges(userId) {
        const data = await this.request(`/api/challenges?user_id=${userId}`);
        return data;
    }
    
    async getChallengeStats(userId) {
        const data = await this.request(`/api/challenge/stats?user_id=${userId}`);
        return data;
    }
    
    async saveChallengeStats(userId, stats) {
        const data = await this.request('/api/challenge/stats', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, stats })
        });
        return data;
    }
    
    async saveChallenges(userId, challenges) {
        const data = await this.request('/api/challenges/save', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, ...challenges })
        });
        return data;
    }
    
    async updateChallengeProgress(userId, challengeId, progress) {
        const data = await this.request('/api/challenge/progress', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, challenge_id: challengeId, progress })
        });
        return data;
    }
    
    // ============================================
    // НОВЫЕ МЕТОДЫ ДЛЯ УВЕДОМЛЕНИЙ
    // ============================================
    
    async getNotificationSettings(userId) {
        const data = await this.request(`/api/notification/settings?user_id=${userId}`);
        return data;
    }
    
    async saveNotificationSettings(userId, settings) {
        const data = await this.request('/api/notification/settings', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, settings })
        });
        return data;
    }
    
    async getNotificationHistory(userId, limit = 50) {
        const data = await this.request(`/api/notification/history?user_id=${userId}&limit=${limit}`);
        return data;
    }
    
    async sendTestNotification(userId) {
        const data = await this.request('/api/notification/test', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
        return data;
    }
    
    async subscribeToPush(userId, subscription) {
        const data = await this.request('/api/notification/subscribe', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, subscription })
        });
        return data;
    }
    
    async unsubscribeFromPush(userId) {
        const data = await this.request('/api/notification/unsubscribe', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
        return data;
    }
    
    async getVapidPublicKey() {
        const data = await this.request('/api/notification/vapid-key');
        return data;
    }
    
    // ============================================
    // НОВЫЕ МЕТОДЫ ДЛЯ ПСИХОМЕТРИЧЕСКИХ ДВОЙНИКОВ
    // ============================================
    
    async findPsychometricDoubles(userId, limit = 10, filters = {}) {
        const params = new URLSearchParams({ user_id: userId, limit, ...filters });
        const data = await this.request(`/api/psychometric/find-doubles?${params}`);
        return data;
    }
    
    async getPsychometricDouble(doubleId, userId) {
        const data = await this.request(`/api/psychometric/double/${doubleId}?user_id=${userId}`);
        return data;
    }
    
    async sendMessageToDouble(userId, doubleId, message) {
        const data = await this.request('/api/psychometric/send-message', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, double_id: doubleId, message })
        });
        return data;
    }
    
    async getDoubleMessages(userId, doubleId, limit = 50) {
        const data = await this.request(`/api/psychometric/messages?user_id=${userId}&double_id=${doubleId}&limit=${limit}`);
        return data;
    }
    
    async markDoubleViewed(userId, doubleId) {
        const data = await this.request('/api/psychometric/mark-viewed', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, double_id: doubleId })
        });
        return data;
    }
    
    async getPsychometricStats(userId) {
        const data = await this.request(`/api/psychometric/stats?user_id=${userId}`);
        return data;
    }
    
    // ============================================
    // НОВЫЙ МЕТОД ДЛЯ НАСТРОЕНИЯ (АНИМИРОВАННЫЙ АВАТАР)
    // ============================================
    
    async getUserMood(userId) {
        const data = await this.request(`/api/user-mood?user_id=${userId}`);
        return data;
    }
    
    // ============================================
    // НОВЫЙ МЕТОД ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЯ (ИМЯ)
    // ============================================
    
    async getUserData(userId) {
        const data = await this.request(`/api/user-data?user_id=${userId}`);
        return data;
    }
    
    // ============================================
    // ОЧИСТКА КЭША
    // ============================================
    
    clearCache() {
        this.cache.clear();
        console.log('🧹 Кэш API очищен');
    }
    
    clearUserCache(userId) {
        const keysToDelete = [];
        for (const [key, value] of this.cache.entries()) {
            if (key.includes(String(userId))) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.cache.delete(key));
        console.log(`🧹 Кэш для пользователя ${userId} очищен`);
    }
}

// Глобальный экземпляр API
window.api = new FrediAPI();

console.log('✅ API модуль загружен');
