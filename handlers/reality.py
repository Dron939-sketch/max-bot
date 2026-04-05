#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики проверки реальности для MAX
Версия 2.2 - ИСПРАВЛЕНЫ ВЫЗОВЫ generate_route_ai
"""

import logging
import re
import time
import asyncio
import threading
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

# БД импортируется лениво внутри функций

logger = logging.getLogger(__name__)

# ============================================
# ✅ ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ АСИНХРОННЫХ ВЫЗОВОВ
# ============================================

def run_async_task(coro_func, *args, **kwargs):
    def _wrapper():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            coro = coro_func(*args, **kwargs)
            loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"❌ Ошибка в асинхронной задаче: {e}")
        finally:
            loop.close()
    threading.Thread(target=_wrapper, daemon=True).start()

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_context(user_id: int):
    return user_contexts.get(user_id)

def get_user_name(user_id: int) -> str:
    return user_names.get(user_id, "друг")

def set_user_state(user_id: int, state: str):
    user_states[user_id] = state

def ensure_state_dict(state_data, user_id: int) -> Dict:
    if state_data is None:
        return get_user_state_data(user_id)
    if isinstance(state_data, dict):
        return state_data
    logger.warning(f"⚠️ state_data не является словарем: {type(state_data)}. Создаем новый.")
    return get_user_state_data(user_id)

# ============================================
# ✅ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ============================================

async def save_reality_check_to_db(user_id: int, goal: Dict, result: Dict):
    try:
        from db_instance import db
        await db.log_event(user_id, 'reality_check_completed', {
            'goal_id': goal.get('id'), 'goal_name': goal.get('name'),
            'deficit': result.get('deficit'), 'status': result.get('status_text'),
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результата проверки для {user_id}: {e}")

async def save_life_context_to_db(user_id: int):
    try:
        from db_instance import save_user_to_db
        save_user_to_db(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения жизненного контекста для {user_id}: {e}")

async def save_goal_context_to_db(user_id: int, goal_context: Dict):
    try:
        from db_instance import save_user_to_db
        user_data_dict = get_user_data(user_id)
        user_data_dict['goal_context'] = goal_context
        save_user_to_db(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения целевого контекста для {user_id}: {e}")

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ ПРОВЕРКИ РЕАЛЬНОСТИ
# ============================================

async def show_reality_check(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    context = get_user_context(user_id)

    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'reality_check_started', {})
    except Exception:
        pass

    if not state_data.get("current_destination"):
        user_data_dict = get_user_data(user_id)
        if user_data_dict.get("current_destination"):
            update_user_state_data(user_id, current_destination=user_data_dict["current_destination"])
            state_data = get_user_state_data(user_id)

    goal = state_data.get("current_destination")

    if not goal:
        text = "🧠 ФРЕДИ: СНАЧАЛА ВЫБЕРИ ЦЕЛЬ\n\nЧтобы проверить реальность, нужно знать, к чему мы стремимся.\n\n👇 Сначала выбери цель:"
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
        return

    if not (context and hasattr(context, 'life_context_complete') and context.life_context_complete):
        await start_life_context_collection(call, goal, state_data)
    else:
        await ask_goal_specific_questions(call, goal, state_data)


async def start_life_context_collection(call: CallbackQuery, goal: Dict, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    user_name = get_user_name(user_id)
    questions = generate_life_context_questions()
    text = f"🧠 ФРЕДИ: ДАВАЙ ПОЗНАКОМИМСЯ С ТВОЕЙ РЕАЛЬНОСТЬЮ\n\n{user_name}, чтобы понять, что потребуется для твоей цели \"{goal.get('name', 'цель')}\", мне нужно знать твои условия.\n\nЭто вопросы на 2 минуты. Ответь коротко (можно одним сообщением все сразу):\n\n{questions}\n\n👇 Напиши ответы одним сообщением:"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (будет неточно)", callback_data="skip_life_context"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    set_user_state(user_id, "collecting_life_context")
    update_user_state_data(user_id, pending_goal=goal)


async def ask_goal_specific_questions(call: CallbackQuery, goal: Dict, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    goal_id = goal.get("id", "income_growth")
    goal_name = goal.get("name", "цель")
    mode = user_data_dict.get("communication_mode", "coach")
    profile = user_data_dict.get("profile_data", {})
    questions = generate_goal_context_questions(goal_id, profile, mode, goal_name)
    text = f"🧠 ФРЕДИ: УТОЧНЯЮ ПОД ТВОЮ ЦЕЛЬ\n\n{user_name}, твоя цель: {goal_name}\n\nЧтобы точно рассчитать маршрут с учётом твоих условий, ответь на несколько вопросов:\n\n{questions}\n\n👇 Напиши ответы (можно по порядку):"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (общий план)", callback_data="skip_goal_questions"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    set_user_state(user_id, "collecting_goal_context")
    update_user_state_data(user_id, pending_goal=goal)


# ============================================
# ОБРАБОТЧИКИ ОТВЕТОВ
# ============================================

async def process_life_context(message: Message, user_id: int = None, text: str = None):
    if user_id is None:
        user_id = message.from_user.id
    if text is None:
        text = message.text
    context = get_user_context(user_id)
    if not context:
        from models import UserContext
        context = UserContext(user_id)
        user_contexts[user_id] = context
    try:
        parsed = parse_life_context_answers(text)
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
        context.raw_life_context = text
    context.life_context_complete = True
    run_async_task(save_life_context_to_db, user_id)
    state_data = get_user_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    if goal:
        from maxibot.types import CallbackQuery
        fake_call = CallbackQuery(id="fake", from_user=message.from_user,
            message=message, data="fake", chat_instance="")
        await ask_goal_specific_questions(fake_call, goal, state_data)
    else:
        from handlers.modes import show_main_menu_after_mode
        await show_main_menu_after_mode(message, context)


async def process_goal_context(message: Message, user_id: int = None, text: str = None):
    if user_id is None:
        user_id = message.from_user.id
    if text is None:
        text = message.text
    state_data = get_user_state_data(user_id)
    try:
        goal_context = parse_goal_context_answers(text)
    except Exception as e:
        logger.error(f"Ошибка при парсинге целевого контекста: {e}")
        goal_context = {"raw_answers": text, "time_per_week": 5, "budget": 0}
        time_match = re.search(r'(\d+)\s*часов', text, re.IGNORECASE)
        if time_match:
            goal_context["time_per_week"] = int(time_match.group(1))
        else:
            numbers = re.findall(r'\d+', text)
            if numbers:
                goal_context["time_per_week"] = int(numbers[0])
    update_user_state_data(user_id, goal_context=goal_context)
    run_async_task(save_goal_context_to_db, user_id, goal_context)
    from maxibot.types import CallbackQuery
    fake_call = CallbackQuery(id="fake", from_user=message.from_user,
        message=message, data="fake", chat_instance="")
    await calculate_and_show_feasibility(fake_call, user_id)


# ============================================
# РАСЧЁТ ДОСТИЖИМОСТИ
# ============================================

async def calculate_and_show_feasibility(call: CallbackQuery, user_id: int):
    state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    goal = state_data.get("current_destination") or state_data.get("pending_goal")
    if not goal:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    goal_id = goal.get("id", "income_growth")
    mode = user_data_dict.get("communication_mode", "coach")
    path = get_theoretical_path(goal_id, mode)
    life_context = {}
    if context:
        life_context = {
            "time_per_week": 0,
            "energy_level": getattr(context, 'energy_level', 5),
            "has_private_space": getattr(context, 'has_private_space', False),
            "support_people": getattr(context, 'support_people', None)
        }
    goal_context = state_data.get("goal_context", {})
    profile = user_data_dict.get("profile_data", {})
    result = calculate_feasibility(path, life_context, goal_context, profile)
    update_user_state_data(user_id, feasibility_result=result)
    run_async_task(save_reality_check_to_db, user_id, goal, result)
    status_emoji = "✅" if result['deficit'] < 30 else "⚠️" if result['deficit'] < 60 else "❌"
    text = f"🧠 ФРЕДИ: РЕАЛЬНОСТЬ ЦЕЛИ\n\n{status_emoji} {result['status_text']}\n\nТвоя цель: {goal.get('name', 'цель')}\n\n👇 ЧТО ПОТРЕБУЕТСЯ:\n{result['requirements_text']}\n\n👇 ЧТО У ТЕБЯ ЕСТЬ:\n{result['available_text']}\n\n📊 ДЕФИЦИТ РЕСУРСОВ: {result['deficit']}%\n\n{result['recommendation']}\n\n👇 Что делаем, {user_name}?"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ПРИНЯТЬ ПЛАН", callback_data="accept_feasibility_plan"))
    keyboard.row(InlineKeyboardButton("🔄 ИЗМЕНИТЬ СРОК", callback_data="adjust_timeline"))
    keyboard.row(InlineKeyboardButton("📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


# ============================================
# ОБРАБОТЧИКИ ПРОПУСКА И РЕШЕНИЙ
# ============================================

async def skip_life_context(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'life_context_skipped',
            {'goal_id': goal.get('id') if goal else None})
    except Exception:
        pass
    text = "🧠 ФРЕДИ: БУДЕТ НЕТОЧНО\n\nОк, пропускаем. Маршрут построю без учёта твоих условий — он будет общим.\n\nХочешь продолжить?"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ДА, ПОКАЖИ ПЛАН", callback_data="skip_to_route"))
    keyboard.row(InlineKeyboardButton("🔄 ВСЁ-ТАКИ ОТВЕТИТЬ", callback_data="check_reality"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


async def skip_goal_questions(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'goal_questions_skipped',
            {'goal_id': goal.get('id') if goal else None})
    except Exception:
        pass
    default_context = {"time_per_week": 5, "budget": 0}
    update_user_state_data(user_id, goal_context=default_context)
    run_async_task(save_goal_context_to_db, user_id, default_context)
    await calculate_and_show_feasibility(call, user_id)


async def skip_to_route(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    user_data_dict = get_user_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    if not goal:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'reality_check_skipped', {'goal_id': goal.get('id')})
    except Exception:
        pass
    status_msg = safe_send_message(call.message,
        f"🧠 Строю маршрут к цели: {goal.get('name')}...\n\nЭто займёт несколько секунд.",
        delete_previous=True)
    try:
        route = await generate_route_ai(user_id, user_data_dict, goal)
    except Exception as e:
        logger.error(f"❌ Ошибка генерации маршрута: {e}")
        route = None
    if route:
        update_user_state_data(user_id, current_route=route)
        from handlers.goals import show_route_step
        await show_route_step(call, state_data, 1, route, status_msg)
    else:
        from handlers.goals import show_fallback_route
        await show_fallback_route(call, state_data, goal, status_msg)


async def accept_feasibility_plan(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    user_data_dict = get_user_data(user_id)
    goal = state_data.get("current_destination")
    if not goal:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'feasibility_plan_accepted',
            {'goal_id': goal.get('id'), 'goal_name': goal.get('name')})
    except Exception:
        pass
    status_msg = safe_send_message(call.message,
        f"🧠 Строю маршрут к цели: {goal.get('name')}...\n\nЭто займёт несколько секунд.",
        delete_previous=True)
    try:
        route = await generate_route_ai(user_id, user_data_dict, goal)
    except Exception as e:
        logger.error(f"❌ Ошибка генерации маршрута: {e}")
        route = None
    if route:
        update_user_state_data(user_id, current_route=route)
        from handlers.goals import show_route_step
        await show_route_step(call, state_data, 1, route, status_msg)
    else:
        from handlers.goals import show_fallback_route
        await show_fallback_route(call, state_data, goal, status_msg)


async def adjust_timeline(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    goal = state_data.get("current_destination")
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'timeline_adjustment_started',
            {'goal_id': goal.get('id') if goal else None})
    except Exception:
        pass
    text = "🧠 ФРЕДИ: КОРРЕКТИРОВКА СРОКОВ\n\nТекущий срок: 6 месяцев\n\nЕсли увеличить срок до 12 месяцев, нагрузка снизится:\n• Время: с 13 ч/нед до 6-7 ч/нед\n• Энергия: с 7/10 до 5-6/10\n\nЭто сделает цель более реалистичной в твоих условиях.\n\n👇 Что выбираешь?"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ УВЕЛИЧИТЬ СРОК", callback_data="apply_extended_timeline"))
    keyboard.row(InlineKeyboardButton("🔄 ОСТАВИТЬ КАК ЕСТЬ", callback_data="accept_feasibility_plan"))
    keyboard.row(InlineKeyboardButton("📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


async def reduce_goal(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    goal = state_data.get("current_destination")
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'goal_reduction_started',
            {'goal_id': goal.get('id') if goal else None})
    except Exception:
        pass
    text = "🧠 ФРЕДИ: СНИЖЕНИЕ ПЛАНКИ\n\nВместо 'увеличить доход в 2 раза' можно выбрать:\n• Увеличить на 50% (реалистично за 6 месяцев)\n• Увеличить на 30% (легко за 3-4 месяца)\n• Проработать денежные блоки (подготовка)\n\n👇 Что выбираешь?"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📈 +50% (6 мес)", callback_data="select_goal_50"))
    keyboard.row(InlineKeyboardButton("📈 +30% (4 мес)", callback_data="select_goal_30"))
    keyboard.row(InlineKeyboardButton("🧠 ПРОРАБОТКА БЛОКОВ", callback_data="select_goal_blocks"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


async def apply_extended_timeline(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'extended_timeline_applied', {})
    except Exception:
        pass
    await accept_feasibility_plan(call, state_data)


async def select_goal_50(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    new_goal = {"id": "income_growth_50", "name": "Увеличить доход на 50%",
        "time": "6 месяцев", "difficulty": "medium", "description": "Постепенный и уверенный рост дохода"}
    update_user_state_data(user_id, current_destination=new_goal)
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'goal_reduced_to_50',
            {'original_goal': state_data.get("current_destination", {}).get('id')})
    except Exception:
        pass
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, state_data, new_goal)


async def select_goal_30(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    new_goal = {"id": "income_growth_30", "name": "Увеличить доход на 30%",
        "time": "4 месяца", "difficulty": "easy", "description": "Лёгкий и достижимый рост"}
    update_user_state_data(user_id, current_destination=new_goal)
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'goal_reduced_to_30',
            {'original_goal': state_data.get("current_destination", {}).get('id')})
    except Exception:
        pass
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, state_data, new_goal)


async def select_goal_blocks(call: CallbackQuery, state_data: Dict = None):
    user_id = call.from_user.id
    state_data = ensure_state_dict(state_data, user_id)
    new_goal = {"id": "money_blocks", "name": "Проработать денежные блоки",
        "time": "3-4 недели", "difficulty": "medium",
        "description": "Выяви и устрани внутренние препятствия"}
    update_user_state_data(user_id, current_destination=new_goal)
    try:
        from db_instance import db
        run_async_task(db.log_event, user_id, 'goal_changed_to_blocks',
            {'original_goal': state_data.get("current_destination", {}).get('id')})
    except Exception:
        pass
    from handlers.goals import show_theoretical_path
    await show_theoretical_path(call, state_data, new_goal)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_reality_check', 'start_life_context_collection', 'ask_goal_specific_questions',
    'process_life_context', 'process_goal_context', 'calculate_and_show_feasibility',
    'skip_life_context', 'skip_goal_questions', 'skip_to_route', 'accept_feasibility_plan',
    'adjust_timeline', 'reduce_goal', 'apply_extended_timeline',
    'select_goal_50', 'select_goal_30', 'select_goal_blocks',
    'save_reality_check_to_db', 'save_life_context_to_db', 'save_goal_context_to_db'
]
