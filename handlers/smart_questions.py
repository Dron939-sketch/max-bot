#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для умных вопросов на основе профиля пользователя
Версия 1.0 - вынесено из handlers/questions.py
"""

import logging
import asyncio
from typing import Dict, Any, List

from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_delete_message
from formatters import clean_text_for_safe_display
from state import get_state_data, update_state_data
from confinement_model import level
from profiles import VECTORS
from services import text_to_speech
from handlers.voice import send_voice_to_max
from db_sync import sync_db

logger = logging.getLogger(__name__)


def generate_smart_questions(scores: Dict[str, float]) -> List[str]:
    """
    Генерирует вопросы на основе профиля
    """
    questions = []
    
    tf = level(scores.get("ТФ", 3))
    sb = level(scores.get("СБ", 3))
    ub = level(scores.get("УБ", 3))
    cv = level(scores.get("ЧВ", 3))
    
    # Вопросы про деньги (ТФ)
    if tf <= 2:
        questions.append("Как начать зарабатывать, если нет денег?")
        questions.append("Почему мне не везет с деньгами?")
    elif tf <= 4:
        questions.append("Как увеличить доход без новых вложений?")
        questions.append("Как создать финансовую подушку?")
    elif tf <= 6:
        questions.append("Как диверсифицировать источники дохода?")
        questions.append("Как начать инвестировать с умом?")
    
    # Вопросы про страх и защиту (СБ)
    if sb <= 2:
        questions.append("Как перестать бояться конфликтов?")
        questions.append("Как научиться говорить 'нет'?")
    elif sb <= 4:
        questions.append("Почему я злюсь внутри, но молчу?")
        questions.append("Как защищать границы без агрессии?")
    elif sb <= 6:
        questions.append("Как использовать свою силу во благо?")
        questions.append("Как защищать других, не выгорая?")
    
    # Вопросы про понимание мира (УБ)
    if ub <= 2:
        questions.append("Как понять, что происходит в жизни?")
        questions.append("Почему всё так сложно?")
    elif ub <= 4:
        questions.append("Как перестать искать заговоры?")
        questions.append("Как отличить правду от лжи?")
    elif ub <= 6:
        questions.append("Как видеть закономерности в хаосе?")
        questions.append("Как предсказывать развитие событий?")
    
    # Вопросы про отношения (ЧВ)
    if cv <= 2:
        questions.append("Как перестать зависеть от других?")
        questions.append("Почему меня бросают?")
    elif cv <= 4:
        questions.append("Как строить здоровые отношения?")
        questions.append("Почему отношения поверхностные?")
    elif cv <= 6:
        questions.append("Как создавать глубокие связи?")
        questions.append("Как быть лидером в отношениях?")
    
    # Общие вопросы
    general = [
        "С чего начать изменения?",
        "Что мне делать с этой ситуацией?",
        "Как не срываться на близких?",
        "Как найти своё призвание?",
        "Как обрести внутренний покой?"
    ]
    
    while len(questions) < 5:
        for q in general:
            if q not in questions and len(questions) < 5:
                questions.append(q)
    
    return questions[:5]


async def show_smart_questions(
    call: CallbackQuery,
    user_id: int,
    user_data_dict: Dict[str, Any],
    context_obj,
    is_test_completed_check_func
):
    """
    Показывает умные вопросы на основе профиля
    """
    if not is_test_completed_check_func(user_data_dict):
        text = f"""
🧠 **ФРЕДИ: СНАЧАЛА ПРОЙДИ ТЕСТ**

Чтобы я мог задавать точные вопросы, нужно знать твой профиль.

👇 Пройди тест (15 минут), и я смогу помогать глубже.
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🚀 ПРОЙТИ ТЕСТ", callback_data="show_stage_1_intro"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu"))
        
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
        return
    
    scores = {}
    for k in VECTORS:
        levels = user_data_dict.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    update_state_data(user_id, smart_questions=questions)
    
    mode = context_obj.communication_mode if context_obj else "coach"
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    if mode == "coach":
        header = f"{mode_config['emoji']} **ЗАДАЙТЕ ВОПРОС (КОУЧ)**\n\n"
        header += "Я буду задавать открытые вопросы, помогая вам найти ответы внутри себя.\n\n"
    elif mode == "psychologist":
        header = f"{mode_config['emoji']} **РАССКАЖИТЕ МНЕ (ПСИХОЛОГ)**\n\n"
        header += "Я здесь, чтобы помочь исследовать глубинные паттерны.\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} **ПОСТАВЬТЕ ЗАДАЧУ (ТРЕНЕР)**\n\n"
        header += "Чётко сформулируйте, что хотите решить. Я дам конкретные шаги.\n\n"
    else:
        header = f"❓ **ЗАДАЙТЕ ВОПРОС**\n\n"
    
    text = header + "👇 **Выберите вопрос или напишите свой:**"
    
    keyboard = InlineKeyboardMarkup()
    
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.add(InlineKeyboardButton(text=f"{q_short}", callback_data=f"ask_{i}"))
    
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
    keyboard.row(InlineKeyboardButton("🍏 Забота о себе", callback_data="help_cat_care"))
    keyboard.row(InlineKeyboardButton("✏️ Написать самому", callback_data="ask_question"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="show_results"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


async def handle_smart_question(
    call: CallbackQuery,
    question_num: int,
    user_id: int,
    user_data_dict: Dict[str, Any],
    context_obj,
    get_mode_func
):
    """
    Обрабатывает выбранный умный вопрос
    """
    data = get_state_data(user_id)
    questions = data.get("smart_questions", [])
    
    if question_num < 1 or question_num > len(questions):
        logger.error(f"❌ Неверный номер вопроса: {question_num}")
        return
    
    question = questions[question_num - 1]
    
    status_msg = safe_send_message(
        call.message,
        "🤔 Думаю над ответом...\n\nЭто займёт около 10-15 секунд",
        parse_mode=None,
        delete_previous=True
    )
    
    mode_name = context_obj.communication_mode if context_obj else "coach"
    mode = get_mode_func(mode_name, user_id, user_data_dict, context_obj)
    
    result = mode.process_question(question)
    response = result["response"]
    
    if "history" not in user_data_dict:
        user_data_dict["history"] = []
    user_data_dict["history"] = mode.history
    
    sync_db.save_user_to_db(user_id)
    
    clean_response = clean_text_for_safe_display(response)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("❓ Ещё вопрос", callback_data="smart_questions"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help"))
    
    suggestions_text = ""
    if result.get("suggestions"):
        suggestions_text = "\n\n" + "\n".join(result["suggestions"])
    
    if status_msg:
        try:
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        call.message,
        f"❓ **{question}**\n\n{clean_response}{suggestions_text}",
        reply_markup=keyboard,
        parse_mode=None,
        delete_previous=True
    )
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_data = loop.run_until_complete(text_to_speech(response, mode_name))
            if audio_data:
                success = loop.run_until_complete(send_voice_to_max(call.message.chat.id, audio_data))
                if success:
                    logger.info(f"🎙 Голосовой ответ отправлен пользователю {user_id}")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голоса: {e}")
