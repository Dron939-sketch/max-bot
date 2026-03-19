// ========== context.js ==========
// Логика сбора контекста (город, пол, возраст)

const Context = {
    // Текущий этап сбора
    currentStep: 'city', // city, gender, age
    
    // Данные контекста
    data: {
        city: null,
        gender: null,
        age: null,
        weather: null
    },

    // Начать сбор контекста
    startCollection() {
        this.currentStep = 'city';
        this.showCityScreen();
    },

    // Экран ввода города
    showCityScreen() {
        const template = document.getElementById('contextCityScreen');
        const clone = template.content.cloneNode(true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        const input = document.getElementById('cityInput');
        const submitBtn = document.getElementById('submitCityBtn');
        const skipBtn = document.getElementById('skipContextBtn');
        
        submitBtn.addEventListener('click', () => {
            const city = input.value.trim();
            if (city) {
                this.saveCity(city);
            } else {
                alert('Введите название города');
            }
        });
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const city = input.value.trim();
                if (city) {
                    this.saveCity(city);
                }
            }
        });
        
        skipBtn.addEventListener('click', () => {
            this.skipContext();
        });
    },

    // Сохранить город
    async saveCity(city) {
        this.data.city = city;
        
        // Получаем погоду
        try {
            const weatherData = await api.getWeather(city);
            this.data.weather = weatherData;
        } catch (e) {
            console.log('Не удалось получить погоду');
        }
        
        this.currentStep = 'gender';
        this.showGenderScreen();
    },

    // Экран выбора пола
    showGenderScreen() {
        const template = document.getElementById('contextGenderScreen');
        const clone = template.content.cloneNode(true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        document.getElementById('genderMaleBtn').addEventListener('click', () => {
            this.saveGender('male');
        });
        
        document.getElementById('genderFemaleBtn').addEventListener('click', () => {
            this.saveGender('female');
        });
        
        document.getElementById('skipGenderBtn').addEventListener('click', () => {
            this.skipGender();
        });
    },

    // Сохранить пол
    saveGender(gender) {
        this.data.gender = gender;
        this.currentStep = 'age';
        this.showAgeScreen();
    },

    // Экран ввода возраста
    showAgeScreen() {
        const template = document.getElementById('contextAgeScreen');
        const clone = template.content.cloneNode(true);
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        const input = document.getElementById('ageInput');
        const submitBtn = document.getElementById('submitAgeBtn');
        const skipBtn = document.getElementById('skipAgeBtn');
        
        submitBtn.addEventListener('click', () => {
            const age = parseInt(input.value);
            if (age && age > 0 && age < 120) {
                this.saveAge(age);
            } else {
                alert('Введите корректный возраст (1-120)');
            }
        });
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const age = parseInt(input.value);
                if (age && age > 0 && age < 120) {
                    this.saveAge(age);
                }
            }
        });
        
        skipBtn.addEventListener('click', () => {
            this.skipAge();
        });
    },

    // Сохранить возраст
    saveAge(age) {
        this.data.age = age;
        this.completeContext();
    },

    // Пропустить контекст
    skipContext() {
        // Просто переходим к тесту без контекста
        this.completeContext(true);
    },

    skipGender() {
        this.currentStep = 'age';
        this.showAgeScreen();
    },

    skipAge() {
        this.completeContext();
    },

    // Завершить сбор контекста
    async completeContext(skipped = false) {
        // Сохраняем контекст на сервере
        try {
            await api.saveContext(App.userId, this.data);
            App.userContext = this.data;
            
            // Обновляем статус в левой панели
            if (this.data.city) {
                document.getElementById('userStatus').textContent = `📍 ${this.data.city}`;
            }
            
        } catch (e) {
            console.error('Ошибка сохранения контекста:', e);
        }
        
        // Показываем экран завершения
        this.showCompleteScreen(this.data);
    },

    // Показать экран завершения сбора контекста
    showCompleteScreen(contextData) {
        const template = document.getElementById('contextCompleteScreen');
        const clone = template.content.cloneNode(true);
        
        // Заполняем информацию
        clone.querySelector('#infoCity').textContent = contextData.city || 'не указан';
        
        let genderText = 'не указан';
        if (contextData.gender === 'male') genderText = 'Мужчина';
        if (contextData.gender === 'female') genderText = 'Женщина';
        clone.querySelector('#infoGender').textContent = genderText;
        
        clone.querySelector('#infoAge').textContent = contextData.age || '—';
        
        if (contextData.weather) {
            clone.querySelector('#infoWeather').innerHTML = 
                `${contextData.weather.icon} Погода: ${contextData.weather.description}, ${contextData.weather.temp}°C`;
        }
        
        const container = document.getElementById('screenContainer');
        container.innerHTML = '';
        container.appendChild(clone);
        
        // Обработчики кнопок
        document.getElementById('startRealTestBtn').addEventListener('click', () => {
            // Переход к 1-му этапу теста
            Test.startStage1();
        });
        
        document.getElementById('whatTestGivesBtn').addEventListener('click', () => {
            Onboarding.showBenefits();
        });
        
        document.getElementById('askQuestionPreBtn').addEventListener('click', () => {
            // Показываем экран вопроса до теста
            alert('Функция вопросов до теста будет добавлена');
        });
    }
};

window.Context = Context;
