// ============================================
// ДИНАМИЧЕСКИЙ ФОН
// Версия 1.0 - Анимированный градиент с частицами
// ============================================

class DynamicBackground {
    constructor(container = 'app', options = {}) {
        this.container = document.getElementById(container) || document.body;
        this.options = {
            particlesCount: 50,
            particleSpeed: 0.5,
            gradientSpeed: 0.002,
            waveIntensity: 0.5,
            ...options
        };
        
        this.canvas = null;
        this.ctx = null;
        this.width = 0;
        this.height = 0;
        this.particles = [];
        this.time = 0;
        this.currentTheme = 'auto';
        this.themes = {
            morning: {
                gradientStart: { r: 255, g: 200, b: 150 },
                gradientEnd: { r: 200, g: 150, b: 100 },
                particlesColor: 'rgba(255, 200, 150, 0.6)',
                accent: '#ffa500'
            },
            day: {
                gradientStart: { r: 100, g: 150, b: 255 },
                gradientEnd: { r: 50, g: 100, b: 200 },
                particlesColor: 'rgba(100, 150, 255, 0.6)',
                accent: '#248bf2'
            },
            evening: {
                gradientStart: { r: 255, g: 100, b: 100 },
                gradientEnd: { r: 150, g: 50, b: 100 },
                particlesColor: 'rgba(255, 100, 100, 0.6)',
                accent: '#ff6b6b'
            },
            night: {
                gradientStart: { r: 30, g: 30, b: 60 },
                gradientEnd: { r: 10, g: 10, b: 30 },
                particlesColor: 'rgba(100, 100, 200, 0.4)',
                accent: '#6c5ce7'
            },
            energetic: {
                gradientStart: { r: 255, g: 100, b: 50 },
                gradientEnd: { r: 200, g: 50, b: 100 },
                particlesColor: 'rgba(255, 100, 50, 0.7)',
                accent: '#ff4500'
            },
            calm: {
                gradientStart: { r: 80, g: 120, b: 160 },
                gradientEnd: { r: 50, g: 80, b: 120 },
                particlesColor: 'rgba(80, 120, 160, 0.5)',
                accent: '#4a90e2'
            },
            creative: {
                gradientStart: { r: 150, g: 50, b: 200 },
                gradientEnd: { r: 100, g: 30, b: 150 },
                particlesColor: 'rgba(150, 50, 200, 0.6)',
                accent: '#9b59b6'
            }
        };
        
        this.moodMap = {
            neutral: 'calm',
            happy: 'day',
            sad: 'evening',
            thoughtful: 'morning',
            energetic: 'energetic',
            calm: 'calm'
        };
        
        this.isAnimating = true;
        this.animationId = null;
        
        this.init();
    }
    
    // ============================================
    // ИНИЦИАЛИЗАЦИЯ
    // ============================================
    
    init() {
        console.log('🎨 Инициализация динамического фона...');
        
        this.createCanvas();
        this.setupResizeHandler();
        this.createParticles();
        this.setupMoodDetection();
        this.startAnimation();
        
        // Загружаем сохранённую тему
        this.loadTheme();
        
        console.log('✅ Динамический фон готов');
    }
    
    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.zIndex = '-1';
        this.canvas.style.pointerEvents = 'none';
        
        this.container.style.position = 'relative';
        this.container.style.zIndex = '1';
        
        this.container.parentNode.insertBefore(this.canvas, this.container);
        
        this.ctx = this.canvas.getContext('2d');
        this.resize();
    }
    
    setupResizeHandler() {
        window.addEventListener('resize', () => this.resize());
    }
    
    resize() {
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        // Пересоздаём частицы при изменении размера
        this.createParticles();
    }
    
    // ============================================
    // ЧАСТИЦЫ
    // ============================================
    
    createParticles() {
        this.particles = [];
        const count = Math.min(this.options.particlesCount, Math.floor(this.width * this.height / 20000));
        
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                radius: 2 + Math.random() * 4,
                speedX: (Math.random() - 0.5) * this.options.particleSpeed,
                speedY: (Math.random() - 0.5) * this.options.particleSpeed,
                alpha: 0.3 + Math.random() * 0.5,
                pulseSpeed: 0.5 + Math.random() * 1,
                pulsePhase: Math.random() * Math.PI * 2
            });
        }
    }
    
    updateParticles() {
        for (const p of this.particles) {
            p.x += p.speedX;
            p.y += p.speedY;
            
            // Отражение от границ
            if (p.x < 0) p.x = this.width;
            if (p.x > this.width) p.x = 0;
            if (p.y < 0) p.y = this.height;
            if (p.y > this.height) p.y = 0;
        }
    }
    
    // ============================================
    // ГРАДИЕНТЫ
    // ============================================
    
    getCurrentTheme() {
        if (this.currentTheme !== 'auto') {
            return this.themes[this.currentTheme] || this.themes.day;
        }
        
        const hour = new Date().getHours();
        
        if (hour >= 5 && hour < 9) return this.themes.morning;
        if (hour >= 9 && hour < 18) return this.themes.day;
        if (hour >= 18 && hour < 22) return this.themes.evening;
        return this.themes.night;
    }
    
    setTheme(themeName) {
        if (this.themes[themeName]) {
            this.currentTheme = themeName;
            this.saveTheme(themeName);
            console.log(`🎨 Тема фона изменена на: ${themeName}`);
        }
    }
    
    setAutoTheme() {
        this.currentTheme = 'auto';
        this.saveTheme('auto');
        console.log('🎨 Включён автоматический выбор темы');
    }
    
    setMood(mood) {
        const themeName = this.moodMap[mood] || 'calm';
        if (this.themes[themeName]) {
            this.currentTheme = themeName;
            console.log(`😊 Фон адаптирован под настроение: ${mood}`);
        }
    }
    
    saveTheme(theme) {
        localStorage.setItem('fredi_bg_theme', theme);
    }
    
    loadTheme() {
        const saved = localStorage.getItem('fredi_bg_theme');
        if (saved && saved !== 'auto') {
            this.currentTheme = saved;
        } else if (saved === 'auto') {
            this.currentTheme = 'auto';
        }
    }
    
    // ============================================
    // ВОЛНОВОЙ ЭФФЕКТ
    // ============================================
    
    drawWaves() {
        const theme = this.getCurrentTheme();
        const time = this.time;
        
        for (let i = 0; i < 3; i++) {
            const amplitude = 30 + Math.sin(time * 0.5) * 10;
            const frequency = 0.005 + i * 0.002;
            const yOffset = this.height * (0.7 + i * 0.1);
            
            this.ctx.beginPath();
            this.ctx.moveTo(0, yOffset);
            
            for (let x = 0; x <= this.width; x += 20) {
                const y = yOffset + 
                    Math.sin(x * frequency + time) * amplitude * this.options.waveIntensity +
                    Math.cos(x * 0.003 + time * 0.8) * amplitude * 0.5;
                this.ctx.lineTo(x, y);
            }
            
            this.ctx.lineTo(this.width, this.height);
            this.ctx.lineTo(0, this.height);
            this.ctx.closePath();
            
            const gradient = this.ctx.createLinearGradient(0, yOffset - 50, 0, this.height);
            gradient.addColorStop(0, `rgba(${theme.gradientStart.r}, ${theme.gradientStart.g}, ${theme.gradientStart.b}, 0.1)`);
            gradient.addColorStop(1, `rgba(${theme.gradientEnd.r}, ${theme.gradientEnd.g}, ${theme.gradientEnd.b}, 0)`);
            
            this.ctx.fillStyle = gradient;
            this.ctx.fill();
        }
    }
    
    // ============================================
    // ЗВЁЗДЫ (для ночной темы)
    // ============================================
    
    drawStars() {
        const theme = this.getCurrentTheme();
        const isNight = this.currentTheme === 'night' || 
                        (this.currentTheme === 'auto' && new Date().getHours() >= 22);
        
        if (!isNight) return;
        
        const starCount = Math.min(200, Math.floor(this.width * this.height / 10000));
        
        for (let i = 0; i < starCount; i++) {
            const x = (i * 131071) % this.width;
            const y = (i * 524287) % this.height;
            const size = 1 + ((i * 7919) % 3);
            const alpha = 0.3 + Math.sin(this.time * 0.5 + i) * 0.2;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(255, 255, 200, ${alpha})`;
            this.ctx.fill();
        }
    }
    
    // ============================================
    // ОСНОВНОЙ ГРАДИЕНТ
    // ============================================
    
    drawGradient() {
        const theme = this.getCurrentTheme();
        
        // Основной градиент
        const gradient = this.ctx.createLinearGradient(0, 0, this.width, this.height);
        
        // Динамическое смещение цветов
        const time = this.time * this.options.gradientSpeed;
        const offset = Math.sin(time) * 0.1;
        
        const startR = Math.min(255, Math.max(0, theme.gradientStart.r + offset * 30));
        const startG = Math.min(255, Math.max(0, theme.gradientStart.g + offset * 20));
        const startB = Math.min(255, Math.max(0, theme.gradientStart.b + offset * 40));
        
        const endR = Math.min(255, Math.max(0, theme.gradientEnd.r + offset * 20));
        const endG = Math.min(255, Math.max(0, theme.gradientEnd.g + offset * 30));
        const endB = Math.min(255, Math.max(0, theme.gradientEnd.b + offset * 10));
        
        gradient.addColorStop(0, `rgb(${startR}, ${startG}, ${startB})`);
        gradient.addColorStop(1, `rgb(${endR}, ${endG}, ${endB})`);
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.width, this.height);
    }
    
    // ============================================
    // ЧАСТИЦЫ НА ФОНЕ
    // ============================================
    
    drawParticles() {
        const theme = this.getCurrentTheme();
        
        for (const p of this.particles) {
            // Пульсация
            const pulse = 0.5 + Math.sin(this.time * p.pulseSpeed + p.pulsePhase) * 0.3;
            const radius = p.radius * (0.8 + pulse * 0.4);
            const alpha = p.alpha * (0.5 + pulse * 0.5);
            
            // Цвет частицы
            let color;
            if (typeof theme.particlesColor === 'string' && theme.particlesColor.startsWith('rgba')) {
                color = theme.particlesColor.replace(/[\d\.]+\)$/, `${alpha})`);
            } else {
                color = `rgba(255, 255, 255, ${alpha * 0.6})`;
            }
            
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
            this.ctx.fillStyle = color;
            this.ctx.fill();
            
            // Свечение для крупных частиц
            if (radius > 2) {
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, radius * 2, 0, Math.PI * 2);
                this.ctx.fillStyle = color.replace(/[\d\.]+\)$/, `${alpha * 0.2})`);
                this.ctx.fill();
            }
        }
    }
    
    // ============================================
    // ДИНАМИЧЕСКИЕ ЭЛЕМЕНТЫ (по настроению)
    // ============================================
    
    drawDynamicElements() {
        const theme = this.getCurrentTheme();
        const time = this.time;
        
        // Элементы в зависимости от темы
        if (theme === this.themes.energetic) {
            this.drawEnergyBursts();
        } else if (theme === this.themes.calm) {
            this.drawCalmRipples();
        } else if (theme === this.themes.creative) {
            this.drawCreativeSparks();
        }
    }
    
    drawEnergyBursts() {
        const time = this.time;
        const burstCount = 3;
        
        for (let i = 0; i < burstCount; i++) {
            const angle = time * 2 + i * Math.PI * 2 / burstCount;
            const radius = 50 + Math.sin(time * 3) * 20;
            const x = this.width / 2 + Math.cos(angle) * radius;
            const y = this.height / 2 + Math.sin(angle) * radius;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, 15 + Math.sin(time * 5 + i) * 5, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(255, 100, 50, 0.2)`;
            this.ctx.fill();
        }
    }
    
    drawCalmRipples() {
        const time = this.time;
        const centerX = this.width / 2;
        const centerY = this.height / 2;
        
        for (let i = 0; i < 3; i++) {
            const radius = 100 + i * 50 + Math.sin(time * 0.5) * 20;
            
            this.ctx.beginPath();
            this.ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
            this.ctx.strokeStyle = `rgba(80, 120, 160, 0.3)`;
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
        }
    }
    
    drawCreativeSparks() {
        const time = this.time;
        const sparkCount = 20;
        
        for (let i = 0; i < sparkCount; i++) {
            const angle = time * 2 + i * Math.PI * 2 / sparkCount;
            const radius = 150 + Math.sin(time * 3 + i) * 30;
            const x = this.width / 2 + Math.cos(angle) * radius;
            const y = this.height / 2 + Math.sin(angle) * radius;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, 3 + Math.sin(time * 10 + i) * 2, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(150, 50, 200, 0.4)`;
            this.ctx.fill();
        }
    }
    
    // ============================================
    // ОСНОВНОЙ ЦИКЛ АНИМАЦИИ
    // ============================================
    
    animate() {
        if (!this.isAnimating) return;
        
        this.time += 0.016; // Примерно 60 FPS
        
        // Обновляем частицы
        this.updateParticles();
        
        // Отрисовка
        this.drawGradient();
        this.drawWaves();
        this.drawParticles();
        this.drawStars();
        this.drawDynamicElements();
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    startAnimation() {
        this.isAnimating = true;
        this.animate();
    }
    
    stopAnimation() {
        this.isAnimating = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    
    // ============================================
    // ОПРЕДЕЛЕНИЕ НАСТРОЕНИЯ ПОЛЬЗОВАТЕЛЯ
    // ============================================
    
    setupMoodDetection() {
        // Слушаем события от других компонентов
        document.addEventListener('userMoodChange', (e) => {
            if (e.detail && e.detail.mood) {
                this.setMood(e.detail.mood);
            }
        });
        
        // Анализ времени активности
        this.trackActivity();
    }
    
    trackActivity() {
        let lastActivity = Date.now();
        let mood = 'neutral';
        
        const updateMood = () => {
            const now = Date.now();
            const inactiveTime = (now - lastActivity) / 1000 / 60; // минут
            
            if (inactiveTime > 10) {
                mood = 'calm';
            } else if (inactiveTime > 5) {
                mood = 'thoughtful';
            } else {
                const hour = new Date().getHours();
                if (hour < 12) mood = 'happy';
                else if (hour < 18) mood = 'energetic';
                else mood = 'calm';
            }
            
            if (this.currentTheme === 'auto') {
                this.setMood(mood);
            }
        };
        
        document.addEventListener('mousemove', () => {
            lastActivity = Date.now();
        });
        
        document.addEventListener('click', () => {
            lastActivity = Date.now();
        });
        
        document.addEventListener('keypress', () => {
            lastActivity = Date.now();
        });
        
        setInterval(updateMood, 30000);
    }
    
    // ============================================
    // ИНТЕГРАЦИЯ С ПРОФИЛЕМ
    // ============================================
    
    async updateFromProfile(userId) {
        try {
            const response = await fetch(`/api/get-profile?user_id=${userId}`);
            const data = await response.json();
            
            if (data && data.profile_data) {
                const scores = {
                    sb: data.profile_data.sb_level || 4,
                    tf: data.profile_data.tf_level || 4,
                    ub: data.profile_data.ub_level || 4,
                    chv: data.profile_data.chv_level || 4
                };
                
                // Определяем доминирующий вектор
                const dominant = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
                
                const themeMap = {
                    sb: 'calm',
                    tf: 'energetic',
                    ub: 'creative',
                    chv: 'day'
                };
                
                if (this.currentTheme === 'auto') {
                    this.setTheme(themeMap[dominant[0]] || 'day');
                }
                
                // Настраиваем параметры под профиль
                this.options.particleSpeed = 0.3 + scores.ub * 0.1;
                this.options.waveIntensity = 0.3 + scores.chv * 0.1;
                this.options.gradientSpeed = 0.001 + scores.sb * 0.0005;
            }
        } catch (error) {
            console.warn('Ошибка загрузки профиля для фона:', error);
        }
    }
    
    // ============================================
    // УТИЛИТЫ
    // ============================================
    
    setParticleCount(count) {
        this.options.particlesCount = count;
        this.createParticles();
    }
    
    setSpeed(speed) {
        this.options.particleSpeed = speed;
        for (const p of this.particles) {
            p.speedX = (Math.random() - 0.5) * speed;
            p.speedY = (Math.random() - 0.5) * speed;
        }
    }
    
    destroy() {
        this.stopAnimation();
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
        console.log('🗑️ Динамический фон уничтожен');
    }
}

// Глобальный экспорт
window.DynamicBackground = DynamicBackground;

console.log('✅ Модуль динамического фона загружен');
