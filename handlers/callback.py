#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик всех callback-запросов для MAX
"""

import logging
from typing import Optional

from maxibot.types import CallbackQuery

# Импорты из наших модулей
from state import get_state, get_state_data, user_contexts, user_data
from message_utils import safe_send_message

# Импорты обработчиков этапов
from handlers.stages import (
    show_stage_1_intro, start_stage_1, handle_stage_1_answer,
    show_stage_2_intro, start_stage_2, handle_stage_2_answer,
    show_stage_3_intro, start_stage_3, handle_stage_3_answer,
    show_stage_4_intro, start_stage_4, handle_stage_4_answer,
    show_stage_5_intro, start_stage_5, handle_stage_5_answer,
    show_preliminary_profile, profile_confirm, profile_doubt, profile_reject,
    handle_goodbye, ask_whats_wrong, handle_discrepancy, clarify_next,
    handle_clarifying_answer
)

# Импорты обработчиков режимов
from handlers.modes import show_mode_selection, show_mode_selected, show_main_menu_after_mode

# Импорты обработчиков контекста
from handlers.context import handle_context_callback

# Импорты обработчиков reality check
from handlers.reality import handle_reality_callback

# Импорты обработчиков целей
from handlers.goals import (
    show_dynamic_destinations, handle_dynamic_destination,
    custom_destination, route_step_done
)

# Импорты обработчиков вопросов
from handlers.questions import (
    show_smart_questions, handle_smart_question, show_question_input
)

# Импорты обработчиков помощи
from handlers.help import show_help, show_benefits, show_tale

# Импорты обработчиков профиля
from handlers.profile import show_profile, show_ai_profile, show_psychologist_thought

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def handle_unknown_callback(call: CallbackQuery):
    """Обработка неизвестного callback"""
    logger.warning(f"⚠️ Неизвестный callback: {call.data}")
    safe_send_message(
        call.message,
        "🤔 Неизвестная команда. Пожалуйста, используйте меню.",
        delete_previous=True
    )

def handle_error_callback(call: CallbackQuery, error: Exception):
    """Обработка ошибок в callback"""
    logger.error(f"❌ Ошибка в callback {call.data}: {error}")
    safe_send_message(
        call.message,
        "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
        delete_previous=True
    )

# ============================================
# ОСНОВНОЙ ОБРАБОТЧИК
# ============================================

def callback_handler(call: CallbackQuery):
    """
    Единый обработчик всех callback'ов
    """
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"🔔 Обратный вызов: {data} от пользователя {user_id}")
    
    # ВРЕМЕННО: Заглушка для MAX API - просто логируем
    if data.startswith('stage'):
        logger.info(f"📝 Обработка ответа на этап: {data}")
    
    try:
        # ============================================
        # ЭТАП 1
        # ============================================
        if data == "show_stage_1_intro":
            logger.info(f"📢 show_stage_1_intro для пользователя {user_id}")
            state_data = get_state_data(user_id)
            show_stage_1_intro(call.message, user_id, state_data)
        
        elif data == "start_stage_1":
            logger.info(f"🎬 start_stage_1 для пользователя {user_id}")
            state_data = get_state_data(user_id)
            start_stage_1(call.message, user_id, state_data)
        
        elif data.startswith("stage1_"):
            logger.info(f"📥 stage1 ответ: {data}")
            state_data = get_state_data(user_id)
            handle_stage_1_answer(call, user_id, state_data)
        
        # ============================================
        # ЭТАП 2
        # ============================================
        elif data == "show_stage_2_intro":
            logger.info(f"📢 show_stage_2_intro для пользователя {user_id}")
            state_data = get_state_data(user_id)
            show_stage_2_intro(call.message, user_id, state_data)
        
        elif data == "start_stage_2":
            logger.info(f"🎬 start_stage_2 для пользователя {user_id}")
            state_data = get_state_data(user_id)
            start_stage_2(call.message, user_id, state_data)
        
        elif data.startswith("stage2_"):
            logger.info(f"📥 stage2 ответ: {data}")
            state_data = get_state_data(user_id)
            handle_stage_2_answer(call, user_id, state_data)
        
        # ============================================
        # ЭТАП 3
        # ============================================
        elif data == "show_stage_3_intro":
            logger.info(f"📢 show_stage_3_intro для пользователя {user_id}")
            state_data = get_state_data(user_id)
            show_stage_3_intro(call.message, user_id, state_data)
        
        elif data == "start_stage_3":
            logger.info(f"🎬 start_stage_3 для пользователя {user_id}")
            state_data = get_state_data(user_id)
            start_stage_3(call.message, user_id, state_data)
        
        elif data.startswith("stage3_"):
            logger.info(f"📥 stage3 ответ: {data}")
            state_data = get_state_data(user_id)
            handle_stage_3_answer(call, user_id, state_data)
        
        # ============================================
        # ЭТАП 4
        # ============================================
        elif data == "show_stage_4_intro":
            logger.info(f"📢 show_stage_4_intro для пользователя {user_id}")
            state_data = get_state_data(user_id)
            show_stage_4_intro(call.message, user_id, state_data)
        
        elif data == "start_stage_4":
            logger.info(f"🎬 start_stage_4 для пользователя {user_id}")
            state_data = get_state_data(user_id)
            start_stage_4(call.message, user_id, state_data)
        
        elif data.startswith("stage4_"):
            logger.info(f"📥 stage4 ответ: {data}")
            state_data = get_state_data(user_id)
            handle_stage_4_answer(call, user_id, state_data)
        
        # ============================================
        # ЭТАП 5
        # ============================================
        elif data == "show_stage_5_intro":
            logger.info(f"📢 show_stage_5_intro для пользователя {user_id}")
            state_data = get_state_data(user_id)
            show_stage_5_intro(call.message, user_id, state_data)
        
        elif data == "start_stage_5":
            logger.info(f"🎬 start_stage_5 для пользователя {user_id}")
            state_data = get_state_data(user_id)
            start_stage_5(call.message, user_id, state_data)
        
        elif data.startswith("stage5_"):
            logger.info(f"📥 stage5 ответ: {data}")
            state_data = get_state_data(user_id)
            handle_stage_5_answer(call, user_id, state_data)
        
        # ============================================
        # ПОДТВЕРЖДЕНИЕ ПРОФИЛЯ
        # ============================================
        elif data == "profile_confirm":
            logger.info(f"✅ profile_confirm для пользователя {user_id}")
            profile_confirm(call)
        
        elif data == "profile_doubt":
            logger.info(f"❓ profile_doubt для пользователя {user_id}")
            profile_doubt(call)
        
        elif data == "profile_reject":
            logger.info(f"🔄 profile_reject для пользователя {user_id}")
            profile_reject(call)
        
        elif data == "goodbye":
            logger.info(f"👋 goodbye для пользователя {user_id}")
            handle_goodbye(call)
        
        # ============================================
        # УТОЧНЯЮЩИЕ ВОПРОСЫ (ДОБАВЛЕНО!)
        # ============================================
        elif data.startswith("discrepancy_"):
            logger.info(f"🔍 discrepancy: {data} для пользователя {user_id}")
            discrepancy = data.replace("discrepancy_", "")
            handle_discrepancy(call, discrepancy)
        
        elif data == "clarify_next":
            logger.info(f"➡️ clarify_next для пользователя {user_id}")
            clarify_next(call)
        
        elif data.startswith("clarify_answer_"):
            logger.info(f"❓ clarify answer: {data} для пользователя {user_id}")
            handle_clarifying_answer(call)
        
        # ============================================
        # РЕЖИМЫ ОБЩЕНИЯ
        # ============================================
        elif data == "show_mode_selection":
            logger.info(f"🎭 show_mode_selection для пользователя {user_id}")
            show_mode_selection(call.message)
        
        elif data.startswith("mode_"):
            mode = data.replace("mode_", "")
            logger.info(f"🎭 Выбран режим: {mode} для пользователя {user_id}")
            show_mode_selected(call.message, mode)
        
        elif data == "back_to_mode_selected":
            logger.info(f"◀️ back_to_mode_selected для пользователя {user_id}")
            context = user_contexts.get(user_id)
            if context:
                show_main_menu_after_mode(call.message, context)
        
        # ============================================
        # КОНТЕКСТ (пол, возраст и т.д.)
        # ============================================
        elif data in ["set_gender_male", "set_gender_female", "set_gender_other"]:
            logger.info(f"👤 Выбор пола: {data} для пользователя {user_id}")
            handle_context_callback(call)
        
        # ============================================
        # REALITY CHECK
        # ============================================
        elif data in [
            "check_reality", "skip_life_context", "skip_goal_questions",
            "skip_to_route", "accept_feasibility_plan", "adjust_timeline", "reduce_goal"
        ]:
            logger.info(f"🔍 reality check: {data} для пользователя {user_id}")
            handle_reality_callback(call)
        
        # ============================================
        # ЦЕЛИ И МАРШРУТЫ
        # ============================================
        elif data == "show_dynamic_destinations":
            logger.info(f"🎯 show_dynamic_destinations для пользователя {user_id}")
            show_dynamic_destinations(call)
        
        elif data.startswith("dynamic_dest_"):
            logger.info(f"🎯 Выбор цели: {data} для пользователя {user_id}")
            handle_dynamic_destination(call)
        
        elif data == "custom_destination":
            logger.info(f"✏️ custom_destination для пользователя {user_id}")
            custom_destination(call)
        
        elif data == "route_step_done":
            logger.info(f"✅ route_step_done для пользователя {user_id}")
            route_step_done(call)
        
        # ============================================
        # ВОПРОСЫ И ПОМОЩЬ
        # ============================================
        elif data == "show_help":
            logger.info(f"❓ show_help для пользователя {user_id}")
            show_help(call.message)
        
        elif data == "show_benefits":
            logger.info(f"📖 show_benefits для пользователя {user_id}")
            show_benefits(call.message)
        
        elif data == "show_tale":
            logger.info(f"📚 show_tale для пользователя {user_id}")
            show_tale(call.message)
        
        elif data == "smart_questions":
            logger.info(f"🤔 smart_questions для пользователя {user_id}")
            show_smart_questions(call)
        
        elif data.startswith("smart_q_"):
            logger.info(f"❓ smart question ответ: {data} для пользователя {user_id}")
            handle_smart_question(call)
        
        elif data == "ask_pretest":
            logger.info(f"❓ ask_pretest для пользователя {user_id}")
            show_question_input(call.message, "pretest")
        
        elif data == "ask_question":
            logger.info(f"❓ ask_question для пользователя {user_id}")
            show_question_input(call.message, "general")
        
        # ============================================
        # ПРОФИЛЬ
        # ============================================
        elif data == "show_profile":
            logger.info(f"🧠 show_profile для пользователя {user_id}")
            show_profile(call.message, user_id)
        
        elif data == "show_ai_profile":
            logger.info(f"🤖 show_ai_profile для пользователя {user_id}")
            show_ai_profile(call.message, user_id)
        
        elif data == "psychologist_thought":
            logger.info(f"🧠 psychologist_thought для пользователя {user_id}")
            show_psychologist_thought(call.message, user_id)
        
        # ============================================
        # НЕИЗВЕСТНЫЙ CALLBACK
        # ============================================
        else:
            logger.warning(f"⚠️ Неизвестный callback: {data} от пользователя {user_id}")
            handle_unknown_callback(call)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в callback_handler для {data}: {e}")
        import traceback
        traceback.print_exc()
        handle_error_callback(call, e)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = ['callback_handler']
