// ============================================
// АНИМИРОВАННЫЙ АВАТАР - ПРОФЕССОР ФРЕЙД
// Версия 3.0 - Стильный, узнаваемый, профессиональный
// ============================================

class AnimatedAvatar {
    constructor(userId, userName, profileData = null) {
        this.userId = userId;
        this.userName = userName || 'Друг';
        this.profileData = profileData;
        
        // Canvas
        this.canvas = null;
        this.ctx = null;
        this.width = 120;
        this.height = 120;
        
        // Состояние
        this.currentMood = 'neutral';
        this.isWebView = /; wv\)/.test(navigator.userAgent) || 
                         /WebView/.test(navigator.userAgent) ||
                         (window.MAX && window.MAX.WebApp);
        
        // Анимация
        this.blinkProgress = 0;
        this.smokeProgress = 0;
        this.pipeGlow = 0;
        this.time = 0;
        
        // Цвета (винтажная палитра)
        this.colors = {
            skin: '#e8d5b5',
            skinShadow: '#c9b28b',
            beard: '#b87c4f',
            beardLight: '#d4a373',
            hair: '#5d3a1a',
            glasses: '#2c3e2f',
            glassesFrame: '#4a3b2a',
            eyes: '#2c3e50',
            pipe: '#8b5a2b',
            pipeStem: '#5a3a1a',
            smoke: 'rgba(200,200,200,0.6)',
            suit: '#2c3e2f',
            bowtie: '#b22234'
        };
        
        this.init();
    }
    
    async init() {
        console.log('🎨 Инициализация аватара "Профессор Фрейд"...');
        
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        this.canvas.className = 'animated-avatar';
        this.canvas.style.width = `${this.width}px`;
        this.canvas.style.height = `${this.height}px`;
        this.canvas.style.borderRadius = '50%';
        this.canvas.style.cursor = 'pointer';
        this.canvas.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
        
        this.ctx = this.canvas.getContext('2d');
        
        this._startAnimation();
        this._startBlinking();
        
        this.canvas.addEventListener('click', () => this._onClick());
        
        console.log('✅ Аватар "Профессор Фрейд" создан');
        return this.canvas;
    }
    
    _startAnimation() {
        const animate = (timestamp) => {
            this.time = timestamp / 1000;
            this._update();
            this._draw();
            this.animationFrame = requestAnimationFrame(animate);
        };
        this.animationFrame = requestAnimationFrame(animate);
    }
    
    _startBlinking() {
        setInterval(() => {
            this.blinkProgress = 1;
            setTimeout(() => { this.blinkProgress = 0; }, 120);
        }, 4200);
    }
    
    _update() {
        // Дым из трубки
        this.smokeProgress = (this.smokeProgress + 0.02) % (Math.PI * 2);
        this.pipeGlow = 0.3 + Math.sin(this.time * 8) * 0.2;
        
        // Моргание
        if (this.blinkProgress > 0) {
            this.blinkProgress = Math.max(0, this.blinkProgress - 0.03);
        }
    }
    
    _draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.width, this.height);
        
        const cx = this.width / 2;
        const cy = this.height / 2;
        
        // 1. Тень
        this._drawShadow(ctx, cx, cy);
        
        // 2. Лицо
        this._drawFace(ctx, cx, cy);
        
        // 3. Борода
        this._drawBeard(ctx, cx, cy);
        
        // 4. Усы
        this._drawMustache(ctx, cx, cy);
        
        // 5. Очки
        this._drawGlasses(ctx, cx, cy);
        
        // 6. Глаза
        this._drawEyes(ctx, cx, cy);
        
        // 7. Трубка
        this._drawPipe(ctx, cx, cy);
        
        // 8. Дым
        this._drawSmoke(ctx, cx, cy);
        
        // 9. Волосы
        this._drawHair(ctx, cx, cy);
        
        // 10. Бант/галстук
        this._drawBowtie(ctx, cx, cy);
    }
    
    _drawShadow(ctx, cx, cy) {
        ctx.beginPath();
        ctx.ellipse(cx + 3, cy + 4, 58, 62, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0,0,0,0.15)';
        ctx.fill();
    }
    
    _drawFace(ctx, cx, cy) {
        // Основное лицо
        ctx.beginPath();
        ctx.ellipse(cx, cy, 54, 58, 0, 0, Math.PI * 2);
        
        const gradient = ctx.createLinearGradient(cx - 20, cy - 20, cx + 20, cy + 30);
        gradient.addColorStop(0, this.colors.skin);
        gradient.addColorStop(1, this.colors.skinShadow);
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // Морщины (интеллектуальные)
        ctx.beginPath();
        ctx.moveTo(cx - 25, cy - 10);
        ctx.quadraticCurveTo(cx - 30, cy - 5, cx - 28, cy);
        ctx.strokeStyle = 'rgba(0,0,0,0.1)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(cx + 25, cy - 10);
        ctx.quadraticCurveTo(cx + 30, cy - 5, cx + 28, cy);
        ctx.stroke();
        
        // Лоб (интеллектуальный)
        ctx.beginPath();
        ctx.moveTo(cx - 25, cy - 35);
        ctx.quadraticCurveTo(cx, cy - 45, cx + 25, cy - 35);
        ctx.fillStyle = 'rgba(0,0,0,0.03)';
        ctx.fill();
    }
    
    _drawBeard(ctx, cx, cy) {
        // Борода
        ctx.beginPath();
        ctx.moveTo(cx - 35, cy - 5);
        ctx.quadraticCurveTo(cx - 25, cy + 25, cx - 20, cy + 40);
        ctx.lineTo(cx + 20, cy + 40);
        ctx.quadraticCurveTo(cx + 25, cy + 25, cx + 35, cy - 5);
        ctx.fillStyle = this.colors.beard;
        ctx.fill();
        
        // Светлые пряди в бороде
        ctx.beginPath();
        ctx.moveTo(cx - 25, cy + 10);
        ctx.quadraticCurveTo(cx - 15, cy + 25, cx - 10, cy + 35);
        ctx.strokeStyle = this.colors.beardLight;
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(cx + 25, cy + 10);
        ctx.quadraticCurveTo(cx + 15, cy + 25, cx + 10, cy + 35);
        ctx.stroke();
    }
    
    _drawMustache(ctx, cx, cy) {
        // Левый ус
        ctx.beginPath();
        ctx.moveTo(cx - 20, cy + 5);
        ctx.quadraticCurveTo(cx - 30, cy + 2, cx - 25, cy - 5);
        ctx.fillStyle = this.colors.beard;
        ctx.fill();
        
        // Правый ус
        ctx.beginPath();
        ctx.moveTo(cx + 20, cy + 5);
        ctx.quadraticCurveTo(cx + 30, cy + 2, cx + 25, cy - 5);
        ctx.fill();
        
        // Центральная часть усов
        ctx.beginPath();
        ctx.moveTo(cx - 8, cy + 8);
        ctx.quadraticCurveTo(cx, cy + 3, cx + 8, cy + 8);
        ctx.fill();
    }
    
    _drawGlasses(ctx, cx, cy) {
        // Очки (круглые, интеллектуальные)
        
        // Левая оправа
        ctx.beginPath();
        ctx.ellipse(cx - 23, cy - 2, 14, 16, 0, 0, Math.PI * 2);
        ctx.strokeStyle = this.colors.glassesFrame;
        ctx.lineWidth = 2.5;
        ctx.stroke();
        
        // Правая оправа
        ctx.beginPath();
        ctx.ellipse(cx + 23, cy - 2, 14, 16, 0, 0, Math.PI * 2);
        ctx.stroke();
        
        // Дужка
        ctx.beginPath();
        ctx.moveTo(cx - 36, cy - 2);
        ctx.lineTo(cx - 45, cy - 8);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(cx + 36, cy - 2);
        ctx.lineTo(cx + 45, cy - 8);
        ctx.stroke();
        
        // Переносица
        ctx.beginPath();
        ctx.moveTo(cx - 10, cy - 4);
        ctx.lineTo(cx, cy - 2);
        ctx.lineTo(cx + 10, cy - 4);
        ctx.stroke();
        
        // Стекло (блик)
        ctx.beginPath();
        ctx.ellipse(cx - 26, cy - 4, 3, 4, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.fill();
        
        ctx.beginPath();
        ctx.ellipse(cx + 20, cy - 4, 3, 4, 0, 0, Math.PI * 2);
        ctx.fill();
    }
    
    _drawEyes(ctx, cx, cy) {
        const blink = Math.min(1, this.blinkProgress);
        const eyeH = 7 * (1 - blink * 0.85);
        
        // Левый глаз
        ctx.beginPath();
        ctx.ellipse(cx - 23, cy - 2, 5, eyeH, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        // Зрачок
        ctx.beginPath();
        ctx.arc(cx - 23, cy - 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = this.colors.eyes;
        ctx.fill();
        
        // Блик (интеллектуальный блеск)
        ctx.beginPath();
        ctx.arc(cx - 25, cy - 4, 1, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        // Правый глаз
        ctx.beginPath();
        ctx.ellipse(cx + 23, cy - 2, 5, eyeH, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(cx + 23, cy - 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = this.colors.eyes;
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(cx + 21, cy - 4, 1, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
    }
    
    _drawPipe(ctx, cx, cy) {
        // Мундштук трубки
        ctx.beginPath();
        ctx.moveTo(cx + 38, cy + 8);
        ctx.quadraticCurveTo(cx + 45, cy + 12, cx + 48, cy + 15);
        ctx.lineWidth = 6;
        ctx.strokeStyle = this.colors.pipeStem;
        ctx.stroke();
        
        // Чаша трубки
        ctx.beginPath();
        ctx.ellipse(cx + 48, cy + 14, 9, 7, -0.2, 0, Math.PI * 2);
        ctx.fillStyle = this.colors.pipe;
        ctx.fill();
        
        // Раскалённый уголёк
        ctx.beginPath();
        ctx.arc(cx + 52, cy + 12, 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 100, 50, ${this.pipeGlow})`;
        ctx.fill();
    }
    
    _drawSmoke(ctx, cx, cy) {
        const smokeX = cx + 54;
        const smokeY = cy + 6;
        const offset = Math.sin(this.smokeProgress) * 3;
        
        // Кольца дыма
        ctx.beginPath();
        ctx.ellipse(smokeX + offset - 5, smokeY - 8, 6, 4, 0, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220, 220, 220, 0.3)`;
        ctx.fill();
        
        ctx.beginPath();
        ctx.ellipse(smokeX + offset, smokeY - 12, 8, 5, 0, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(200, 200, 200, 0.25)`;
        ctx.fill();
        
        ctx.beginPath();
        ctx.ellipse(smokeX + offset + 4, smokeY - 16, 7, 4.5, 0, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 180, 180, 0.2)`;
        ctx.fill();
    }
    
    _drawHair(ctx, cx, cy) {
        // Волосы (профессорская причёска)
        ctx.beginPath();
        ctx.moveTo(cx - 35, cy - 32);
        ctx.quadraticCurveTo(cx, cy - 48, cx + 35, cy - 32);
        ctx.fillStyle = this.colors.hair;
        ctx.fill();
        
        // Пробор
        ctx.beginPath();
        ctx.moveTo(cx - 5, cy - 38);
        ctx.lineTo(cx + 5, cy - 38);
        ctx.strokeStyle = 'rgba(0,0,0,0.2)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }
    
    _drawBowtie(ctx, cx, cy) {
        // Бант/галстук (профессорский)
        ctx.fillStyle = this.colors.bowtie;
        
        // Центр
        ctx.beginPath();
        ctx.ellipse(cx, cy + 52, 8, 5, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Левое крыло
        ctx.beginPath();
        ctx.moveTo(cx - 12, cy + 50);
        ctx.quadraticCurveTo(cx - 22, cy + 48, cx - 18, cy + 56);
        ctx.fill();
        
        // Правое крыло
        ctx.beginPath();
        ctx.moveTo(cx + 12, cy + 50);
        ctx.quadraticCurveTo(cx + 22, cy + 48, cx + 18, cy + 56);
        ctx.fill();
    }
    
    setMood(mood) {
        // Изменение выражения лица
        const validMoods = ['neutral', 'happy', 'thoughtful', 'energetic', 'calm'];
        if (!validMoods.includes(mood)) return;
        
        this.currentMood = mood;
        
        switch(mood) {
            case 'happy':
                // Лёгкая улыбка
                this._drawSmile();
                break;
            case 'thoughtful':
                // Задумчивый взгляд
                this._drawThoughtful();
                break;
            case 'energetic':
                // Энергичный блеск
                this.pipeGlow = 0.8;
                setTimeout(() => { this.pipeGlow = 0.3; }, 1000);
                break;
        }
        
        setTimeout(() => this._resetMood(), 2000);
    }
    
    _drawSmile() {
        if (!this.ctx) return;
        const cx = this.width / 2;
        const cy = this.height / 2;
        
        this.ctx.beginPath();
        this.ctx.arc(cx, cy + 15, 12, 0.1, Math.PI - 0.1, false);
        this.ctx.strokeStyle = '#8b5a2b';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }
    
    _drawThoughtful() {
        if (!this.ctx) return;
        const cx = this.width / 2;
        const cy = this.height / 2;
        
        // Приподнятая бровь
        this.ctx.beginPath();
        this.ctx.moveTo(cx - 35, cy - 12);
        this.ctx.quadraticCurveTo(cx - 30, cy - 18, cx - 25, cy - 14);
        this.ctx.strokeStyle = this.colors.hair;
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // Мыслительная лампочка
        this.ctx.beginPath();
        this.ctx.arc(cx + 40, cy - 25, 8, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(255, 200, 100, 0.3)';
        this.ctx.fill();
    }
    
    _resetMood() {
        this.currentMood = 'neutral';
        this._draw();
    }
    
    _onClick() {
        // Реакция на клик
        const moods = ['thoughtful', 'happy', 'energetic'];
        const randomMood = moods[Math.floor(Math.random() * moods.length)];
        this.setMood(randomMood);
        
        if (this.onAvatarClick) this.onAvatarClick();
    }
    
    setSize(width, height) {
        this.width = width;
        this.height = height;
        this.canvas.width = width;
        this.canvas.height = height;
        this.canvas.style.width = `${width}px`;
        this.canvas.style.height = `${height}px`;
    }
    
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
    }
}

window.AnimatedAvatar = AnimatedAvatar;
console.log('✅ Аватар "Профессор Фрейд" загружен');
