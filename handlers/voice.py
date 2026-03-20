#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики голосовых сообщений для MAX
Версия 2.9 - ИСПРАВЛЕНО: поддержка разных типов токенов
"""

import os
import tempfile
import logging
import asyncio
import json
import threading
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

# ✅ ИСПРАВЛЕНО: используем sync_db
from db_sync import sync_db

logger = logging.getLogger(__name__)


# ============================================
# ФУНКЦИЯ ДЛЯ ОТПРАВКИ ГОЛОСОВЫХ СООБЩЕНИЙ В MAX
# ============================================

async def send_voice_to_max(chat_id: int, audio_data: bytes, caption: str = None) -> bool:
    """
    Отправляет голосовое сообщение в MAX API
    Поддерживает как JWT токены, так и простые API ключи
    """
    if not audio_data:
        logger.error("❌ Нет аудиоданных для отправки")
        return False
    
    # ========== ДИАГНОСТИКА ТОКЕНА ==========
    logger.info("=" * 50)
    logger.info("🔍 ДИАГНОСТИКА ОТПРАВКИ ГОЛОСА")
    logger.info("=" * 50)
    
    if not MAX_TOKEN:
        logger.error("❌ MAX_TOKEN не настроен в config.py")
        return False
    
    if MAX_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("❌ MAX_TOKEN не заменен на реальный токен")
        return False
    
    # Определяем тип токена
    is_jwt = '.' in MAX_TOKEN
    token_parts = MAX_TOKEN.split('.')
    
    logger.info(f"📏 Длина токена: {len(MAX_TOKEN)} символов")
    logger.info(f"🔑 Тип токена: {'JWT' if is_jwt else 'простой API ключ'}")
    if is_jwt:
        logger.info(f"📋 JWT частей: {len(token_parts)}")
    
    logger.info(f"📤 Отправка голоса в чат {chat_id}")
    logger.info("=" * 50)
    
    temp_path = None
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Выбираем метод авторизации в зависимости от типа токена
            if is_jwt:
                headers = {
                    "Authorization": f"Bearer {MAX_TOKEN}",
                    "Content-Type": "application/json"
                }
                logger.info("🔑 Используем Bearer авторизацию (JWT)")
            else:
                # Простой API ключ - пробуем разные форматы
                headers = {
                    "X-API-Key": MAX_TOKEN,
                    "Content-Type": "application/json"
                }
                logger.info("🔑 Используем X-API-Key авторизацию")
            
            logger.info("📡 ШАГ 1: Запрашиваем upload URL...")
            
            # Пробуем основной эндпоинт
            upload_response = await session.post(
                "https://platform-api.max.ru/uploads?type=audio",
                headers=headers
            )
            
            logger.info(f"📡 Статус ответа: {upload_response.status}")
            
            # Если не сработало с X-API-Key, пробуем другой формат
            if upload_response.status == 401 and not is_jwt:
                logger.info("🔄 Пробуем другой формат авторизации...")
                headers = {
                    "Authorization": f"Token {MAX_TOKEN}",
                    "Content-Type": "application/json"
                }
                upload_response = await session.post(
                    "https://platform-api.max.ru/uploads?type=audio",
                    headers=headers
                )
                logger.info(f"📡 Статус ответа (Token): {upload_response.status}")
            
            if upload_response.status != 200:
                error_text = await upload_response.text()
                logger.error(f"❌ Не удалось получить upload URL: {upload_response.status}")
                logger.error(f"❌ Текст ошибки: {error_text}")
                
                if upload_response.status == 401:
                    logger.error("🔍 ОШИБКА 401: Токен недействителен или не имеет прав")
                    logger.error("   Проверьте:")
                    logger.error("   1. Токен правильный?")
                    logger.error("   2. У токена есть права на отправку голосовых сообщений?")
                    logger.error("   3. В MAX API другой формат авторизации?")
                
                return False
            
            upload_data = await upload_response.json()
            upload_url = upload_data.get("upload_url")
            token = upload_data.get("token")
            
            if not upload_url:
                logger.error(f"❌ Нет upload_url в ответе: {upload_data}")
                return False
            
            if not token:
                logger.error(f"❌ Нет token в ответе: {upload_data}")
                return False
            
            logger.info(f"✅ Получен upload URL: {upload_url[:50]}...")
            logger.info(f"✅ Получен token для загрузки: {token[:10]}...")
            
            # ШАГ 2: Загружаем аудиофайл
            logger.info("📡 ШАГ 2: Загружаем аудиофайл...")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg', mode='wb') as tmp:
                tmp.write(audio_data)
                temp_path = tmp.name
            
            logger.info(f"📝 Создан временный файл: {temp_path} ({len(audio_data)} байт)")
            
            # Для загрузки файла используем те же заголовки (без Content-Type)
            file_headers = {}
            if is_jwt:
                file_headers = {"Authorization": f"Bearer {MAX_TOKEN}"}
            
            with open(temp_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, filename='voice.ogg', content_type='audio/ogg')
                
                upload_file_response = await session.post(
                    upload_url,
                    data=form_data,
                    headers=file_headers
                )
            
            logger.info(f"📡 Статус загрузки файла: {upload_file_response.status}")
            
            if upload_file_response.status not in [200, 201, 204]:
                error_text = await upload_file_response.text()
                logger.error(f"❌ Ошибка загрузки файла: {upload_file_response.status}")
                logger.error(f"❌ Текст ошибки: {error_text}")
                return False
            
            logger.info("✅ Файл успешно загружен")
            
            # ШАГ 3: Отправляем сообщение с аттачем
            logger.info("📡 ШАГ 3: Отправляем сообщение с аудио...")
            
            # Для отправки сообщения используем исходные заголовки
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
            
            # Используем тот же тип авторизации, что и в первом шаге
            if is_jwt:
                msg_headers = {"Authorization": f"Bearer {MAX_TOKEN}", "Content-Type": "application/json"}
            else:
                # Пробуем X-API-Key для отправки сообщения
                msg_headers = {"X-API-Key": MAX_TOKEN, "Content-Type": "application/json"}
            
            message_response = await session.post(
                "https://platform-api.max.ru/messages",
                headers=msg_headers,
                json=message_data
            )
            
            logger.info(f"📡 Статус отправки сообщения: {message_response.status}")
            
            if message_response.status in [200, 201]:
                logger.info("✅ Голосовое сообщение успешно отправлено")
                return True
            else:
                error_text = await message_response.text()
                logger.error(f"❌ Ошибка отправки сообщения: {message_response.status}")
                logger.error(f"❌ Текст ошибки: {error_text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голоса: {e}", exc_info=True)
        return False
    
    finally:
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
    
    # Логируем через sync_db
    threading.Thread(target=sync_db.log_event, args=(
        user_id, 'voice_received', 
        {'state': current_state, 'voice_duration': message.voice.duration if message.voice else None}
    ), daemon=True).start()
    
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
            
            threading.Thread(target=sync_db.log_event, args=(user_id, 'voice_recognition_failed', {}), daemon=True).start()
            
            await safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        logger.info(f"✅ Распознан текст ({len(recognized_text)} символов): {recognized_text[:100]}...")
        
        threading.Thread(target=sync_db.log_event, args=(
            user_id, 'voice_recognized', 
            {'text_length': len(recognized_text), 'state': current_state}
        ), daemon=True).start()
        
        # Удаляем статусное сообщение
        await safe_delete_message(message.chat.id, status_msg.message_id)
        
        # Отправляем текст, что распознали
        await safe_send_message(
            message,
            f"📝 <b>Вы сказали:</b>\n{recognized_text}",
            delete_previous=True
        )
        
        # Обрабатываем распознанный текст в зависимости от состояния
        if current_state == TestStates.awaiting_question:
            from handlers.questions import process_text_question_async
            await process_text_question_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.collecting_life_context:
            from handlers.reality import process_life_context_async
            await process_life_context_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.collecting_goal_context:
            from handlers.reality import process_goal_context_async
            await process_goal_context_async(message, user_id, recognized_text)
            
        elif current_state == TestStates.pretest_question:
            await handle_pretest_voice(message, user_id, recognized_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        
        threading.Thread(target=sync_db.log_event, args=(user_id, 'voice_error', {'error': str(e)}), daemon=True).start()
        
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
    
    threading.Thread(target=sync_db.log_event, args=(
        user_id, 'pretest_question_voice', 
        {'text_preview': recognized_text[:100]}
    ), daemon=True).start()
    
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
    
    threading.Thread(target=sync_db.log_event, args=(user_id, 'voice_test_started', {'text_length': len(text)}), daemon=True).start()
    
    status_msg = await safe_send_message(
        message,
        "🎧 Генерирую тестовый голос...",
        delete_previous=True
    )
    
    results = []
    for mode in ["coach", "psychologist", "trainer"]:
        audio = await text_to_speech(text, mode)
        if audio:
            success = await send_voice_to_max(message.chat.id, audio, f"Тест режима {mode}")
            if success:
                results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']} (отправлен)")
            else:
                results.append(f"⚠️ {COMMUNICATION_MODES[mode]['display_name']} (сгенерирован, но не отправлен)")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']} (не сгенерирован)")
        await asyncio.sleep(1)
    
    await safe_delete_message(message.chat.id, status_msg.message_id)
    
    threading.Thread(target=sync_db.log_event, args=(user_id, 'voice_test_completed', {'results': results}), daemon=True).start()
    
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
