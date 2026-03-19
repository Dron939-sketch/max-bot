// screens/test-stage1.js
// Этап 1 теста: Определение типа восприятия

const TestStage1 = {
    // Вопросы этапа 1
    questions: [
        {
            text: "Как вы обычно воспринимаете новую информацию?",
            options: [
                { id: 'A', text: 'Через визуальные образы и картинки', vector: 'visual' },
                { id: 'B', text: 'Через ощущения и телесный опыт', vector: 'kinesthetic' },
                { id: 'C', text: 'Через логические схемы и структуры', vector: 'auditory' },
                { id: 'D', text: 'Через интуицию и общее впечатление', vector: 'digital' }
            ]
        },
        {
            text: "Что для вас важнее при принятии решения?",
            options: [
                { id: 'A', text: 'Как это будет выглядеть', vector: 'visual' },
                { id: 'B', text: 'Что я чувствую по этому поводу', vector: 'kinesthetic' },
                { id: 'C', text: 'Логика и факты', vector: 'auditory' },
                { id: 'D', text: 'Общая картина и смысл', vector: 'digital' }
            ]
        },
        {
            text: "Как вы лучше запоминаете?",
            options: [
                { id: 'A', text: 'Когда вижу схему или изображение', vector: 'visual' },
                { id: 'B', text: 'Когда записываю или проживаю', vector: 'kinesthetic' },
                { id: 'C', text: 'Когда проговариваю вслух', vector: 'auditory' },
                { id: 'D', text: 'Когда понимаю суть', vector: 'digital' }
            ]
        },
        {
            text: "Что вас вдохновляет?",
            options: [
                { id: 'A', text: 'Красота и гармония', vector: 'visual' },
                { id: 'B', text: 'Глубокие переживания', vector: 'kinesthetic' },
                { id: 'C', text: 'Идеи и концепции', vector: 'auditory' },
                { id: 'D', text: 'Смысл и предназначение', vector: 'digital' }
            ]
        }
    ],
    
    // Подсчет результатов
    calculateResult(answers) {
        const counts = { visual: 0, kinesthetic: 0, auditory: 0, digital: 0 };
        
        answers.forEach(answer => {
            if (answer.vector) counts[answer.vector]++;
        });
        
        // Определяем доминирующий тип
        let dominant = 'visual';
        let maxCount = 0;
        
        for (const [type, count] of Object.entries(counts)) {
            if (count > maxCount) {
                maxCount = count;
                dominant = type;
            }
        }
        
        const descriptions = {
            visual: 'Визуал — воспринимаете мир через образы и картинки',
            kinesthetic: 'Кинестетик — воспринимаете через ощущения и опыт',
            auditory: 'Аудиал — воспринимаете через звуки и логику',
            digital: 'Дискрет — воспринимаете через смыслы и интуицию'
        };
        
        return {
            type: dominant,
            description: descriptions[dominant],
            counts: counts
        };
    }
};

window.TestStage1 = TestStage1;
