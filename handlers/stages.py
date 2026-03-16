#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики этапов тестирования (1-5) для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import time
import logging
import os
import json
from typing import Dict, Any, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message
from keyboards import (
    get_stage_1_keyboard, get_stage_2_keyboard, get_stage_3_keyboard,
    get_stage_4_keyboard, get_stage_5_keyboard, get_back_keyboard
)
from questions import (
    get_stage1_question, get_stage1_total,
    get_stage2_question, get_stage2_total, get_stage2_score,
    get_stage3_question, get_stage3_total,
    get_stage4_question, get_stage4_total,
    get_stage5_question, get_stage5_total,
    get_question_text, get_option_text, get_option_value,
    map_to_stage3_feedback_level, analyze_stage5_results
)
from profiles import (
    STAGE_1_FEEDBACK, STAGE_2_FEEDBACK, STAGE_3_FEEDBACK,
    VECTORS, LEVEL_PROFILES
)
from models import ConfinementModel9
from services import generate_ai_profile

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def calculate_progress(current: int, total: int) -> str:
    """Возвращает прогресс-бар"""
    percent = int((current / total) * 10)
    bar = "█" * percent + "░" * (10 - percent)
    return f"▸ Вопрос {current}/{total} • {bar}"

def determine_perception_type(scores: dict) -> str:
    """Определяет тип восприятия из scores этапа 1"""
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
    """Рассчитывает уровень мышления для этапа 2"""
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

def get_level_group(level: int) -> str:
    """Группирует уровни для этапа 2"""
    if level <= 3:
        return "1-3"
    elif level <= 6:
        return "4-6"
    else:
        return "7-9"

def calculate_final_level(stage2_level: int, stage3_scores: list) -> int:
    """Рассчитывает финальный уровень для этапа 3"""
    if not stage3_scores:
        return stage2_level
    avg_behavior = sum(stage3_scores) / len(stage3_scores)
    return round((stage2_level + avg_behavior) / 2)

def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса для этапа 4"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def calculate_profile_final(user_data: dict) -> dict:
    """Финальный расчет профиля после этапа 4"""
    perception_type = user_data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    thinking_level = user_data.get("thinking_level", 5)
    
    behavioral_levels = user_data.get("behavioral_levels", {})
    
    sb_levels = behavioral_levels.get("СБ", [])
    tf_levels = behavioral_levels.get("ТФ", [])
    ub_levels = behavioral_levels.get("УБ", [])
    chv_levels = behavioral_levels.get("ЧВ", [])
    
    sb_avg = sum(sb_levels) / len(sb_levels) if sb_levels else 3
    tf_avg = sum(tf_levels) / len(tf_levels) if tf_levels else 3
    ub_avg = sum(ub_levels) / len(ub_levels) if ub_levels else 3
    chv_avg = sum(chv_levels) / len(chv_levels) if chv_levels else 3
    
    dilts_counts = user_data.get("dilts_counts", {})
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

def calculate_profile_confidence(profile: dict) -> float:
    """Рассчитывает уверенность в профиле"""
    confidence = 0.5
    
    stages_done = 0
    if profile.get("perception_type"):
        stages_done += 1
    if profile.get("thinking_level"):
        stages_done += 1
    if profile.get("behavioral_levels"):
        stages_done += 1
    if profile.get("dilts_counts"):
        stages_done += 1
    if profile.get("deep_patterns"):
        stages_done += 1
    
    confidence += stages_done * 0.1
    
    clarification_count = profile.get("clarification_iteration", 0)
    confidence += clarification_count * 0.05
    
    return min(1.0, confidence)

def convert_to_simple_language(scores, perception_type, thinking_level, deep_patterns=None):
    """Конвертирует технические данные в простые описания"""
    result = {}
    
    # 1. Внимание (куда смотрит)
    if perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
        result['attention_desc'] = "Для вас важно, что думают другие, вы чутко считываете настроение и ожидания окружающих."
    else:
        result['attention_desc'] = "Для вас важнее ваши внутренние ощущения и чувства, чем мнение других."
    
    # 2. Мышление
    if thinking_level <= 3:
        result['thinking_desc'] = "Вы хорошо видите отдельные ситуации, но не всегда замечаете общие закономерности."
    elif thinking_level <= 6:
        result['thinking_desc'] = "Вы замечаете закономерности, но не всегда видите, к чему они приведут в будущем."
    else:
        result['thinking_desc'] = "Вы видите общие законы и можете предсказывать развитие ситуаций."
    
    # 3. СБ (реакция на угрозу)
    sb_level = scores.get("СБ", 3)
    sb_profiles = {
        1: "Под давлением вы замираете и не можете слова сказать.",
        2: "Вы избегаете конфликтов — уходите, прячетесь, уворачиваетесь.",
        3: "Вы соглашаетесь внешне, но внутри всё кипит.",
        4: "Вы внешне спокойны, но внутри держите всё в себе.",
        5: "Вы пытаетесь сгладить конфликт, перевести в шутку.",
        6: "Вы умеете защищать себя, но можете и атаковать в ответ."
    }
    result['sb_desc'] = sb_profiles.get(int(sb_level), "Вы по-разному реагируете на давление.")
    
    # 4. ТФ (деньги)
    tf_level = scores.get("ТФ", 3)
    tf_profiles = {
        1: "Деньги приходят и уходят — как повезёт.",
        2: "Вы ищете возможности, но каждый раз как с нуля.",
        3: "Вы умеете зарабатывать своим трудом.",
        4: "Вы хорошо зарабатываете и можете копить.",
        5: "Вы создаёте системы дохода и управляете финансами.",
        6: "Вы управляете капиталом и создаёте финансовые структуры."
    }
    result['tf_desc'] = tf_profiles.get(int(tf_level), "У вас свои отношения с деньгами.")
    
    # 5. УБ (понимание мира)
    ub_level = scores.get("УБ", 3)
    ub_profiles = {
        1: "Вы стараетесь не думать о сложном — само как-то решится.",
        2: "Вы верите в знаки, судьбу, высшие силы.",
        3: "Вы доверяете экспертам и авторитетам.",
        4: "Вы ищете скрытые смыслы и заговоры.",
        5: "Вы анализируете факты и делаете выводы сами.",
        6: "Вы строите теории и ищете закономерности."
    }
    result['ub_desc'] = ub_profiles.get(int(ub_level), "Вы по-своему понимаете мир.")
    
    # 6. ЧВ (отношения)
    chv_level = scores.get("ЧВ", 3)
    chv_profiles = {
        1: "Вы сильно привязываетесь к людям, тяжело без них.",
        2: "Вы подстраиваетесь под других, теряя себя.",
        3: "Вы хотите нравиться, показываете себя с лучшей стороны.",
        4: "Вы умеете влиять на людей, добиваться своего.",
        5: "Вы строите равные партнёрские отношения.",
        6: "Вы создаёте сообщества и сети контактов."
    }
    result['chv_desc'] = chv_profiles.get(int(chv_level), "У вас свои паттерны в отношениях.")
    
    # 7. Точка роста
    growth_map = {
        "ENVIRONMENT": "Посмотрите вокруг — может, дело в обстоятельствах?",
        "BEHAVIOR": "Попробуйте делать хоть что-то по-другому — маленькие шаги многое меняют.",
        "CAPABILITIES": "Развивайте новые навыки — они откроют новые возможности.",
        "VALUES": "Поймите, что для вас действительно важно — это изменит всё.",
        "IDENTITY": "Ответьте себе на вопрос «кто я?» — в этом ключ к изменениям."
    }
    result['growth_point'] = growth_map.get(perception_type, "Начните с малого — и увидите, куда приведёт.")
    
    return result

def cleanup_old_state_files(max_age_hours=24):
    """Удаляет старые файлы состояний"""
    try:
        state_dir = '/tmp/user_states'
        if not os.path.exists(state_dir):
            return
        
        current_time = time.time()
        for filename in os.listdir(state_dir):
            filepath = os.path.join(state_dir, filename)
            if os.path.isfile(filepath):
                # Проверяем возраст файла
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_hours * 3600:
                    os.remove(filepath)
                    logger.info(f"🧹 Удален старый файл состояния: {filename}")
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке старых файлов: {e}")

# Вызываем при загрузке модуля
cleanup_old_state_files()

# ============================================
# ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ
# ============================================

def show_stage_1_intro(message, user_id: int, state_data: dict):
    """Экран перед ЭТАПОМ 1"""
    logger.info(f"📢 show_stage_1_intro для user {user_id}")
    intro_text = f"""
🧠 <b>ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>

Восприятие — это линза, через которую вы смотрите на мир.

🔍 <b>Что мы исследуем:</b>
• Куда направлено ваше внимание — вовне или внутрь
• Какая тревога доминирует — страх отвержения или страх потери контроля

📊 <b>Вопросов:</b> 8
⏱ <b>Время:</b> ~3 минуты

Отвечайте честно — это поможет мне лучше понять вас.
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_1"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True, keep_last=1)
    state_data["stage"] = 1
    state_data["stage1_current"] = 0
    logger.info(f"✅ stage1 инициализирован, stage1_current=0")

def start_stage_1(message, user_id: int, state_data: dict):
    """Начало ЭТАПА 1"""
    logger.info(f"🎬 start_stage_1 для user {user_id}")
    state_data.update({
        "stage1_current": 0,
        "stage1_last_answered": -1,
        "stage1_start_time": time.time(),
        "perception_scores": {"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0},
        "stage": 1
    })
    logger.info(f"✅ state_data обновлен: stage1_current=0")
    
    ask_stage_1_question(message, user_id, state_data)

def ask_stage_1_question(message, user_id: int, state_data: dict):
    """Задаёт вопрос ЭТАПА 1"""
    current = state_data.get("stage1_current", 0)
    total = get_stage1_total()
    
    logger.info(f"❓ ask_stage_1_question: current={current}, total={total}")
    
    if current >= total:
        logger.info(f"🎯 Все вопросы отвечены (current={current} >= total={total}), вызываем finish_stage_1")
        finish_stage_1(message, user_id, state_data)
        return
    
    question = get_stage1_question(current)
    logger.info(f"📋 Вопрос {current+1}/{total}: {question['text'][:50]}...")
    
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 <b>ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage1_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)
    logger.info(f"✅ Вопрос {current+1} отправлен")

def handle_stage_1_answer(call, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 1"""
    logger.info(f"📥 handle_stage_1_answer для user {user_id}, data={call.data}")
    logger.info(f"📊 stage1_current до обработки = {state_data.get('stage1_current')}")
    
    if state_data.get("processing", False):
        logger.info(f"⚠️ Уже обрабатывается, пропускаем")
        return
    
    state_data["processing"] = True
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            logger.error(f"❌ Неправильный формат callback: {call.data}")
            return
        
        if not parts[1].isdigit():
            logger.error(f"❌ Неправильный индекс вопроса: {parts[1]}")
            return
        current = int(parts[1])
        option_id = parts[2]
        
        logger.info(f"📝 Обработка ответа на вопрос {current}, опция {option_id}")
        
        last_answered = state_data.get("stage1_last_answered", -1)
        if current <= last_answered:
            logger.info(f"⏭️ Вопрос {current} уже отвечен (last_answered={last_answered}), пропускаем")
            return
        
        question = get_stage1_question(current)
        if not question:
            logger.error(f"❌ Вопрос {current} не найден")
            return
            
        selected_option = question["options"].get(option_id)
        if not selected_option:
            logger.error(f"❌ Опция {option_id} не найдена в вопросе {current}")
            return
        
        logger.info(f"✅ Ответ: {selected_option['text']}")
        
        perception_scores = state_data.get("perception_scores", {})
        for axis, score in selected_option.get("scores", {}).items():
            if axis in ["EXTERNAL", "INTERNAL", "SYMBOLIC", "MATERIAL"]:
                perception_scores[axis] = perception_scores.get(axis, 0) + score
                logger.info(f"📊 {axis} +{score} = {perception_scores[axis]}")
        
        all_answers = state_data.get("all_answers", [])
        all_answers.append({
            'stage': 1,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'scores': selected_option.get('scores', {})
        })
        
        new_current = current + 1
        state_data.update({
            "perception_scores": perception_scores,
            "stage1_last_answered": current,
            "stage1_current": new_current,
            "all_answers": all_answers
        })
        
        logger.info(f"📈 stage1_current обновлен: {current} -> {new_current}")
        
        ask_stage_1_question(call.message, user_id, state_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в stage1: {e}")
        import traceback
        traceback.print_exc()
        ask_stage_1_question(call.message, user_id, state_data)
    finally:
        state_data["processing"] = False

def finish_stage_1(message, user_id: int, state_data: dict):
    """Завершение ЭТАПА 1"""
    from main import user_data
    
    logger.info(f"🏁 finish_stage_1 для user {user_id}")
    
    perception_scores = state_data.get("perception_scores", {})
    perception_type = determine_perception_type(perception_scores)
    
    logger.info(f"📊 perception_scores = {perception_scores}")
    logger.info(f"🎯 perception_type = {perception_type}")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["perception_type"] = perception_type
    
    logger.info(f"✅ User {user_id}: Stage 1 complete, type={perception_type}")

    # 💾 Сохраняем состояние в файл
    try:
        # Создаем директорию для состояний, если её нет
        state_dir = '/tmp/user_states'
        os.makedirs(state_dir, exist_ok=True)
        
        state_file = os.path.join(state_dir, f'user_{user_id}_stage1.json')
        
        # Сохраняем данные
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump({
                'perception_type': perception_type,
                'perception_scores': perception_scores,
                'timestamp': time.time()
            }, f, ensure_ascii=False, indent=2)
        
        # Проверяем, что файл действительно создан
        if os.path.exists(state_file):
            logger.info(f"✅ Состояние пользователя {user_id} сохранено в {state_file} (размер: {os.path.getsize(state_file)} байт)")
        else:
            logger.error(f"❌ Файл состояния не создан: {state_file}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения состояния пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
    
    result_text = STAGE_1_FEEDBACK.get(perception_type, STAGE_1_FEEDBACK["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"])
    logger.info(f"📋 result_text = {result_text[:100]}...")
    
    text = f"{result_text}\n\n▶️ <b>Перейти к этапу 2</b>"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 2", callback_data="show_stage_2_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    state_data["stage"] = 2
    logger.info(f"✅ Этап 1 завершен, stage установлен в 2")
    
    # Очищаем временные данные этапа 1
    for key in ['stage1_current', 'stage1_last_answered', 'processing', 'perception_scores']:
        if key in state_data:
            del state_data[key]

# ============================================
# ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ
# ============================================

def show_stage_2_intro(message, user_id: int, state_data: dict):
    """Экран перед ЭТАПОМ 2"""
    from main import user_data
    
    logger.info(f"📢 show_stage_2_intro для user {user_id}")

    # Пытаемся загрузить сохраненное состояние из файла
    state_file = f'/tmp/user_states/user_{user_id}_stage1.json'
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
            
            # Проверяем, что файл содержит нужные данные
            if saved_state and 'perception_type' in saved_state:
                # Восстанавливаем данные в user_data
                if user_id not in user_data:
                    user_data[user_id] = {}
                
                # Восстанавливаем perception_type, если его нет в памяти
                if "perception_type" not in user_data[user_id]:
                    user_data[user_id]["perception_type"] = saved_state.get('perception_type')
                    logger.info(f"✅ Восстановлен perception_type для user {user_id}: {saved_state.get('perception_type')}")
                    
                # Также восстанавливаем в state_data, если нужно
                if "perception_scores" not in state_data and "perception_scores" in saved_state:
                    state_data["perception_scores"] = saved_state.get('perception_scores')
                    
                logger.info(f"✅ Состояние успешно восстановлено из {state_file}")
            else:
                logger.warning(f"⚠️ Файл состояния {state_file} не содержит нужных данных")
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки состояния для user {user_id}: {e}")
    else:
        logger.info(f"ℹ️ Файл состояния {state_file} не найден")
    
    # Получаем perception_type (либо из памяти, либо из восстановленного)
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    total_questions = get_stage2_total(perception_type)
    
    logger.info(f"📊 Используется perception_type: {perception_type}")
    
    intro_text = f"""
🧠 <b>ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>

Восприятие определяет, что вы видите. Мышление — как вы это понимаете.

🎯 <b>Самое важное:</b>
Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте. Если ничего не менять — вы попадёте именно туда.

📊 <b>Вопросов:</b> {total_questions}
⏱ <b>Время:</b> ~3-4 минуты

Продолжим исследование?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_2"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True, keep_last=1)

def start_stage_2(message, user_id: int, state_data: dict):
    """Начало ЭТАПА 2"""
    logger.info(f"🎬 start_stage_2 для user {user_id}")
    state_data.update({
        "stage2_current": 0,
        "stage2_last_answered": -1,
        "stage2_start_time": time.time(),
        "stage2_level_scores_dict": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0},
        "strategy_levels": {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []},
        "stage": 2
    })
    
    ask_stage_2_question(message, user_id, state_data)

def ask_stage_2_question(message, user_id: int, state_data: dict):
    """Задаёт вопрос ЭТАПА 2"""
    from main import user_data
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    current = state_data.get("stage2_current", 0)
    total_questions = get_stage2_total(perception_type)
    
    logger.info(f"❓ ask_stage_2_question: current={current}, total={total_questions}")
    
    if current >= total_questions:
        logger.info(f"🎯 Все вопросы этапа 2 отвечены, завершаем")
        finish_stage_2(message, user_id, state_data)
        return
    
    question = get_stage2_question(perception_type, current)
    if not question:
        logger.error(f"❌ Вопрос {current} не найден для типа {perception_type}")
        finish_stage_2(message, user_id, state_data)
        return
    
    measures = question.get("measures", "thinking")
    progress = calculate_progress(current + 1, total_questions)
    
    question_text = f"""
🧠 <b>ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for level_num, answer_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=answer_text,
            callback_data=f"stage2_{current}_{level_num}_{measures}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_2_answer(call, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 2"""
    from main import user_data
    
    logger.info(f"📥 handle_stage_2_answer для user {user_id}, data={call.data}")
    
    if state_data.get("processing", False):
        return
    
    state_data["processing"] = True
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        selected_level = parts[2]
        measures = parts[3]
        
        last_answered = state_data.get("stage2_last_answered", -1)
        if current <= last_answered:
            return
        
        perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception_type, current)
        if not question:
            return
        
        answer_text = question["options"].get(selected_level, "неизвестно")
        
        stage2_level_scores_dict = state_data.get("stage2_level_scores_dict", {})
        
        if measures == "thinking":
            points = get_stage2_score(perception_type, current, selected_level)
            stage2_level_scores_dict[selected_level] = stage2_level_scores_dict.get(selected_level, 0) + points
            logger.info(f"📊 thinking score +{points} для уровня {selected_level}")
        
        strategy_levels = state_data.get("strategy_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if measures in ["СБ", "ТФ", "УБ", "ЧВ"]:
            try:
                value = int(selected_level)
                strategy_levels[measures].append(value)
                logger.info(f"📊 strategy {measures} +{value}")
            except ValueError:
                pass
        
        all_answers = state_data.get("all_answers", [])
        all_answers.append({
            'stage': 2,
            'question_index': current,
            'question': question['text'],
            'answer': answer_text,
            'option': selected_level,
            'measures': measures,
            'perception_type': perception_type
        })
        
        state_data.update({
            "stage2_level_scores_dict": stage2_level_scores_dict,
            "strategy_levels": strategy_levels,
            "stage2_last_answered": current,
            "stage2_current": current + 1,
            "all_answers": all_answers
        })
        
        ask_stage_2_question(call.message, user_id, state_data)
        
    except Exception as e:
        logger.error(f"Ошибка в stage2: {e}")
        ask_stage_2_question(call.message, user_id, state_data)
    finally:
        state_data["processing"] = False

def finish_stage_2(message, user_id: int, state_data: dict):
    """Завершение ЭТАПА 2"""
    from main import user_data
    
    logger.info(f"🏁 finish_stage_2 для user {user_id}")
    
    level_scores_dict = state_data.get("stage2_level_scores_dict", {})
    thinking_level = calculate_thinking_level_by_scores(level_scores_dict)
    
    logger.info(f"📊 level_scores_dict = {level_scores_dict}")
    logger.info(f"🎯 thinking_level = {thinking_level}")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["thinking_level"] = thinking_level
    
    # Сохраняем стратегии
    strategy_levels = state_data.get("strategy_levels", {})
    user_data[user_id]["behavioral_levels"] = strategy_levels
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    level_group = get_level_group(thinking_level)
    
    logger.info(f"✅ User {user_id}: Stage 2 complete, level={thinking_level}")
    
    result_text = STAGE_2_FEEDBACK.get((perception_type, level_group))
    if not result_text:
        result_text = STAGE_2_FEEDBACK[("СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "1-3")]
    
    text = f"{result_text}\n\n▶️ <b>Перейти к этапу 3</b>"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 3", callback_data="show_stage_3_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    state_data["stage"] = 3

# ============================================
# ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ
# ============================================

def show_stage_3_intro(message, user_id: int, state_data: dict):
    """Экран перед ЭТАПОМ 3"""
    logger.info(f"📢 show_stage_3_intro для user {user_id}")
    
    intro_text = f"""
🧠 <b>ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>

Восприятие определяет, что вы видите.
Мышление — как вы это понимаете.

Конфигурация поведения — это то, как вы на это реагируете.

🔍 <b>Здесь мы исследуем:</b>
• Ваши автоматические реакции
• Как вы действуете в разных ситуациях
• Какие стратегии поведения закреплены

📊 <b>Вопросов:</b> 8
⏱ <b>Время:</b> ~3 минуты

Продолжим?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_3"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True, keep_last=1)

def start_stage_3(message, user_id: int, state_data: dict):
    """Начало ЭТАПА 3"""
    logger.info(f"🎬 start_stage_3 для user {user_id}")
    state_data.update({
        "stage3_current": 0,
        "stage3_last_answered": -1,
        "stage3_start_time": time.time(),
        "stage3_level_scores": [],
        "behavioral_levels": {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []},
        "stage": 3
    })
    
    ask_stage_3_question(message, user_id, state_data)

def ask_stage_3_question(message, user_id: int, state_data: dict):
    """Задаёт вопрос ЭТАПА 3"""
    current = state_data.get("stage3_current", 0)
    total = get_stage3_total()
    
    logger.info(f"❓ ask_stage_3_question: current={current}, total={total}")
    
    if current >= total:
        finish_stage_3(message, user_id, state_data)
        return
    
    question = get_stage3_question(current)
    strategy = question.get("strategy", "УБ")
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 <b>ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option_text,
            callback_data=f"stage3_{current}_{option_id}_{strategy}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_3_answer(call, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 3"""
    logger.info(f"📥 handle_stage_3_answer для user {user_id}, data={call.data}")
    
    if state_data.get("processing", False):
        return
    
    state_data["processing"] = True
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        strategy = parts[3]
        
        stage3_current = state_data.get("stage3_current", 0)
        
        if current < stage3_current:
            ask_stage_3_question(call.message, user_id, state_data)
            return
        
        question = get_stage3_question(current)
        option_text = question["options"].get(option_id)
        
        if not option_text:
            return
        
        try:
            level_val = int(option_id)
        except ValueError:
            level_val = 1
        
        stage3_level_scores = state_data.get("stage3_level_scores", [])
        stage3_level_scores.append(level_val)
        
        behavioral_levels = state_data.get("behavioral_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if strategy in ["СБ", "ТФ", "УБ", "ЧВ"]:
            behavioral_levels[strategy].append(level_val)
        
        all_answers = state_data.get("all_answers", [])
        all_answers.append({
            'stage': 3,
            'question_index': current,
            'question': question['text'],
            'answer': option_text,
            'answer_value': level_val,
            'strategy': strategy
        })
        
        state_data.update({
            "stage3_level_scores": stage3_level_scores,
            "behavioral_levels": behavioral_levels,
            "stage3_last_answered": current,
            "stage3_current": current + 1,
            "all_answers": all_answers
        })
        
        ask_stage_3_question(call.message, user_id, state_data)
        
    except Exception as e:
        logger.error(f"Ошибка в stage3: {e}")
        ask_stage_3_question(call.message, user_id, state_data)
    finally:
        state_data["processing"] = False

def finish_stage_3(message, user_id: int, state_data: dict):
    """Завершение ЭТАПА 3"""
    from main import user_data
    
    logger.info(f"🏁 finish_stage_3 для user {user_id}")
    
    stage2_level = user_data.get(user_id, {}).get("thinking_level", 1)
    stage3_scores = state_data.get("stage3_level_scores", [])
    
    final_level = calculate_final_level(stage2_level, stage3_scores)
    
    logger.info(f"📊 stage2_level={stage2_level}, stage3_scores={stage3_scores}")
    logger.info(f"🎯 final_level={final_level}")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["final_level"] = final_level
    
    # Сохраняем поведенческие уровни
    behavioral_levels = state_data.get("behavioral_levels", {})
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
    
    text = f"{result_text}\n\n▶️ <b>Перейти к этапу 4</b>"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 4", callback_data="show_stage_4_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    state_data["stage"] = 4

# ============================================
# ЭТАП 4: ТОЧКА РОСТА
# ============================================

def show_stage_4_intro(message, user_id: int, state_data: dict):
    """Экран перед ЭТАПОМ 4"""
    logger.info(f"📢 show_stage_4_intro для user {user_id}")
    
    intro_text = f"""
🧠 <b>ЭТАП 4: ТОЧКА РОСТА</b>

Восприятие — что вы видите.
Мышление — как понимаете.
Поведение — как реагируете.

🌍 Но она живёт внутри внешней системы — общества, которое постоянно меняется.

⚡ Когда одна система меняется, а другая — нет, возникает напряжение.

🔍 <b>Здесь мы найдём:</b> где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.

📊 <b>Вопросов:</b> 8
⏱ <b>Время:</b> ~3 минуты

Готовы найти свою точку роста?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_4"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True, keep_last=1)

def start_stage_4(message, user_id: int, state_data: dict):
    """Начало ЭТАПА 4"""
    logger.info(f"🎬 start_stage_4 для user {user_id}")
    state_data.update({
        "stage4_current": 0,
        "stage4_last_answered": -1,
        "stage4_start_time": time.time(),
        "dilts_counts": {"ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0},
        "stage": 4
    })
    
    ask_stage_4_question(message, user_id, state_data)

def ask_stage_4_question(message, user_id: int, state_data: dict):
    """Задаёт вопрос ЭТАПА 4"""
    current = state_data.get("stage4_current", 0)
    total = get_stage4_total()
    
    logger.info(f"❓ ask_stage_4_question: current={current}, total={total}")
    
    if current >= total:
        finish_stage_4(message, user_id, state_data)
        return
    
    question = get_stage4_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 <b>ЭТАП 4: ТОЧКА РОСТА</b>

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage4_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_4_answer(call, user_id: int, state_data: dict):
    """Обработка ответа ЭТАПА 4"""
    logger.info(f"📥 handle_stage_4_answer для user {user_id}, data={call.data}")
    
    if state_data.get("processing", False):
        return
    
    state_data["processing"] = True
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = state_data.get("stage4_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage4_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        dilts = selected_option.get("dilts", "BEHAVIOR")
        dilts_counts = state_data.get("dilts_counts", {})
        dilts_counts[dilts] = dilts_counts.get(dilts, 0) + 1
        
        all_answers = state_data.get("all_answers", [])
        all_answers.append({
            'stage': 4,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'dilts': dilts
        })
        
        state_data.update({
            "dilts_counts": dilts_counts,
            "stage4_last_answered": current,
            "stage4_current": current + 1,
            "all_answers": all_answers
        })
        
        ask_stage_4_question(call.message, user_id, state_data)
        
    except Exception as e:
        logger.error(f"Ошибка в stage4: {e}")
        ask_stage_4_question(call.message, user_id, state_data)
    finally:
        state_data["processing"] = False

def finish_stage_4(message, user_id: int, state_data: dict):
    """Завершение ЭТАПА 4"""
    from main import user_data
    
    logger.info(f"🏁 finish_stage_4 для user {user_id}")
    
    dilts_counts = state_data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    logger.info(f"📊 dilts_counts = {dilts_counts}")
    logger.info(f"🎯 dominant_dilts = {dominant_dilts}")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["dilts_counts"] = dilts_counts
    user_data[user_id]["dominant_dilts"] = dominant_dilts
    
    # Рассчитываем финальный профиль
    profile_data = calculate_profile_final(user_data[user_id])
    user_data[user_id]["profile_data"] = profile_data
    
    # Строим конфайнмент-модель
    scores = {}
    for vector in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = user_data[user_id].get("behavioral_levels", {}).get(vector, [])
        scores[vector] = sum(levels) / len(levels) if levels else 3
    
    model = ConfinementModel9(user_id)
    model.build_from_profile(scores, user_data[user_id].get('history', []))
    user_data[user_id]["confinement_model"] = model.to_dict()
    
    logger.info(f"✅ User {user_id}: Stage 4 complete, profile={profile_data.get('display_name', 'unknown')}")
    
    # Показываем предварительный профиль
    show_preliminary_profile(message, user_id, state_data)

def show_preliminary_profile(message, user_id: int, state_data: dict):
    """Показывает предварительный портрет после 4 этапа"""
    from main import user_data, user_contexts
    
    logger.info(f"📢 show_preliminary_profile для user {user_id}")
    
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "unknown")
    thinking_level = data.get("thinking_level", 5)
    
    simple_profile = convert_to_simple_language(
        scores, perception_type, thinking_level
    )
    
    confidence = calculate_profile_confidence(data)
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    text = f"""
🧠 <b>ПРЕДВАРИТЕЛЬНЫЙ ПОРТРЕТ</b>

{simple_profile['attention_desc']}

{simple_profile['thinking_desc']}

📊 <b>ТВОИ ВЕКТОРЫ:</b>
• <b>Реакция на давление:</b> {simple_profile['sb_desc']}
• <b>Отношение к деньгам:</b> {simple_profile['tf_desc']}
• <b>Понимание мира:</b> {simple_profile['ub_desc']}
• <b>Отношения с людьми:</b> {simple_profile['chv_desc']}

🎯 <b>Точка роста:</b> {simple_profile['growth_point']}

📊 <b>Уверенность:</b> {confidence_bar} {int(confidence*100)}%

👇 <b>ЭТО ПОХОЖЕ НА ВАС?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ ДА", callback_data="profile_confirm"),
        InlineKeyboardButton("❓ ЕСТЬ СОМНЕНИЯ", callback_data="profile_doubt")
    )
    keyboard.row(InlineKeyboardButton("🔄 НЕТ", callback_data="profile_reject"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    state_data["stage"] = "profile_confirmation"
    logger.info(f"✅ Предварительный профиль показан")

# ============================================
# ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ
# ============================================

def show_stage_5_intro(message, user_id: int, state_data: dict):
    """Экран перед 5-м этапом"""
    logger.info(f"📢 show_stage_5_intro для user {user_id}")
    
    intro_text = f"""
🧠 <b>ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</b>

Мы узнали, как вы воспринимаете мир, мыслите и действуете.
Теперь пришло время заглянуть глубже — в то, что сформировало вас.

🔍 <b>Здесь мы исследуем:</b>
• Какой у вас тип привязанности (из детства)
• Какие защитные механизмы вы используете
• Какие глубинные убеждения управляют вами
• Чего вы боитесь на самом деле

📊 <b>Вопросов:</b> 10
⏱ <b>Время:</b> ~5 минут

👇 <b>Готовы заглянуть вглубь себя?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_5"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True, keep_last=1)
    state_data["stage"] = 5

def start_stage_5(message, user_id: int, state_data: dict):
    """Начало 5-го этапа"""
    logger.info(f"🎬 start_stage_5 для user {user_id}")
    state_data.update({
        "stage5_current": 0,
        "stage5_last_answered": -1,
        "stage5_answers": []
    })
    
    ask_stage_5_question(message, user_id, state_data)

def ask_stage_5_question(message, user_id: int, state_data: dict):
    """Задаёт вопрос 5-го этапа"""
    current = state_data.get("stage5_current", 0)
    total = get_stage5_total()
    
    logger.info(f"❓ ask_stage_5_question: current={current}, total={total}")
    
    if current >= total:
        finish_stage_5(message, user_id, state_data)
        return
    
    question = get_stage5_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 <b>ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</b>

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage5_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_5_answer(call, user_id: int, state_data: dict):
    """Обработка ответа 5-го этапа"""
    logger.info(f"📥 handle_stage_5_answer для user {user_id}, data={call.data}")
    
    if state_data.get("processing", False):
        return
    
    state_data["processing"] = True
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = state_data.get("stage5_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage5_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        stage5_answers = state_data.get("stage5_answers", [])
        stage5_answers.append({
            'question_id': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'pattern': selected_option.get('pattern'),
            'target': question.get('target')
        })
        
        state_data.update({
            "stage5_answers": stage5_answers,
            "stage5_last_answered": current,
            "stage5_current": current + 1
        })
        
        ask_stage_5_question(call.message, user_id, state_data)
        
    except Exception as e:
        logger.error(f"Ошибка в stage5: {e}")
        ask_stage_5_question(call.message, user_id, state_data)
    finally:
        state_data["processing"] = False

def finish_stage_5(message, user_id: int, state_data: dict):
    """Завершение 5-го этапа"""
    from main import user_data
    
    logger.info(f"🏁 finish_stage_5 для user {user_id}")
    
    stage5_answers = state_data.get("stage5_answers", [])
    
    deep_patterns = analyze_stage5_results(stage5_answers)
    
    logger.info(f"📊 deep_patterns = {deep_patterns}")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["deep_patterns"] = deep_patterns
    
    logger.info(f"✅ User {user_id}: Stage 5 complete")
    
    # Импортируем здесь, чтобы избежать циклических импортов
    try:
        from handlers.profile import show_final_profile
    except ImportError:
        # Если не получается, пробуем другой путь
        from profile import show_final_profile
    
    show_final_profile(message, user_id)

# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Этап 1
    'show_stage_1_intro', 'start_stage_1', 'ask_stage_1_question',
    'handle_stage_1_answer', 'finish_stage_1',
    
    # Этап 2
    'show_stage_2_intro', 'start_stage_2', 'ask_stage_2_question',
    'handle_stage_2_answer', 'finish_stage_2',
    
    # Этап 3
    'show_stage_3_intro', 'start_stage_3', 'ask_stage_3_question',
    'handle_stage_3_answer', 'finish_stage_3',
    
    # Этап 4
    'show_stage_4_intro', 'start_stage_4', 'ask_stage_4_question',
    'handle_stage_4_answer', 'finish_stage_4',
    
    # Этап 5
    'show_stage_5_intro', 'start_stage_5', 'ask_stage_5_question',
    'handle_stage_5_answer', 'finish_stage_5',
    
    # Вспомогательные
    'show_preliminary_profile',
    'cleanup_old_state_files'
]
