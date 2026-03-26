#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ОБЪЕДИНЕННЫЙ ФАЙЛ: Обработчики вопросов тестирования И умных вопросов
Версия для MAX - ПОЛНАЯ с голосовой поддержкой
ИСПРАВЛЕНО: добавлена передача system_prompt в DeepSeek
"""

import logging
import re
import time
import random
import asyncio
import tempfile
import os
import threading
from typing import Dict, Any, List, Optional

from maxibot import MaxiBot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

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

# ✅ ИСПРАВЛЕНО: используем sync_db
from db_sync import sync_db

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

# Импортируем функцию отправки голоса
from handlers.voice import send_voice_to_max

# ✅ ИМПОРТ УМНЫХ ВОПРОСОВ (вынесено в отдельный файл)
from .smart_questions import generate_smart_questions, show_smart_questions, handle_smart_question

logger = logging.getLogger(__name__)

# ============================================
# 👇👇👇 СЮДА ВСТАВИТЬ БЛОКИРОВКУ 👇👇👇
# ============================================

# БЛОКИРОВКА ДЛЯ ПРЕДОТВРАЩЕНИЯ ДВОЙНОЙ ОБРАБОТКИ
_processing_lock = {}

def is_processing(user_id: int) -> bool:
    """Проверяет, обрабатывается ли уже запрос пользователя"""
    return _processing_lock.get(user_id, False)

def set_processing(user_id: int, value: bool):
    """Устанавливает флаг обработки"""
    _processing_lock[user_id] = value


def save_answer_to_db_sync(user_id: int, answer_data: Dict[str, Any]):
    """Синхронное сохранение отдельного ответа в БД"""
    try:
        results = sync_db.get_user_test_results(user_id, limit=1)
        test_result_id = results[0]['id'] if results else None
        
        sync_db.save_test_answer(
            user_id=user_id,
            test_result_id=test_result_id,
            stage=answer_data.get('stage', 0),
            question_index=answer_data.get('question_index', 0),
            question_text=answer_data.get('question', ''),
            answer_text=answer_data.get('answer', ''),
            answer_value=answer_data.get('option', ''),
            scores=answer_data.get('scores'),
            measures=answer_data.get('measures'),
            strategy=answer_data.get('strategy'),
            dilts=answer_data.get('dilts'),
            pattern=answer_data.get('pattern'),
            target=answer_data.get('target')
        )
        logger.debug(f"💾 Ответ этапа {answer_data.get('stage')} для {user_id} сохранен в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения ответа для {user_id}: {e}")


# ============================================
# БЛОКИРОВКА ДЛЯ ПРЕДОТВРАЩЕНИЯ ДВОЙНОЙ ОБРАБОТКИ
# ============================================

# Словарь для блокировки одновременной обработки запросов одного пользователя
_processing_lock = {}

def is_processing(user_id: int) -> bool:
    """Проверяет, обрабатывается ли уже запрос пользователя"""
    return _processing_lock.get(user_id, False)

def set_processing(user_id: int, value: bool):
    """Устанавливает флаг обработки"""
    _processing_lock[user_id] = value


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
🧠 **ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ**

Восприятие — это линза, через которую вы смотрите на мир.

🔍 **Что мы исследуем:**
• Куда направлено ваше внимание — вовне или внутрь
• Какая тревога доминирует — страх отвержения или страх потери контроля

📊 **Вопросов:** 8
⏱ **Время:** ~3 минуты

Отвечайте честно — это поможет мне лучше понять вас.
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_1"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
🧠 **ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ**

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage1_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
        answer_data = {
            'stage': 1,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'scores': selected_option.get('scores', {})
        }
        all_answers.append(answer_data)
        
        # ✅ Сохраняем в БД
        threading.Thread(target=save_answer_to_db_sync, args=(user_id, answer_data), daemon=True).start()
        
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
    
    text = f"{result_text}\n\n▶️ **Перейти к этапу 2**"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 2", callback_data="show_stage_2_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    set_state(user_id, TestStates.stage_2)


# ============================================
# ЭТАП 2: МЫШЛЕНИЕ
# ============================================

def show_stage_2_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 2"""
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    total_questions = get_stage2_total(perception_type)
    
    text = f"""
🧠 **ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ**

Восприятие определяет, что вы видите. Мышление — как вы это понимаете.

🎯 **Самое важное:**
Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте.

📊 **Вопросов:** {total_questions}
⏱ **Время:** ~3-4 минуты

Продолжим исследование?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_2"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
🧠 **ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ**

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for level_num, answer_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=answer_text,
            callback_data=f"stage2_{current}_{level_num}_{measures}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
        answer_data = {
            'stage': 2,
            'question_index': current,
            'question': question['text'],
            'answer': answer_text,
            'option': selected_level,
            'measures': measures,
            'perception_type': perception_type
        }
        all_answers.append(answer_data)
        
        # ✅ Сохраняем в БД
        threading.Thread(target=save_answer_to_db_sync, args=(user_id, answer_data), daemon=True).start()
        
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
    
    text = f"{result_text}\n\n▶️ **Перейти к этапу 3**"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 3", callback_data="show_stage_3_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    set_state(user_id, TestStates.stage_3)


# ============================================
# ЭТАП 3: ПОВЕДЕНИЕ
# ============================================

def show_stage_3_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 3"""
    text = f"""
🧠 **ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ**

Восприятие определяет, что вы видите.
Мышление — как вы это понимаете.

Конфигурация поведения — это то, как вы на это реагируете.

🔍 **Здесь мы исследуем:**
• Ваши автоматические реакции
• Как вы действуете в разных ситуациях

📊 **Вопросов:** 8
⏱ **Время:** ~3 минуты

Продолжим?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_3"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
🧠 **ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ**

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option_text,
            callback_data=f"stage3_{current}_{option_id}_{strategy}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
        answer_data = {
            'stage': 3,
            'question_index': current,
            'question': question['text'],
            'answer': option_text,
            'answer_value': level_val,
            'strategy': strategy
        }
        all_answers.append(answer_data)
        
        # ✅ Сохраняем в БД
        threading.Thread(target=save_answer_to_db_sync, args=(user_id, answer_data), daemon=True).start()
        
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
    
    text = f"{result_text}\n\n▶️ **Перейти к этапу 4**"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 4", callback_data="show_stage_4_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)
    set_state(user_id, TestStates.stage_4)


# ============================================
# ЭТАП 4: ТОЧКА РОСТА
# ============================================

def show_stage_4_intro(message, user_id: int, state_data: dict):
    """Показывает введение в этап 4"""
    text = f"""
🧠 **ЭТАП 4: ТОЧКА РОСТА**

Восприятие — что вы видите.
Мышление — как понимаете.
Поведение — как реагируете.

🔍 **Здесь мы найдём:** где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.

📊 **Вопросов:** 8
⏱ **Время:** ~3 минуты

Готовы найти свою точку роста?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_4"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
🧠 **ЭТАП 4: ТОЧКА РОСТА**

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage4_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
        answer_data = {
            'stage': 4,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'dilts': dilts
        }
        all_answers.append(answer_data)
        
        # ✅ Сохраняем в БД
        threading.Thread(target=save_answer_to_db_sync, args=(user_id, answer_data), daemon=True).start()
        
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
🧠 **ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ**

Мы узнали, как вы воспринимаете мир, мыслите и действуете.
Теперь пришло время заглянуть глубже — в то, что сформировало вас.

🔍 **Здесь мы исследуем:**
• Какой у вас тип привязанности
• Какие защитные механизмы вы используете
• Какие глубинные убеждения управляют вами

📊 **Вопросов:** 10
⏱ **Время:** ~5 минут

👇 **Готовы заглянуть вглубь себя?**
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_5"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
🧠 **ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ**

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage5_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
        answer_data = {
            'stage': 5,
            'question_id': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'pattern': selected_option.get('pattern'),
            'target': question.get('target')
        }
        stage5_answers.append(answer_data)
        
        # ✅ Сохраняем в БД
        threading.Thread(target=save_answer_to_db_sync, args=(user_id, answer_data), daemon=True).start()
        
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
🔍 **{f'УТОЧНЯЮЩИЙ ВОПРОС {current + 1}/{len(questions)}'}**

{question['text']}
"""
    
    keyboard = InlineKeyboardMarkup()
    options = question.get('options', {})
    for opt_key, opt_text in options.items():
        keyboard.add(InlineKeyboardButton(
            text=opt_text,
            callback_data=f"clarify_answer_{current}_{opt_key}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, parse_mode=None, delete_previous=True)


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
    answer_data = {
        "question": question['text'],
        "answer_key": answer_key,
        "answer_text": question['options'].get(answer_key, ""),
        "type": question.get('type'),
        "target": question.get('target') or question.get('vector')
    }
    answers.append(answer_data)
    
    # ✅ Сохраняем в БД
    threading.Thread(target=save_answer_to_db_sync, args=(user_id, {
    'stage': 'clarifying',
    'question_index': current,
    'question': question['text'],
    'answer': answer_data['answer_text'],
    'option': answer_key,
    'target': answer_data['target']
}), daemon=True).start()
    
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
# ЭКРАН ВВОДА ВОПРОСА
# ============================================

def show_question_input(call: CallbackQuery):
    """
    Показывает экран ввода вопроса
    ⚠️ ВНИМАНИЕ: Голосовой ввод временно отключён на платформе MAX
    """
    user_id = call.from_user.id
    user_name = get_user_name(user_id)
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    
    # Получаем профиль и режим для отображения
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', '')
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Строим информационную строку (компактно)
    info_line = ""
    if profile_code:
        info_line = f"**Твой профиль:** {profile_code}  |  **Режим:** {mode_config['emoji']} {mode_config['name']}\n\n"
    
    # ✅ ТЕКСТ ЭКРАНА С КОММЕНТАРИЕМ О ГОЛОСЕ
    text = f"""
✏️ **ЗАДАВАЙТЕ ЛЮБОЙ ВОПРОС**

{info_line}Если мой создатель знает ответ на него — значит и я вам что-то отвечу 😉

📝 **Напишите свой вопрос:**

*(🎙 Голосовой ввод временно недоступен на платформе MAX)*
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="show_results"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='Markdown',
        delete_previous=True
    )
    
    # Устанавливаем состояние ожидания вопроса
    set_state(user_id, TestStates.awaiting_question)


# ============================================
# СИНХРОННАЯ ФУНКЦИЯ ОБРАБОТКИ ВОПРОСА (БЕЗ await)
# ============================================

def process_text_question_sync(
    message: Message, 
    user_id: int, 
    text: str, 
    show_question_text: bool = True
):
    """
    СИНХРОННАЯ обработка текстового вопроса пользователя
    (вызывается из потока, НЕ использует await)
    """
    # ✅ Проверяем, не обрабатывается ли уже запрос
    if is_processing(user_id):
        logger.warning(f"⚠️ Запрос от пользователя {user_id} уже обрабатывается, пропускаем")
        safe_send_message(
            message,
            "⏳ Ваш предыдущий вопрос еще обрабатывается. Пожалуйста, подождите...",
            delete_previous=True
        )
        return
    
    # ✅ Устанавливаем блокировку
    set_processing(user_id, True)
    
    try:
        user_data_dict = get_user_data_dict(user_id)
        
        # Проверяем, завершен ли тест
        if not is_test_completed_check(user_data_dict):
            safe_send_message(
                message,
                "❓ Сначала нужно пройти тест. Используйте /start",
                delete_previous=True
            )
            return
        
        # Отправляем статусное сообщение
        status_msg = safe_send_message(
            message,
            "🎙 Думаю над ответом...",
            delete_previous=True
        )
        
        context_obj = get_user_context_obj(user_id)
        mode_name = context_obj.communication_mode if context_obj else "coach"
        
        # ✅ ПОЛУЧАЕМ system_prompt ИЗ КОНФИГА
        mode_config = COMMUNICATION_MODES.get(mode_name, COMMUNICATION_MODES["coach"])
        system_prompt = mode_config.get("system_prompt", "")
        
        logger.info("=" * 80)
        logger.info(f"🔍 ДИАГНОСТИКА process_text_question_sync:")
        logger.info(f"📝 Текст вопроса: {text[:100]}...")
        logger.info(f"📝 mode_name: {mode_name}")
        logger.info(f"📝 system_prompt (первые 200 символов): {system_prompt[:200]}...")
        logger.info("=" * 80)
        
        # Формируем УПРОЩЕННЫЙ промпт (стиль уже в system_prompt)
        prompt = f"""
Вопрос пользователя: {text}

Информация о пользователе:
Профиль: {user_data_dict.get('profile_data', {}).get('display_name', 'не определен')}
Тип восприятия: {user_data_dict.get('perception_type', 'не определен')}
Уровень мышления: {user_data_dict.get('thinking_level', 5)}/9

Напиши свой ответ ТОЛЬКО ТЕКСТОМ, готовым для озвучивания.
"""
        
        logger.info(f"📝 Промпт для DeepSeek:\n{prompt}")
        
        # ✅ ПРАВИЛЬНЫЙ ВЫЗОВ С system_prompt
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(call_deepseek(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1000
            ))
        finally:
            loop.close()
        
        logger.info(f"📝 Ответ от DeepSeek: {response[:200]}..." if response else "❌ Ответ пустой")
        
        if not response:
            response = "Извините, я немного задумался. Можете повторить вопрос?"
        
        # Сохраняем в историю
        history = user_data_dict.get('history', [])
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        user_data_dict["history"] = history
        
        # ✅ Сохраняем в БД
        sync_db.save_user_to_db(user_id)
        
        # Очищаем ответ от форматирования для отображения
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
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        # ПОКАЗЫВАЕМ ТЕКСТ ВОПРОСА ТОЛЬКО ЕСЛИ НУЖНО
        if show_question_text:
            safe_send_message(
                message,
                f"📝 **Вы сказали:**\n{text}",
                delete_previous=False  # не удаляем ничего, просто отправляем
            )
        
        # ОТПРАВЛЯЕМ ТЕКСТОВЫЙ ОТВЕТ
        safe_send_message(
            message,
            f"💭 **Ответ**\n\n{clean_response}",
            reply_markup=keyboard,
            parse_mode=None,
            delete_previous=not show_question_text  # удаляем предыдущие только если не показывали вопрос
        )
        
        # Генерируем и отправляем голосовой ответ
        try:
            # Создаем новый event loop для асинхронной операции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_data = loop.run_until_complete(text_to_speech(response, mode_name))
                if audio_data:
                    # ✅ send_voice_to_max - СИНХРОННАЯ функция (без await)
                    success = send_voice_to_max(message.chat.id, audio_data)
                    if success:
                        logger.info(f"🎙 Голосовой ответ отправлен пользователю {user_id}")
                    else:
                        logger.warning(f"⚠️ Не удалось отправить голос пользователю {user_id}")
                else:
                    logger.warning(f"⚠️ Не удалось сгенерировать голос для пользователя {user_id}")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке голоса: {e}", exc_info=True)
        
        # Сбрасываем состояние
        set_state(user_id, TestStates.awaiting_question)
        
    finally:
        # ✅ ВАЖНО: Снимаем блокировку в любом случае
        set_processing(user_id, False)


# ============================================
# АСИНХРОННАЯ ОБЕРТКА (ДЛЯ СОВМЕСТИМОСТИ)
# ============================================

async def process_text_question_async(
    message: Message, 
    user_id: int, 
    text: str, 
    show_question_text: bool = True
):
    """
    Асинхронная обертка для синхронной функции обработки вопроса
    (вызывается из main.py с await)
    """
    # Запускаем синхронную функцию в отдельном потоке
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,  # используем ThreadPoolExecutor по умолчанию
        lambda: process_text_question_sync(message, user_id, text, show_question_text)
    )


async def process_voice_message_async(message: Message, user_id: int, file_path: str):
    """
    Асинхронная обработка голосового сообщения пользователя
    """
    # ✅ ПРОВЕРКА ФЛАГА - ЕСЛИ ГОЛОС УЖЕ ОБРАБАТЫВАЕТСЯ, ПРОПУСКАЕМ
    from state import is_voice_processing
    
    if is_voice_processing(user_id):
        logger.info(f"⏳ Голос для {user_id} уже обрабатывается в voice.py, пропускаем обработку в questions.py")
        return
    
    # 🔥🔥🔥 МАРКЕР ДЛЯ ОТЛАДКИ 🔥🔥🔥
    logger.info("=" * 80)
    logger.info("🔥🔥🔥 ВЫЗВАНА ФУНКЦИЯ process_voice_message_async ИЗ ФАЙЛА questions.py 🔥🔥🔥")
    logger.info("=" * 80)
    
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
        
        logger.info(f"🎤 process_voice_message_async: распознанный текст = '{recognized_text}'")
        
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
        
        # Обрабатываем как обычный вопрос, но НЕ показываем текст вопроса повторно
        await process_text_question_async(message, user_id, recognized_text, show_question_text=False)
        
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
    
    # Функции умных вопросов (импортированы из smart_questions.py)
    'generate_smart_questions',
    'show_smart_questions',
    'handle_smart_question',
    
    'show_question_input',
    'process_text_question_sync',
    'process_text_question_async',
    'process_voice_message_async',
    
    # Вспомогательные функции
    'determine_perception_type',
    'calculate_thinking_level_by_scores',
    'get_level_group',
    'calculate_final_level',
    'determine_dominant_dilts',
    'calculate_profile_final',
    
    # Синхронная функция сохранения
    'save_answer_to_db_sync'
]
