#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики для показа профиля и результатов тестирования
"""
import logging
import time
from typing import Dict, Any, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import (
    get_profile_keyboard, get_ai_profile_keyboard,
    get_psychologist_thought_keyboard, get_back_keyboard
)
from formatters import bold

# Импорты из state.py
from state import user_data, get_user_context, get_user_context_dict

# Импорты из profiles.py (только константы)
from profiles import (
    VECTORS, LEVEL_PROFILES, DILTS_LEVELS,
    STAGE_1_FEEDBACK, STAGE_2_FEEDBACK, STAGE_3_FEEDBACK
)
from services import generate_ai_profile, generate_psychologist_thought
from confinement_model import build_confinement_model
from models import UserContext

logger = logging.getLogger(__name__)

# ============================================
# ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ ПРОФИЛЯ (ДОБАВЛЕНЫ)
# ============================================

def get_profile_display(profile_data: Dict[str, Any]) -> str:
    """Возвращает отображаемое название профиля"""
    return profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')

def get_perception_description(perception_type: str) -> str:
    """Возвращает описание типа восприятия"""
    descriptions = {
        "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ": "Вы ориентируетесь на мнение других, чутко считываете настроение и ожидания окружающих.",
        "СТАТУСНО-ОРИЕНТИРОВАННЫЙ": "Для вас важны статус, положение в обществе, внешние атрибуты успеха.",
        "СМЫСЛО-ОРИЕНТИРОВАННЫЙ": "Вы ищете глубинные смыслы, важнее понимание, чем внешние проявления.",
        "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ": "Вы ориентируетесь на практические результаты, конкретные действия и факты."
    }
    return descriptions.get(perception_type, "Тип восприятия не определен")

def get_dilts_description(dominant_dilts: str) -> str:
    """Возвращает описание доминирующего уровня Дилтса"""
    descriptions = {
        "ENVIRONMENT": "Вы часто ищете причины проблем в окружении, обстоятельствах, других людях.",
        "BEHAVIOR": "Вы фокусируетесь на действиях и поведении — своём и других.",
        "CAPABILITIES": "Для вас важны навыки, способности, компетенции.",
        "VALUES": "Вы руководствуетесь ценностями и убеждениями, они определяют ваш выбор.",
        "IDENTITY": "Вы ищете ответы на вопросы «кто я?», «какова моя миссия?»."
    }
    return descriptions.get(dominant_dilts, "Уровень не определен")

def get_vectors_description(sb: int, tf: int, ub: int, chv: int) -> str:
    """Возвращает описание векторов"""
    lines = []
    
    sb_desc = {
        1: "Под давлением замираете, теряетесь",
        2: "Избегаете конфликтов, уходите",
        3: "Внешне соглашаетесь, внутри кипите",
        4: "Внешне спокойны, внутри держите всё в себе",
        5: "Пытаетесь сгладить конфликт",
        6: "Умеете защищать себя и других"
    }.get(sb, "Реагируете по-разному")
    
    tf_desc = {
        1: "Деньги приходят и уходят хаотично",
        2: "Ищете возможности, но не системно",
        3: "Умеете зарабатывать трудом",
        4: "Можете копить и планировать",
        5: "Создаёте системы дохода",
        6: "Управляете капиталом"
    }.get(tf, "Свои отношения с деньгами")
    
    ub_desc = {
        1: "Не задумываетесь о сложном",
        2: "Верите в знаки и судьбу",
        3: "Доверяете экспертам",
        4: "Ищете скрытые смыслы",
        5: "Анализируете факты",
        6: "Строите теории"
    }.get(ub, "По-своему понимаете мир")
    
    chv_desc = {
        1: "Сильно привязываетесь к людям",
        2: "Подстраиваетесь под других",
        3: "Хотите нравиться, показываете себя",
        4: "Умеете влиять на людей",
        5: "Строите равные партнёрства",
        6: "Создаёте сообщества"
    }.get(chv, "Свои паттерны в отношениях")
    
    lines.append(f"• СБ (реакция на давление): {sb_desc}")
    lines.append(f"• ТФ (деньги): {tf_desc}")
    lines.append(f"• УБ (понимание мира): {ub_desc}")
    lines.append(f"• ЧВ (отношения): {chv_desc}")
    
    return "\n".join(lines)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОФИЛЕМ
# ============================================

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Получает профиль пользователя из глобального хранилища"""
    data = user_data.get(user_id, {})
    return data.get("profile_data", {})

def save_user_profile(user_id: int, profile_data: Dict[str, Any]):
    """Сохраняет профиль пользователя в глобальное хранилище"""
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["profile_data"] = profile_data

def is_test_completed(user_data_dict: dict) -> bool:
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
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def show_profile(message, user_id: int = None):
    """
    Показывает профиль пользователя
    """
    if user_id is None:
        user_id = message.chat.id
    
    # Получаем данные профиля из user_data
    user_data_dict = user_data.get(user_id, {})
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data and not is_test_completed(user_data_dict):
        # Если профиля нет, предлагаем пройти тест
        text = """
📋 ПРОФИЛЬ НЕ НАЙДЕН

У вас ещё нет профиля. Пройдите тест, чтобы узнать себя лучше.
"""
        keyboard = get_back_keyboard("main_menu")
        keyboard.add(InlineKeyboardButton("🚀 ПРОЙТИ ТЕСТ", callback_data="start_context"))
        
        safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
        return
    
    # Форматируем профиль для отображения
    profile_text = format_profile_display(user_data_dict, context)
    
    keyboard = get_profile_keyboard()
    
    safe_send_message(message, profile_text, reply_markup=keyboard, delete_previous=True)


def format_profile_display(user_data_dict: Dict[str, Any], context: Optional[UserContext] = None) -> str:
    """Форматирует профиль для отображения"""
    name = context.name if context and context.name else "Пользователь"
    
    profile_data = user_data_dict.get("profile_data", {})
    
    # Основной код профиля
    profile_code = get_profile_display(profile_data)
    
    # Расшифровка векторов
    sb = profile_data.get('sb_level', 4)
    tf = profile_data.get('tf_level', 4)
    ub = profile_data.get('ub_level', 4)
    chv = profile_data.get('chv_level', 4)
    
    # Тип восприятия
    perception = user_data_dict.get('perception_type', 'не определен')
    perception_desc = get_perception_description(perception)
    
    # Уровень мышления
    thinking = user_data_dict.get('thinking_level', 5)
    
    # Доминирующий уровень Дилтса
    dilts = profile_data.get('dominant_dilts', 'BEHAVIOR')
    dilts_desc = get_dilts_description(dilts)
    
    # Векторные описания
    vectors_desc = get_vectors_description(sb, tf, ub, chv)
    
    # Точка роста
    growth = profile_data.get('growth_area', 'Поведение')
    
    text = f"""
📊 ПРОФИЛЬ {name}

🔢 КОД: {profile_code}

🧩 ВОСПРИЯТИЕ: {perception}
{perception_desc}

🧠 МЫШЛЕНИЕ: Уровень {thinking}/9

📈 ВЕКТОРЫ:
{vectors_desc}

🎯 ТОЧКА РОСТА: {growth}
{dilts_desc}

💭 Что дальше?
• AI-профиль — глубинный анализ
• Мысли психолога — взгляд со стороны
• Выбрать цель — начать работу
"""
    return text


def show_ai_profile(message, user_id: int = None):
    """
    Показывает AI-сгенерированный профиль
    """
    if user_id is None:
        user_id = message.chat.id
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🧠 Генерирую психологический портрет...\nЭто займёт около 30 секунд.",
        delete_previous=True
    )
    
    # Получаем данные
    user_data_dict = user_data.get(user_id, {})
    context = get_user_context(user_id)
    
    if not is_test_completed(user_data_dict):
        safe_send_message(
            message,
            "❌ Профиль не найден. Сначала пройдите тест.",
            reply_markup=get_back_keyboard("main_menu")
        )
        return
    
    # Генерируем AI-профиль
    ai_text = generate_ai_profile(user_id, user_data_dict)
    
    if not ai_text:
        # Если генерация не удалась, показываем заглушку
        ai_text = """
🧠 ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ

К сожалению, сейчас не удалось сгенерировать портрет.
Попробуйте позже или обратитесь к @MasterBot
"""
    
    # Добавляем имя, если есть
    name = context.name if context and context.name else ""
    if name and "обращаюсь" not in ai_text[:50]:
        ai_text = f"{name}, {ai_text[0].lower()}{ai_text[1:]}"
    
    # Показываем результат
    keyboard = get_ai_profile_keyboard()
    
    safe_send_message(
        status_msg if status_msg else message,
        ai_text,
        reply_markup=keyboard
    )


def show_psychologist_thought(message, user_id: int = None):
    """
    Показывает мысли психолога (анализ конфайнмент-модели)
    """
    if user_id is None:
        user_id = message.chat.id
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "💭 Анализирую конфайнмент-модель...\nЭто займёт около 20 секунд.",
        delete_previous=True
    )
    
    # Получаем данные
    user_data_dict = user_data.get(user_id, {})
    context = get_user_context(user_id)
    
    if not is_test_completed(user_data_dict):
        safe_send_message(
            message,
            "❌ Профиль не найден. Сначала пройдите тест.",
            reply_markup=get_back_keyboard("main_menu")
        )
        return
    
    # Строим или получаем конфайнмент-модель
    if "confinement_model" not in user_data_dict:
        confinement = build_confinement_model(user_data_dict)
        user_data_dict["confinement_model"] = confinement.to_dict() if confinement else {}
        user_data[user_id] = user_data_dict
    
    # Генерируем мысли психолога
    thoughts = generate_psychologist_thought(user_id, user_data_dict)
    
    if not thoughts:
        # Если генерация не удалась, показываем заглушку
        thoughts = """
💭 МЫСЛИ ПСИХОЛОГА

К сожалению, сейчас не удалось провести анализ.
Попробуйте позже или обратитесь к @MasterBot
"""
    
    # Показываем результат
    keyboard = get_psychologist_thought_keyboard()
    
    safe_send_message(
        status_msg if status_msg else message,
        thoughts,
        reply_markup=keyboard
    )


def show_final_profile(message, user_id: int):
    """
    Показывает финальный профиль после завершения теста
    """
    # Получаем данные
    user_data_dict = user_data.get(user_id, {})
    context = get_user_context(user_id)
    
    if not is_test_completed(user_data_dict):
        # Если профиля нет, возвращаемся в меню
        from .start import cmd_start
        cmd_start(message)
        return
    
    name = context.name if context and context.name else ""
    
    text = f"""
🎉 ТЕСТ ЗАВЕРШЁН!

{name}, спасибо за прохождение теста «Матрица поведений 4×6».

📊 ТВОЙ ПРОФИЛЬ СОЗДАН!

Теперь ты можешь:
• Посмотреть AI-профиль — глубинный анализ
• Узнать мысли психолога — взгляд на твою систему
• Выбрать цель — начать работу над собой

С чего начнём?
"""
    
    keyboard = get_profile_keyboard()
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)


# ============================================
# ДЕТАЛЬНЫЙ ПРОФИЛЬ (ВСЕ ДАННЫЕ)
# ============================================

def show_detailed_profile(message, user_id: int = None):
    """
    Показывает детальный профиль со всеми данными
    """
    if user_id is None:
        user_id = message.chat.id
    
    user_data_dict = user_data.get(user_id, {})
    context = get_user_context(user_id)
    
    if not is_test_completed(user_data_dict):
        show_profile(message, user_id)
        return
    
    name = context.name if context and context.name else "Пользователь"
    
    profile_data = user_data_dict.get("profile_data", {})
    
    # Все данные в сыром виде
    profile_code = get_profile_display(profile_data)
    sb = profile_data.get('sb_level', 4)
    tf = profile_data.get('tf_level', 4)
    ub = profile_data.get('ub_level', 4)
    chv = profile_data.get('chv_level', 4)
    perception = user_data_dict.get('perception_type', 'не определен')
    thinking = user_data_dict.get('thinking_level', 5)
    final_level = user_data_dict.get('final_level', 5)
    
    # Поведенческие уровни
    behavioral = user_data_dict.get('behavioral_levels', {})
    sb_levels = behavioral.get('СБ', [])
    tf_levels = behavioral.get('ТФ', [])
    ub_levels = behavioral.get('УБ', [])
    chv_levels = behavioral.get('ЧВ', [])
    
    # Дилтс
    dilts_counts = user_data_dict.get('dilts_counts', {})
    dominant_dilts = user_data_dict.get('dominant_dilts', 'BEHAVIOR')
    
    # Глубинные паттерны
    deep_patterns = user_data_dict.get('deep_patterns', {})
    
    text = f"""
📊 ДЕТАЛЬНЫЙ ПРОФИЛЬ {name}

🔢 КОД: {profile_code}

🧩 ВОСПРИЯТИЕ: {perception}
🧠 МЫШЛЕНИЕ: {thinking}/9
📊 ФИНАЛЬНЫЙ УРОВЕНЬ: {final_level}/6

📈 ПОВЕДЕНЧЕСКИЕ УРОВНИ:
СБ: {sb_levels} → {sb}
ТФ: {tf_levels} → {tf}
УБ: {ub_levels} → {ub}
ЧВ: {chv_levels} → {chv}

🎯 УРОВНИ ДИЛТСА:
{dilts_counts}
Доминирующий: {dominant_dilts}

🌀 ГЛУБИННЫЕ ПАТТЕРНЫ:
Привязанность: {deep_patterns.get('attachment', 'не определен')}
Защиты: {', '.join(deep_patterns.get('defense_mechanisms', ['нет']))}
Убеждения: {', '.join(deep_patterns.get('core_beliefs', ['нет']))}
"""
    
    keyboard = get_back_keyboard("show_profile")
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)


# ============================================
# ЭКСПОРТ ПРОФИЛЯ (ДЛЯ ПОЛЬЗОВАТЕЛЯ)
# ============================================

def export_profile(message, user_id: int = None):
    """
    Экспортирует профиль в текстовый файл
    """
    if user_id is None:
        user_id = message.chat.id
    
    user_data_dict = user_data.get(user_id, {})
    context = get_user_context(user_id)
    
    if not is_test_completed(user_data_dict):
        safe_send_message(message, "❌ Профиль не найден")
        return
    
    name = context.name if context and context.name else "Пользователь"
    
    # Формируем текст для экспорта
    export_text = f"""ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {name}
ДАТА: {time.strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}

{format_profile_display(user_data_dict, context)}

{'='*50}

ДЕТАЛЬНЫЕ ДАННЫЕ:
{user_data_dict}

{'='*50}
"""
    
    # В MAX нет прямого способа отправить файл,
    # поэтому отправляем как обычное сообщение с пометкой
    text = f"""
📁 ЭКСПОРТ ПРОФИЛЯ

{export_text[:3000]}...
(профиль слишком длинный для сообщения)
"""
    
    keyboard = get_back_keyboard("show_profile")
    
    safe_send_message(message, text, reply_markup=keyboard)


# ============================================
# СРАВНЕНИЕ ПРОФИЛЕЙ
# ============================================

def compare_profiles(message, user_id1: int, user_id2: int):
    """
    Сравнивает два профиля (для админов/парной работы)
    """
    data1 = user_data.get(user_id1, {})
    data2 = user_data.get(user_id2, {})
    context1 = get_user_context(user_id1)
    context2 = get_user_context(user_id2)
    
    if not is_test_completed(data1) or not is_test_completed(data2):
        safe_send_message(message, "❌ Один из профилей не найден")
        return
    
    name1 = context1.name if context1 and context1.name else f"User {user_id1}"
    name2 = context2.name if context2 and context2.name else f"User {user_id2}"
    
    profile1 = data1.get("profile_data", {})
    profile2 = data2.get("profile_data", {})
    
    code1 = get_profile_display(profile1)
    code2 = get_profile_display(profile2)
    
    text = f"""
🔄 СРАВНЕНИЕ ПРОФИЛЕЙ

👤 {name1}: {code1}
👤 {name2}: {code2}

{'='*30}

Сходства:
• Вектор СБ: {profile1.get('sb_level')} vs {profile2.get('sb_level')}
• Вектор ТФ: {profile1.get('tf_level')} vs {profile2.get('tf_level')}
• Вектор УБ: {profile1.get('ub_level')} vs {profile2.get('ub_level')}
• Вектор ЧВ: {profile1.get('chv_level')} vs {profile2.get('chv_level')}

Доминирующий уровень Дилтса:
• {name1}: {data1.get('dominant_dilts')}
• {name2}: {data2.get('dominant_dilts')}
"""
    
    safe_send_message(message, text, reply_markup=get_back_keyboard("admin_panel"))


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

def profile_confirm(call: CallbackQuery):
    """Пользователь подтвердил профиль"""
    from .stages import show_stage_5_intro
    safe_send_message(call.message, "✅ Отлично! Тогда исследуем глубину...", delete_previous=True)
    show_stage_5_intro(call.message)


def profile_doubt(call: CallbackQuery):
    """Пользователь сомневается"""
    from .stages import ask_whats_wrong
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    
    current_levels = {}
    for vector in VECTORS:
        levels = data.get("behavioral_levels", {}).get(vector, [])
        current_levels[vector] = sum(levels) / len(levels) if levels else 3
    
    ask_whats_wrong(call, current_levels)


def profile_reject(call: CallbackQuery):
    """Пользователь полностью не согласен - показываем анекдот"""
    from .start import cmd_start
    
    # Текст с анекдотом
    anecdote = """
🧠 <b>ЧЕСТНОСТЬ - ЛУЧШАЯ ПОЛИТИКА</b>

Две подруги решили сходить на ипподром. Приходят, а там скачки, все ставки делают. Решили и они ставку сделать — вдруг повезёт? Одна другой и говорит: «Слушай, у тебя какой размер груди?». Вторая: «Второй… а у тебя?». Первая: «Третий… ну давай на пятую поставим — чтоб сумма была…».

Поставили на пятую, лошадь приходит первая, они счастливые прибегают домой с деньгами и мужьям рассказывают, как было дело.

На следующий день мужики тоже решили сходить на скачки — а вдруг им повезёт? Когда решали, на какую ставить, один говорит: «Ты сколько раз за ночь свою жену можешь удовлетворить?». Другой говорит: «Ну, три…». Первый: «А я четыре… ну давай на седьмую поставим».

Поставили на седьмую, первой пришла вторая.

Мужики переглянулись: «Не напиздили бы — выиграли…».

<b>Мораль:</b> Если врать в тесте — результат будет как у мужиков на скачках. Хотите попробовать еще раз?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔄 ПРОЙТИ ТЕСТ ЕЩЕ РАЗ", callback_data="restart_test"))
    keyboard.row(InlineKeyboardButton("👋 ДОСВИДУЛИ", callback_data="goodbye"))
    
    safe_send_message(
        call.message,
        anecdote,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


def handle_goodbye(call: CallbackQuery):
    """Обработчик кнопки Досвидули"""
    from state import clear_state
    
    safe_send_message(
        call.message,
        f"👋 {bold('До свидания!')}\n\nБуду рад помочь, если решите вернуться. Просто напишите /start",
        parse_mode='HTML',
        delete_previous=True
    )
    
    clear_state(call.from_user.id)


def show_ai_analysis(call: CallbackQuery):
    """Показывает мысли психолога"""
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else ""
    
    if data.get("psychologist_thought"):
        show_saved_psychologist_thought(call.message, user_id, data["psychologist_thought"])
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        "🧠 Анализирую через конфайнмент-модель...\n\nЭто займёт около 15-20 секунд",
        delete_previous=True
    )
    
    # Генерируем мысли
    thought = generate_psychologist_thought(user_id, data)
    
    if thought:
        user_data[user_id]["psychologist_thought"] = thought
        safe_delete_message(call.message.chat.id, status_msg.message_id)
        show_saved_psychologist_thought(call.message, user_id, thought)
    else:
        safe_delete_message(call.message.chat.id, status_msg.message_id)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("◀️ НАЗАД", callback_data="show_results"))
        safe_send_message(
            call.message,
            "❌ Не удалось сгенерировать анализ",
            reply_markup=keyboard,
            delete_previous=True
        )


def show_saved_psychologist_thought(message: types.Message, user_id: int, thought: str):
    """Показывает сохраненные мысли психолога с красивым форматированием"""
    from formatters import format_psychologist_text
    
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else ""
    
    # Форматируем текст
    formatted_thought = format_psychologist_text(thought, user_name)
    
    # Добавляем заголовок, если его нет
    if not formatted_thought.startswith("🧠"):
        formatted_thought = f"🧠 {bold('МЫСЛИ ПСИХОЛОГА')}\n\n{formatted_thought}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("◀️ К ПОРТРЕТУ", callback_data="show_results"))
    
    safe_send_message(
        message,
        formatted_thought,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_profile',
    'show_ai_profile',
    'show_psychologist_thought',
    'show_final_profile',
    'show_detailed_profile',
    'export_profile',
    'compare_profiles',
    'profile_confirm',
    'profile_doubt',
    'profile_reject',
    'handle_goodbye',
    'show_ai_analysis',
    'show_saved_psychologist_thought'
]
