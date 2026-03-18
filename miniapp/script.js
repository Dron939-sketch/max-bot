// ============================================
// script.js - ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ
// Все тексты взяты из Telegram-бота
// ИСПРАВЛЕНО: подстановка имени, рабочая кнопка
// ============================================

// ============================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
// ============================================

let app = {
    userId: null,
    currentScreen: 'welcome',
    userData: {},
    hasProfile: false,
    selectedMode: null,
    messages: []
};

// ============================================
// ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ
// ============================================

function getUserId() {
    // 1. Из URL параметров
    const urlParams = new URLSearchParams(window.location.search);
    const urlUserId = urlParams.get('user_id');
    
    if (urlUserId) {
        console.log('✅ User ID из URL:', urlUserId);
        return urlUserId;
    }
    
    // 2. Из MAX WebApp
    try {
        if (window.WebApp?.initDataUnsafe?.user?.id) {
            const maxId = window.WebApp.initDataUnsafe.user.id;
            console.log('✅ User ID из MAX WebApp:', maxId);
            return maxId;
        }
    } catch (e) {}
    
    // 3. Тестовый ID
    console.log('⚠️ Использую тестовый ID: 213102077');
    return '213102077';
}

// ============================================
// ПРИВЕТСТВИЕ ПО ВРЕМЕНИ СУТОК
// ============================================

function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour < 6) return "Доброй ночи";
    if (hour < 12) return "Доброе утро";
    if (hour < 18) return "Добрый день";
    return "Добрый вечер";
}

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 ФРЕДИ: Мини-приложение запущено');
    
    // Получаем ID пользователя
    app.userId = getUserId();
    
    // Показываем загрузку
    showLoading();
    
    // Загружаем данные
    await loadUserData();
    
    // Настраиваем кнопку назад
    setupBackButton();
});

// ============================================
// ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ
// ============================================

async function loadUserData() {
    try {
        const response = await fetch(`/api/user-data?user_id=${app.userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки');
        
        app.userData = await response.json();
        app.hasProfile = app.userData.has_profile || false;
        
        // Показываем соответствующий экран
        if (app.hasProfile) {
            // У пользователя есть профиль - показываем главное меню
            showScreen('main');
            // Показываем навигацию
            document.getElementById('navBar').style.display = 'flex';
        } else {
            // Новый пользователь - показываем приветствие
            showScreen('welcome');
            // Скрываем навигацию
            document.getElementById('navBar').style.display = 'none';
        }
        
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        showError('Не удалось загрузить данные пользователя');
    }
}

// ============================================
// НАСТРОЙКА КНОПКИ НАЗАД
// ============================================

function setupBackButton() {
    const backBtn = document.getElementById('backBtn');
    backBtn.addEventListener('click', () => {
        if (app.currentScreen === 'welcome' || app.currentScreen === 'main') {
            // На главной - закрываем приложение
            if (window.WebApp?.close) window.WebApp.close();
        } else if (app.currentScreen === 'why') {
            // С экрана "А ты кто" возвращаемся к приветствию
            showScreen('welcome');
        } else if (app.currentScreen === 'mode') {
            // С выбора режима возвращаемся к главному меню
            showScreen('main');
        } else if (app.currentScreen === 'stage1') {
            // С этапа 1 возвращаемся к приветствию
            showScreen('welcome');
        } else {
            // По умолчанию - на главную
            showScreen('main');
        }
    });
}

// ============================================
// ПОКАЗ ЭКРАНОВ
// ============================================

function showScreen(screen) {
    app.currentScreen = screen;
    
    // Обновляем заголовок
    const headerTitle = document.getElementById('header-title');
    const titles = {
        'welcome': '👋 ФРЕДИ',
        'why': '🧐 ФРЕДИ',
        'main': '🏠 ФРЕДИ',
        'mode': '🔮 ФРЕДИ',
        'stage1': '🧠 ЭТАП 1',
        'profile': '📊 ПОРТРЕТ',
        'thought': '🧠 МЫСЛИ',
        'goals': '🎯 ЦЕЛИ',
        'ask': '❓ ВОПРОС'
    };
    headerTitle.textContent = titles[screen] || '🧠 ФРЕДИ';
    
    // Показываем/скрываем кнопку назад
    const backBtn = document.getElementById('backBtn');
    backBtn.style.display = (screen === 'welcome' || screen === 'main') ? 'none' : 'flex';
    
    // Загружаем контент
    const content = document.getElementById('content');
    content.classList.add('fade-out');
    
    setTimeout(() => {
        switch(screen) {
            case 'welcome':
                renderWelcomeScreen(content);
                break;
            case 'why':
                renderWhyScreen(content);
                break;
            case 'main':
                renderMainScreen(content);
                break;
            case 'mode':
                renderModeScreen(content);
                break;
            case 'stage1':
                renderStage1Screen(content);
                break;
            case 'profile':
                renderProfileScreen(content);
                break;
            case 'thought':
                renderThoughtScreen(content);
                break;
            case 'goals':
                renderGoalsScreen(content);
                break;
            case 'ask':
                renderAskScreen(content);
                break;
        }
        
        content.classList.remove('fade-out');
        content.classList.add('fade-in');
        setTimeout(() => content.classList.remove('fade-in'), 300);
    }, 300);
}

// ============================================
// ЭКРАН ПРИВЕТСТВИЯ (ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ)
// ============================================

function renderWelcomeScreen(container) {
    // ✅ Берем имя из данных пользователя
    const userName = app.userData.user_name || 'Андрей';
    
    const html = `
        <div class="welcome-screen">
            <div class="welcome-text">
                <p><strong>${userName}, привет! Ну, здравствуйте, дорогой человек! 👋</strong></p>
                
                <p>🧠 <strong>Я — Фреди, виртуальный психолог.</strong><br>
                Оцифрованная версия Андрея Мейстера, если хотите — его цифровой слепок.</p>
                
                <p>🎭 Короче, я — это он, только батарейка дольше держит и пожрать не прошу.</p>
                
                <p>🕒 Нам нужно познакомиться, потому что я пока не экстрасенс.</p>
                
                <p>🧐 Чтобы я понимал, с кем имею дело и чем могу быть полезен —<br>
                давайте-ка пройдём небольшой тест.</p>
                
                <p>📊 <strong>Всего 5 этапов:</strong></p>
            </div>
            
            <div class="stages-list">
                <div class="stage-item">
                    <span class="stage-number">1️⃣</span>
                    <span class="stage-text">Конфигурация восприятия — как вы фильтруете реальность</span>
                </div>
                <div class="stage-item">
                    <span class="stage-number">2️⃣</span>
                    <span class="stage-text">Конфигурация мышления — как ваш мозг перерабатывает информацию</span>
                </div>
                <div class="stage-item">
                    <span class="stage-number">3️⃣</span>
                    <span class="stage-text">Конфигурация поведения — что вы делаете на автопилоте</span>
                </div>
                <div class="stage-item">
                    <span class="stage-number">4️⃣</span>
                    <span class="stage-text">Точка роста — куда двигаться, чтобы не топтаться на месте</span>
                </div>
                <div class="stage-item">
                    <span class="stage-number">5️⃣</span>
                    <span class="stage-text">Глубинные паттерны — что сформировало вас как личность</span>
                </div>
            </div>
            
            <div class="welcome-text">
                <p>⏱ <strong>15 минут</strong> — и я буду знать о вас больше, чем вы думаете.</p>
                
                <p>🚀 <strong>Ну что, начнём наше знакомство?</strong></p>
            </div>
            
            <div class="action-buttons">
                <button class="action-btn primary" onclick="startTest()">
                    🚀 ДАВАЙ, ПОГНАЛИ!
                </button>
                <button class="action-btn secondary" onclick="showScreen('why')">
                    🤨 А ТЫ ВООБЩЕ КТО?
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН "А ТЫ ВООБЩЕ КТО?"
// ============================================

function renderWhyScreen(container) {
    const html = `
        <div class="why-screen">
            <div class="why-text">
                <p>🎭 <strong>Ну, вопрос хороший. Давайте по существу.</strong></p>
                
                <p>Видите ли, дорогой человек, я — экспериментальная модель.<br>
                Андрей Мейстер однажды подумал: "А что, если я создам свою цифровую копию?<br>
                Пусть работает, пока я сплю, ем или просто ленюсь".</p>
                
                <p>Так я и появился. 🧠</p>
                
                <p>🧐 <strong>Что я умею:</strong></p>
                
                <ul class="why-list">
                    <li>Вижу паттерны там, где вы видите просто день сурка</li>
                    <li>Нахожу систему в ваших "случайных" решениях</li>
                    <li>Понимаю, почему вы выбираете одних и тех же "не тех" людей</li>
                    <li>Я реально беспристрастен — у меня нет плохого настроения</li>
                </ul>
                
                <p>🎯 <strong>Конкретно по тесту:</strong></p>
                
                <ul class="why-list">
                    <li>1️⃣ Восприятие — поймём, какую линзу вы носите</li>
                    <li>2️⃣ Мышление — узнаем, как вы пережёвываете реальность</li>
                    <li>3️⃣ Поведение — посмотрим, что вы делаете "на автомате"</li>
                    <li>4️⃣ Точка роста — я скажу, куда вам двигаться</li>
                    <li>5️⃣ Глубинные паттерны — заглянем в детство и подсознание</li>
                </ul>
                
                <p>⏱ <strong>15 минут</strong> — и я составлю ваш профиль.</p>
                
                <p>👌 Погнали?</p>
            </div>
            
            <div class="action-buttons">
                <button class="action-btn primary" onclick="startTest()">
                    🚀 ПОГНАЛИ!
                </button>
                <button class="action-btn secondary" onclick="showScreen('welcome')">
                    ◀️ НАЗАД
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЭТАПА 1 (ПОСЛЕ НАЖАТИЯ "ДАВАЙ, ПОГНАЛИ!")
// ============================================

function renderStage1Screen(container) {
    const html = `
        <div class="welcome-screen">
            <div class="welcome-text">
                <p>🧠 <strong>ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</strong></p>
                
                <p>Восприятие — это линза, через которую вы смотрите на мир.</p>
                
                <p>🔍 <strong>Что мы исследуем:</strong><br>
                • Куда направлено ваше внимание — вовне или внутрь<br>
                • Какая тревога доминирует — страх отвержения или страх потери контроля</p>
                
                <p>📊 <strong>Вопросов:</strong> 8<br>
                ⏱ <strong>Время:</strong> ~3 минуты</p>
                
                <p>Отвечайте честно — это поможет мне лучше понять вас.</p>
            </div>
            
            <div class="action-buttons">
                <button class="action-btn primary" onclick="startStage1()">
                    ▶️ НАЧАТЬ ИССЛЕДОВАНИЕ
                </button>
                <button class="action-btn secondary" onclick="showScreen('welcome')">
                    ◀️ НАЗАД
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ГЛАВНЫЙ ЭКРАН (ДЛЯ ПОЛЬЗОВАТЕЛЕЙ С ПРОФИЛЕМ)
// ============================================

function renderMainScreen(container) {
    const greeting = getTimeGreeting();
    const userName = app.userData.user_name || 'друг';
    
    // Погода (заглушка)
    const weatherEmoji = '☁️';
    const weatherDesc = 'пасмурно';
    const weatherTemp = '+5°C';
    
    // Определяем контекст по времени
    const hour = new Date().getHours();
    let contextMessage = '';
    if (hour >= 9 && hour < 18) {
        contextMessage = '💼 Рабочее время. Чем займёмся?';
    } else if (hour >= 18 || hour < 6) {
        contextMessage = '🏡 Личное время. Есть что обсудить?';
    } else {
        contextMessage = '🌙 Ночное время. Что тревожит?';
    }
    
    // Проверяем выходной
    const day = new Date().getDay();
    if (day === 0 || day === 6) {
        contextMessage = '🏖 Сегодня выходной! Как настроение?';
    }
    
    const html = `
        <div class="welcome-screen">
            <div class="greeting">👋 ${greeting}, ${userName}!</div>
            
            <div class="weather">
                <span>${weatherEmoji}</span>
                <span>${weatherDesc}, ${weatherTemp}</span>
            </div>
            
            <div class="context-message">
                ${contextMessage}
            </div>
            
            <div class="mode-buttons">
                <div class="mode-row">
                    <button class="mode-btn hard" onclick="selectMode('hard')">
                        🔴 ЖЕСТКИЙ
                    </button>
                    <button class="mode-btn medium" onclick="selectMode('medium')">
                        🟡 СРЕДНИЙ
                    </button>
                </div>
                <div class="mode-row">
                    <button class="mode-btn soft" onclick="selectMode('soft')">
                        🟢 МЯГКИЙ
                    </button>
                </div>
            </div>
            
            <div class="menu-buttons">
                <button class="menu-btn" onclick="showBenefits()">
                    📖 ЧТО ДАЕТ ТЕСТ
                </button>
                <button class="menu-btn" onclick="showScreen('ask')">
                    ❓ ЗАДАТЬ ВОПРОС
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ВЫБОРА РЕЖИМА
// ============================================

function renderModeScreen(container) {
    const profileCode = app.userData.profile_code || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
    
    const html = `
        <div class="mode-screen">
            <div class="mode-header">
                <div class="mode-profile">
                    <span class="mode-profile-label">Твой профиль:</span>
                    <span class="mode-profile-code">${profileCode}</span>
                </div>
            </div>
            
            <div class="mode-card ${app.selectedMode === 'coach' ? 'active' : ''}" onclick="setMode('coach')">
                <div class="mode-title">🔮 КОУЧ</div>
                <div class="mode-desc">
                    Если хочешь, чтобы я помог тебе самому найти решения.
                </div>
                <ul class="mode-benefits">
                    <li>• Жить станет легче — перестанешь закапываться в сомнениях</li>
                    <li>• Появится больше радости от простых вещей</li>
                    <li>• Начнёшь замечать возможности вместо проблем</li>
                </ul>
            </div>
            
            <div class="mode-card ${app.selectedMode === 'psychologist' ? 'active' : ''}" onclick="setMode('psychologist')">
                <div class="mode-title">🧠 ПСИХОЛОГ</div>
                <div class="mode-desc">
                    Если хочешь копнуть вглубь, разобраться с причинами, а не следствиями.
                </div>
                <ul class="mode-benefits">
                    <li>• Перестанешь реагировать на триггеры</li>
                    <li>• Исчезнут старые сценарии, которые портили жизнь</li>
                    <li>• Внутри станет легче и спокойнее</li>
                </ul>
            </div>
            
            <div class="mode-card ${app.selectedMode === 'trainer' ? 'active' : ''}" onclick="setMode('trainer')">
                <div class="mode-title">⚡ ТРЕНЕР</div>
                <div class="mode-desc">
                    Если нужны чёткие инструменты, навыки и результат.
                </div>
                <ul class="mode-benefits">
                    <li>• Научишься чётко формулировать мысли</li>
                    <li>• Освоишь алгоритмы ведения переговоров</li>
                    <li>• Сформируешь полезные привычки</li>
                </ul>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ПРОФИЛЯ
// ============================================

function renderProfileScreen(container) {
    // Заглушка для профиля
    const html = `
        <div class="profile-screen">
            <div class="profile-header">
                <div class="profile-code">СБ-5_ТФ-5_УБ-5_ЧВ-3</div>
            </div>
            
            <div class="profile-section">
                <h2><span>🔑</span> КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА</h2>
                <p>Вы — командир крепости с тревожным сердцем. Снаружи — неприступные стены, отлаженные системы управления.</p>
            </div>
            
            <div class="profile-section">
                <h2><span>💪</span> СИЛЬНЫЕ СТОРОНЫ</h2>
                <ul>
                    <li>Высокоразвитые социальные навыки</li>
                    <li>Системное мышление</li>
                    <li>Устойчивость к стрессу</li>
                    <li>Прагматизм</li>
                </ul>
            </div>
            
            <div class="profile-section">
                <h2><span>🎯</span> ЗОНЫ РОСТА</h2>
                <ul>
                    <li>Страх конфликтов</li>
                    <li>Энергией</li>
                    <li>Временем</li>
                </ul>
            </div>
            
            <div class="profile-section">
                <h2><span>⚠️</span> ГЛАВНАЯ ЛОВУШКА</h2>
                <p>⚡ Поведение</p>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН МЫСЛЕЙ ПСИХОЛОГА
// ============================================

function renderThoughtScreen(container) {
    const html = `
        <div class="thought-screen">
            <div class="thought-block">
                <div class="thought-title">🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ</div>
                <p>Ключ ко всей системе — твоя «Реакция на угрозу». Это как бронированная дверь, которая всегда на замке.</p>
            </div>
            
            <div class="thought-block">
                <div class="thought-title">🔄 ПЕТЛЯ</div>
                <p>Анализ → Сомнения → Ещё больший анализ</p>
            </div>
            
            <div class="thought-block">
                <div class="thought-title">🚪 ТОЧКА ВХОДА</div>
                <p>Спроси себя: "Что я чувствую прямо сейчас?"</p>
            </div>
            
            <div class="thought-block">
                <div class="thought-title">📊 ПРОГНОЗ</div>
                <p>Если продолжишь в том же духе, рискуешь упустить несколько хороших возможностей.</p>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЦЕЛЕЙ
// ============================================

function renderGoalsScreen(container) {
    const goals = [
        { id: 'boundaries', name: 'Научиться защищать границы', time: '2-3 недели', difficulty: 'medium' },
        { id: 'income', name: 'Увеличить доход', time: '4-6 недель', difficulty: 'hard' },
        { id: 'purpose', name: 'Найти предназначение', time: '5-7 недель', difficulty: 'hard' },
        { id: 'relations', name: 'Улучшить отношения', time: '4-6 недель', difficulty: 'medium' },
        { id: 'calm', name: 'Найти внутреннее спокойствие', time: '3-5 недель', difficulty: 'medium' }
    ];
    
    let html = '<div class="goals-screen">';
    html += '<h2>👇 Выберите цель:</h2>';
    
    goals.forEach(goal => {
        const difficultyClass = goal.difficulty;
        const difficultyEmoji = {
            'easy': '🟢',
            'medium': '🟡',
            'hard': '🔴'
        }[difficultyClass];
        
        html += `
            <div class="goal-card" onclick="selectGoal('${goal.id}')">
                <div class="goal-difficulty ${difficultyClass}">${difficultyEmoji}</div>
                <div class="goal-info">
                    <div class="goal-name">${goal.name}</div>
                    <div class="goal-time">${goal.time}</div>
                </div>
            </div>
        `;
    });
    
    html += `
        <button class="custom-goal-btn" onclick="customGoal()">
            ✏️ Сформулирую сам
        </button>
    </div>`;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ВОПРОСА
// ============================================

function renderAskScreen(container) {
    const examples = [
        "Как найти своё предназначение?",
        "Что делать с неопределённостью?",
        "Как перестать сомневаться?",
        "Почему я реагирую на одни и те же триггеры?",
        "Как проработать детскую травму?"
    ];
    
    const html = `
        <div class="ask-screen">
            <div class="ask-header">
                <h2>Задайте вопрос</h2>
                <p>Напишите текст или отправьте голосовое сообщение</p>
            </div>
            
            <div class="messages-container" id="messagesContainer">
                <div class="message system">
                    👋 Задайте любой вопрос, и я отвечу с учётом вашего профиля
                </div>
            </div>
            
            <div class="input-panel">
                <input type="text" class="text-input" id="messageInput" 
                       placeholder="Напишите вопрос..." onkeypress="handleKeyPress(event)">
                <button class="voice-btn" onclick="toggleRecording()">🎤</button>
                <button class="send-btn" onclick="sendMessage()">➤</button>
            </div>
            
            <div class="examples-section">
                <h3>Примеры вопросов:</h3>
                <div class="example-buttons">
                    ${examples.map(ex => `
                        <button class="example-btn" onclick="setExampleQuestion('${ex}')">
                            ${ex}
                        </button>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЗАГРУЗКА
// ============================================

function showLoading() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="loading-screen">
            <div class="spinner"></div>
            <p>Загрузка...</p>
        </div>
    `;
}

function showError(message) {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="error-screen">
            ❌ ${message}
        </div>
    `;
}

// ============================================
// НАЧАЛО ТЕСТА
// ============================================

function startTest() {
    console.log('🚀 Начинаем тест');
    showScreen('stage1');
}

function startStage1() {
    console.log('▶️ Начинаем этап 1');
    // Здесь будет логика первого вопроса
    alert('Этап 1: Первый вопрос появится здесь');
}

// ============================================
// ОБРАБОТЧИКИ ДЕЙСТВИЙ
// ============================================

function showBenefits() {
    console.log('📖 Показываем преимущества теста');
    showScreen('why');
}

function selectMode(mode) {
    console.log('🎯 Выбран режим:', mode);
    
    // Маппинг
    const modeMap = {
        'hard': 'trainer',
        'medium': 'coach',
        'soft': 'psychologist'
    };
    
    app.selectedMode = modeMap[mode];
    showScreen('mode');
}

function setMode(mode) {
    console.log('✅ Установлен режим:', mode);
    app.selectedMode = mode;
    
    // Здесь будет вызов API для сохранения режима
    showScreen('main');
}

function selectGoal(goalId) {
    console.log('🎯 Выбрана цель:', goalId);
    alert('Функция выбора цели будет доступна в следующей версии!');
}

function customGoal() {
    console.log('✏️ Пользователь хочет сформулировать свою цель');
    alert('Функция будет доступна в следующей версии!');
}

function setExampleQuestion(question) {
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = question;
        input.focus();
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    
    if (!text) return;
    
    console.log('📤 Отправляем вопрос:', text);
    
    // Добавляем сообщение пользователя
    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.innerHTML += `
        <div class="message user">${escapeHtml(text)}</div>
    `;
    
    // Очищаем поле
    input.value = '';
    
    // Прокручиваем вниз
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Имитируем ответ бота
    setTimeout(() => {
        messagesContainer.innerHTML += `
            <div class="message bot">
                Спасибо за вопрос! Чтобы ответить точнее, мне нужно знать ваш профиль. 
                Пройдите тест — это займёт 15 минут.
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 1000);
}

function toggleRecording() {
    console.log('🎤 Запись голоса');
    alert('Голосовой ввод будет доступен в следующей версии!');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// ЭКСПОРТ (для глобального доступа)
// ============================================

window.showScreen = showScreen;
window.startTest = startTest;
window.startStage1 = startStage1;
window.selectMode = selectMode;
window.setMode = setMode;
window.selectGoal = selectGoal;
window.customGoal = customGoal;
window.setExampleQuestion = setExampleQuestion;
window.handleKeyPress = handleKeyPress;
window.sendMessage = sendMessage;
window.toggleRecording = toggleRecording;
window.showBenefits = showBenefits;
