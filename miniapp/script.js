// Глобальные переменные
let userId = null;
let currentView = 'profile';
let userData = {};

// Звуковой эффект (тихий клик)
function playClick() {
    try {
        const audio = new Audio();
        audio.src = 'data:audio/wav;base64,//uQZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABIADAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD//////////////////////////////////////////////////////////////////8AAAAKTEFNRTMuMTAwA8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';
        audio.volume = 0.1;
        audio.play().catch(() => {});
    } catch (e) {}
}

// Приветствие в зависимости от времени суток
function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour < 6) return "Доброй ночи";
    if (hour < 12) return "Доброе утро";
    if (hour < 18) return "Добрый день";
    return "Добрый вечер";
}

// Эмодзи настроения
const moodEmojis = ['😊', '🤔', '💭', '🧘', '🌱', '🌈', '✨', '🌟'];

// Анимация печати текста
function typeWriter(element, text, speed = 20, callback = null) {
    let i = 0;
    element.innerHTML = '';
    
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        } else if (callback) {
            callback();
        }
    }
    
    type();
}

// Плавное переключение контента
async function fadeOut(element) {
    return new Promise(resolve => {
        element.classList.add('fade-out');
        setTimeout(() => {
            resolve();
        }, 300);
    });
}

async function fadeIn(element) {
    return new Promise(resolve => {
        element.classList.remove('fade-out');
        element.classList.add('fade-in');
        setTimeout(() => {
            element.classList.remove('fade-in');
            resolve();
        }, 300);
    });
}

// Расчет прогресса профиля
function calculateProfileProgress(data) {
    let total = 0;
    let filled = 0;
    
    const checks = [
        'perception_type',
        'thinking_level',
        'behavioral_levels',
        'dilts_counts',
        'deep_patterns',
        'profile_data',
        'ai_generated_profile'
    ];
    
    checks.forEach(field => {
        total++;
        if (data[field]) filled++;
    });
    
    return Math.round((filled / total) * 100);
}

// Обновление прогресс-бара
function updateProgressBar(percent) {
    const bar = document.getElementById('progress-fill');
    if (bar) {
        bar.style.width = percent + '%';
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Mini-app initialized');
    
    // Добавляем прогресс-бар в DOM
    const app = document.getElementById('app');
    const header = document.querySelector('.header');
    if (header) {
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        progressBar.innerHTML = '<div class="progress-fill" id="progress-fill" style="width: 0%"></div>';
        header.after(progressBar);
    }
    
    // Получаем параметры из URL
    const urlParams = new URLSearchParams(window.location.search);
    userId = urlParams.get('user_id');

    // Если нет user_id, показываем ошибку
    if (!userId) {
        showError('Ошибка: не передан ID пользователя');
        return;
    }

    // Получаем данные с API
    await loadUserData();

    // Настраиваем навигацию
    setupNavigation();

    // Загружаем начальный view
    loadView(currentView);
});

// Загрузка данных пользователя
async function loadUserData() {
    try {
        const response = await fetch(`/api/user-data?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки данных');

        userData = await response.json();
        
        // Случайное эмодзи настроения
        const randomMood = moodEmojis[Math.floor(Math.random() * moodEmojis.length)];

        // Обновляем приветствие
        document.getElementById('user-greeting').innerHTML = 
            `🧠 Фреди • ${getTimeGreeting()}, ${userData.user_name || 'друг'} ${randomMood}`;

    } catch (error) {
        console.error('Error loading user data:', error);
        showError('Не удалось загрузить данные пользователя');
    }
}

// Настройка навигационных кнопок
function setupNavigation() {
    const buttons = document.querySelectorAll('.nav-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            playClick(); // звук клика
            
            // Обновляем активную кнопку
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Загружаем выбранный view
            const view = btn.dataset.view;
            currentView = view;
            loadView(view);
        });
    });
}

// Загрузка выбранного view
async function loadView(view) {
    const content = document.getElementById('content');
    
    // Плавное исчезновение
    await fadeOut(content);

    // Показываем загрузку
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Загрузка...</p>
        </div>
    `;

    try {
        const response = await fetch(`/api/${view}?user_id=${userId}`);
        if (!response.ok) throw new Error('Ошибка загрузки');

        const data = await response.json();

        // Плавное появление после загрузки
        await fadeIn(content);

        // Рендерим соответствующий view
        switch(view) {
            case 'profile':
                renderProfile(content, data);
                break;
            case 'thought':
                renderThought(content, data);
                break;
            case 'ideas':
                renderIdeas(content, data);
                break;
        }
        
        // Обновляем прогресс-бар
        updateProgressBar(calculateProfileProgress(data));
        
    } catch (error) {
        console.error(`Error loading ${view}:`, error);
        await fadeIn(content);
        showError('Не удалось загрузить данные');
    }
}

// Рендеринг профиля с анимацией печати
function renderProfile(container, data) {
    let html = '';

    if (data.profile) {
        // Разбиваем текст на секции
        const sections = data.profile.split('\n\n');

        sections.forEach((section, index) => {
            if (section.includes('КЛЮЧЕВАЯ')) {
                html += `
                    <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                        <h2><span>🔑</span> Ключевая характеристика</h2>
                        <p class="typewriter-text" id="section-${index}"></p>
                    </div>
                `;
            } else if (section.includes('СИЛЬНЫЕ')) {
                html += `
                    <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                        <h2><span>💪</span> Сильные стороны</h2>
                        <p class="typewriter-text" id="section-${index}"></p>
                    </div>
                `;
            } else if (section.includes('ЗОНЫ')) {
                html += `
                    <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                        <h2><span>🎯</span> Зоны роста</h2>
                        <p class="typewriter-text" id="section-${index}"></p>
                    </div>
                `;
            } else if (section.includes('ЛОВУШКА')) {
                html += `
                    <div class="profile-section" style="animation-delay: ${index * 0.1}s">
                        <h2><span>⚠️</span> Главная ловушка</h2>
                        <p class="typewriter-text" id="section-${index}"></p>
                    </div>
                `;
            }
        });
        
        container.innerHTML = html;
        
        // Запускаем анимацию печати для каждой секции
        sections.forEach((section, index) => {
            const element = document.getElementById(`section-${index}`);
            if (element) {
                const text = section.replace(/КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА|СИЛЬНЫЕ СТОРОНЫ|ЗОНЫ РОСТА|ГЛАВНАЯ ЛОВУШКА/g, '').trim();
                setTimeout(() => {
                    typeWriter(element, text, 15);
                }, index * 300);
            }
        });
        
    } else {
        container.innerHTML = '<p>Профиль не найден</p>';
    }
}

// Рендеринг мыслей психолога
function renderThought(container, data) {
    let html = '';

    if (data.thought) {
        const sections = data.thought.split('\n\n');

        sections.forEach((section, index) => {
            if (section.includes('КЛЮЧЕВОЙ')) {
                html += `
                    <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                        <div class="thought-title">🔐 Ключевой элемент</div>
                        <p class="typewriter-text" id="thought-${index}"></p>
                    </div>
                `;
            } else if (section.includes('ПЕТЛЯ')) {
                html += `
                    <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                        <div class="thought-title">🔄 Петля</div>
                        <p class="typewriter-text" id="thought-${index}"></p>
                    </div>
                `;
            } else if (section.includes('ТОЧКА')) {
                html += `
                    <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                        <div class="thought-title">🚪 Точка входа</div>
                        <p class="typewriter-text" id="thought-${index}"></p>
                    </div>
                `;
            } else if (section.includes('ПРОГНОЗ')) {
                html += `
                    <div class="thought-block" style="animation-delay: ${index * 0.1}s">
                        <div class="thought-title">📊 Прогноз</div>
                        <p class="typewriter-text" id="thought-${index}"></p>
                    </div>
                `;
            }
        });
        
        container.innerHTML = html;
        
        // Запускаем анимацию печати
        sections.forEach((section, index) => {
            const element = document.getElementById(`thought-${index}`);
            if (element) {
                const text = section.replace(/КЛЮЧЕВОЙ ЭЛЕМЕНТ|ПЕТЛЯ|ТОЧКА ВХОДА|ПРОГНОЗ/g, '').trim();
                setTimeout(() => {
                    typeWriter(element, text, 20);
                }, index * 400);
            }
        });
        
    } else {
        container.innerHTML = '<p>Мысли психолога не найдены</p>';
    }
}

// Рендеринг идей на выходные
function renderIdeas(container, data) {
    let html = '';

    if (data.ideas && data.ideas.length > 0) {
        data.ideas.forEach((idea, index) => {
            html += `
                <div class="idea-card" style="animation-delay: ${index * 0.1}s">
                    <div class="idea-title">${idea.title || 'Идея'}</div>
                    <div class="idea-desc">${idea.description || ''}</div>
                </div>
            `;
        });
    } else {
        html = '<p>Идеи не найдены</p>';
    }

    container.innerHTML = html;
}

// Показать ошибку
function showError(message) {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="error">
            ❌ ${message}
        </div>
    `;
}
