#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики целей и маршрутов для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import logging
import time
from typing import Dict, Any, List, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Наши модули
from config import COMMUNICATION_MODES, DESTINATIONS
from message_utils import safe_send_message, safe_edit_message
from keyboards import (
    get_goals_categories_keyboard, get_goal_details_keyboard,
    get_back_keyboard, get_main_menu_after_mode_keyboard
)
from services import generate_route_ai
from reality_check import get_theoretical_path

# ✅ ИСПРАВЛЕНО: Импортируем из state, а не из main
from state import (
    user_data, user_contexts, user_state_data, user_states,
    get_state, set_state, get_state_data, update_state_data
)

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (теперь используют state)
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

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ ДЛЯ ЦЕЛЕЙ
# ============================================

def show_goals_categories(message, user_id: int):
    """Показывает категории целей"""
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = user_data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    text = f"""
🧠 <b>ФРЕДИ: КАТЕГОРИИ ЦЕЛЕЙ</b>

{user_name}, выбери категорию, которая сейчас актуальна.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

👇 <b>Куда двинемся?</b>
"""
    
    keyboard = get_goals_categories_keyboard()
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)

def show_goals_for_category(call: CallbackQuery, category: str):
    """Показывает цели для выбранной категории"""
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data.get("communication_mode", "coach")
    
    # Получаем цели для данной категории из DESTINATIONS
    destinations = DESTINATIONS.get(mode, DESTINATIONS["coach"])
    category_data = destinations.get(category, {})
    goals = category_data.get("destinations", [])
    
    if not goals:
        safe_send_message(
            call.message,
            "❌ В этой категории пока нет целей",
            reply_markup=get_back_keyboard("show_goals"),
            delete_previous=True
        )
        return
    
    category_name = category_data.get("name", category)
    category_desc = category_data.get("description", "")
    
    text = f"""
🧠 <b>{category_name}</b>

{category_desc}

👇 <b>Выбери конкретную цель:</b>
"""
    
    # Строим клавиатуру с целями
    keyboard = InlineKeyboardMarkup()
    for goal in goals:
        # Определяем эмодзи сложности
        difficulty_emoji = {
            "easy": "🟢",
            "medium": "🟡", 
            "hard": "🔴"
        }.get(goal.get("difficulty", "medium"), "⚪")
        
        button_text = f"{difficulty_emoji} {goal['name']} ({goal['time']})"
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_goal_{goal['id']}"
        ))
    
    keyboard.add(InlineKeyboardButton(
        text="◀️ НАЗАД", 
        callback_data="show_goals"
    ))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)

def select_goal(call: CallbackQuery, goal_id: str):
    """Выбирает конкретную цель и показывает её детали"""
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data.get("communication_mode", "coach")
    
    # Ищем цель по ID во всех категориях
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        safe_send_message(
            call.message,
            "❌ Цель не найдена",
            reply_markup=get_back_keyboard("show_goals"),
            delete_previous=True
        )
        return
    
    # Сохраняем выбранную цель
    update_user_state_data(user_id, current_goal=goal_info)
    
    text = f"""
🧠 <b>ВЫБРАННАЯ ЦЕЛЬ</b>

{user_name}, ты выбрал: <b>{goal_info['name']}</b>

📊 <b>Сложность:</b> {goal_info.get('difficulty', 'medium')}
⏱ <b>Ориентировочное время:</b> {goal_info.get('time', 'не указано')}

{goal_info.get('description', '')}

👇 <b>Что дальше?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🚀 ПОСТРОИТЬ МАРШРУТ", callback_data=f"build_route_{goal_id}"),
        InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data=f"check_reality_{goal_id}")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_goals")
    )
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)

def find_goal_by_id(goal_id: str, mode: str) -> Optional[Dict]:
    """Ищет цель по ID во всех категориях"""
    destinations = DESTINATIONS.get(mode, DESTINATIONS["coach"])
    
    for category_id, category in destinations.items():
        for goal in category.get("destinations", []):
            if goal.get("id") == goal_id:
                # Добавляем описание, если его нет
                if "description" not in goal:
                    goal["description"] = category.get("description", "")
                return goal
    return None

# ============================================
# ДИНАМИЧЕСКИЙ ПОДБОР ЦЕЛЕЙ
# ============================================

def get_dynamic_destinations(profile_code: str, mode: str) -> List[Dict]:
    """Динамически подбирает цели под профиль и режим"""
    
    # Парсим профиль (СБ-4_ТФ-4_УБ-4_ЧВ-4)
    parts = profile_code.split('_')
    scores = {}
    for part in parts:
        if '-' in part:
            vec, val = part.split('-')
            scores[vec] = int(val)
    
    if not scores:
        scores = {"СБ": 4, "ТФ": 4, "УБ": 4, "ЧВ": 4}
    
    # Находим слабые и сильные стороны
    sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
    weakest = sorted_vectors[0] if sorted_vectors else ("СБ", 4)
    strongest = sorted_vectors[-1] if sorted_vectors else ("ЧВ", 4)
    
    # База целей для разных режимов (ваша существующая база данных)
    destinations_db = {
        "coach": {
            "weak": {
                "СБ": [
                    {"id": "fear_work", "name": "Проработать страхи", "time": "3-4 недели", "difficulty": "medium", "description": "Исследуй свои страхи и научись с ними работать"},
                    # ... остальные цели
                ],
                # ... остальные векторы
            },
            # ... остальные режимы
        }
    }
    # ... (ваш существующий код с destinations_db)
    
    mode_db = destinations_db.get(mode, destinations_db["coach"])
    
    # Собираем цели
    destinations = []
    
    # Цели для слабого вектора
    if weakest[0] in mode_db["weak"]:
        destinations.extend(mode_db["weak"][weakest[0]])
    
    # Цели для сильного вектора (развитие силы)
    if strongest[0] in mode_db["strong"]:
        destinations.extend(mode_db["strong"][strongest[0]])
    
    # Добавляем общие цели
    destinations.extend(mode_db.get("general", []))
    
    # Убираем дубликаты по id
    seen = set()
    unique_destinations = []
    for dest in destinations:
        if dest["id"] not in seen:
            seen.add(dest["id"])
            unique_destinations.append(dest)
    
    return unique_destinations[:9]  # Не больше 9 целей

def show_dynamic_destinations(call: CallbackQuery):
    """Показывает динамически подобранные цели"""
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = user_data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем динамические цели
    destinations = get_dynamic_destinations(profile_code, mode)
    
    text = f"""
🧠 <b>ФРЕДИ: ЦЕЛИ ПО ТВОЕМУ ПРОФИЛЮ</b>

{user_name}, я проанализировал твой профиль и подобрал цели, которые сейчас наиболее актуальны.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

👇 <b>Куда двинемся?</b>
"""
    
    # Строим клавиатуру
    keyboard = InlineKeyboardMarkup()
    
    for dest in destinations:
        # Определяем эмодзи сложности
        difficulty_emoji = {
            "easy": "🟢",
            "medium": "🟡",
            "hard": "🔴"
        }.get(dest["difficulty"], "⚪")
        
        button_text = f"{difficulty_emoji} {dest['name']}"
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"dynamic_dest_{dest['id']}"
        ))
    
    keyboard.add(InlineKeyboardButton(
        text="✏️ Сформулирую сам", 
        callback_data="custom_destination"
    ))
    keyboard.add(InlineKeyboardButton(
        text="◀️ НАЗАД", 
        callback_data="back_to_mode_selected"
    ))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def handle_dynamic_destination(call: CallbackQuery):
    """Обрабатывает выбор динамической цели"""
    dest_id = call.data.replace("dynamic_dest_", "")
    
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    mode = user_data.get("communication_mode", "coach")
    profile_code = user_data.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем все цели
    all_destinations = get_dynamic_destinations(profile_code, mode)
    
    # Находим выбранную
    dest_info = None
    for dest in all_destinations:
        if dest["id"] == dest_id:
            dest_info = dest
            break
    
    if not dest_info:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Сохраняем выбранную цель
    update_user_state_data(user_id,
        current_destination=dest_info,
        route_step=1,
        route_progress=[]
    )
    
    # Показываем теоретический путь
    show_theoretical_path(call, dest_info)

def custom_destination(call: CallbackQuery):
    """Пользователь хочет сформулировать цель самостоятельно"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    text = f"""
🧠 <b>ФРЕДИ: СФОРМУЛИРУЙ ЦЕЛЬ</b>

{user_name}, расскажи своими словами, чего ты хочешь достичь.

Напиши мне сообщение с описанием цели, и я помогу построить маршрут.

👇 <b>Напиши свою цель:</b>
"""
    
    keyboard = get_back_keyboard("show_dynamic_destinations")
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    
    # ✅ ИСПРАВЛЕНО: используем импортированный user_states из state
    user_states[user_id] = "awaiting_custom_goal"

# ============================================
# МАРШРУТЫ К ЦЕЛЯМ
# ============================================

def show_theoretical_path(call: CallbackQuery, goal_info: Dict):
    """
    Показывает теоретический путь к цели после её выбора
    """
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal_id = goal_info.get("id", "income_growth")
    mode = user_data.get("communication_mode", "coach")
    
    # Получаем теоретический путь
    path = get_theoretical_path(goal_id, mode)
    
    # Сохраняем путь в состоянии
    update_user_state_data(user_id, theoretical_path=path)
    
    text = f"""
🧠 <b>ФРЕДИ: ТВОЯ ЦЕЛЬ</b>

{user_name}, ты выбрал: <b>{goal_info.get('name', 'цель')}</b>
Режим: <b>{COMMUNICATION_MODES.get(mode, {}).get('name', 'КОУЧ')}</b>

👇 <b>ТЕОРЕТИЧЕСКИЙ МАРШРУТ:</b>

Чтобы достичь этой цели, в идеальном мире нужно:
{path['formatted_text']}

⚠️ Это в идеале. В реальности всё зависит от твоих условий.

👇 Хочешь проверить, насколько это реально для тебя?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data=f"check_reality_{goal_id}"))
    keyboard.row(InlineKeyboardButton("🔄 ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)

def build_route(call: CallbackQuery, goal_id: str):
    """Строит маршрут к цели (после проверки реальности или сразу)"""
    user_id = call.from_user.id
    state_data = get_user_state_data(user_id)
    user_data = get_user_data(user_id)
    
    # Получаем информацию о цели
    mode = user_data.get("communication_mode", "coach")
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        goal_info = state_data.get("current_destination")
    
    if not goal_info:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: <b>{goal_info.get('name')}</b>...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Генерируем маршрут через ИИ
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если цикл уже запущен, создаем задачу
            future = asyncio.run_coroutine_threadsafe(
                generate_route_ai(user_id, user_data, goal_info), loop
            )
            route = future.result(timeout=30)
        else:
            route = loop.run_until_complete(generate_route_ai(user_id, user_data, goal_info))
    except RuntimeError:
        route = asyncio.run(generate_route_ai(user_id, user_data, goal_info))
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации маршрута: {e}")
        route = None
    
    if route:
        update_user_state_data(user_id, current_route=route)
        show_route_step(call, 1, route, status_msg)
    else:
        # Если ИИ не сработал, показываем резервный маршрут
        show_fallback_route(call, goal_info, status_msg)

def show_route_step(call: CallbackQuery, step: int, route: Dict, status_msg=None):
    """Показывает текущий шаг маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data(user_id)
    user_data = get_user_data(user_id)
    
    destination = state_data.get("current_destination", {})
    mode = user_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    route_text = route.get('full_text', 'Маршрут строится...')
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

🎯 <b>Точка назначения:</b> {destination.get('name', 'цель')}
⏱ <b>Ориентировочное время:</b> {destination.get('time', 'не указано')}

{route_text}

👇 <b>Отмечай выполнение, когда готов(а)</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ВЫПОЛНИЛ ЭТАП", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_fallback_route(call: CallbackQuery, destination: dict, status_msg=None):
    """Резервный маршрут, если ИИ не отвечает"""
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    mode = user_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

🎯 <b>Точка назначения:</b> {destination.get('name', 'цель')}
⏱ <b>Ориентировочное время:</b> {destination.get('time', 'не указано')}

📍 <b>ЭТАП 1: ДИАГНОСТИКА</b>
   • <b>Что делаем:</b> анализируем текущую ситуацию
   • <b>📝 Домашнее задание:</b> записываем всё, что связано с целью
   • <b>✅ Критерий:</b> есть список наблюдений

📍 <b>ЭТАП 2: ПЛАНИРОВАНИЕ</b>
   • <b>Что делаем:</b> составляем пошаговый план
   • <b>📝 Домашнее задание:</b> разбиваем цель на микро-шаги
   • <b>✅ Критерий:</b> есть конкретный план

📍 <b>ЭТАП 3: ДЕЙСТВИЕ</b>
   • <b>Что делаем:</b> начинаем с первого микро-шага
   • <b>📝 Домашнее задание:</b> каждый день делать хотя бы одно действие
   • <b>✅ Критерий:</b> первый шаг сделан

👇 <b>Начинаем?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ НАЧАТЬ", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)

def route_step_done(call: CallbackQuery):
    """Отмечает выполнение этапа маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data(user_id)
    
    step = state_data.get("route_step", 1)
    route_progress = state_data.get("route_progress", [])
    
    route_progress.append(step)
    next_step = step + 1
    
    update_user_state_data(user_id,
        route_step=next_step,
        route_progress=route_progress
    )
    
    if next_step > 3:
        complete_route(call)
    else:
        safe_send_message(
            call.message,
            f"✅ <b>Этап {step} выполнен!</b>\n\nПереходим к этапу {next_step}...",
            parse_mode='HTML',
            delete_previous=True
        )
        time.sleep(1)
        
        route = state_data.get("current_route", {})
        show_route_step(call, next_step, route, None)

def complete_route(call: CallbackQuery):
    """Показывает завершение маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    destination = state_data.get("current_destination", {})
    
    text = f"""
🎉 <b>МАРШРУТ ЗАВЕРШЕН!</b>

Поздравляю, {user_name}! Ты достиг цели: <b>{destination.get('name', 'цель')}</b>

💪 <b>ГОРДИСЬ СОБОЙ!</b>

Хочешь выбрать новую цель или закрепить результат?

👇 <b>Выбери действие:</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🎯 НОВАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    # Очищаем данные маршрута
    update_user_state_data(user_id, route_step=None, current_destination=None, current_route=None)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_goals_categories',
    'show_goals_for_category',
    'select_goal',
    'show_dynamic_destinations',
    'handle_dynamic_destination',
    'custom_destination',
    'build_route',
    'show_route_step',
    'show_fallback_route',
    'route_step_done',
    'complete_route'
]
