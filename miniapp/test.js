// ============================================
// ПОЛНЫЙ ТЕСТ ИЗ 5 ЭТАПОВ
// Версия 2.0 - Исправлена логика подсчета и интерпретации
// ============================================

const Test = {
    // ============================================
    // СОСТОЯНИЕ ТЕСТА
    // ============================================
    currentStage: 0,
    currentQuestionIndex: 0,
    userId: null,
    answers: [],
    pollingInterval: null,
    statusMessageElement: null,
    
    // Данные для расчетов (этап 1)
    perceptionScores: {
        EXTERNAL: 0,
        INTERNAL: 0,
        SYMBOLIC: 0,
        MATERIAL: 0
    },
    perceptionType: null,
    
    // Данные для расчетов (этап 2)
    thinkingLevel: null,
    thinkingScores: {
        "1": 0, "2": 0, "3": 0, "4": 0, "5": 0,
        "6": 0, "7": 0, "8": 0, "9": 0
    },
    strategyLevels: {
        "СБ": [],
        "ТФ": [],
        "УБ": [],
        "ЧВ": []
    },
    
    // Данные для расчетов (этап 3)
    behavioralLevels: {
        "СБ": [],
        "ТФ": [],
        "УБ": [],
        "ЧВ": []
    },
    stage3Scores: [],
    
    // Данные для расчетов (этап 4)
    diltsCounts: {
        "ENVIRONMENT": 0,
        "BEHAVIOR": 0,
        "CAPABILITIES": 0,
        "VALUES": 0,
        "IDENTITY": 0
    },
    
    // Данные для расчетов (этап 5)
    deepAnswers: [],
    deepPatterns: null,
    profileData: null,
    
    // Уточнения
    clarificationIteration: 0,
    discrepancies: [],
    clarifyingAnswers: [],
    clarifyingQuestions: [],
    clarifyingCurrent: 0,
    
    // ============================================
    // СТРУКТУРА ЭТАПОВ
    // ============================================
    stages: [
        { id: 'perception', name: 'ЭТАП 1/5: ВОСПРИЯТИЕ', description: 'Линза, через которую вы смотрите на мир', total: 8 },
        { id: 'thinking', name: 'ЭТАП 2/5: МЫШЛЕНИЕ', description: 'Как вы обрабатываете информацию', total: null },
        { id: 'behavior', name: 'ЭТАП 3/5: ПОВЕДЕНИЕ', description: 'Ваши автоматические реакции', total: 8 },
        { id: 'growth', name: 'ЭТАП 4/5: ТОЧКА РОСТА', description: 'Где находится рычаг изменений', total: 8 },
        { id: 'deep', name: 'ЭТАП 5/5: ГЛУБИННЫЕ ПАТТЕРНЫ', description: 'Тип привязанности, защитные механизмы', total: 10 }
    ],
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 1 (8 вопросов) - КАК В БОТЕ
    // ============================================
    perception_questions: [
        {
            id: 'p0',
            text: 'Когда принимаешь важное решение, опираешься на:',
            options: [
                { text: '👥 Мнение и опыт других', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 } },
                { text: '💭 Внутренние ощущения, интуицию', scores: { EXTERNAL: 0, INTERNAL: 2, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '📊 Факты, цифры, данные', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '🤝 Советуюсь с близкими, но решаю сам', scores: { EXTERNAL: 1, INTERNAL: 1, SYMBOLIC: 0, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p1',
            text: 'Что вызывает тревогу?',
            options: [
                { text: '😟 Что не поймут, отвергнут', scores: { EXTERNAL: 1, INTERNAL: 0, SYMBOLIC: 2, MATERIAL: 0 } },
                { text: '⚠️ Потеряю контроль над ситуацией', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '💰 Не будет денег, стабильности', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '🤔 Сделаю неправильный выбор', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 1, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p2',
            text: 'В компании незнакомых людей ты:',
            options: [
                { text: '👀 Наблюдаю, изучаю правила', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 } },
                { text: '🎧 Прислушиваюсь к себе', scores: { EXTERNAL: 0, INTERNAL: 2, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '🎯 Ищу чем заняться', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 1 } },
                { text: '💫 Стараюсь понравиться', scores: { EXTERNAL: 1, INTERNAL: 0, SYMBOLIC: 1, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p3',
            text: 'Что важнее в работе?',
            options: [
                { text: '🎯 Смысл, предназначение', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 2, MATERIAL: 0 } },
                { text: '📈 Конкретный результат', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '🏆 Признание, статус', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '🌱 Процесс, развитие', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 0, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p4',
            text: 'Когда устал, восстанавливаешься:',
            options: [
                { text: '👥 Иду к людям за поддержкой', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 } },
                { text: '🏠 Уединяюсь с собой', scores: { EXTERNAL: 0, INTERNAL: 2, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '📋 Занимаюсь делами, рутиной', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 1 } },
                { text: '📚 Ухожу в фильмы/книги', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 1, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p5',
            text: 'Реакция на критику:',
            options: [
                { text: '😔 Обижаюсь, переживаю', scores: { EXTERNAL: 1, INTERNAL: 0, SYMBOLIC: 2, MATERIAL: 0 } },
                { text: '🔍 Анализирую, исправляю', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 0, MATERIAL: 1 } },
                { text: '🛡️ Защищаюсь, объясняю', scores: { EXTERNAL: 1, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 } },
                { text: '🤷 Обесцениваю критикующего', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 1, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p6',
            text: 'Что замечаешь в новом помещении?',
            options: [
                { text: '👥 Людей, кто где находится', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 } },
                { text: '✨ Атмосферу, освещение', scores: { EXTERNAL: 0, INTERNAL: 1, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '🏠 Предметы, структуру', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '💭 Свои ощущения', scores: { EXTERNAL: 0, INTERNAL: 2, SYMBOLIC: 0, MATERIAL: 0 } }
            ]
        },
        {
            id: 'p7',
            text: 'Что для тебя успех?',
            options: [
                { text: '🏆 Признание, уважение других', scores: { EXTERNAL: 2, INTERNAL: 0, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '😌 Внутренняя гармония', scores: { EXTERNAL: 0, INTERNAL: 2, SYMBOLIC: 1, MATERIAL: 0 } },
                { text: '💰 Достижения, статус, блага', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 2 } },
                { text: '🎯 Реализовать предназначение', scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 2, MATERIAL: 0 } }
            ]
        }
    ],
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 2 (КАК В БОТЕ - 4-5 вопросов)
    // ============================================
    thinking_questions: {
        // Для СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ (5 вопросов)
        external: [
            {
                text: 'Когда в группе возникает конфликт, вы скорее:',
                options: [
                    { text: '🔍 Замечаю только то, что касается меня', level: 2 },
                    { text: '👥 Вижу кто на чьей стороне', level: 3 },
                    { text: '📋 Понимаю явные причины', level: 4 },
                    { text: '🎯 Анализирую позиции и интересы', level: 5 },
                    { text: '🔗 Вижу систему отношений', level: 6 },
                    { text: '📜 Понимаю связь с историей группы', level: 7 },
                    { text: '🔮 Могу предсказать развитие', level: 8 },
                    { text: '🔄 Вижу повторяющиеся паттерны', level: 9 }
                ],
                measures: 'ЧВ'
            },
            {
                text: 'Как вы понимаете, почему люди поступают так, а не иначе?',
                options: [
                    { text: '🤷 Они просто такие', level: 1 },
                    { text: '🌍 Так сложились обстоятельства', level: 2 },
                    { text: '💭 У них явные мотивы', level: 3 },
                    { text: '📚 Анализирую их прошлый опыт', level: 4 },
                    { text: '💎 Понимаю их ценности', level: 5 },
                    { text: '🏠 Вижу связь с окружением', level: 6 },
                    { text: '🔮 Могу предсказать реакции', level: 7 },
                    { text: '🎭 Замечаю архетипы', level: 8 },
                    { text: '📜 Понимаю универсальные законы', level: 9 }
                ],
                measures: 'ЧВ'
            },
            {
                text: 'Когда вас критикуют, ваша мысль:',
                options: [
                    { text: '😤 Они ко мне придираются', level: 1 },
                    { text: '😞 Я что-то сделал не так', level: 2 },
                    { text: '🤔 В этот раз я ошибся', level: 3 },
                    { text: '🔄 У меня повторяется паттерн ошибок', level: 4 },
                    { text: '💭 Это связано с моими убеждениями', level: 5 },
                    { text: '🎭 Это часть моей роли', level: 6 },
                    { text: '📚 Это жизненный урок', level: 7 },
                    { text: '🌍 Универсальный паттерн', level: 8 },
                    { text: '📜 Законы развития', level: 9 }
                ],
                measures: 'СБ'
            },
            {
                text: 'Как вы относитесь к деньгам?',
                options: [
                    { text: '🌊 Приходят и уходят', level: 1 },
                    { text: '🔍 Нужно искать возможности', level: 2 },
                    { text: '💪 Результат действий', level: 3 },
                    { text: '📊 Система, которую можно выстроить', level: 4 },
                    { text: '⚡ Энергия и свобода', level: 5 },
                    { text: '🎯 Инструмент для целей', level: 6 },
                    { text: '📈 Часть экономики', level: 7 },
                    { text: '💎 Отражение ценности', level: 8 },
                    { text: '🔄 Универсальный эквивалент', level: 9 }
                ],
                measures: 'ТФ'
            },
            {
                text: 'Когда происходит что-то непонятное:',
                options: [
                    { text: '😴 Стараюсь не думать', level: 1 },
                    { text: '🔮 Ищу знаки', level: 2 },
                    { text: '📚 Обращаюсь к эксперту', level: 3 },
                    { text: '🔍 Ищу заговор', level: 4 },
                    { text: '📊 Анализирую факты', level: 5 },
                    { text: '🏛️ Смотрю в контексте системы', level: 6 },
                    { text: '📜 Ищу аналогии в истории', level: 7 },
                    { text: '🧠 Строю модели', level: 8 },
                    { text: '🔗 Ищу закономерности', level: 9 }
                ],
                measures: 'УБ'
            }
        ],
        
        // Для СМЫСЛО-ОРИЕНТИРОВАННЫЙ (4 вопроса)
        internal: [
            {
                text: 'Как ищешь смысл в происходящем?',
                options: [
                    { text: '😴 Не ищу', level: 1 },
                    { text: '💭 Чувствую, есть или нет', level: 2 },
                    { text: '📚 Спрашиваю у знающих', level: 3 },
                    { text: '💖 Анализирую свои чувства', level: 4 },
                    { text: '🔍 Ищу глубинные причины', level: 5 },
                    { text: '💎 Вижу связи с ценностями', level: 6 },
                    { text: '📖 Понимаю жизненные уроки', level: 7 },
                    { text: '🎭 Вижу архетипические сюжеты', level: 8 },
                    { text: '🌌 Понимаю универсальные смыслы', level: 9 }
                ],
                measures: 'УБ'
            },
            {
                text: 'Как выбираешь, чем заниматься?',
                options: [
                    { text: '🍃 Как получится', level: 1 },
                    { text: '😊 По настроению', level: 2 },
                    { text: '👥 По совету', level: 3 },
                    { text: '🔍 Анализирую интересы', level: 4 },
                    { text: '🎯 Ищу призвание', level: 5 },
                    { text: '💎 Связываю с ценностями', level: 6 },
                    { text: '📜 Понимаю предназначение', level: 7 },
                    { text: '🛤️ Вижу свой путь', level: 8 },
                    { text: '🌟 Следую миссии', level: 9 }
                ],
                measures: 'ТФ'
            },
            {
                text: 'В конфликте с близким по духу:',
                options: [
                    { text: '😰 Теряюсь', level: 1 },
                    { text: '🚶 Ухожу', level: 2 },
                    { text: '👍 Соглашаюсь', level: 3 },
                    { text: '🔍 Анализирую', level: 4 },
                    { text: '🤝 Ищу компромисс', level: 5 },
                    { text: '💎 Понимаю его ценности', level: 6 },
                    { text: '📚 Вижу урок', level: 7 },
                    { text: '🎭 Понимаю архетип', level: 8 },
                    { text: '📜 Вижу закономерность', level: 9 }
                ],
                measures: 'СБ'
            },
            {
                text: 'В отношениях с единомышленниками:',
                options: [
                    { text: '🪢 Привязываюсь', level: 1 },
                    { text: '🔄 Подстраиваюсь', level: 2 },
                    { text: '✨ Показываю себя', level: 3 },
                    { text: '💭 Понимаю их', level: 4 },
                    { text: '🤝 Строю партнерство', level: 5 },
                    { text: '🏛️ Создаю сообщество', level: 6 },
                    { text: '💫 Вдохновляю', level: 7 },
                    { text: '🎭 Вижу архетипы', level: 8 },
                    { text: '📜 Понимаю законы', level: 9 }
                ],
                measures: 'ЧВ'
            }
        ]
    },
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 3 (8 вопросов) - КАК В БОТЕ
    // ============================================
    behavior_questions: [
        {
            text: 'Начальник кричит несправедливо. Реакция:',
            options: [
                { text: '😶 Теряюсь, слова не идут', level: 1, strategy: 'СБ' },
                { text: '🚶 Придумываю причину уйти', level: 2, strategy: 'СБ' },
                { text: '😤 Соглашаюсь внешне, внутри кипит', level: 3, strategy: 'СБ' },
                { text: '😌 Сохраняю спокойствие, молчу', level: 4, strategy: 'СБ' },
                { text: '😄 Пытаюсь перевести в шутку', level: 5, strategy: 'СБ' },
                { text: '🗣️ Спокойно говорю, что не согласен', level: 6, strategy: 'СБ' }
            ]
        },
        {
            text: 'Срочно нужны деньги. Первое действие:',
            options: [
                { text: '🙏 Попрошу в долг', level: 1, strategy: 'ТФ' },
                { text: '💼 Найду разовую подработку', level: 2, strategy: 'ТФ' },
                { text: '🏪 Продам что-то из вещей', level: 3, strategy: 'ТФ' },
                { text: '🎨 Предложу свои услуги', level: 4, strategy: 'ТФ' },
                { text: '💰 Использую накопления', level: 5, strategy: 'ТФ' },
                { text: '📊 Создам системный доход', level: 6, strategy: 'ТФ' }
            ]
        },
        {
            text: 'Экономический кризис. Твое объяснение:',
            options: [
                { text: '😴 Стараюсь не думать', level: 1, strategy: 'УБ' },
                { text: '🔮 Судьба, знак, карма', level: 2, strategy: 'УБ' },
                { text: '📚 Верю экспертам', level: 3, strategy: 'УБ' },
                { text: '🎭 Кто-то специально устроил', level: 4, strategy: 'УБ' },
                { text: '📊 Анализирую факты сам', level: 5, strategy: 'УБ' },
                { text: '🔄 Понимаю экономические циклы', level: 6, strategy: 'УБ' }
            ]
        },
        {
            text: 'В новом коллективе в первые дни:',
            options: [
                { text: '🤝 Держусь с тем, кто принял', level: 1, strategy: 'ЧВ' },
                { text: '👀 Наблюдаю и копирую', level: 2, strategy: 'ЧВ' },
                { text: '✨ Стараюсь запомниться', level: 3, strategy: 'ЧВ' },
                { text: '🎯 Смотрю, кто на что влияет', level: 4, strategy: 'ЧВ' },
                { text: '🤝 Ищу общие интересы', level: 5, strategy: 'ЧВ' },
                { text: '🌱 Выстраиваю отношения постепенно', level: 6, strategy: 'ЧВ' }
            ]
        },
        {
            text: 'Близкий снова раздражает. Ты:',
            options: [
                { text: '😔 Терплю, не знаю как начать', level: 1, strategy: 'СБ' },
                { text: '🚶 Незаметно дистанцируюсь', level: 2, strategy: 'СБ' },
                { text: '💬 Намекаю, прямо не говорю', level: 3, strategy: 'СБ' },
                { text: '🌋 Коплю и потом взрываюсь', level: 4, strategy: 'СБ' },
                { text: '🤔 Пытаюсь понять причину', level: 5, strategy: 'СБ' },
                { text: '🗣️ Говорю прямо о чувствах', level: 6, strategy: 'СБ' }
            ]
        },
        {
            text: 'Возможность заработать, но нужно вложиться:',
            options: [
                { text: '🔍 Ищу вариант без вложений', level: 1, strategy: 'ТФ' },
                { text: '🎲 Пробую на минимуме', level: 2, strategy: 'ТФ' },
                { text: '🧮 Считаю, сколько заработаю', level: 3, strategy: 'ТФ' },
                { text: '📊 Оцениваю вложения и доход', level: 4, strategy: 'ТФ' },
                { text: '⚙️ Думаю, как встроить в процессы', level: 5, strategy: 'ТФ' },
                { text: '📈 Анализирую, как масштабировать', level: 6, strategy: 'ТФ' }
            ]
        },
        {
            text: 'Коллега поступил странно, не понимаю зачем:',
            options: [
                { text: '😐 Не придаю значения', level: 1, strategy: 'УБ' },
                { text: '🤷 Он просто такой человек', level: 2, strategy: 'УБ' },
                { text: '📞 Спрашиваю у других', level: 3, strategy: 'УБ' },
                { text: '🎭 Он что-то замышляет', level: 4, strategy: 'УБ' },
                { text: '🔄 Ищу паттерн в поведении', level: 5, strategy: 'УБ' },
                { text: '🧠 Анализирую его мотивы', level: 6, strategy: 'УБ' }
            ]
        },
        {
            text: 'Нужна помощь от того, с кем сложные отношения:',
            options: [
                { text: '😟 Не прошу, боюсь отказа', level: 1, strategy: 'ЧВ' },
                { text: '🎁 Сначала сделаю для него', level: 2, strategy: 'ЧВ' },
                { text: '🎭 Создам ситуацию, где сам предложит', level: 3, strategy: 'ЧВ' },
                { text: '💬 Объясню, почему мне важно', level: 4, strategy: 'ЧВ' },
                { text: '🤝 Говорю прямо, предлагаю обмен', level: 5, strategy: 'ЧВ' },
                { text: '🌱 Строю долгосрочные отношения', level: 6, strategy: 'ЧВ' }
            ]
        }
    ],
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 4 (8 вопросов) - КАК В БОТЕ
    // ============================================
    growth_questions: [
        { text: 'Если что-то не получается, причина в:', options: [
            { text: '🌍 Обстоятельствах, людях вокруг', dilts: 'ENVIRONMENT' },
            { text: '🛠️ Моих действиях', dilts: 'BEHAVIOR' },
            { text: '📚 Нехватке навыков, опыта', dilts: 'CAPABILITIES' },
            { text: '💎 Моих убеждениях, ценностях', dilts: 'VALUES' },
            { text: '🧠 Моей личности, характере', dilts: 'IDENTITY' }
        ]},
        { text: 'Самый ценный результат работы с психологом:', options: [
            { text: '🤝 Научиться взаимодействовать с людьми', dilts: 'ENVIRONMENT' },
            { text: '🔄 Изменить привычки и реакции', dilts: 'BEHAVIOR' },
            { text: '🎓 Развить новые навыки', dilts: 'CAPABILITIES' },
            { text: '💎 Понять свои ценности', dilts: 'VALUES' },
            { text: '🔍 Найти себя', dilts: 'IDENTITY' }
        ]},
        { text: 'Когда злишься на себя, чаще всего за что?', options: [
            { text: '🌍 Не смог повлиять на ситуацию', dilts: 'ENVIRONMENT' },
            { text: '🛠️ Сделал не то, поступил неправильно', dilts: 'BEHAVIOR' },
            { text: '📚 Не справился, не хватило умения', dilts: 'CAPABILITIES' },
            { text: '💎 Предал свои принципы', dilts: 'VALUES' },
            { text: '😞 Что я такой бестолковый', dilts: 'IDENTITY' }
        ]},
        { text: 'Что труднее всего в отношениях с близкими?', options: [
            { text: '🌍 Они меня не понимают', dilts: 'ENVIRONMENT' },
            { text: '🔄 Мое собственное поведение', dilts: 'BEHAVIOR' },
            { text: '📚 Не умею донести', dilts: 'CAPABILITIES' },
            { text: '💎 У нас разные ценности', dilts: 'VALUES' },
            { text: '😔 Теряю себя', dilts: 'IDENTITY' }
        ]},
        { text: 'Что останавливает от больших целей?', options: [
            { text: '🌍 Внешние обстоятельства', dilts: 'ENVIRONMENT' },
            { text: '🔄 Не знаю с чего начать', dilts: 'BEHAVIOR' },
            { text: '📚 Не хватает знаний, навыков', dilts: 'CAPABILITIES' },
            { text: '💎 Не уверен, что важно для меня', dilts: 'VALUES' },
            { text: '😔 Не верю, что способен', dilts: 'IDENTITY' }
        ]},
        { text: 'Как объясняешь свои успехи?', options: [
            { text: '🍀 Повезло, оказался в нужном месте', dilts: 'ENVIRONMENT' },
            { text: '💪 Сделал правильно, приложил усилия', dilts: 'BEHAVIOR' },
            { text: '🎯 Смог, справился', dilts: 'CAPABILITIES' },
            { text: '💎 Был верен принципам', dilts: 'VALUES' },
            { text: '🧠 Я такой человек', dilts: 'IDENTITY' }
        ]},
        { text: 'Что хочешь изменить в себе в первую очередь?', options: [
            { text: '🌍 Свою жизнь, окружение', dilts: 'ENVIRONMENT' },
            { text: '🔄 Привычки, реакции', dilts: 'BEHAVIOR' },
            { text: '📚 Способности, навыки', dilts: 'CAPABILITIES' },
            { text: '💎 Ценности, убеждения', dilts: 'VALUES' },
            { text: '🧠 Личность, характер', dilts: 'IDENTITY' }
        ]},
        { text: 'О чем чаще всего жалеешь?', options: [
            { text: '🌍 Что не сложились обстоятельства', dilts: 'ENVIRONMENT' },
            { text: '🔄 О том, что сделал или не сделал', dilts: 'BEHAVIOR' },
            { text: '📚 Что не умел, не знал', dilts: 'CAPABILITIES' },
            { text: '💎 Что предал свои принципы', dilts: 'VALUES' },
            { text: '😔 Что был не собой', dilts: 'IDENTITY' }
        ]}
    ],
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 5 (10 вопросов) - КАК В БОТЕ
    // ============================================
    deep_questions: [
        { text: 'В детстве, когда расстраивался, родители:', options: [
            { text: '🤗 Утешали, обнимали', pattern: 'secure', target: 'attachment' },
            { text: '💪 Говорили "не плачь, будь сильным"', pattern: 'avoidant', target: 'attachment' },
            { text: '🎭 Реагировали по-разному', pattern: 'anxious', target: 'attachment' },
            { text: '🚶 Оставляли одного остыть', pattern: 'dismissive', target: 'attachment' }
        ]},
        { text: 'Когда случается плохое, я обычно:', options: [
            { text: '🔍 Ищу виноватого', pattern: 'projection', target: 'defense' },
            { text: '🧠 Объясняю логически', pattern: 'rationalization', target: 'defense' },
            { text: '😴 Стараюсь не думать', pattern: 'denial', target: 'defense' },
            { text: '😤 Злюсь и раздражаюсь', pattern: 'regression', target: 'defense' }
        ]},
        { text: 'В отношениях чаще всего боюсь, что:', options: [
            { text: '😢 Меня бросят', pattern: 'abandonment', target: 'fear' },
            { text: '🎮 Будут управлять мной', pattern: 'control', target: 'fear' },
            { text: '🙅 Не поймут', pattern: 'misunderstanding', target: 'fear' },
            { text: '😔 Не справлюсь', pattern: 'inadequacy', target: 'fear' }
        ]},
        { text: 'Какое утверждение ближе всего?', options: [
            { text: '😞 Я недостаточно хорош', pattern: 'not_good_enough', target: 'belief' },
            { text: '🤔 Людям нельзя доверять', pattern: 'no_trust', target: 'belief' },
            { text: '🌍 Мир опасен', pattern: 'world_dangerous', target: 'belief' },
            { text: '⭐ Я должен быть идеальным', pattern: 'perfectionism', target: 'belief' }
        ]},
        { text: 'Когда злюсь, я обычно:', options: [
            { text: '💥 Выплёскиваю на других', pattern: 'externalize', target: 'anger_style' },
            { text: '🤐 Подавляю и молчу', pattern: 'suppress', target: 'anger_style' },
            { text: '🏠 Ухожу в себя', pattern: 'withdraw', target: 'anger_style' },
            { text: '🔧 Ищу решение', pattern: 'constructive', target: 'anger_style' }
        ]},
        { text: 'Мои друзья сказали бы, что я:', options: [
            { text: '😭 Слишком эмоциональный', pattern: 'emotional', target: 'social_role' },
            { text: '🧠 Слишком рациональный', pattern: 'rational', target: 'social_role' },
            { text: '🤝 Надёжный, но закрытый', pattern: 'reliable_closed', target: 'social_role' },
            { text: '🎉 Душа компании', pattern: 'soul_company', target: 'social_role' }
        ]},
        { text: 'В стрессе я:', options: [
            { text: '😰 Суечусь и паникую', pattern: 'panic', target: 'stress_response' },
            { text: '😶 Замираю и тупею', pattern: 'freeze', target: 'stress_response' },
            { text: '🎯 Становлюсь сверхсобранным', pattern: 'hyperfocus', target: 'stress_response' },
            { text: '🤝 Ищу поддержку', pattern: 'seek_support', target: 'stress_response' }
        ]},
        { text: 'Что для тебя самое важное в жизни?', options: [
            { text: '🛡️ Безопасность, стабильность', pattern: 'security', target: 'core_value' },
            { text: '🕊️ Свобода, независимость', pattern: 'freedom', target: 'core_value' },
            { text: '❤️ Любовь, близость', pattern: 'love', target: 'core_value' },
            { text: '🏆 Достижения, успех', pattern: 'achievement', target: 'core_value' }
        ]},
        { text: 'Когда меня критикуют, я:', options: [
            { text: '😢 Обижаюсь и закрываюсь', pattern: 'shutdown', target: 'criticism_response' },
            { text: '⚔️ Атакую в ответ', pattern: 'counterattack', target: 'criticism_response' },
            { text: '🔍 Анализирую, правы ли они', pattern: 'analyze', target: 'criticism_response' },
            { text: '👍 Соглашаюсь, чтобы не спорить', pattern: 'appease', target: 'criticism_response' }
        ]},
        { text: 'Моя главная внутренняя проблема:', options: [
            { text: '😔 Страх быть покинутым', pattern: 'abandonment_fear', target: 'core_issue' },
            { text: '😰 Страх неудачи', pattern: 'failure_fear', target: 'core_issue' },
            { text: '🎭 Страх быть собой', pattern: 'authenticity_fear', target: 'core_issue' },
            { text: '⚔️ Страх конфликтов', pattern: 'conflict_fear', target: 'core_issue' }
        ]}
    ],
    
    // ============================================
    // РАСЧЕТНЫЕ ФУНКЦИИ
    // ============================================
    
    determinePerceptionType() {
        const external = this.perceptionScores.EXTERNAL;
        const internal = this.perceptionScores.INTERNAL;
        const symbolic = this.perceptionScores.SYMBOLIC;
        const material = this.perceptionScores.MATERIAL;
        
        const attention = external > internal ? "EXTERNAL" : "INTERNAL";
        const anxiety = symbolic > material ? "SYMBOLIC" : "MATERIAL";
        
        if (attention === "EXTERNAL" && anxiety === "SYMBOLIC") {
            return "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ";
        } else if (attention === "EXTERNAL" && anxiety === "MATERIAL") {
            return "СТАТУСНО-ОРИЕНТИРОВАННЫЙ";
        } else if (attention === "INTERNAL" && anxiety === "SYMBOLIC") {
            return "СМЫСЛО-ОРИЕНТИРОВАННЫЙ";
        } else {
            return "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ";
        }
    },
    
    calculateThinkingLevel() {
        let totalScore = 0;
        for (let level in this.thinkingScores) {
            totalScore += this.thinkingScores[level];
        }
        
        if (totalScore <= 10) return 1;
        else if (totalScore <= 20) return 2;
        else if (totalScore <= 30) return 3;
        else if (totalScore <= 40) return 4;
        else if (totalScore <= 50) return 5;
        else if (totalScore <= 60) return 6;
        else if (totalScore <= 70) return 7;
        else if (totalScore <= 80) return 8;
        else return 9;
    },
    
    getLevelGroup(level) {
        if (level <= 3) return "1-3";
        if (level <= 6) return "4-6";
        return "7-9";
    },
    
    calculateFinalLevel() {
        const stage2Level = this.thinkingLevel;
        const stage3Avg = this.stage3Scores.length > 0 
            ? this.stage3Scores.reduce((a, b) => a + b, 0) / this.stage3Scores.length 
            : stage2Level;
        return Math.round((stage2Level + stage3Avg) / 2);
    },
    
    determineDominantDilts() {
        let max = 0;
        let dominant = "BEHAVIOR";
        for (let level in this.diltsCounts) {
            if (this.diltsCounts[level] > max) {
                max = this.diltsCounts[level];
                dominant = level;
            }
        }
        return dominant;
    },
    
    calculateFinalProfile() {
        const sbAvg = this.behavioralLevels["СБ"].length 
            ? this.behavioralLevels["СБ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["СБ"].length 
            : 3;
        const tfAvg = this.behavioralLevels["ТФ"].length 
            ? this.behavioralLevels["ТФ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["ТФ"].length 
            : 3;
        const ubAvg = this.behavioralLevels["УБ"].length 
            ? this.behavioralLevels["УБ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["УБ"].length 
            : 3;
        const chvAvg = this.behavioralLevels["ЧВ"].length 
            ? this.behavioralLevels["ЧВ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["ЧВ"].length 
            : 3;
        
        return {
            displayName: `СБ-${Math.round(sbAvg)}_ТФ-${Math.round(tfAvg)}_УБ-${Math.round(ubAvg)}_ЧВ-${Math.round(chvAvg)}`,
            perceptionType: this.perceptionType,
            thinkingLevel: this.thinkingLevel,
            sbLevel: Math.round(sbAvg),
            tfLevel: Math.round(tfAvg),
            ubLevel: Math.round(ubAvg),
            chvLevel: Math.round(chvAvg),
            dominantDilts: this.determineDominantDilts(),
            diltsCounts: this.diltsCounts
        };
    },
    
    analyzeDeepPatterns() {
        const patterns = { secure: 0, anxious: 0, avoidant: 0, dismissive: 0 };
        (this.deepAnswers || []).forEach(a => {
            if (a.pattern && patterns[a.pattern] !== undefined) {
                patterns[a.pattern] = (patterns[a.pattern] || 0) + 1;
            }
        });
        
        let max = 0, dominant = "secure";
        for (let p in patterns) {
            if (patterns[p] > max) { max = patterns[p]; dominant = p; }
        }
        
        const map = {
            secure: "🤗 Надежный",
            anxious: "😥 Тревожный",
            avoidant: "🛡️ Избегающий",
            dismissive: "🏔️ Отстраненный"
        };
        
        return { attachment: map[dominant] || "🤗 Надежный", patterns };
    },
    
    // ============================================
    // ИНТЕРПРЕТАЦИИ ПОСЛЕ ЭТАПОВ
    // ============================================
    
    getStage1Interpretation() {
        const interpretations = {
            "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ": "Вы ориентированы на других, чутко считываете настроение и ожидания окружающих. Ваше внимание направлено вовне, а тревога связана с отвержением.",
            "СТАТУСНО-ОРИЕНТИРОВАННЫЙ": "Для вас важны статус, положение и материальные достижения. Вы ориентированы на внешние атрибуты успеха, а тревожитесь о потере контроля.",
            "СМЫСЛО-ОРИЕНТИРОВАННЫЙ": "Вы ищете глубинные смыслы и ориентируетесь на внутренние ощущения. Ваша тревога связана с отвержением и непониманием.",
            "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ": "Вы ориентированы на практические результаты и конкретные действия. Ваше внимание направлено внутрь, а тревога — о потере контроля."
        };
        return interpretations[this.perceptionType] || interpretations["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"];
    },
    
    getStage2Interpretation() {
        const levelGroup = this.getLevelGroup(this.thinkingLevel);
        
        const interpretations = {
            "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ": {
                "1-3": "Ваше мышление конкретно и привязано к социальным ситуациям. Вы хорошо понимаете сиюминутные взаимодействия, но не всегда видите общие закономерности.",
                "4-6": "Вы замечаете социальные закономерности и тренды. Видите, как складываются отношения и почему люди ведут себя определенным образом.",
                "7-9": "Вы видите глубинные социальные механизмы и законы. Можете предсказывать развитие социальных ситуаций."
            },
            "СТАТУСНО-ОРИЕНТИРОВАННЫЙ": {
                "1-3": "Ваше мышление направлено на достижение статуса. Вы хорошо понимаете иерархию и позиции, но не всегда видите скрытые механизмы.",
                "4-6": "Вы стратегически мыслите в категориях статуса. Видите, как меняются позиции и что нужно для продвижения.",
                "7-9": "Вы видите иерархические закономерности. Понимаете законы власти и влияния."
            },
            "СМЫСЛО-ОРИЕНТИРОВАННЫЙ": {
                "1-3": "Вы ищете смыслы в отдельных событиях. Вам важно понять 'почему' в конкретных ситуациях.",
                "4-6": "Вы находите закономерности в жизненных историях. Видите связь событий и их глубинный смысл.",
                "7-9": "Вы постигаете глубинные смыслы бытия. Видите универсальные законы, управляющие жизнью."
            },
            "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ": {
                "1-3": "Ваше мышление конкретно и практично. Вы хорошо решаете текущие задачи, но не всегда видите перспективу.",
                "4-6": "Вы видите практические закономерности. Понимаете, как устроены процессы и системы.",
                "7-9": "Вы создаёте эффективные практические модели. Можете оптимизировать любые процессы."
            }
        };
        
        return interpretations[this.perceptionType]?.[levelGroup] || interpretations["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"]["4-6"];
    },
    
    getStage3Interpretation() {
        const finalLevel = this.calculateFinalLevel();
        const feedback = {
            1: "Ваше поведение реактивно — вы скорее отвечаете на стимулы, чем действуете осознанно.",
            2: "Вы начинаете осознавать свои автоматические реакции.",
            3: "Вы можете выбирать реакции, но не всегда.",
            4: "Вы управляете своим поведением в большинстве ситуаций.",
            5: "Поведение становится инструментом для достижения целей.",
            6: "Вы мастерски владеете своим поведением."
        };
        
        let level = finalLevel <= 2 ? 1 : finalLevel <= 4 ? 2 : finalLevel <= 6 ? 3 : finalLevel <= 8 ? 4 : 5;
        if (finalLevel >= 9) level = 6;
        
        return feedback[level] || feedback[3];
    },
    
    getStage5Interpretation() {
        const deep = this.deepPatterns || { attachment: "🤗 Надежный" };
        
        const attachmentDesc = {
            "🤗 Надежный": "✅ У тебя надёжный тип привязанности — ты уверен в отношениях и не боишься близости.",
            "😥 Тревожный": "⚠️ Тревожный тип привязанности: ты часто боишься, что тебя бросят, нуждаешься в подтверждениях любви.",
            "🛡️ Избегающий": "⚠️ Избегающий тип привязанности: ты держишь дистанцию, боишься близости, надеясь только на себя.",
            "🏔️ Отстраненный": "⚠️ Отстранённый тип: ты обесцениваешь отношения, считая, что лучше быть одному."
        };
        
        return `🔗 **Тип привязанности:**\n${attachmentDesc[deep.attachment] || attachmentDesc["🤗 Надежный"]}`;
    },
    
    // ============================================
    // ПОЛУЧЕНИЕ USER_ID
    // ============================================
    
    getUserId() {
        // Проверяем window.maxContext
        if (window.maxContext?.user_id && window.maxContext.user_id !== 'null' && window.maxContext.user_id !== 'undefined') {
            return window.maxContext.user_id;
        }
        
        // Проверяем URL параметры
        const urlParams = new URLSearchParams(window.location.search);
        const urlUserId = urlParams.get('user_id');
        if (urlUserId && urlUserId !== 'null' && urlUserId !== 'undefined') {
            return urlUserId;
        }
        
        // Проверяем localStorage
        const stored = localStorage.getItem('fredi_user_id');
        if (stored && stored !== 'null' && stored !== 'undefined') {
            return stored;
        }
        
        console.warn('⚠️ userId не найден!');
        return null;
    },
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    init(userId) {
        // Получаем userId из разных источников
        const urlParams = new URLSearchParams(window.location.search);
        const urlUserId = urlParams.get('user_id');
        
        this.userId = userId || this.getUserId() || urlUserId;
        
        if (!this.userId || this.userId === 'null' || this.userId === 'undefined') {
            console.warn('⚠️ userId не найден! Тест будет работать в локальном режиме');
            this.userId = null;
        } else {
            console.log('✅ userId найден:', this.userId);
            localStorage.setItem('fredi_user_id', this.userId);
        }
        
        // Сброс состояния
        this.currentStage = 0;
        this.currentQuestionIndex = 0;
        this.answers = [];
        this.perceptionScores = { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 };
        this.perceptionType = null;
        this.thinkingLevel = null;
        this.thinkingScores = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0 };
        this.strategyLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.behavioralLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.stage3Scores = [];
        this.diltsCounts = { "ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0 };
        this.deepAnswers = [];
        this.deepPatterns = null;
        this.profileData = null;
        
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        
        this.loadProgress();
        console.log('📝 Тест инициализирован для пользователя:', this.userId);
    },
    
    loadProgress() {
        if (!this.userId) return;
        
        const saved = localStorage.getItem(`test_${this.userId}`);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                this.currentStage = data.currentStage || 0;
                this.currentQuestionIndex = data.currentQuestionIndex || 0;
                this.answers = data.answers || [];
                this.perceptionScores = data.perceptionScores || { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 };
                this.perceptionType = data.perceptionType || null;
                this.thinkingLevel = data.thinkingLevel || null;
                this.thinkingScores = data.thinkingScores || { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0 };
                this.strategyLevels = data.strategyLevels || { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
                this.behavioralLevels = data.behavioralLevels || { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
                this.stage3Scores = data.stage3Scores || [];
                this.diltsCounts = data.diltsCounts || { "ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0 };
                this.deepAnswers = data.deepAnswers || [];
                this.deepPatterns = data.deepPatterns || null;
                this.profileData = data.profileData || null;
                
                if (this.perceptionType) {
                    const questions = this.perceptionType.includes("СОЦИАЛЬНО") || this.perceptionType.includes("СТАТУСНО") 
                        ? this.thinking_questions.external 
                        : this.thinking_questions.internal;
                    this.stages[1].total = questions.length;
                }
            } catch (e) { console.warn('❌ Ошибка загрузки прогресса:', e); }
        }
    },
    
    saveProgress() {
        if (!this.userId) return;
        
        const data = {
            currentStage: this.currentStage,
            currentQuestionIndex: this.currentQuestionIndex,
            answers: this.answers,
            perceptionScores: this.perceptionScores,
            perceptionType: this.perceptionType,
            thinkingLevel: this.thinkingLevel,
            thinkingScores: this.thinkingScores,
            strategyLevels: this.strategyLevels,
            behavioralLevels: this.behavioralLevels,
            stage3Scores: this.stage3Scores,
            diltsCounts: this.diltsCounts,
            deepAnswers: this.deepAnswers,
            deepPatterns: this.deepPatterns,
            profileData: this.profileData,
            updatedAt: new Date().toISOString()
        };
        localStorage.setItem(`test_${this.userId}`, JSON.stringify(data));
        console.log('💾 Прогресс сохранен');
    },
    
    // ============================================
    // ЗАПУСК ТЕСТА
    // ============================================
    
    start() {
        this.currentStage = 0;
        this.currentQuestionIndex = 0;
        this.answers = [];
        this.perceptionScores = { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 };
        this.perceptionType = null;
        this.thinkingLevel = null;
        this.thinkingScores = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0 };
        this.strategyLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.behavioralLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.stage3Scores = [];
        this.diltsCounts = { "ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0 };
        this.deepAnswers = [];
        this.deepPatterns = null;
        this.profileData = null;
        this.saveProgress();
        this.showTestScreen();
        
        setTimeout(() => {
            this.addBotMessage('🧠 Начинаем тест из 5 этапов. Я буду задавать вопросы, а ты выбирай ответы.');
            setTimeout(() => this.sendStageIntro(), 1000);
        }, 100);
    },
    
    showTestScreen() {
        const container = document.getElementById('screenContainer');
        if (!container) return;
        container.innerHTML = `
            <div class="test-messages-container" id="testMessagesContainer">
                <div class="test-messages-list" id="testMessagesList"></div>
            </div>
        `;
    },
    
    sendStageIntro() {
        const stage = this.stages[this.currentStage];
        let text = `🧠 **${stage.name}**\n\n${stage.description}`;
        
        if (stage.id === 'thinking' && this.perceptionType) {
            text += `\n\nВаш тип восприятия: ${this.perceptionType}`;
            const questions = this.perceptionType.includes("СОЦИАЛЬНО") || this.perceptionType.includes("СТАТУСНО") 
                ? this.thinking_questions.external 
                : this.thinking_questions.internal;
            stage.total = questions.length;
        }
        
        text += `\n\n📊 **Всего вопросов:** ${stage.total}\n⏱ **Время:** ~${stage.id === 'thinking' ? '3-4' : '3'} минуты`;
        
        this.addBotMessage(text);
        setTimeout(() => this.sendNextQuestion(), 2000);
    },
    
    // ============================================
    // ОТРИСОВКА СООБЩЕНИЙ
    // ============================================
    
    addBotMessage(text, isHtml = true) {
        const list = document.getElementById('testMessagesList');
        if (!list) return;
        const msg = document.createElement('div');
        msg.className = 'message bot-message';
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        if (isHtml) {
            textDiv.innerHTML = text.replace(/\n/g, '<br>');
        } else {
            textDiv.textContent = text;
        }
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = 'только что';
        bubble.appendChild(textDiv);
        bubble.appendChild(timeDiv);
        msg.appendChild(bubble);
        list.appendChild(msg);
        this.scrollToBottom();
        return msg;
    },
    
    addUserMessage(text) {
        const list = document.getElementById('testMessagesList');
        if (!list) return;
        const msg = document.createElement('div');
        msg.className = 'message user-message';
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = text;
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = 'только что';
        bubble.appendChild(textDiv);
        bubble.appendChild(timeDiv);
        msg.appendChild(bubble);
        list.appendChild(msg);
        this.scrollToBottom();
    },
    
    addQuestionMessage(text, options, callback, current, total) {
        const list = document.getElementById('testMessagesList');
        if (!list) return;
        
        const msg = document.createElement('div');
        msg.className = 'message bot-message';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = `<strong>Вопрос ${current}/${total}</strong><br><br>${text}`;
        
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'message-buttons';
        
        options.forEach((opt, idx) => {
            const optText = typeof opt === 'object' ? opt.text : opt;
            const btn = document.createElement('button');
            btn.className = 'message-button';
            btn.setAttribute('data-option-index', idx);
            btn.innerHTML = `<span>${optText}</span>`;
            
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.optionIndex);
                const option = options[index];
                const optionText = typeof option === 'object' ? option.text : option;
                
                this.addUserMessage(optionText);
                
                const buttonsContainer = msg.querySelector('.message-buttons');
                if (buttonsContainer) {
                    buttonsContainer.remove();
                }
                
                callback(index, option);
            });
            
            buttonsDiv.appendChild(btn);
        });
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = `📊 Прогресс: ${Math.round((current / total) * 100)}%`;
        
        bubble.appendChild(textDiv);
        bubble.appendChild(buttonsDiv);
        bubble.appendChild(timeDiv);
        msg.appendChild(bubble);
        
        list.appendChild(msg);
        this.scrollToBottom();
    },
    
    addMessageWithButtons(text, buttons) {
        const list = document.getElementById('testMessagesList');
        if (!list) return;
        
        const msg = document.createElement('div');
        msg.className = 'message bot-message';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = text.replace(/\n/g, '<br>');
        
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'message-buttons';
        
        buttons.forEach((btn, i) => {
            const button = document.createElement('button');
            button.className = 'message-button';
            button.setAttribute('data-callback', i);
            button.innerHTML = `<span>${btn.text}</span>`;
            
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(button.dataset.callback);
                
                const buttonsContainer = msg.querySelector('.message-buttons');
                if (buttonsContainer) {
                    buttonsContainer.remove();
                }
                
                buttons[idx].callback();
            });
            
            buttonsDiv.appendChild(button);
        });
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = 'только что';
        
        bubble.appendChild(textDiv);
        bubble.appendChild(buttonsDiv);
        bubble.appendChild(timeDiv);
        msg.appendChild(bubble);
        
        list.appendChild(msg);
        this.scrollToBottom();
        return msg;
    },
    
    scrollToBottom() {
        setTimeout(() => {
            const container = document.getElementById('testMessagesContainer');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 50);
    },
    
    // ============================================
    // ЛОГИКА ТЕСТА
    // ============================================
    
    getCurrentQuestions() {
        const stage = this.stages[this.currentStage];
        
        if (stage.id === 'perception') return this.perception_questions;
        if (stage.id === 'thinking') {
            const isExternal = this.perceptionType === "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ" || 
                               this.perceptionType === "СТАТУСНО-ОРИЕНТИРОВАННЫЙ";
            return isExternal ? this.thinking_questions.external : this.thinking_questions.internal;
        }
        if (stage.id === 'behavior') return this.behavior_questions;
        if (stage.id === 'growth') return this.growth_questions;
        if (stage.id === 'deep') return this.deep_questions;
        return [];
    },
    
    sendNextQuestion() {
        if (this.currentStage >= this.stages.length) {
            this.showFinalProfile();
            return;
        }
        
        const stage = this.stages[this.currentStage];
        const questions = this.getCurrentQuestions();
        
        if (this.currentQuestionIndex >= stage.total) {
            this.completeCurrentStage();
            return;
        }
        
        const q = questions[this.currentQuestionIndex];
        this.addQuestionMessage(
            q.text,
            q.options,
            (idx, opt) => this.handleAnswer(stage.id, q, idx, opt),
            this.currentQuestionIndex + 1,
            stage.total
        );
    },
    
    handleAnswer(stageId, q, idx, opt) {
        this.answers.push({
            stage: stageId,
            questionIndex: this.currentQuestionIndex,
            questionId: q.id,
            question: q.text,
            answer: opt.text,
            option: idx,
            scores: opt.scores,
            level: opt.level,
            strategy: opt.strategy,
            dilts: opt.dilts,
            pattern: opt.pattern,
            target: q.target
        });
        
        // Этап 1: Восприятие
        if (stageId === 'perception' && opt.scores) {
            for (let axis in opt.scores) {
                this.perceptionScores[axis] += opt.scores[axis];
            }
        }
        
        // Этап 2: Мышление
        if (stageId === 'thinking' && opt.level) {
            this.thinkingScores[opt.level] = (this.thinkingScores[opt.level] || 0) + 1;
            
            if (q.measures && q.measures !== 'thinking') {
                this.strategyLevels[q.measures].push(opt.level);
            }
        }
        
        // Этап 3: Поведение
        if (stageId === 'behavior' && opt.level) {
            this.stage3Scores.push(opt.level);
            if (opt.strategy) {
                this.behavioralLevels[opt.strategy].push(opt.level);
            }
        }
        
        // Этап 4: Точка роста
        if (stageId === 'growth' && opt.dilts) {
            this.diltsCounts[opt.dilts] = (this.diltsCounts[opt.dilts] || 0) + 1;
        }
        
        // Этап 5: Глубинные паттерны
        if (stageId === 'deep') {
            this.deepAnswers.push({
                questionId: q.id,
                pattern: opt.pattern,
                target: q.target
            });
        }
        
        this.saveProgress();
        this.currentQuestionIndex++;
        setTimeout(() => this.sendNextQuestion(), 800);
    },
    
    completeCurrentStage() {
        const stage = this.stages[this.currentStage];
        
        if (stage.id === 'perception') {
            this.perceptionType = this.determinePerceptionType();
            this.stages[1].total = this.perceptionType.includes("СОЦИАЛЬНО") || this.perceptionType.includes("СТАТУСНО") 
                ? this.thinking_questions.external.length 
                : this.thinking_questions.internal.length;
            this.showStage1Result();
            
        } else if (stage.id === 'thinking') {
            this.thinkingLevel = this.calculateThinkingLevel();
            this.showStage2Result();
            
        } else if (stage.id === 'behavior') {
            this.showStage3Result();
            
        } else if (stage.id === 'growth') {
            this.profileData = this.calculateFinalProfile();
            this.showStage4Result();
            
        } else if (stage.id === 'deep') {
            this.deepPatterns = this.analyzeDeepPatterns();
            this.showStage5Result();
        }
    },
    
    // ============================================
    // ЭКРАН 1: РЕЗУЛЬТАТ ЭТАПА 1
    // ============================================
    showStage1Result() {
        const interpretation = this.getStage1Interpretation();
        
        const text = `✨ **РЕЗУЛЬТАТ ЭТАПА 1**\n\nВаш тип восприятия: **${this.perceptionType}**\n\n${interpretation}\n\n▶️ **ЧТО ДАЛЬШЕ?**\n\n**Этап 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ**\n\nМы узнали, как вы воспринимаете мир. Теперь исследуем, как вы обрабатываете информацию.\n\n📊 **Вопросов:** ${this.stages[1].total}\n⏱ **Время:** ~3-4 минуты`;
        
        this.addMessageWithButtons(text, [
            { text: "▶️ Перейти к этапу 2", callback: () => this.goToNextStage() }
        ]);
    },
    
    // ============================================
    // ЭКРАН 2: РЕЗУЛЬТАТ ЭТАПА 2
    // ============================================
    showStage2Result() {
        const interpretation = this.getStage2Interpretation();
        
        const text = `✨ **РЕЗУЛЬТАТ ЭТАПА 2**\n\nУровень мышления: **${this.thinkingLevel}/9**\n\n${interpretation}\n\n▶️ **ЧТО ДАЛЬШЕ?**\n\n**Этап 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ**\n\nТеперь посмотрим, как вы действуете на автомате.\n\n📊 **Вопросов:** 8\n⏱ **Время:** ~3 минуты`;
        
        this.addMessageWithButtons(text, [
            { text: "▶️ Перейти к этапу 3", callback: () => this.goToNextStage() }
        ]);
    },
    
    // ============================================
    // ЭКРАН 3: РЕЗУЛЬТАТ ЭТАПА 3
    // ============================================
    showStage3Result() {
        const interpretation = this.getStage3Interpretation();
        const finalLevel = this.calculateFinalLevel();
        
        const sbAvg = this.behavioralLevels["СБ"].length 
            ? Math.round(this.behavioralLevels["СБ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["СБ"].length) 
            : 3;
        const tfAvg = this.behavioralLevels["ТФ"].length 
            ? Math.round(this.behavioralLevels["ТФ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["ТФ"].length) 
            : 3;
        const ubAvg = this.behavioralLevels["УБ"].length 
            ? Math.round(this.behavioralLevels["УБ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["УБ"].length) 
            : 3;
        const chvAvg = this.behavioralLevels["ЧВ"].length 
            ? Math.round(this.behavioralLevels["ЧВ"].reduce((a, b) => a + b, 0) / this.behavioralLevels["ЧВ"].length) 
            : 3;
        
        const text = `✨ **РЕЗУЛЬТАТ ЭТАПА 3**\n\nВаши поведенческие уровни:\n• Реакция на давление (СБ): **${sbAvg}/6**\n• Отношение к деньгам (ТФ): **${tfAvg}/6**\n• Понимание мира (УБ): **${ubAvg}/6**\n• Отношения с людьми (ЧВ): **${chvAvg}/6**\n\nФинальный уровень: **${finalLevel}/9**\n\n${interpretation}\n\n▶️ **ЧТО ДАЛЬШЕ?**\n\n**Этап 4: ТОЧКА РОСТА**\n\nНайдем, где находится рычаг изменений.\n\n📊 **Вопросов:** 8\n⏱ **Время:** ~3 минуты`;
        
        this.addMessageWithButtons(text, [
            { text: "▶️ Перейти к этапу 4", callback: () => this.goToNextStage() }
        ]);
    },
    
    // ============================================
    // ЭКРАН 4: ПРЕДВАРИТЕЛЬНЫЙ ПРОФИЛЬ
    // ============================================
    showStage4Result() {
        const profile = this.calculateFinalProfile();
        const finalLevel = this.calculateFinalLevel();
        
        const sbDesc = {
            1: "Под давлением замираете",
            2: "Избегаете конфликтов",
            3: "Внешне соглашаетесь",
            4: "Внешне спокойны",
            5: "Умеете защищать",
            6: "Защищаете и используете силу"
        }[profile.sbLevel] || "Информация уточняется";
        
        const tfDesc = {
            1: "Деньги как повезёт",
            2: "Ищете возможности с нуля",
            3: "Зарабатываете трудом",
            4: "Хорошо зарабатываете",
            5: "Создаёте системы дохода",
            6: "Управляете капиталом"
        }[profile.tfLevel] || "Информация уточняется";
        
        const ubDesc = {
            1: "Не думаете о сложном",
            2: "Верите в знаки",
            3: "Доверяете экспертам",
            4: "Ищете заговоры",
            5: "Анализируете факты",
            6: "Строите теории"
        }[profile.ubLevel] || "Информация уточняется";
        
        const chvDesc = {
            1: "Сильно привязываетесь",
            2: "Подстраиваетесь",
            3: "Хотите нравиться",
            4: "Умеете влиять",
            5: "Строите равные отношения",
            6: "Создаёте сообщества"
        }[profile.chvLevel] || "Информация уточняется";
        
        const attentionDesc = profile.perceptionType.includes("СОЦИАЛЬНО") || profile.perceptionType.includes("СТАТУСНО")
            ? "Для вас важно, что думают другие, вы чутко считываете настроение и ожидания окружающих."
            : "Для вас важнее ваши внутренние ощущения и чувства, чем мнение других.";
        
        const thinkingDesc = profile.thinkingLevel <= 3 
            ? "Вы хорошо видите отдельные ситуации, но не всегда замечаете общие закономерности."
            : profile.thinkingLevel <= 6
            ? "Вы замечаете закономерности, но не всегда видите, к чему они приведут в будущем."
            : "Вы видите общие законы и можете предсказывать развитие ситуаций.";
        
        const growthMap = {
            "ENVIRONMENT": "Посмотрите вокруг — может, дело в обстоятельствах?",
            "BEHAVIOR": "Попробуйте делать хоть что-то по-другому — маленькие шаги многое меняют.",
            "CAPABILITIES": "Развивайте новые навыки — они откроют новые возможности.",
            "VALUES": "Поймите, что для вас действительно важно — это изменит всё.",
            "IDENTITY": "Ответьте себе на вопрос «кто я?» — в этом ключ к изменениям."
        };
        
        const confidence = 0.7;
        const confidenceBar = "█".repeat(Math.floor(confidence * 10)) + "░".repeat(10 - Math.floor(confidence * 10));
        
        const text = `🧠 **ПРЕДВАРИТЕЛЬНЫЙ ПОРТРЕТ**\n\n${attentionDesc}\n\n${thinkingDesc}\n\n📊 **ТВОИ ВЕКТОРЫ:**\n\n• **Реакция на давление (СБ ${profile.sbLevel}/6):** ${sbDesc}\n\n• **Отношение к деньгам (ТФ ${profile.tfLevel}/6):** ${tfDesc}\n\n• **Понимание мира (УБ ${profile.ubLevel}/6):** ${ubDesc}\n\n• **Отношения с людьми (ЧВ ${profile.chvLevel}/6):** ${chvDesc}\n\n🎯 **Точка роста:** ${growthMap[profile.dominantDilts] || "Начните с малого — и увидите, куда приведёт."}\n\n📊 **Уверенность:** ${confidenceBar} ${Math.floor(confidence * 100)}%\n\n👇 **ЭТО ПОХОЖЕ НА ВАС?**`;
        
        this.addMessageWithButtons(text, [
            { text: "✅ ДА", callback: () => this.profileConfirm() },
            { text: "❓ ЕСТЬ СОМНЕНИЯ", callback: () => this.profileDoubt() },
            { text: "🔄 НЕТ", callback: () => this.profileReject() }
        ]);
    },
    
    profileConfirm() {
        this.addBotMessage("✅ Отлично! Тогда исследуем глубину...");
        setTimeout(() => this.goToNextStage(), 1500);
    },
    
    profileDoubt() {
        const text = `🔍 **ДАВАЙ УТОЧНИМ**\n\nЧто именно вам не подходит?\n(можно выбрать несколько)\n\n🎭 Про людей — я не так сильно завишу от чужого мнения\n💰 Про деньги — у меня с ними по-другому\n🔍 Про знаки — я вполне себе анализирую\n🤝 Про отношения — я знаю, чего хочу\n🛡 Про давление — я реагирую иначе\n\n👇 Выберите и нажмите ДАЛЬШЕ`;
        
        this.addMessageWithButtons(text, [
            { text: "🎭 Про людей", callback: () => this.toggleDiscrepancy("people") },
            { text: "💰 Про деньги", callback: () => this.toggleDiscrepancy("money") },
            { text: "🔍 Про знаки", callback: () => this.toggleDiscrepancy("signs") },
            { text: "🤝 Про отношения", callback: () => this.toggleDiscrepancy("relations") },
            { text: "🛡 Про давление", callback: () => this.toggleDiscrepancy("sb") },
            { text: "➡️ ДАЛЬШЕ", callback: () => this.clarifyNext() }
        ]);
    },
    
    toggleDiscrepancy(type) {
        if (this.discrepancies.includes(type)) {
            this.discrepancies = this.discrepancies.filter(d => d !== type);
        } else {
            this.discrepancies.push(type);
        }
        this.saveProgress();
    },
    
    clarifyNext() {
        if (this.discrepancies.length === 0) {
            alert("Выберите хотя бы одно расхождение!");
            return;
        }
        
        // Упрощенные уточняющие вопросы
        const questions = [
            { text: "Расскажите подробнее, что именно не так с описанием?", options: ["Я спокойнее", "Я агрессивнее", "Я вообще не такой"] }
        ];
        
        this.clarifyingQuestions = questions;
        this.clarifyingCurrent = 0;
        this.askClarifyingQuestion();
    },
    
    askClarifyingQuestion() {
        if (this.clarifyingCurrent >= this.clarifyingQuestions.length) {
            this.updateProfileWithClarifications();
            return;
        }
        
        const q = this.clarifyingQuestions[this.clarifyingCurrent];
        const text = `🔍 **УТОЧНЯЮЩИЙ ВОПРОС ${this.clarifyingCurrent + 1}/${this.clarifyingQuestions.length}**\n\n${q.text}`;
        
        this.addMessageWithButtons(text, q.options.map((opt, i) => ({
            text: opt,
            callback: () => {
                this.clarifyingAnswers.push({ question: q.text, answer: opt });
                this.clarifyingCurrent++;
                this.askClarifyingQuestion();
            }
        })));
    },
    
    updateProfileWithClarifications() {
        this.clarificationIteration++;
        this.saveProgress();
        this.showStage4Result();
    },
    
    profileReject() {
        const anecdote = `🧠 **ЧЕСТНОСТЬ - ЛУЧШАЯ ПОЛИТИКА**\n\nДве подруги решили сходить на ипподром. Приходят, а там скачки, все ставки делают. Решили и они ставку сделать — вдруг повезёт? Одна другой и говорит: «Слушай, у тебя какой размер груди?». Вторая: «Второй… а у тебя?». Первая: «Третий… ну давай на пятую поставим — чтоб сумма была…».\n\nПоставили на пятую, лошадь приходит первая, они счастливые прибегают домой с деньгами и мужьям рассказывают, как было дело.\n\nНа следующий день мужики тоже решили сходить на скачки — а вдруг им повезёт? Когда решали, на какую ставить, один говорит: «Ты сколько раз за ночь свою жену можешь удовлетворить?». Другой говорит: «Ну, три…». Первый: «А я четыре… ну давай на седьмую поставим».\n\nПоставили на седьмую, первой пришла вторая.\n\nМужики переглянулись: «Не напиздили бы — выиграли…».\n\n**Мораль:** Если врать в тесте — результат будет как у мужиков на скачках. Хотите попробовать еще раз?`;
        
        this.addMessageWithButtons(anecdote, [
            { text: "🔄 ПРОЙТИ ТЕСТ ЕЩЕ РАЗ", callback: () => this.restartTest() },
            { text: "👋 ДОСВИДУЛИ", callback: () => this.goToChat() }
        ]);
        
        this.currentStage = 0;
        this.currentQuestionIndex = 0;
        this.answers = [];
        this.perceptionScores = { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 };
        this.perceptionType = null;
        this.thinkingLevel = null;
        this.thinkingScores = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0 };
        this.strategyLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.behavioralLevels = { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] };
        this.stage3Scores = [];
        this.diltsCounts = { "ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0 };
        this.deepAnswers = [];
        this.saveProgress();
    },
    
    restartTest() {
        this.start();
    },
    
    goToChat() {
        this.addBotMessage('👋 До свидания!\n\nБуду рад помочь, если решите вернуться.');
        setTimeout(() => {
            if (window.App && App.showMainChat) {
                App.showMainChat();
            }
        }, 2000);
    },
    
    // ============================================
    // ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ
    // ============================================
    showStage5Result() {
        const deep = this.deepPatterns || { attachment: "🤗 Надежный" };
        const interpretation = this.getStage5Interpretation();
        
        const text = `✨ **РЕЗУЛЬТАТ ЭТАПА 5**\n\n${interpretation}\n\n✅ **ТЕСТ ЗАВЕРШЕН!**\n\n🧠 Собираю воедино результаты 5 этапов...`;
        
        this.addBotMessage(text);
        this.sendTestResultsToServer();
    },
    
    // ============================================
    // ОТПРАВКА РЕЗУЛЬТАТОВ НА СЕРВЕР
    // ============================================
    async sendTestResultsToServer() {
        if (!this.userId) {
            console.warn('⚠️ Нет user_id, результаты сохранены локально');
            this.showFinalProfileButtons();
            return;
        }
        
        const profile = this.calculateFinalProfile();
        const deep = this.deepPatterns || { attachment: "🤗 Надежный" };
        
        const results = {
            user_id: parseInt(this.userId),
            results: {
                perception_type: this.perceptionType,
                thinking_level: this.thinkingLevel,
                behavioral_levels: this.behavioralLevels,
                dilts_counts: this.diltsCounts,
                deep_patterns: deep,
                profile_data: profile,
                all_answers: this.answers,
                test_completed: true,
                test_completed_at: new Date().toISOString()
            }
        };
        
        console.log('📤 Отправка результатов на сервер...', { userId: parseInt(this.userId) });
        
        try {
            const response = await fetch('/api/save-test-results', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(results)
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Результаты теста успешно отправлены на сервер');
            } else {
                console.error('❌ Ошибка при отправке:', data.error);
            }
        } catch (error) {
            console.error('❌ Ошибка сети:', error);
        }
        
        this.showFinalProfileButtons();
    },
    
    // ============================================
    // ФИНАЛЬНЫЙ ПРОФИЛЬ
    // ============================================
    showFinalProfileButtons() {
        const profile = this.calculateFinalProfile();
        const deep = this.deepPatterns || { attachment: "🤗 Надежный" };
        const finalLevel = this.calculateFinalLevel();
        
        const sbDesc = {
            1: "Под давлением замираете",
            2: "Избегаете конфликтов",
            3: "Внешне соглашаетесь",
            4: "Внешне спокойны",
            5: "Умеете защищать",
            6: "Защищаете и используете силу"
        }[profile.sbLevel] || "Информация уточняется";
        
        const tfDesc = {
            1: "Деньги как повезёт",
            2: "Ищете возможности с нуля",
            3: "Зарабатываете трудом",
            4: "Хорошо зарабатываете",
            5: "Создаёте системы дохода",
            6: "Управляете капиталом"
        }[profile.tfLevel] || "Информация уточняется";
        
        const ubDesc = {
            1: "Не думаете о сложном",
            2: "Верите в знаки",
            3: "Доверяете экспертам",
            4: "Ищете заговоры",
            5: "Анализируете факты",
            6: "Строите теории"
        }[profile.ubLevel] || "Информация уточняется";
        
        const chvDesc = {
            1: "Сильно привязываетесь",
            2: "Подстраиваетесь",
            3: "Хотите нравиться",
            4: "Умеете влиять",
            5: "Строите равные отношения",
            6: "Создаёте сообщества"
        }[profile.chvLevel] || "Информация уточняется";
        
        const text = `🧠 **ВАШ ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ**\n\n**Профиль:** ${profile.displayName}\n**Тип восприятия:** ${profile.perceptionType}\n**Уровень мышления:** ${profile.thinkingLevel}/9\n\n📊 **ТВОИ ВЕКТОРЫ:**\n\n• **Реакция на давление (СБ ${profile.sbLevel}/6):** ${sbDesc}\n\n• **Отношение к деньгам (ТФ ${profile.tfLevel}/6):** ${tfDesc}\n\n• **Понимание мира (УБ ${profile.ubLevel}/6):** ${ubDesc}\n\n• **Отношения с людьми (ЧВ ${profile.chvLevel}/6):** ${chvDesc}\n\n🧠 **Глубинный паттерн:** ${deep.attachment}\n\n👇 **Что дальше?**`;
        
        this.addMessageWithButtons(text, [
            { text: "🧠 МЫСЛИ ПСИХОЛОГА", callback: () => this.showPsychologistThought() },
            { text: "🎯 ВЫБРАТЬ ЦЕЛЬ", callback: () => this.showGoals() },
            { text: "⚙️ ВЫБРАТЬ РЕЖИМ", callback: () => this.showModes() }
        ]);
        
        if (this.userId) {
            localStorage.setItem(`test_results_${this.userId}`, JSON.stringify({
                profile,
                deepPatterns: deep,
                perceptionType: this.perceptionType,
                thinkingLevel: this.thinkingLevel
            }));
        }
    },
    
    goToNextStage() {
        this.currentStage++;
        this.currentQuestionIndex = 0;
        this.sendStageIntro();
    },
    
    showFinalProfile() {
        this.showFinalProfileButtons();
    },
    
    showPsychologistThought() {
        if (window.dashboard && window.dashboard.renderPsychologistThoughtScreen) {
            window.dashboard.renderPsychologistThoughtScreen();
        } else if (App && App.showPsychologistThought) {
            App.showPsychologistThought();
        } else {
            this.addBotMessage("🧠 Мысли психолога будут доступны в личном кабинете.");
        }
    },
    
    showGoals() {
        if (window.dashboard && window.dashboard.renderGoalsScreen) {
            window.dashboard.renderGoalsScreen();
        } else if (App && App.showDynamicDestinations) {
            App.showDynamicDestinations();
        } else {
            this.addBotMessage("🎯 Выбор целей будет доступен в личном кабинете.");
        }
    },
    
    showModes() {
        if (window.dashboard && window.dashboard.renderModeSelectionScreen) {
            window.dashboard.renderModeSelectionScreen();
        } else if (App && App.showModeSelection) {
            App.showModeSelection();
        } else {
            this.addBotMessage("⚙️ Выбор режима будет доступен в личном кабинете.");
        }
    }
};

// Глобальный экспорт
window.Test = Test;

console.log('✅ Модуль теста загружен (версия 2.0)');
