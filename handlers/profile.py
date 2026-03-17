#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики профиля пользователя для MAX
"""

import logging
import asyncio
import time
import traceback
from typing import Optional, List

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot_instance import bot
from message_utils import safe_send_message, safe_delete_message, send_with_status_cleanup
from state import user_data, user_contexts, get_state, set_state
from services import generate_ai_profile, generate_psychologist_thought
from profiles import VECTORS, DILTS_LEVELS, LEVEL_PROFILES
from formatters import (
    bold, format_profile_text, format_psychologist_text,
    clean_text_for_safe_display
)

logger = logging.getLogger(__name__)

# Флаг для предотвращения одновременной генерации для одного пользователя
_profile_generation_in_progress = {}

# ============================================
# ФУНКЦИЯ ДЛЯ РАЗБИВКИ ДЛИННЫХ СООБЩЕНИЙ
# ============================================

def split_long_message(text: str, max_length: int = 3500) -> List[str]:
    """
    Разбивает длинное сообщение на части по границам предложений
    """
    if not text or len(text) <= max_length:
        return [text]
    
    parts = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_length:
            parts.append(remaining)
            break
        
        # Ищем место для разрыва
        split_point = -1
        
        # 1. Пробуем найти конец предложения
        for separator in ['. ', '! ', '? ', '.\n', '!\n', '?\n', '\n\n']:
            pos = remaining.rfind(separator, 0, max_length)
            if pos > split_point:
                split_point = pos + len(separator)
        
        # 2. Если нет конца предложения, ищем пробел
        if split_point == -1 or split_point <= max_length // 2:
            split_point = remaining.rfind(' ', 0, max_length)
        
        # 3. Если нет пробела, режем жестко
        if split_point == -1:
            split_point = max_length
        
        # Добавляем часть
        parts.append(remaining[:split_point].strip())
        remaining = remaining[split_point:].strip()
    
    logger.info(f"✂️ Сообщение разбито на {len(parts)} частей (было {len(text)} символов)")
    return parts

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def safe_get_profile_info(vector: str, level_num: int, key: str, default: str = "Информация уточняется") -> str:
    """Безопасно получает информацию из профиля"""
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

def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", 
                                thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
    lines = []
    
    if scores:
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector, score = min_vector
        lvl = int(score)
        
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

# ============================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ АСИНХРОННЫХ ВЫЗОВОВ
# ============================================

async def run_async_function(coro, timeout: Optional[float] = None):
    """Безопасно запускает асинхронную корутину в текущем цикле событий"""
    try:
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        else:
            return await coro
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Таймаут при выполнении асинхронной функции")
        return None

# ============================================
# АСИНХРОННЫЕ ВЕРСИИ ФУНКЦИЙ
# ============================================

async def show_ai_profile_async(message: Message, user_id: int):
    """Асинхронная версия показа профиля, сгенерированного ИИ"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую данные и генерирую ваш психологический портрет...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    try:
        ai_profile = data.get("ai_generated_profile")
        
        if not ai_profile:
            try:
                ai_profile = await run_async_function(generate_ai_profile(user_id, data), timeout=60.0)
            except Exception as e:
                logger.error(f"❌ Ошибка при вызове generate_ai_profile: {e}")
                ai_profile = None
            
            if ai_profile:
                user_data[user_id]["ai_generated_profile"] = ai_profile
        
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        if ai_profile:
            if len(ai_profile) > 3500:
                logger.info(f"📏 AI профиль слишком длинный: {len(ai_profile)} > 3500. Разбиваем на части.")
                profile_parts = split_long_message(ai_profile)
                logger.info(f"✂️ Разбито на {len(profile_parts)} частей")
            else:
                profile_parts = [ai_profile]
            
            # Форматируем все части
            formatted_parts = []
            for i, part in enumerate(profile_parts):
                formatted_part = format_profile_text(part)
                
                if i == 0 and not formatted_part.startswith("🧠"):
                    formatted_part = f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}\n\n{formatted_part}"
                
                if i == 0 and user_name and "обращаюсь" not in formatted_part[:50].lower():
                    formatted_part = f"{user_name}, " + formatted_part[0].lower() + formatted_part[1:]
                
                # Проверяем длину отформатированной части
                if len(formatted_part) > 3500:
                    logger.warning(f"⚠️ Часть {i+1} слишком длинная: {len(formatted_part)}. Разбиваем ещё раз.")
                    sub_parts = split_long_message(formatted_part)
                    formatted_parts.extend(sub_parts)
                else:
                    formatted_parts.append(formatted_part)
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
            keyboard.row(
                InlineKeyboardButton("🎤 ЗАДАТЬ ВОПРОС", callback_data="ask_question"),
                InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")
            )
            keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
            
            # Отправляем все части
            for i, part in enumerate(formatted_parts):
                try:
                    if i == len(formatted_parts) - 1:
                        text = f"""
{part}

👇 {bold('Что дальше?')}
"""
                        result = safe_send_message(
                            message if i == 0 else None,
                            text,
                            reply_markup=keyboard,
                            parse_mode='HTML',
                            delete_previous=(i == 0)
                        )
                        if result:
                            logger.info(f"✅ Отправлена последняя часть {i+1} с кнопками")
                    else:
                        part_text = f"{part}\n\n<code>✉️ Часть {i+1}/{len(formatted_parts)}</code>"
                        
                        result = safe_send_message(
                            message if i == 0 else None,
                            part_text,
                            parse_mode='HTML',
                            delete_previous=(i == 0)
                        )
                        if result:
                            logger.info(f"✅ Отправлена часть {i+1}/{len(formatted_parts)}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке части {i+1}: {e}")
                    continue
            
            logger.info(f"🎉 Все {len(formatted_parts)} частей профиля успешно отправлены")
            return
            
        else:
            scores = {}
            for k in VECTORS:
                levels = data.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            
            perception_type = data.get("perception_type", "не определен")
            thinking_level = data.get("thinking_level", 5)
            dilts_counts = data.get("dilts_counts", {})
            dominant_dilts = determine_dominant_dilts(dilts_counts)
            
            profile_text = get_human_readable_profile(
                scores, model=None,
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
        traceback.print_exc()
        
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
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(
        InlineKeyboardButton("🎤 ЗАДАТЬ ВОПРОС", callback_data="ask_question"),
        InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


async def show_psychologist_thought_async(message: Message, user_id: int):
    """Асинхронная версия показа мыслей психолога"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую ваш профиль и формирую мысли психолога...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    try:
        thought = None
        try:
            thought = await run_async_function(generate_psychologist_thought(user_id, data), timeout=60.0)
        except Exception as e:
            if str(e):
                logger.error(f"❌ Ошибка при вызове generate_psychologist_thought: {e}")
            else:
                logger.info("⚠️ Пустая ошибка при генерации мысли психолога")
            thought = None
        
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        if thought:
            if len(thought) > 3500:
                logger.info(f"📏 Мысли психолога слишком длинные: {len(thought)} > 3500. Разбиваем на части.")
                thought_parts = split_long_message(thought)
                logger.info(f"✂️ Разбито на {len(thought_parts)} частей")
            else:
                thought_parts = [thought]
            
            # Форматируем все части
            formatted_parts = []
            for part in thought_parts:
                formatted_part = format_psychologist_text(part, user_name)
                if len(formatted_part) > 3500:
                    logger.warning(f"⚠️ Часть мысли слишком длинная: {len(formatted_part)}. Разбиваем ещё раз.")
                    sub_parts = split_long_message(formatted_part)
                    formatted_parts.extend(sub_parts)
                else:
                    formatted_parts.append(formatted_part)
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("📊 К ПРОФИЛЮ", callback_data="show_profile"))
            keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
            keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
            
            for i, part in enumerate(formatted_parts):
                try:
                    if i == len(formatted_parts) - 1:
                        text = f"""
🧠 {bold('МЫСЛИ ПСИХОЛОГА')}

{part}

👇 {bold('Что дальше?')}
"""
                        result = safe_send_message(
                            message if i == 0 else None,
                            text,
                            reply_markup=keyboard,
                            parse_mode='HTML',
                            delete_previous=(i == 0)
                        )
                        if result:
                            logger.info(f"✅ Отправлена последняя часть мысли {i+1} с кнопками")
                    else:
                        part_text = f"""
🧠 {bold('МЫСЛИ ПСИХОЛОГА')} <code>(часть {i+1}/{len(formatted_parts)})</code>

{part}

<code>✉️ Продолжение следует...</code>
"""
                        result = safe_send_message(
                            message if i == 0 else None,
                            part_text,
                            parse_mode='HTML',
                            delete_previous=(i == 0)
                        )
                        if result:
                            logger.info(f"✅ Отправлена часть мысли {i+1}/{len(formatted_parts)}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке части мысли {i+1}: {e}")
                    continue
            
            logger.info(f"🎉 Все {len(formatted_parts)} частей мысли успешно отправлены")
            return
            
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
        traceback.print_exc()
        
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
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📊 К ПРОФИЛЮ", callback_data="show_profile"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


async def show_final_profile_async(message: Message, user_id: int):
    """Асинхронная версия показа финального профиля после всех этапов"""
    logger.info(f"🔍 show_final_profile_async ВЫЗВАНО для пользователя {user_id}")
    
    if user_id in _profile_generation_in_progress and _profile_generation_in_progress[user_id]:
        logger.info(f"⏳ Генерация профиля уже выполняется для пользователя {user_id}")
        safe_send_message(
            message,
            "⏳ Ваш профиль уже генерируется, пожалуйста, подождите...",
            delete_previous=True
        )
        return
    
    data = user_data.get(user_id, {})
    
    if data.get("ai_generated_profile"):
        logger.info(f"✅ Найден сохраненный AI профиль для пользователя {user_id}")
        await show_ai_profile_async(message, user_id)
        return
    
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую данные...\n\n"
        "Собираю воедино результаты 5 этапов тестирования.\n"
        "Это займёт около 20-30 секунд.\n\n"
        "Формирую ваш точный психологический портрет...",
        delete_previous=True
    )
    
    _profile_generation_in_progress[user_id] = True
    start_time = time.time()
    logger.info(f"⏱️ Начало генерации профиля ИИ в {start_time}")
    
    ai_profile = None
    try:
        ai_profile = await run_async_function(generate_ai_profile(user_id, data), timeout=60.0)
        elapsed = time.time() - start_time
        logger.info(f"⏱️ Генерация профиля ИИ завершена, прошло {elapsed:.1f} сек")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Ошибка при генерации AI профиля: {e}")
        logger.error(traceback.format_exc())
        logger.info(f"⏱️ Генерация завершилась ошибкой через {elapsed:.1f} сек")
        ai_profile = None
    finally:
        _profile_generation_in_progress[user_id] = False
        logger.info(f"🔓 Флаг генерации снят для пользователя {user_id}")
    
    if ai_profile:
        logger.info(f"✅ AI профиль успешно сгенерирован, длина: {len(ai_profile)} символов")
        user_data[user_id]["ai_generated_profile"] = ai_profile
        
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        await show_ai_profile_async(message, user_id)
        return
    
    logger.warning(f"⚠️ Не удалось сгенерировать AI профиль, показываем стандартный")
    show_old_final_profile(message, user_id, status_msg)


# ============================================
# СИНХРОННЫЕ ОБЕРТКИ
# ============================================

def show_profile(message: Message, user_id: int):
    """Синхронная обертка для показа профиля"""
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
        scores, model=None,
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
    """Синхронная обертка для показа AI профиля"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(show_ai_profile_async(message, user_id))
    except RuntimeError:
        asyncio.run(show_ai_profile_async(message, user_id))


def show_psychologist_thought(message: Message, user_id: int):
    """Синхронная обертка для показа мыслей психолога"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(show_psychologist_thought_async(message, user_id))
    except RuntimeError:
        asyncio.run(show_psychologist_thought_async(message, user_id))


def show_final_profile(message: Message, user_id: int):
    """Синхронная обертка для показа финального профиля"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(show_final_profile_async(message, user_id))
    except RuntimeError:
        asyncio.run(show_final_profile_async(message, user_id))


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
        scores, model=None,
        perception_type=perception_type,
        thinking_level=thinking_level,
        dominant_dilts=dominant_dilts
    )
    
    text = f"{profile_text}\n\n👇 {bold('Что дальше?')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
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
