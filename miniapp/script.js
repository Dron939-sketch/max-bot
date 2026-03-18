// ============================================
// script.js - Вся логика мини-приложения
// ============================================

// Глобальные переменные
let userId = null;
let currentScreen = 'main';
let userData = {};
let app = {
    userId: null,
    currentScreen: 'main',
    userData: {},
    context: null
};

// ============================================
// ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ
// ============================================

function getUserId() {
    // 1. Пробуем из URL параметров
    const urlParams = new URLSearchParams(window.location.search);
    const urlUserId = urlParams.get('user_id');
    
    if (urlUserId) {
        console.log('✅ User ID из URL:', urlUserId);
        return urlUserId;
    }
    
    // 2. Пробуем из MAX WebApp
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
    console.log('🚀 Mini-app initialized');
    
    // Получаем ID пользователя
    userId = getUserId();
    app.userId = userId;
    
    // Показываем экран загрузки
    showLoading();
    
    // Загружаем данные пользователя
    await loadUserData();
    
    // Показываем главный экран
    showScreen('main');
    
    // Настраиваем навигацию
    setupNavigation();
});

// ============================================
// ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ
// ============================================

async function loadUserData() {
    try {
        const response = await fetch(`/api/user-data?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки');
        
        app.userData = await response.json();
        
        // Загружаем дополнительные данные
        await Promise.all([
            loadProfile(),
            loadThought(),
            loadGoals()
        ]);
        
    } catch (error) {
        console.error('Error loading user data:', error);
        showError('Не удалось загрузить данные пользователя');
    }
}

async function loadProfile() {
    try {
        const response = await fetch(`/api/profile?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки профиля');
        
        const data = await response.json();
        app.userData.profile = data.profile;
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function loadThought() {
    try {
        const response = await fetch(`/api/thought?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки мыслей');
        
        const data = await response.json();
        app.userData.thought = data.thought;
    } catch (error) {
        console.error('Error loading thought:', error);
    }
}

async function loadGoals() {
    try {
        const response = await fetch(`/api/goals?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки целей');
        
        const data = await response.json();
        app.userData.goals = data.goals || [];
    } catch (error) {
        console.error('Error loading goals:', error);
        app.userData.goals = getDefaultGoals();
    }
}

// ============================================
// ЦЕЛИ ПО УМОЛЧАНИЮ (ЕСЛИ API НЕ ОТВЕЧАЕТ)
// ============================================

function getDefaultGoals() {
    return [
        { id: 'boundaries', name: 'Научиться защищать границы', time: '2-3 недели', difficulty: 'medium' },
        { id: 'income', name: 'Увеличить доход', time: '4-6 недель', difficulty: 'hard' },
        { id: 'purpose', name: 'Найти предназначение', time: '5-7 недель', difficulty: 'hard' },
        { id: 'relations', name: 'Улучшить отношения', time: '4-6 недель', difficulty: 'medium' },
        { id: 'calm', name: 'Найти внутреннее спокойствие', time: '3-5 недель', difficulty: 'medium' }
    ];
}

// ============================================
// НАВИГАЦИЯ
// ============================================

function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const screen = btn.dataset.screen;
            
            // Обновляем активную кнопку
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Показываем экран
            showScreen(screen);
        });
    });
    
    // Кнопка назад
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (currentScreen === 'main') {
                // На главной - ничего не делаем или закрываем приложение
                if (window.WebApp?.close) window.WebApp.close();
            } else {
                showScreen('main');
            }
        });
    }
}

// ============================================
// ПОКАЗ ЭКРАНОВ
// ============================================

function showScreen(screen) {
    currentScreen = screen;
    
    // Обновляем заголовок
    const headerTitle = document.getElementById('header-title');
    const titles = {
        'main': '🏠 ФРЕДИ',
        'profile': '📊 ПОРТРЕТ',
        'thought': '🧠 МЫСЛИ',
        'goals': '🎯 ЦЕЛИ',
        'mode': '🔮 РЕЖИМ'
    };
    headerTitle.textContent = titles[screen] || '🧠 ФРЕДИ';
    
    // Показываем/скрываем кнопку назад
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.style.display = screen === 'main' ? 'none' : 'flex';
    }
    
    // Загружаем контент
    const content = document.getElementById('content');
    content.classList.add('fade-out');
    
    setTimeout(() => {
        switch(screen) {
            case 'main':
                renderMainScreen(content);
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
            case 'mode':
                renderModeScreen(content);
                break;
        }
        
        content.classList.remove('fade-out');
        content.classList.add('fade-in');
        setTimeout(() => content.classList.remove('fade-in'), 300);
    }, 300);
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
// ГЛАВНЫЙ ЭКРАН (как после /start в Telegram)
// ============================================

function renderMainScreen(container) {
    const greeting = getTimeGreeting();
    const userName = app.userData.user_name || 'друг';
    
    // Эмодзи погоды (заглушка, в реальности придет из API)
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
                <button class="menu-btn" onclick="showScreen('benefits')">
                    📖 ЧТО ДАЕТ ТЕСТ
                </button>
                <button class="menu-btn" onclick="askQuestion()">
                    ❓ ЗАДАТЬ ВОПРОС
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ПРОФИЛЯ
// ============================================

function renderProfileScreen(container) {
    if (!app.userData.profile) {
        container.innerHTML = `
            <div class="error-screen">
                ❌ Профиль не найден. Пройдите тест в чате.
            </div>
        `;
        return;
    }
    
    // Парсим профиль из текста
    const profile = app.userData.profile;
    const sections = profile.split('\n\n');
    
    // Код профиля (СБ-5_ТФ-5_УБ-5_ЧВ-3)
    const profileCode = extractProfileCode(profile) || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
    
    let html = `
        <div class="profile-header">
            <div class="profile-code">${profileCode}</div>
        </div>
    `;
    
    // Добавляем каждую секцию
    sections.forEach((section, index) => {
        if (section.includes('КЛЮЧЕВАЯ')) {
            html += `
                <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                    <h2><span>🔑</span> КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА</h2>
                    <p>${cleanSection(section, 'КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА')}</p>
                </div>
            `;
        } else if (section.includes('СИЛЬНЫЕ')) {
            html += `
                <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                    <h2><span>💪</span> СИЛЬНЫЕ СТОРОНЫ</h2>
                    ${formatList(cleanSection(section, 'СИЛЬНЫЕ СТОРОНЫ'))}
                </div>
            `;
        } else if (section.includes('ЗОНЫ')) {
            html += `
                <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                    <h2><span>🎯</span> ЗОНЫ РОСТА</h2>
                    ${formatList(cleanSection(section, 'ЗОНЫ РОСТА'))}
                </div>
            `;
        } else if (section.includes('ЛОВУШКА')) {
            html += `
                <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                    <h2><span>⚠️</span> ГЛАВНАЯ ЛОВУШКА</h2>
                    <p>${cleanSection(section, 'ГЛАВНАЯ ЛОВУШКА')}</p>
                </div>
            `;
        }
    });
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН МЫСЛЕЙ ПСИХОЛОГА
// ============================================

function renderThoughtScreen(container) {
    if (!app.userData.thought) {
        container.innerHTML = `
            <div class="error-screen">
                ❌ Мысли психолога не найдены.
            </div>
        `;
        return;
    }
    
    const thought = app.userData.thought;
    const sections = thought.split('\n\n');
    
    let html = '';
    
    sections.forEach((section, index) => {
        if (section.includes('КЛЮЧЕВОЙ')) {
            html += `
                <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                    <div class="thought-title">🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ</div>
                    <p>${cleanSection(section, 'КЛЮЧЕВОЙ ЭЛЕМЕНТ')}</p>
                </div>
            `;
        } else if (section.includes('ПЕТЛЯ')) {
            html += `
                <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                    <div class="thought-title">🔄 ПЕТЛЯ</div>
                    <p>${cleanSection(section, 'ПЕТЛЯ')}</p>
                </div>
            `;
        } else if (section.includes('ТОЧКА')) {
            html += `
                <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                    <div class="thought-title">🚪 ТОЧКА ВХОДА</div>
                    <p>${cleanSection(section, 'ТОЧКА ВХОДА')}</p>
                </div>
            `;
        } else if (section.includes('ПРОГНОЗ')) {
            html += `
                <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                    <div class="thought-title">📊 ПРОГНОЗ</div>
                    <p>${cleanSection(section, 'ПРОГНОЗ')}</p>
                </div>
            `;
        }
    });
    
    container.innerHTML = html;
}

// ============================================
// ЭКРАН ЦЕЛЕЙ
// ============================================

function renderGoalsScreen(container) {
    const goals = app.userData.goals || getDefaultGoals();
    
    let html = '<div class="goals-screen">';
    html += '<h2>👇 Выберите цель:</h2>';
    
    goals.forEach(goal => {
        const difficultyClass = goal.difficulty || 'medium';
        const difficultyEmoji = {
            'easy': '🟢',
            'medium': '🟡',
            'hard': '🔴'
        }[difficultyClass] || '⚪';
        
        html += `
            <div class="goal-card" onclick="selectGoal('${goal.id}')">
                <div class="goal-difficulty ${difficultyClass}">${difficultyEmoji}</div>
                <div class="goal-info">
                    <div class="goal-name">${goal.name}</div>
                    <div class="goal-time">${goal.time || '3-4 недели'}</div>
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
// ЭКРАН ВЫБОРА РЕЖИМА
// ============================================

function renderModeScreen(container) {
    const profileCode = extractProfileCode(app.userData.profile) || 'СБ-4_ТФ-4_УБ-4_ЧВ-4';
    
    const html = `
        <div class="mode-screen">
            <div style="margin-bottom: 24px;">
                <div style="color: var(--tg-hint); font-size: 14px; margin-bottom: 4px;">Твой профиль:</div>
                <div style="font-weight: 600;">${profileCode}</div>
            </div>
            
            <div class="mode-detail-card" onclick="setMode('coach')">
                <div style="font-size: 20px; margin-bottom: 8px;">🔮 КОУЧ</div>
                <div style="color: var(--tg-hint); font-size: 14px;">
                    Помогаю найти ответы внутри тебя через открытые вопросы
                </div>
            </div>
            
            <div class="mode-detail-card" onclick="setMode('psychologist')">
                <div style="font-size: 20px; margin-bottom: 8px;">🧠 ПСИХОЛОГ</div>
                <div style="color: var(--tg-hint); font-size: 14px;">
                    Исследую глубинные паттерны, работаю с подсознанием
                </div>
            </div>
            
            <div class="mode-detail-card" onclick="setMode('trainer')">
                <div style="font-size: 20px; margin-bottom: 8px;">⚡ ТРЕНЕР</div>
                <div style="color: var(--tg-hint); font-size: 14px;">
                    Даю чёткие инструкции, структуру, план действий
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ============================================

function cleanSection(section, title) {
    return section.replace(title, '').replace(/^[:\s]+/, '').trim();
}

function formatList(text) {
    if (text.includes('•')) {
        const items = text.split('•').filter(item => item.trim());
        let html = '<ul>';
        items.forEach(item => {
            if (item.trim()) html += `<li>${item.trim()}</li>`;
        });
        html += '</ul>';
        return html;
    }
    return `<p>${text}</p>`;
}

function extractProfileCode(text) {
    if (!text) return null;
    const match = text.match(/[СБТФУБЧВ]-?\d+[_\s][СБТФУБЧВ]-?\d+[_\s][СБТФУБЧВ]-?\d+[_\s][СБТФУБЧВ]-?\d+/);
    return match ? match[0] : null;
}

// ============================================
// ОБРАБОТЧИКИ ДЕЙСТВИЙ
// ============================================

function selectMode(mode) {
    console.log('Selected mode:', mode);
    // Здесь будет вызов API для установки режима
    showScreen('mode');
}

function setMode(mode) {
    console.log('Setting mode:', mode);
    // Здесь будет вызов API
    showScreen('main');
}

function selectGoal(goalId) {
    console.log('Selected goal:', goalId);
    // Здесь будет переход к деталям цели
}

function customGoal() {
    console.log('Custom goal');
    // Здесь будет открытие формы
}

function askQuestion() {
    console.log('Ask question');
    // Здесь будет переход к чату
}

// ============================================
// ЭКСПОРТ (для глобального доступа)
// ============================================

window.showScreen = showScreen;
window.selectMode = selectMode;
window.setMode = setMode;
window.selectGoal = selectGoal;
window.customGoal = customGoal;
window.askQuestion = askQuestion;
