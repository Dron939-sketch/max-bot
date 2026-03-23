#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации идей на выходные с учётом профиля пользователя
ВЕРСИЯ 2.1 - ИСПРАВЛЕНО: замена db на синхронные функции
"""
import logging
import random
import re
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# Заменяем aiogram на maxibot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton

from profiles import VECTORS
from services import call_deepseek

# ✅ ИСПРАВЛЕНО: импорт синхронных функций из db_instance
from db_instance import (
    log_event,
    add_reminder,
    get_user_reminders,
    save_user_data
)

logger = logging.getLogger(__name__)


class WeekendPlanner:
    """Генератор идей на выходные с учётом профиля и кэшированием"""
    
    def __init__(self):
        self.cache = {}  # in-memory кэш (для быстрого доступа)
    
    async def get_weekend_ideas(self, user_id: int, user_name: str, scores: dict, profile_data: dict, context=None) -> str:
        """
        Генерирует идеи на выходные на основе профиля
        
        Args:
            user_id: ID пользователя
            user_name: Имя пользователя
            scores: Словарь с баллами по векторам
            profile_data: Данные профиля
            context: Контекст пользователя (опционально)
            
        Returns:
            Отформатированный текст с идеями
        """
        # Проверяем in-memory кэш
        cache_key = f"{user_id}_{datetime.now().strftime('%Y-%m-%d')}"
        if cache_key in self.cache:
            logger.info(f"✅ Найдены кэшированные идеи для пользователя {user_id} (in-memory)")
            return self.cache[cache_key]
        
        # Определяем основной вектор (самый слабый)
        if scores:
            min_vector = min(scores.items(), key=lambda x: x[1])
            main_vector = min_vector[0]
            level = self._level(min_vector[1])
            
            # Описание вектора
            vector_names = {
                "СБ": "страх конфликтов и защиту границ",
                "ТФ": "отношения с деньгами и ресурсами",
                "УБ": "понимание мира и поиск смыслов",
                "ЧВ": "отношения с людьми и эмоциональные связи"
            }
            vector_desc = vector_names.get(main_vector, "психологический профиль")
        else:
            main_vector = "ЧВ"
            vector_desc = "психологический профиль"
            level = 3
        
        # Пол для обращения
        gender = context.gender if context else "other"
        address = "друг"
        if gender == "male":
            address = "брат"
        elif gender == "female":
            address = "сестрёнка"
        
        # Погода для контекста
        weather_context = ""
        if context and context.weather_cache:
            weather = context.weather_cache
            temp = weather.get('temp', 0)
            desc = weather.get('description', '')
            icon = weather.get('icon', '☁️')
            weather_context = f"Погода: {icon} {desc}, {temp}°C. "
        
        # Формируем промпт для ИИ
        prompt = f"""
Ты - психолог Фреди. Сгенерируй идеи для выходных для пользователя.

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
- Имя: {user_name}
- Обращение: {address}
- Пол: {gender}
- Основной вектор: {main_vector} ({vector_desc})
- Уровень по этому вектору: {level}/6
- {weather_context}

ТРЕБОВАНИЯ К ИДЕЯМ:
1. 3-5 конкретных идей, что можно сделать на выходных
2. Идеи должны учитывать профиль пользователя (помогать развивать слабый вектор)
3. Тёплые, поддерживающие, без давления
4. Используй обращение "{address}" в тексте
5. Разные категории: отдых, развитие, творчество, общение
6. НЕ ИСПОЛЬЗУЙ звёздочки, решётки, markdown
7. Только текст, готовый для отправки

ФОРМАТ:
Привет, {address}! Вот несколько идей, как провести выходные с пользой для души:

🌟 *Категория 1*
• Идея 1
• Идея 2

🎨 *Категория 2*
• Идея 1
• Идея 2

... и так далее.

Выбери то, что откликается!
"""
        
        try:
            response = await call_deepseek(prompt, max_tokens=1000)
            if response:
                # Форматируем ответ
                formatted = self._format_response(response, address)
                
                # Сохраняем в in-memory кэш
                self.cache[cache_key] = formatted
                
                # Логируем генерацию (синхронно в отдельном потоке)
                import threading
                threading.Thread(
                    target=self._log_generation,
                    args=(user_id, True, main_vector, level),
                    daemon=True
                ).start()
                
                return formatted
        except Exception as e:
            logger.error(f"❌ Ошибка генерации идей: {e}")
            # Логируем ошибку (синхронно в отдельном потоке)
            import threading
            threading.Thread(
                target=self._log_generation,
                args=(user_id, False, main_vector, level, str(e)),
                daemon=True
            ).start()
        
        # Запасной вариант
        fallback = await self._get_fallback_ideas(main_vector, level, address)
        self.cache[cache_key] = fallback
        
        return fallback
    
    # ============================================
    # ✅ ИСПРАВЛЕНО: СИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
    # ============================================
    
    def _log_generation(self, user_id: int, success: bool, main_vector: str, level: int, error: str = None):
        """Синхронно логирует генерацию идей в БД"""
        try:
            log_event(
                user_id,
                'weekend_ideas_generation',
                {
                    'success': success,
                    'main_vector': main_vector,
                    'level': level,
                    'error': error[:200] if error else None,
                    'timestamp': time.time()
                }
            )
            logger.debug(f"📊 Генерация идей для {user_id} залогирована")
        except Exception as e:
            logger.error(f"❌ Ошибка логирования: {e}")
    
    async def clear_user_cache(self, user_id: int):
        """Очищает in-memory кэш пользователя"""
        try:
            # Очищаем in-memory кэш
            keys_to_delete = [k for k in self.cache.keys() if str(user_id) in k]
            for key in keys_to_delete:
                del self.cache[key]
            logger.info(f"🧹 Кэш пользователя {user_id} очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша для {user_id}: {e}")
    
    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ============================================
    
    def _format_response(self, text: str, address: str) -> str:
        """Форматирует ответ для отправки"""
        # Убираем markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Убеждаемся, что есть обращение
        if address and not text.lower().startswith(address.lower()):
            text = f"Привет, {address}!\n\n{text}"
        
        return text
    
    async def _get_fallback_ideas(self, vector: str, level: int, address: str) -> str:
        """Запасные идеи, если ИИ недоступен"""
        
        base_ideas = {
            "СБ": [
                "🚶 Прогулка в новом месте (парк, район, где ты не был)",
                "📝 Написать список своих границ и подумать, где их нарушают",
                "🧘 Практика заземления: походить босиком по траве/полу",
                "🎬 Посмотреть фильм, где герой преодолевает страх",
                "🤝 Пригласить друга в гости (или сходить самому)"
            ],
            "ТФ": [
                "💰 Разобрать свои финансы за месяц",
                "📚 Почитать книгу по финансовой грамотности",
                "🛒 Сходить в магазин с конкретным списком (без импульсивных покупок)",
                "💡 Придумать 3 идеи дополнительного дохода",
                "🎁 Сделать подарок себе в рамках бюджета"
            ],
            "УБ": [
                "📖 Почитать книгу по психологии/философии",
                "🧩 Посмотреть документальный фильм на новую тему",
                "✍️ Написать эссе 'Что для меня важно'",
                "🗣 Поговорить с мудрым человеком",
                "🌌 Посмотреть на звёзды и подумать о вечном"
            ],
            "ЧВ": [
                "👥 Встретиться с друзьями, которых давно не видел",
                "📞 Позвонить родным просто так",
                "🤗 Сделать комплимент незнакомцу",
                "🍵 Пригласить коллегу на чай",
                "💌 Написать письмо благодарности кому-то"
            ]
        }
        
        ideas = base_ideas.get(vector, base_ideas["ЧВ"])
        random.shuffle(ideas)
        
        categories = {
            "СБ": "🌿 ГАРМОНИЯ И СПОКОЙСТВИЕ",
            "ТФ": "💰 РЕСУРСЫ И ИЗОБИЛИЕ",
            "УБ": "📚 ПОЗНАНИЕ И СМЫСЛЫ",
            "ЧВ": "🤝 ОТНОШЕНИЯ И ТЕПЛО"
        }
        
        category = categories.get(vector, "🌟 ИДЕИ НА ВЫХОДНЫЕ")
        
        text = f"Привет, {address}! Вот несколько идей, как провести выходные с пользой:\n\n"
        text += f"🌟 *{category}*\n"
        for idea in ideas[:4]:
            text += f"• {idea}\n"
        text += "\nВыбери то, что откликается!"
        
        return text
    
    def _level(self, score: float) -> int:
        """Дробный балл 1..4 → целый уровень 1..6"""
        if score <= 1.49:
            return 1
        elif score <= 2.00:
            return 2
        elif score <= 2.50:
            return 3
        elif score <= 3.00:
            return 4
        elif score <= 3.50:
            return 5
        else:
            return 6


def get_weekend_planner() -> WeekendPlanner:
    """Возвращает экземпляр планировщика"""
    return WeekendPlanner()


def get_weekend_ideas_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для идей на выходные"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ЕЩЁ ИДЕИ", callback_data="weekend_ideas")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_question")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")]
    ])


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'WeekendPlanner',
    'get_weekend_planner',
    'get_weekend_ideas_keyboard'
]
