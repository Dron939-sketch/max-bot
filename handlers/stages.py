#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики этапов тестирования для MAX
"""
import logging
from typing import Dict, Any, Optional

from bot_instance import bot
from message_utils import safe_send_message, safe_edit_message
from keyboards import (
    get_stage_1_keyboard, get_stage_2_keyboard, get_stage_3_keyboard,
    get_stage_4_keyboard, get_stage_5_keyboard, get_back_keyboard,
    get_clarifying_keyboard
)
from questions import (
    get_stage1_question, get_stage1_total,
    get_stage2_question, get_stage2_total, get_stage2_score,
    get_stage3_question, get_stage3_total,
    get_stage4_question, get_stage4_total,
    get_stage5_question, get_stage5_total,
    get_question_text, get_option_text, get_option_value,
    get_clarifying_questions
)
from database import save_user_answer, get_user_test_state, update_user_test_state
from profiles import calculate_profile, get_perception_type
from confinement_model import update_confinement_model
from models import UserContext

logger = logging.getLogger(__name__)

# Хранилище временных данных (можно перенести в БД/Redis)
user_test_data = {}

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_test_data(user_id: int) -> Dict[str, Any]:
    """Получает данные теста пользователя"""
    if user_id not in user_test_data:
        # Пробуем загрузить из БД
        saved = get_user_test_state(user_id)
        if saved:
            user_test_data[user_id] = saved
        else:
            user_test_data[user_id] = {
                "stage": 1,
                "question_index": 0,
                "answers": [],
                "scores": {
                    "EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0,
                    "СБ": [], "ТФ": [], "УБ": [], "ЧВ": [],
                    "dilts": {"ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0},
                    "stage5": []
                },
                "perception_type": None,
                "thinking_level": 0,
                "deep_patterns": {}
            }
    return user_test_data[user_id]


def save_user_test_data(user_id: int, data: Dict[str, Any]):
    """Сохраняет данные теста пользователя"""
    user_test_data[user_id] = data
    update_user_test_state(user_id, data)


def get_stage_info(stage: int, question_index: int, total: int) -> str:
    """Возвращает информацию о прогрессе теста"""
    return f"📊 ЭТАП {stage}/5 · Вопрос {question_index + 1}/{total}\n\n"


# ============================================
# ОБЩИЙ ОБРАБОТЧИК ДЛЯ ЭТАПОВ
# ============================================

def show_stage_intro(message, stage: int):
    """Показывает введение в этап"""
    user_id = message.chat.id
    data = get_user_test_data(user_id)
    
    intros = {
        1: {
            "title": "🧩 ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ",
            "text": """
Как ты фильтруешь реальность? На что опираешься, когда принимаешь решения?

8 простых вопросов помогут понять твой базовый способ взаимодействия с миром.

Готов?"""
        },
        2: {
            "title": "🧠 ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ",
            "text": """
Как твой мозг перерабатывает информацию? На каком уровне сложности ты мыслишь?

Оцени каждый вопрос по шкале от 1 до 9, где:
1️⃣ — самый простой, поверхностный уровень
9️⃣ — самый глубокий, системный уровень

Готов?"""
        },
        3: {
            "title": "🎭 ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ",
            "text": """
Что ты делаешь на автопилоте? Как реагируешь в стрессовых ситуациях?

Выбирай вариант, который ближе всего к твоей реальной реакции.

Готов?"""
        },
        4: {
            "title": "🌱 ЭТАП 4: ТОЧКА РОСТА",
            "text": """
На каком уровне ты обычно ищешь причины проблем и пути развития?

Выбирай вариант, который лучше всего отражает твой подход.

Готов?"""
        },
        5: {
            "title": "🌀 ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ",
            "text": """
Что сформировало тебя как личность? Какие глубинные убеждения управляют твоей жизнью?

10 вопросов о твоём прошлом и реакциях. Будь честен с собой.

Готов?"""
        }
    }
    
    intro = intros.get(stage, intros[1])
    
    text = f"""
{intro['title']}

{intro['text']}
"""
    
    keyboard = get_back_keyboard("main_menu" if stage == 1 else f"stage_{stage-1}_results")
    keyboard.add(types.InlineKeyboardButton("🚀 НАЧАТЬ", callback_data=f"stage_{stage}_start"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)


def show_stage_question(message, stage: int, question_index: int):
    """Показывает вопрос этапа"""
    user_id = message.chat.id
    data = get_user_test_data(user_id)
    
    # Получаем вопрос
    if stage == 1:
        question = get_stage1_question(question_index)
        total = get_stage1_total()
        keyboard = get_stage_1_keyboard()
    elif stage == 2:
        perception = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception, question_index)
        total = get_stage2_total(perception)
        keyboard = get_stage_2_keyboard()
    elif stage == 3:
        question = get_stage3_question(question_index)
        total = get_stage3_total()
        keyboard = get_stage_3_keyboard()
    elif stage == 4:
        question = get_stage4_question(question_index)
        total = get_stage4_total()
        keyboard = get_stage_4_keyboard()
    elif stage == 5:
        question = get_stage5_question(question_index)
        total = get_stage5_total()
        keyboard = get_stage_5_keyboard()
    else:
        return
    
    if not question:
        # Если вопрос не найден, завершаем этап
        finish_stage(message, stage)
        return
    
    question_text = get_question_text(question)
    progress = get_stage_info(stage, question_index, total)
    
    # Формируем текст с вариантами
    options_text = "\n"
    options = question.get("options", {})
    for key, option in options.items():
        if isinstance(option, dict):
            opt_text = option.get("text", "")
        else:
            opt_text = str(option)
        
        if stage in [2, 3]:
            # Для цифровых этапов
            emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"][int(key)-1] if key.isdigit() else key
            options_text += f"{emoji} — {opt_text}\n\n"
        else:
            # Для буквенных этапов
            options_text += f"{key.upper()}) {opt_text}\n\n"
    
    full_text = f"""
{progress}{question_text}

{options_text}
👇 Выбери вариант:"""
    
    safe_send_message(message, full_text, reply_markup=keyboard, delete_previous=True)


def process_stage_answer(call, stage: int, answer_key: str):
    """Обрабатывает ответ на вопрос этапа"""
    user_id = call.from_user.id
    data = get_user_test_data(user_id)
    question_index = data.get("question_index", 0)
    
    # Получаем вопрос
    if stage == 1:
        question = get_stage1_question(question_index)
        value = get_option_value(question, answer_key)
        
        # Сохраняем баллы для восприятия
        scores = value.get("scores", {})
        for key, val in scores.items():
            data["scores"][key] = data["scores"].get(key, 0) + val
        
    elif stage == 2:
        perception = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception, question_index)
        
        # Получаем баллы (для этапа 2 answer_key это цифра 1-9)
        score_value = get_stage2_score(perception, question_index, answer_key)
        
        # Определяем, какой вектор измеряет вопрос
        measures = question.get("measures", "УБ")
        if measures in ["СБ", "ТФ", "УБ", "ЧВ"]:
            data["scores"][measures].append(score_value)
        
    elif stage == 3:
        question = get_stage3_question(question_index)
        strategy = question.get("strategy", "УБ")
        
        # Для этапа 3 answer_key это цифра 1-6
        level = int(answer_key)
        
        # Сохраняем в соответствующий вектор
        if strategy in ["СБ", "ТФ", "УБ", "ЧВ"]:
            data["scores"][strategy].append(level)
        
    elif stage == 4:
        question = get_stage4_question(question_index)
        value = get_option_value(question, answer_key)
        dilts_level = value.get("dilts")
        
        if dilts_level:
            data["scores"]["dilts"][dilts_level] = data["scores"]["dilts"].get(dilts_level, 0) + 1
        
    elif stage == 5:
        question = get_stage5_question(question_index)
        value = get_option_value(question, answer_key)
        
        # Сохраняем паттерн
        answer_data = {
            "question_id": question.get("id", question_index),
            "target": question.get("target"),
            "pattern": value.get("pattern") if isinstance(value, dict) else answer_key
        }
        data["scores"]["stage5"].append(answer_data)
    
    # Сохраняем ответ
    data["answers"].append({
        "stage": stage,
        "question_index": question_index,
        "answer": answer_key,
        "timestamp": time.time()
    })
    
    # Переходим к следующему вопросу
    next_index = question_index + 1
    
    # Проверяем, закончился ли этап
    total = 0
    if stage == 1:
        total = get_stage1_total()
    elif stage == 2:
        perception = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        total = get_stage2_total(perception)
    elif stage == 3:
        total = get_stage3_total()
    elif stage == 4:
        total = get_stage4_total()
    elif stage == 5:
        total = get_stage5_total()
    
    if next_index >= total:
        # Этап завершен
        data["question_index"] = 0
        finish_stage(call.message, stage)
    else:
        # Следующий вопрос
        data["question_index"] = next_index
        save_user_test_data(user_id, data)
        show_stage_question(call.message, stage, next_index)


def finish_stage(message, stage: int):
    """Завершает этап и показывает результаты/переход"""
    user_id = message.chat.id
    data = get_user_test_data(user_id)
    
    if stage == 1:
        # Определяем тип восприятия
        scores = data["scores"]
        perception_type = get_perception_type(
            scores.get("EXTERNAL", 0),
            scores.get("INTERNAL", 0),
            scores.get("SYMBOLIC", 0),
            scores.get("MATERIAL", 0)
        )
        data["perception_type"] = perception_type
        data["stage"] = 2
        
        text = f"""
✅ ЭТАП 1 ЗАВЕРШЁН!

Твой тип восприятия: {perception_type}

Переходим к этапу 2 — конфигурация мышления.
"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 К ЭТАПУ 2", callback_data="stage_2_start"))
        
    elif stage == 2:
        # Вычисляем средние по векторам
        for vector in ["СБ", "ТФ", "УБ", "ЧВ"]:
            values = data["scores"].get(vector, [])
            if values:
                avg = sum(values) / len(values)
                data["thinking_level"] = avg  # для совместимости
        
        data["stage"] = 3
        
        text = """
✅ ЭТАП 2 ЗАВЕРШЁН!

Твой уровень мышления определён.
Переходим к этапу 3 — конфигурация поведения.
"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 К ЭТАПУ 3", callback_data="stage_3_start"))
        
    elif stage == 3:
        data["stage"] = 4
        
        text = """
✅ ЭТАП 3 ЗАВЕРШЁН!

Твои поведенческие паттерны проанализированы.
Переходим к этапу 4 — точка роста.
"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 К ЭТАПУ 4", callback_data="stage_4_start"))
        
    elif stage == 4:
        data["stage"] = 5
        
        text = """
✅ ЭТАП 4 ЗАВЕРШЁН!

Определена твоя основная точка роста.
Переходим к финальному этапу — глубинные паттерны.
"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 К ЭТАПУ 5", callback_data="stage_5_start"))
        
    elif stage == 5:
        # Тест полностью завершен
        from .profile import show_final_profile
        show_final_profile(message, user_id)
        return
    
    save_user_test_data(user_id, data)
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('stage_') and call.data.endswith('_start'))
def stage_start_callback(call):
    """Начало этапа"""
    stage = int(call.data.split('_')[1])
    user_id = call.from_user.id
    data = get_user_test_data(user_id)
    
    data["stage"] = stage
    data["question_index"] = 0
    save_user_test_data(user_id, data)
    
    show_stage_question(call.message, stage, 0)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stage1_'))
def stage1_callback(call):
    """Обработка ответов этапа 1"""
    answer = call.data.replace('stage1_', '')
    process_stage_answer(call, 1, answer)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stage2_'))
def stage2_callback(call):
    """Обработка ответов этапа 2"""
    answer = call.data.replace('stage2_', '')
    process_stage_answer(call, 2, answer)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stage3_'))
def stage3_callback(call):
    """Обработка ответов этапа 3"""
    answer = call.data.replace('stage3_', '')
    process_stage_answer(call, 3, answer)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stage4_'))
def stage4_callback(call):
    """Обработка ответов этапа 4"""
    answer = call.data.replace('stage4_', '')
    process_stage_answer(call, 4, answer)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stage5_'))
def stage5_callback(call):
    """Обработка ответов этапа 5"""
    answer = call.data.replace('stage5_', '')
    process_stage_answer(call, 5, answer)


@bot.callback_query_handler(func=lambda call: call.data == 'restart_test')
def restart_test_callback(call):
    """Перезапуск теста"""
    user_id = call.from_user.id
    
    # Очищаем данные теста
    if user_id in user_test_data:
        del user_test_data[user_id]
    
    # Очищаем в БД
    from database import clear_user_test_state
    clear_user_test_state(user_id)
    
    text = """
🔄 ТЕСТ ПЕРЕЗАПУЩЕН

Начинаем с чистого листа.
"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🚀 К ЭТАПУ 1", callback_data="stage_1_start"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)


# ============================================
# УТОЧНЯЮЩИЕ ВОПРОСЫ
# ============================================

def show_clarifying_questions(message, user_id: int):
    """Показывает уточняющие вопросы, если есть расхождения"""
    data = get_user_test_data(user_id)
    
    # Получаем расхождения (нужно реализовать логику)
    discrepancies = []  # Здесь должна быть логика определения расхождений
    current_levels = {
        "СБ": data["scores"].get("СБ", [3])[-1] if data["scores"].get("СБ") else 3,
        "ТФ": data["scores"].get("ТФ", [3])[-1] if data["scores"].get("ТФ") else 3,
        "УБ": data["scores"].get("УБ", [3])[-1] if data["scores"].get("УБ") else 3,
        "ЧВ": data["scores"].get("ЧВ", [3])[-1] if data["scores"].get("ЧВ") else 3
    }
    
    questions = get_clarifying_questions(discrepancies, current_levels)
    
    if not questions:
        # Если нет уточняющих вопросов, показываем финальный профиль
        from .profile import show_final_profile
        show_final_profile(message, user_id)
        return
    
    # Показываем первый уточняющий вопрос
    data["clarifying_index"] = 0
    data["clarifying_questions"] = questions
    save_user_test_data(user_id, data)
    
    show_clarifying_question(message, user_id, 0)


def show_clarifying_question(message, user_id: int, index: int):
    """Показывает уточняющий вопрос"""
    data = get_user_test_data(user_id)
    questions = data.get("clarifying_questions", [])
    
    if index >= len(questions):
        # Все вопросы заданы
        from .profile import show_final_profile
        show_final_profile(message, user_id)
        return
    
    q = questions[index]
    text = q.get("text", "")
    options = q.get("options", {})
    
    # Преобразуем опции в словарь для клавиатуры
    opt_dict = {}
    for key, opt_text in options.items():
        opt_dict[key] = opt_text
    
    keyboard = get_clarifying_keyboard(opt_dict)
    
    safe_send_message(message, f"📌 УТОЧНЯЮЩИЙ ВОПРОС\n\n{text}", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('clarify_'))
def clarifying_callback(call):
    """Обработка ответов на уточняющие вопросы"""
    user_id = call.from_user.id
    data = get_user_test_data(user_id)
    
    answer = call.data.replace('clarify_', '')
    index = data.get("clarifying_index", 0)
    
    # Сохраняем ответ
    if "clarifying_answers" not in data:
        data["clarifying_answers"] = []
    
    data["clarifying_answers"].append({
        "question_index": index,
        "answer": answer
    })
    
    # Переходим к следующему
    next_index = index + 1
    data["clarifying_index"] = next_index
    save_user_test_data(user_id, data)
    
    show_clarifying_question(call.message, user_id, next_index)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_stage_intro',
    'show_stage_question',
    'show_clarifying_questions',
    'stage_start_callback',
    'stage1_callback',
    'stage2_callback',
    'stage3_callback',
    'stage4_callback',
    'stage5_callback',
    'restart_test_callback',
    'clarifying_callback'
]
