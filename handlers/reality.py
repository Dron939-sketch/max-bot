#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики проверки реальности для MAX
Восстановлено из оригинального bot3.py и адаптировано
ИСПРАВЛЕНО: убраны await перед синхронными функциями safe_send_message
"""

import logging
import re
import time
import asyncio
from typing import Dict, Any, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import get_back_keyboard
from reality_check import (
    get_theoretical_path,
    generate_life_context_questions,
    generate_goal_context_questions,
    calculate_feasibility,
    parse_life_context_answers,
    parse_goal_context_answers
)
from services import generate_route_ai
from state import user_data, user_state_data, user_contexts, user_states, user_names

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_context(user_id: int):
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_name(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "друг")

def set_user_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ ПРОВЕРКИ РЕАЛЬНОСТИ
# ============================================

async def show_reality_check(call: CallbackQuery, state_data: Dict = None):
    """
    Запускает проверку реальности для выбранной цели
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    context = get_user_context(user_id)
    
    # ✅ Получаем данные из user_data, если в state_data нет
    if not state_data.get("current_destination"):
        # Пробуем найти в user_data
        user_data_dict = get_user_data(user_id)
        if user_data_dict.get("current_destination"):
            update_user_state_data(user_id, current_destination=user_data_dict["current_destination"])
            state_data = get_user_state_data(user_id)  # Обновляем
    
    # Проверяем, есть ли цель
    goal = state_data.get("current_destination")
    
    if not goal:
        text = f"""
🧠 **ФРЕДИ: СНАЧАЛА ВЫБЕРИ ЦЕЛЬ**

Чтобы проверить реальность, нужно знать, к чему мы стремимся.

👇 Сначала выбери цель:
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
        
        # Убираем await!
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
        return
    
    # Проверяем, есть ли базовый контекст
    if not (context and context.life_context_complete):
        # Если нет — собираем
        await start_life_context_collection(call, goal, state_data)
    else:
        # Если есть — задаём целевые вопросы
        await ask_goal_specific_questions(call, goal, state_data)

async def start_life_context_collection(call: CallbackQuery, goal: Dict, state_data: Dict = None):
    """
    Сбор базового контекста жизни (1 раз)
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    user_name = get_user_name(user_id)
    
    questions = generate_life_context_questions()
    
    text = f"""
🧠 **ФРЕДИ: ДАВАЙ ПОЗНАКОМИМСЯ С ТВОЕЙ РЕАЛЬНОСТЬЮ**

{user_name}, чтобы понять, что потребуется для твоей цели "**{goal.get('name', 'цель')}**", мне нужно знать твои условия.

Это вопросы на 2 минуты. Ответь коротко (можно одним сообщением все сразу):

{questions}

👇 **Напиши ответы одним сообщением или отправь голосовое сообщение 🎤**
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (будет неточно)", callback_data="skip_life_context"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    
    # Устанавливаем состояние
    set_user_state(user_id, "collecting_life_context")
    update_user_state_data(user_id, pending_goal=goal)

async def ask_goal_specific_questions(call: CallbackQuery, goal: Dict, state_data: Dict = None):
    """
    Задаёт вопросы, специфичные для цели
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal_id = goal.get("id", "income_growth")
    goal_name = goal.get("name", "цель")
    mode = user_data_dict.get("communication_mode", "coach")
    profile = user_data_dict.get("profile_data", {})
    
    questions = generate_goal_context_questions(goal_id, profile, mode, goal_name)
    
    text = f"""
🧠 **ФРЕДИ: УТОЧНЯЮ ПОД ТВОЮ ЦЕЛЬ**

{user_name}, твоя цель: **{goal_name}**

Чтобы точно рассчитать маршрут с учётом твоих условий, ответь на несколько вопросов:

{questions}

👇 **Напиши ответы (можно по порядку) или отправь голосовое сообщение 🎤**
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (общий план)", callback_data="skip_goal_questions"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    
    # Устанавливаем состояние
    set_user_state(user_id, "collecting_goal_context")
    update_user_state_data(user_id, pending_goal=goal)

# ============================================
# ОБРАБОТЧИКИ ОТВЕТОВ
# ============================================

async def process_life_context(message: Message, user_id: int, text: str):
    """Обрабатывает ответы на вопросы о жизненном контексте"""
    context = get_user_context(user_id)
    if not context:
        from models import UserContext
        context = UserContext(user_id)
        user_contexts[user_id] = context
    
    try:
        parsed = parse_life_context_answers(text)
        
        # Заполняем контекст из распарсенных данных
        context.family_status = parsed.get('family_status', 'не указано')
        context.has_children = parsed.get('has_children', False)
        context.children_ages = parsed.get('children_info', '')
        context.work_schedule = parsed.get('work_schedule', '')
        context.job_title = parsed.get('job_title', '')
        context.commute_time = parsed.get('commute_time', '')
        context.housing_type = parsed.get('housing_type', '')
        context.has_private_space = parsed.get('has_private_space', False)
        context.has_car = parsed.get('has_car', False)
        context.support_people = parsed.get('support_people', '')
        context.resistance_people = parsed.get('resistance_people', '')
        context.energy_level = parsed.get('energy_level', 5)
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге жизненного контекста: {e}")
        # Запасной вариант — просто сохраняем сырой ответ
        context.raw_life_context = text
    
    context.life_context_complete = True
    
    # Получаем сохранённую цель
    state_data = get_user_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    if goal:
        # Переходим к целевым вопросам
        from maxibot.types import CallbackQuery
        fake_call = CallbackQuery(
            id="fake",
            from_user=message.from_user,
            message=message,
            data="fake",
            chat_instance=""
        )
        # Запускаем асинхронную функцию
        await ask_goal_specific_questions(fake_call, goal)
    else:
        # Если цели нет, показываем меню
        from handlers.modes import show_main_menu_after_mode
        await show_main_menu_after_mode(message, context)

async def process_goal_context(message: Message, user_id: int, text: str):
    """Обрабатывает ответы на вопросы о целевом контексте"""
    state_data = get_user_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    try:
        goal_context = parse_goal_context_answers(text)
    except Exception as e:
        logger.error(f"Ошибка при парсинге целевого контекста: {e}")
        goal_context = {
            "raw_answers": text,
            "time_per_week": 5,
            "budget": 0
        }
        
        # Пробуем извлечь время
        time_match = re.search(r'(\d+)\s*часов', text, re.IGNORECASE)
        if time_match:
            goal_context["time_per_week"] = int(time_match.group(1))
        else:
            numbers = re.findall(r'\d+', text)
            if numbers and len(numbers) > 0:
                goal_context["time_per_week"] = int(numbers[0])
    
    update_user_state_data(user_id, goal_context=goal_context)
    
    # Переходим к расчёту
    from maxibot.types import CallbackQuery
    fake_call = CallbackQuery(
        id="fake",
        from_user=message.from_user,
        message=message,
        data="fake",
        chat_instance=""
    )
    # Запускаем асинхронную функцию
    await calculate_and_show_feasibility(fake_call, user_id)

# ============================================
# РАСЧЁТ ДОСТИЖИМОСТИ
# ============================================

async def calculate_and_show_feasibility(call: CallbackQuery, user_id: int):
    """
    Рассчитывает достижимость и показывает результат
    """
    state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal = state_data.get("current_destination") or state_data.get("pending_goal")
    if not goal:
        # Убираем await!
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    goal_id = goal.get("id", "income_growth")
    mode = user_data_dict.get("communication_mode", "coach")
    
    # Получаем теоретический путь
    path = get_theoretical_path(goal_id, mode)
    
    # Собираем контекст
    life_context = {}
    if context:
        life_context = {
            "time_per_week": 0,
            "energy_level": context.energy_level or 5,
            "has_private_space": context.has_private_space or False,
            "support_people": context.support_people or None
        }
    
    goal_context = state_data.get("goal_context", {})
    profile = user_data_dict.get("profile_data", {})
    
    # Рассчитываем
    result = calculate_feasibility(path, life_context, goal_context, profile)
    
    # Сохраняем результат
    update_user_state_data(user_id, feasibility_result=result)
    
    # Определяем статус
    status_emoji = "✅" if result['deficit'] < 30 else "⚠️" if result['deficit'] < 60 else "❌"
    
    text = f"""
🧠 **ФРЕДИ: РЕАЛЬНОСТЬ ЦЕЛИ**

{status_emoji} **{result['status_text']}**

Твоя цель: **{goal.get('name', 'цель')}**

👇 **ЧТО ПОТРЕБУЕТСЯ:**
{result['requirements_text']}

👇 **ЧТО У ТЕБЯ ЕСТЬ:**
{result['available_text']}

📊 **ДЕФИЦИТ РЕСУРСОВ:** {result['deficit']}%

{result['recommendation']}

👇 **Что делаем, {user_name}?**
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ПРИНЯТЬ ПЛАН", callback_data="accept_feasibility_plan"))
    keyboard.row(InlineKeyboardButton("🔄 ИЗМЕНИТЬ СРОК", callback_data="adjust_timeline"))
    keyboard.row(InlineKeyboardButton("📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)

# ============================================
# ОБРАБОТЧИКИ ПРОПУСКА
# ============================================

async def skip_life_context(call: CallbackQuery, state_data: Dict = None):
    """
    Пропускает сбор жизненного контекста
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    text = f"""
🧠 **ФРЕДИ: БУДЕТ НЕТОЧНО**

Ок, пропускаем. Маршрут построю без учёта твоих условий — он будет общим.

Хочешь продолжить?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ДА, ПОКАЖИ ПЛАН", callback_data="skip_to_route"))
    keyboard.row(InlineKeyboardButton("🔄 ВСЁ-ТАКИ ОТВЕТИТЬ", callback_data="check_reality"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)

async def skip_goal_questions(call: CallbackQuery, state_data: Dict = None):
    """
    Пропускает целевые вопросы
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    # Используем данные по умолчанию
    update_user_state_data(user_id, goal_context={"time_per_week": 5, "budget": 0})
    
    await calculate_and_show_feasibility(call, user_id)

async def skip_to_route(call: CallbackQuery, state_data: Dict = None):
    """
    Пропускает проверку и сразу строит маршрут
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    if not goal:
        # Убираем await!
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Отправляем статусное сообщение (без await!)
    status_msg = safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: **{goal.get('name')}**...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Генерируем маршрут (асинхронно)
    try:
        loop = asyncio.get_running_loop()
        route = loop.run_until_complete(generate_route_ai(user_id, user_data_dict, goal))
    except RuntimeError:
        route = await generate_route_ai(user_id, user_data_dict, goal)
    
    if route:
        update_user_state_data(user_id, current_route=route)
        from handlers.goals import show_route_step
        # show_route_step должна быть асинхронной
        await show_route_step(call, 1, route, status_msg)
    else:
        from handlers.goals import show_fallback_route
        await show_fallback_route(call, goal, status_msg)

# ============================================
# ОБРАБОТЧИКИ РЕШЕНИЙ ПОСЛЕ ПРОВЕРКИ
# ============================================

async def accept_feasibility_plan(call: CallbackQuery, state_data: Dict = None):
    """
    Принимает план и переходит к построению маршрута
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    
    goal = state_data.get("current_destination")
    
    if not goal:
        # Убираем await!
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Отправляем статусное сообщение (без await!)
    status_msg = safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: **{goal.get('name')}**...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Генерируем маршрут (асинхронно)
    try:
        loop = asyncio.get_running_loop()
        route = loop.run_until_complete(generate_route_ai(user_id, user_data_dict, goal))
    except RuntimeError:
        route = await generate_route_ai(user_id, user_data_dict, goal)
    
    if route:
        update_user_state_data(user_id, current_route=route)
        from handlers.goals import show_route_step
        await show_route_step(call, 1, route, status_msg)
    else:
        from handlers.goals import show_fallback_route
        await show_fallback_route(call, goal, status_msg)

async def adjust_timeline(call: CallbackQuery, state_data: Dict = None):
    """
    Предлагает скорректировать сроки
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    goal = state_data.get("current_destination")
    
    text = f"""
🧠 **ФРЕДИ: КОРРЕКТИРОВКА СРОКОВ**

Текущий срок: **6 месяцев**

Если увеличить срок до 12 месяцев, нагрузка снизится:
• Время: с 13 ч/нед до 6-7 ч/нед
• Энергия: с 7/10 до 5-6/10

Это сделает цель более реалистичной в твоих условиях.

👇 Что выбираешь?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ УВЕЛИЧИТЬ СРОК", callback_data="apply_extended_timeline"))
    keyboard.row(InlineKeyboardButton("🔄 ОСТАВИТЬ КАК ЕСТЬ", callback_data="accept_feasibility_plan"))
    keyboard.row(InlineKeyboardButton("📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)

async def reduce_goal(call: CallbackQuery, state_data: Dict = None):
    """
    Предлагает снизить планку цели
    """
    text = f"""
🧠 **ФРЕДИ: СНИЖЕНИЕ ПЛАНКИ**

Вместо "увеличить доход в 2 раза" можно выбрать:
• **Увеличить на 50%** (реалистично за 6 месяцев)
• **Увеличить на 30%** (легко за 3-4 месяца)
• **Проработать денежные блоки** (подготовка)

👇 Что выбираешь?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📈 +50% (6 мес)", callback_data="select_goal_50"))
    keyboard.row(InlineKeyboardButton("📈 +30% (4 мес)", callback_data="select_goal_30"))
    keyboard.row(InlineKeyboardButton("🧠 ПРОРАБОТКА БЛОКОВ", callback_data="select_goal_blocks"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    # Убираем await!
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)

async def apply_extended_timeline(call: CallbackQuery, state_data: Dict = None):
    """
    Применяет увеличенный срок и пересчитывает
    """
    # Пока просто принимаем план
    await accept_feasibility_plan(call, state_data)

async def select_goal_50(call: CallbackQuery, state_data: Dict = None):
    """
    Выбирает цель +50%
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    
    # Создаём новую цель с меньшей амбициозностью
    new_goal = {
        "id": "income_growth_50",
        "name": "Увеличить доход на 50%",
        "time": "6 месяцев",
        "difficulty": "medium",
        "description": "Постепенный и уверенный рост дохода"
    }
    
    update_user_state_data(user_id, current_destination=new_goal)
    
    # Показываем теоретический путь
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, new_goal)

async def select_goal_30(call: CallbackQuery, state_data: Dict = None):
    """
    Выбирает цель +30%
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    
    new_goal = {
        "id": "income_growth_30",
        "name": "Увеличить доход на 30%",
        "time": "4 месяца",
        "difficulty": "easy",
        "description": "Легкий и достижимый рост"
    }
    
    update_user_state_data(user_id, current_destination=new_goal)
    
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, new_goal)

async def select_goal_blocks(call: CallbackQuery, state_data: Dict = None):
    """
    Выбирает работу с блоками
    """
    user_id = call.from_user.id
    if state_data is None:
        state_data = get_user_state_data(user_id)
    
    new_goal = {
        "id": "money_blocks",
        "name": "Проработать денежные блоки",
        "time": "3-4 недели",
        "difficulty": "medium",
        "description": "Выяви и устрани внутренние препятствия"
    }
    
    update_user_state_data(user_id, current_destination=new_goal)
    
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, new_goal)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_reality_check',
    'start_life_context_collection',
    'ask_goal_specific_questions',
    'process_life_context',
    'process_goal_context',
    'calculate_and_show_feasibility',
    'skip_life_context',
    'skip_goal_questions',
    'skip_to_route',
    'accept_feasibility_plan',
    'adjust_timeline',
    'reduce_goal',
    'apply_extended_timeline',
    'select_goal_50',
    'select_goal_30',
    'select_goal_blocks'
]
