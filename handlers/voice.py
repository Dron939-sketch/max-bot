#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики голосовых сообщений для MAX
Версия 2.0 - ПОЛНАЯ асинхронная с поддержкой всех состояний
"""

import os
import tempfile
import logging
import asyncio
from typing import Optional

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from maxibot.utils import BufferedInputFile

from bot_instance import bot
from message_utils import safe_send_message, safe_delete_message
from services import speech_to_text, text_to_speech
from state import (
    user_data, user_contexts, user_state_data,
    get_state, set_state, TestStates,
    get_user_name, get_user_context
)
from modes import get_mode
from formatters import bold, clean_text_for_safe_display
from config import COMMUNICATION_MODES

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

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
# ОСНОВНОЙ ОБРАБОТЧИК ГОЛОСОВЫХ СООБЩЕНИЙ
# ============================================

async def handle_voice_message(message: Message):
    """
    Обрабатывает голосовое сообщение пользователя
    """
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    current_state = get_state(user_id)
    
    logger.info(f"🎤 Получено голосовое сообщение от пользователя {user_id}, состояние: {current_state}")
    
    # Проверяем, в правильном ли состоянии получено сообщение
    allowed_states = [
        TestStates.awaiting_question,
        TestStates.collecting_life_context,
        TestStates.collecting_goal_context,
        TestStates.pretest_question
    ]
    
    if current_state not in allowed_states:
        if not is_test_completed(data):
            await safe_send_message(
                message,
                "🎙 Сначала нужно пройти тест. Используйте /start",
                delete_previous=True
            )
            return
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="ask_question"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
        
        await safe_send_message(
            message,
            "🎙 Чтобы задать вопрос голосом, сначала нажмите кнопку '❓ ЗАДАТЬ ВОПРОС'",
            reply_markup=keyboard,
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = await safe_send_message(
        message,
        "🎤 Распознаю речь...",
        delete_previous=True
    )
    
    temp_file = None
    try:
        # Получаем файл голосового сообщения
        file_info = await bot.get_file(message.voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            await bot.download_file(file_info.file_path, destination=temp_file)
        
        logger.info(f"📥 Голосовой файл сохранен: {temp_file}")
        
        # Распознаем речь
        recognized_text = await speech_to_text(temp_file)
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file)
            logger.info(f"🗑️ Временный файл удален: {temp_file}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        if not recognized_text:
            await safe_delete_message(message.chat.id, status_msg.message_id)
            await safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        logger.info(f"✅ Распознан текст ({len(recognized_text)} символов): {recognized_text[:100]}...")
        
        # Удаляем статусное сообщение
        await safe_delete_message(message.chat.id, status_msg.message_id)
        
        # ✅ 1. Отправляем текст, что распознали
        await safe_send_message(
            message,
            f"📝 <b>Вы сказали:</b>\n{recognized_text}",
            delete_previous=True
        )
        
        # Обрабатываем распознанный текст в зависимости от состояния
        if current_state == TestStates.awaiting_question:
            # Обычный вопрос - обрабатываем через questions.py
            from handlers.questions import process_text_question_async
            await process_text_question_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.collecting_life_context:
            # Сбор контекста жизни
            from handlers.reality import process_life_context_async
            await process_life_context_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.collecting_goal_context:
            # Сбор контекста цели
            from handlers.reality import process_goal_context_async
            await process_goal_context_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.pretest_question:
            # Вопрос до теста
            await handle_pretest_voice(message, user_id, recognized_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        
        if status_msg:
            try:
                await safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке голоса\n\nПопробуйте еще раз или напишите текстом.",
            delete_previous=True
        )


# ============================================
# ОБРАБОТЧИК ГОЛОСОВЫХ СООБЩЕНИЙ ДО ТЕСТА
# ============================================

async def handle_pretest_voice(message: Message, user_id: int, recognized_text: str):
    """
    Обрабатывает голосовой вопрос до прохождения теста
    """
    await safe_send_message(
        message,
        f"📝 <b>Вы сказали:</b>\n{recognized_text}\n\n"
        f"Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. "
        f"Пройдите тест — это займёт 15 минут.",
        delete_previous=True
    )
    
    # Сбрасываем состояние
    set_state(user_id, None)


# ============================================
# ФУНКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ ГОЛОСА
# ============================================

async def test_voice_message(message: Message, text: str = "Привет! Это тестовое голосовое сообщение."):
    """
    Тестирует синтез речи (только для администраторов)
    """
    user_id = message.from_user.id
    from config import ADMIN_IDS
    
    if user_id not in ADMIN_IDS:
        await safe_send_message(message, "⛔ Только для администраторов", delete_previous=True)
        return
    
    status_msg = await safe_send_message(
        message,
        "🎧 Генерирую тестовый голос...",
        delete_previous=True
    )
    
    results = []
    for mode in ["coach", "psychologist", "trainer"]:
        audio = await text_to_speech(text, mode)
        if audio:
            audio_file = BufferedInputFile(audio, filename=f"test_{mode}.ogg")
            await message.answer_voice(
                audio_file,
                caption=f"🎙 Режим: {COMMUNICATION_MODES[mode]['display_name']}"
            )
            results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']}")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']}")
        await asyncio.sleep(0.5)
    
    await safe_delete_message(message.chat.id, status_msg.message_id)
    await safe_send_message(
        message,
        "📊 Результаты тестирования:\n" + "\n".join(results),
        delete_previous=True
    )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'handle_voice_message',
    'test_voice_message'
]
