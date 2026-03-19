// ========== test.js ==========
// ПОЛНАЯ ВЕРСИЯ С 5 ЭТАПАМИ ТЕСТИРОВАНИЯ

const Test = {
    currentStage: 1,
    currentQuestion: 0,
    answers: {},
    
    // Данные пользователя для сохранения результатов
    userData: {
        perception_type: null,
        thinking_level: null,
        behavioral_levels: {},
        dilts_counts: {},
        deep_patterns: {}
    },

    // Вопросы для этапа 1 (Тип восприятия)
    stage1Questions: [
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

    // Вопросы для этапа 2 (Уровень мышления)
    stage2Questions: [
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

    // Запуск этапа 1
    startStage1() {
        this.currentStage = 1;
        this.currentQuestion = 0;
        this.answers.stage1 = [];
        this.showQuestion();
    },

    // Показать текущий вопрос
    showQuestion() {
        let questions, total;
        
        if (this.currentStage === 1) {
            questions = this.stage1Questions;
            total = questions.length;
        } else if (this.currentStage === 2) {
            questions = this.stage2Questions;
            total = questions.length;
        } else {
            alert(`Этап ${this.currentStage} в разработке`);
            return;
        }

        if (this.currentQuestion >= total) {
            this.completeStage();
            return;
        }

        const question = questions[this.currentQuestion];
        
        // Создаем HTML для вопроса
        let html = `
            <div class="test-container">
                <div class="test-header">
                    <div class="test-stage">Этап ${this.currentStage}/5</div>
                    <div class="test-progress">Вопрос ${this.currentQuestion + 1}/${total}</div>
                </div>
                <div class="test-question">${question.text}</div>
                <div class="test-options">
        `;

        question.options.forEach(option => {
            html += `
                <button class="test-option" data-option-id="${option.id}">
                    <span class="option-letter">${option.id}</span>
                    <span class="option-text">${option.text}</span>
                </button>
            `;
        });

        html += `</div>`;

        const container = document.getElementById('screenContainer');
        container.innerHTML = html;

        // Добавляем обработчики
        document.querySelectorAll('.test-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const optionId = btn.dataset.optionId;
                const question_ = questions[this.currentQuestion];
                const option = question_.options.find(o => o.id === optionId);
                
                this.saveAnswer(option);
                
                // Подсвечиваем выбранный
                document.querySelectorAll('.test-option').forEach(b => 
                    b.classList.remove('selected'));
                btn.classList.add('selected');
                
                // Переходим к следующему вопросу через небольшую задержку
                setTimeout(() => {
                    this.currentQuestion++;
                    this.showQuestion();
                }, 300);
            });
        });
    },

    // Сохранить ответ
    saveAnswer(option) {
        if (this.currentStage === 1) {
            this.answers.stage1.push({
                question: this.currentQuestion,
                option: option.id,
                vector: option.vector
            });
            
            // Подсчитываем тип восприятия после последнего вопроса
            if (this.currentQuestion === this.stage1Questions.length - 1) {
                this.calculatePerceptionType();
            }
        } else if (this.currentStage === 2) {
            if (!this.answers.stage2) this.answers.stage2 = [];
            this.answers.stage2.push({
                question: this.currentQuestion,
                option: option.id,
                value: option.value
            });
            
            // Подсчитываем уровень мышления после последнего вопроса
            if (this.currentQuestion === this.stage2Questions.length - 1) {
                this.calculateThinkingLevel();
            }
        }
    },

    // Подсчет типа восприятия (этап 1)
    calculatePerceptionType() {
        const counts = { visual: 0, kinesthetic: 0, auditory: 0, digital: 0 };
        
        this.answers.stage1.forEach(answer => {
            if (answer.vector) counts[answer.vector]++;
        });
        
        let dominant = 'visual';
        let maxCount = 0;
        
        for (const [type, count] of Object.entries(counts)) {
            if (count > maxCount) {
                maxCount = count;
                dominant = type;
            }
        }
        
        const types = {
            visual: 'Визуал — воспринимаете мир через образы и картинки',
            kinesthetic: 'Кинестетик — воспринимаете через ощущения и опыт',
            auditory: 'Аудиал — воспринимаете через звуки и логику',
            digital: 'Дискрет — воспринимаете через смыслы и интуицию'
        };
        
        this.userData.perception_type = types[dominant];
        console.log('Тип восприятия:', this.userData.perception_type);
    },

    // Подсчет уровня мышления (этап 2)
    calculateThinkingLevel() {
        const sum = this.answers.stage2.reduce((acc, a) => acc + a.value, 0);
        const avg = sum / this.answers.stage2.length;
        
        // Уровень мышления от 1 до 9
        const level = Math.round(avg * 1.8);
        
        const levels = {
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
        
        this.userData.thinking_level = {
            level: Math.min(9, Math.max(1, level)),
            description: levels[Math.min(9, Math.max(1, level))]
        };
        
        console.log('Уровень мышления:', this.userData.thinking_level);
    },

    // Завершение этапа
    completeStage() {
        if (this.currentStage === 1) {
            // Показываем результат этапа 1
            const html = `
                <div class="stage-complete">
                    <div class="complete-icon">✅</div>
                    <div class="complete-title">Этап 1 завершен!</div>
                    <div class="complete-text">
                        Ваш тип восприятия: <strong>${this.userData.perception_type}</strong>
                    </div>
                    <button class="next-stage-btn" id="nextStageBtn">Перейти к этапу 2 →</button>
                </div>
            `;
            
            document.getElementById('screenContainer').innerHTML = html;
            
            document.getElementById('nextStageBtn').addEventListener('click', () => {
                this.currentStage = 2;
                this.currentQuestion = 0;
                this.showQuestion();
            });
            
        } else if (this.currentStage === 2) {
            // Показываем результат этапа 2
            const html = `
                <div class="stage-complete">
                    <div class="complete-icon">✅</div>
                    <div class="complete-title">Этап 2 завершен!</div>
                    <div class="complete-text">
                        Ваш уровень мышления: <strong>${this.userData.thinking_level.description}</strong>
                    </div>
                    <button class="next-stage-btn" id="nextStageBtn">Перейти к этапу 3 →</button>
                </div>
            `;
            
            document.getElementById('screenContainer').innerHTML = html;
            
            document.getElementById('nextStageBtn').addEventListener('click', () => {
                alert('Этап 3 будет добавлен позже');
            });
        }
    }
};

// Добавляем стили для теста
const style = document.createElement('style');
style.textContent = `
    .test-container {
        padding: 20px;
        max-width: 600px;
        margin: 0 auto;
    }
    
    .test-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 30px;
        padding: 10px;
        background-color: var(--max-panel-bg);
        border-radius: 30px;
    }
    
    .test-stage {
        color: var(--max-blue);
        font-weight: 600;
    }
    
    .test-progress {
        color: var(--max-text-secondary);
    }
    
    .test-question {
        font-size: 20px;
        margin-bottom: 30px;
        line-height: 1.5;
    }
    
    .test-options {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .test-option {
        display: flex;
        align-items: center;
        padding: 15px;
        background-color: var(--max-panel-bg);
        border: 2px solid transparent;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        text-align: left;
    }
    
    .test-option:hover {
        background-color: var(--max-hover);
        border-color: var(--max-blue);
    }
    
    .test-option.selected {
        background-color: rgba(36, 139, 242, 0.2);
        border-color: var(--max-blue);
    }
    
    .option-letter {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: var(--max-blue);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        margin-right: 15px;
        flex-shrink: 0;
    }
    
    .option-text {
        font-size: 16px;
        color: var(--max-text);
    }
    
    .stage-complete {
        text-align: center;
        padding: 40px 20px;
    }
    
    .complete-icon {
        font-size: 64px;
        margin-bottom: 20px;
    }
    
    .complete-title {
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 20px;
    }
    
    .complete-text {
        font-size: 18px;
        margin-bottom: 30px;
        line-height: 1.6;
    }
    
    .next-stage-btn {
        padding: 15px 30px;
        background-color: var(--max-blue);
        color: white;
        border: none;
        border-radius: 30px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .next-stage-btn:hover {
        background-color: var(--max-blue-hover);
    }
`;

document.head.appendChild(style);

window.Test = Test;
