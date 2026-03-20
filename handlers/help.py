#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики помощи и сказок для MAX
ВЕРСИЯ 2.2 - ИСПРАВЛЕНО: используется sync_db
"""

import logging
import random
import time
import threading
from typing import Dict, Any, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message
from keyboards import get_back_keyboard
from hypno_module import TherapeuticTales
from formatters import bold

# Импорты из state
from state import (
    user_data, user_state_data, user_contexts, user_names, user_states,
    get_state, set_state, get_state_data, update_state_data, clear_state
)

# ✅ ИСПРАВЛЕНО: используем sync_db
from db_sync import sync_db

logger = logging.getLogger(__name__)

# ============================================
# ИНИЦИАЛИЗАЦИЯ ТЕРАПЕВТИЧЕСКИХ СКАЗОК
# ============================================

tales = TherapeuticTales()

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data_dict(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data_dict(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def get_user_context_obj(user_id: int):
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_name(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "друг")

def is_test_completed_check(user_data_dict: dict) -> bool:
    """Проверяет, завершен ли тест"""
    if user_data_dict.get("profile_data"):
        return True
    if user_data_dict.get("ai_generated_profile"):
        return True
    required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
    if all(field in user_data_dict for field in required_minimal):
        return True
    return False

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БД (СИНХРОННЫЕ)
# ============================================

def log_help_event(user_id: int, action: str, category: str = None):
    """Синхронно логирует события помощи в БД"""
    try:
        sync_db.log_event(
            user_id,
            f'help_{action}',
            {
                'category': category,
                'timestamp': time.time()
            }
        )
        logger.debug(f"💾 Событие помощи {action} для {user_id} сохранено в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка логирования события помощи для {user_id}: {e}")

def log_tale_event(user_id: int, tale_title: str, issue: str):
    """Синхронно логирует просмотр сказки в БД"""
    try:
        sync_db.log_event(
            user_id,
            'tale_viewed',
            {
                'tale_title': tale_title,
                'issue': issue,
                'timestamp': time.time()
            }
        )
        logger.debug(f"💾 Просмотр сказки для {user_id} сохранен в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка логирования просмотра сказки для {user_id}: {e}")

def log_benefits_view(user_id: int):
    """Синхронно логирует просмотр преимуществ теста"""
    try:
        sync_db.log_event(
            user_id,
            'benefits_viewed',
            {'timestamp': time.time()}
        )
    except Exception as e:
        logger.error(f"❌ Ошибка логирования просмотра преимуществ для {user_id}: {e}")

def log_weekend_ideas_view(user_id: int, idea_type: str = None):
    """Синхронно логирует просмотр идей на выходные"""
    try:
        sync_db.log_event(
            user_id,
            'weekend_ideas_viewed',
            {
                'idea_type': idea_type,
                'timestamp': time.time()
            }
        )
    except Exception as e:
        logger.error(f"❌ Ошибка логирования просмотра идей для {user_id}: {e}")

# ============================================
# КЛАВИАТУРА ДЛЯ ПОМОЩИ
# ============================================

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с категориями помощи"""
    keyboard = InlineKeyboardMarkup()
    
    keyboard.row(
        InlineKeyboardButton("🗣 Отношения", callback_data="help_cat_relations"),
        InlineKeyboardButton("💰 Деньги", callback_data="help_cat_money")
    )
    keyboard.row(
        InlineKeyboardButton("🧠 Самоощущение", callback_data="help_cat_self"),
        InlineKeyboardButton("📚 Знания", callback_data="help_cat_knowledge")
    )
    keyboard.row(
        InlineKeyboardButton("💪 Поддержка", callback_data="help_cat_support"),
        InlineKeyboardButton("🎨 Муза", callback_data="help_cat_muse")
    )
    keyboard.row(
        InlineKeyboardButton("🍏 Забота о себе", callback_data="help_cat_care")
    )
    keyboard.row(
        InlineKeyboardButton("✏️ Написать самому", callback_data="ask_question")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ НАЗАД", callback_data="show_results")
    )
    
    return keyboard

# ============================================
# ПОКАЗ МЕНЮ ПОМОЩИ
# ============================================

def show_help(call: CallbackQuery):
    """
    Показывает меню помощи с категориями
    """
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_help_event, args=(user_id, 'menu_opened'), daemon=True).start()
    
    # Проверяем, есть ли контекст для персонализации
    greeting = ""
    if context and context.name:
        greeting = f"{context.name}, "
    
    text = f"""
🧠 <b>{greeting}ЧЕМ Я МОГУ БЫТЬ ПОЛЕЗЕН?</b>

🗣 <b>Отношения</b> — сложности с близкими, друзьями, коллегами
💰 <b>Деньги и ресурсы</b> — финансовые вопросы, карьера
🧠 <b>Самоощущение</b> — тревога, апатия, поиск себя
📚 <b>Знания и развитие</b> — обучение, навыки, рост
💪 <b>Поддержка</b> — просто выговориться, получить опору
🎨 <b>Муза и творчество</b> — вдохновение, креативность
🍏 <b>Забота о себе</b> — отдых, здоровье, энергия

✏️ <b>Написать самому</b> — свой вопрос

👇 <b>Выбери категорию:</b>
"""
    
    keyboard = get_help_keyboard()
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

# ============================================
# ОБРАБОТКА КАТЕГОРИЙ ПОМОЩИ
# ============================================

def handle_help_category(call: CallbackQuery, category: str):
    """
    Обрабатывает выбор категории помощи
    """
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_help_event, args=(user_id, 'category_selected', category), daemon=True).start()
    
    # Тексты для разных категорий
    category_texts = {
        "relations": """
🗣 <b>Отношения</b>

Расскажите, что происходит в ваших отношениях. Я помогу разобраться в чувствах и найти новые перспективы.

Возможные темы:
• Конфликты с близкими
• Трудности в общении
• Поиск партнёра
• Границы в отношениях
• Доверие и близость
""",
        "money": """
💰 <b>Деньги и ресурсы</b>

Что беспокоит в финансовой сфере? Вместе исследуем ваши паттерны и найдём пути к изобилию.

Возможные темы:
• Нехватка денег
• Страхи, связанные с финансами
• Карьерный рост
• Поиск призвания
• Инвестиции и накопления
""",
        "self": """
🧠 <b>Самоощущение</b>

Расскажите о том, что чувствуете. Я помогу разобраться в себе и найти внутреннюю опору.

Возможные темы:
• Тревога и беспокойство
• Апатия и усталость
• Поиск себя
• Самооценка
• Внутренние конфликты
""",
        "knowledge": """
📚 <b>Знания и развитие</b>

Что хотите понять или освоить? Вместе построим путь к новым знаниям.

Возможные темы:
• Выбор направления обучения
• Преодоление учебных трудностей
• Развитие навыков
• Систематизация знаний
• Менторство и наставничество
""",
        "support": """
💪 <b>Поддержка</b>

Нужно просто выговориться? Я здесь, чтобы выслушать и поддержать. Иногда само проговаривание уже помогает найти решение.

Расскажите, что у вас на душе.
""",
        "muse": """
🎨 <b>Муза и творчество</b>

Творческий блок? Расскажите, что мешает творить. Вместе поищем вдохновение.

Возможные темы:
• Страх чистого листа
• Поиск идей
• Самовыражение
• Преодоление перфекционизма
• Творческие проекты
""",
        "care": """
🍏 <b>Забота о себе</b>

Как вы заботитесь о себе? Поделитесь, что получается, а что хотелось бы улучшить.

Возможные темы:
• Отдых и восстановление
• Здоровье и тело
• Энергия и ресурсы
• Границы и баланс
• Привычки и режим
"""
    }
    
    base_text = category_texts.get(category, "Чем я могу помочь?")
    
    # Добавляем погоду и приветствие, если есть контекст
    if context:
        if context.weather_cache:
            weather = context.weather_cache
            greeting = context.get_greeting(context.name)
            base_text += f"\n\n{greeting}\n"
            base_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C"
    
    base_text += f"\n\n👇 <b>Напишите своим текстом:</b>"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="show_help"))
    
    safe_send_message(
        call.message,
        base_text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # ✅ ИСПРАВЛЕНО: используем state
    user_states[user_id] = "awaiting_question"
    
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id]["question_context"] = category

# ============================================
# ТЕРАПЕВТИЧЕСКИЕ СКАЗКИ
# ============================================

def show_tale(call: CallbackQuery):
    """
    Показывает случайную терапевтическую сказку
    """
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    user_data_dict = get_user_data_dict(user_id)
    
    # Определяем текущую проблему на основе профиля
    scores = {}
    for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = user_data_dict.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    # Находим самый слабый вектор
    if scores:
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector = min_vector[0]
        
        # Маппинг векторов на проблемы для сказок
        issue_map = {
            "СБ": "страх",
            "ТФ": "деньги",
            "УБ": "понимание",
            "ЧВ": "отношения"
        }
        issue = issue_map.get(vector, "рост")
    else:
        issue = "рост"
    
    # Получаем сказку
    try:
        tale = tales.get_tale_for_issue(issue)
        tale_title = tale.get("title", "Сказка на ночь")
    except:
        tale = None
        tale_title = "Сказка на ночь"
    
    if not tale:
        # Если сказка не найдена, используем заглушку
        tale = {
            "title": "Сказка на ночь",
            "text": "Жил-был человек, который искал ответы. Он ходил по миру, спрашивал мудрецов, читал книги. И однажды понял, что все ответы уже были внутри него. Просто нужно было время, чтобы их услышать."
        }
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_tale_event, args=(user_id, tale_title, issue), daemon=True).start()
    
    # Формируем текст
    text = f"📖 <b>{tale['title']}</b>\n\n{tale['text']}"
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📖 ЕЩЁ СКАЗКУ", callback_data="show_tale"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

# ============================================
# ПОКАЗ ПРЕИМУЩЕСТВ ТЕСТА
# ============================================

def show_benefits(call: CallbackQuery):
    """
    Показывает преимущества прохождения теста
    """
    user_id = call.from_user.id
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_benefits_view, args=(user_id,), daemon=True).start()
    
    text = f"""
🔍 **ЧТО ВЫ УЗНАЕТЕ О СЕБЕ:**

🧠 **ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ**
Линза, через которую вы смотрите на мир.

🧠 **ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ**
Как вы обрабатываете информацию.

🧠 **ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ**
Ваши автоматические реакции.

🧠 **ЭТАП 4: ТОЧКА РОСТА**
Где находится рычаг изменений.

🧠 **ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ**
Тип привязанности, защитные механизмы, базовые убеждения.

⚡ **ПОСЛЕ ТЕСТА ВЫ ПОЛУЧИТЕ:**

✅ Полный психологический портрет
✅ Глубинный анализ подсознательных паттернов
✅ Выбор стиля общения: 🔮 КОУЧ | 🧠 ПСИХОЛОГ | ⚡ ТРЕНЕР
✅ Индивидуальный навигатор по целям
✅ Напоминания и поддержка на пути

⏱ **Всего 15 минут**

👇 **Начинаем прямо сейчас?**
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🚀 НАЧАТЬ ТЕСТ", callback_data="start_stage_1_direct"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='Markdown', 
        delete_previous=True
    )

# ============================================
# ИДЕИ НА ВЫХОДНЫЕ
# ============================================

def show_weekend_ideas(call: CallbackQuery):
    """
    Показывает идеи на выходные
    """
    user_id = call.from_user.id
    user_name = get_user_name(user_id)
    user_data_dict = get_user_data_dict(user_id)
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_weekend_ideas_view, args=(user_id,), daemon=True).start()
    
    # Проверяем, есть ли профиль
    if not is_test_completed_check(user_data_dict):
        safe_send_message(
            call.message,
            "❓ Сначала нужно пройти тест, чтобы я понимал твой профиль. Используй /start",
            delete_previous=True
        )
        return
    
    text = f"""
🎨 {bold('ИДЕИ НА ВЫХОДНЫЕ')}

{user_name}, я подготовил для тебя несколько идей, как провести выходные с пользой и удовольствием.

Выбери, что тебя интересует:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏃 Активный отдых", callback_data="weekend_active"),
            InlineKeyboardButton(text="🧘 Расслабление", callback_data="weekend_relax")
        ],
        [
            InlineKeyboardButton(text="🎨 Творчество", callback_data="weekend_creative"),
            InlineKeyboardButton(text="📚 Саморазвитие", callback_data="weekend_learning")
        ],
        [
            InlineKeyboardButton(text="👥 Общение", callback_data="weekend_social"),
            InlineKeyboardButton(text="🏠 Домашний уют", callback_data="weekend_home")
        ],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_main")]
    ])
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

# ============================================
# ОБРАБОТКА ВОПРОСОВ ПОСЛЕ ПОМОЩИ
# ============================================

def process_help_question(message: Message, user_id: int, text: str, category: str):
    """
    Обрабатывает вопрос, заданный через категорию помощи
    """
    user_data_dict = get_user_data_dict(user_id)
    
    # ✅ ИСПРАВЛЕНО: синхронный вызов
    threading.Thread(target=log_help_event, args=(user_id, 'question_asked', category), daemon=True).start()
    
    # Проверяем, завершен ли тест
    if not is_test_completed_check(user_data_dict):
        # Если тест не пройден, предлагаем пройти
        response = f"""
Спасибо за вопрос в категории "{category}".

Чтобы я мог ответить точнее с учётом твоего профиля, рекомендую сначала пройти тест (15 минут).

А пока — вот общий ответ:
        """
        
        # Общие ответы по категориям
        general_responses = {
            "relations": "В отношениях важно помнить, что каждый человек — отдельный мир со своими страхами и желаниями. Иногда достаточно просто быть рядом и слушать.",
            "money": "Деньги — это энергия, которая приходит и уходит. Важно не количество, а ваше отношение к ним. Начните с благодарности за то, что уже есть.",
            "self": "Самоощущение меняется каждый день. Разрешите себе чувствовать всё, что приходит, без осуждения.",
            "knowledge": "Знания — это путь, а не цель. Важно не то, сколько вы знаете, а то, как вы это применяете.",
            "support": "Просить о поддержке — это нормально. Вы не одиноки в своих переживаниях.",
            "muse": "Творчество — это игра. Иногда нужно просто начать, не думая о результате.",
            "care": "Забота о себе — это не эгоизм, а необходимость. Вы не можете дать другим то, чего нет у вас."
        }
        
        general = general_responses.get(category, "Я здесь, чтобы помочь. Расскажите подробнее.")
        
        full_response = f"{response}\n\n{general}"
        
        safe_send_message(
            message,
            full_response,
            parse_mode='HTML',
            delete_previous=True
        )
        return
    
    # Если тест пройден, используем режим для ответа
    from handlers.questions import process_text_question_sync
    process_text_question_sync(message, user_id, text)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_help',
    'handle_help_category',
    'show_tale',
    'show_benefits',
    'show_weekend_ideas',
    'process_help_question',
    'get_help_keyboard',
    'log_help_event',
    'log_tale_event',
    'log_benefits_view',
    'log_weekend_ideas_view'
]
