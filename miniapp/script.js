// Глобальные переменные
let userId = null;
let currentView = 'profile';
let userData = {};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Mini-app initialized');
    
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
        
        // Обновляем приветствие
        document.getElementById('user-greeting').innerHTML = 
            `🧠 Фреди, ${userData.user_name || 'друг'}`;
            
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
    } catch (error) {
        console.error(`Error loading ${view}:`, error);
        showError('Не удалось загрузить данные');
    }
}

// Рендеринг профиля
function renderProfile(container, data) {
    let html = '';
    
    if (data.profile) {
        // Разбиваем текст на секции
        const sections = data.profile.split('\n\n');
        
        sections.forEach(section => {
            if (section.includes('КЛЮЧЕВАЯ')) {
                html += `
                    <div class="profile-section">
                        <h2><span>🔑</span> Ключевая характеристика</h2>
                        <p>${section.replace('КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('СИЛЬНЫЕ')) {
                html += `
                    <div class="profile-section">
                        <h2><span>💪</span> Сильные стороны</h2>
                        <p>${section.replace('СИЛЬНЫЕ СТОРОНЫ', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('ЗОНЫ')) {
                html += `
                    <div class="profile-section">
                        <h2><span>🎯</span> Зоны роста</h2>
                        <p>${section.replace('ЗОНЫ РОСТА', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('ЛОВУШКА')) {
                html += `
                    <div class="profile-section">
                        <h2><span>⚠️</span> Главная ловушка</h2>
                        <p>${section.replace('ГЛАВНАЯ ЛОВУШКА', '').trim()}</p>
                    </div>
                `;
            }
        });
    }
    
    container.innerHTML = html || '<p>Профиль не найден</p>';
}

// Рендеринг мыслей психолога
function renderThought(container, data) {
    let html = '';
    
    if (data.thought) {
        const sections = data.thought.split('\n\n');
        
        sections.forEach(section => {
            if (section.includes('КЛЮЧЕВОЙ')) {
                html += `
                    <div class="thought-block">
                        <div class="thought-title">🔐 Ключевой элемент</div>
                        <p>${section.replace('КЛЮЧЕВОЙ ЭЛЕМЕНТ', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('ПЕТЛЯ')) {
                html += `
                    <div class="thought-block">
                        <div class="thought-title">🔄 Петля</div>
                        <p>${section.replace('ПЕТЛЯ', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('ТОЧКА')) {
                html += `
                    <div class="thought-block">
                        <div class="thought-title">🚪 Точка входа</div>
                        <p>${section.replace('ТОЧКА ВХОДА', '').trim()}</p>
                    </div>
                `;
            } else if (section.includes('ПРОГНОЗ')) {
                html += `
                    <div class="thought-block">
                        <div class="thought-title">📊 Прогноз</div>
                        <p>${section.replace('ПРОГНОЗ', '').trim()}</p>
                    </div>
                `;
            }
        });
    }
    
    container.innerHTML = html || '<p>Мысли психолога не найдены</p>';
}

// Рендеринг идей на выходные
function renderIdeas(container, data) {
    let html = '';
    
    if (data.ideas && data.ideas.length > 0) {
        data.ideas.forEach(idea => {
            html += `
                <div class="idea-card">
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
