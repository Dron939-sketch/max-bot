// ========== api.js ==========
// РАБОЧАЯ ВЕРСИЯ С РЕАЛЬНЫМИ ВЫЗОВАМИ API

const API_BASE = ''; // Пусто, так как API на том же домене

const api = {
    /**
     * Получает статус пользователя
     */
    async getUserStatus(userId) {
        try {
            const response = await fetch(`${API_BASE}/api/user-data?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // Преобразуем ответ бэкенда в формат, ожидаемый фронтендом
            return {
                user_id: data.user_id,
                user_name: data.user_name || 'друг',
                context_complete: false, // Бэкенд пока не возвращает это
                test_completed: data.has_profile || false,
                first_visit: !data.has_profile
            };
        } catch (error) {
            console.error('Ошибка получения статуса пользователя:', error);
            // Возвращаем минимальные данные при ошибке
            return {
                user_id: userId,
                user_name: 'друг',
                context_complete: false,
                test_completed: false,
                first_visit: true
            };
        }
    },
    
    /**
     * Получает погоду для города
     */
    async getWeather(city) {
        try {
            // Пока нет отдельного эндпоинта для погоды, 
            // возвращаем тестовые данные
            return {
                icon: '🌤',
                description: 'тестовый режим',
                temp: '+15'
            };
        } catch (error) {
            console.error('Ошибка получения погоды:', error);
            return null;
        }
    },
    
    /**
     * Сохраняет контекст пользователя
     */
    async saveContext(userId, contextData) {
        try {
            const response = await fetch(`${API_BASE}/api/save-context`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    context: contextData
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка сохранения контекста:', error);
            return { success: false, error: error.message };
        }
    },
    
    /**
     * Получает профиль пользователя
     */
    async getUserProfile(userId) {
        try {
            const response = await fetch(`${API_BASE}/api/get-profile?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Ошибка получения профиля:', error);
            return null;
        }
    },
    
    /**
     * Сохраняет профиль пользователя
     */
    async saveUserProfile(userId, profileData) {
        try {
            const response = await fetch(`${API_BASE}/api/save-profile`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    profile: profileData
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка сохранения профиля:', error);
            return { success: false, error: error.message };
        }
    },
    
    /**
     * Получает мысли психолога
     */
    async getPsychologistThought(userId) {
        try {
            const response = await fetch(`${API_BASE}/api/thought?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.thought;
        } catch (error) {
            console.error('Ошибка получения мыслей:', error);
            return null;
        }
    },
    
    /**
     * Получает идеи на выходные
     */
    async getWeekendIdeas(userId) {
        try {
            const response = await fetch(`${API_BASE}/api/ideas?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.ideas || [];
        } catch (error) {
            console.error('Ошибка получения идей:', error);
            return [];
        }
    },
    
    /**
     * Получает прогресс теста
     */
    async getTestProgress(userId) {
        try {
            const response = await fetch(`${API_BASE}/api/get-test-progress?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Ошибка получения прогресса теста:', error);
            return {
                stage1_complete: false,
                stage2_complete: false,
                stage3_complete: false,
                stage4_complete: false,
                stage5_complete: false,
                answers_count: 0,
                current_stage: 1
            };
        }
    },
    
    /**
     * Сохраняет прогресс теста
     */
    async saveTestProgress(userId, stage, answers) {
        try {
            const response = await fetch(`${API_BASE}/api/save-test-progress`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    stage: stage,
                    answers: answers
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка сохранения прогресса теста:', error);
            return { success: false, error: error.message };
        }
    },
    
    /**
     * Сохраняет режим общения
     */
    async saveCommunicationMode(userId, mode) {
        try {
            const response = await fetch(`${API_BASE}/api/save-mode`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    mode: mode
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка сохранения режима:', error);
            return { success: false, error: error.message };
        }
    },
    
    /**
     * Синхронизирует все данные
     */
    async syncAllData(userId, data) {
        try {
            const response = await fetch(`${API_BASE}/api/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    data: data
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка синхронизации:', error);
            return { success: false, error: error.message };
        }
    }
};

// Делаем API доступным глобально
window.api = api;

// Для отладки
console.log('✅ API инициализирован, эндпоинты:', Object.keys(api));
