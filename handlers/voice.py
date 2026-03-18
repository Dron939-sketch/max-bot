#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики голосовых сообщений для MAX
Версия 2.4 - ПОЛНАЯ с диагностикой токена и исправленными await
"""

import os
import tempfile
import logging
import asyncio
import aiohttp
import json
from typing import Optional

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем bot напрямую из bot_instance
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
from config import COMMUNICATION_MODES, MAX_TOKEN

logger = logging.getLogger(__name__)

# ============================================
# ФУНКЦИЯ ДЛЯ ОТПРАВКИ ГОЛОСОВЫХ СООБЩЕНИЙ В MAX
# ============================================

async def send_voice_to_max(chat_id: int, audio_data: bytes, caption: str = None) -> bool:
    """
    Отправляет голосовое сообщение в MAX (3-шаговый процесс)
    
    Args:
        chat_id: ID чата (не используется напрямую, но нужен для совместимости)
        audio_data: Аудиоданные в формате OGG
        caption: Подпись к сообщению (опционально)
    
    Returns:
        True если успешно, False если ошибка
    """
    if not audio_data:
        logger.error("❌ Нет аудиоданных для отправки")
        return False
    
    # ========== ДИАГНОСТИКА ТОКЕНА ==========
    if not MAX_TOKEN:
        logger.error("❌ MAX_TOKEN не настроен в config.py")
        logger.error("Проверьте переменные окружения на Render")
        return False
    
    # Проверяем, что токен не равен заглушке
    if MAX_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("❌ MAX_TOKEN не заменен на реальный токен (стоит заглушка)")
        return False
    
    # Показываем первые символы токена для отладки (безопасно)
    token_preview = MAX_TOKEN[:10] + "..." if len(MAX_TOKEN) > 10 else MAX_TOKEN
    logger.info(f"🔑 Использую токен: {token_preview}")
    logger.info(f"📤 Отправка голоса в чат {chat_id}")
    # =========================================
    
    temp_path = None
    try:
        # ШАГ 1: Получаем URL для загрузки
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {MAX_TOKEN}",
                "Content-Type": "application/json"
            }
            
            logger.info("📡 Запрашиваем upload URL...")
            upload_response = await session.post(
                "https://platform-api.max.ru/uploads?type=audio",
                headers=headers
            )
            
            if upload_response.status != 200:
                error_text = await upload_response.text()
                logger.error(f"❌ Не удалось получить upload URL: {upload_response.status} - {error_text}")
                return False
            
            upload_data = await upload_response.json()
            upload_url = upload_data.get("upload_url")
            token = upload_data.get("token")
            
            if not upload_url or not token:
                logger.error(f"❌ Нет upload_url или token в ответе: {upload_data}")
                return False
            
            logger.info(f"✅ Получен upload URL: {upload_url[:50]}...")
            logger.info(f"✅ Получен token для загрузки: {token[:10]}...")
            
            # ШАГ 2: Загружаем аудиофайл
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg', mode='wb') as tmp:
                tmp.write(audio_data)
                temp_path = tmp.name
            
            logger.info(f"📝 Создан временный файл: {temp_path} ({len(audio_data)} байт)")
            
            # Загружаем файл
            with open(temp_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, filename='voice.ogg', content_type='audio/ogg')
                
                upload_file_response = await session.post(
                    upload_url,
                    data=form_data
                )
            
            if upload_file_response.status not in [200, 201, 204]:
                error_text = await upload_file_response.text()
                logger.error(f"❌ Ошибка загрузки файла: {upload_file_response.status} - {error_text}")
                return False
            
            logger.info("✅ Файл успешно загружен")
            
            # ШАГ 3: Отправляем сообщение с аттачем
            message_data = {
                "text": caption or "🎙 Голосовое сообщение",
                "attachments": [
                    {
                        "type": "audio",
                        "payload": {
                            "token": token
                        }
                    }
                ]
            }
            
            logger.info("📤 Отправляем сообщение с аудио...")
            message_response = await session.post(
                "https://platform-api.max.ru/messages",
                headers=headers,
                json=message_data
            )
            
            if message_response.status in [200, 201]:
                logger.info("✅ Голосовое сообщение успешно отправлено")
                return True
            else:
                error_text = await message_response.text()
                logger.error(f"❌ Ошибка отправки сообщения: {message_response.status} - {error_text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голоса: {e}", exc_info=True)
        return False
    
    finally:
        # Удаляем временный файл
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"🗑️ Временный файл удален: {temp_path}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить временный файл: {e}")


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
            # ✅ Отправляем голос
            success = await send_voice_to_max(message.chat.id, audio, f"Тест режима {mode}")
            if success:
                results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']} (отправлен)")
            else:
                results.append(f"⚠️ {COMMUNICATION_MODES[mode]['display_name']} (сгенерирован, но не отправлен)")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']} (не сгенерирован)")
        await asyncio.sleep(1)
    
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
    'test_voice_message',
    'send_voice_to_max'
]
