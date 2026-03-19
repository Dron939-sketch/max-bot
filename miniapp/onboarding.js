// ========== onboarding.js ==========
// Логика экранов приветствия (онбординг)

const Onboarding = {
    // Показать первый экран (приветствие с двумя кнопками)
    showScreen1(userName = 'друг') {
        const template = document.getElementById('onboardingScreen1');
        if (!template) {
            console.error('❌ Шаблон onboardingScreen1 не найден!');
            return;
        }
        
        const clone = document.importNode(template.content, true);
        
        // Подставляем имя пользователя
        const nameSpan = clone.querySelector('#userNamePlaceholder');
        if (nameSpan) nameSpan.textContent = userName;
        
        const container = document.getElementById('screenContainer');
        if (!container) {
            console.error('❌ Контейнер screenContainer не найден!');
            return;
        }
        
        container.innerHTML = '';
        container.appendChild(clone);
        
        // Назначаем обработчики
        setTimeout(() => {
            const startBtn = document.getElementById('startTestBtn');
            const whoBtn = document.getElementById('whoAreYouBtn');
            
            if (startBtn) {
                startBtn.addEventListener('click', () => {
                    Onboarding.startTest();
                });
            }
            
            if (whoBtn) {
                whoBtn.addEventListener('click', () => {
                    Onboarding.showScreen2();
                });
            }
        }, 100);
    },

    // Показать второй экран ("А ты кто вообще")
    showScreen2() {
        const template = document.getElementById('onboardingScreen2');
        if (!template) {
            console.error('❌ Шаблон onboardingScreen2 не найден!');
            return;
        }
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        setTimeout(() => {
            const letsGoBtn = document.getElementById('letsGoBtn');
            if (letsGoBtn) {
                letsGoBtn.addEventListener('click', () => {
                    Onboarding.startTest();
                });
            }
        }, 100);
    },

    // Начать тест (переход к сбору контекста)
    startTest() {
        console.log('🚀 Начинаем тест - переход к сбору контекста');
        if (typeof Context !== 'undefined' && Context.startCollection) {
            Context.startCollection();
        } else {
            alert('Функция сбора контекста временно недоступна');
        }
    },

    // Показать экран преимуществ теста
    showBenefits() {
        const template = document.getElementById('benefitsScreen');
        if (!template) return;
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('startTestFromBenefitsBtn')?.addEventListener('click', () => {
            Onboarding.startTest();
        });
        
        document.getElementById('backToContextBtn')?.addEventListener('click', () => {
            if (App.userContext) {
                Context.showCompleteScreen(App.userContext);
            } else {
                Onboarding.showScreen1(App.userName);
            }
        });
    }
};

window.Onboarding = Onboarding;
