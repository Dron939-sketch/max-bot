// ========== test.js ==========
// Логика 5 этапов тестирования

const Test = {
    currentStage: 1,
    currentQuestion: 0,
    answers: {},

    async startStage1() {
        this.currentStage = 1;
        this.currentQuestion = 0;
        
        console.log('📝 Начинаем этап 1');
        
        // Здесь будет загрузка первого вопроса с сервера
        // Пока показываем заглушку
        alert('Этап 1 теста будет загружен с сервера');
        
        // Временно возвращаемся на экран контекста
        Context.showCompleteScreen(App.userContext);
    }
};

window.Test = Test;
