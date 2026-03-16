#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики сбора контекста (город, возраст, пол) для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import logging
import re
import time
from typing import Dict, Any, Optional, Tuple

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message
from keyboards import (
    get_gender_keyboard, get_age_keyboard, get_skip_keyboard,
    get_confirm_keyboard, get_back_keyboard
)
from models import UserContext

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    from main import user_data
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    from main import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    from main import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_context(user_id: int) -> Optional[UserContext]:
    """Получает контекст пользователя"""
    from main import user_contexts
    return user_contexts.get(user_id)

def get_user_names(user_id: int) -> str:
    """Получает имя пользователя"""
    from main import user_names
    return user_names.get(user_id, "друг")

# ============================================
# НАЧАЛО СБОРА КОНТЕКСТА
# ============================================

def start_context(message: Message):
    """
    Начинает сбор контекста (обязательный)
    """
    user_id = message.chat.id
    
    if user_id not in get_user_context_dict():
        from main import user_contexts
        user_contexts[user_id] = UserContext(user_id)
    
    context = get_user_context(user_id)
    
    # Принудительный сброс (чтобы точно спросило)
    context.city = None
    context.gender = None
    context.age = None
    context.awaiting_context = None
    
    # Получаем первый вопрос
    question, keyboard = context.ask_for_context()
    
    if question:
        safe_send_message(
            message,
            f"📝 <b>Давайте познакомимся</b>\n\n{question}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        # Устанавливаем состояние
        from main import user_states
        user_states[user_id] = "awaiting_context"
    else:
        # Если вопросы не нужны (уже всё есть), показываем завершение
        show_context_complete(message, context)

def get_user_context_dict() -> Dict[int, UserContext]:
    """Возвращает словарь контекстов пользователей"""
    from main import user_contexts
    return user_contexts

# ============================================
# ОБРАБОТЧИКИ CALLBACK'ОВ ДЛЯ КОНТЕКСТА
# ============================================

def set_gender_male(call: CallbackQuery):
    """Устанавливает пол: мужской"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if not context:
        safe_send_message(call.message, "❌ Ошибка контекста", delete_previous=True)
        return
    
    # Устанавливаем пол
    context.gender = "male"
    context.awaiting_context = None
    
    # Получаем следующий вопрос
    question, keyboard = context.ask_for_context()
    
    if question:
        safe_send_message(
            call.message,
            f"📝 <b>Давайте познакомимся</b>\n\n{question}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
    else:
        # Если вопросы закончились, показываем завершение
        show_context_complete(call.message, context)
    
    call.answer()

def set_gender_female(call: CallbackQuery):
    """Устанавливает пол: женский"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if not context:
        safe_send_message(call.message, "❌ Ошибка контекста", delete_previous=True)
        return
    
    # Устанавливаем пол
    context.gender = "female"
    context.awaiting_context = None
    
    # Получаем следующий вопрос
    question, keyboard = context.ask_for_context()
    
    if question:
        safe_send_message(
            call.message,
            f"📝 <b>Давайте познакомимся</b>\n\n{question}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
    else:
        # Если вопросы закончились, показываем завершение
        show_context_complete(call.message, context)
    
    call.answer()

def skip_context(call: CallbackQuery):
    """Пропускает сбор контекста"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if context:
        context.awaiting_context = None
    
    safe_send_message(
        call.message,
        f"⏭ Хорошо, будем общаться без привязки к месту и времени.\n\n"
        "Но помните: с контекстом советы точнее 😉\n"
        "Можете в любой момент рассказать о себе — просто напишите /context",
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Показываем главное меню
    from .modes import show_main_menu
    show_main_menu(call.message, context)
    
    call.answer()

# ============================================
# ОБРАБОТКА ТЕКСТОВЫХ ОТВЕТОВ
# ============================================

def handle_context_message(message: Message) -> bool:
    """
    Обрабатывает ответы на контекстные вопросы
    Возвращает True, если сообщение было обработано как контекстное
    """
    user_id = message.from_user.id
    context = get_user_context(user_id)
    
    if not context or not context.awaiting_context:
        return False
    
    text = message.text.strip()
    
    if context.awaiting_context == "city":
        # Обработка города
        context.city = text
        context.awaiting_context = None
        
        # 👇 ИСПРАВЛЕНО: синхронные вызовы
        context.update_weather()
        context.detect_timezone_from_city()
        
        # Получаем следующий вопрос
        question, keyboard = context.ask_for_context()
        
        if question:
            safe_send_message(
                message,
                f"📝 <b>Давайте познакомимся</b>\n\n{question}",
                reply_markup=keyboard,
                parse_mode='HTML',
                delete_previous=True
            )
        else:
            show_context_complete(message, context)
        
        return True
    
    elif context.awaiting_context == "age":
        # Обработка возраста
        try:
            age = int(text)
            if 1 <= age <= 120:
                context.age = age
                context.awaiting_context = None
                
                # Получаем следующий вопрос
                question, keyboard = context.ask_for_context()
                
                if question:
                    safe_send_message(
                        message,
                        f"📝 <b>Давайте познакомимся</b>\n\n{question}",
                        reply_markup=keyboard,
                        parse_mode='HTML',
                        delete_previous=True
                    )
                else:
                    show_context_complete(message, context)
            else:
                safe_send_message(
                    message,
                    "<b>❌ Возраст должен быть от 1 до 120 лет.</b>\n\n📅 Сколько вам лет? (напишите число)",
                    parse_mode='HTML',
                    delete_previous=True
                )
        except ValueError:
            safe_send_message(
                message,
                "<b>❌ Пожалуйста, введите число.</b>\n\n📅 Сколько вам лет? (напишите число)",
                parse_mode='HTML',
                delete_previous=True
            )
        
        return True
    
    elif context.awaiting_context == "gender":
        # Обработка пола из текста
        gender_lower = text.lower().strip()
        if gender_lower in ['м', 'муж', 'мужчина', 'male', 'парень']:
            context.gender = "male"
        elif gender_lower in ['ж', 'жен', 'женщина', 'female', 'девушка']:
            context.gender = "female"
        else:
            context.gender = "other"
        
        context.awaiting_context = None
        
        # Получаем следующий вопрос
        question, keyboard = context.ask_for_context()
        
        if question:
            safe_send_message(
                message,
                f"📝 <b>Давайте познакомимся</b>\n\n{question}",
                reply_markup=keyboard,
                parse_mode='HTML',
                delete_previous=True
            )
        else:
            show_context_complete(message, context)
        
        return True
    
    return False

# ============================================
# ЗАВЕРШЕНИЕ СБОРА КОНТЕКСТА
# ============================================

def show_context_complete(message: Message, context: UserContext):
    """
    Показывает итоговый экран после сбора контекста
    """
    # 👇 ИСПРАВЛЕНО: синхронный вызов
    context.update_weather()
    
    # Формируем сводку
    summary = f"✅ <b>Отлично! Теперь я знаю о вас:</b>\n\n"
    
    if context.city:
        summary += f"📍 <b>Город:</b> {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        summary += f"👤 <b>Пол:</b> {gender_str}\n"
    if context.age:
        summary += f"📅 <b>Возраст:</b> {context.age}\n"
    if context.weather_cache:
        weather = context.weather_cache
        summary += f"{weather['icon']} <b>Погода:</b> {weather['description']}, {weather['temp']}°C\n"
    
    summary += f"\n🎯 Теперь я буду учитывать это в наших разговорах!\n\n"
    summary += f"🧠 <b>ЧТО ДАЛЬШЕ?</b>\n\n"
    summary += "Чтобы я мог помочь по-настоящему, нужно пройти тест (15 минут).\n"
    summary += "Он определит ваш психологический профиль по 4 векторам и глубинным паттернам.\n\n"
    summary += f"👇 <b>Начинаем?</b>"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro"))
    keyboard.row(InlineKeyboardButton("📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest"))
    
    safe_send_message(
        message,
        summary,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Очищаем состояние
    from main import user_states
    if message.chat.id in user_states:
        del user_states[message.chat.id]

# ============================================
# ПРИНУДИТЕЛЬНЫЙ СБОР КОНТЕКСТА (КОМАНДА)
# ============================================

def cmd_context(message: Message):
    """
    Команда /context - принудительный сбор контекста
    """
    user_id = message.chat.id
    
    if user_id not in get_user_context_dict():
        from main import user_contexts
        user_contexts[user_id] = UserContext(user_id)
    
    context = get_user_context(user_id)
    
    # Сбрасываем контекст
    context.city = None
    context.gender = None
    context.age = None
    context.weather_cache = {}
    context.life_context_complete = False
    
    safe_send_message(
        message,
        "🔄 <b>Давайте обновим ваш контекст</b>",
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Начинаем сбор заново
    start_context(message)

# ============================================
# ПРОВЕРКА ЗАПОЛНЕННОСТИ КОНТЕКСТА
# ============================================

def is_context_complete(user_id: int) -> bool:
    """
    Проверяет, заполнен ли базовый контекст (город, пол, возраст)
    """
    context = get_user_context(user_id)
    if not context:
        return False
    
    return bool(context.city and context.gender and context.age)

def ensure_context(message: Message) -> bool:
    """
    Проверяет наличие контекста и при необходимости запускает его сбор
    Возвращает True, если контекст есть, False если начат сбор
    """
    user_id = message.chat.id
    
    if is_context_complete(user_id):
        return True
    
    # Контекст не заполнен - начинаем сбор
    safe_send_message(
        message,
        "📝 <b>Для точной работы мне нужно немного узнать о вас.</b>",
        parse_mode='HTML',
        delete_previous=True
    )
    
    start_context(message)
    return False

# ============================================
# ПОКАЗ ТЕКУЩЕГО КОНТЕКСТА
# ============================================

def show_current_context(message: Message):
    """
    Показывает текущий контекст пользователя
    """
    user_id = message.chat.id
    context = get_user_context(user_id)
    
    if not context:
        safe_send_message(
            message,
            "❌ Контекст не найден",
            delete_previous=True
        )
        return
    
    if not is_context_complete(user_id):
        text = "📝 <b>Контекст не заполнен</b>\n\n"
        text += "Необходимо указать город, пол и возраст."
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("📝 ЗАПОЛНИТЬ", callback_data="start_context"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu"))
        
        safe_send_message(
            message,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        return
    
    # Формируем текст с текущим контекстом
    text = f"📊 <b>ТВОЙ КОНТЕКСТ</b>\n\n"
    
    if context.name:
        text += f"👤 <b>Имя:</b> {context.name}\n"
    if context.city:
        text += f"📍 <b>Город:</b> {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        text += f"👤 <b>Пол:</b> {gender_str}\n"
    if context.age:
        text += f"📅 <b>Возраст:</b> {context.age}\n"
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} <b>Погода:</b> {weather['description']}, {weather['temp']}°C\n"
    
    # Жизненный контекст, если есть
    if context.life_context_complete:
        text += f"\n📋 <b>ЖИЗНЕННЫЙ КОНТЕКСТ:</b>\n"
        if context.family_status:
            text += f"• Семья: {context.family_status}\n"
        if context.has_children:
            text += f"• Дети: {context.children_ages}\n"
        if context.job_title:
            text += f"• Работа: {context.job_title}\n"
        if context.energy_level:
            text += f"• Энергия: {context.energy_level}/10\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🔄 ОБНОВИТЬ", callback_data="start_context"),
        InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu")
    )
    
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

# ============================================
# ОБРАБОТКА ЖИЗНЕННОГО КОНТЕКСТА
# ============================================

def save_life_context(user_id: int, answers: dict):
    """
    Сохраняет жизненный контекст из ответов пользователя
    """
    context = get_user_context(user_id)
    if not context:
        return
    
    context.family_status = answers.get('family_status')
    context.has_children = answers.get('has_children')
    context.children_ages = answers.get('children_ages')
    context.work_schedule = answers.get('work_schedule')
    context.job_title = answers.get('job_title')
    context.commute_time = answers.get('commute_time')
    context.housing_type = answers.get('housing_type')
    context.has_private_space = answers.get('has_private_space')
    context.has_car = answers.get('has_car')
    context.support_people = answers.get('support_people')
    context.resistance_people = answers.get('resistance_people')
    context.energy_level = answers.get('energy_level')
    context.life_context_complete = True

def parse_life_context_from_text(text: str) -> dict:
    """
    Парсит ответы на вопросы о жизненном контексте из текста
    """
    lines = text.strip().split('\n')
    answers = {}
    
    for i, line in enumerate(lines):
        # Убираем нумерацию и лишние пробелы
        clean = re.sub(r'^[\d️⃣🔟\s]*', '', line.strip())
        if not clean:
            continue
        
        # Семейное положение
        if i == 0:
            answers['family_status'] = clean
        
        # Дети
        elif i == 1:
            answers['has_children'] = 'да' in clean.lower() or 'есть' in clean.lower()
            answers['children_ages'] = clean
        
        # Работа и график
        elif i == 2:
            # Пробуем извлечь профессию и график
            answers['job_title'] = clean
            if '5/2' in clean:
                answers['work_schedule'] = '5/2'
            elif '2/2' in clean:
                answers['work_schedule'] = '2/2'
            elif 'свободный' in clean.lower() or 'фриланс' in clean.lower():
                answers['work_schedule'] = 'свободный'
            else:
                answers['work_schedule'] = clean
        
        # Время на дорогу
        elif i == 3:
            minutes = re.findall(r'\d+', clean)
            answers['commute_time'] = int(minutes[0]) if minutes else None
        
        # Жильё
        elif i == 4:
            answers['housing_type'] = clean
        
        # Отдельное пространство
        elif i == 5:
            answers['has_private_space'] = 'да' in clean.lower() or 'есть' in clean.lower()
        
        # Машина
        elif i == 6:
            answers['has_car'] = 'да' in clean.lower() or 'есть' in clean.lower()
        
        # Поддержка
        elif i == 7:
            answers['support_people'] = clean
        
        # Сопротивление
        elif i == 8:
            answers['resistance_people'] = clean if 'нет' not in clean.lower() else None
        
        # Энергия
        elif i == 9:
            energy = re.findall(r'\d+', clean)
            answers['energy_level'] = int(energy[0]) if energy else 5
    
    return answers


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'start_context',
    'set_gender_male',
    'set_gender_female',
    'skip_context',
    'handle_context_message',
    'show_context_complete',
    'cmd_context',
    'is_context_complete',
    'ensure_context',
    'show_current_context',
    'save_life_context',
    'parse_life_context_from_text'
]
