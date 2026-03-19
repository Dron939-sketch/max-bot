// ========== context.js ==========
// Логика сбора контекста (город, пол, возраст)

const Context = {
    currentStep: 'city',
    data: {
        city: null,
        gender: null,
        age: null,
        weather: null
    },

    startCollection() {
        this.currentStep = 'city';
        this.showCityScreen();
    },

    showCityScreen() {
        const template = document.getElementById('contextCityScreen');
        if (!template) {
            alert('Экран города временно недоступен');
            return;
        }
        
        const clone = document.importNode(template.content, true);
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('submitCityBtn')?.addEventListener('click', () => {
            const city = document.getElementById('cityInput')?.value.trim();
            if (city) {
                this.saveCity(city);
            } else {
                alert('Введите название города');
            }
        });
        
        document.getElementById('skipContextBtn')?.addEventListener('click', () => {
            this.completeContext(true);
        });
    },

    async saveCity(city) {
        this.data.city = city;
        this.currentStep = 'gender';
        this.showGenderScreen();
    },

    showGenderScreen() {
        const template = document.getElementById('contextGenderScreen');
        const clone = document.importNode(template.content, true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('genderMaleBtn')?.addEventListener('click', () => {
            this.saveGender('male');
        });
        
        document.getElementById('genderFemaleBtn')?.addEventListener('click', () => {
            this.saveGender('female');
        });
        
        document.getElementById('skipGenderBtn')?.addEventListener('click', () => {
            this.currentStep = 'age';
            this.showAgeScreen();
        });
    },

    saveGender(gender) {
        this.data.gender = gender;
        this.currentStep = 'age';
        this.showAgeScreen();
    },

    showAgeScreen() {
        const template = document.getElementById('contextAgeScreen');
        const clone = document.importNode(template.content, true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('submitAgeBtn')?.addEventListener('click', () => {
            const age = parseInt(document.getElementById('ageInput')?.value);
            if (age && age > 0 && age < 120) {
                this.saveAge(age);
            } else {
                alert('Введите корректный возраст (1-120)');
            }
        });
        
        document.getElementById('skipAgeBtn')?.addEventListener('click', () => {
            this.completeContext();
        });
    },

    saveAge(age) {
        this.data.age = age;
        this.completeContext();
    },

    async completeContext(skipped = false) {
        // Сохраняем контекст (имитация)
        App.userContext = this.data;
        
        // Обновляем статус
        const statusEl = document.getElementById('userStatus');
        if (statusEl && this.data.city) {
            statusEl.textContent = `📍 ${this.data.city}`;
        }
        
        this.showCompleteScreen(this.data);
    },

    showCompleteScreen(contextData) {
        const template = document.getElementById('contextCompleteScreen');
        const clone = document.importNode(template.content, true);
        
        // Заполняем информацию
        const citySpan = clone.querySelector('#infoCity');
        if (citySpan) citySpan.textContent = contextData.city || 'не указан';
        
        const genderSpan = clone.querySelector('#infoGender');
        if (genderSpan) {
            let genderText = 'не указан';
            if (contextData.gender === 'male') genderText = 'Мужчина';
            if (contextData.gender === 'female') genderText = 'Женщина';
            genderSpan.textContent = genderText;
        }
        
        const ageSpan = clone.querySelector('#infoAge');
        if (ageSpan) ageSpan.textContent = contextData.age || '—';
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('startRealTestBtn')?.addEventListener('click', () => {
            alert('Этап 1 теста (будет добавлен)');
        });
        
        document.getElementById('whatTestGivesBtn')?.addEventListener('click', () => {
            if (typeof Onboarding !== 'undefined' && Onboarding.showBenefits) {
                Onboarding.showBenefits();
            }
        });
    }
};

window.Context = Context;
