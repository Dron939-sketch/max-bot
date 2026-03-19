// utils/storage.js
// Работа с localStorage

const Storage = {
    // Сохранить данные пользователя
    saveUserData(userId, data) {
        try {
            const key = `fredi_user_${userId}`;
            localStorage.setItem(key, JSON.stringify({
                ...data,
                timestamp: Date.now()
            }));
            return true;
        } catch (e) {
            console.error('Ошибка сохранения в localStorage:', e);
            return false;
        }
    },
    
    // Загрузить данные пользователя
    loadUserData(userId) {
        try {
            const key = `fredi_user_${userId}`;
            const data = localStorage.getItem(key);
            if (!data) return null;
            
            const parsed = JSON.parse(data);
            
            // Проверяем актуальность (не старше 7 дней)
            if (Date.now() - parsed.timestamp > 7 * 24 * 60 * 60 * 1000) {
                localStorage.removeItem(key);
                return null;
            }
            
            return parsed;
        } catch (e) {
            console.error('Ошибка загрузки из localStorage:', e);
            return null;
        }
    },
    
    // Сохранить историю сообщений
    saveMessageHistory(userId, messages) {
        try {
            const key = `fredi_history_${userId}`;
            // Храним только последние 100 сообщений
            const recent = messages.slice(-100);
            localStorage.setItem(key, JSON.stringify(recent));
            return true;
        } catch (e) {
            console.error('Ошибка сохранения истории:', e);
            return false;
        }
    },
    
    // Загрузить историю сообщений
    loadMessageHistory(userId) {
        try {
            const key = `fredi_history_${userId}`;
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Ошибка загрузки истории:', e);
            return [];
        }
    },
    
    // Сохранить прогресс теста
    saveTestProgress(userId, stage, answers) {
        try {
            const key = `fredi_test_${userId}`;
            let progress = this.loadTestProgress(userId) || {};
            progress[stage] = answers;
            progress.lastUpdate = Date.now();
            localStorage.setItem(key, JSON.stringify(progress));
            return true;
        } catch (e) {
            console.error('Ошибка сохранения прогресса теста:', e);
            return false;
        }
    },
    
    // Загрузить прогресс теста
    loadTestProgress(userId) {
        try {
            const key = `fredi_test_${userId}`;
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Ошибка загрузки прогресса теста:', e);
            return null;
        }
    },
    
    // Очистить все данные пользователя
    clearUserData(userId) {
        try {
            localStorage.removeItem(`fredi_user_${userId}`);
            localStorage.removeItem(`fredi_history_${userId}`);
            localStorage.removeItem(`fredi_test_${userId}`);
            return true;
        } catch (e) {
            console.error('Ошибка очистки данных:', e);
            return false;
        }
    }
};

window.Storage = Storage;
