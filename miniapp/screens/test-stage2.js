// screens/test-stage2.js
// Этап 2 теста: Определение уровня мышления (1-9)

const TestStage2 = {
    questions: [
        {
            text: "Я часто анализирую свои мысли и чувства",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        },
        {
            text: "Мне важно понимать причины своих поступков",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        },
        {
            text: "Я вижу взаимосвязи между разными событиями",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        },
        {
            text: "Я задумываюсь о смысле жизни",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        },
        {
            text: "Мне интересно изучать новые концепции",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        },
        {
            text: "Я замечаю, как меняются мои взгляды со временем",
            options: [
                { id: 'A', text: 'Совершенно не согласен', value: 1 },
                { id: 'B', text: 'Скорее не согласен', value: 2 },
                { id: 'C', text: 'Нейтрально', value: 3 },
                { id: 'D', text: 'Скорее согласен', value: 4 },
                { id: 'E', text: 'Полностью согласен', value: 5 }
            ]
        }
    ],
    
    calculateResult(answers) {
        const sum = answers.reduce((acc, a) => acc + a.value, 0);
        const avg = sum / answers.length;
        
        // Уровень мышления от 1 до 9
        const level = Math.round(avg * 1.8); // 5->9, 1->1.8
        
        const descriptions = {
            1: 'Конкретное мышление',
            2: 'Образное мышление',
            3: 'Логическое мышление',
            4: 'Системное мышление',
            5: 'Стратегическое мышление',
            6: 'Концептуальное мышление',
            7: 'Философское мышление',
            8: 'Мета-мышление',
            9: 'Трансцендентное мышление'
        };
        
        return {
            level: Math.min(9, Math.max(1, level)),
            description: descriptions[Math.min(9, Math.max(1, level))],
            average: avg
        };
    }
};

window.TestStage2 = TestStage2;
