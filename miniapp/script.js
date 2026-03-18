// ============================================
// script.js - ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ для MAX
// ПОЛНАЯ ВЕРСИЯ со всеми вопросами и экранами
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
    messages: [],
    max: {
        initialized: false,
        theme: 'light',
        platform: 'unknown',
        viewport: { width: 0, height: 0 }
    },
    
    // Данные теста
    testData: {
        stage1: {
            current: 0,
            total: 8,
            answers: [],
            scores: { EXTERNAL: 0, INTERNAL: 0, SYMBOLIC: 0, MATERIAL: 0 }
        },
        stage2: {
            current: 0,
            total: 0,
            answers: [],
            levelScores: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0 },
            strategyLevels: { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] }
        },
        stage3: {
            current: 0,
            total: 8,
            answers: [],
            behavioralLevels: { "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [] }
        },
        stage4: {
            current: 0,
            total: 8,
            answers: [],
            diltsCounts: { "ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0 }
        },
        stage5: {
            current: 0,
            total: 10,
            answers: []
        }
    },
    
    // ============================================
    // ВОПРОСЫ ЭТАПА 1 (ПОЛНАЯ ВЕРСИЯ)
    // ============================================
    stage1Questions: [
        {
            text: "Как вы обычно реагируете, когда кто-то критикует вашу работу?",
            options: {
                "a": { text: "Долго переживаю, прокручиваю в голове", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Сразу начинаю защищаться или оправдываться", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Анализирую, есть ли в критике польза", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "d": { text: "Забиваю — подумаешь, дело житейское", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Что для вас важнее при выборе одежды?",
            options: {
                "a": { text: "Чтобы выглядеть стильно и соответствовать моде", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Чтобы было комфортно и удобно", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "c": { text: "Чтобы подчеркнуть мою индивидуальность", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "d": { text: "Чтобы было практично и не марко", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Когда вы попадаете в новую компанию, вы:",
            options: {
                "a": { text: "Сначала наблюдаете, прислушиваетесь к своим ощущениям", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Активно знакомитесь, вступаете в разговоры", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Оцениваете, кто здесь может быть полезен", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "d": { text: "Думаете: 'Главное, чтобы не доставали'", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Что вас больше всего тревожит в нестабильные времена?",
            options: {
                "a": { text: "Что я могу потерять связь с близкими", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Что я потеряю контроль над своей жизнью", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "c": { text: "Что обесценятся мои знания и опыт", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "d": { text: "Что останусь без денег и ресурсов", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Как вы обычно принимаете важные решения?",
            options: {
                "a": { text: "Прислушиваюсь к интуиции, внутреннему голосу", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Советуюсь с теми, кому доверяю", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Просчитываю риски и выгоду", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "d": { text: "Смотрю, как другие в такой ситуации поступили", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Что для вас означает 'успех'?",
            options: {
                "a": { text: "Быть признанным, уважаемым в обществе", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Чувствовать гармонию и удовлетворение", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Иметь стабильный доход и активы", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "d": { text: "Достичь конкретных целей, которые поставил", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Когда кто-то обещает вам что-то важное, вы:",
            options: {
                "a": { text: "Верю на слово, пока не докажут обратное", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Надеюсь, но внутренне готовлюсь к худшему", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Проверяю, создаю запасной план", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } },
                "d": { text: "Жду результата, слова — не главное", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        },
        {
            text: "Что вы чувствуете, когда долго находитесь в одиночестве?",
            options: {
                "a": { text: "Тревогу, хочется к людям", scores: { "EXTERNAL": 1, "INTERNAL": 0, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "b": { text: "Умиротворение, наконец-то тишина", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "c": { text: "Начинаю думать о смысле жизни", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 1, "MATERIAL": 0 } },
                "d": { text: "Планирую дела, строю планы", scores: { "EXTERNAL": 0, "INTERNAL": 1, "SYMBOLIC": 0, "MATERIAL": 1 } }
            }
        }
    ],
    
    // ============================================
    // РЕЗУЛЬТАТЫ ЭТАПА 1 (ПОЛНАЯ ВЕРСИЯ)
    // ============================================
    stage1Results: {
        "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ": "🧠 ВАШЕ ВОСПРИЯТИЕ: СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ\n\nВы смотрите на мир через людей. Для вас важны отношения, статус, признание. Ваша тревога — быть отвергнутым, непонятым, остаться в одиночестве. Вы чутко считываете настроение других и часто подстраиваетесь под ожидания. Это делает вас прекрасным коммуникатором, но иногда вы теряете себя в угоду другим.",
        
        "СТАТУСНО-ОРИЕНТИРОВАННЫЙ": "🧠 ВАШЕ ВОСПРИЯТИЕ: СТАТУСНО-ОРИЕНТИРОВАННЫЙ\n\nВы смотрите на мир через достижения. Для вас важны результаты, ресурсы, контроль. Ваша тревога — потерять позиции, оказаться не у дел, лишиться ресурсов. Вы прагматичны, цените эффективность и умеете добиваться своего. Это помогает вам в карьере, но иногда вы забываете о чувствах — своих и чужих.",
        
        "СМЫСЛО-ОРИЕНТИРОВАННЫЙ": "🧠 ВАШЕ ВОСПРИЯТИЕ: СМЫСЛО-ОРИЕНТИРОВАННЫЙ\n\nВы смотрите на мир через идеи и смыслы. Для вас важны понимание, глубина, истина. Ваша тревога — жить бессмысленно, не найти своего пути. Вы склонны к рефлексии, ищете закономерности и часто углублены в себя. Это даёт вам мудрость, но может отрывать от реальности.",
        
        "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ": "🧠 ВАШЕ ВОСПРИЯТИЕ: ПРАКТИКО-ОРИЕНТИРОВАННЫЙ\n\nВы смотрите на мир через конкретику. Для вас важны факты, действия, результат здесь и сейчас. Ваша тревога — не справиться, не успеть, не получить нужного. Вы живёте в реальности, цените практичность и умеете действовать. Это делает вас эффективным, но иногда вы упускаете общую картину."
    }
};

// ============================================
// КОНСТАНТЫ ДЛЯ ХРАНЕНИЯ
// ============================================

const STORAGE_KEYS = {
    USER_DATA: 'fredi_user_data',
    PROFILE: 'fredi_profile',
    THOUGHT: 'fredi_thought',
    TEST_PROGRESS: 'fredi_test_progress',
    PENDING_SYNC: 'fredi_pending_sync',
    MODE: 'fredi_mode'
};

// ============================================
// ИНИЦИАЛИЗАЦИЯ MAX
// ============================================

async function initMAX() {
    return new Promise((resolve) => {
        if (window.MAX) {
            setupMAX();
            resolve();
        } else {
            window.addEventListener('load', () => {
                if (window.MAX) {
                    setupMAX();
                } else {
                    console.log('⚠️ MAX Bridge не найден, работа в автономном режиме');
                    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                    app.max.theme = prefersDark ? 'dark' : 'light';
                    document.documentElement.setAttribute('data-max-theme', app.max.theme);
                }
                resolve();
            });
        }
    });
}

function setupMAX() {
    console.log('✅ MAX Bridge инициализирован');
    
    app.max.initialized = true;
    
    try {
        if (window.MAX.theme) {
            app.max.theme = window.MAX.theme;
            document.documentElement.setAttribute('data-max-theme', app.max.theme);
        }
        
        if (window.MAX.platform) {
            app.max.platform = window.MAX.platform;
            document.documentElement.setAttribute('data-max-platform', app.max.platform);
        }
        
        if (window.MAX.viewport) {
            app.max.viewport = window.MAX.viewport;
        }
    } catch (e) {
        console.warn('⚠️ Ошибка получения данных MAX:', e);
    }
    
    try {
        window.MAX.onEvent('themeChanged', (newTheme) => {
            console.log('🎨 Тема изменена:', newTheme);
            app.max.theme = newTheme;
            document.documentElement.setAttribute('data-max-theme', newTheme);
            if (app.currentScreen) {
                showScreen(app.currentScreen);
            }
        });
        
        window.MAX.onEvent('viewportChanged', (viewport) => {
            app.max.viewport = viewport;
        });
        
        window.MAX.onEvent('backButtonPressed', () => {
            handleBackButton();
        });
        
    } catch (e) {
        console.warn('⚠️ Ошибка подписки на события MAX:', e);
    }
    
    try {
        window.MAX.ready();
    } catch (e) {}
}

// ============================================
// ОБРАБОТКА КНОПКИ НАЗАД
// ============================================

function handleBackButton() {
    switch(app.currentScreen) {
        case 'welcome':
        case 'main':
            if (window.MAX) {
                window.MAX.close();
            }
            break;
        case 'why':
        case 'stage1':
        case 'stage2':
        case 'stage3':
        case 'stage4':
        case 'stage5':
        case 'profile':
        case 'thought':
        case 'goals':
        case 'mode':
        case 'ask':
            showScreen('main');
            break;
        default:
            showScreen('main');
    }
}

// ============================================
// ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ
// ============================================

function getUserId() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlUserId = urlParams.get('user_id');
    const urlName = urlParams.get('first_name');
    
    if (urlUserId) {
        console.log('✅ User ID из URL:', urlUserId);
        if (urlName) app.userData.user_name = urlName;
        return urlUserId;
    }
    
    try {
        if (window.MAX && window.MAX.user) {
            const maxUser = window.MAX.user;
            console.log('✅ User ID из MAX WebApp:', maxUser.id);
            app.userData.user_name = maxUser.first_name || maxUser.name || 'Пользователь';
            return maxUser.id;
        }
    } catch (e) {}
    
    try {
        if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
            const tgUser = window.Telegram.WebApp.initDataUnsafe.user;
            console.log('✅ User ID из Telegram WebApp:', tgUser.id);
            app.userData.user_name = tgUser.first_name;
            return tgUser.id;
        }
    } catch (e) {}
    
    console.log('⚠️ Использую тестовый ID: 213102077');
    app.userData.user_name = 'Андрей';
    return '213102077';
}

// ============================================
// ФУНКЦИИ ДЛЯ ЛОКАЛЬНОГО ХРАНЕНИЯ
// ============================================

function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify({
            data: data,
            timestamp: Date.now(),
            userId: app.userId
        }));
        return true;
    } catch (e) {
        console.warn('⚠️ Ошибка сохранения в localStorage:', e);
        return false;
    }
}

function loadFromStorage(key, maxAge = 7 * 24 * 60 * 60 * 1000) {
    try {
        const item = localStorage.getItem(key);
        if (!item) return null;
        
        const { data, timestamp, userId } = JSON.parse(item);
        
        if (userId && userId !== app.userId) {
            return null;
        }
        
        if (Date.now() - timestamp > maxAge) {
            localStorage.removeItem(key);
            return null;
        }
        
        return data;
    } catch (e) {
        return null;
    }
}

// ============================================
// ФУНКЦИИ ДЛЯ API
// ============================================

async function saveProfile(profileData) {
    saveToStorage(STORAGE_KEYS.PROFILE, profileData);
    
    if (window.MAX && window.MAX.api) {
        try {
            await window.MAX.api.post('/api/save-profile', {
                user_id: app.userId,
                profile: profileData
            });
            console.log('✅ Профиль сохранен на сервере');
        } catch (error) {
            console.log('⚠️ Ошибка сохранения на сервере');
        }
    }
}

async function saveTestAnswer(stage, questionIndex, answer) {
    const progress = loadFromStorage(STORAGE_KEYS.TEST_PROGRESS) || {};
    if (!progress[stage]) progress[stage] = [];
    progress[stage].push({ question: questionIndex, answer });
    saveToStorage(STORAGE_KEYS.TEST_PROGRESS, progress);
    
    if (window.MAX && window.MAX.api) {
        try {
            await window.MAX.api.post('/api/save-test-progress', {
                user_id: app.userId,
                stage: stage,
                answers: [{question: questionIndex, answer: answer}]
            });
        } catch (error) {}
    }
}

async function saveMode(mode) {
    app.selectedMode = mode;
    saveToStorage(STORAGE_KEYS.MODE, mode);
    
    if (window.MAX && window.MAX.api) {
        try {
            await window.MAX.api.post('/api/save-mode', {
                user_id: app.userId,
                mode: mode
            });
        } catch (error) {}
    }
}

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 ФРЕДИ для MAX запущено');
    
    await initMAX();
    
    app.userId = getUserId();
    
    loadSavedData();
    
    showLoading();
    
    await loadUserData();
    
    setupMAXUI();
});

function loadSavedData() {
    const savedMode = loadFromStorage(STORAGE_KEYS.MODE);
    if (savedMode) {
        app.selectedMode = savedMode;
    }
    
    const savedProfile = loadFromStorage(STORAGE_KEYS.PROFILE);
    if (savedProfile) {
        app.userData.profile = savedProfile;
    }
    
    const savedThought = loadFromStorage(STORAGE_KEYS.THOUGHT);
    if (savedThought) {
        app.userData.thought = savedThought;
    }
}

function setupMAXUI() {
    document.body.classList.add('max-webapp');
    
    if (app.max.platform === 'ios') {
        document.documentElement.style.setProperty('--safe-area-top', 'env(safe-area-inset-top)');
        document.documentElement.style.setProperty('--safe-area-bottom', 'env(safe-area-inset-bottom)');
    }
}

async function loadUserData() {
    const cached = loadFromStorage(STORAGE_KEYS.USER_DATA);
    if (cached) {
        app.userData = { ...app.userData, ...cached };
        app.hasProfile = cached.has_profile || false;
        
        if (app.hasProfile) {
            showScreen('main');
            document.getElementById('navBar').style.display = 'flex';
        } else {
            showScreen('welcome');
            document.getElementById('navBar').style.display = 'none';
        }
    } else {
        showScreen('welcome');
        document.getElementById('navBar').style.display = 'none';
    }
    
    if (window.MAX && window.MAX.api) {
        try {
            const data = await window.MAX.api.get(`/api/user-data?user_id=${app.userId}`);
            if (data) {
                app.userData = { ...app.userData, ...data };
                app.hasProfile = data.has_profile || false;
                saveToStorage(STORAGE_KEYS.USER_DATA, data);
                
                if (app.hasProfile) {
                    showScreen('main');
                    document.getElementById('navBar').style.display = 'flex';
                }
            }
        } catch (error) {
            console.log('⚠️ Не удалось загрузить данные с сервера');
        }
    }
}

// ============================================
// ПОКАЗ ЭКРАНОВ
// ============================================

function showScreen(screen) {
    app.currentScreen = screen;
    
    const headerTitle = document.getElementById('header-title');
    const titles = {
        'welcome': '👋 ФРЕДИ',
        'why': '🧐 ФРЕДИ',
        'main': '🏠 ФРЕДИ',
        'mode': '🔮 ФРЕДИ',
        'stage1': '🧠 ЭТАП 1/5',
        'stage2': '🧠 ЭТАП 2/5',
        'stage3': '🧠 ЭТАП 3/5',
        'stage4': '🧠 ЭТАП 4/5',
        'stage5': '🧠 ЭТАП 5/5',
        'profile': '📊 ПОРТРЕТ',
        'thought': '🧠 МЫСЛИ',
        'goals': '🎯 ЦЕЛИ',
        'ask': '❓ ВОПРОС'
    };
    headerTitle.textContent = titles[screen] || '🧠 ФРЕДИ';
    
    const backBtn = document.getElementById('backBtn');
    backBtn.style.display = (screen === 'welcome' || screen === 'main') ? 'none' : 'flex';
    
    const navBar = document.getElementById('navBar');
    if (screen === 'main' || screen === 'profile' || screen === 'thought' || screen === 'goals' || screen === 'ask') {
        navBar.style.display = 'flex';
    } else {
        navBar.style.display = 'none';
    }
    
    if (window.MAX) {
        try {
            if (screen === 'welcome' || screen === 'main') {
                window.MAX.backButton.hide();
            } else {
                window.MAX.backButton.show();
            }
        } catch (e) {}
    }
    
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
            case 'stage2':
                renderStage2Screen(content);
                break;
            case 'stage3':
                renderStage3Screen(content);
                break;
            case 'stage4':
                renderStage4Screen(content);
                break;
            case 'stage5':
                renderStage5Screen(content);
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
// ЭКРАН ПРИВЕТСТВИЯ
// ============================================

function renderWelcomeScreen(container) {
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
                <button class="action-btn primary" onclick="startStage1()">
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
                <button class="action-btn primary" onclick="startStage1()">
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
// ГЛАВНЫЙ ЭКРАН
// ============================================

function renderMainScreen(container) {
    const greeting = getTimeGreeting();
    const userName = app.userData.user_name || 'друг';
    
    const html = `
        <div class="main-screen">
            <div class="greeting">${greeting}, ${userName}!</div>
            
            <div class="profile-badge" onclick="showScreen('profile')">
                <span class="profile-code">${app.userData.profile_code || 'СБ-4_ТФ-4_УБ-4_ЧВ-4'}</span>
                <span class="profile-arrow">📊</span>
            </div>
            
            <div class="context-message">
                ${getContextMessage()}
            </div>
            
            <div class="main-menu">
                <button class="menu-card" onclick="showScreen('mode')">
                    <span class="menu-emoji">🔮</span>
                    <span class="menu-title">ВЫБРАТЬ РЕЖИМ</span>
                    <span class="menu-desc">Коуч / Психолог / Тренер</span>
                </button>
                
                <button class="menu-card" onclick="showScreen('thought')">
                    <span class="menu-emoji">🧠</span>
                    <span class="menu-title">МЫСЛИ ПСИХОЛОГА</span>
                    <span class="menu-desc">Глубинный анализ</span>
                </button>
                
                <button class="menu-card" onclick="showScreen('goals')">
                    <span class="menu-emoji">🎯</span>
                    <span class="menu-title">ВЫБРАТЬ ЦЕЛЬ</span>
                    <span class="menu-desc">Индивидуальный маршрут</span>
                </button>
                
                <button class="menu-card" onclick="showScreen('ask')">
                    <span class="menu-emoji">❓</span>
                    <span class="menu-title">ЗАДАТЬ ВОПРОС</span>
                    <span class="menu-desc">Текст или голос</span>
                </button>
            </div>
            
            <div class="weekend-hint" onclick="showWeekendIdeas()">
                🎨 Идеи на выходные →
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour < 6) return "Доброй ночи";
    if (hour < 12) return "Доброе утро";
    if (hour < 18) return "Добрый день";
    return "Добрый вечер";
}

function getContextMessage() {
    const hour = new Date().getHours();
    const day = new Date().getDay();
    
    if (day === 0 || day === 6) {
        return '🏖 Сегодня выходной! Как настроение?';
    }
    
    if (hour >= 9 && hour < 18) {
        return '💼 Рабочее время. Чем займёмся?';
    } else if (hour >= 18 || hour < 6) {
        return '🏡 Личное время. Есть что обсудить?';
    } else {
        return '🌙 Ночное время. Что тревожит?';
    }
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
            
            <div class="mode-card ${app.selectedMode === 'coach' ? 'active' : ''}" onclick="setMode('coach', this)">
                <div class="mode-title">🔮 КОУЧ</div>
                <div class="mode-desc">
                    Если хочешь, чтобы я помог тебе самому найти решения.
                </div>
                <ul class="mode-benefits">
                    <li>• Жить станет легче — перестанешь закапываться в сомнениях</li>
                    <li>• Появится больше радости от простых вещей</li>
                    <li>• Начнёшь замечать возможности вместо проблем</li>
                    <li>• Перестанешь чувствовать вину за каждый шаг</li>
                </ul>
            </div>
            
            <div class="mode-card ${app.selectedMode === 'psychologist' ? 'active' : ''}" onclick="setMode('psychologist', this)">
                <div class="mode-title">🧠 ПСИХОЛОГ</div>
                <div class="mode-desc">
                    Если хочешь копнуть вглубь, разобраться с причинами, а не следствиями.
                </div>
                <ul class="mode-benefits">
                    <li>• Перестанешь реагировать на триггеры — будешь выбирать реакцию сам</li>
                    <li>• Исчезнут старые сценарии, которые портили жизнь</li>
                    <li>• Поймёшь, откуда растут ноги у твоих страхов</li>
                    <li>• Внутри станет легче и спокойнее</li>
                </ul>
            </div>
            
            <div class="mode-card ${app.selectedMode === 'trainer' ? 'active' : ''}" onclick="setMode('trainer', this)">
                <div class="mode-title">⚡ ТРЕНЕР</div>
                <div class="mode-desc">
                    Если нужны чёткие инструменты, навыки и результат.
                </div>
                <ul class="mode-benefits">
                    <li>• Научишься чётко формулировать мысли — тебя будут понимать</li>
                    <li>• Освоишь алгоритмы ведения переговоров</li>
                    <li>• Сформируешь полезные привычки</li>
                    <li>• Будешь уверенно действовать в стрессовых ситуациях</li>
                </ul>
            </div>
            
            <button class="apply-mode-btn" onclick="applyMode()">
                ✅ ПРИМЕНИТЬ РЕЖИМ
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

function setMode(mode, element) {
    app.selectedMode = mode;
    
    const cards = document.querySelectorAll('.mode-card');
    cards.forEach(card => {
        card.classList.remove('active');
    });
    if (element) {
        element.classList.add('active');
    }
}

async function applyMode() {
    if (!app.selectedMode) {
        alert('Выберите режим');
        return;
    }
    
    console.log('✅ Режим установлен:', app.selectedMode);
    await saveMode(app.selectedMode);
    showScreen('main');
}

// ============================================
// ЭКРАН ЭТАПА 1
// ============================================

function startStage1() {
    app.testData.stage1.current = 0;
    showScreen('stage1');
}

function renderStage1Screen(container) {
    const current = app.testData.stage1.current;
    const total = app.testData.stage1.total;
    
    if (current >= total) {
        finishStage1();
        return;
    }
    
    const question = app.stage1Questions[current];
    const progress = Math.round((current / total) * 100);
    
    let optionsHtml = '';
    for (const [key, option] of Object.entries(question.options)) {
        optionsHtml += `
            <button class="option-btn" onclick="answerStage1('${key}')">
                ${option.text}
            </button>
        `;
    }
    
    const html = `
        <div class="stage-screen">
            <div class="stage-header">
                <span class="stage-title">🧠 ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</span>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <span class="progress-text">Вопрос ${current + 1}/${total}</span>
            </div>
            
            <div class="question-text">
                ${question.text}
            </div>
            
            <div class="options-container">
                ${optionsHtml}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function answerStage1(optionKey) {
    const current = app.testData.stage1.current;
    const question = app.stage1Questions[current];
    const selectedOption = question.options[optionKey];
    
    app.testData.stage1.answers.push({
        question: current,
        answer: optionKey,
        text: selectedOption.text
    });
    
    const scores = selectedOption.scores;
    for (const [key, value] of Object.entries(scores)) {
        app.testData.stage1.scores[key] += value;
    }
    
    saveTestAnswer(1, current, {
        option: optionKey,
        scores: scores
    });
    
    app.testData.stage1.current++;
    
    if (app.testData.stage1.current >= app.testData.stage1.total) {
        finishStage1();
    } else {
        showScreen('stage1');
    }
}

function finishStage1() {
    const scores = app.testData.stage1.scores;
    const external = scores.EXTERNAL || 0;
    const internal = scores.INTERNAL || 0;
    const symbolic = scores.SYMBOLIC || 0;
    const material = scores.MATERIAL || 0;
    
    const attention = external > internal ? "EXTERNAL" : "INTERNAL";
    const anxiety = symbolic > material ? "SYMBOLIC" : "MATERIAL";
    
    let perceptionType = "";
    if (attention === "EXTERNAL" && anxiety === "SYMBOLIC") {
        perceptionType = "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ";
    } else if (attention === "EXTERNAL" && anxiety === "MATERIAL") {
        perceptionType = "СТАТУСНО-ОРИЕНТИРОВАННЫЙ";
    } else if (attention === "INTERNAL" && anxiety === "SYMBOLIC") {
        perceptionType = "СМЫСЛО-ОРИЕНТИРОВАННЫЙ";
    } else {
        perceptionType = "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ";
    }
    
    app.testData.perceptionType = perceptionType;
    
    saveProfile({ stage1_complete: true, perception_type: perceptionType, scores: scores });
    
    const resultText = app.stage1Results[perceptionType] || app.stage1Results["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"];
    
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="result-screen">
            <div class="result-text">${resultText.replace(/\n/g, '<br>')}</div>
            <button class="action-btn primary" onclick="startStage2()">
                ▶️ ПЕРЕЙТИ К ЭТАПУ 2
            </button>
        </div>
    `;
}

// ============================================
// ЭКРАН ЭТАПА 2
// ============================================

function startStage2() {
    showScreen('stage2');
}

function renderStage2Screen(container) {
    const html = `
        <div class="stage-screen">
            <div class="stage-header">
                <span class="stage-title">🧠 ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</span>
            </div>
            
            <div class="welcome-text">
                <p>Восприятие определяет, что вы видите. Мышление — как вы это понимаете.</p>
                
                <p>🎯 <strong>Самое важное:</strong><br>
                Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте. Если ничего не менять — вы попадёте именно туда.</p>
                
                <p>📊 <strong>Вопросов:</strong> зависит от типа восприятия<br>
                ⏱ <strong>Время:</strong> ~3-4 минуты</p>
                
                <p>Продолжим исследование?</p>
            </div>
            
            <button class="action-btn primary" onclick="alert('Этап 2 в разработке')">
                ▶️ НАЧАТЬ ИССЛЕДОВАНИЕ
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЭТАПА 3
// ============================================

function renderStage3Screen(container) {
    const html = `
        <div class="stage-screen">
            <div class="stage-header">
                <span class="stage-title">🧠 ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</span>
            </div>
            
            <div class="welcome-text">
                <p>Восприятие определяет, что вы видите.<br>
                Мышление — как вы это понимаете.</p>
                
                <p>Конфигурация поведения — это то, как вы на это реагируете.</p>
                
                <p>🔍 <strong>Здесь мы исследуем:</strong><br>
                • Ваши автоматические реакции<br>
                • Как вы действуете в разных ситуациях<br>
                • Какие стратегии поведения закреплены</p>
                
                <p>📊 <strong>Вопросов:</strong> 8<br>
                ⏱ <strong>Время:</strong> ~3 минуты</p>
            </div>
            
            <button class="action-btn primary" onclick="alert('Этап 3 в разработке')">
                ▶️ НАЧАТЬ ИССЛЕДОВАНИЕ
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЭТАПА 4
// ============================================

function renderStage4Screen(container) {
    const html = `
        <div class="stage-screen">
            <div class="stage-header">
                <span class="stage-title">🧠 ЭТАП 4: ТОЧКА РОСТА</span>
            </div>
            
            <div class="welcome-text">
                <p>Восприятие — что вы видите.<br>
                Мышление — как понимаете.<br>
                Поведение — как реагируете.</p>
                
                <p>🌍 Но она живёт внутри внешней системы — общества, которое постоянно меняется.</p>
                
                <p>⚡ Когда одна система меняется, а другая — нет, возникает напряжение.</p>
                
                <p>🔍 <strong>Здесь мы найдём:</strong> где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.</p>
                
                <p>📊 <strong>Вопросов:</strong> 8<br>
                ⏱ <strong>Время:</strong> ~3 минуты</p>
            </div>
            
            <button class="action-btn primary" onclick="alert('Этап 4 в разработке')">
                ▶️ НАЧАТЬ ИССЛЕДОВАНИЕ
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЭТАПА 5
// ============================================

function renderStage5Screen(container) {
    const html = `
        <div class="stage-screen">
            <div class="stage-header">
                <span class="stage-title">🧠 ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</span>
            </div>
            
            <div class="welcome-text">
                <p>Мы узнали, как вы воспринимаете мир, мыслите и действуете.<br>
                Теперь пришло время заглянуть глубже — в то, что сформировало вас.</p>
                
                <p>🔍 <strong>Здесь мы исследуем:</strong><br>
                • Какой у вас тип привязанности (из детства)<br>
                • Какие защитные механизмы вы используете<br>
                • Какие глубинные убеждения управляют вами<br>
                • Чего вы боитесь на самом деле</p>
                
                <p>📊 <strong>Вопросов:</strong> 10<br>
                ⏱ <strong>Время:</strong> ~5 минут</p>
            </div>
            
            <button class="action-btn primary" onclick="alert('Этап 5 в разработке')">
                ▶️ НАЧАТЬ ИССЛЕДОВАНИЕ
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ПРОФИЛЯ
// ============================================

function renderProfileScreen(container) {
    const profile = app.userData.profile || `
🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ

🔍 Тип восприятия: СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ
🧠 Уровень мышления: 5/9

🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА
Вы — командир крепости с тревожным сердцем. Снаружи — неприступные стены, отлаженные системы управления.

💪 СИЛЬНЫЕ СТОРОНЫ
• Высокоразвитые социальные навыки
• Системное мышление
• Устойчивость к стрессу
• Прагматизм

🎯 ЗОНЫ РОСТА
• Страх конфликтов
• Энергией
• Временем

⚠️ ГЛАВНАЯ ЛОВУШКА
⚡ Поведение
    `;
    
    const html = `
        <div class="profile-screen">
            <div class="profile-content">
                ${profile.replace(/\n/g, '<br>')}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН МЫСЛЕЙ
// ============================================

function renderThoughtScreen(container) {
    const thought = app.userData.thought || `
🧠 МЫСЛИ ПСИХОЛОГА

🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ
Ключ ко всей системе — твоя «Реакция на угрозу». Это как бронированная дверь, которая всегда на замке.

🔄 ПЕТЛЯ
Анализ → Сомнения → Ещё больший анализ

🚪 ТОЧКА ВХОДА
Спроси себя: "Что я чувствую прямо сейчас?"

📊 ПРОГНОЗ
Если продолжишь в том же духе, рискуешь упустить несколько хороших возможностей.
    `;
    
    const html = `
        <div class="thought-screen">
            <div class="thought-content">
                ${thought.replace(/\n/g, '<br>')}
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
        { id: 'fear_work', name: 'Проработать страхи', time: '3-4 недели', difficulty: 'medium', desc: 'Научиться справляться с тревогой' },
        { id: 'boundaries', name: 'Научиться защищать границы', time: '2-3 недели', difficulty: 'medium', desc: 'Говорить "нет" без чувства вины' },
        { id: 'income', name: 'Увеличить доход', time: '4-6 недель', difficulty: 'hard', desc: 'Найти новые источники' },
        { id: 'purpose', name: 'Найти предназначение', time: '5-7 недель', difficulty: 'hard', desc: 'Понять, куда двигаться' },
        { id: 'relations', name: 'Улучшить отношения', time: '4-6 недель', difficulty: 'medium', desc: 'С партнёром, детьми, родителями' },
        { id: 'calm', name: 'Найти внутреннее спокойствие', time: '3-5 недель', difficulty: 'medium', desc: 'Перестать тревожиться' }
    ];
    
    let html = '<div class="goals-screen">';
    html += '<h2 class="goals-title">👇 Выберите цель:</h2>';
    
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
                    <div class="goal-desc">${goal.desc}</div>
                    <div class="goal-time">⏱ ${goal.time}</div>
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

function selectGoal(goalId) {
    console.log('🎯 Выбрана цель:', goalId);
    
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="goal-path-screen">
            <h2>🧠 ТВОЯ ЦЕЛЬ</h2>
            
            <p>👇 <strong>ТЕОРЕТИЧЕСКИЙ МАРШРУТ:</strong></p>
            
            <div class="path-steps">
                <div class="path-step">
                    <span class="step-number">1</span>
                    <span class="step-text">Диагностика текущей ситуации</span>
                </div>
                <div class="path-step">
                    <span class="step-number">2</span>
                    <span class="step-text">Выявление ключевых блоков</span>
                </div>
                <div class="path-step">
                    <span class="step-number">3</span>
                    <span class="step-text">Пошаговый план действий</span>
                </div>
                <div class="path-step">
                    <span class="step-number">4</span>
                    <span class="step-text">Первые шаги и закрепление</span>
                </div>
            </div>
            
            <p>⚠️ Это в идеале. В реальности всё зависит от твоих условий.</p>
            
            <div class="action-buttons">
                <button class="action-btn primary" onclick="checkReality()">
                    🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ
                </button>
                <button class="action-btn secondary" onclick="showScreen('goals')">
                    ◀️ ДРУГАЯ ЦЕЛЬ
                </button>
            </div>
        </div>
    `;
}

function checkReality() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="reality-check-screen">
            <h2>🧠 ФРЕДИ: ПРОВЕРКА РЕАЛЬНОСТИ</h2>
            
            <p>👇 <strong>ЧТО ПОТРЕБУЕТСЯ:</strong></p>
            <p>• Время: 3-4 часа в неделю<br>
            • Энергия: средняя (6/10)<br>
            • Поддержка: желательна</p>
            
            <p>👇 <strong>ЧТО У ТЕБЯ ЕСТЬ:</strong></p>
            <p>• Время: 2 часа в неделю<br>
            • Энергия: низкая (3/10)<br>
            • Поддержка: нет</p>
            
            <p>📊 <strong>ДЕФИЦИТ РЕСУРСОВ:</strong> 60%</p>
            
            <p>Рекомендуется увеличить срок или снизить планку.</p>
            
            <div class="action-buttons">
                <button class="action-btn primary" onclick="showScreen('main')">
                    ✅ ПОНЯТНО
                </button>
            </div>
        </div>
    `;
}

function customGoal() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="custom-goal-screen">
            <h2>✏️ СФОРМУЛИРУЙТЕ ЦЕЛЬ</h2>
            
            <p>Расскажите своими словами, чего хотите достичь.</p>
            
            <textarea id="goalInput" class="goal-input" 
                placeholder="Например: Хочу научиться зарабатывать удаленно и путешествовать..." 
                rows="4"></textarea>
            
            <button class="action-btn primary" onclick="submitCustomGoal()">
                🚀 ПОСТРОИТЬ МАРШРУТ
            </button>
        </div>
    `;
}

function submitCustomGoal() {
    const goalText = document.getElementById('goalInput').value;
    if (!goalText) {
        alert('Напишите вашу цель');
        return;
    }
    
    console.log('🎯 Пользовательская цель:', goalText);
    alert('Функция в разработке!');
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
    
    let messagesHtml = '';
    app.messages.forEach(msg => {
        messagesHtml += `
            <div class="message ${msg.role}">
                ${escapeHtml(msg.text)}
            </div>
        `;
    });
    
    if (messagesHtml === '') {
        messagesHtml = `
            <div class="message system">
                👋 Задайте любой вопрос, и я отвечу с учётом вашего профиля
            </div>
        `;
    }
    
    const html = `
        <div class="ask-screen">
            <div class="messages-container" id="messagesContainer">
                ${messagesHtml}
            </div>
            
            <div class="input-panel">
                <input type="text" class="text-input" id="messageInput" 
                       placeholder="Напишите вопрос..." onkeypress="handleKeyPress(event)">
                <button class="voice-btn" onclick="toggleRecording()">🎤</button>
                <button class="send-btn" onclick="sendMessage()">➤</button>
            </div>
            
            <div class="examples-section">
                <div class="example-buttons">
                    ${examples.map(ex => `
                        <button class="example-btn" onclick="setExampleQuestion('${escapeHtml(ex)}')">
                            ${escapeHtml(ex)}
                        </button>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    setTimeout(() => {
        const messagesContainer = document.getElementById('messagesContainer');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }, 100);
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    
    if (!text) return;
    
    app.messages.push({
        role: 'user',
        text: escapeHtml(text)
    });
    
    input.value = '';
    
    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.innerHTML += `
        <div class="message bot typing">
            <span class="typing-dots">...</span>
        </div>
    `;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    setTimeout(() => {
        const typingIndicator = document.querySelector('.message.typing');
        if (typingIndicator) typingIndicator.remove();
        
        const response = generateBotResponse(text);
        app.messages.push({
            role: 'bot',
            text: response
        });
        
        renderAskScreen(document.getElementById('content'));
    }, 1500);
}

function generateBotResponse(question) {
    const lowercaseQ = question.toLowerCase();
    
    if (lowercaseQ.includes('предназначен') || lowercaseQ.includes('смысл')) {
        return "Вопрос о предназначении — один из самых глубоких. Часто мы ищем его вовне, хотя ответ уже внутри. Что для вас важно настолько, что вы готовы делать это бесплатно? А что приносит энергию, даже когда вы устали?";
    }
    
    if (lowercaseQ.includes('тревог') || lowercaseQ.includes('страх')) {
        return "Тревога — это сигнал, а не враг. Она говорит о том, что что-то требует внимания. Что именно вызывает тревогу? Попробуйте описать её: где в теле она живёт? Какого она цвета?";
    }
    
    if (lowercaseQ.includes('отношен') || lowercaseQ.includes('любов')) {
        return "В отношениях мы часто повторяем сценарии, усвоенные в детстве. Какой паттерн вы замечаете? Возможно, вы выбираете партнёров, похожих на кого-то из родителей?";
    }
    
    if (lowercaseQ.includes('деньг') || lowercaseQ.includes('финанс')) {
        return "Деньги — это энергия. Как вы относитесь к деньгам? Чувствуете, что достойны их? Часто наши денежные блоки родом из убеждений, которые мы впитали в семье.";
    }
    
    return "Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. Пройдите тест — это займёт 15 минут.";
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function setExampleQuestion(question) {
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = question;
        input.focus();
    }
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
// ИДЕИ НА ВЫХОДНЫЕ
// ============================================

function showWeekendIdeas() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="weekend-ideas-screen">
            <h2>🎨 ИДЕИ НА ВЫХОДНЫЕ</h2>
            
            <div class="ideas-container">
                <div class="idea-card">
                    <div class="idea-emoji">🧘</div>
                    <div class="idea-text">
                        <strong>Практика осознанности</strong><br>
                        Попробуй 10 минут тишины без телефона. Просто посиди и понаблюдай за дыханием.
                    </div>
                </div>
                
                <div class="idea-card">
                    <div class="idea-emoji">🌳</div>
                    <div class="idea-text">
                        <strong>Прогулка в новом месте</strong><br>
                        Найди парк или район, где никогда не был. Обрати внимание на детали.
                    </div>
                </div>
                
                <div class="idea-card">
                    <div class="idea-emoji">📝</div>
                    <div class="idea-text">
                        <strong>Дневник благодарности</strong><br>
                        Запиши 3 вещи, за которые ты благодарен прошедшей неделе.
                    </div>
                </div>
                
                <div class="idea-card">
                    <div class="idea-emoji">🎨</div>
                    <div class="idea-text">
                        <strong>Творчество без цели</strong><br>
                        Порисуй, полепи, потанцуй — не для результата, а для процесса.
                    </div>
                </div>
            </div>
            
            <button class="action-btn primary" onclick="showScreen('main')">
                ◀️ НАЗАД
            </button>
        </div>
    `;
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

// ============================================
// ЭКСПОРТ (для глобального доступа)
// ============================================

window.showScreen = showScreen;
window.startStage1 = startStage1;
window.startStage2 = startStage2;
window.answerStage1 = answerStage1;
window.setMode = setMode;
window.applyMode = applyMode;
window.setExampleQuestion = setExampleQuestion;
window.handleKeyPress = handleKeyPress;
window.sendMessage = sendMessage;
window.toggleRecording = toggleRecording;
window.showWeekendIdeas = showWeekendIdeas;
window.selectGoal = selectGoal;
window.customGoal = customGoal;
window.submitCustomGoal = submitCustomGoal;
window.checkReality = checkReality;
