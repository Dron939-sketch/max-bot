#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ОБЪЕДИНЕННЫЙ ФАЙЛ: Обработчики вопросов тестирования И умных вопросов
Версия для MAX - ПОЛНАЯ с голосовой поддержкой
"""

import logging
import re
import time
import random
import asyncio
import tempfile
import os
from typing import Dict, Any, List, Optional

from maxibot import MaxiBot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from maxibot.utils import BufferedInputFile

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import get_back_keyboard, get_main_menu_after_mode_keyboard
from formatters import bold, italic, calculate_progress, clean_text_for_safe_display

# Импорты из state.py
from state import (
    user_data, user_names, user_contexts,
    get_state, set_state, get_state_data, update_state_data, TestStates
)

# Импорты из profiles.py
from profiles import VECTORS, STAGE_1_FEEDBACK, STAGE_2_FEEDBACK, STAGE_3_FEEDBACK

# !!! ВАЖНО: импортируем level из confinement_model.py
from confinement_model import level

# Импорты из questions.py (основной файл с вопросами теста)
from questions import (
    get_stage1_question, get_stage1_total,
    get_stage2_question, get_stage2_total, get_stage2_score,
    get_stage3_question, get_stage3_total,
    get_stage4_question, get_stage4_total,
    get_stage5_question, get_stage5_total,
    get_clarifying_questions,
    analyze_stage5_results,
    map_to_stage3_feedback_level
)

# Импорты из services.py
from services import call_deepseek, text_to_speech, speech_to_text
from question_analyzer import create_analyzer_from_user_data

logger = logging.getLogger(__name__)

# ============================================
# ЧАСТЬ 1: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data_dict(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]


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
# ЧАСТЬ 2: ФУНКЦИИ ДЛЯ ЭТАПОВ ТЕСТИРОВАНИЯ
# ============================================

def determine_perception_type(scores: dict) -> str:
    """Определяет тип восприятия"""
    external = scores.get("EXTERNAL", 0)
    internal = scores.get("INTERNAL", 0)
    symbolic = scores.get("SYMBOLIC", 0)
    material = scores.get("MATERIAL", 0)
    
    attention = "EXTERNAL" if external > internal else "INTERNAL"
    anxiety = "SYMBOLIC" if symbolic > material else "MATERIAL"
    
    if attention == "EXTERNAL" and anxiety == "SYMBOLIC":
        return "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "EXTERNAL" and anxiety == "MATERIAL":
        return "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "INTERNAL" and anxiety == "SYMBOLIC":
        return "СМЫСЛО-ОРИЕНТИРОВАННЫЙ"
    else:
        return "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ"


def calculate_thinking_level_by_scores(level_scores_dict: dict) -> int:
    """Рассчитывает уровень мышления"""
    total_score = sum(level_scores_dict.values())
    
    if total_score <= 10:
        return 1
    elif total_score <= 20:
        return 2
    elif total_score <= 30:
        return 3
    elif total_score <= 40:
        return 4
    elif total_score <= 50:
        return 5
    elif total_score <= 60:
        return 6
    elif total_score <= 70:
        return 7
    elif total_score <= 80:
        return 8
    else:
        return 9


def get_level_group(level_num: int) -> str:
    """Группирует уровни"""
    if level_num <= 3:
        return "1-3"
    elif level_num <= 6:
        return "4-6"
    else:
        return "7-9"


def calculate_final_level(stage2_level: int, stage3_scores: list) -> int:
    """Рассчитывает финальный уровень"""
    if not stage3_scores:
        return stage2_level
    avg_behavior = sum(stage3_scores) / len(stage3_scores)
    return round((stage2_level + avg_behavior) / 2)


def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]


def calculate_profile_final(user_data_dict: dict) -> dict:
    """Финальный расчет профиля"""
    perception_type = user_data_dict.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    thinking_level = user_data_dict.get("thinking_level", 5)
    
    behavioral_levels = user_data_dict.get("behavioral_levels", {})
    
    sb_levels = behavioral_levels.get("СБ", [])
    tf_levels = behavioral_levels.get("ТФ", [])
    ub_levels = behavioral_levels.get("УБ", [])
    chv_levels = behavioral_levels.get("ЧВ", [])
    
    sb_avg = sum(sb_levels) / len(sb_levels) if sb_levels else 3
    tf_avg = sum(tf_levels) / len(tf_levels) if tf_levels else 3
    ub_avg = sum(ub_levels) / len(ub_levels) if ub_levels else 3
    chv_avg = sum(chv_levels) / len(chv_levels) if chv_levels else 3
    
    dilts_counts = user_data_dict.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_code = f"СБ-{round(sb_avg)}_ТФ-{round(tf_avg)}_УБ-{round(ub_avg)}_ЧВ-{round(chv_avg)}"
    
    return {
        "display_name": profile_code,
        "perception_type": perception_type,
        "thinking_level": thinking_level,
        "sb_level": round(sb_avg),
        "tf_level": round(tf_avg),
        "ub_level": round(ub_avg),
        "chv_level": round(chv_avg),
        "dominant_dilts": dominant_dilts,
        "dilts_counts": dilts_counts
    }


# ============================================
# ЭТАП 1: ВОСПРИЯТИЕ
# ============================================

def show_stage_1_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 1"""
    text = f"""
🧠 {bold('ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ')}

Восприятие — это линза, через которую вы смотрите на мир.

🔍 {bold('Что мы исследуем:')}
• Куда направлено ваше внимание — вовне или внутрь
• Какая тревога доминирует — страх отвержения или страх потери контроля

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Отвечайте честно — это поможет мне лучше понять вас.
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_1"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def start_stage_1(message, user_id: int, state_data: dict):
    """Начало этапа 1"""
    update_state_data(user_id,
        stage1_current=0,
        stage1_last_answered=-1,
        stage1_start_time=time.time(),
        perception_scores={"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0}
    )
    
    ask_stage_1_question(message, user_id)


def ask_stage_1_question(message, user_id: int):
    """Задаёт вопрос ЭТАПА 1"""
    data = get_state_data(user_id)
    
    current = data.get("stage1_current", 0)
    total = get_stage1_total()
    
    if current >= total:
        finish_stage_1(message, user_id)
        return
    
    question = get_stage1_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage1_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_stage_1_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 1"""
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage1_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage1_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        perception_scores = data.get("perception_scores", {})
        for axis, score in selected_option.get("scores", {}).items():
            if axis in ["EXTERNAL", "INTERNAL", "SYMBOLIC", "MATERIAL"]:
                perception_scores[axis] = perception_scores.get(axis, 0) + score
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 1,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'scores': selected_option.get('scores', {})
        })
        
        update_state_data(user_id,
            perception_scores=perception_scores,
            stage1_last_answered=current,
            stage1_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_1_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_1_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)


def finish_stage_1(message, user_id: int):
    """Завершение ЭТАПА 1"""
    data = get_state_data(user_id)
    
    perception_scores = data.get("perception_scores", {})
    perception_type = determine_perception_type(perception_scores)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["perception_type"] = perception_type
    
    logger.info(f"✅ User {user_id}: Stage 1 complete, type={perception_type}")
    
    result_text = STAGE_1_FEEDBACK.get(perception_type, STAGE_1_FEEDBACK["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"])
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 2')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 2", callback_data="show_stage_2_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.stage_2)


# ============================================
# ЭТАП 2: МЫШЛЕНИЕ
# ============================================

def show_stage_2_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 2"""
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    total_questions = get_stage2_total(perception_type)
    
    text = f"""
🧠 {bold('ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ')}

Восприятие определяет, что вы видите. Мышление — как вы это понимаете.

🎯 {bold('Самое важное:')}
Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте.

📊 {bold('Вопросов:')} {total_questions}
⏱ {bold('Время:')} ~3-4 минуты

Продолжим исследование?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_2"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def start_stage_2(message, user_id: int, state_data: dict):
    """Начало этапа 2"""
    update_state_data(user_id,
        stage2_current=0,
        stage2_last_answered=-1,
        stage2_start_time=time.time(),
        stage2_level_scores_dict={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0},
        strategy_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    ask_stage_2_question(message, user_id)


def ask_stage_2_question(message, user_id: int):
    """Задаёт вопрос ЭТАПА 2"""
    data = get_state_data(user_id)
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    current = data.get("stage2_current", 0)
    total_questions = get_stage2_total(perception_type)
    
    if current >= total_questions:
        finish_stage_2(message, user_id)
        return
    
    question = get_stage2_question(perception_type, current)
    if not question:
        finish_stage_2(message, user_id)
        return
    
    measures = question.get("measures", "thinking")
    progress = calculate_progress(current + 1, total_questions)
    
    question_text = f"""
🧠 {bold('ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for level_num, answer_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=answer_text,
            callback_data=f"stage2_{current}_{level_num}_{measures}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_stage_2_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 2"""
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        selected_level = parts[2]
        measures = parts[3]
        
        last_answered = data.get("stage2_last_answered", -1)
        if current <= last_answered:
            return
        
        perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception_type, current)
        if not question:
            return
        
        answer_text = question["options"].get(selected_level, "неизвестно")
        
        stage2_level_scores_dict = data.get("stage2_level_scores_dict", {})
        
        if measures == "thinking":
            points = get_stage2_score(perception_type, current, selected_level)
            stage2_level_scores_dict[selected_level] = stage2_level_scores_dict.get(selected_level, 0) + points
        
        strategy_levels = data.get("strategy_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if measures in ["СБ", "ТФ", "УБ", "ЧВ"]:
            try:
                value = int(selected_level)
                strategy_levels[measures].append(value)
            except ValueError:
                pass
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 2,
            'question_index': current,
            'question': question['text'],
            'answer': answer_text,
            'option': selected_level,
            'measures': measures,
            'perception_type': perception_type
        })
        
        update_state_data(user_id,
            stage2_level_scores_dict=stage2_level_scores_dict,
            strategy_levels=strategy_levels,
            stage2_last_answered=current,
            stage2_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_2_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_2_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)


def finish_stage_2(message, user_id: int):
    """Завершение ЭТАПА 2"""
    data = get_state_data(user_id)
    
    level_scores_dict = data.get("stage2_level_scores_dict", {})
    thinking_level = calculate_thinking_level_by_scores(level_scores_dict)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["thinking_level"] = thinking_level
    
    # Сохраняем стратегии
    strategy_levels = data.get("strategy_levels", {})
    user_data[user_id]["behavioral_levels"] = strategy_levels
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    level_group = get_level_group(thinking_level)
    
    logger.info(f"✅ User {user_id}: Stage 2 complete, level={thinking_level}")
    
    result_text = STAGE_2_FEEDBACK.get((perception_type, level_group))
    if not result_text:
        result_text = STAGE_2_FEEDBACK[("СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "1-3")]
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 3')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 3", callback_data="show_stage_3_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.stage_3)


# ============================================
# ЭТАП 3: ПОВЕДЕНИЕ
# ============================================

def show_stage_3_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 3"""
    text = f"""
🧠 {bold('ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ')}

Восприятие определяет, что вы видите.
Мышление — как вы это понимаете.

Конфигурация поведения — это то, как вы на это реагируете.

🔍 {bold('Здесь мы исследуем:')}
• Ваши автоматические реакции
• Как вы действуете в разных ситуациях

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Продолжим?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_3"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def start_stage_3(message, user_id: int, state_data: dict):
    """Начало этапа 3"""
    update_state_data(user_id,
        stage3_current=0,
        stage3_last_answered=-1,
        stage3_start_time=time.time(),
        stage3_level_scores=[],
        behavioral_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    ask_stage_3_question(message, user_id)


def ask_stage_3_question(message, user_id: int):
    """Задаёт вопрос ЭТАПА 3"""
    data = get_state_data(user_id)
    
    current = data.get("stage3_current", 0)
    total = get_stage3_total()
    
    if current >= total:
        finish_stage_3(message, user_id)
        return
    
    question = get_stage3_question(current)
    strategy = question.get("strategy", "УБ")
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option_text,
            callback_data=f"stage3_{current}_{option_id}_{strategy}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_stage_3_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 3"""
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        strategy = parts[3]
        
        stage3_current = data.get("stage3_current", 0)
        
        if current < stage3_current:
            ask_stage_3_question(call.message, user_id)
            return
        
        question = get_stage3_question(current)
        option_text = question["options"].get(option_id)
        
        if not option_text:
            return
        
        try:
            level_val = int(option_id)
        except ValueError:
            level_val = 1
        
        stage3_level_scores = data.get("stage3_level_scores", [])
        stage3_level_scores.append(level_val)
        
        behavioral_levels = data.get("behavioral_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if strategy in ["СБ", "ТФ", "УБ", "ЧВ"]:
            behavioral_levels[strategy].append(level_val)
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 3,
            'question_index': current,
            'question': question['text'],
            'answer': option_text,
            'answer_value': level_val,
            'strategy': strategy
        })
        
        update_state_data(user_id,
            stage3_level_scores=stage3_level_scores,
            behavioral_levels=behavioral_levels,
            stage3_last_answered=current,
            stage3_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_3_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_3_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)


def finish_stage_3(message, user_id: int):
    """Завершение ЭТАПА 3"""
    data = get_state_data(user_id)
    
    stage2_level = user_data.get(user_id, {}).get("thinking_level", 1)
    stage3_scores = data.get("stage3_level_scores", [])
    
    final_level = calculate_final_level(stage2_level, stage3_scores)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["final_level"] = final_level
    
    # Сохраняем поведенческие уровни
    behavioral_levels = data.get("behavioral_levels", {})
    if "behavioral_levels" not in user_data[user_id]:
        user_data[user_id]["behavioral_levels"] = {}
    
    for key, values in behavioral_levels.items():
        if key in user_data[user_id]["behavioral_levels"]:
            user_data[user_id]["behavioral_levels"][key].extend(values)
        else:
            user_data[user_id]["behavioral_levels"][key] = values
    
    behavior_level = map_to_stage3_feedback_level(final_level)
    
    logger.info(f"✅ User {user_id}: Stage 3 complete, final_level={final_level}")
    
    result_text = STAGE_3_FEEDBACK.get(behavior_level, STAGE_3_FEEDBACK[1])
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 4')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 4", callback_data="show_stage_4_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.stage_4)


# ============================================
# ЭТАП 4: ТОЧКА РОСТА
# ============================================

def show_stage_4_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 4"""
    text = f"""
🧠 {bold('ЭТАП 4: ТОЧКА РОСТА')}

Восприятие — что вы видите.
Мышление — как понимаете.
Поведение — как реагируете.

🔍 {bold('Здесь мы найдём:')} где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Готовы найти свою точку роста?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_4"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def start_stage_4(message, user_id: int, state_data: dict):
    """Начало этапа 4"""
    update_state_data(user_id,
        stage4_current=0,
        stage4_last_answered=-1,
        stage4_start_time=time.time(),
        dilts_counts={"ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0}
    )
    
    ask_stage_4_question(message, user_id)


def ask_stage_4_question(message, user_id: int):
    """Задаёт вопрос ЭТАПА 4"""
    data = get_state_data(user_id)
    
    current = data.get("stage4_current", 0)
    total = get_stage4_total()
    
    if current >= total:
        finish_stage_4(message, user_id)
        return
    
    question = get_stage4_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 4: ТОЧКА РОСТА')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage4_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_stage_4_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 4"""
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage4_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage4_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        dilts = selected_option.get("dilts", "BEHAVIOR")
        dilts_counts = data.get("dilts_counts", {})
        dilts_counts[dilts] = dilts_counts.get(dilts, 0) + 1
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 4,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'dilts': dilts
        })
        
        update_state_data(user_id,
            dilts_counts=dilts_counts,
            stage4_last_answered=current,
            stage4_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_4_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_4_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)


def finish_stage_4(message, user_id: int):
    """Завершение ЭТАПА 4"""
    data = get_state_data(user_id)
    
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["dilts_counts"] = dilts_counts
    user_data[user_id]["dominant_dilts"] = dominant_dilts
    
    # Рассчитываем финальный профиль
    profile_data = calculate_profile_final(user_data[user_id])
    user_data[user_id]["profile_data"] = profile_data
    
    logger.info(f"✅ User {user_id}: Stage 4 complete, profile={profile_data.get('display_name', 'unknown')}")
    
    # Показываем предварительный профиль
    from handlers.profile import show_preliminary_profile
    show_preliminary_profile(message, user_id)


# ============================================
# ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ
# ============================================

def show_stage_5_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 5"""
    text = f"""
🧠 {bold('ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ')}

Мы узнали, как вы воспринимаете мир, мыслите и действуете.
Теперь пришло время заглянуть глубже — в то, что сформировало вас.

🔍 {bold('Здесь мы исследуем:')}
• Какой у вас тип привязанности
• Какие защитные механизмы вы используете
• Какие глубинные убеждения управляют вами

📊 {bold('Вопросов:')} 10
⏱ {bold('Время:')} ~5 минут

👇 {bold('Готовы заглянуть вглубь себя?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_5"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def start_stage_5(message, user_id: int, state_data: dict):
    """Начало этапа 5"""
    update_state_data(user_id,
        stage5_current=0,
        stage5_last_answered=-1,
        stage5_answers=[]
    )
    
    ask_stage_5_question(message, user_id)


def ask_stage_5_question(message, user_id: int):
    """Задаёт вопрос 5-го этапа"""
    data = get_state_data(user_id)
    
    current = data.get("stage5_current", 0)
    total = get_stage5_total()
    
    if current >= total:
        finish_stage_5(message, user_id)
        return
    
    question = get_stage5_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage5_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_stage_5_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обработка ответа 5-го этапа"""
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage5_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage5_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        stage5_answers = data.get("stage5_answers", [])
        stage5_answers.append({
            'question_id': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'pattern': selected_option.get('pattern'),
            'target': question.get('target')
        })
        
        update_state_data(user_id,
            stage5_answers=stage5_answers,
            stage5_last_answered=current,
            stage5_current=current + 1
        )
        
        ask_stage_5_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_5_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)


def finish_stage_5(message, user_id: int):
    """Завершение 5-го этапа"""
    data = get_state_data(user_id)
    stage5_answers = data.get("stage5_answers", [])
    
    deep_patterns = analyze_stage5_results(stage5_answers)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["deep_patterns"] = deep_patterns
    
    logger.info(f"✅ User {user_id}: Stage 5 complete")
    
    from handlers.profile import show_final_profile
    show_final_profile(message, user_id)


# ============================================
# УТОЧНЯЮЩИЕ ВОПРОСЫ
# ============================================

def ask_clarifying_question(message, user_id: int):
    """Задаёт уточняющий вопрос"""
    data = get_state_data(user_id)
    questions = data.get("clarifying_questions", [])
    current = data.get("clarifying_current", 0)
    
    if current >= len(questions):
        update_profile_with_clarifications(message, user_id)
        return
    
    question = questions[current]
    
    question_text = f"""
🔍 {bold(f'УТОЧНЯЮЩИЙ ВОПРОС {current + 1}/{len(questions)}')}

{question['text']}
"""
    
    keyboard = InlineKeyboardMarkup()
    options = question.get('options', {})
    for opt_key, opt_text in options.items():
        keyboard.add(InlineKeyboardButton(
            text=opt_text,
            callback_data=f"clarify_answer_{current}_{opt_key}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_clarifying_answer(call: CallbackQuery, user_id: int, state_data: dict):
    """Обрабатывает ответ на уточняющий вопрос"""
    data = get_state_data(user_id)
    
    parts = call.data.split("_")
    if len(parts) < 4:
        return
    
    if not parts[2].isdigit():
        return
    current = int(parts[2])
    answer_key = parts[3]
    
    questions = data.get("clarifying_questions", [])
    if current >= len(questions):
        return
    
    question = questions[current]
    
    answers = data.get("clarifying_answers", [])
    answers.append({
        "question": question['text'],
        "answer_key": answer_key,
        "answer_text": question['options'].get(answer_key, ""),
        "type": question.get('type'),
        "target": question.get('target') or question.get('vector')
    })
    
    update_state_data(user_id,
        clarifying_answers=answers,
        clarifying_current=current + 1
    )
    
    ask_clarifying_question(call.message, user_id)


def update_profile_with_clarifications(message, user_id: int):
    """Обновляет профиль с учётом уточнений"""
    data = get_state_data(user_id)
    
    iteration = data.get("clarification_iteration", 0) + 1
    update_state_data(user_id, clarification_iteration=iteration)
    
    from handlers.profile import show_preliminary_profile
    show_preliminary_profile(message, user_id)


# ============================================
# ЧАСТЬ 3: ФУНКЦИИ ДЛЯ УМНЫХ ВОПРОСОВ
# ============================================

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
    
    # Добавляем общие вопросы, если не хватает
    while len(questions) < 5:
        for q in general:
            if q not in questions and len(questions) < 5:
                questions.append(q)
    
    return questions[:5]


def show_smart_questions(call: CallbackQuery):
    """
    Показывает умные вопросы на основе профиля
    """
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed_check(user_data_dict):
        text = f"""
🧠 <b>ФРЕДИ: СНАЧАЛА ПРОЙДИ ТЕСТ</b>

Чтобы я мог задавать точные вопросы, нужно знать твой профиль.

👇 Пройди тест (15 минут), и я смогу помогать глубже.
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🚀 ПРОЙТИ ТЕСТ", callback_data="show_stage_1_intro"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu"))
        
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
        return
    
    # Получаем scores
    scores = {}
    for k in VECTORS:
        levels = user_data_dict.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    update_state_data(user_id, smart_questions=questions)
    
    mode = context.communication_mode if context else "coach"
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Разные заголовки для разных режимов
    if mode == "coach":
        header = f"{mode_config['emoji']} <b>ЗАДАЙТЕ ВОПРОС (КОУЧ)</b>\n\n"
        header += "Я буду задавать открытые вопросы, помогая вам найти ответы внутри себя.\n\n"
    elif mode == "psychologist":
        header = f"{mode_config['emoji']} <b>РАССКАЖИТЕ МНЕ (ПСИХОЛОГ)</b>\n\n"
        header += "Я здесь, чтобы помочь исследовать глубинные паттерны.\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} <b>ПОСТАВЬТЕ ЗАДАЧУ (ТРЕНЕР)</b>\n\n"
        header += "Чётко сформулируйте, что хотите решить. Я дам конкретные шаги.\n\n"
    else:
        header = f"❓ <b>ЗАДАЙТЕ ВОПРОС</b>\n\n"
    
    text = header + "👇 <b>Выберите вопрос или напишите свой:</b>"
    
    # Строим клавиатуру
    keyboard = InlineKeyboardMarkup()
    
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.add(InlineKeyboardButton(
            text=f"{q_short}",
            callback_data=f"ask_{i}"
        ))
    
    # Добавляем категории
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
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def handle_smart_question(call: CallbackQuery, question_num: int):
    """
    Обрабатывает выбранный умный вопрос
    """
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    
    # Получаем вопрос из сохраненных
    data = get_state_data(user_id)
    questions = data.get("smart_questions", [])
    
    if question_num < 1 or question_num > len(questions):
        logger.error(f"❌ Неверный номер вопроса: {question_num}")
        return
    
    question = questions[question_num - 1]
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        "🤔 Думаю над ответом...\n\nЭто займёт около 10-15 секунд",
        delete_previous=True
    )
    
    context_obj = get_user_context_obj(user_id)
    mode_name = context_obj.communication_mode if context_obj else "coach"
    
    # Получаем режим
    from modes import get_mode
    mode = get_mode(mode_name, user_id, user_data_dict, context_obj)
    
    # Обрабатываем вопрос через режим
    result = mode.process_question(question)
    response = result["response"]
    
    # Обновляем данные с новой историей
    if "history" not in user_data_dict:
        user_data_dict["history"] = []
    user_data_dict["history"] = mode.history
    
    # Очищаем ответ от форматирования
    clean_response = clean_text_for_safe_display(response)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("❓ Ещё вопрос", callback_data="smart_questions"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help"))
    
    # Добавляем предложения, если есть
    suggestions_text = ""
    if result.get("suggestions"):
        suggestions_text = "\n\n" + "\n".join(result["suggestions"])
    
    # Удаляем статусное и отправляем ответ
    if status_msg:
        try:
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        call.message,
        f"❓ <b>{question}</b>\n\n{clean_response}{suggestions_text}",
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Отправляем голосовой ответ
    audio_data = text_to_speech(clean_response, mode_name)
    if audio_data:
        logger.info(f"🎙 Голосовой ответ сгенерирован для пользователя {user_id}")


def show_question_input(call: CallbackQuery):
    """
    Показывает экран ввода вопроса
    """
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Примеры вопросов для разных режимов
    examples = {
        "coach": [
            "Как найти своё предназначение?",
            "Что делать с неопределённостью?",
            "Как перестать сомневаться?"
        ],
        "psychologist": [
            "Почему реагирую на одни и те же триггеры?",
            "Откуда этот сценарий в отношениях?",
            "Как проработать детскую травму?"
        ],
        "trainer": [
            "Как научиться быстро принимать решения?",
            "Какие навыки нужны для роста дохода?",
            "Как действовать в конфликте?"
        ]
    }
    
    mode_examples = examples.get(mode, examples["coach"])
    examples_text = "\n".join([f"• {ex}" for ex in mode_examples])
    
    text = f"""
🧠 <b>ФРЕДИ: ЗАДАЙТЕ ВОПРОС</b>

{user_name}, <b>задавай вопрос.</b> Я отвечу с учётом твоего профиля и выбранного режима.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

📝 <b>Напиши вопрос текстом</b> или отправь голосовое сообщение.

👇 <b>Примеры:</b>
{examples_text}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    # Устанавливаем состояние ожидания вопроса
    set_state(user_id, TestStates.awaiting_question)


async def process_text_question_async(message: Message, user_id: int, text: str):
    """
    Асинхронная обработка текстового вопроса пользователя
    """
    user_data_dict = get_user_data_dict(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed_check(user_data_dict):
        await safe_send_message(
            message,
            "❓ Сначала нужно пройти тест. Используйте /start",
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = await safe_send_message(
        message,
        "🎙 Думаю над ответом...",
        delete_previous=True
    )
    
    context_obj = get_user_context_obj(user_id)
    mode_name = context_obj.communication_mode if context_obj else "coach"
    
    # Формируем промпт для ИИ
    prompt = f"""
Ты - {COMMUNICATION_MODES[mode_name]['name']} Фреди. Ты общаешься с пользователем.

❗️ВАЖНЕЙШИЕ ПРАВИЛА ДЛЯ ТВОИХ ОТВЕТОВ:

1. Твой текст БУДЕТ ОЗВУЧЕН, поэтому:
   - НЕ ИСПОЛЬЗУЙ НИКАКИЕ СИМВОЛЫ: * # _ - • → [ ] ( ) 
   - НЕ ИСПОЛЬЗУЙ НУМЕРАЦИЮ (1., 2., 3.)
   - НЕ ИСПОЛЬЗУЙ МАРКИРОВАННЫЕ СПИСКИ
   - Пиши ТОЛЬКО ТЕКСТ, как в разговоре

2. Стиль речи - теплый, эмпатичный психологический разговор:
   - Используй имя пользователя: {get_user_name(user_id)}
   - Говори короткими предложениями
   - Добавляй паузы с помощью многоточий...
   - Задавай риторические вопросы

Вопрос пользователя: {text}

Информация о пользователе:
Профиль: {user_data_dict.get('profile_data', {}).get('display_name', 'не определен')}
Тип восприятия: {user_data_dict.get('perception_type', 'не определен')}
Уровень мышления: {user_data_dict.get('thinking_level', 5)}/9

Напиши свой ответ ТОЛЬКО ТЕКСТОМ, готовым для озвучивания.
"""
    
    # Получаем ответ от ИИ
    response = await call_deepseek(prompt, max_tokens=1000)
    
    if not response:
        response = "Извините, я немного задумался. Можете повторить вопрос?"
    
    # Сохраняем в историю
    history = user_data_dict.get('history', [])
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})
    user_data_dict["history"] = history
    
    # Очищаем ответ от форматирования
    clean_response = clean_text_for_safe_display(response)
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🎤 ЗАДАТЬ ЕЩЁ", callback_data="ask_question"),
        InlineKeyboardButton("🎯 К ЦЕЛИ", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(InlineKeyboardButton("◀️ К ПОРТРЕТУ", callback_data="show_results"))
    
    # Удаляем статусное сообщение
    if status_msg:
        try:
            await safe_delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
    
    # Отправляем ответ
    await safe_send_message(
        message,
        f"💭 <b>Ответ</b>\n\n{clean_response}",
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Отправляем голосовой ответ
    audio_data = await text_to_speech(clean_response, mode_name)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="response.ogg")
        await message.answer_voice(
            audio_file,
            caption=f"🎙 Голосовой ответ ({COMMUNICATION_MODES[mode_name]['display_name']})"
        )
    
    # Сбрасываем состояние
    set_state(user_id, TestStates.results)


async def process_voice_message_async(message: Message, user_id: int, file_path: str):
    """
    Асинхронная обработка голосового сообщения пользователя
    """
    user_data_dict = get_user_data_dict(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed_check(user_data_dict):
        await safe_send_message(
            message,
            "🎙 Голосовые сообщения доступны только после завершения теста",
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = await safe_send_message(
        message,
        "🎤 Распознаю речь...",
        delete_previous=True
    )
    
    try:
        # Распознаём речь
        recognized_text = await speech_to_text(file_path)
        
        if not recognized_text:
            if status_msg:
                try:
                    await safe_delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
            
            await safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                await safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        # Обрабатываем распознанный текст как обычный вопрос
        await process_text_question_async(message, user_id, recognized_text)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        
        if status_msg:
            try:
                await safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке голоса",
            delete_previous=True
        )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Функции этапов тестирования
    'show_stage_1_intro',
    'start_stage_1',
    'ask_stage_1_question',
    'handle_stage_1_answer',
    'finish_stage_1',
    'show_stage_2_intro',
    'start_stage_2',
    'ask_stage_2_question',
    'handle_stage_2_answer',
    'finish_stage_2',
    'show_stage_3_intro',
    'start_stage_3',
    'ask_stage_3_question',
    'handle_stage_3_answer',
    'finish_stage_3',
    'show_stage_4_intro',
    'start_stage_4',
    'ask_stage_4_question',
    'handle_stage_4_answer',
    'finish_stage_4',
    'show_stage_5_intro',
    'start_stage_5',
    'ask_stage_5_question',
    'handle_stage_5_answer',
    'finish_stage_5',
    'ask_clarifying_question',
    'handle_clarifying_answer',
    'update_profile_with_clarifications',
    
    # Функции умных вопросов
    'generate_smart_questions',
    'show_smart_questions',
    'handle_smart_question',
    'show_question_input',
    'process_text_question_async',
    'process_voice_message_async',
    
    # Вспомогательные функции
    'determine_perception_type',
    'calculate_thinking_level_by_scores',
    'get_level_group',
    'calculate_final_level',
    'determine_dominant_dilts',
    'calculate_profile_final'
]
