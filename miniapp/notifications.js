// ============================================
// PUSH-УВЕДОМЛЕНИЯ И SERVICE WORKER
// Версия 1.0 - Вовлечение пользователя
// ============================================

class NotificationManager {
    constructor(userId, userName = 'Друг') {
        this.userId = userId;
        this.userName = userName;
        this.isSupported = 'Notification' in window && 'serviceWorker' in navigator;
        this.isSubscribed = false;
        this.swRegistration = null;
        this.vapidPublicKey = null;
        this.permission = 'default';
        this.notifications = [];
        this.unreadCount = 0;
        
        // Настройки уведомлений
        this.settings = {
            enabled: true,
            reminders: true,
            challenges: true,
            messages: true,
            dailyDigest: true,
            quietHours: {
                enabled: false,
                start: 22,
                end: 8
            }
        };
        
        this.init();
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    async init() {
        console.log('🔔 Инициализация системы уведомлений...');
        
        if (!this.isSupported) {
            console.warn('⚠️ Push-уведомления не поддерживаются в этом браузере');
            return;
        }
        
        await this.loadSettings();
        await this.registerServiceWorker();
        await this.checkPermission();
        await this.loadNotifications();
        
        console.log('✅ Система уведомлений готова');
        return this;
    }
    
    // ============================================
    // SERVICE WORKER
    // ============================================
    
    async registerServiceWorker() {
        try {
            this.swRegistration = await navigator.serviceWorker.register('/sw.js');
            console.log('✅ Service Worker зарегистрирован');
            
            // Проверяем подписку
            const subscription = await this.swRegistration.pushManager.getSubscription();
            this.isSubscribed = subscription !== null;
            
            // Получаем VAPID ключ
            await this.getVapidKey();
            
        } catch (error) {
            console.error('❌ Ошибка регистрации Service Worker:', error);
        }
    }
    
    async getVapidKey() {
        try {
            const response = await fetch('/api/notification/vapid-key');
            const data = await response.json();
            this.vapidPublicKey = data.key;
        } catch (error) {
            console.warn('Ошибка получения VAPID ключа:', error);
        }
    }
    
    // ============================================
    // РАЗРЕШЕНИЯ
    // ============================================
    
    async checkPermission() {
        if (Notification.permission === 'granted') {
            this.permission = 'granted';
            await this.subscribe();
        } else if (Notification.permission === 'denied') {
            this.permission = 'denied';
        } else {
            this.permission = 'default';
        }
    }
    
    async requestPermission() {
        if (this.permission === 'granted') return true;
        if (this.permission === 'denied') return false;
        
        try {
            const permission = await Notification.requestPermission();
            this.permission = permission;
            
            if (permission === 'granted') {
                await this.subscribe();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Ошибка запроса разрешения:', error);
            return false;
        }
    }
    
    // ============================================
    // ПОДПИСКА НА PUSH
    // ============================================
    
    async subscribe() {
        if (!this.swRegistration || !this.vapidPublicKey) return;
        
        try {
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            
            await this.sendSubscriptionToServer(subscription);
            this.isSubscribed = true;
            console.log('✅ Подписка на push-уведомления оформлена');
            
        } catch (error) {
            console.error('❌ Ошибка подписки:', error);
        }
    }
    
    async unsubscribe() {
        if (!this.swRegistration) return;
        
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (subscription) {
                await subscription.unsubscribe();
                await this.sendUnsubscriptionToServer();
                this.isSubscribed = false;
                console.log('✅ Отписка от push-уведомлений выполнена');
            }
        } catch (error) {
            console.error('❌ Ошибка отписки:', error);
        }
    }
    
    async sendSubscriptionToServer(subscription) {
        try {
            await fetch('/api/notification/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    subscription: subscription
                })
            });
        } catch (error) {
            console.error('Ошибка отправки подписки на сервер:', error);
        }
    }
    
    async sendUnsubscriptionToServer() {
        try {
            await fetch('/api/notification/unsubscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId
                })
            });
        } catch (error) {
            console.error('Ошибка отправки отписки на сервер:', error);
        }
    }
    
    // ============================================
    // НАСТРОЙКИ
    // ============================================
    
    async loadSettings() {
        try {
            const response = await fetch(`/api/notification/settings?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.settings = data.settings;
            }
        } catch (error) {
            // Загружаем из localStorage
            const saved = localStorage.getItem(`notification_settings_${this.userId}`);
            if (saved) {
                this.settings = JSON.parse(saved);
            }
        }
    }
    
    async saveSettings() {
        try {
            await fetch('/api/notification/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    settings: this.settings
                })
            });
        } catch (error) {
            localStorage.setItem(`notification_settings_${this.userId}`, JSON.stringify(this.settings));
        }
    }
    
    updateSetting(key, value) {
        if (key in this.settings) {
            this.settings[key] = value;
            this.saveSettings();
            this.notifyListeners('settings_changed', { key, value });
        }
    }
    
    // ============================================
    // ОТПРАВКА УВЕДОМЛЕНИЙ
    // ============================================
    
    async sendNotification(title, options = {}) {
        if (!this.settings.enabled) return false;
        
        // Проверяем тихие часы
        if (this.isQuietHours()) return false;
        
        // Проверяем тип уведомления
        const type = options.type || 'general';
        if (!this.settings[type] && type !== 'general') return false;
        
        try {
            // Отправляем через сервер (для push)
            await fetch('/api/notification/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    title: title,
                    body: options.body || '',
                    icon: options.icon || '/icon-192.png',
                    data: options.data || {},
                    type: type
                })
            });
            
            // Сохраняем в историю
            this.addToHistory({
                title,
                body: options.body,
                type,
                timestamp: Date.now(),
                read: false
            });
            
            return true;
        } catch (error) {
            console.error('Ошибка отправки уведомления:', error);
            return false;
        }
    }
    
    // Локальное уведомление (без сервера)
    showLocalNotification(title, options = {}) {
        if (!this.settings.enabled) return;
        if (this.isQuietHours()) return;
        
        const type = options.type || 'general';
        if (!this.settings[type] && type !== 'general') return;
        
        if (Notification.permission === 'granted') {
            const notification = new Notification(title, {
                body: options.body || '',
                icon: options.icon || '/icon-192.png',
                data: options.data || {},
                silent: options.silent || false,
                vibrate: options.vibrate || [200, 100, 200]
            });
            
            notification.onclick = (event) => {
                event.preventDefault();
                window.focus();
                if (options.onClick) options.onClick();
                notification.close();
            };
            
            setTimeout(() => notification.close(), 5000);
            
            // Сохраняем в историю
            this.addToHistory({
                title,
                body: options.body,
                type,
                timestamp: Date.now(),
                read: false
            });
        }
    }
    
    // ============================================
    // ТИПОВЫЕ УВЕДОМЛЕНИЯ
    // ============================================
    
    sendReminder() {
        this.sendNotification('🧠 Напоминание от Фреди', {
            body: 'Как дела? Не забывайте заботиться о себе!',
            type: 'reminders',
            icon: '/icon-192.png'
        });
    }
    
    sendChallengeComplete(challengeName, xp) {
        this.sendNotification('🏆 Челлендж выполнен!', {
            body: `${challengeName} +${xp} XP`,
            type: 'challenges',
            icon: '/icon-192.png',
            data: { type: 'challenge', name: challengeName }
        });
    }
    
    sendLevelUp(level) {
        this.sendNotification('🎉 Новый уровень!', {
            body: `Поздравляем! Вы достигли ${level} уровня!`,
            type: 'challenges',
            icon: '/icon-192.png'
        });
    }
    
    sendDailyDigest() {
        this.sendNotification('📊 Ежедневный дайджест', {
            body: 'Посмотрите, что нового произошло сегодня',
            type: 'dailyDigest',
            icon: '/icon-192.png'
        });
    }
    
    sendNewMessage(fromName) {
        this.sendNotification('💬 Новое сообщение', {
            body: `${fromName} написал(а) вам`,
            type: 'messages',
            icon: '/icon-192.png',
            data: { type: 'message', from: fromName }
        });
    }
    
    // ============================================
    // ИСТОРИЯ УВЕДОМЛЕНИЙ
    // ============================================
    
    async loadNotifications() {
        try {
            const response = await fetch(`/api/notification/history?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.notifications = data.notifications;
                this.unreadCount = this.notifications.filter(n => !n.read).length;
            }
        } catch (error) {
            const saved = localStorage.getItem(`notifications_${this.userId}`);
            if (saved) {
                this.notifications = JSON.parse(saved);
                this.unreadCount = this.notifications.filter(n => !n.read).length;
            }
        }
    }
    
    addToHistory(notification) {
        this.notifications.unshift(notification);
        this.unreadCount++;
        
        // Ограничиваем историю 100 записями
        if (this.notifications.length > 100) {
            this.notifications.pop();
        }
        
        this.saveHistory();
        this.notifyListeners('new_notification', notification);
    }
    
    async saveHistory() {
        try {
            await fetch('/api/notification/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    notifications: this.notifications
                })
            });
        } catch (error) {
            localStorage.setItem(`notifications_${this.userId}`, JSON.stringify(this.notifications));
        }
    }
    
    markAsRead(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification && !notification.read) {
            notification.read = true;
            this.unreadCount--;
            this.saveHistory();
            this.notifyListeners('notification_read', notification);
        }
    }
    
    markAllAsRead() {
        this.notifications.forEach(n => n.read = true);
        this.unreadCount = 0;
        this.saveHistory();
        this.notifyListeners('all_read');
    }
    
    // ============================================
    // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    // ============================================
    
    isQuietHours() {
        if (!this.settings.quietHours.enabled) return false;
        
        const now = new Date();
        const currentHour = now.getHours();
        const { start, end } = this.settings.quietHours;
        
        if (start <= end) {
            return currentHour >= start && currentHour < end;
        } else {
            return currentHour >= start || currentHour < end;
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    // ============================================
    // ОТРИСОВКА
    // ============================================
    
    renderWidget() {
        return `
            <div class="notifications-widget">
                <div class="widget-header">
                    <div class="widget-title">
                        <span class="widget-icon">🔔</span>
                        Уведомления
                        ${this.unreadCount > 0 ? `<span class="unread-badge">${this.unreadCount}</span>` : ''}
                    </div>
                    <button class="notifications-settings-btn" id="notifSettingsBtn">⚙️</button>
                </div>
                
                <div class="notifications-list">
                    ${this.notifications.slice(0, 5).map(n => this._renderNotificationItem(n)).join('')}
                    ${this.notifications.length === 0 ? '<div class="empty-notifications">Нет уведомлений</div>' : ''}
                </div>
                
                ${this.notifications.length > 5 ? `
                    <button class="show-all-notif-btn">Показать все →</button>
                ` : ''}
            </div>
        `;
    }
    
    _renderNotificationItem(notification) {
        const timeAgo = this.getTimeAgo(notification.timestamp);
        const unreadClass = notification.read ? '' : 'unread';
        
        return `
            <div class="notification-item ${unreadClass}" data-notif-id="${notification.id}">
                <div class="notification-icon">${this._getNotificationIcon(notification.type)}</div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-body">${notification.body || ''}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
            </div>
        `;
    }
    
    _getNotificationIcon(type) {
        const icons = {
            reminders: '🧠',
            challenges: '🏆',
            messages: '💬',
            dailyDigest: '📊',
            general: '🔔'
        };
        return icons[type] || '🔔';
    }
    
    getTimeAgo(timestamp) {
        const seconds = Math.floor((Date.now() - timestamp) / 1000);
        
        if (seconds < 60) return 'только что';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} мин назад`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} ч назад`;
        const days = Math.floor(hours / 24);
        return `${days} д назад`;
    }
    
    renderSettingsModal() {
        return `
            <div class="modal-overlay" id="notifSettingsModal">
                <div class="modal-content settings-modal">
                    <div class="modal-header">
                        <h3>⚙️ Настройки уведомлений</h3>
                        <button class="modal-close" id="closeNotifSettings">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.enabled ? 'checked' : ''} id="notifEnabled">
                                <span>Включить уведомления</span>
                            </label>
                        </div>
                        
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.reminders ? 'checked' : ''} id="notifReminders">
                                <span>🧠 Напоминания</span>
                            </label>
                        </div>
                        
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.challenges ? 'checked' : ''} id="notifChallenges">
                                <span>🏆 Челленджи</span>
                            </label>
                        </div>
                        
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.messages ? 'checked' : ''} id="notifMessages">
                                <span>💬 Сообщения</span>
                            </label>
                        </div>
                        
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.dailyDigest ? 'checked' : ''} id="notifDailyDigest">
                                <span>📊 Ежедневный дайджест</span>
                            </label>
                        </div>
                        
                        <div class="setting-item">
                            <label class="setting-label">
                                <input type="checkbox" ${this.settings.quietHours.enabled ? 'checked' : ''} id="quietHoursEnabled">
                                <span>🌙 Тихие часы</span>
                            </label>
                        </div>
                        
                        <div class="quiet-hours-settings" style="display: ${this.settings.quietHours.enabled ? 'block' : 'none'}">
                            <div class="time-range">
                                <label>С: 
                                    <select id="quietStartHour">
                                        ${this._renderHourOptions(this.settings.quietHours.start)}
                                    </select>
                                </label>
                                <label>До: 
                                    <select id="quietEndHour">
                                        ${this._renderHourOptions(this.settings.quietHours.end)}
                                    </select>
                                </label>
                            </div>
                        </div>
                        
                        <div class="setting-actions">
                            <button class="test-notification-btn" id="testNotificationBtn">🔔 Тестовое уведомление</button>
                            <button class="request-permission-btn" id="requestPermissionBtn">🔔 Запросить разрешение</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    _renderHourOptions(selected) {
        let options = '';
        for (let i = 0; i < 24; i++) {
            const hourStr = i.toString().padStart(2, '0');
            options += `<option value="${i}" ${selected === i ? 'selected' : ''}>${hourStr}:00</option>`;
        }
        return options;
    }
    
    attachSettingsEvents() {
        const enabledCheckbox = document.getElementById('notifEnabled');
        if (enabledCheckbox) {
            enabledCheckbox.onchange = (e) => this.updateSetting('enabled', e.target.checked);
        }
        
        const remindersCheckbox = document.getElementById('notifReminders');
        if (remindersCheckbox) {
            remindersCheckbox.onchange = (e) => this.updateSetting('reminders', e.target.checked);
        }
        
        const challengesCheckbox = document.getElementById('notifChallenges');
        if (challengesCheckbox) {
            challengesCheckbox.onchange = (e) => this.updateSetting('challenges', e.target.checked);
        }
        
        const messagesCheckbox = document.getElementById('notifMessages');
        if (messagesCheckbox) {
            messagesCheckbox.onchange = (e) => this.updateSetting('messages', e.target.checked);
        }
        
        const dailyDigestCheckbox = document.getElementById('notifDailyDigest');
        if (dailyDigestCheckbox) {
            dailyDigestCheckbox.onchange = (e) => this.updateSetting('dailyDigest', e.target.checked);
        }
        
        const quietHoursCheckbox = document.getElementById('quietHoursEnabled');
        if (quietHoursCheckbox) {
            quietHoursCheckbox.onchange = (e) => {
                this.settings.quietHours.enabled = e.target.checked;
                this.saveSettings();
                const quietDiv = document.querySelector('.quiet-hours-settings');
                if (quietDiv) quietDiv.style.display = e.target.checked ? 'block' : 'none';
            };
        }
        
        const startHourSelect = document.getElementById('quietStartHour');
        if (startHourSelect) {
            startHourSelect.onchange = (e) => {
                this.settings.quietHours.start = parseInt(e.target.value);
                this.saveSettings();
            };
        }
        
        const endHourSelect = document.getElementById('quietEndHour');
        if (endHourSelect) {
            endHourSelect.onchange = (e) => {
                this.settings.quietHours.end = parseInt(e.target.value);
                this.saveSettings();
            };
        }
        
        const testBtn = document.getElementById('testNotificationBtn');
        if (testBtn) {
            testBtn.onclick = () => {
                this.showLocalNotification('🔔 Тестовое уведомление', {
                    body: 'Если вы видите это сообщение, уведомления работают!',
                    type: 'general'
                });
            };
        }
        
        const requestPermissionBtn = document.getElementById('requestPermissionBtn');
        if (requestPermissionBtn) {
            requestPermissionBtn.onclick = async () => {
                const granted = await this.requestPermission();
                if (granted) {
                    alert('✅ Разрешение получено! Теперь вы будете получать уведомления.');
                } else {
                    alert('❌ Разрешение не получено. Проверьте настройки браузера.');
                }
            };
        }
    }
    
    // ============================================
    // СОБЫТИЯ
    // ============================================
    
    addListener(callback) {
        if (!this.listeners) this.listeners = [];
        this.listeners.push(callback);
    }
    
    notifyListeners(event, data) {
        if (this.listeners) {
            this.listeners.forEach(cb => cb(event, data));
        }
    }
}

// Глобальный экспорт
window.NotificationManager = NotificationManager;

console.log('✅ Модуль уведомлений загружен');
