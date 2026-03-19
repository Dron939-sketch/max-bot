// ========== test.js ==========
// Логика 5 этапов тестирования

const Test = {
    currentStage: 1,
    currentQuestion: 0,
    answers: {},

    startStage1() {
        this.currentStage = 1;
        this.currentQuestion = 0;
        alert('Этап 1 тестирования будет доступен в следующей версии');
    }
};

window.Test = Test;
