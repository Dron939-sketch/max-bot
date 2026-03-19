// components/message.js
// Компоненты для работы с сообщениями

const MessageComponent = {
    // Создать сообщение бота
    createBotMessage(text, time, options = {}) {
        const template = document.getElementById('botMessageTemplate');
        const clone = template.content.cloneNode(true);
        const messageDiv = clone.querySelector('.message');
        
        messageDiv.id = `msg-${Date.now()}-${Math.random()}`;
        
        const messageText = clone.querySelector('.message-text');
        messageText.innerHTML = this.formatText(text);
        
        clone.querySelector('.message-time').textContent = time || this.getCurrentTime();
        
        if (options.isThought) {
            messageDiv.classList.add('thought-message');
            clone.querySelector('.message-sender').textContent = 'Мысли психолога';
        }
        
        return clone;
    },
    
    // Создать сообщение пользователя
    createUserMessage(text, time) {
        const template = document.getElementById('userMessageTemplate');
        const clone = template.content.cloneNode(true);
        
        clone.querySelector('.message-text').textContent = text;
        clone.querySelector('.message-time').textContent = time || this.getCurrentTime();
        
        return clone;
    },
    
    // Форматирование текста
    formatText(text) {
        if (!text) return '';
        
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        return formatted;
    },
    
    // Текущее время
    getCurrentTime() {
        const now = new Date();
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    }
};

window.MessageComponent = MessageComponent;
