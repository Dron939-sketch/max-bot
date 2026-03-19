// ========== onboarding.js ==========
// Логика экранов приветствия (онбординг)

const Onboarding = {
    // Показать первый экран (приветствие с двумя кнопками)
    showScreen1(userName = 'друг') {
        const template = document.getElementById('onboardingScreen1');
        const clone = template.content.cloneNode(true);
        
        // Подставляем имя пользователя
        const nameSpan = clone.querySelector('#userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = userName;
        
        // Очищаем контейнер и вставляем
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        // Скрываем шапку чата
        document.getElementById('chatHeader').style.display = 'none';
        
        // Назначаем обработчики
        document.getElementById('startTestBtn').addEventListener('click', () => {
            Onboarding.startTest();
        });
        
        document.getElementById('whoAreYouBtn').addEventListener('click', () => {
            Onboarding.showScreen2();
        });
    },

    // Показать второй экран ("А ты кто вообще")
    showScreen2() {
        const template = document.getElementById('onboardingScreen2');
        const clone = template.content.cloneNode(true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('letsGoBtn').addEventListener('click', () => {
            Onboarding.startTest();
        });
    },

    // Начать тест (переход к сбору контекста)
    startTest() {
        console.log('🚀 Начинаем тест - переход к сбору контекста');
        Context.startCollection();
    },

    // Показать экран преимуществ теста
    showBenefits() {
        const template = document.getElementById('benefitsScreen');
        const clone = template.content.cloneNode(true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('startTestFromBenefitsBtn').addEventListener('click', () => {
            Onboarding.startTest();
        });
        
        document.getElementById('backToContextBtn').addEventListener('click', () => {
            // Возвращаемся на экран завершения контекста
            if (App.userContext) {
                Context.showCompleteScreen(App.userContext);
            } else {
                Onboarding.showScreen1(App.userName);
            }
        });
    }
};

window.Onboarding = Onboarding;
