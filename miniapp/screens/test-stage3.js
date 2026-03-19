// screens/test-stage3.js
// Этап 3 теста: Поведенческие уровни по 4 векторам

const TestStage3 = {
    vectors: ['extraversion', 'neuroticism', 'agreeableness', 'conscientiousness'],
    
    vectorNames: {
        'extraversion': 'Экстраверсия',
        'neuroticism': 'Нейротизм',
        'agreeableness': 'Доброжелательность',
        'conscientiousness': 'Добросовестность'
    },
    
    questions: [
        // Экстраверсия (6 вопросов)
        {
            vector: 'extraversion',
            text: 'Я легко завожу новые знакомства',
            options: [1,2,3,4,5]
        },
        {
            vector: 'extraversion',
            text: 'В компании я обычно в центре внимания',
            options: [1,2,3,4,5]
        },
        {
            vector: 'extraversion',
            text: 'Я получаю энергию от общения с людьми',
            options: [1,2,3,4,5]
        },
        {
            vector: 'extraversion',
            text: 'Я предпочитаю работать в команде',
            options: [1,2,3,4,5]
        },
        {
            vector: 'extraversion',
            text: 'Я люблю быть в центре событий',
            options: [1,2,3,4,5]
        },
        {
            vector: 'extraversion',
            text: 'Мне легко говорить перед аудиторией',
            options: [1,2,3,4,5]
        },
        
        // Нейротизм (6 вопросов)
        {
            vector: 'neuroticism',
            text: 'Я часто беспокоюсь о будущем',
            options: [1,2,3,4,5]
        },
        {
            vector: 'neuroticism',
            text: 'Моё настроение легко меняется',
            options: [1,2,3,4,5]
        },
        {
            vector: 'neuroticism',
            text: 'Я остро реагирую на критику',
            options: [1,2,3,4,5]
        },
        {
            vector: 'neuroticism',
            text: 'Мне трудно расслабиться',
            options: [1,2,3,4,5]
        },
        {
            vector: 'neuroticism',
            text: 'Я часто чувствую напряжение',
            options: [1,2,3,4,5]
        },
        {
            vector: 'neuroticism',
            text: 'Я принимаю всё близко к сердцу',
            options: [1,2,3,4,5]
        },
        
        // Доброжелательность (6 вопросов)
        {
            vector: 'agreeableness',
            text: 'Я доверяю людям',
            options: [1,2,3,4,5]
        },
        {
            vector: 'agreeableness',
            text: 'Я готов помочь даже незнакомцу',
            options: [1,2,3,4,5]
        },
        {
            vector: 'agreeableness',
            text: 'Я избегаю конфликтов',
            options: [1,2,3,4,5]
        },
        {
            vector: 'agreeableness',
            text: 'Мне важны чувства других',
            options: [1,2,3,4,5]
        },
        {
            vector: 'agreeableness',
            text: 'Я легко прощаю обиды',
            options: [1,2,3,4,5]
        },
        {
            vector: 'agreeableness',
            text: 'Я ценю гармонию в отношениях',
            options: [1,2,3,4,5]
        },
        
        // Добросовестность (6 вопросов)
        {
            vector: 'conscientiousness',
            text: 'Я всегда довожу дела до конца',
            options: [1,2,3,4,5]
        },
        {
            vector: 'conscientiousness',
            text: 'Я люблю порядок и планирование',
            options: [1,2,3,4,5]
        },
        {
            vector: 'conscientiousness',
            text: 'Я ответственно отношусь к обязанностям',
            options: [1,2,3,4,5]
        },
        {
            vector: 'conscientiousness',
            text: 'Я пунктуален',
            options: [1,2,3,4,5]
        },
        {
            vector: 'conscientiousness',
            text: 'Я ставлю цели и достигаю их',
            options: [1,2,3,4,5]
        },
        {
            vector: 'conscientiousness',
            text: 'Меня раздражает неорганизованность',
            options: [1,2,3,4,5]
        }
    ],
    
    calculateResult(answers) {
        const scores = {};
        
        // Группируем ответы по векторам
        this.vectors.forEach(vector => {
            const vectorAnswers = answers.filter(a => a.vector === vector);
            if (vectorAnswers.length > 0) {
                const sum = vectorAnswers.reduce((acc, a) => acc + a.value, 0);
                scores[vector] = sum / vectorAnswers.length;
            } else {
                scores[vector] = 3; // По умолчанию
            }
        });
        
        return scores;
    }
};

window.TestStage3 = TestStage3;
