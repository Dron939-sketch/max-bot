// screens/profile.js
// Отображение психологического портрета

const ProfileScreen = {
    async show() {
        try {
            const profile = await api.getProfile(App.userId);
            const thought = await api.getThoughts(App.userId);
            
            let html = '';
            
            if (profile.profile) {
                html += `
                    <div class="profile-section">
                        <div class="profile-section-title">🧠 Психологический портрет</div>
                        <div class="profile-text">${this.formatProfile(profile.profile)}</div>
                    </div>
                `;
            }
            
            if (thought.thought) {
                html += `
                    <div class="profile-section">
                        <div class="profile-section-title">💭 Мысли психолога</div>
                        <div class="profile-text thought-text">${thought.thought}</div>
                    </div>
                `;
            }
            
            if (!profile.profile && !thought.thought) {
                html = `
                    <div class="profile-section">
                        <div class="profile-text">Профиль ещё не сформирован. Пройдите тест из 5 этапов.</div>
                    </div>
                `;
            }
            
            App.elements.profileContent.innerHTML = html;
            
        } catch (error) {
            console.error('Ошибка загрузки профиля:', error);
            App.elements.profileContent.innerHTML = `
                <div class="error-message">
                    Не удалось загрузить профиль. Попробуйте позже.
                </div>
            `;
        }
    },
    
    formatProfile(text) {
        if (!text) return '';
        
        // Добавляем эмодзи к разделам
        let formatted = text
            .replace(/ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ/g, '🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')
            .replace(/Тип восприятия/g, '🔍 Тип восприятия')
            .replace(/Уровень мышления/g, '📊 Уровень мышления')
            .replace(/КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА/g, '🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА')
            .replace(/СИЛЬНЫЕ СТОРОНЫ/g, '💪 СИЛЬНЫЕ СТОРОНЫ')
            .replace(/ЗОНЫ РОСТА/g, '🎯 ЗОНЫ РОСТА')
            .replace(/ГЛАВНАЯ ЛОВУШКА/g, '⚠️ ГЛАВНАЯ ЛОВУШКА');
        
        // Заменяем переносы строк на <br>
        return formatted.replace(/\n/g, '<br>');
    }
};

window.ProfileScreen = ProfileScreen;
