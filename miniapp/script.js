// ========== script.js ==========
// ГЛАВНЫЙ ФАЙЛ ЛОГИКИ МИНИ-ПРИЛОЖЕНИЯ
// Имитация мессенджера MAX с полной синхронизацией через API

// ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
const App = {
    // Данные пользователя
    userId: null,
    userName: 'Загрузка...',
    userData: {},
    userContext: {},
    
    // Состояние приложения
    currentScreen: 'chat', // chat, test, profile, modes, thoughts, weekend
    currentTestStage: 1,
    currentQuestionIndex: 0,
    testAnswers: {},
    
    // UI элементы
    elements: {},
    
    // Настройки
    apiBase: '/api', // относительный путь (работает через прокси MAX)
    isLoading: false,
    typingTimeout: null
};

// ===== ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ =====
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Фреди: инициализация мини-приложения');
    
    // Кэшируем DOM элементы
    cacheElements();
    
    // Получаем ID пользователя из MAX окружения
    await initUserId();
    
    // Загружаем данные пользователя
    await loadUserData();
    
    // Загружаем историю чата
    await loadChatHistory();
    
    // Настраиваем обработчики событий
    setupEventListeners();
    
    // Показываем приветственное сообщение если нужно
    if (App.userData.first_visit) {
        showWelcomeMessage();
    }
    
    // Запускаем периодическое обновление
    startPeriodicUpdates();
});

// ===== КЭШИРОВАНИЕ DOM ЭЛЕМЕНТОВ =====
function cacheElements() {
    App.elements = {
        // Основные панели
        chatsPanel: document.getElementById('chatsPanel'),
        chatPanel: document.getElementById('chatPanel'),
        profilePanel: document.getElementById('profilePanel'),
        modesPanel: document.getElementById('modesPanel'),
        
        // Список чатов
        chatsList: document.getElementById('chatsList'),
        chatFredi: document.getElementById('chatFredi'),
        chatSaved: document.getElementById('chatSaved'),
        chatThoughts: document.getElementById('chatThoughts'),
        chatWeekend: document.getElementById('chatWeekend'),
        chatPreview: document.getElementById('chatPreview'),
        chatTime: document.getElementById('chatTime'),
        
        // Шапка чата
        chatHeaderName: document.getElementById('chatHeaderName'),
        chatHeaderStatus: document.getElementById('chatHeaderStatus'),
        
        // Сообщения
        messagesList: document.getElementById('messagesList'),
        messagesEnd: document.getElementById('messagesEnd'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        
        // Кнопки
        mobileMenuBtn: document.getElementById('mobileMenuBtn'),
        modeBtn: document.getElementById('modeBtn'),
        profileBtn: document.getElementById('profileBtn'),
        menuBtn: document.getElementById('menuBtn'),
        attachBtn: document.getElementById('attachBtn'),
        voiceBtn: document.getElementById('voiceBtn'),
        
        // Панели
        inlineButtonsContainer: document.getElementById('inlineButtonsContainer'),
        inlineButtons: document.getElementById('inlineButtons'),
        testPanel: document.getElementById('testPanel'),
        inputPanel: document.getElementById('inputPanel'),
        
        // Профиль
        userAvatar: document.getElementById('userAvatar'),
        userName: document.getElementById('userName'),
        userStatus: document.getElementById('userStatus'),
        profileContent: document.getElementById('profileContent'),
        closeProfileBtn: document.getElementById('closeProfileBtn'),
        
        // Режимы
        modesContent: document.getElementById('modesContent'),
        closeModesBtn: document.getElementById('closeModesBtn'),
        
        // Поиск
        chatSearchInput: document.getElementById('chatSearchInput'),
        newChatBtn: document.getElementById('newChatBtn')
    };
}

// ===== ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ =====
async function initUserId() {
    try {
        // Пытаемся получить из MAX Bridge
        if (window.MAXBridge && window.MAXBridge.getUserId) {
            App.userId = await window.MAXBridge.getUserId();
            console.log('✅ Получен userId из MAX Bridge:', App.userId);
        }
        
        // Если не получилось, проверяем URL параметры
        if (!App.userId) {
            const urlParams = new URLSearchParams(window.location.search);
            App.userId = urlParams.get('user_id') || urlParams.get('userId');
            console.log('✅ Получен userId из URL:', App.userId);
        }
        
        // Если всё ещё нет, используем тестовый ID
        if (!App.userId) {
            App.userId = 'test_user_123';
            console.warn('⚠️ Используется тестовый userId:', App.userId);
        }
        
        // Сохраняем в localStorage для отладки
        localStorage.setItem('fredi_user_id', App.userId);
        
    } catch (error) {
        console.error('❌ Ошибка получения userId:', error);
        App.userId = 'test_user_123';
    }
}

// ===== ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ =====
async function loadUserData() {
    try {
        showLoading('userMiniProfile', 'Загрузка профиля...');
        
        // Загружаем базовую информацию
        const userInfo = await api.getUserData(App.userId);
        App.userName = userInfo.user_name || 'друг';
        App.userData = userInfo;
        
        // Обновляем UI
        updateUserInfo();
        
        // Загружаем прогресс теста
        const testProgress = await api.getTestProgress(App.userId);
        App.testProgress = testProgress;
        
        // Загружаем профиль если есть
        if (userInfo.has_profile) {
            const profile = await api.getProfile(App.userId);
            App.userProfile = profile.profile;
        }
        
        // Загружаем мысли психолога
        try {
            const thoughts = await api.getThoughts(App.userId);
            App.userThoughts = thoughts.thought;
        } catch (e) {
            console.log('Мысли ещё не сгенерированы');
        }
        
        console.log('✅ Данные пользователя загружены:', App.userName);
        
    } catch (error) {
        console.error('❌ Ошибка загрузки данных:', error);
        showError('Не удалось загрузить данные пользователя');
    }
}

// ===== ОБНОВЛЕНИЕ ИНФОРМАЦИИ О ПОЛЬЗОВАТЕЛЕ =====
function updateUserInfo() {
    if (App.elements.userName) {
        App.elements.userName.textContent = App.userName;
    }
    
    if (App.elements.userStatus) {
        const progress = App.testProgress || {};
        if (progress.stage5_complete) {
            App.elements.userStatus.textContent = '✅ тест пройден';
        } else if (progress.current_stage > 1) {
            App.elements.userStatus.textContent = `📊 этап ${progress.current_stage}/5`;
        } else {
            App.elements.userStatus.textContent = '🧠 ожидает тест';
        }
    }
    
    // Обновляем превью в чате
    if (App.elements.chatPreview) {
        if (App.testProgress?.stage5_complete) {
            App.elements.chatPreview.textContent = '✅ Тест пройден. Чем помочь?';
        } else {
            App.elements.chatPreview.textContent = '🧠 Пройдите тест из 5 этапов';
        }
    }
}

// ===== ЗАГРУЗКА ИСТОРИИ ЧАТА =====
async function loadChatHistory() {
    try {
        // Очищаем сообщения
        App.elements.messagesList.innerHTML = '';
        
        // Добавляем разделитель даты
        addDateDivider(getCurrentDateString());
        
        // Получаем историю с сервера
        const history = await api.getChatHistory(App.userId, 50);
        
        if (history && history.length > 0) {
            // Отображаем сохраненную историю
            history.forEach(msg => {
                if (msg.type === 'bot') {
                    addBotMessage(msg.text, msg.time, msg.buttons);
                } else {
                    addUserMessage(msg.text, msg.time);
                }
            });
        } else {
            // Показываем приветствие по умолчанию
            showDefaultWelcome();
        }
        
        // Прокручиваем вниз
        scrollToBottom();
        
    } catch (error) {
        console.error('❌ Ошибка загрузки истории:', error);
        showDefaultWelcome();
    }
}

// ===== ПРИВЕТСТВИЕ ПО УМОЛЧАНИЮ =====
function showDefaultWelcome() {
    const welcomeText = `Привет! Я Фреди, твой виртуальный психолог. 👋

Я помогу тебе разобраться в себе через тест из 5 этапов, исследовать глубинные паттерны и найти опоры.

**Что я умею:**
• 🧠 **5-этапное тестирование** - твой полный психологический портрет
• 💭 **Глубинный анализ вопросов** - отвечаю на любые темы
• 🎯 **Динамический подбор целей** - под твой профиль
• 🔍 **Проверка реальности** - помогаю увидеть паттерны
• 🎨 **Идеи на выходные** - под твой тип личности
• 🎭 **3 режима общения** - коуч, психолог, тренер

С чего начнём?`;
    
    addBotMessage(welcomeText, getCurrentTime(), [
        { text: '🧠 Пройти тест', action: 'start_test' },
        { text: '📊 Мой портрет', action: 'show_profile' },
        { text: '❓ Задать вопрос', action: 'ask_question' },
        { text: '🎭 Режим', action: 'show_modes' }
    ]);
}

// ===== ПОКАЗ ПРИВЕТСТВИЯ ДЛЯ НОВЫХ =====
function showWelcomeMessage() {
    addBotMessage(
        'Рад снова тебя видеть! 👋\n\nКак прошёл день? Есть что обсудить?',
        getCurrentTime(),
        [
            { text: '📊 Мой портрет', action: 'show_profile' },
            { text: '🧠 Мысли психолога', action: 'show_thoughts' },
            { text: '🎯 Идеи на выходные', action: 'show_weekend' }
        ]
    );
}

// ===== ДОБАВЛЕНИЕ СООБЩЕНИЯ БОТА =====
function addBotMessage(text, time, buttons = null) {
    const template = document.getElementById('botMessageTemplate');
    const clone = template.content.cloneNode(true);
    const messageDiv = clone.querySelector('.message');
    
    // Устанавливаем уникальный ID
    messageDiv.id = `msg-${Date.now()}-${Math.random()}`;
    
    // Заполняем текст (поддерживает markdown)
    const messageText = clone.querySelector('.message-text');
    messageText.innerHTML = formatMessageText(text);
    
    // Время
    clone.querySelector('.message-time').textContent = time || getCurrentTime();
    
    // Добавляем в контейнер
    App.elements.messagesList.appendChild(clone);
    
    // Если есть кнопки, добавляем их отдельным сообщением
    if (buttons && buttons.length > 0) {
        addInlineButtons(buttons);
    }
    
    // Прокручиваем к новому сообщению
    scrollToBottom();
    
    return messageDiv;
}

// ===== ДОБАВЛЕНИЕ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ =====
function addUserMessage(text, time) {
    const template = document.getElementById('userMessageTemplate');
    const clone = template.content.cloneNode(true);
    const messageDiv = clone.querySelector('.message');
    
    messageDiv.id = `msg-${Date.now()}`;
    clone.querySelector('.message-text').textContent = text;
    clone.querySelector('.message-time').textContent = time || getCurrentTime();
    
    App.elements.messagesList.appendChild(clone);
    scrollToBottom();
    
    return messageDiv;
}

// ===== ДОБАВЛЕНИЕ СООБЩЕНИЯ С МЫСЛЯМИ =====
function addThoughtMessage(text, time) {
    const template = document.getElementById('thoughtMessageTemplate');
    const clone = template.content.cloneNode(true);
    
    clone.querySelector('.message-text').innerHTML = formatMessageText(text);
    clone.querySelector('.message-time').textContent = time || getCurrentTime();
    
    App.elements.messagesList.appendChild(clone);
    scrollToBottom();
}

// ===== ДОБАВЛЕНИЕ ИНЛАЙН-КНОПОК =====
function addInlineButtons(buttons) {
    App.elements.inlineButtons.innerHTML = '';
    App.elements.inlineButtonsContainer.style.display = 'block';
    
    buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = `inline-button ${btn.secondary ? 'secondary' : ''}`;
        button.textContent = btn.text;
        button.setAttribute('data-action', btn.action);
        button.setAttribute('data-data', JSON.stringify(btn.data || {}));
        
        button.addEventListener('click', () => handleButtonClick(btn.action, btn.data));
        
        App.elements.inlineButtons.appendChild(button);
    });
}

// ===== ДОБАВЛЕНИЕ РАЗДЕЛИТЕЛЯ ДАТЫ =====
function addDateDivider(date) {
    const template = document.getElementById('dateDividerTemplate');
    const clone = template.content.cloneNode(true);
    
    clone.querySelector('span').textContent = date;
    App.elements.messagesList.appendChild(clone);
}

// ===== ФОРМАТИРОВАНИЕ ТЕКСТА (MARKDOWN) =====
function formatMessageText(text) {
    if (!text) return '';
    
    // Жирный текст: **текст**
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Курсив: *текст*
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Код: `текст`
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Списки: • или -
    text = text.replace(/^[•\-] (.*?)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*?<\/li>)\n(?!<li>)/gs, '<ul>$1</ul>');
    
    // Переносы строк
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// ===== ОБРАБОТКА НАЖАТИЯ КНОПОК =====
async function handleButtonClick(action, data = {}) {
    console.log('👆 Нажата кнопка:', action, data);
    
    switch (action) {
        case 'start_test':
            startTest();
            break;
            
        case 'show_profile':
            showProfilePanel();
            break;
            
        case 'show_modes':
            showModesPanel();
            break;
            
        case 'show_thoughts':
            showThoughts();
            break;
            
        case 'show_weekend':
            showWeekendIdeas();
            break;
            
        case 'ask_question':
            showQuestionInput();
            break;
            
        case 'next_question':
            nextTestQuestion();
            break;
            
        case 'prev_question':
            prevTestQuestion();
            break;
            
        case 'select_option':
            selectTestOption(data.optionIndex);
            break;
            
        case 'complete_stage':
            completeTestStage(data.stage);
            break;
            
        default:
            console.warn('Неизвестное действие:', action);
    }
}

// ===== НАЧАЛО ТЕСТИРОВАНИЯ =====
async function startTest() {
    console.log('📝 Начинаем тестирование');
    
    App.currentScreen = 'test';
    App.currentTestStage = 1;
    App.currentQuestionIndex = 0;
    
    // Скрываем панель ввода, показываем панель теста
    App.elements.inputPanel.style.display = 'none';
    App.elements.testPanel.style.display = 'block';
    App.elements.inlineButtonsContainer.style.display = 'none';
    
    // Загружаем первый вопрос
    await loadTestQuestion(1, 0);
}

// ===== ЗАГРУЗКА ВОПРОСА ТЕСТА =====
async function loadTestQuestion(stage, index) {
    try {
        // Показываем загрузку
        App.elements.testPanel.innerHTML = '<div class="loading">Загрузка вопроса...</div>';
        
        // Получаем вопрос с сервера
        const question = await api.getTestQuestion(App.userId, stage, index);
        
        // Рендерим вопрос
        renderTestQuestion(question);
        
    } catch (error) {
        console.error('❌ Ошибка загрузки вопроса:', error);
        App.elements.testPanel.innerHTML = '<div class="error-message">Не удалось загрузить вопрос</div>';
    }
}

// ===== ОТОБРАЖЕНИЕ ВОПРОСА ТЕСТА =====
function renderTestQuestion(question) {
    const template = document.getElementById('testQuestionTemplate');
    const clone = template.content.cloneNode(true);
    
    // Заполняем заголовок
    clone.querySelector('#testStageBadge').textContent = `Этап ${question.stage}/5`;
    clone.querySelector('#testQuestionCounter').textContent = `Вопрос ${question.index + 1}/${question.total}`;
    
    // Текст вопроса
    clone.querySelector('#testQuestionText').innerHTML = formatMessageText(question.text);
    
    // Варианты ответов
    const optionsList = clone.querySelector('#testOptionsList');
    question.options.forEach((opt, idx) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'test-option';
        optionDiv.setAttribute('data-option-idx', idx);
        optionDiv.setAttribute('data-option-value', opt.value || opt.id);
        
        optionDiv.innerHTML = `
            <div class="test-option-letter">${String.fromCharCode(65 + idx)}</div>
            <div class="test-option-text">${opt.text}</div>
        `;
        
        optionDiv.addEventListener('click', () => selectTestOption(idx));
        optionsList.appendChild(optionDiv);
    });
    
    // Навигация
    const prevBtn = clone.querySelector('#testPrevBtn');
    const nextBtn = clone.querySelector('#testNextBtn');
    
    prevBtn.disabled = question.index === 0;
    nextBtn.disabled = !question.hasAnswer;
    
    prevBtn.addEventListener('click', prevTestQuestion);
    nextBtn.addEventListener('click', nextTestQuestion);
    
    // Очищаем и вставляем
    App.elements.testPanel.innerHTML = '';
    App.elements.testPanel.appendChild(clone);
}

// ===== ВЫБОР ВАРИАНТА ОТВЕТА =====
async function selectTestOption(optionIndex) {
    // Подсвечиваем выбранный вариант
    document.querySelectorAll('.test-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    document.querySelectorAll('.test-option')[optionIndex].classList.add('selected');
    
    // Активируем кнопку "Далее"
    document.getElementById('testNextBtn').disabled = false;
    
    // Сохраняем ответ
    const answer = {
        stage: App.currentTestStage,
        questionIndex: App.currentQuestionIndex,
        option: optionIndex
    };
    
    try {
        // Отправляем на сервер
        const result = await api.submitTestAnswer(App.userId, answer);
        
        // Сохраняем локально
        if (!App.testAnswers[App.currentTestStage]) {
            App.testAnswers[App.currentTestStage] = [];
        }
        App.testAnswers[App.currentTestStage][App.currentQuestionIndex] = answer;
        
        // Если этап завершен, показываем сообщение
        if (result.stageComplete) {
            setTimeout(() => completeTestStage(App.currentTestStage), 500);
        }
        
    } catch (error) {
        console.error('❌ Ошибка сохранения ответа:', error);
    }
}

// ===== СЛЕДУЮЩИЙ ВОПРОС =====
async function nextTestQuestion() {
    const totalQuestions = getTotalQuestionsForStage(App.currentTestStage);
    
    if (App.currentQuestionIndex < totalQuestions - 1) {
        App.currentQuestionIndex++;
        await loadTestQuestion(App.currentTestStage, App.currentQuestionIndex);
    } else {
        // Переход к следующему этапу
        if (App.currentTestStage < 5) {
            App.currentTestStage++;
            App.currentQuestionIndex = 0;
            await loadTestQuestion(App.currentTestStage, 0);
        } else {
            // Тест завершен
            completeTest();
        }
    }
}

// ===== ПРЕДЫДУЩИЙ ВОПРОС =====
async function prevTestQuestion() {
    if (App.currentQuestionIndex > 0) {
        App.currentQuestionIndex--;
        await loadTestQuestion(App.currentTestStage, App.currentQuestionIndex);
    }
}

// ===== ЗАВЕРШЕНИЕ ЭТАПА ТЕСТА =====
async function completeTestStage(stage) {
    // Показываем сообщение о завершении этапа
    addBotMessage(
        `✅ **Этап ${stage} завершен!**\n\nПерехожу к следующему этапу...`,
        getCurrentTime()
    );
    
    // Обновляем прогресс
    if (stage === 1) {
        App.testProgress.stage1_complete = true;
        App.testProgress.current_stage = 2;
    } else if (stage === 2) {
        App.testProgress.stage2_complete = true;
        App.testProgress.current_stage = 3;
    } else if (stage === 3) {
        App.testProgress.stage3_complete = true;
        App.testProgress.current_stage = 4;
    } else if (stage === 4) {
        App.testProgress.stage4_complete = true;
        App.testProgress.current_stage = 5;
    }
    
    updateUserInfo();
}

// ===== ЗАВЕРШЕНИЕ ТЕСТА =====
async function completeTest() {
    App.testProgress.stage5_complete = true;
    App.currentScreen = 'chat';
    
    // Возвращаем обычный интерфейс
    App.elements.testPanel.style.display = 'none';
    App.elements.inputPanel.style.display = 'flex';
    
    // Показываем результаты
    const profile = await api.getProfile(App.userId);
    
    addBotMessage(
        `🎉 **Поздравляю! Тест завершен!**\n\n` +
        `Я составил твой психологический портрет. Посмотреть можно в профиле.\n\n` +
        `**Что дальше?**\n` +
        `• 📊 Изучи свой портрет\n` +
        `• 🧠 Спроси совет (я буду отвечать с учётом твоего профиля)\n` +
        `• 🎯 Поставь цели\n` +
        `• 🎨 Получи идеи на выходные`,
        getCurrentTime(),
        [
            { text: '📊 Мой портрет', action: 'show_profile' },
            { text: '🧠 Мысли психолога', action: 'show_thoughts' },
            { text: '🎯 Идеи на выходные', action: 'show_weekend' }
        ]
    );
    
    updateUserInfo();
}

// ===== ПОКАЗ ПАНЕЛИ ПРОФИЛЯ =====
async function showProfilePanel() {
    App.elements.profilePanel.style.display = 'flex';
    App.elements.profileContent.innerHTML = '<div class="profile-loading">Загрузка профиля...</div>';
    
    try {
        const profile = await api.getProfile(App.userId);
        const thought = await api.getThoughts(App.userId);
        
        renderProfile(profile.profile, thought.thought);
        
    } catch (error) {
        console.error('❌ Ошибка загрузки профиля:', error);
        App.elements.profileContent.innerHTML = '<div class="error-message">Не удалось загрузить профиль</div>';
    }
}

// ===== ОТОБРАЖЕНИЕ ПРОФИЛЯ =====
function renderProfile(profileText, thoughtText) {
    let html = '';
    
    if (profileText) {
        html += `
            <div class="profile-section">
                <div class="profile-section-title">🧠 Психологический портрет</div>
                <div class="profile-text">${formatMessageText(profileText)}</div>
            </div>
        `;
    }
    
    if (thoughtText) {
        html += `
            <div class="profile-section">
                <div class="profile-section-title">💭 Мысли психолога</div>
                <div class="profile-text thought-text">${formatMessageText(thoughtText)}</div>
            </div>
        `;
    }
    
    if (!profileText && !thoughtText) {
        html = '<div class="profile-section">Профиль ещё не сформирован. Пройдите тест.</div>';
    }
    
    App.elements.profileContent.innerHTML = html;
}

// ===== ПОКАЗ ПАНЕЛИ РЕЖИМОВ =====
function showModesPanel() {
    App.elements.modesPanel.style.display = 'flex';
    
    // Подсвечиваем текущий режим
    const currentMode = App.userContext?.communication_mode || 'coach';
    document.querySelectorAll('.mode-card').forEach(card => {
        if (card.dataset.mode === currentMode) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
}

// ===== ПОКАЗ МЫСЛЕЙ ПСИХОЛОГА =====
async function showThoughts() {
    try {
        const thought = await api.getThoughts(App.userId);
        addThoughtMessage(thought.thought);
    } catch (error) {
        console.error('❌ Ошибка загрузки мыслей:', error);
        addBotMessage('😔 Не удалось загрузить мысли психолога. Попробуй позже.');
    }
}

// ===== ПОКАЗ ИДЕЙ НА ВЫХОДНЫЕ =====
async function showWeekendIdeas() {
    addBotMessage('🎨 Генерирую идеи специально для тебя... Это займёт несколько секунд.', getCurrentTime());
    
    try {
        const ideas = await api.getWeekendIdeas(App.userId);
        
        let ideasText = '🎯 **Идеи на выходные**\n\n';
        ideas.ideas.forEach((idea, idx) => {
            ideasText += `${idx + 1}. **${idea.title}**\n${idea.description}\n\n`;
        });
        
        addBotMessage(ideasText, getCurrentTime(), [
            { text: '🔄 Другие идеи', action: 'show_weekend' },
            { text: '📊 В профиль', action: 'show_profile' }
        ]);
        
    } catch (error) {
        console.error('❌ Ошибка загрузки идей:', error);
        addBotMessage('😔 Не удалось сгенерировать идеи. Попробуй позже.');
    }
}

// ===== ПОКАЗ ПОЛЯ ДЛЯ ВОПРОСА =====
function showQuestionInput() {
    App.elements.messageInput.focus();
    App.elements.messageInput.placeholder = 'Задайте вопрос...';
}

// ===== ОТПРАВКА СООБЩЕНИЯ =====
async function sendMessage() {
    const input = App.elements.messageInput;
    const text = input.value.trim();
    
    if (!text) return;
    
    // Очищаем поле
    input.value = '';
    
    // Показываем сообщение пользователя
    addUserMessage(text);
    
    // Показываем индикатор печати
    showTypingIndicator();
    
    try {
        // Отправляем на сервер
        const response = await api.sendChatMessage(App.userId, text, App.userContext?.communication_mode);
        
        // Убираем индикатор
        hideTypingIndicator();
        
        // Показываем ответ бота
        if (response.response) {
            addBotMessage(response.response, getCurrentTime(), response.buttons);
        }
        
        // Если есть анализ вопроса, показываем
        if (response.analysis) {
            console.log('Анализ вопроса:', response.analysis);
        }
        
    } catch (error) {
        console.error('❌ Ошибка отправки сообщения:', error);
        hideTypingIndicator();
        addBotMessage('😔 Произошла ошибка. Попробуйте еще раз.');
    }
}

// ===== ПОКАЗ ИНДИКАТОРА ПЕЧАТИ =====
function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    
    App.elements.messagesList.appendChild(indicator);
    scrollToBottom();
}

// ===== СКРЫТИЕ ИНДИКАТОРА ПЕЧАТИ =====
function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// ===== ПРОКРУТКА ВНИЗ =====
function scrollToBottom() {
    setTimeout(() => {
        if (App.elements.messagesEnd) {
            App.elements.messagesEnd.scrollIntoView({ behavior: 'smooth' });
        }
    }, 50);
}

// ===== ПОЛУЧЕНИЕ ТЕКУЩЕГО ВРЕМЕНИ =====
function getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

// ===== ПОЛУЧЕНИЕ ТЕКУЩЕЙ ДАТЫ =====
function getCurrentDateString() {
    const now = new Date();
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                   'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
}

// ===== КОЛИЧЕСТВО ВОПРОСОВ ДЛЯ ЭТАПА =====
function getTotalQuestionsForStage(stage) {
    const counts = {
        1: 4,  // Тип восприятия
        2: 6,  // Уровень мышления
        3: 24, // Поведенческие уровни (4 вектора × 6)
        4: 12, // Уровни Дилтса
        5: 8   // Глубинные паттерны
    };
    return counts[stage] || 4;
}

// ===== ПОКАЗ ЗАГРУЗКИ =====
function showLoading(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="loading">${message}</div>`;
    }
}

// ===== ПОКАЗ ОШИБКИ =====
function showError(message) {
    console.error('❌', message);
    
    // Показываем в чате
    addBotMessage(`⚠️ ${message}`, getCurrentTime());
}

// ===== НАСТРОЙКА ОБРАБОТЧИКОВ СОБЫТИЙ =====
function setupEventListeners() {
    // Отправка сообщения
    App.elements.sendBtn.addEventListener('click', sendMessage);
    App.elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Кнопки в шапке
    App.elements.modeBtn.addEventListener('click', showModesPanel);
    App.elements.profileBtn.addEventListener('click', showProfilePanel);
    
    // Закрытие панелей
    App.elements.closeProfileBtn.addEventListener('click', () => {
        App.elements.profilePanel.style.display = 'none';
    });
    
    App.elements.closeModesBtn.addEventListener('click', () => {
        App.elements.modesPanel.style.display = 'none';
    });
    
    // Выбор режима
    document.querySelectorAll('.mode-card').forEach(card => {
        card.addEventListener('click', async () => {
            const mode = card.dataset.mode;
            await api.setMode(App.userId, mode);
            
            // Обновляем UI
            App.userContext.communication_mode = mode;
            document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            
            // Показываем сообщение
            addBotMessage(`🎭 Режим изменен на **${card.querySelector('.mode-name').textContent}**`, getCurrentTime());
            
            // Закрываем панель
            App.elements.modesPanel.style.display = 'none';
        });
    });
    
    // Переключение чатов
    App.elements.chatFredi.addEventListener('click', () => {
        document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));
        App.elements.chatFredi.classList.add('active');
        App.elements.chatHeaderName.textContent = 'Фреди';
        App.elements.chatHeaderStatus.textContent = '🧠 психолог · онлайн';
    });
    
    App.elements.chatSaved.addEventListener('click', () => {
        document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));
        App.elements.chatSaved.classList.add('active');
        App.elements.chatHeaderName.textContent = 'Сохранённые';
        App.elements.chatHeaderStatus.textContent = 'заметки и профиль';
        showProfilePanel();
    });
    
    App.elements.chatThoughts.addEventListener('click', () => {
        document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));
        App.elements.chatThoughts.classList.add('active');
        App.elements.chatHeaderName.textContent = 'Мысли психолога';
        App.elements.chatHeaderStatus.textContent = 'глубинные инсайты';
        showThoughts();
    });
    
    App.elements.chatWeekend.addEventListener('click', () => {
        document.querySelectorAll('.chat-item').forEach(c => c.classList.remove('active'));
        App.elements.chatWeekend.classList.add('active');
        App.elements.chatHeaderName.textContent = 'Идеи на выходные';
        App.elements.chatHeaderStatus.textContent = 'подборка активностей';
        showWeekendIdeas();
    });
    
    // Мобильное меню
    App.elements.mobileMenuBtn.addEventListener('click', () => {
        App.elements.chatsPanel.classList.toggle('visible');
    });
    
    // Поиск
    App.elements.chatSearchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.chat-item').forEach(item => {
            const name = item.querySelector('.chat-name')?.textContent.toLowerCase() || '';
            if (name.includes(query) || query === '') {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    });
    
    // Голосовое сообщение
    App.elements.voiceBtn.addEventListener('click', () => {
        addBotMessage('🎤 Голосовые сообщения будут доступны в следующей версии', getCurrentTime());
    });
    
    // Прикрепление файлов
    App.elements.attachBtn.addEventListener('click', () => {
        addBotMessage('📎 Прикрепление файлов будет доступно позже', getCurrentTime());
    });
    
    // Нажатие на профиль в левой панели
    document.querySelector('.user-mini-profile').addEventListener('click', showProfilePanel);
}

// ===== ПЕРИОДИЧЕСКОЕ ОБНОВЛЕНИЕ =====
function startPeriodicUpdates() {
    // Обновляем статус каждые 30 секунд
    setInterval(async () => {
        try {
            const progress = await api.getTestProgress(App.userId);
            App.testProgress = progress;
            updateUserInfo();
        } catch (e) {
            console.log('Ошибка обновления прогресса');
        }
    }, 30000);
}

// ===== ОБРАБОТКА ОШИБОК ГЛОБАЛЬНО =====
window.addEventListener('error', (event) => {
    console.error('❌ Глобальная ошибка:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('❌ Unhandled Promise Rejection:', event.reason);
});

// Экспортируем глобально для доступа из других скриптов
window.App = App;
window.api = api; // будет определен в api.js
