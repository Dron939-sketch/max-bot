#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик всех callback-запросов для MAX
Версия 2.0 - ПОЛНАЯ с поддержкой state
"""

import logging
import asyncio
import traceback
from typing import Optional

from maxibot.types import CallbackQuery

# Импорты из наших модулей
from state import get_state, get_state_data, user_contexts, user_data, clear_state, update_state_data, get_user_name
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
from handlers.modes import (
    show_mode_selection, show_mode_selected, show_main_menu_after_mode,
    set_mode_coach, set_mode_psychologist, set_mode_trainer
)

# Импорты обработчиков контекста
from handlers.context import handle_context_callback, start_context

# Импорты обработчиков reality check
from handlers.reality import (
    show_reality_check, skip_life_context, skip_goal_questions,
    skip_to_route, accept_feasibility_plan, adjust_timeline, reduce_goal,
    apply_extended_timeline, select_goal_50, select_goal_30, select_goal_blocks
)

# Импорты обработчиков целей
from handlers.goals import (
    show_dynamic_destinations, handle_dynamic_destination,
    custom_destination, route_step_done, show_goals_categories,
    show_goals_for_category, select_goal, build_route
)

# Импорты обработчиков вопросов
from handlers.questions import (
    show_smart_questions, handle_smart_question, show_question_input
)

# Импорты обработчиков помощи
from handlers.help import show_help, show_benefits, show_tale, show_weekend_ideas

# Импорты обработчиков профиля
from handlers.profile import (
    show_profile, 
    show_ai_profile, 
    show_psychologist_thought,
    show_ai_profile_async,
    show_psychologist_thought_async
)

# Импорты обработчиков старта
from handlers.start import cmd_start, show_intro, show_why_details

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def handle_unknown_callback(call: CallbackQuery):
    """Обработка неизвестного callback"""
    user_id = call.from_user.id
    logger.warning(f"⚠️ Неизвестный callback: {call.data} от пользователя {user_id}")
    safe_send_message(
        call.message,
        "🤔 Неизвестная команда. Пожалуйста, используйте меню.",
        delete_previous=True
    )

def handle_error_callback(call: CallbackQuery, error: Exception):
    """Обработка ошибок в callback"""
    user_id = call.from_user.id
    logger.error(f"❌ Ошибка в callback {call.data} для пользователя {user_id}: {error}")
    traceback.print_exc()
    
    safe_send_message(
        call.message,
        "❌ Произошла техническая ошибка. Пожалуйста, попробуйте еще раз позже.\n\n"
        "Если ошибка повторяется, используйте /start для перезапуска.",
        delete_previous=True
    )

# ============================================
# ФУНКЦИЯ ПЕРЕЗАПУСКА ТЕСТА
# ============================================

def restart_test(call: CallbackQuery):
    """Перезапускает тест с начала"""
    user_id = call.from_user.id
    logger.info(f"🔄 Перезапуск теста для пользователя {user_id}")
    
    # Очищаем все данные пользователя
    if user_id in user_data:
        # Сохраняем только базовую информацию
        user_data[user_id] = {
            "perception_type": None,
            "thinking_level": None,
            "behavioral_levels": {},
            "dilts_counts": {},
            "deep_patterns": {},
            "profile_data": {},
            "ai_generated_profile": None
        }
    
    # Очищаем состояние
    clear_state(user_id)
    
    # Отправляем сообщение о перезапуске
    safe_send_message(
        call.message,
        "🔄 Перезапускаю тест...\n\n"
        "Все предыдущие ответы сброшены. Начинаем заново!",
        delete_previous=True
    )
    
    # Показываем введение в этап 1
    from handlers.stages import show_stage_1_intro
    state_data = get_state_data(user_id)
    show_stage_1_intro(call.message, user_id, state_data)

# ============================================
# АСИНХРОННЫЙ ОСНОВНОЙ ОБРАБОТЧИК
# ============================================

async def async_callback_handler(call: CallbackQuery):
    """
    Асинхронный обработчик всех callback'ов
    """
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"🔔 Асинхронный обратный вызов: {data} от пользователя {user_id}")
    
    try:
        # ============================================
        # ПРОФИЛЬ (асинхронные функции)
        # ============================================
        if data == "show_ai_profile":
            logger.info(f"🤖 show_ai_profile для пользователя {user_id}")
            await show_ai_profile_async(call.message, user_id)
        
        elif data == "psychologist_thought":
            logger.info(f"🧠 psychologist_thought для пользователя {user_id}")
            await show_psychologist_thought_async(call.message, user_id)
        
        # ============================================
        # ОСТАЛЬНЫЕ ОБРАБОТЧИКИ
        # ============================================
        else:
            await handle_sync_callback(call)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в async_callback_handler для {data}: {e}")
        traceback.print_exc()
        handle_error_callback(call, e)


async def handle_sync_callback(call: CallbackQuery):
    """Обработчик синхронных callback'ов"""
    user_id = call.from_user.id
    data = call.data
    state_data = get_state_data(user_id)
    
    # ============================================
    # ПЕРЕЗАПУСК ТЕСТА
    # ============================================
    if data == "restart_test":
        restart_test(call)
    
    # ============================================
    # ПОЧЕМУ ДЕТАЛИ (WHY DETAILS)
    # ============================================
    elif data == "why_details":
        logger.info(f"❓ why_details для пользователя {user_id}")
        show_why_details(call)
    
    # ============================================
    # КОНТЕКСТ
    # ============================================
    elif data == "start_context":
        logger.info(f"📝 start_context для пользователя {user_id}")
        start_context(call.message)
    
    # ============================================
    # ЭТАП 1
    # ============================================
    elif data == "show_stage_1_intro":
        logger.info(f"📢 show_stage_1_intro для пользователя {user_id}")
        show_stage_1_intro(call.message, user_id, state_data)
    
    elif data == "start_stage_1":
        logger.info(f"🎬 start_stage_1 для пользователя {user_id}")
        start_stage_1(call.message, user_id, state_data)
    
    elif data.startswith("stage1_"):
        logger.info(f"📥 stage1 ответ: {data}")
        handle_stage_1_answer(call, user_id, state_data)
    
    # ============================================
    # ЭТАП 2
    # ============================================
    elif data == "show_stage_2_intro":
        logger.info(f"📢 show_stage_2_intro для пользователя {user_id}")
        show_stage_2_intro(call.message, user_id, state_data)
    
    elif data == "start_stage_2":
        logger.info(f"🎬 start_stage_2 для пользователя {user_id}")
        start_stage_2(call.message, user_id, state_data)
    
    elif data.startswith("stage2_"):
        logger.info(f"📥 stage2 ответ: {data}")
        handle_stage_2_answer(call, user_id, state_data)
    
    # ============================================
    # ЭТАП 3
    # ============================================
    elif data == "show_stage_3_intro":
        logger.info(f"📢 show_stage_3_intro для пользователя {user_id}")
        show_stage_3_intro(call.message, user_id, state_data)
    
    elif data == "start_stage_3":
        logger.info(f"🎬 start_stage_3 для пользователя {user_id}")
        start_stage_3(call.message, user_id, state_data)
    
    elif data.startswith("stage3_"):
        logger.info(f"📥 stage3 ответ: {data}")
        handle_stage_3_answer(call, user_id, state_data)
    
    # ============================================
    # ЭТАП 4
    # ============================================
    elif data == "show_stage_4_intro":
        logger.info(f"📢 show_stage_4_intro для пользователя {user_id}")
        show_stage_4_intro(call.message, user_id, state_data)
    
    elif data == "start_stage_4":
        logger.info(f"🎬 start_stage_4 для пользователя {user_id}")
        start_stage_4(call.message, user_id, state_data)
    
    elif data.startswith("stage4_"):
        logger.info(f"📥 stage4 ответ: {data}")
        handle_stage_4_answer(call, user_id, state_data)
    
    # ============================================
    # ЭТАП 5
    # ============================================
    elif data == "show_stage_5_intro":
        logger.info(f"📢 show_stage_5_intro для пользователя {user_id}")
        show_stage_5_intro(call.message, user_id, state_data)
    
    elif data == "start_stage_5":
        logger.info(f"🎬 start_stage_5 для пользователя {user_id}")
        start_stage_5(call.message, user_id, state_data)
    
    elif data.startswith("stage5_"):
        logger.info(f"📥 stage5 ответ: {data}")
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
    # УТОЧНЯЮЩИЕ ВОПРОСЫ
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
    # РЕЖИМЫ ОБЩЕНИЯ (НОВЫЙ ФОРМАТ)
    # ============================================
    elif data == "show_mode_selection":
        logger.info(f"🎭 show_mode_selection для пользователя {user_id}")
        show_mode_selection(call.message)
    
    elif data == "set_mode_coach":
        logger.info(f"🎭 Установка режима: coach для пользователя {user_id}")
        update_state_data(user_id, communication_mode="coach")
        show_mode_selected(call.message, "coach")
    
    elif data == "set_mode_psychologist":
        logger.info(f"🎭 Установка режима: psychologist для пользователя {user_id}")
        update_state_data(user_id, communication_mode="psychologist")
        show_mode_selected(call.message, "psychologist")
    
    elif data == "set_mode_trainer":
        logger.info(f"🎭 Установка режима: trainer для пользователя {user_id}")
        update_state_data(user_id, communication_mode="trainer")
        show_mode_selected(call.message, "trainer")
    
    # ============================================
    # РЕЖИМЫ ОБЩЕНИЯ (СТАРЫЙ ФОРМАТ - ДЛЯ СОВМЕСТИМОСТИ)
    # ============================================
    elif data == "mode_coach":
        logger.info(f"🎭 Выбран режим: coach (старый формат) для пользователя {user_id}")
        update_state_data(user_id, communication_mode="coach")
        show_mode_selected(call.message, "coach")
    
    elif data == "mode_psychologist":
        logger.info(f"🎭 Выбран режим: psychologist (старый формат) для пользователя {user_id}")
        update_state_data(user_id, communication_mode="psychologist")
        show_mode_selected(call.message, "psychologist")
    
    elif data == "mode_trainer":
        logger.info(f"🎭 Выбран режим: trainer (старый формат) для пользователя {user_id}")
        update_state_data(user_id, communication_mode="trainer")
        show_mode_selected(call.message, "trainer")
    
    elif data == "back_to_mode_selected":
        logger.info(f"◀️ back_to_mode_selected для пользователя {user_id}")
        context = user_contexts.get(user_id)
        if context:
            mode = context.communication_mode or "coach"
            show_mode_selected(call.message, mode)
    
    # ============================================
    # КОНТЕКСТ (пол, возраст и т.д.)
    # ============================================
    elif data in ["set_gender_male", "set_gender_female", "set_gender_other"]:
        logger.info(f"👤 Выбор пола: {data} для пользователя {user_id}")
        handle_context_callback(call)
    
    # ============================================
    # REALITY CHECK
    # ============================================
    elif data == "check_reality":
        logger.info(f"🔍 check_reality для пользователя {user_id}")
        await show_reality_check(call, state_data)
    
    elif data == "skip_life_context":
        logger.info(f"⏭ skip_life_context для пользователя {user_id}")
        await skip_life_context(call, state_data)
    
    elif data == "skip_goal_questions":
        logger.info(f"⏭ skip_goal_questions для пользователя {user_id}")
        await skip_goal_questions(call, state_data)
    
    elif data == "skip_to_route":
        logger.info(f"⏭ skip_to_route для пользователя {user_id}")
        await skip_to_route(call, state_data)
    
    elif data == "accept_feasibility_plan":
        logger.info(f"✅ accept_feasibility_plan для пользователя {user_id}")
        await accept_feasibility_plan(call, state_data)
    
    elif data == "adjust_timeline":
        logger.info(f"🔄 adjust_timeline для пользователя {user_id}")
        await adjust_timeline(call, state_data)
    
    elif data == "reduce_goal":
        logger.info(f"📉 reduce_goal для пользователя {user_id}")
        await reduce_goal(call, state_data)
    
    elif data == "apply_extended_timeline":
        logger.info(f"⏱ apply_extended_timeline для пользователя {user_id}")
        await apply_extended_timeline(call, state_data)
    
    elif data == "select_goal_50":
        logger.info(f"📈 select_goal_50 для пользователя {user_id}")
        await select_goal_50(call, state_data)
    
    elif data == "select_goal_30":
        logger.info(f"📈 select_goal_30 для пользователя {user_id}")
        await select_goal_30(call, state_data)
    
    elif data == "select_goal_blocks":
        logger.info(f"🧱 select_goal_blocks для пользователя {user_id}")
        await select_goal_blocks(call, state_data)
    
    # ============================================
    # ЦЕЛИ И МАРШРУТЫ
    # ============================================
    elif data == "show_goals":
        logger.info(f"🎯 show_goals для пользователя {user_id}")
        show_goals_categories(call.message, user_id)
    
    elif data == "show_dynamic_destinations":
        logger.info(f"🎯 show_dynamic_destinations для пользователя {user_id}")
        await show_dynamic_destinations(call, state_data)
    
    elif data.startswith("goal_cat_"):
        logger.info(f"🎯 Категория целей: {data} для пользователя {user_id}")
        category = data.replace("goal_cat_", "")
        show_goals_for_category(call, category)
    
    elif data.startswith("select_goal_"):
        logger.info(f"🎯 Выбор цели: {data} для пользователя {user_id}")
        goal_id = data.replace("select_goal_", "")
        select_goal(call, goal_id)
    
    elif data.startswith("dynamic_dest_"):
        logger.info(f"🎯 Выбор динамической цели: {data} для пользователя {user_id}")
        await handle_dynamic_destination(call, state_data)
    
    elif data == "custom_destination":
        logger.info(f"✏️ custom_destination для пользователя {user_id}")
        await custom_destination(call, state_data)
    
    elif data == "route_step_done":
        logger.info(f"✅ route_step_done для пользователя {user_id}")
        await route_step_done(call, state_data)
    
    elif data.startswith("build_route_"):
        logger.info(f"🛤 build_route: {data} для пользователя {user_id}")
        goal_id = data.replace("build_route_", "")
        await build_route(call, state_data, goal_id)
    
    # ============================================
    # ВОПРОСЫ И ПОМОЩЬ
    # ============================================
    elif data == "show_help":
        logger.info(f"❓ show_help для пользователя {user_id}")
        show_help(call)
    
    elif data == "show_benefits":
        logger.info(f"📖 show_benefits для пользователя {user_id}")
        show_benefits(call)
    
    elif data == "show_tale":
        logger.info(f"📚 show_tale для пользователя {user_id}")
        show_tale(call)
    
    elif data == "weekend_ideas":
        logger.info(f"🎨 weekend_ideas для пользователя {user_id}")
        show_weekend_ideas(call)
    
    elif data == "smart_questions":
        logger.info(f"🤔 smart_questions для пользователя {user_id}")
        show_smart_questions(call)
    
    elif data.startswith("smart_q_"):
        logger.info(f"❓ smart question ответ: {data} для пользователя {user_id}")
        try:
            question_num = int(data.replace("smart_q_", ""))
            handle_smart_question(call, question_num)
        except ValueError:
            logger.error(f"❌ Неверный формат smart_q: {data}")
    
    elif data == "ask_pretest":
        logger.info(f"❓ ask_pretest для пользователя {user_id}")
        show_question_input(call)
    
    elif data == "ask_question":
        logger.info(f"❓ ask_question для пользователя {user_id}")
        show_question_input(call)
    
    elif data == "ask_hypnosis":
        logger.info(f"🧠 ask_hypnosis для пользователя {user_id}")
        from handlers.help import show_tale
        show_tale(call)
    
    # ============================================
    # ПРОФИЛЬ (синхронные версии)
    # ============================================
    elif data == "show_profile":
        logger.info(f"🧠 show_profile для пользователя {user_id}")
        show_profile(call.message, user_id)
    
    elif data == "show_results":
        logger.info(f"📊 show_results для пользователя {user_id}")
        show_profile(call.message, user_id)
    
    # ============================================
    # НАВИГАЦИЯ
    # ============================================
    elif data == "back_to_main":
        logger.info(f"◀️ back_to_main для пользователя {user_id}")
        context = user_contexts.get(user_id)
        if context:
            from handlers.modes import show_main_menu_after_mode
            show_main_menu_after_mode(call.message, context)
    
    elif data == "back_to_results":
        logger.info(f"◀️ back_to_results для пользователя {user_id}")
        show_profile(call.message, user_id)
    
    elif data == "back_to_intro":
        logger.info(f"◀️ back_to_intro для пользователя {user_id}")
        show_intro(call.message)
    
    # ✅ ДОБАВЛЕНО: обработка back_to_start
    elif data == "back_to_start":
        logger.info(f"◀️ back_to_start для пользователя {user_id}")
        from handlers.start import cmd_start
        # Создаем фейковое сообщение для cmd_start
        class FakeMessage:
            def __init__(self, user_id, chat_id):
                self.from_user = type('obj', (), {'id': user_id, 'first_name': get_user_name(user_id)})
                self.chat = type('obj', (), {'id': chat_id})
                self.text = '/start'
                self.message_id = call.message.message_id
        
        fake_msg = FakeMessage(user_id, call.message.chat.id)
        cmd_start(fake_msg)
    
    # ✅ ДОБАВЛЕНО: обработка back_to_context (возврат к контексту из начала теста)
    elif data == "back_to_context":
        logger.info(f"◀️ back_to_context для пользователя {user_id}")
        from handlers.context import start_context
        start_context(call.message)
    
    # ============================================
    # ИГНОРИРУЕМЫЕ CALLBACK'И
    # ============================================
    elif data == "ignore":
        logger.debug(f"⏭ Игнорируем callback: {data}")
        # Просто игнорируем
    
    # ============================================
    # НЕИЗВЕСТНЫЙ CALLBACK
    # ============================================
    else:
        logger.warning(f"⚠️ Неизвестный callback: {data} от пользователя {user_id}")
        handle_unknown_callback(call)


# ============================================
# СИНХРОННАЯ ОБЕРТКА ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================

def callback_handler(call: CallbackQuery):
    """
    Синхронная обертка для асинхронного обработчика callback'ов
    """
    try:
        # Пытаемся получить текущий цикл событий
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Нет запущенного цикла - создаем новый и запускаем
        asyncio.run(async_callback_handler(call))
    else:
        # Есть запущенный цикл - создаем задачу
        asyncio.create_task(async_callback_handler(call))


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = ['callback_handler']
