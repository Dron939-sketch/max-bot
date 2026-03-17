#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики голосовых сообщений для MAX
"""

import os
import tempfile
import logging
from typing import Optional

from bot_instance import bot
from maxibot.types import Message, CallbackQuery
from message_utils import safe_send_message, safe_delete_message
from services import speech_to_text, text_to_speech
from state import user_data, user_contexts, get_state, set_state, TestStates
from modes import get_mode
from formatters import clean_text_for_safe_display

logger = logging.getLogger(__name__)

async def handle_voice_message(message: Message):
    """
    Обрабатывает голосовое сообщение пользователя
    """
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    
    # Проверяем, завершен ли тест
    if not data.get("profile_data") and not data.get("ai_generated_profile"):
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
    
    temp_file = None
    try:
        # Получаем файл голосового сообщения
        file_info = await bot.get_file(message.voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            await bot.download_file(file_info.file_path, destination=temp_file)
        
        # Распознаем речь
        recognized_text = await speech_to_text(temp_file)
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file)
        except:
            pass
        
        if not recognized_text:
            await safe_delete_message(message.chat.id, status_msg.message_id)
            await safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        # Удаляем статусное сообщение
        await safe_delete_message(message.chat.id, status_msg.message_id)
        
        # Обрабатываем распознанный текст как обычный вопрос
        from handlers.questions import process_text_question
        await process_text_question(message, user_id, recognized_text)
        
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
