// ========== api.js ==========
// МИНИМАЛЬНАЯ ВЕРСИЯ ДЛЯ ТЕСТА

const api = {
    async getUserStatus(userId) {
        return {
            user_id: userId,
            user_name: 'Александр',
            context_complete: false,
            test_completed: false,
            first_visit: true
        };
    },
    
    async getWeather(city) {
        return {
            icon: '🌧',
            description: 'пасмурно',
            temp: '+5'
        };
    },
    
    async saveContext(userId, contextData) {
        console.log('Сохранение контекста:', contextData);
        return { success: true };
    }
};

window.api = api;
