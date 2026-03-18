#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для утренних вдохновляющих сообщений (3 дня)
С ИИ-генерацией для Дней 2 и 3
ВЕРСИЯ ДЛЯ MAX
ДОБАВЛЕНО: Сохранение в PostgreSQL
"""

import asyncio
import logging
import random
import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

import pytz
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton
# BufferedInputFile не нужен в MAX - для голоса используется text_to_speech из services

from profiles import VECTORS, LEVEL_PROFILES
from services import call_deepseek, text_to_speech

# ✅ ДОБАВЛЕНО: импорт для БД
from db_instance import db

logger = logging.getLogger(__name__)


class MorningMessageManager:
    """Менеджер утренних сообщений с ИИ-генерацией и сохранением в БД"""
    
    def __init__(self):
        self.scheduled_tasks = {}  # {user_id: {day: task}}
        self.bot = None
        self.user_contexts = None
        self.user_data = None
    
    def set_bot(self, bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
    
    def set_contexts(self, user_contexts, user_data):
        """Устанавливает ссылки на глобальные хранилища"""
        self.user_contexts = user_contexts
        self.user_data = user_data
    
    # ============================================
    # ✅ ДОБАВЛЕНО: ФУНКЦИИ ДЛЯ РАБОТЫ С БД
    # ============================================
    
    async def _save_message_to_db(self, user_id: int, day: int, message_text: str, message_type: str = "morning"):
        """Сохраняет отправленное сообщение в БД"""
        try:
            # Сохраняем как событие
            await db.log_event(
                user_id,
                f'morning_message_day_{day}',
                {
                    'day': day,
                    'message_type': message_type,
                    'message_preview': message_text[:100],
                    'timestamp': time.time()
                }
            )
            
            # Также добавляем напоминание в таблицу reminders
            await db.add_reminder(
                user_id=user_id,
                reminder_type=f'morning_day_{day}',
                remind_at=datetime.now(),
                data={
                    'day': day,
                    'message': message_text[:200],
                    'sent': True
                }
            )
            
            logger.debug(f"💾 Утреннее сообщение для дня {day} пользователя {user_id} сохранено в БД")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения для {user_id}: {e}")
    
    async def _save_generation_stats(self, user_id: int, day: int, success: bool, error: str = None):
        """Сохраняет статистику генерации"""
        try:
            await db.log_event(
                user_id,
                'morning_generation',
                {
                    'day': day,
                    'success': success,
                    'error': error,
                    'timestamp': time.time()
                }
            )
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики генерации: {e}")
    
    async def _get_user_morning_history(self, user_id: int) -> List[Dict]:
        """Получает историю утренних сообщений пользователя"""
        try:
            # Получаем из событий
            async with db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT event_data, created_at
                    FROM fredi_events
                    WHERE user_id = $1 AND event_type LIKE 'morning_message_day_%'
                    ORDER BY created_at DESC
                    LIMIT 10
                """, user_id)
                
                history = []
                for row in rows:
                    data = row['event_data']
                    if isinstance(data, str):
                        data = json.loads(data)
                    history.append({
                        'day': data.get('day'),
                        'preview': data.get('message_preview'),
                        'time': row['created_at']
                    })
                return history
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории: {e}")
            return []
    
    # ============================================
    # ОСНОВНЫЕ ФУНКЦИИ
    # ============================================
    
    async def schedule_morning_message(self, user_id: int, user_name: str, scores: dict, profile_data: dict):
        """
        Планирует серию из 3 утренних сообщений
        День 1: завтра в 9:00 (сценарий)
        День 2: послезавтра в 9:00 (ИИ)
        День 3: через 2 дня в 9:00 (ИИ)
        """
        # Отменяем все предыдущие задачи для этого пользователя
        self.cancel_all_user_tasks(user_id)
        
        # Получаем часовой пояс пользователя
        context = self.user_contexts.get(user_id) if self.user_contexts else None
        timezone = self._get_user_timezone(context)
        
        # Текущее время
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(timezone)
        
        # Планируем на 3 дня
        for day in range(1, 4):
            # Целевая дата (сегодня + day дней)
            target_local = now_local.replace(hour=9, minute=0, second=0, microsecond=0)
            target_local = target_local + timedelta(days=day)
            
            # Если сегодня уже после 9:00, то начинаем с завтра
            if day == 1 and now_local.hour >= 9:
                target_local = target_local + timedelta(days=1)
            
            target_utc = target_local.astimezone(pytz.UTC)
            seconds_until_target = (target_utc - now_utc).total_seconds()
            
            if seconds_until_target < 0:
                seconds_until_target = 60
            
            logger.info(
                f"📅 День {day} для пользователя {user_id}\n"
                f"   Отправка: {target_local.strftime('%Y-%m-%d %H:%M')}\n"
                f"   Через: {seconds_until_target/3600:.1f} часов"
            )
            
            # ✅ СОХРАНЯЕМ ЗАПЛАНИРОВАННОЕ СООБЩЕНИЕ В БД
            asyncio.create_task(db.add_reminder(
                user_id=user_id,
                reminder_type=f'morning_scheduled_day_{day}',
                remind_at=target_utc,
                data={
                    'day': day,
                    'scheduled_time': target_utc.isoformat(),
                    'user_name': user_name
                }
            ))
            
            # Создаем задачу
            task = asyncio.create_task(
                self._send_daily_message(
                    user_id, user_name, scores, profile_data,
                    seconds_until_target, timezone, day
                )
            )
            
            if user_id not in self.scheduled_tasks:
                self.scheduled_tasks[user_id] = {}
            
            self.scheduled_tasks[user_id][day] = task
    
    def _get_user_timezone(self, context) -> pytz.timezone:
        """Определяет часовой пояс пользователя"""
        if context and hasattr(context, 'timezone') and context.timezone:
            try:
                return pytz.timezone(context.timezone)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка часового пояса {context.timezone}: {e}")
        
        return pytz.timezone("Europe/Moscow")
    
    async def _send_daily_message(self, user_id: int, user_name: str, scores: dict,
                                   profile_data: dict, delay_seconds: float,
                                   timezone: pytz.timezone, day: int):
        """Отправляет ежедневное сообщение"""
        try:
            await asyncio.sleep(delay_seconds)
            
            if not self.bot:
                logger.error(f"❌ Бот не инициализирован")
                return
            
            # Получаем актуальные данные
            context = self.user_contexts.get(user_id) if self.user_contexts else None
            mode = context.communication_mode if context else "coach"
            
            if context:
                # Проверяем, является ли update_weather асинхронной функцией
                if hasattr(context, 'update_weather'):
                    if asyncio.iscoroutinefunction(context.update_weather):
                        await context.update_weather()
                    else:
                        context.update_weather()
            
            success = True
            error_msg = None
            
            # Генерируем текст для этого дня
            try:
                if day == 1:
                    # День 1 - по сценарию (как в текущем коде)
                    text = await self._generate_day1_text(
                        user_id, user_name, scores, profile_data, context, timezone
                    )
                else:
                    # Дни 2 и 3 - через ИИ
                    text = await self._generate_ai_text(
                        user_id, user_name, scores, profile_data, context, timezone, day
                    )
            except Exception as e:
                logger.error(f"❌ Ошибка генерации текста для дня {day}: {e}")
                text = await self._generate_fallback_text(day, user_name, 
                    self._get_address_from_context(context))
                success = False
                error_msg = str(e)
            
            clean_text = self._clean_text_for_voice(text)
            
            # Клавиатура для дня (три кнопки)
            keyboard = self._get_keyboard_for_day(day)
            
            # ✅ СОХРАНЯЕМ В БД
            asyncio.create_task(self._save_message_to_db(user_id, day, text))
            asyncio.create_task(self._save_generation_stats(user_id, day, success, error_msg))
            
            # ✅ ИСПРАВЛЕНО: отправляем текст (проверяем асинхронность)
            try:
                if hasattr(self.bot, 'send_message') and asyncio.iscoroutinefunction(self.bot.send_message):
                    await self.bot.send_message(
                        user_id,
                        text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                else:
                    self.bot.send_message(
                        user_id,
                        text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                logger.info(f"✅ Текст для дня {day} отправлен пользователю {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки текста для дня {day}: {e}")
            
            # Отправляем голос (text_to_speech асинхронная)
            try:
                audio_data = await text_to_speech(clean_text, mode)
                if audio_data:
                    logger.info(f"🎙 Голос для дня {day} сгенерирован ({len(audio_data)} байт)")
                    # Если в MAX есть метод send_audio
                    if hasattr(self.bot, 'send_audio'):
                        if asyncio.iscoroutinefunction(self.bot.send_audio):
                            await self.bot.send_audio(user_id, ('voice.ogg', audio_data))
                        else:
                            self.bot.send_audio(user_id, ('voice.ogg', audio_data))
            except Exception as e:
                logger.error(f"❌ Ошибка голоса для дня {day}: {e}")
            
            logger.info(f"✅ День {day} полностью отправлен пользователю {user_id}")
            
        except asyncio.CancelledError:
            logger.info(f"⏰ День {day} для {user_id} отменён")
        except Exception as e:
            logger.error(f"❌ Ошибка дня {day} для {user_id}: {e}")
    
    def _get_address_from_context(self, context) -> str:
        """Получает обращение из контекста"""
        if not context:
            return "друг"
        
        gender = getattr(context, 'gender', 'other')
        if gender == "male":
            return "брат"
        elif gender == "female":
            return "сестрёнка"
        else:
            return "друг"
    
    def _get_keyboard_for_day(self, day: int) -> InlineKeyboardMarkup:
        """
        Возвращает клавиатуру для конкретного дня
        Всегда три кнопки: вопрос, профиль, идеи на выходные
        """
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_question")],
            [InlineKeyboardButton(text="🧠 МОЙ ПРОФИЛЬ", callback_data="show_results")],
            [InlineKeyboardButton(text="🌟 ИДЕИ НА ВЫХОДНЫЕ", callback_data="weekend_ideas")]
        ])
    
    async def _generate_day1_text(self, user_id: int, user_name: str, scores: dict,
                                    profile_data: dict, context, timezone: pytz.timezone) -> str:
        """
        Генерирует текст для Дня 1 (по сценарию, как в текущем коде)
        """
        now_local = datetime.now(timezone)
        hour = now_local.hour
        
        # Приветствие
        greeting = self._get_greeting(hour, user_name, context)
        
        # Погода
        weather_text = self._get_weather_text(context, hour)
        
        # Вдохновение на основе профиля
        inspiration = self._get_profile_inspiration(scores)
        
        # Совет на день
        daily_tip = self._get_daily_tip(scores)
        
        text = f"""
🌅 <b>{greeting}!</b>

{weather_text}

{inspiration}

💡 <b>Совет на сегодня:</b>
{daily_tip}

✨ Хорошего дня!
"""
        return text.strip()
    
    async def _generate_ai_text(self, user_id: int, user_name: str, scores: dict,
                                  profile_data: dict, context, timezone: pytz.timezone,
                                  day: int) -> str:
        """
        Генерирует текст через DeepSeek для Дней 2 и 3
        """
        now_local = datetime.now(timezone)
        hour = now_local.hour
        weekday = now_local.weekday()
        
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
            main_vector = "СБ"
            vector_desc = "психологический профиль"
            level = 3
        
        # Дни недели
        weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        weekday_name = weekdays[weekday]
        
        # Тема дня
        day_themes = {
            2: "маленькие действия и эксперименты",
            3: "интеграция опыта и взгляд в будущее"
        }
        theme = day_themes.get(day, "продолжение пути")
        
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
Ты - психолог Фреди. Напиши утреннее мотивационное сообщение для пользователя.

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
- Имя: {user_name}
- Обращение: {address}
- Пол: {gender}
- Основной вектор: {main_vector} ({vector_desc})
- Уровень по этому вектору: {level}/6
- День недели: {weekday_name}
- Время суток: {hour} часов
- {weather_context}

КОНТЕКСТ СООБЩЕНИЯ:
- Это ДЕНЬ {day} из 3-дневной серии
- Тема дня: {theme}
- День 1 уже был (он был о принятии себя)
- Сегодня нужно вдохновить на {theme}

ТРЕБОВАНИЯ К СООБЩЕНИЮ:
1. Тёплое, поддерживающее, без нравоучений
2. Учитывай профиль пользователя (вектор и уровень)
3. Используй обращение "{address}" в тексте
4. Добавь 1-2 риторических вопроса
5. Закончи ободряющей фразой
6. Длина: 3-5 абзацев
7. НЕ ИСПОЛЬЗУЙ звёздочки, решётки, markdown
8. Только текст, готовый для голосового озвучивания

Напиши сообщение:
"""
        
        try:
            response = await call_deepseek(prompt, max_tokens=800)
            if response:
                # Добавляем эмодзи и форматирование для чата
                formatted = self._format_ai_response(response, day, address)
                return formatted
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ИИ: {e}")
            asyncio.create_task(self._save_generation_stats(user_id, day, False, str(e)))
        
        # Запасной вариант, если ИИ не ответил
        return await self._generate_fallback_text(day, user_name, address)
    
    def _format_ai_response(self, text: str, day: int, address: str) -> str:
        """Форматирует ответ ИИ для чата (добавляет эмодзи и структуру)"""
        # Убираем возможные markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Добавляем заголовок в зависимости от дня
        if day == 2:
            header = f"⚡ <b>Доброе утро, {address}!</b>\n\n"
        else:
            header = f"🌟 <b>Доброе утро, {address}!</b>\n\n"
        
        # Разбиваем на абзацы для читаемости
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p:
                formatted_paragraphs.append(p)
        
        body = '\n\n'.join(formatted_paragraphs)
        
        return header + body
    
    async def _generate_fallback_text(self, day: int, user_name: str, address: str) -> str:
        """Запасной текст, если ИИ недоступен"""
        if day == 2:
            return f"""
🌅 <b>Доброе утро, {address}!</b>

Сегодня день маленьких шагов. Не надо геройства, просто одно маленькое действие в сторону того, что для тебя важно.

Помни: большие перемены начинаются с малого.

✨ Хорошего дня!
"""
        else:
            return f"""
🌅 <b>Доброе утро, {address}!</b>

Третий день нашей работы. Ты уже прошёл большой путь за это время.

Посмотри назад — ты изменился. Пусть немного, но это начало новой привычки — быть на своей стороне.

✨ Я рядом и всегда поддержу.
"""
    
    def _get_greeting(self, hour: int, user_name: str, context) -> str:
        """Возвращает приветствие"""
        if 5 <= hour < 12:
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            greeting = "Добрый день"
        elif 18 <= hour < 23:
            greeting = "Добрый вечер"
        else:
            greeting = "Доброй ночи"
        
        address = self._get_address_from_context(context)
        
        return f"{greeting}, {address}"
    
    def _get_weather_text(self, context, hour: int) -> str:
        """Формирует текст о погоде (как в текущем коде)"""
        if not context or not hasattr(context, 'weather_cache') or not context.weather_cache:
            return "За окном новый день, полный возможностей."
        
        weather = context.weather_cache
        temp = weather.get('temp', 0)
        desc = weather.get('description', '')
        icon = weather.get('icon', '☁️')
        
        if 5 <= hour < 12:
            time_word = "утро"
        elif 12 <= hour < 18:
            time_word = "день"
        elif 18 <= hour < 23:
            time_word = "вечер"
        else:
            time_word = "ночь"
        
        if temp < -15:
            return f"{icon} Морозное {time_word}, {temp}°C. Даже в самый холод можно найти тепло внутри себя."
        elif temp < 0:
            return f"{icon} {desc}, {temp}°C. Холодно, но твоя внутренняя искра уже согревает."
        elif temp < 10:
            return f"{icon} Прохладное {time_word}, {temp}°C. Самое время для уютных мыслей и планов."
        elif temp < 20:
            return f"{icon} Свежее {time_word}, {temp}°C. Природа просыпается — как и твои новые возможности."
        elif temp < 30:
            return f"{icon} Теплое {time_word}, {temp}°C. Энергия так и плещет — лови момент!"
        else:
            return f"{icon} Жаркое {time_word}, {temp}°C. Даже солнце сегодня хочет тебя вдохновить."
    
    def _get_profile_inspiration(self, scores: dict) -> str:
        """Вдохновение на основе профиля (как в текущем коде)"""
        if not scores:
            return "Каждый день — это новая страница твоей истории."
        
        # Находим сильные и слабые стороны
        sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
        weakest = sorted_vectors[0] if sorted_vectors else ("СБ", 3)
        strongest = sorted_vectors[-1] if sorted_vectors else ("ЧВ", 3)
        
        weak_vector, weak_score = weakest
        strong_vector, strong_score = strongest
        
        weak_lvl = self._level(weak_score)
        strong_lvl = self._level(strong_score)
        
        # Вдохновение для слабой стороны
        weak_inspirations = {
            "СБ": [
                f"Твоя сила не в отсутствии страха, а в умении действовать несмотря на него.",
                f"Каждый раз, когда ты встречаешь вызов, ты становишься сильнее.",
                f"Ты уже справился со многими бурями — справишься и с этой."
            ],
            "ТФ": [
                f"Деньги — это просто энергия, и ты учишься ей управлять.",
                f"Твоя ценность не в кошельке, а в том, какой ты человек.",
                f"Изобилие начинается с благодарности за то, что уже есть."
            ],
            "УБ": [
                f"Мир полон загадок, и каждая разгаданная делает тебя мудрее.",
                f"Ты не обязан всё понимать сразу — просто наблюдай.",
                f"В хаосе всегда есть порядок, просто он пока не виден."
            ],
            "ЧВ": [
                f"Самые важные отношения — это отношения с собой.",
                f"Ты достоин любви просто потому, что ты есть.",
                f"Каждая встреча — это урок, который делает тебя ближе к себе."
            ]
        }
        
        # Вдохновение для сильной стороны
        strong_inspirations = {
            "СБ": "Твоя устойчивость — это твой суперсила. Используй её, чтобы защищать не только себя, но и свои мечты.",
            "ТФ": "Твой талант управлять ресурсами может изменить не только твою жизнь, но и жизнь вокруг.",
            "УБ": "Твоя способность видеть закономерности — дар. Доверяй своей интуиции.",
            "ЧВ": "Твоя эмпатия — это мост к другим людям. Не бойся открываться."
        }
        
        weak_text = random.choice(weak_inspirations.get(weak_vector, ["Сегодня — день новых возможностей."]))
        strong_text = strong_inspirations.get(strong_vector, "")
        
        return f"{weak_text}\n\n{strong_text}"
    
    def _get_daily_tip(self, scores: dict) -> str:
        """Совет на день на основе профиля (как в текущем коде)"""
        if not scores:
            return "Найди 5 минут для себя и просто подыши."
        
        # Находим самое слабое место
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector, score = min_vector
        lvl = self._level(score)
        
        tips = {
            "СБ": {
                1: "Сделай одно маленькое дело, которое откладывал.",
                2: "Скажи 'нет' тому, что тебе не нужно.",
                3: "Позволь себе не согласиться с кем-то сегодня.",
                4: "Выдохни и отпусти контроль над одной ситуацией.",
                5: "Защити не себя, а того, кто слабее.",
                6: "Используй свою силу, чтобы созидать, а не обороняться."
            },
            "ТФ": {
                1: "Запиши одну идею заработка, которая пришла в голову.",
                2: "Посмотри на свои расходы и найди одну статью для оптимизации.",
                3: "Поблагодари себя за то, что уже имеешь.",
                4: "Подумай, на что ты потратишь неожиданный доход.",
                5: "Сделай маленький шаг к финансовой цели.",
                6: "Поделись ресурсом с тем, кому он нужнее."
            },
            "УБ": {
                1: "Прочитай одну статью на новую тему.",
                2: "Задай вопрос 'почему' три раза подряд.",
                3: "Найди закономерность в своей неделе.",
                4: "Попробуй посмотреть на ситуацию глазами другого.",
                5: "Запиши одну мысль, которая кажется важной.",
                6: "Поделись своим пониманием с кем-то."
            },
            "ЧВ": {
                1: "Напиши близкому человеку просто так.",
                2: "Скажи комплимент незнакомцу.",
                3: "Выслушай кого-то, не перебивая.",
                4: "Попроси о помощи, если она нужна.",
                5: "Поблагодари того, кто это заслужил.",
                6: "Обними того, кто рядом."
            }
        }
        
        vector_tips = tips.get(vector, {})
        tip = vector_tips.get(lvl, "Сделай что-то хорошее для себя сегодня.")
        
        return tip
    
    def _clean_text_for_voice(self, text: str) -> str:
        """Очищает текст для синтеза речи"""
        if not text:
            return text
        
        # Убираем HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Убираем эмодзи
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
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
    
    def cancel_all_user_tasks(self, user_id: int):
        """Отменяет все задачи пользователя"""
        if user_id in self.scheduled_tasks:
            for day, task in self.scheduled_tasks[user_id].items():
                task.cancel()
                logger.info(f"⏰ Отменён день {day} для пользователя {user_id}")
            del self.scheduled_tasks[user_id]
            
            # ✅ ОТМЕЧАЕМ В БД
            asyncio.create_task(db.log_event(
                user_id,
                'morning_cancelled',
                {'days': list(self.scheduled_tasks.get(user_id, {}).keys())}
            ))
    
    async def get_user_morning_stats(self, user_id: int) -> Dict[str, Any]:
        """Получает статистику утренних сообщений пользователя"""
        history = await self._get_user_morning_history(user_id)
        
        # Считаем по дням
        days_sent = set()
        for item in history:
            days_sent.add(item.get('day'))
        
        return {
            'total_sent': len(history),
            'days_completed': len(days_sent),
            'history': history[:5]  # последние 5
        }


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = ['MorningMessageManager']
