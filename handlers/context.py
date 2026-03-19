#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики сбора контекста (город, возраст, пол) для MAX
Восстановлено из оригинального bot3.py и адаптировано
ДОБАВЛЕНО: Сохранение контекста в PostgreSQL
ИСПРАВЛЕНО: Устранен циклический импорт с main.py
ИСПРАВЛЕНО: Асинхронные вызовы обернуты в threading
ИСПРАВЛЕНО: Город обрабатывается в отдельном потоке без зависаний
"""

import logging
import re
import time
import threading
import asyncio
from typing import Dict, Any, Optional, Tuple
from concurrent.futures import Future

from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import (
    get_gender_keyboard, get_age_keyboard, get_skip_keyboard,
    get_confirm_keyboard, get_back_keyboard
)
from models import UserContext

# ИСПРАВЛЕННЫЕ ИМПОРТЫ - используем state.py
from state import (
    user_data, user_names, user_contexts, user_states, user_state_data,
    get_user_context, get_user_context_dict,
    get_state, set_state, get_state_data, update_state_data, clear_state, TestStates
)

# ✅ ИСПРАВЛЕНО: Импортируем базу данных из отдельного модуля, а не из main
from db_instance import db, save_user_to_db

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ АСИНХРОННЫХ ВЫЗОВОВ
# ============================================

def run_async_task(coro_func, *args, **kwargs):
    """
    Запускает асинхронную корутину в отдельном потоке с собственным циклом событий
    """
    def _wrapper():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            coro = coro_func(*args, **kwargs)
            loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"❌ Ошибка в асинхронной задаче: {e}")
        finally:
            loop.close()
    
    threading.Thread(target=_wrapper, daemon=True).start()

def run_async_task_with_result(coro_func, *args, **kwargs):
    """
    Запускает асинхронную корутину и возвращает Future для получения результата
    """
    future = Future()
    
    def _wrapper():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            coro = coro_func(*args, **kwargs)
            result = loop.run_until_complete(coro)
            future.set_result(result)
        except Exception as e:
            logger.error(f"❌ Ошибка в асинхронной задаче: {e}")
            future.set_exception(e)
        finally:
            loop.close()
    
    threading.Thread(target=_wrapper, daemon=True).start()
    return future

# ============================================
# ГЛОБАЛЬНАЯ БЛОКИРОВКА ДЛЯ ПРЕДОТВРАЩЕНИЯ ДВОЙНЫХ ВЫЗОВОВ
# ============================================

_context_lock = threading.Lock()
_executing_context = False

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

# get_user_context уже есть в state.py, но переопределим для единообразия
def get_user_context(user_id: int) -> Optional[UserContext]:
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_names(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "друг")

def get_user_context_dict() -> Dict[int, UserContext]:
    """Возвращает словарь контекстов пользователей"""
    return user_contexts

async def save_context_to_db(user_id: int):
    """Сохраняет контекст пользователя в БД"""
    context = get_user_context(user_id)
    if context:
        await db.save_user_context(user_id, context)
        logger.debug(f"💾 Контекст пользователя {user_id} сохранен в БД")

# ============================================
# НАЧАЛО СБОРА КОНТЕКСТА
# ============================================

def start_context(message: Message):
    """
    Начинает сбор контекста (обязательный)
    """
    global _executing_context
    
    user_id = message.chat.id
    
    # ========== ГЛОБАЛЬНАЯ БЛОКИРОВКА ==========
    if not _context_lock.acquire(blocking=False):
        logger.info(f"⚠️ start_context уже выполняется (блокировка), пропускаем для user {user_id}")
        return
    
    try:
        if _executing_context:
            logger.info(f"⚠️ start_context уже выполняется (флаг), пропускаем для user {user_id}")
            return
        
        _executing_context = True
    finally:
        _context_lock.release()
    
    try:
        from state import user_states, TestStates
        
        # Проверяем состояние
        current_state = user_states.get(user_id)
        if current_state == TestStates.awaiting_context:
            logger.info(f"⚠️ Сбор контекста уже начат для user {user_id}, пропускаем")
            return
        
        logger.info(f"🚀 start_context вызван для user {user_id}")
        
        if user_id not in user_contexts:
            logger.info(f"📝 Создаем новый контекст для user {user_id}")
            user_contexts[user_id] = UserContext(user_id)
        
        context = user_contexts[user_id]
        
        # Принудительный сброс (чтобы точно спросило)
        context.city = None
        context.gender = None
        context.age = None
        context.awaiting_context = None
        
        # Получаем первый вопрос
        logger.info(f"❓ Получаем первый вопрос от ask_for_context()")
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Первый вопрос: '{question}', клавиатура: {keyboard is not None}")
        
        if question:
            logger.info(f"📤 Отправляем вопрос о городе...")
            
            # Удаляем предыдущее сообщение
            try:
                safe_delete_message(message.chat.id, message.message_id)
            except:
                pass
            
            safe_send_message(
                message,
                f"📝 **Давайте познакомимся**\n\n{question}",
                reply_markup=keyboard,
                parse_mode=None,
                delete_previous=True
            )
            logger.info(f"✅ Вопрос о городе отправлен, устанавливаем состояние awaiting_context")
            
            # Устанавливаем состояние
            set_state(user_id, TestStates.awaiting_context)
            logger.info(f"📊 Состояние пользователя {user_id} установлено на {TestStates.awaiting_context}")
        else:
            logger.info(f"⚠️ Вопросов нет, показываем завершение")
            # Если вопросы не нужны (уже всё есть), показываем завершение
            show_context_complete(message, context)
            
    finally:
        # Сбрасываем флаг
        _executing_context = False

# ============================================
# ОБРАБОТЧИКИ CALLBACK'ОВ ДЛЯ КОНТЕКСТА
# ============================================

def handle_context_callback(call: CallbackQuery):
    """
    Единый обработчик для всех callback'ов контекста (пол, возраст, пропуск)
    """
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"🔔 handle_context_callback: {data} для пользователя {user_id}")
    
    # Получаем контекст
    context = get_user_context(user_id)
    
    if not context:
        logger.warning(f"❌ Контекст не найден для user {user_id}")
        safe_send_message(call.message, "❌ Ошибка контекста", delete_previous=True)
        call.answer()
        return
    
    # Обработка выбора пола
    if data == "set_gender_male":
        logger.info(f"👨 Устанавливаем пол: мужской")
        context.gender = "male"
        context.awaiting_context = None
        
        # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
        run_async_task(save_context_to_db, user_id)
        
        # Получаем следующий вопрос
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
        
        if question:
            safe_send_message(
                call.message,
                f"📝 **Давайте познакомимся**\n\n{question}",
                reply_markup=keyboard,
                parse_mode=None,
                delete_previous=True
            )
        else:
            show_context_complete(call.message, context)
        
        call.answer()
        return
    
    elif data == "set_gender_female":
        logger.info(f"👩 Устанавливаем пол: женский")
        context.gender = "female"
        context.awaiting_context = None
        
        # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
        run_async_task(save_context_to_db, user_id)
        
        # Получаем следующий вопрос
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
        
        if question:
            safe_send_message(
                call.message,
                f"📝 **Давайте познакомимся**\n\n{question}",
                reply_markup=keyboard,
                parse_mode=None,
                delete_previous=True
            )
        else:
            show_context_complete(call.message, context)
        
        call.answer()
        return
    
    elif data == "set_gender_other":
        logger.info(f"🧑 Устанавливаем пол: другое")
        context.gender = "other"
        context.awaiting_context = None
        
        # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
        run_async_task(save_context_to_db, user_id)
        
        # Получаем следующий вопрос
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
        
        if question:
            safe_send_message(
                call.message,
                f"📝 **Давайте познакомимся**\n\n{question}",
                reply_markup=keyboard,
                parse_mode=None,
                delete_previous=True
            )
        else:
            show_context_complete(call.message, context)
        
        call.answer()
        return
    
    # Обработка пропуска контекста
    elif data == "skip_context":
        logger.info(f"⏭️ Пропускаем сбор контекста")
        context.awaiting_context = None
        
        # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
        run_async_task(save_context_to_db, user_id)
        
        safe_send_message(
            call.message,
            f"⏭ Хорошо, будем общаться без привязки к месту и времени.\n\n"
            "Но помните: с контекстом советы точнее 😉\n"
            "Можете в любой момент рассказать о себе — просто напишите /context",
            parse_mode=None,
            delete_previous=True
        )
        
        # Показываем главное меню
        # ✅ ИСПРАВЛЕНО: Импортируем здесь, чтобы избежать циклического импорта
        from handlers.modes import show_main_menu
        show_main_menu(call.message, context)
        
        call.answer()
        return
    
    # Неизвестный callback
    else:
        logger.warning(f"⚠️ Неизвестный callback в handle_context_callback: {data}")
        call.answer()

def set_gender_male(call: CallbackQuery):
    """Устанавливает пол: мужской (для обратной совместимости)"""
    handle_context_callback(call)

def set_gender_female(call: CallbackQuery):
    """Устанавливает пол: женский (для обратной совместимости)"""
    handle_context_callback(call)

def skip_context(call: CallbackQuery):
    """Пропускает сбор контекста (для обратной совместимости)"""
    handle_context_callback(call)

# ============================================
# ОБРАБОТКА ТЕКСТОВЫХ ОТВЕТОВ - ИСПРАВЛЕНО!
# ============================================

def handle_context_message(message: Message) -> bool:
    """
    Обрабатывает ответы на контекстные вопросы
    Возвращает True, если сообщение было обработано как контекстное
    """
    user_id = message.from_user.id
    logger.info(f"📥 handle_context_message вызван для user {user_id}, текст: {message.text}")
    
    # Получаем текущее состояние пользователя
    current_state = get_state(user_id)
    logger.info(f"📊 Текущее состояние из get_state: {current_state}")
    
    context = get_user_context(user_id)
    
    if not context:
        logger.warning(f"❌ Контекст не найден для user {user_id}")
        return False
    
    logger.info(f"📊 context.awaiting_context = {context.awaiting_context}")
    
    if not context.awaiting_context:
        logger.info(f"⏭️ Не ожидается контекст (context.awaiting_context is None), выходим")
        return False
    
    text = message.text.strip()
    logger.info(f"📝 Обрабатываем текст: '{text}' для поля {context.awaiting_context}")
    
    if context.awaiting_context == "city":
        # ========== ИСПРАВЛЕННАЯ ОБРАБОТКА ГОРОДА ==========
        logger.info(f"🏙️ Сохраняем город: {text}")
        context.city = text
        context.awaiting_context = None
        
        # Отправляем сообщение о загрузке
        loading_msg = safe_send_message(
            message,
            "🔄 Получаю данные о погоде и часовом поясе...\nЭто займёт несколько секунд.",
            delete_previous=True
        )
        
        # Запускаем обновление погоды и часового пояса в отдельном потоке
        def update_weather_and_continue():
            """Обновляет погоду и продолжает диалог в отдельном потоке"""
            try:
                logger.info(f"🌤️ Обновляем погоду для города {text}...")
                # Синхронный вызов update_weather (но в отдельном потоке)
                context.update_weather()
                logger.info(f"✅ Погода обновлена")
                
                # Определяем часовой пояс
                logger.info(f"🌍 Определяем часовой пояс для города {text}...")
                context.detect_timezone_from_city()
                logger.info(f"✅ Часовой пояс определен")
                
                # Сохраняем в БД асинхронно
                run_async_task(save_context_to_db, user_id)
                
                # Получаем следующий вопрос
                question, keyboard = context.ask_for_context()
                logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
                
                # Отправляем следующий вопрос
                if question:
                    safe_send_message(
                        message,
                        f"📝 **Давайте познакомимся**\n\n{question}",
                        reply_markup=keyboard,
                        parse_mode=None,
                        delete_previous=True
                    )
                else:
                    # Если вопросов больше нет, показываем завершение
                    # Запускаем в основном потоке через run_async_task
                    run_async_task(lambda: show_context_complete(message, context))
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при обновлении погоды: {e}")
                # В случае ошибки всё равно показываем следующий вопрос
                question, keyboard = context.ask_for_context()
                if question:
                    safe_send_message(
                        message,
                        f"📝 **Давайте познакомимся**\n\n{question}",
                        reply_markup=keyboard,
                        parse_mode=None,
                        delete_previous=True
                    )
                else:
                    run_async_task(lambda: show_context_complete(message, context))
        
        # Запускаем в отдельном потоке
        threading.Thread(target=update_weather_and_continue, daemon=True).start()
        
        return True
    
    elif context.awaiting_context == "age":
        # Обработка возраста
        logger.info(f"📅 Обрабатываем возраст: {text}")
        try:
            age = int(text)
            if 1 <= age <= 120:
                logger.info(f"✅ Возраст корректен: {age}")
                context.age = age
                context.awaiting_context = None
                
                # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
                run_async_task(save_context_to_db, user_id)
                
                # Получаем следующий вопрос
                logger.info(f"❓ Получаем следующий вопрос после возраста...")
                question, keyboard = context.ask_for_context()
                logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
                
                if question:
                    logger.info(f"📤 Отправляем следующий вопрос...")
                    safe_send_message(
                        message,
                        f"📝 **Давайте познакомимся**\n\n{question}",
                        reply_markup=keyboard,
                        parse_mode=None,
                        delete_previous=True
                    )
                    logger.info(f"✅ Вопрос отправлен")
                else:
                    logger.info(f"🎉 Вопросов больше нет, показываем завершение")
                    show_context_complete(message, context)
            else:
                logger.warning(f"⚠️ Возраст вне диапазона: {age}")
                safe_send_message(
                    message,
                    "**❌ Возраст должен быть от 1 до 120 лет.**\n\n📅 Сколько вам лет? (напишите число)",
                    parse_mode=None,
                    delete_previous=True
                )
        except ValueError:
            logger.warning(f"⚠️ Некорректное число: {text}")
            safe_send_message(
                message,
                "**❌ Пожалуйста, введите число.**\n\n📅 Сколько вам лет? (напишите число)",
                parse_mode=None,
                delete_previous=True
            )
        
        return True
    
    elif context.awaiting_context == "gender":
        # Обработка пола из текста
        logger.info(f"👤 Обрабатываем пол из текста: {text}")
        gender_lower = text.lower().strip()
        if gender_lower in ['м', 'муж', 'мужчина', 'male', 'парень']:
            context.gender = "male"
            logger.info(f"✅ Распознан мужской пол")
        elif gender_lower in ['ж', 'жен', 'женщина', 'female', 'девушка']:
            context.gender = "female"
            logger.info(f"✅ Распознан женский пол")
        else:
            context.gender = "other"
            logger.info(f"⚠️ Пол не распознан, установлен other")
        
        context.awaiting_context = None
        
        # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
        run_async_task(save_context_to_db, user_id)
        
        # Получаем следующий вопрос
        logger.info(f"❓ Получаем следующий вопрос после пола...")
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
        
        if question:
            logger.info(f"📤 Отправляем следующий вопрос...")
            safe_send_message(
                message,
                f"📝 **Давайте познакомимся**\n\n{question}",
                reply_markup=keyboard,
                parse_mode=None,
                delete_previous=True
            )
            logger.info(f"✅ Вопрос отправлен")
        else:
            logger.info(f"🎉 Вопросов больше нет, показываем завершение")
            show_context_complete(message, context)
        
        return True
    
    logger.warning(f"❓ Неизвестное состояние awaiting_context: {context.awaiting_context}")
    return False

# ============================================
# ЗАВЕРШЕНИЕ СБОРА КОНТЕКСТА (ИСПРАВЛЕНО)
# ============================================

def show_context_complete(message: Message, context: UserContext):
    """
    Показывает итоговый экран после сбора контекста
    """
    user_id = message.chat.id
    logger.info(f"🎉 show_context_complete вызван для user {user_id}")
    
    # 👇 СИНХРОННЫЙ ВЫЗОВ (НО В ОТДЕЛЬНОМ ПОТОКЕ)
    logger.info(f"🌤️ Обновляем погоду для итогового экрана...")
    context.update_weather()
    
    # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
    run_async_task(save_context_to_db, user_id)
    
    # Формируем сводку
    summary = f"✅ **Отлично! Теперь я знаю о вас:**\n\n"
    
    if context.city:
        summary += f"📍 **Город:** {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        summary += f"👤 **Пол:** {gender_str}\n"
    if context.age:
        summary += f"📅 **Возраст:** {context.age}\n"
    if context.weather_cache:
        weather = context.weather_cache
        summary += f"{weather['icon']} **Погода:** {weather['description']}, {weather['temp']}°C\n"
    
    summary += f"\n🎯 Теперь я буду учитывать это в наших разговорах!\n\n"
    summary += f"🧠 **ЧТО ДАЛЬШЕ?**\n\n"
    summary += "Чтобы я мог помочь по-настоящему, нужно пройти тест (15 минут).\n"
    summary += "Он определит ваш психологический профиль по 4 векторам и глубинным паттернам.\n\n"
    summary += f"👇 **Начинаем?**"
    
    # ✅ ИСПРАВЛЕНО: меняем callback на прямой старт теста
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🚀 НАЧАТЬ ТЕСТ", callback_data="start_stage_1_direct"))
    keyboard.row(InlineKeyboardButton("📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits"))
    # ❌ Кнопка "❓ ЗАДАТЬ ВОПРОС" удалена
    
    logger.info(f"📤 Отправляем итоговый экран...")
    safe_send_message(
        message,
        summary,
        reply_markup=keyboard,
        parse_mode=None,
        delete_previous=True
    )
    logger.info(f"✅ Итоговый экран отправлен")
    
    # Очищаем состояние
    if user_id in user_states:
        logger.info(f"🧹 Очищаем состояние пользователя {user_id}")
        del user_states[user_id]

# ============================================
# ПРИНУДИТЕЛЬНЫЙ СБОР КОНТЕКСТА (КОМАНДА)
# ============================================

def cmd_context(message: Message):
    """
    Команда /context - принудительный сбор контекста
    """
    user_id = message.chat.id
    logger.info(f"🔄 cmd_context вызван для user {user_id}")
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    
    # Сбрасываем контекст
    context.city = None
    context.gender = None
    context.age = None
    context.weather_cache = {}
    context.life_context_complete = False
    
    # ✅ ИСПРАВЛЕНО: Сохраняем сброс в БД через run_async_task
    run_async_task(save_context_to_db, user_id)
    
    safe_send_message(
        message,
        "🔄 **Давайте обновим ваш контекст**",
        parse_mode=None,
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
        "📝 **Для точной работы мне нужно немного узнать о вас.**",
        parse_mode=None,
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
        text = "📝 **Контекст не заполнен**\n\n"
        text += "Необходимо указать город, пол и возраст."
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("📝 ЗАПОЛНИТЬ", callback_data="start_context"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu"))
        
        safe_send_message(
            message,
            text,
            reply_markup=keyboard,
            parse_mode=None,
            delete_previous=True
        )
        return
    
    # Формируем текст с текущим контекстом
    text = f"📊 **ТВОЙ КОНТЕКСТ**\n\n"
    
    if context.name:
        text += f"👤 **Имя:** {context.name}\n"
    if context.city:
        text += f"📍 **Город:** {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        text += f"👤 **Пол:** {gender_str}\n"
    if context.age:
        text += f"📅 **Возраст:** {context.age}\n"
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} **Погода:** {weather['description']}, {weather['temp']}°C\n"
    
    # Жизненный контекст, если есть
    if context.life_context_complete:
        text += f"\n📋 **ЖИЗНЕННЫЙ КОНТЕКСТ:**\n"
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
        parse_mode=None,
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
    
    # ✅ ИСПРАВЛЕНО: Сохраняем в БД через run_async_task
    run_async_task(save_context_to_db, user_id)

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
    'handle_context_callback',
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
