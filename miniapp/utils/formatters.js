// utils/formatters.js
// Утилиты для форматирования текста

const Formatters = {
    // Форматирование текста с Markdown
    markdown(text) {
        if (!text) return '';
        
        let formatted = text
            // Жирный
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Курсив
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Код
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Зачеркнутый
            .replace(/~(.*?)~/g, '<del>$1</del>')
            // Списки
            .replace(/^[•\-] (.*?)$/gm, '<li>$1</li>')
            // Переносы
            .replace(/\n/g, '<br>');
        
        // Оборачиваем списки
        formatted = formatted.replace(/(<li>.*?<\/li>)\n(?!<li>)/gs, '<ul>$1</ul>');
        
        return formatted;
    },
    
    // Обрезка текста (для превью)
    truncate(text, length = 100) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    },
    
    // Эмодзи для режимов
    getModeEmoji(mode) {
        const emojis = {
            'coach': '🔮',
            'psychologist': '🧠',
            'trainer': '⚡'
        };
        return emojis[mode] || '🎭';
    },
    
    // Название режима
    getModeName(mode) {
        const names = {
            'coach': 'Коуч',
            'psychologist': 'Психолог',
            'trainer': 'Тренер'
        };
        return names[mode] || mode;
    }
};

window.Formatters = Formatters;
