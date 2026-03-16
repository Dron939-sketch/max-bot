#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ: ПЛАНИРОВЩИК ВЫХОДНЫХ (weekend_planner.py)
Генерирует индивидуальные идеи на выходные с учётом профиля пользователя
"""

import logging
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services import call_deepseek
from profiles import VECTORS

logger = logging.getLogger(__name__)


class WeekendPlanner:
    """
    Генератор индивидуальных идей на выходные через ИИ
    """
    
    # Типы активностей для разных векторов (для промпта)
    ACTIVITY_TYPES = {
        "СБ": [
            "спокойные, уединённые, безопасные",
            "расслабляющие, без стресса",
            "предсказуемые, комфортные"
        ],
        "ТФ": [
            "бесплатные или бюджетные",
            "связанные с саморазвитием и заработком",
            "практичные и полезные"
        ],
        "УБ": [
            "интеллектуальные, развивающие",
            "новые, неизведанные",
            "глубокие, со смыслом"
        ],
        "ЧВ": [
            "социальные, в компании",
            "душевные, тёплые",
            "для укрепления связей"
        ]
    }
    
    # Уровни энергии/риска для разных уровней векторов
    LEVEL_DESCRIPTIONS = {
        1: "очень осторожный, избегающий стресса",
        2: "склонный к безопасному, предсказуемому",
        3: "умеренный, ищущий баланс",
        4: "готовый к экспериментам",
        5: "активный, ищущий новые впечатления",
        6: "экстремальный, жаждущий острых ощущений"
    }
    
    def __init__(self):
        self.cache = {}  # Простой кэш, чтобы не генерировать слишком часто
    
    async def get_weekend_ideas(self, user_id: int, user_name: str, scores: dict, 
                                 profile_data: dict, context) -> str:
        """
        Генерирует индивидуальные идеи на выходные через ИИ
        
        Args:
            user_id: ID пользователя
            user_name: имя
            scores: баллы по векторам
            profile_data: полные данные профиля
            context: объект UserContext (пол, возраст, город, погода)
        
        Returns:
            str: отформатированное сообщение с идеями
        """
        
        # Проверяем кэш (не чаще раза в час для одного пользователя)
        cache_key = f"{user_id}_{datetime.now().strftime('%Y%m%d%H')}"
        if cache_key in self.cache:
            logger.info(f"📦 Использую кэшированные идеи для {user_name}")
            return self.cache[cache_key]
        
        # Определяем основной вектор и уровень
        if scores:
            main_vector = min(scores.items(), key=lambda x: x[1])[0]
            main_level = self._level(scores[main_vector])
            
            # Второй вектор (для баланса)
            sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
            second_vector = sorted_vectors[1][0] if len(sorted_vectors) > 1 else main_vector
        else:
            main_vector = "СБ"
            main_level = 3
            second_vector = "ЧВ"
        
        # Получаем данные пользователя
        gender = context.gender if context else "other"
        age = context.age if context else 30
        city = context.city if context else "Москва"
        
        # Погода (если есть)
        weather_info = ""
        if context and context.weather_cache:
            w = context.weather_cache
            weather_info = f"Погода в эти выходные: {w.get('description', '')}, {w.get('temp', 0)}°C"
        
        # День недели и сколько до выходных
        now = datetime.now()
        weekday = now.weekday()  # 0-6
        days_to_weekend = max(0, 5 - weekday) if weekday <= 5 else 0
        
        # Формируем промпт для ИИ
        prompt = self._build_prompt(
            user_name=user_name,
            gender=gender,
            age=age,
            city=city,
            weather=weather_info,
            main_vector=main_vector,
            main_level=main_level,
            second_vector=second_vector,
            days_to_weekend=days_to_weekend,
            scores=scores,
            profile_data=profile_data
        )
        
        try:
            # Получаем ответ от DeepSeek
            response = await call_deepseek(prompt, max_tokens=1200, temperature=0.8)
            
            if response:
                # Форматируем ответ для Telegram
                formatted = self._format_response(response, user_name, main_vector)
                
                # Сохраняем в кэш
                self.cache[cache_key] = formatted
                
                # Очищаем старые записи в кэше (если больше 100)
                if len(self.cache) > 100:
                    oldest_key = min(self.cache.keys())
                    del self.cache[oldest_key]
                
                return formatted
            else:
                logger.warning(f"⚠️ ИИ не ответил, использую резервный вариант")
                return self._fallback_ideas(main_vector, main_level, city, user_name)
                
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации идей: {e}")
            return self._fallback_ideas(main_vector, main_level, city, user_name)
    
    def _build_prompt(self, user_name: str, gender: str, age: int, city: str,
                      weather: str, main_vector: str, main_level: int,
                      second_vector: str, days_to_weekend: int,
                      scores: dict, profile_data: dict) -> str:
        """Строит промпт для ИИ"""
        
        # Описание векторов
        vector_names = {
            "СБ": "страх и безопасность",
            "ТФ": "деньги и ресурсы",
            "УБ": "мышление и понимание мира",
            "ЧВ": "отношения и эмоциональные связи"
        }
        
        # Характеристики уровней
        level_activity = self.LEVEL_DESCRIPTIONS.get(main_level, "умеренный")
        
        # Типы активностей для векторов
        main_activities = random.choice(self.ACTIVITY_TYPES.get(main_vector, ["разные"]))
        second_activities = random.choice(self.ACTIVITY_TYPES.get(second_vector, ["разные"]))
        
        # Контекст времени
        if days_to_weekend == 0:
            time_context = "СЕГОДНЯ ВЫХОДНЫЕ! 🎉"
            action_verb = "провести"
        elif days_to_weekend == 1:
            time_context = "ЗАВТРА ВЫХОДНЫЕ! 🎈"
            action_verb = "запланировать"
        else:
            time_context = f"До выходных {days_to_weekend} дня"
            action_verb = "представляешь, как хочешь провести"
        
        # Пол для обращений
        if gender == "male":
            address = "брат"
            pronoun = "он"
            gender_word = "мужчина"
        elif gender == "female":
            address = "сестрёнка"
            pronoun = "она"
            gender_word = "женщина"
        else:
            address = "друг"
            pronoun = "человек"
            gender_word = "человек"
        
        prompt = f"""
ТЫ - ПСИХОЛОГ ФРЕДИ. Твоя задача: предложить 3-5 индивидуальных идей на выходные для пользователя.

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
- Имя: {user_name}
- Пол: {gender_word}
- Возраст: {age} лет
- Город: {city}
- {weather}
- ВРЕМЕННОЙ КОНТЕКСТ: {time_context}

ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ (самое важное):

1. ОСНОВНОЙ ВЕКТОР: {main_vector} ({vector_names.get(main_vector, '')})
   Уровень: {main_level}/6
   Характеристика: {level_activity}
   Значит, пользователю подходят: {main_activities}

2. ВТОРОЙ ПО ЗНАЧИМОСТИ ВЕКТОР: {second_vector} ({vector_names.get(second_vector, '')})
   Значит, пользователю также важны: {second_activities}

ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ ПРОФИЛЯ (могут пригодиться):
{scores}

ТВОЯ ЗАДАЧА:
Предложи 3-5 КОНКРЕТНЫХ идей на выходные, которые идеально подходят ЭТОМУ КОНКРЕТНОМУ ЧЕЛОВЕКУ.

ВАЖНО:
- Идеи должны быть РЕАЛЬНЫМИ для его города ({city})
- Учитывай ЕГО психологический профиль (кому-то парашют, кому-то лес за грибами)
- Для кого-то Ма́льдивы, для кого-то Сочи — предлагай с учётом его возможностей
- Смешивай идеи: что-то спокойное, что-то активное, что-то социальное
- Добавь 1-2 неожиданные, "выпадающие" идеи, которые могут его удивить

ФОРМАТ ОТВЕТА:
Напиши ТОЛЬКО идеи, без лишних предисловий. Используй эмодзи для каждой идеи.
Каждая идея должна быть описана 1-2 предложениями.

Пример:
🏔️ Съездить в национальный парк за город — там сейчас золотая осень, можно устроить фотосессию и подышать воздухом.
🎨 Сходить на мастер-класс по гончарному делу — отлично снимает стресс и даёт тактильное удовольствие.
📚 Устроить "культурный день": посетить новую выставку в музее современного искусства, а вечером — джазовый концерт.
🚁 Сюрприз-вариант: полетать на параплане с инструктором — давно хотел, но боялся? Самое время!

ТЕПЕРЬ НАПИШИ ИДЕИ ДЛЯ {user_name}:
"""
        return prompt
    
    def _format_response(self, response: str, user_name: str, main_vector: str) -> str:
        """Форматирует ответ ИИ для Telegram"""
        
        # Убираем лишние markdown
        response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)
        response = re.sub(r'__(.*?)__', r'\1', response)
        response = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', response)
        
        # Добавляем заголовок
        header = f"🌟 <b>{user_name}, идеи на выходные!</b>\n\n"
        
        # Добавляем персонализированный комментарий под вектор
        vector_comments = {
            "СБ": "🌿 Для тебя важно чувствовать себя в безопасности, но иногда стоит выходить из зоны комфорта — здесь есть идеи на любой вкус.",
            "ТФ": "💰 Есть идеи на любой бюджет — от бесплатных до тех, где можно себя побаловать.",
            "УБ": "🧠 Я подобрал идеи, которые заставят твой мозг работать по-новому и откроют неожиданные грани.",
            "ЧВ": "👥 Для тебя важны люди — здесь есть идеи для компании, а есть и для уединения, чтобы восстановить контакт с собой."
        }
        
        comment = vector_comments.get(main_vector, "✨ Выбери то, что откликается именно тебе.")
        
        # Разбиваем на абзацы
        paragraphs = response.split('\n\n')
        formatted_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p:
                # Если строка начинается с эмодзи и текста — оставляем как есть
                if re.match(r'^[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF]', p):
                    formatted_paragraphs.append(p)
                else:
                    formatted_paragraphs.append(p)
        
        body = '\n\n'.join(formatted_paragraphs)
        
        # Добавляем завершающий вопрос
        footer = "\n\n❓ Какая идея откликается больше всего? Можешь рассказать, я подскажу детали."
        
        return header + comment + "\n\n" + body + footer
    
    def _fallback_ideas(self, vector: str, level: int, city: str, user_name: str) -> str:
        """Резервный вариант, если ИИ недоступен"""
        
        # Базовые идеи для разных векторов
        ideas_db = {
            "СБ": [
                "🌳 Съездить в парк или лес за город — подышать, погулять, послушать тишину",
                "📚 Найти уютную кофейню с книгой и провести там пару часов",
                "🧘 Сходить на йогу или медитацию — отлично снимает напряжение",
                "🎨 Попробовать себя в гончарном деле или рисовании — очень успокаивает"
            ],
            "ТФ": [
                "💰 Устроить день без денег — найти бесплатные развлечения в городе",
                "📝 Провести ревизию финансов и спланировать бюджет на месяц",
                "🍳 Приготовить сложное блюдо дома вместо ресторана — и вкусно, и выгодно",
                "🚶 Исследовать новый район города пешком — бесплатно и интересно"
            ],
            "УБ": [
                "🎬 Посмотреть фильм, который давно в списке, и записать мысли",
                "📖 Прочитать главу из книги по психологии или философии",
                "🎨 Сходить на выставку современного искусства — расширяет сознание",
                "🧩 Решить головоломку или пройти квест"
            ],
            "ЧВ": [
                "👥 Организовать встречу с друзьями, с которыми давно не виделись",
                "📞 Позвонить родным просто так, без повода",
                "🤝 Сходить в гости или пригласить кого-то к себе",
                "💬 Написать старым знакомым — узнать, как у них дела"
            ]
        }
        
        # Выбираем идеи под вектор
        ideas = ideas_db.get(vector, ideas_db["СБ"])
        
        # Перемешиваем
        random.shuffle(ideas)
        selected = ideas[:4]
        
        # Формируем сообщение
        message = f"""
🌟 <b>{user_name}, вот несколько идей на выходные!</b>

✨ Выбери то, что откликается:

{selected[0]}

{selected[1]}

{selected[2]}

{selected[3]}

❓ Хочешь больше идей или расскажешь, что выбрал(а)?
"""
        
        return message.strip()
    
    def _level(self, score: float) -> int:
        """Дробный балл → целый уровень 1-6"""
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


# ============================================
# ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ПЛАНИРОВЩИКА
# ============================================

def get_weekend_planner() -> WeekendPlanner:
    """Возвращает экземпляр планировщика (синглтон)"""
    if not hasattr(get_weekend_planner, "_instance"):
        get_weekend_planner._instance = WeekendPlanner()
    return get_weekend_planner._instance


# ============================================
# КЛАВИАТУРА ДЛЯ ИДЕЙ НА ВЫХОДНЫЕ
# ============================================

def get_weekend_ideas_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для взаимодействия с идеями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ БУДУ ДЕЛАТЬ", callback_data="will_do_weekend")],
        [InlineKeyboardButton(text="🎯 ДРУГИЕ ИДЕИ", callback_data="weekend_ideas")],
        [InlineKeyboardButton(text="📝 РАССКАЗАТЬ", callback_data="tell_about_weekend")]
    ])
