#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики голосовых сообщений для MAX
Версия 2.7 - ИСПРАВЛЕНЫ АСИНХРОННЫЕ ВЫЗОВЫ
"""

import os
import tempfile
import logging
import asyncio
import aiohttp
import json
import threading  # ✅ ДОБАВЛЕНО
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

# ✅ ДОБАВЛЕНО: импорт для БД
from db_instance import db

logger = logging.getLogger(__name__)

# ============================================
# ✅ ДОБАВЛЕНО: ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ АСИНХРОННЫХ ВЫЗОВОВ
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
    
    # ========== РАСШИРЕННАЯ ДИАГНОСТИКА ТОКЕНА ==========
    logger.info("=" * 50)
    logger.info("🔍 ДИАГНОСТИКА ОТПРАВКИ ГОЛОСА")
    logger.info("=" * 50)
    
    if not MAX_TOKEN:
        logger.error("❌ MAX_TOKEN не настроен в config.py")
        logger.error("Проверьте переменные окружения на Render")
        logger.error("В Dashboard Render -> ваш сервис -> Environment -> добавьте MAX_TOKEN")
        return False
    
    # Проверяем, что токен не равен заглушке
    if MAX_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("❌ MAX_TOKEN не заменен на реальный токен (стоит заглушка)")
        logger.error("Получите реальный токен у @MasterBot и добавьте в переменные окружения")
        return False
    
    # Проверяем длину токена (обычно JWT токены имеют длину > 100 символов)
    logger.info(f"📏 Длина токена: {len(MAX_TOKEN)} символов")
    if len(MAX_TOKEN) < 50:
        logger.warning("⚠️ Токен подозрительно короткий. Обычно JWT токены длиннее 50 символов.")
    
    # Показываем первые и последние символы для отладки
    token_start = MAX_TOKEN[:15] if len(MAX_TOKEN) > 15 else MAX_TOKEN
    token_end = MAX_TOKEN[-15:] if len(MAX_TOKEN) > 15 else MAX_TOKEN
    logger.info(f"🔑 Начало токена: {token_start}...")
    logger.info(f"🔑 Конец токена: ...{token_end}")
    
    # Проверяем, есть ли у токена префикс "Bearer " (это ошибка - в токене не должно быть)
    if MAX_TOKEN.startswith("Bearer "):
        logger.error("❌ Токен содержит 'Bearer ' в начале. Это неправильно!")
        logger.error("Токен должен быть просто строкой, без 'Bearer '")
        return False
    
    # Проверяем, есть ли у токена пробелы
    if " " in MAX_TOKEN:
        logger.error("❌ Токен содержит пробелы. Токен не должен содержать пробелов.")
        return False
    
    # Проверяем, является ли токен валидным JWT (опционально)
    parts = MAX_TOKEN.split('.')
    if len(parts) == 3:
        logger.info("✅ Токен имеет структуру JWT (3 части через точки)")
        try:
            # Пробуем декодировать первую часть (заголовок) - не проверяем подпись, просто смотрим
            import base64
            import json
            # Добавляем padding если нужно
            header_part = parts[0]
            header_part += '=' * (4 - len(header_part) % 4) if len(header_part) % 4 else ''
            try:
                header_json = base64.urlsafe_b64decode(header_part).decode('utf-8')
                header = json.loads(header_json)
                logger.info(f"📋 JWT заголовок: {header}")
            except:
                logger.warning("⚠️ Не удалось декодировать JWT заголовок")
        except:
            logger.warning("⚠️ Ошибка при анализе JWT структуры")
    else:
        logger.warning(f"⚠️ Токен имеет {len(parts)} частей (ожидалось 3 для JWT)")
    
    logger.info(f"📤 Отправка голоса в чат {chat_id}")
    logger.info("=" * 50)
    # ===================================================
    
    temp_path = None
    try:
        # ШАГ 1: Получаем URL для загрузки
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {MAX_TOKEN}",
                "Content-Type": "application/json"
            }
            
            logger.info("📡 ШАГ 1: Запрашиваем upload URL...")
            upload_response = await session.post(
                "https://platform-api.max.ru/uploads?type=audio",
                headers=headers
            )
            
            logger.info(f"📡 Статус ответа: {upload_response.status}")
            
            if upload_response.status != 200:
                error_text = await upload_response.text()
                logger.error(f"❌ Не удалось получить upload URL: {upload_response.status}")
                logger.error(f"❌ Текст ошибки: {error_text}")
                
                # Дополнительная диагностика
                if upload_response.status == 401:
                    logger.error("🔍 ОШИБКА 401: Проблема с авторизацией")
                    logger.error("   Возможные причины:")
                    logger.error("   • Токен недействителен или истек")
                    logger.error("   • Токен не имеет прав на отправку голосовых сообщений")
                    logger.error("   • Неправильный формат токена")
                elif upload_response.status == 403:
                    logger.error("🔍 ОШИБКА 403: Доступ запрещен")
                elif upload_response.status == 429:
                    logger.error("🔍 ОШИБКА 429: Слишком много запросов")
                
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
            
            logger.info(f"📡 Статус загрузки файла: {upload_file_response.status}")
            
            if upload_file_response.status not in [200, 201, 204]:
                error_text = await upload_file_response.text()
                logger.error(f"❌ Ошибка загрузки файла: {upload_file_response.status}")
                logger.error(f"❌ Текст ошибки: {error_text}")
                return False
            
            logger.info("✅ Файл успешно загружен")
            
            # ШАГ 3: Отправляем сообщение с аттачем
            logger.info("📡 ШАГ 3: Отправляем сообщение с аудио...")
            
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
            
            message_response = await session.post(
                "https://platform-api.max.ru/messages",
                headers=headers,
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
    
    # ✅ ИСПРАВЛЕНО: Логируем событие через run_async_task
    run_async_task(db.log_event,
        user_id, 
        'voice_received', 
        {'state': current_state, 'voice_duration': message.voice.duration if message.voice else None}
    )
    
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
            
            # ✅ ИСПРАВЛЕНО: Логируем ошибку через run_async_task
            run_async_task(db.log_event, user_id, 'voice_recognition_failed', {})
            
            await safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        logger.info(f"✅ Распознан текст ({len(recognized_text)} символов): {recognized_text[:100]}...")
        
        # ✅ ИСПРАВЛЕНО: Логируем успешное распознавание через run_async_task
        run_async_task(db.log_event,
            user_id, 
            'voice_recognized', 
            {'text_length': len(recognized_text), 'state': current_state}
        )
        
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
        
        # ✅ ИСПРАВЛЕНО: Логируем ошибку через run_async_task
        run_async_task(db.log_event, user_id, 'voice_error', {'error': str(e)})
        
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
    
    # ✅ ИСПРАВЛЕНО: Логируем вопрос до теста через run_async_task
    run_async_task(db.log_event,
        user_id, 
        'pretest_question_voice', 
        {'text_preview': recognized_text[:100]}
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
    
    # ✅ ИСПРАВЛЕНО: Логируем тест через run_async_task
    run_async_task(db.log_event, user_id, 'voice_test_started', {'text_length': len(text)})
    
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
    
    # ✅ ИСПРАВЛЕНО: Логируем результаты через run_async_task
    run_async_task(db.log_event, user_id, 'voice_test_completed', {'results': results})
    
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
