#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики для показа профиля и результатов тестирования
"""
import logging
import time
from typing import Dict, Any, Optional

from bot_instance import bot
from message_utils import safe_send_message, safe_edit_message
from keyboards import (
    get_profile_keyboard, get_ai_profile_keyboard,
    get_psychologist_thought_keyboard, get_back_keyboard
)
from database import get_user_profile, save_user_profile, get_user_context
from profiles import (
    get_profile_display, get_perception_description,
    get_dilts_description, get_vectors_description
)
from services import generate_ai_profile, generate_psychologist_thought
from confinement_model import build_confinement_model
from models import UserContext

logger = logging.getLogger(__name__)

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def show_profile(message, user_id: int = None):
    """
    Показывает профиль пользователя
    """
    if user_id is None:
        user_id = message.chat.id
    
    # Получаем данные профиля
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
        # Если профиля нет, предлагаем пройти тест
        text = """
📋 ПРОФИЛЬ НЕ НАЙДЕН

У вас ещё нет профиля. Пройдите тест, чтобы узнать себя лучше.
"""
        keyboard = get_back_keyboard("main_menu")
        keyboard.add(types.InlineKeyboardButton("🚀 ПРОЙТИ ТЕСТ", callback_data="start_context"))
        
        safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
        return
    
    # Форматируем профиль для отображения
    profile_text = format_profile_display(profile_data, context)
    
    keyboard = get_profile_keyboard()
    
    safe_send_message(message, profile_text, reply_markup=keyboard, delete_previous=True)


def format_profile_display(profile_data: Dict[str, Any], context: Optional[UserContext] = None) -> str:
    """
    Форматирует профиль для отображения
    """
    name = context.name if context and context.name else "Пользователь"
    
    # Основной код профиля
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Расшифровка векторов
    sb = profile_data.get('sb_level', 4)
    tf = profile_data.get('tf_level', 4)
    ub = profile_data.get('ub_level', 4)
    chv = profile_data.get('chv_level', 4)
    
    # Тип восприятия
    perception = profile_data.get('perception_type', 'не определен')
    perception_desc = get_perception_description(perception)
    
    # Уровень мышления
    thinking = profile_data.get('thinking_level', 5)
    
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
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
        safe_send_message(
            message,
            "❌ Профиль не найден. Сначала пройдите тест.",
            reply_markup=get_back_keyboard("main_menu")
        )
        return
    
    # Генерируем AI-профиль
    ai_text = generate_ai_profile(user_id, profile_data)
    
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
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
        safe_send_message(
            message,
            "❌ Профиль не найден. Сначала пройдите тест.",
            reply_markup=get_back_keyboard("main_menu")
        )
        return
    
    # Строим или получаем конфайнмент-модель
    if "confinement_model" not in profile_data:
        confinement = build_confinement_model(profile_data)
        profile_data["confinement_model"] = confinement.to_dict() if confinement else {}
        save_user_profile(user_id, profile_data)
    
    # Генерируем мысли психолога
    thoughts = generate_psychologist_thought(user_id, profile_data)
    
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
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
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
    
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
        show_profile(message, user_id)
        return
    
    name = context.name if context and context.name else "Пользователь"
    
    # Все данные в сыром виде
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    sb = profile_data.get('sb_level', 4)
    tf = profile_data.get('tf_level', 4)
    ub = profile_data.get('ub_level', 4)
    chv = profile_data.get('chv_level', 4)
    perception = profile_data.get('perception_type', 'не определен')
    thinking = profile_data.get('thinking_level', 5)
    final_level = profile_data.get('final_level', 5)
    
    # Поведенческие уровни
    behavioral = profile_data.get('behavioral_levels', {})
    sb_levels = behavioral.get('СБ', [])
    tf_levels = behavioral.get('ТФ', [])
    ub_levels = behavioral.get('УБ', [])
    chv_levels = behavioral.get('ЧВ', [])
    
    # Дилтс
    dilts_counts = profile_data.get('dilts_counts', {})
    dominant_dilts = profile_data.get('dominant_dilts', 'BEHAVIOR')
    
    # Глубинные паттерны
    deep_patterns = profile_data.get('deep_patterns', {})
    
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
    
    profile_data = get_user_profile(user_id)
    context = get_user_context(user_id)
    
    if not profile_data:
        safe_send_message(message, "❌ Профиль не найден")
        return
    
    name = context.name if context and context.name else "Пользователь"
    
    # Формируем текст для экспорта
    export_text = f"""ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {name}
ДАТА: {time.strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}

{format_profile_display(profile_data, context)}

{'='*50}

ДЕТАЛЬНЫЕ ДАННЫЕ:
{profile_data}

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
    profile1 = get_user_profile(user_id1)
    profile2 = get_user_profile(user_id2)
    context1 = get_user_context(user_id1)
    context2 = get_user_context(user_id2)
    
    if not profile1 or not profile2:
        safe_send_message(message, "❌ Один из профилей не найден")
        return
    
    name1 = context1.name if context1 and context1.name else f"User {user_id1}"
    name2 = context2.name if context2 and context2.name else f"User {user_id2}"
    
    code1 = profile1.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    code2 = profile2.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
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
• {name1}: {profile1.get('dominant_dilts')}
• {name2}: {profile2.get('dominant_dilts')}
"""
    
    safe_send_message(message, text, reply_markup=get_back_keyboard("admin_panel"))


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: call.data == 'show_profile')
def show_profile_callback(call):
    """Показать профиль"""
    show_profile(call.message, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == 'show_ai_profile')
def show_ai_profile_callback(call):
    """Показать AI-профиль"""
    show_ai_profile(call.message, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == 'show_psychologist_thought')
def show_psychologist_thought_callback(call):
    """Показать мысли психолога"""
    show_psychologist_thought(call.message, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == 'show_detailed_profile')
def show_detailed_profile_callback(call):
    """Показать детальный профиль"""
    show_detailed_profile(call.message, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == 'export_profile')
def export_profile_callback(call):
    """Экспортировать профиль"""
    export_profile(call.message, call.from_user.id)


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
    'show_profile_callback',
    'show_ai_profile_callback',
    'show_psychologist_thought_callback'
]
