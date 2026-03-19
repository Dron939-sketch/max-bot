// ========== api.js ==========
// Слой для работы с API

const api = {
    baseUrl: '/api',
    timeout: 15000,

    async get(endpoint, params = {}) {
        try {
            if (App?.userId && !params.user_id) {
                params.user_id = App.userId;
            }
            
            const url = new URL(endpoint, window.location.origin);
            Object.keys(params).forEach(key => 
                url.searchParams.append(key, params[key])
            );
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/json' },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`❌ GET ${endpoint} error:`, error);
            throw error;
        }
    },

    async post(endpoint, data = {}) {
        try {
            if (App?.userId && !data.user_id) {
                data.user_id = App.userId;
            }
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`❌ POST ${endpoint} error:`, error);
            throw error;
        }
    },

    // ===== ПОЛЬЗОВАТЕЛЬ =====
    async getUserStatus(userId) {
        try {
            return await this.get('/api/user/status', { user_id: userId });
        } catch (error) {
            console.error('❌ getUserStatus error:', error);
            return {
                user_id: userId,
                user_name: 'друг',
                context_complete: false,
                test_completed: false,
                first_visit: true
            };
        }
    },

    async getUserData(userId) {
        try {
            return await this.get('/api/user-data', { user_id: userId });
        } catch (error) {
            console.error('❌ getUserData error:', error);
            return {
                user_id: userId,
                user_name: 'друг',
                has_profile: false,
                first_visit: true
            };
        }
    },

    // ===== КОНТЕКСТ =====
    async saveContext(userId, contextData) {
        return this.post('/api/save-context', {
            user_id: userId,
            context: contextData
        });
    },

    async getWeather(city) {
        return this.get('/api/weather', { city });
    },

    // ===== ТЕСТ =====
    async getTestProgress(userId) {
        try {
            return await this.get('/api/get-test-progress', { user_id: userId });
        } catch (error) {
            return {
                stage1_complete: false,
                stage2_complete: false,
                stage3_complete: false,
                stage4_complete: false,
                stage5_complete: false,
                current_stage: 1
            };
        }
    },

    async getTestQuestion(userId, stage, index) {
        try {
            return await this.get('/api/test/question', {
                user_id: userId,
                stage: stage,
                index: index
            });
        } catch (error) {
            console.error('❌ getTestQuestion error:', error);
            return null;
        }
    },

    async submitTestAnswer(userId, stage, questionIndex, answer, option) {
        return this.post('/api/test/answer', {
            user_id: userId,
            stage: stage,
            question_index: questionIndex,
            answer: answer,
            option: option
        });
    },

    async getTestStageResults(userId, stage) {
        return this.get('/api/test/results', {
            user_id: userId,
            stage: stage
        });
    },

    // ===== ПРОФИЛЬ =====
    async getProfile(userId) {
        try {
            return await this.get('/api/get-profile', { user_id: userId });
        } catch (error) {
            return { profile: null };
        }
    },

    async getThoughts(userId) {
        try {
            return await this.get('/api/thought', { user_id: userId });
        } catch (error) {
            return { thought: null };
        }
    },

    async saveProfile(userId, profile) {
        return this.post('/api/save-profile', {
            user_id: userId,
            profile: profile
        });
    },

    // ===== ЧАТ =====
    async sendChatMessage(userId, message, mode = null) {
        try {
            return await this.post('/api/chat/message', {
                user_id: userId,
                message: message,
                mode: mode
            });
        } catch (error) {
            console.error('❌ sendChatMessage error:', error);
            return {
                response: '😔 Произошла ошибка. Попробуйте еще раз.',
                buttons: null
            };
        }
    },

    async getChatHistory(userId, limit = 50) {
        try {
            const data = await this.get('/api/chat/history', { user_id: userId, limit });
            return data.history || [];
        } catch (error) {
            return [];
        }
    },

    async performAction(userId, action, data = {}) {
        return this.post('/api/chat/action', {
            user_id: userId,
            action: action,
            data: data
        });
    },

    async setMode(userId, mode) {
        return this.post('/api/save-mode', {
            user_id: userId,
            mode: mode
        });
    }
};

window.api = api;
