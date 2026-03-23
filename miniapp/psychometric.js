// ============================================
// ПСИХОМЕТРИЧЕСКИЕ ДВОЙНИКИ
// Поиск людей с похожим психологическим профилем
// Версия 1.1 - исправленная
// ============================================

class PsychometricDoubles {
    constructor(userId, userProfile) {
        this.userId = userId;
        this.userProfile = userProfile || {};
        this.doubles = [];
        this.currentDouble = null;
        this.isLoading = false;
        this.apiBase = '/api/psychometric';
    }
    
    async init() {
        console.log('🔍 Инициализация поиска психометрических двойников...');
        await this.findDoubles();
        return this;
    }
    
    // ============================================
    // ПОИСК ДВОЙНИКОВ
    // ============================================
    
    async findDoubles(limit = 10, filters = {}) {
        if (this.isLoading) return this.doubles;
        this.isLoading = true;
        
        try {
            const params = new URLSearchParams({
                user_id: this.userId,
                limit: limit,
                ...filters
            });
            
            const response = await fetch(`${this.apiBase}/find-doubles?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.doubles = data.doubles || [];
                console.log(`✅ Найдено ${this.doubles.length} психометрических двойников`);
                return this.doubles;
            } else {
                console.warn('⚠️ Не удалось найти двойников:', data.error);
                this.doubles = [];
                return [];
            }
        } catch (error) {
            console.error('❌ Ошибка поиска двойников:', error);
            this.doubles = [];
            return [];
        } finally {
            this.isLoading = false;
        }
    }
    
    // ============================================
    // ПОЛУЧИТЬ СЛУЧАЙНОГО ДВОЙНИКА
    // ============================================
    
    getRandomDouble() {
        if (this.doubles.length === 0) return null;
        const randomIndex = Math.floor(Math.random() * this.doubles.length);
        this.currentDouble = this.doubles[randomIndex];
        return this.currentDouble;
    }
    
    // ============================================
    // ПОЛУЧИТЬ ДВОЙНИКА ПО ID
    // ============================================
    
    async getDoubleById(doubleId) {
        try {
            const response = await fetch(`${this.apiBase}/double/${doubleId}?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.currentDouble = data.double;
                return this.currentDouble;
            }
            return null;
        } catch (error) {
            console.error('❌ Ошибка получения двойника:', error);
            return null;
        }
    }
    
    // ============================================
    // РАССЧИТАТЬ СОВМЕСТИМОСТЬ
    // ============================================
    
    calculateCompatibility(profile1, profile2) {
        const vectors = ['sb', 'tf', 'ub', 'chv'];
        let totalDifference = 0;
        
        for (const v of vectors) {
            const val1 = profile1?.[v] || 4;
            const val2 = profile2?.[v] || 4;
            totalDifference += Math.abs(val1 - val2);
        }
        
        // Максимальная разница 4 вектора * 5 = 20
        const compatibility = Math.max(0, Math.min(100, 100 - (totalDifference * 5)));
        
        let description = '';
        let emoji = '';
        
        if (compatibility >= 85) {
            emoji = '🌟';
            description = 'Потрясающая совместимость! Вы практически одно целое.';
        } else if (compatibility >= 70) {
            emoji = '💫';
            description = 'Отличная совместимость. Ваши профили очень похожи.';
        } else if (compatibility >= 55) {
            emoji = '✨';
            description = 'Хорошая совместимость. Много общего, но есть и различия.';
        } else if (compatibility >= 40) {
            emoji = '🌊';
            description = 'Средняя совместимость. Вы можете дополнять друг друга.';
        } else {
            emoji = '⚡';
            description = 'Низкая совместимость. Вы очень разные, но это может быть интересно.';
        }
        
        return {
            score: Math.round(compatibility),
            emoji: emoji,
            description: description,
            details: {
                sb: this._getCompatibilityDetail(profile1?.sb || 4, profile2?.sb || 4, 'реакция на давление'),
                tf: this._getCompatibilityDetail(profile1?.tf || 4, profile2?.tf || 4, 'отношение к деньгам'),
                ub: this._getCompatibilityDetail(profile1?.ub || 4, profile2?.ub || 4, 'понимание мира'),
                chv: this._getCompatibilityDetail(profile1?.chv || 4, profile2?.chv || 4, 'отношения с людьми')
            }
        };
    }
    
    _getCompatibilityDetail(val1, val2, name) {
        const diff = Math.abs(val1 - val2);
        if (diff === 0) return `✅ Идеальное совпадение по ${name}`;
        if (diff === 1) return `🟢 Близки по ${name} (разница ${diff})`;
        if (diff === 2) return `🟡 Различаетесь по ${name} (разница ${diff})`;
        return `🔴 Сильно различаетесь по ${name} (разница ${diff})`;
    }
    
    // ============================================
    // ОТПРАВИТЬ СООБЩЕНИЕ ДВОЙНИКУ
    // ============================================
    
    async sendMessage(doubleId, message) {
        if (!message || message.trim() === '') {
            console.warn('⚠️ Пустое сообщение');
            return false;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/send-message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    double_id: doubleId,
                    message: message.trim()
                })
            });
            
            const data = await response.json();
            return data.success === true;
        } catch (error) {
            console.error('❌ Ошибка отправки сообщения:', error);
            return false;
        }
    }
    
    // ============================================
    // ПОЛУЧИТЬ ДИАЛОГ С ДВОЙНИКОМ
    // ============================================
    
    async getMessages(doubleId, limit = 50) {
        try {
            const response = await fetch(`${this.apiBase}/messages?user_id=${this.userId}&double_id=${doubleId}&limit=${limit}`);
            const data = await response.json();
            if (data.success) {
                return data.messages || [];
            }
            return [];
        } catch (error) {
            console.error('❌ Ошибка получения сообщений:', error);
            return [];
        }
    }
    
    // ============================================
    // ОТМЕТИТЬ ПРОСМОТР
    // ============================================
    
    async markAsViewed(doubleId) {
        try {
            await fetch(`${this.apiBase}/mark-viewed`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    double_id: doubleId
                })
            });
        } catch (error) {
            console.error('❌ Ошибка отметки просмотра:', error);
        }
    }
    
    // ============================================
    // ПОЛУЧИТЬ СТАТИСТИКУ ДВОЙНИКОВ
    // ============================================
    
    async getStats() {
        try {
            const response = await fetch(`${this.apiBase}/stats?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                return data.stats;
            }
            return {
                total_doubles_found: 0,
                total_messages_sent: 0,
                total_messages_received: 0,
                unique_contacts: 0,
                compatibility_score: 0
            };
        } catch (error) {
            console.error('❌ Ошибка получения статистики:', error);
            return null;
        }
    }
    
    // ============================================
    // ОТРИСОВКА КАРТОЧКИ ДВОЙНИКА
    // ============================================
    
    renderDoubleCard(double, compatibility = null) {
        if (!compatibility) {
            compatibility = this.calculateCompatibility(this.userProfile, double.profile);
        }
        
        const avatarUrl = double.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(double.first_name || '?')}&background=248bf2&color=fff&size=128&bold=true`;
        
        return `
            <div class="double-card" data-double-id="${double.id}">
                <div class="double-avatar">
                    <img src="${avatarUrl}" alt="${double.first_name || 'Двойник'}">
                    <div class="double-compatibility-badge" style="background: ${this._getCompatibilityColor(compatibility.score)}">
                        ${compatibility.emoji} ${compatibility.score}%
                    </div>
                </div>
                <div class="double-info">
                    <div class="double-name">${this._escapeHtml(double.first_name || 'Двойник')} ${this._escapeHtml(double.last_name || '')}</div>
                    <div class="double-details">
                        <span class="double-age">${double.age || '?'} лет</span>
                        <span class="double-gender">${double.gender === 'male' ? '👨' : double.gender === 'female' ? '👩' : '👤'}</span>
                        <span class="double-city">${this._escapeHtml(double.city || '?')}</span>
                    </div>
                    <div class="double-profile">
                        <span class="profile-badge">${this._escapeHtml(double.profile_code || 'СБ-4_ТФ-4_УБ-4_ЧВ-4')}</span>
                    </div>
                    <div class="double-compatibility-desc">${this._escapeHtml(compatibility.description)}</div>
                </div>
                <div class="double-actions">
                    <button class="double-message-btn" data-double-id="${double.id}">
                        💬 Написать
                    </button>
                    <button class="double-details-btn" data-double-id="${double.id}">
                        👤 Подробнее
                    </button>
                </div>
            </div>
        `;
    }
    
    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    _getCompatibilityColor(score) {
        if (score >= 80) return '#4caf50';
        if (score >= 60) return '#8bc34a';
        if (score >= 40) return '#ffc107';
        if (score >= 20) return '#ff9800';
        return '#f44336';
    }
    
    // ============================================
    // ОТРИСОВКА МОДАЛЬНОГО ОКНА ЧАТА
    // ============================================
    
    renderChatModal(double) {
        const compatibility = double.compatibility || this.calculateCompatibility(this.userProfile, double.profile);
        
        return `
            <div class="modal-overlay" id="psychometricChatModal">
                <div class="modal-content chat-modal">
                    <div class="modal-header">
                        <div class="modal-header-info">
                            <div class="chat-avatar-small">
                                <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(double.first_name || '?')}&background=248bf2&color=fff&size=64" alt="${double.first_name || 'Двойник'}">
                            </div>
                            <div class="chat-header-info">
                                <div class="chat-name">${this._escapeHtml(double.first_name || 'Двойник')} ${this._escapeHtml(double.last_name || '')}</div>
                                <div class="chat-status">Совместимость: ${compatibility.score}%</div>
                            </div>
                        </div>
                        <button class="modal-close" id="closeChatModal">✕</button>
                    </div>
                    <div class="modal-body chat-messages" id="chatMessages">
                        <div class="messages-list" id="messagesList">
                            <div class="message system-message">
                                🤝 Совместимость: ${compatibility.emoji} ${compatibility.score}% — ${compatibility.description}
                            </div>
                            <div class="message system-message">
                                💬 Напишите первое сообщение, чтобы начать общение
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="chat-input-area">
                            <input type="text" class="chat-input" id="chatMessageInput" placeholder="Напишите сообщение..." autocomplete="off">
                            <button class="chat-send-btn" id="sendChatMessage">➡️</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // ============================================
    // ОТРИСОВКА СПИСКА ВСЕХ ДВОЙНИКОВ
    // ============================================
    
    renderDoublesList(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`❌ Контейнер ${containerId} не найден`);
            return;
        }
        
        if (this.doubles.length === 0) {
            container.innerHTML = `
                <div class="doubles-empty">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-title">Пока нет двойников</div>
                    <div class="empty-text">Пройдите тест, чтобы найти людей с похожим психологическим профилем</div>
                    <button class="btn-primary" onclick="window.location.href='/test'">Пройти тест</button>
                </div>
            `;
            return;
        }
        
        let html = '<div class="doubles-grid">';
        for (const double of this.doubles) {
            const compatibility = this.calculateCompatibility(this.userProfile, double.profile);
            html += this.renderDoubleCard(double, compatibility);
        }
        html += '</div>';
        
        container.innerHTML = html;
        
        // Добавляем обработчики событий
        this._attachEventListeners(container);
    }
    
    _attachEventListeners(container) {
        // Кнопки "Написать"
        container.querySelectorAll('.double-message-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const doubleId = parseInt(btn.dataset.doubleId);
                const double = this.doubles.find(d => d.id === doubleId);
                if (double) {
                    await this.openChat(double);
                }
            });
        });
        
        // Кнопки "Подробнее"
        container.querySelectorAll('.double-details-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const doubleId = parseInt(btn.dataset.doubleId);
                const double = this.doubles.find(d => d.id === doubleId);
                if (double) {
                    this.showDoubleDetails(double);
                }
            });
        });
    }
    
    // ============================================
    // ОТКРЫТЬ ЧАТ С ДВОЙНИКОМ
    // ============================================
    
    async openChat(double) {
        // Отмечаем как просмотренный
        await this.markAsViewed(double.id);
        
        // Загружаем историю сообщений
        const messages = await this.getMessages(double.id);
        
        // Создаем модальное окно
        const modalHtml = this.renderChatModal(double);
        
        // Удаляем старое модальное окно, если есть
        const existingModal = document.getElementById('psychometricChatModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Добавляем новое
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('psychometricChatModal');
        const messagesList = document.getElementById('messagesList');
        
        // Загружаем сообщения
        if (messages && messages.length > 0) {
            messagesList.innerHTML = '';
            for (const msg of messages) {
                const isFromMe = msg.from === this.userId;
                messagesList.insertAdjacentHTML('beforeend', this._renderMessage(msg, isFromMe));
            }
            messagesList.scrollTop = messagesList.scrollHeight;
        }
        
        // Обработчики
        const closeBtn = document.getElementById('closeChatModal');
        const sendBtn = document.getElementById('sendChatMessage');
        const input = document.getElementById('chatMessageInput');
        
        const closeModal = () => {
            modal.remove();
        };
        
        const sendMessage = async () => {
            const message = input.value.trim();
            if (!message) return;
            
            // Отправляем сообщение
            const success = await this.sendMessage(double.id, message);
            
            if (success) {
                // Добавляем сообщение в чат
                messagesList.insertAdjacentHTML('beforeend', this._renderMessage({
                    from: this.userId,
                    to: double.id,
                    message: message,
                    timestamp: new Date().toISOString()
                }, true));
                
                input.value = '';
                messagesList.scrollTop = messagesList.scrollHeight;
            } else {
                alert('Не удалось отправить сообщение. Попробуйте позже.');
            }
        };
        
        closeBtn.addEventListener('click', closeModal);
        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Закрытие по клику вне модального окна
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }
    
    _renderMessage(message, isFromMe) {
        const time = message.timestamp ? new Date(message.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';
        const messageClass = isFromMe ? 'message-out' : 'message-in';
        
        return `
            <div class="message ${messageClass}">
                <div class="message-bubble">
                    <div class="message-text">${this._escapeHtml(message.message)}</div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    }
    
    // ============================================
    // ПОКАЗАТЬ ДЕТАЛИ ДВОЙНИКА
    // ============================================
    
    showDoubleDetails(double) {
        const compatibility = this.calculateCompatibility(this.userProfile, double.profile);
        
        const modalHtml = `
            <div class="modal-overlay" id="doubleDetailsModal">
                <div class="modal-content double-details-modal">
                    <div class="modal-header">
                        <div class="modal-header-info">
                            <div class="double-details-avatar">
                                <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(double.first_name || '?')}&background=248bf2&color=fff&size=128" alt="${double.first_name}">
                            </div>
                            <div class="double-details-name">
                                <h2>${this._escapeHtml(double.first_name || 'Двойник')} ${this._escapeHtml(double.last_name || '')}</h2>
                                <div class="compatibility-badge-large" style="background: ${this._getCompatibilityColor(compatibility.score)}">
                                    ${compatibility.emoji} Совместимость: ${compatibility.score}%
                                </div>
                            </div>
                        </div>
                        <button class="modal-close" id="closeDetailsModal">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="double-details-section">
                            <h3>📊 Психометрический профиль</h3>
                            <div class="profile-code-large">${this._escapeHtml(double.profile_code || 'СБ-4_ТФ-4_УБ-4_ЧВ-4')}</div>
                            <div class="vectors-details">
                                <div class="vector-item">
                                    <span class="vector-name">🛡️ СБ (Безопасность):</span>
                                    <span class="vector-value">${double.profile?.sb || 4}/5</span>
                                </div>
                                <div class="vector-item">
                                    <span class="vector-name">💰 ТФ (Деньги):</span>
                                    <span class="vector-value">${double.profile?.tf || 4}/5</span>
                                </div>
                                <div class="vector-item">
                                    <span class="vector-name">🌍 УБ (Понимание мира):</span>
                                    <span class="vector-value">${double.profile?.ub || 4}/5</span>
                                </div>
                                <div class="vector-item">
                                    <span class="vector-name">💕 ЧВ (Отношения):</span>
                                    <span class="vector-value">${double.profile?.chv || 4}/5</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="double-details-section">
                            <h3>🔍 Детали совместимости</h3>
                            <ul class="compatibility-details">
                                <li>${compatibility.details.sb}</li>
                                <li>${compatibility.details.tf}</li>
                                <li>${compatibility.details.ub}</li>
                                <li>${compatibility.details.chv}</li>
                            </ul>
                        </div>
                        
                        <div class="double-details-section">
                            <h3>📍 Основная информация</h3>
                            <div class="info-grid">
                                <div class="info-item"><span class="info-label">Город:</span> ${this._escapeHtml(double.city || 'Не указан')}</div>
                                <div class="info-item"><span class="info-label">Возраст:</span> ${double.age || 'Не указан'} лет</div>
                                <div class="info-item"><span class="info-label">Пол:</span> ${double.gender === 'male' ? 'Мужчина' : double.gender === 'female' ? 'Женщина' : 'Не указан'}</div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-primary" id="writeToDoubleBtn">💬 Написать сообщение</button>
                        <button class="btn-secondary" id="closeDetailsBtn">Закрыть</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('doubleDetailsModal');
        
        const close = () => modal.remove();
        
        document.getElementById('closeDetailsModal')?.addEventListener('click', close);
        document.getElementById('closeDetailsBtn')?.addEventListener('click', close);
        document.getElementById('writeToDoubleBtn')?.addEventListener('click', () => {
            close();
            this.openChat(double);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) close();
        });
    }
    
    // ============================================
    // ПОЛУЧИТЬ ВСЕХ ДВОЙНИКОВ
    // ============================================
    
    getAllDoubles() {
        return this.doubles;
    }
    
    // ============================================
    // ОЧИСТИТЬ КЭШ
    // ============================================
    
    clearCache() {
        this.doubles = [];
        this.currentDouble = null;
        console.log('🧹 Кэш психометрических двойников очищен');
    }
}

// Глобальный экземпляр
window.PsychometricDoubles = PsychometricDoubles;

console.log('✅ Психометрические двойники загружены (версия 1.1)');
