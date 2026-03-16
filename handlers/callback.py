#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик всех callback-запросов для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import logging
import time
from typing import Dict, Any

from bot_instance import bot
from maxibot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import (
    get_mode_selection_keyboard, get_mode_confirmation_keyboard,
    get_main_menu_keyboard, get_main_menu_after_mode_keyboard,
    get_profile_keyboard, get_ai_profile_keyboard,
    get_psychologist_thought_keyboard, get_restart_keyboard,
    get_goals_categories_keyboard, get_goal_details_keyboard,
    get_start_context_keyboard, get_why_details_keyboard,
    get_back_keyboard, get_cancel_keyboard
)

# Импортируем обработчики этапов
from .stages import (
    show_stage_1_intro, start_stage_1, handle_stage_1_answer,
    show_stage_2_intro, start_stage_2, handle_stage_2_answer,
    show_stage_3_intro, start_stage_3, handle_stage_3_answer,
    show_stage_4_intro, start_stage_4, handle_stage_4_answer,
    show_stage_5_intro, start_stage_5, handle_stage_5_answer,
    show_preliminary_profile
)

# Импортируем другие обработчики
from .modes import show_mode_selection, show_mode_selected
from .profile import (
    show_profile, show_ai_profile, show_psychologist_thought,
    show_final_profile, profile_confirm, profile_doubt, profile_reject,
    handle_goodbye, handle_discrepancy, clarify_next, handle_clarifying_answer
)
from .start import show_why_details, cmd_start

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ CALLBACK'ОВ
# ============================================

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    from state import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    from state import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    from state import user_data
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_context(user_id: int):
    """Получает контекст пользователя"""
    from state import user_contexts
    return user_contexts.get(user_id)

def set_user_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    from state import user_states
    user_states[user_id] = state

def get_state(user_id: int) -> str:
    """Получает состояние пользователя"""
    from state import user_states
    return user_states.get(user_id, "")

# ============================================
# ОСНОВНОЙ ОБРАБОТЧИК CALLBACK'ОВ
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    """Основной обработчик всех callback'ов"""
    
    user_id = call.from_user.id
    data = call.data
    
    # Получаем данные состояния
    state_data = get_user_state_data(user_id)
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    
    logger.info(f"🔔 Callback: {data} от пользователя {user_id}")
    
    # ============================================
    # ОБРАБОТЧИКИ НАВИГАЦИИ И ГЛАВНОГО МЕНЮ
    # ============================================
    
    # Возврат в главное меню
    if data == "main_menu":
        if context:
            show_main_menu_after_mode(call.message, context)
        else:
            cmd_start(call.message)
        return
    
    # Возврат к стартовому экрану
    elif data == "back_to_start":
        cmd_start(call.message)
        return
    
    # Показать детали о боте
    elif data == "why_details":
        show_why_details(call)
        return
    
    # Начать сбор контекста
    elif data == "start_context":
        from .context import start_context
        logger.info(f"🔘 Вызов start_context для user {user_id}")
        start_context(call.message)
        return
    
    # Пропустить контекст
    elif data == "skip_context":
        from .context import skip_context
        skip_context(call)
        return
    
    # Выбор пола
    elif data == "set_gender_male":
        from .context import set_gender_male
        set_gender_male(call)
        return
    elif data == "set_gender_female":
        from .context import set_gender_female
        set_gender_female(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ РЕЖИМОВ
    # ============================================
    
    # Показать выбор режима
    elif data == "show_modes":
        show_mode_selection(call.message)
        return
    
    # Установить конкретный режим
    elif data == "set_mode_coach":
        from .modes import set_mode_coach
        set_mode_coach(call)
        return
    elif data == "set_mode_psychologist":
        from .modes import set_mode_psychologist
        set_mode_psychologist(call)
        return
    elif data == "set_mode_trainer":
        from .modes import set_mode_trainer
        set_mode_trainer(call)
        return
    
    # Вернуться к выбору режима
    elif data == "back_to_modes":
        show_mode_selection(call.message)
        return
    
    # Вернуться к выбранному режиму
    elif data == "back_to_mode_selected":
        from .modes import back_to_mode_selected
        back_to_mode_selected(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ЭТАПОВ 1-5
    # ============================================
    
    # ЭТАП 1
    elif data == "show_stage_1_intro":
        show_stage_1_intro(call.message, user_id, state_data)
        set_user_state(user_id, "stage_1")
        return
    elif data == "start_stage_1":
        start_stage_1(call.message, user_id, state_data)
        return
    elif data.startswith("stage1_"):
        handle_stage_1_answer(call, user_id, state_data)
        return
    
    # ЭТАП 2
    elif data == "show_stage_2_intro":
        show_stage_2_intro(call.message, user_id, state_data)
        set_user_state(user_id, "stage_2")
        return
    elif data == "start_stage_2":
        start_stage_2(call.message, user_id, state_data)
        return
    elif data.startswith("stage2_"):
        handle_stage_2_answer(call, user_id, state_data)
        return
    
    # ЭТАП 3
    elif data == "show_stage_3_intro":
        show_stage_3_intro(call.message, user_id, state_data)
        set_user_state(user_id, "stage_3")
        return
    elif data == "start_stage_3":
        start_stage_3(call.message, user_id, state_data)
        return
    elif data.startswith("stage3_"):
        handle_stage_3_answer(call, user_id, state_data)
        return
    
    # ЭТАП 4
    elif data == "show_stage_4_intro":
        show_stage_4_intro(call.message, user_id, state_data)
        set_user_state(user_id, "stage_4")
        return
    elif data == "start_stage_4":
        start_stage_4(call.message, user_id, state_data)
        return
    elif data.startswith("stage4_"):
        handle_stage_4_answer(call, user_id, state_data)
        return
    
    # ЭТАП 5
    elif data == "show_stage_5_intro":
        show_stage_5_intro(call.message, user_id, state_data)
        set_user_state(user_id, "stage_5")
        return
    elif data == "start_stage_5":
        start_stage_5(call.message, user_id, state_data)
        return
    elif data.startswith("stage5_"):
        handle_stage_5_answer(call, user_id, state_data)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ПОДТВЕРЖДЕНИЯ ПРОФИЛЯ
    # ============================================
    
    elif data == "profile_confirm":
        profile_confirm(call)
        return
    elif data == "profile_doubt":
        profile_doubt(call)
        return
    elif data == "profile_reject":
        profile_reject(call)
        return
    elif data == "goodbye":
        handle_goodbye(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ РАСХОЖДЕНИЙ И УТОЧНЕНИЙ
    # ============================================
    
    elif data.startswith("discrepancy_"):
        disc = data.replace("discrepancy_", "")
        handle_discrepancy(call, disc)
        return
    elif data == "clarify_next":
        clarify_next(call)
        return
    elif data.startswith("clarify_answer_"):
        handle_clarifying_answer(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ РЕЗУЛЬТАТОВ И ПРОФИЛЯ
    # ============================================
    
    # Показать результаты (финальный профиль)
    elif data == "show_results":
        show_final_profile(call.message, user_id)
        return
    
    # Показать профиль
    elif data == "show_profile":
        show_profile(call.message, user_id)
        return
    
    # Показать AI-профиль
    elif data == "show_ai_profile":
        show_ai_profile(call.message, user_id)
        return
    
    # Показать мысли психолога
    elif data == "show_psychologist_thought":
        show_psychologist_thought(call.message, user_id)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ЦЕЛЕЙ
    # ============================================
    
    # Показать категории целей
    elif data == "show_goals":
        from .goals import show_goals_categories
        show_goals_categories(call.message, user_id)
        return
    
    # Выбрать категорию целей
    elif data.startswith("goals_"):
        from .goals import show_goals_for_category
        category = data.replace("goals_", "")
        show_goals_for_category(call, category)
        return
    
    # Выбрать конкретную цель
    elif data.startswith("select_goal_"):
        from .goals import select_goal
        goal_id = data.replace("select_goal_", "")
        select_goal(call, goal_id)
        return
    
    # Показать динамические цели
    elif data == "show_dynamic_destinations":
        from .goals import show_dynamic_destinations
        show_dynamic_destinations(call)
        return
    
    # Выбрать динамическую цель
    elif data.startswith("dynamic_dest_"):
        from .goals import handle_dynamic_destination
        handle_dynamic_destination(call)
        return
    
    # Сформулировать цель самостоятельно
    elif data == "custom_destination":
        from .goals import custom_destination
        custom_destination(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ МАРШРУТОВ
    # ============================================
    
    # Выполнен этап маршрута
    elif data == "route_step_done":
        from .goals import route_step_done
        route_step_done(call)
        return
    
    # Показать следующий шаг маршрута
    elif data == "next_route_step":
        from .goals import show_next_route_step
        show_next_route_step(call)
        return
    
    # Завершить маршрут
    elif data == "complete_route":
        from .goals import complete_route
        complete_route(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ПРОВЕРКИ РЕАЛЬНОСТИ
    # ============================================
    
    # Начать проверку реальности
    elif data == "check_reality":
        from .reality import show_reality_check
        show_reality_check(call)
        return
    
    # Пропустить сбор жизненного контекста
    elif data == "skip_life_context":
        from .reality import skip_life_context
        skip_life_context(call)
        return
    
    # Пропустить целевые вопросы
    elif data == "skip_goal_questions":
        from .reality import skip_goal_questions
        skip_goal_questions(call)
        return
    
    # Перейти к маршруту (пропуская проверку)
    elif data == "skip_to_route":
        from .reality import skip_to_route
        skip_to_route(call)
        return
    
    # Принять план после проверки
    elif data == "accept_feasibility_plan":
        from .reality import accept_feasibility_plan
        accept_feasibility_plan(call)
        return
    
    # Скорректировать сроки
    elif data == "adjust_timeline":
        from .reality import adjust_timeline
        adjust_timeline(call)
        return
    
    # Снизить планку
    elif data == "reduce_goal":
        from .reality import reduce_goal
        reduce_goal(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ВОПРОСОВ И ПОМОЩИ
    # ============================================
    
    # Показать умные вопросы
    elif data == "smart_questions":
        from .questions import show_smart_questions
        show_smart_questions(call)
        return
    
    # Выбрать умный вопрос
    elif data.startswith("ask_"):
        from .questions import handle_smart_question
        parts = data.split("_")
        if len(parts) > 1 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            state_data = get_user_state_data(user_id)
            questions = state_data.get("smart_questions", [])
            if 0 <= idx < len(questions):
                handle_smart_question(call, questions[idx])
        else:
            # Просто показать ввод вопроса
            from .questions import show_question_input
            show_question_input(call)
        return
    
    # Показать помощь
    elif data == "show_help":
        from .help import show_help
        show_help(call)
        return
    
    # Выбрать категорию помощи
    elif data.startswith("help_cat_"):
        from .help import handle_help_category
        category = data.replace("help_cat_", "")
        handle_help_category(call, category)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ СКАЗОК
    # ============================================
    
    # Показать сказку
    elif data == "show_tale":
        from .help import show_tale
        show_tale(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ АДМИНКИ
    # ============================================
    
    # Показать админ-панель
    elif data == "admin_panel":
        from .admin import show_admin_panel
        show_admin_panel(call)
        return
    
    # Показать статистику
    elif data == "admin_stats":
        from .admin import show_admin_stats
        show_admin_stats(call)
        return
    
    # Сделать рассылку
    elif data == "admin_broadcast":
        from .admin import start_broadcast
        start_broadcast(call)
        return
    
    # Показать список пользователей
    elif data == "admin_users":
        from .admin import show_users_list
        show_users_list(call)
        return
    
    # ============================================
    # ОБРАБОТЧИКИ ПЕРЕЗАПУСКА ТЕСТА
    # ============================================
    
    elif data == "restart_test":
        # Очищаем данные пользователя
        from state import user_data, user_state_data
        if user_id in user_data:
            user_data[user_id] = {}
        if user_id in user_state_data:
            user_state_data[user_id] = {}
        set_user_state(user_id, "")
        
        # Показываем стартовый экран
        cmd_start(call.message)
        return
    
    # ============================================
    # ОБРАБОТЧИК ПО УМОЛЧАНИЮ (если ничего не подошло)
    # ============================================
    
    else:
        logger.warning(f"⚠️ Неизвестный callback: {data}")
        safe_send_message(
            call.message,
            "❓ Неизвестная команда. Используйте кнопки меню.",
            reply_markup=get_back_keyboard("main_menu"),
            delete_previous=True
        )
        return


# ============================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОКАЗА МЕНЮ ПОСЛЕ ВЫБОРА РЕЖИМА
# ============================================

def show_main_menu_after_mode(message, context):
    """Показывает главное меню после выбора режима"""
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    # Обновляем погоду
    context.update_weather()
    day_context = context.get_day_context()
    
    text = f"{mode_config['emoji']} <b>РЕЖИМ {mode_config['display_name']}</b>\n\n"
    text += context.get_greeting(context.name) + "\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if hasattr(context, 'weather_cache') and context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n\n"
    
    text += f"🧠 <b>ЧЕМ ЗАЙМЁМСЯ?</b>\n\n"
    
    if context.communication_mode == "coach":
        text += "• Задать вопрос — я помогу найти ответ внутри себя\n"
    elif context.communication_mode == "psychologist":
        text += "• Расскажите, что у вас на душе — я помогу исследовать глубинные паттерны\n"
    elif context.communication_mode == "trainer":
        text += "• Поставьте задачу — я дам конкретные шаги\n"
    
    text += "• Выбрать тему — отношения, деньги, самоощущение\n"
    text += "• Послушать сказку — для глубокой работы\n"
    text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    keyboard = get_main_menu_after_mode_keyboard()
    
    safe_send_message(message, text, reply_markup=keyboard)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = ['callback_handler', 'show_main_menu_after_mode']
