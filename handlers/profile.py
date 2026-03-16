#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики профиля пользователя для MAX
"""

import logging
import asyncio
from typing import Optional

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot_instance import bot
from message_utils import safe_send_message, safe_delete_message, send_with_status_cleanup
from state import user_data, user_contexts, get_state, set_state
from services import generate_ai_profile, generate_psychologist_thought
from profiles import VECTORS, DILTS_LEVELS
from formatters import (
    bold, format_profile_text, format_psychologist_text,
    clean_text_for_safe_display
)

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", 
                                thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
    lines = []
    
    if scores:
        # Находим вектор с минимальным значением (самая проблемная зона)
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector, score = min_vector
        lvl = int(score)
        
        # Безопасно получаем информацию из профиля
        from profiles import LEVEL_PROFILES
        from services import safe_get_profile_info
        
        quote = safe_get_profile_info(vector, lvl, 'quote', 'Пока не определено')
        pain_origin = safe_get_profile_info(vector, lvl, 'pain_origin', 'Из вашего опыта')
        costs = safe_get_profile_info(vector, lvl, 'pain_costs', ["Энергией", "Временем", "Возможностями"])
    else:
        vector = "СБ"
        quote = "Пока не определено"
        pain_origin = "Из вашего опыта"
        costs = ["Энергией", "Временем", "Возможностями"]
    
    lines.append(f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}")
    lines.append("")
    lines.append(f"🔍 {bold('Тип восприятия:')} {perception_type}")
    lines.append(f"🧠 {bold('Уровень мышления:')} {thinking_level}/9")
    lines.append("")
    
    lines.append(f"🔑 {bold('КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА')}")
    lines.append(quote)
    lines.append("")
    
    lines.append(f"💪 {bold('СИЛЬНЫЕ СТОРОНЫ')}")
    lines.append("• Высокоразвитые социальные навыки и умение выстраивать надежные, доверительные отношения.")
    lines.append("• Системное мышление, позволяющее видеть связи, управлять сложными процессами и достигать целей.")
    lines.append("• Исключительная устойчивость к стрессу и угрозам, способность действовать хладнокровно в кризисах.")
    lines.append("• Прагматизм и высокая компетентность в вопросах финансов, карьеры и социального взаимодействия.")
    lines.append("")
    
    lines.append(f"🎯 {bold('ЗОНЫ РОСТА')}")
    lines.append(f"• {pain_origin}")
    if isinstance(costs, list):
        for cost in costs[:3]:
            lines.append(f"• {cost}")
    lines.append("")
    
    lines.append(f"⚠️ {bold('ГЛАВНАЯ ЛОВУШКА')}")
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "⚡ Поведение")
    lines.append(f"• {dilts_desc}")
    
    return "\n".join(lines)

def safe_get_profile_info(vector: str, level_num: int, key: str, default: str = "Информация уточняется") -> str:
    """Безопасно получает информацию из профиля"""
    from profiles import LEVEL_PROFILES
    try:
        profile = LEVEL_PROFILES.get(vector, {}).get(level_num, {})
        if isinstance(profile, dict):
            if key == 'quote':
                return profile.get('quote') or profile.get('description') or profile.get('block1') or default
            elif key == 'pain_origin':
                return profile.get('pain_origin') or profile.get('origin') or profile.get('block2') or default
            elif key == 'pain_costs':
                costs = profile.get('pain_costs') or profile.get('costs') or []
                if costs:
                    return costs
                return ["Энергией", "Временем", "Возможностями"]
        else:
            if key == 'quote':
                return str(profile)
            elif key == 'pain_origin':
                return "Из вашего опыта"
            elif key == 'pain_costs':
                return ["Энергией", "Временем", "Возможностями"]
    except Exception as e:
        logger.error(f"Ошибка при получении информации из профиля: {e}")
    
    return default

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def show_profile(message: Message, user_id: int):
    """Показывает профиль пользователя"""
    data = user_data.get(user_id, {})
    
    if not data:
        safe_send_message(
            message,
            "📊 У вас пока нет профиля. Пройдите тест, чтобы узнать себя лучше.",
            delete_previous=True
        )
        return
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_text = get_human_readable_profile(
        scores, 
        model=None,
        perception_type=perception_type,
        thinking_level=thinking_level,
        dominant_dilts=dominant_dilts
    )
    
    text = f"{profile_text}\n\n👇 {bold('Что дальше?')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


def show_ai_profile(message: Message, user_id: int):
    """Показывает профиль, сгенерированный ИИ"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую данные и генерирую ваш психологический портрет...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # ИСПРАВЛЕНИЕ: Используем asyncio для вызова асинхронной функции
    try:
        # Пытаемся получить существующий AI профиль или генерируем новый
        ai_profile = data.get("ai_generated_profile")
        
        if not ai_profile:
            # Создаем и запускаем event loop для асинхронного вызова
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ai_profile = loop.run_until_complete(generate_ai_profile(user_id, data))
            loop.close()
            
            # Сохраняем сгенерированный профиль
            if ai_profile:
                user_data[user_id]["ai_generated_profile"] = ai_profile
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        if ai_profile:
            # Форматируем текст
            formatted_profile = format_profile_text(ai_profile)
            
            # Добавляем заголовок, если его нет
            if not formatted_profile.startswith("🧠"):
                formatted_profile = f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}\n\n{formatted_profile}"
            
            # Форматируем с учетом имени пользователя
            if user_name and "обращаюсь" not in formatted_profile[:50].lower():
                # Добавляем обращение в начало
                formatted_profile = f"{user_name}, " + formatted_profile[0].lower() + formatted_profile[1:]
            
            text = f"""
{formatted_profile}

👇 {bold('Что дальше?')}
"""
        else:
            # Если не удалось сгенерировать, показываем обычный профиль
            scores = {}
            for k in VECTORS:
                levels = data.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            
            perception_type = data.get("perception_type", "не определен")
            thinking_level = data.get("thinking_level", 5)
            dilts_counts = data.get("dilts_counts", {})
            dominant_dilts = determine_dominant_dilts(dilts_counts)
            
            profile_text = get_human_readable_profile(
                scores, 
                model=None,
                perception_type=perception_type,
                thinking_level=thinking_level,
                dominant_dilts=dominant_dilts
            )
            
            text = f"""
⚠️ <b>Не удалось сгенерировать расширенный профиль.</b> Показываю стандартный:

{profile_text}

👇 {bold('Что дальше?')}
"""
        
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации AI профиля: {e}")
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        text = f"""
⚠️ <b>Ошибка генерации профиля</b>

Не удалось создать расширенный психологический портрет.
Пожалуйста, попробуйте позже или используйте стандартный профиль.

👇 {bold('Что дальше?')}
"""
    
    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(
        InlineKeyboardButton("🎤 ЗАДАТЬ ВОПРОС", callback_data="ask_question"),
        InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    # Отправляем финальное сообщение
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


def show_psychologist_thought(message: Message, user_id: int):
    """Показывает мысли психолога о пользователе"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую ваш профиль и формирую мысли психолога...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # ИСПРАВЛЕНИЕ: Используем asyncio для вызова асинхронной функции
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        thought = loop.run_until_complete(generate_psychologist_thought(user_id, data))
        loop.close()
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        if thought:
            # Форматируем текст
            formatted_thought = format_psychologist_text(thought, user_name)
            
            text = f"""
🧠 {bold('МЫСЛИ ПСИХОЛОГА')}

{formatted_thought}

👇 {bold('Что дальше?')}
"""
        else:
            text = f"""
🧠 {bold('МЫСЛИ ПСИХОЛОГА')}

Анализируя ваш профиль, я вижу интересную динамику...

<b>Ключевой паттерн:</b> Вы склонны анализировать ситуации глубоко, но иногда это мешает быстрым решениям.

<b>Петля:</b> Анализ → Сомнения → Ещё больший анализ.

<b>Точка входа:</b> Попробуйте в следующий раз, когда будете анализировать, задать себе вопрос: "Что я чувствую прямо сейчас?"

<b>Прогноз:</b> Если продолжите в том же духе, рискуете упустить несколько хороших возможностей.

👇 {bold('Что дальше?')}
"""
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации мысли психолога: {e}")
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        text = f"""
⚠️ <b>Ошибка генерации</b>

Не удалось сформировать мысли психолога.
Пожалуйста, попробуйте позже.

👇 {bold('Что дальше?')}
"""
    
    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📊 К ПРОФИЛЮ", callback_data="show_profile"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    # Отправляем финальное сообщение
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


def show_final_profile(message: Message, user_id: int):
    """Показывает финальный профиль после всех этапов"""
    data = user_data.get(user_id, {})
    
    if data.get("ai_generated_profile"):
        show_ai_profile(message, user_id)
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую данные...\n\n"
        "Собираю воедино результаты 5 этапов тестирования.\n"
        "Это займёт около 20-30 секунд.\n\n"
        "Формирую ваш точный психологический портрет...",
        delete_previous=True
    )
    
    # ИСПРАВЛЕНИЕ: Используем asyncio для вызова асинхронной функции
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ai_profile = loop.run_until_complete(generate_ai_profile(user_id, data))
        loop.close()
        
        if ai_profile:
            user_data[user_id]["ai_generated_profile"] = ai_profile
            # Удаляем статусное сообщение и показываем AI профиль
            if status_msg:
                try:
                    safe_delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
            show_ai_profile(message, user_id)
            return
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации AI профиля в show_final_profile: {e}")
    
    # Если не удалось сгенерировать AI профиль, показываем старый
    show_old_final_profile(message, user_id, status_msg)


def show_old_final_profile(message: Message, user_id: int, status_msg: Optional[Message] = None):
    """Старая версия финального профиля (резерв)"""
    data = user_data.get(user_id, {})
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_text = get_human_readable_profile(
        scores, 
        model=None,
        perception_type=perception_type,
        thinking_level=thinking_level,
        dominant_dilts=dominant_dilts
    )
    
    text = f"{profile_text}\n\n👇 {bold('Что дальше?')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    # Удаляем статусное сообщение
    if status_msg:
        try:
            safe_delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        message,
        text,
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
    'show_old_final_profile'
]
