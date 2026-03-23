// ============================================
// SERVICE WORKER ДЛЯ PUSH-УВЕДОМЛЕНИЙ
// Версия 1.1 - Исправлена ошибка кэширования POST
// ============================================

const CACHE_NAME = 'fredi-v2';

// ✅ Кэшируем только существующие файлы (без иконок, которых нет)
const urlsToCache = [
    '/',
    '/static/styles.css',
    '/static/script.js',
    '/static/app.js',
    '/static/api.js',
    '/static/dashboard.js',
    '/static/psychometric.js',
    '/static/challenges.js',
    '/static/animated-avatar.js',
    '/static/animations.js',
    '/static/notifications.js',
    '/static/dynamic-bg.js',
    '/static/context.js',
    '/static/onboarding.js',
    '/static/test.js',
    '/static/psychometric.css',
    '/manifest.json',
    '/sw.js'
];

// ============================================
// УСТАНОВКА
// ============================================

self.addEventListener('install', (event) => {
    console.log('📦 Service Worker установлен');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('🔧 Кэширование файлов');
                // Кэшируем каждый файл отдельно, чтобы один неудачный не ломал все
                return Promise.allSettled(
                    urlsToCache.map(url => 
                        cache.add(url).catch(err => {
                            console.warn(`⚠️ Не удалось закэшировать: ${url}`, err);
                        })
                    )
                );
            })
            .catch((error) => {
                console.error('Ошибка кэширования:', error);
            })
    );
    
    self.skipWaiting();
});

// ============================================
// АКТИВАЦИЯ
// ============================================

self.addEventListener('activate', (event) => {
    console.log('🚀 Service Worker активирован');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Удаление старого кэша:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    
    self.clients.claim();
});

// ============================================
// ОБРАБОТКА ЗАПРОСОВ (ОФФЛАЙН)
// ============================================

self.addEventListener('fetch', (event) => {
    // ✅ КЭШИРУЕМ ТОЛЬКО GET-ЗАПРОСЫ
    if (event.request.method !== 'GET') {
        return;
    }
    
    // ✅ Не кэшируем API запросы, чтобы данные были актуальными
    if (event.request.url.includes('/api/')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                if (response) {
                    // Возвращаем из кэша
                    return response;
                }
                
                // Иначе запрашиваем из сети
                return fetch(event.request)
                    .then((response) => {
                        // Проверяем, что ответ успешный
                        if (!response || response.status !== 200) {
                            return response;
                        }
                        
                        // Кэшируем только успешные ответы
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(event.request, responseToCache);
                            })
                            .catch((err) => {
                                console.warn('⚠️ Ошибка кэширования:', err);
                            });
                        
                        return response;
                    })
                    .catch(() => {
                        // Оффлайн-страница
                        if (event.request.destination === 'document') {
                            return caches.match('/offline.html') || new Response(
                                '<h1>Вы оффлайн</h1><p>Проверьте подключение к интернету</p>',
                                { headers: { 'Content-Type': 'text/html' } }
                            );
                        }
                        return new Response('Вы оффлайн', {
                            status: 503,
                            statusText: 'Service Unavailable'
                        });
                    });
            })
    );
});

// ============================================
// PUSH-УВЕДОМЛЕНИЯ
// ============================================

self.addEventListener('push', (event) => {
    console.log('📨 Получено push-уведомление:', event);
    
    let data = {
        title: '🔔 Фреди',
        body: 'Новое уведомление',
        icon: '/static/icon-192.png',  // ✅ используем путь /static/
        badge: '/static/icon-192.png',
        data: {}
    };
    
    if (event.data) {
        try {
            const parsed = event.data.json();
            data = { ...data, ...parsed };
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        vibrate: [200, 100, 200],
        data: data.data,
        actions: [
            {
                action: 'open',
                title: '📱 Открыть'
            },
            {
                action: 'dismiss',
                title: '❌ Закрыть'
            }
        ],
        tag: data.tag || 'fredi-notification',
        renotify: true,
        requireInteraction: data.requireInteraction || false
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// ============================================
// КЛИК ПО УВЕДОМЛЕНИЮ
// ============================================

self.addEventListener('notificationclick', (event) => {
    console.log('🔔 Клик по уведомлению:', event);
    
    event.notification.close();
    
    const action = event.action;
    const notificationData = event.notification.data;
    
    if (action === 'dismiss') {
        return;
    }
    
    // Открываем приложение
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // Если уже есть открытое окно, фокусируем его
            for (const client of clientList) {
                if (client.url.includes('/') && 'focus' in client) {
                    return client.focus();
                }
            }
            // Иначе открываем новое
            if (clients.openWindow) {
                return clients.openWindow('/');
            }
        })
    );
    
    // Обработка специальных действий
    if (notificationData && notificationData.type) {
        console.log('Тип уведомления:', notificationData.type);
        // Здесь можно добавить навигацию по типам уведомлений
        // Например, открыть конкретную страницу
        if (notificationData.type === 'challenge') {
            // Открыть челленджи
            clients.openWindow('/?action=challenges');
        } else if (notificationData.type === 'thought') {
            // Открыть мысли психолога
            clients.openWindow('/?action=thoughts');
        }
    }
});

// ============================================
// ОБНОВЛЕНИЕ КЭША
// ============================================

self.addEventListener('message', (event) => {
    if (event.data === 'skipWaiting') {
        self.skipWaiting();
    }
    
    if (event.data === 'clearCache') {
        caches.delete(CACHE_NAME).then(() => {
            console.log('🧹 Кэш очищен');
        });
    }
});

console.log('✅ Service Worker загружен (версия 1.1)');
