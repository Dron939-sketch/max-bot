#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации идей на выходные с учётом профиля пользователя
ВЕРСИЯ 2.0 - ДОБАВЛЕНО КЭШИРОВАНИЕ В БД
"""
import logging
import random
import re
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton

from profiles import VECTORS
from services import call_deepseek

# БД импортируется лениво внутри методов

logger = logging.getLogger(__name__)


class WeekendPlanner:
    """Генератор идей на выходные с учётом профиля и кэшированием в БД"""
    
    def __init__(self):
        self.cache = {}
    
    async def get_weekend_ideas(self, user_id: int, user_name: str, scores: dict, profile_data: dict, context=None) -> str:
        cached = await self._get_cached_from_db(user_id)
        if cached:
            logger.info(f"✅ Найдены кэшированные идеи для пользователя {user_id}")
            return cached
        
        cache_key = f"{user_id}_{datetime.now().strftime('%Y-%m-%d')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        if scores:
            min_vector = min(scores.items(), key=lambda x: x[1])
            main_vector = min_vector[0]
            level = self._level(min_vector[1])
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
        
        gender = context.gender if context else "other"
        address = "друг"
        if gender == "male":
            address = "брат"
        elif gender == "female":
            address = "сестрёнка"
        
        weather_context = ""
        if context and context.weather_cache:
            weather = context.weather_cache
            temp = weather.get('temp', 0)
            desc = weather.get('description', '')
            icon = weather.get('icon', '☁️')
            weather_context = f"Погода: {icon} {desc}, {temp}°C. "
        
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

🌟 Категория 1
• Идея 1
• Идея 2

🎨 Категория 2
• Идея 1
• Идея 2

Выбери то, что откликается!
"""
        
        try:
            response = await call_deepseek(prompt, max_tokens=1000)
            if response:
                formatted = self._format_response(response, address)
                await self._cache_to_db(user_id, formatted, main_vector, level)
                self.cache[cache_key] = formatted
                return formatted
        except Exception as e:
            logger.error(f"❌ Ошибка генерации идей: {e}")
            await self._log_generation_error(user_id, str(e))
        
        fallback = await self._get_fallback_ideas(main_vector, level, address)
        await self._cache_to_db(user_id, fallback, main_vector, level)
        self.cache[cache_key] = fallback
        return fallback
    
    # ============================================
    # ФУНКЦИИ ДЛЯ РАБОТЫ С БД (lazy import)
    # ============================================
    
    async def _cache_to_db(self, user_id: int, ideas_text: str, main_vector: str, main_level: int):
        try:
            from db_instance import db
            await db.cache_weekend_ideas(
                user_id=user_id, ideas_text=ideas_text,
                main_vector=main_vector, main_level=main_level
            )
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения идей в БД для {user_id}: {e}")
    
    async def _get_cached_from_db(self, user_id: int) -> Optional[str]:
        try:
            from db_instance import db
            return await db.get_cached_weekend_ideas(user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка получения кэша из БД для {user_id}: {e}")
            return None
    
    async def _log_generation_error(self, user_id: int, error: str):
        try:
            from db_instance import db
            await db.log_event(user_id, 'weekend_ideas_error',
                {'error': error[:200], 'timestamp': time.time()})
        except Exception as e:
            logger.error(f"❌ Ошибка логирования: {e}")
    
    async def clear_user_cache(self, user_id: int):
        try:
            from db_instance import db
            async with db.get_connection() as conn:
                await conn.execute(
                    "DELETE FROM fredi_weekend_ideas_cache WHERE user_id = $1", user_id)
            keys_to_delete = [k for k in self.cache.keys() if str(user_id) in k]
            for key in keys_to_delete:
                del self.cache[key]
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша для {user_id}: {e}")
    
    async def get_cache_stats(self, user_id: int = None) -> Dict[str, Any]:
        try:
            from db_instance import db
            async with db.get_connection() as conn:
                if user_id:
                    row = await conn.fetchrow("""
                        SELECT COUNT(*) as total, MAX(created_at) as last_generated,
                               main_vector, main_level
                        FROM fredi_weekend_ideas_cache WHERE user_id = $1
                        GROUP BY main_vector, main_level
                    """, user_id)
                    return dict(row) if row else {}
                else:
                    rows = await conn.fetch("""
                        SELECT COUNT(DISTINCT user_id) as users_with_cache,
                               COUNT(*) as total_entries
                        FROM fredi_weekend_ideas_cache
                    """)
                    return dict(rows[0]) if rows else {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики кэша: {e}")
            return {}
    
    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ============================================
    
    def _format_response(self, text: str, address: str) -> str:
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        if address and not text.lower().startswith(address.lower()):
            text = f"Привет, {address}!\n\n{text}"
        return text
    
    async def _get_fallback_ideas(self, vector: str, level: int, address: str) -> str:
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
        text += f"🌟 {category}\n"
        for idea in ideas[:4]:
            text += f"• {idea}\n"
        text += "\nВыбери то, что откликается!"
        return text
    
    def _level(self, score: float) -> int:
        if score <= 1.49: return 1
        elif score <= 2.00: return 2
        elif score <= 2.50: return 3
        elif score <= 3.00: return 4
        elif score <= 3.50: return 5
        else: return 6


def get_weekend_planner() -> WeekendPlanner:
    return WeekendPlanner()


def get_weekend_ideas_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ЕЩЁ ИДЕИ", callback_data="weekend_ideas")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_question")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")]
    ])


__all__ = ['WeekendPlanner', 'get_weekend_planner', 'get_weekend_ideas_keyboard']
