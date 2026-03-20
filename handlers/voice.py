#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик голосовых сообщений для MAX
Версия 2.1 - ИСПРАВЛЕНО: использование правильного токена MAX_TOKEN
"""

import logging
import requests
import asyncio
import io
import os
import time
from typing import Optional, Tuple, Dict, Any, List

from maxibot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from message_utils import safe_send_message, safe_delete_message, send_with_status_cleanup

# ✅ ИСПРАВЛЕНО: используем правильную переменную MAX_TOKEN
from config import MAX_TOKEN, DEEPGRAM_API_KEY, YANDEX_API_KEY, VOICE_SETTINGS, COMMUNICATION_MODES
from services import synthesize_speech, transcribe_audio

logger = logging.getLogger(__name__)

# API URL для работы с голосом в MAX
MAX_VOICE_API_URL = "https://api.max.ru/v1/voice"  # Замените на реальный URL

# Кэш для синтезированной речи
_voice_cache = {}
_voice_cache_time = {}

def send_voice_message(chat_id: int, audio_data: bytes, filename: str = "voice.ogg") -> bool:
    """
    Отправляет голосовое сообщение через API MAX
    
    Args:
        chat_id: ID чата (пользователя)
        audio_data: бинарные данные аудио
        filename: имя файла
        
    Returns:
        bool: успешность отправки
    """
    try:
        if not MAX_TOKEN:
            logger.error("❌ MAX_TOKEN не задан в .env файле")
            return False
        
        # Пробуем разные форматы авторизации
        auth_methods = [
            {"name": "X-API-Key", "headers": {"X-API-Key": MAX_TOKEN}},
            {"name": "Bearer", "headers": {"Authorization": f"Bearer {MAX_TOKEN}"}},
            {"name": "query_param", "headers": {}, "use_param": True}
        ]
        
        upload_url = None
        upload_method = None
        
        # ШАГ 1: Получаем URL для загрузки
        logger.info("📡 ШАГ 1: запрашиваем URL для загрузки...")
        
        for method in auth_methods:
            try:
                if method.get("use_param"):
                    response = requests.post(
                        f"{MAX_VOICE_API_URL}/upload",
                        params={"token": MAX_TOKEN},
                        json={
                            "chat_id": chat_id,
                            "filename": filename,
                            "size": len(audio_data),
                            "type": "voice"
                        },
                        timeout=10
                    )
                else:
                    response = requests.post(
                        f"{MAX_VOICE_API_URL}/upload",
                        headers=method["headers"],
                        json={
                            "chat_id": chat_id,
                            "filename": filename,
                            "size": len(audio_data),
                            "type": "voice"
                        },
                        timeout=10
                    )
                
                logger.info(f"📡 Статус ответа ({method['name']}): {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    upload_url = data.get("upload_url")
                    upload_method = method["name"]
                    logger.info(f"✅ Получен URL для загрузки через {method['name']}")
                    break
                elif response.status_code == 401:
                    logger.warning(f"⚠️ Ошибка 401 для метода {method['name']}: {response.text}")
                    continue
                else:
                    logger.warning(f"⚠️ Неожиданный статус {response.status_code} для {method['name']}: {response.text}")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при запросе через {method['name']}: {e}")
                continue
        
        if not upload_url:
            logger.error("❌ Не удалось получить URL для загрузки ни одним методом")
            return False
        
        # ШАГ 2: Загружаем аудио по полученному URL
        logger.info(f"📡 ШАГ 2: загружаем аудио ({len(audio_data)} байт)...")
        
        try:
            response = requests.put(
                upload_url,
                data=audio_data,
                headers={
                    "Content-Type": "audio/ogg",
                    "Content-Length": str(len(audio_data))
                },
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка загрузки: {response.status_code}")
                return False
                
            logger.info(f"✅ Аудио успешно загружено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке аудио: {e}")
            return False
        
        # ШАГ 3: Отправляем сообщение с голосом
        logger.info(f"📡 ШАГ 3: отправляем сообщение с голосом в чат {chat_id}...")
        
        try:
            if upload_method == "X-API-Key":
                headers = {"X-API-Key": MAX_TOKEN}
            elif upload_method == "Bearer":
                headers = {"Authorization": f"Bearer {MAX_TOKEN}"}
            else:
                headers = {}
            
            response = requests.post(
                f"{MAX_VOICE_API_URL}/send",
                headers=headers,
                json={
                    "chat_id": chat_id,
                    "voice_file": upload_url,
                    "type": "voice"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Голосовое сообщение успешно отправлено пользователю {chat_id}")
                return True
            else:
                logger.error(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при отправке голоса: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_voice_message_url(message_id: int) -> Optional[str]:
    """
    Получает URL голосового сообщения для скачивания
    
    Args:
        message_id: ID сообщения с голосом
        
    Returns:
        Optional[str]: URL для скачивания или None
    """
    try:
        if not MAX_TOKEN:
            logger.error("❌ MAX_TOKEN не задан")
            return None
        
        auth_methods = [
            {"name": "X-API-Key", "headers": {"X-API-Key": MAX_TOKEN}},
            {"name": "Bearer", "headers": {"Authorization": f"Bearer {MAX_TOKEN}"}}
        ]
        
        for method in auth_methods:
            try:
                response = requests.get(
                    f"{MAX_VOICE_API_URL}/message/{message_id}",
                    headers=method["headers"],
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    voice_url = data.get("voice_url") or data.get("audio_url")
                    if voice_url:
                        logger.info(f"✅ Получен URL голоса через {method['name']}")
                        return voice_url
                elif response.status_code == 401:
                    logger.warning(f"⚠️ Ошибка 401 для {method['name']}")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при получении URL через {method['name']}: {e}")
                continue
        
        logger.error("❌ Не удалось получить URL голосового сообщения")
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении URL голоса: {e}")
        return None


def download_voice_message(voice_url: str) -> Optional[bytes]:
    """
    Скачивает голосовое сообщение по URL
    
    Args:
        voice_url: URL для скачивания
        
    Returns:
        Optional[bytes]: бинарные данные аудио или None
    """
    try:
        response = requests.get(voice_url, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Голосовое сообщение скачано: {len(response.content)} байт")
            return response.content
        else:
            logger.error(f"❌ Ошибка скачивания: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка при скачивании: {e}")
        return None


def get_cached_voice(text: str, voice_id: str, emotion: str = "neutral") -> Optional[bytes]:
    """
    Получает синтезированную речь из кэша
    
    Args:
        text: текст для синтеза
        voice_id: ID голоса
        emotion: эмоция
        
    Returns:
        Optional[bytes]: аудио данные или None
    """
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    
    # Проверяем кэш (храним 1 час)
    if cache_key in _voice_cache:
        cache_time = _voice_cache_time.get(cache_key, 0)
        if time.time() - cache_time < 3600:  # 1 час
            logger.info(f"📦 Используем кэшированный голос для {voice_id}")
            return _voice_cache[cache_key]
    
    return None


def cache_voice(text: str, voice_id: str, emotion: str, audio_data: bytes):
    """
    Сохраняет синтезированную речь в кэш
    
    Args:
        text: текст для синтеза
        voice_id: ID голоса
        emotion: эмоция
        audio_data: аудио данные
    """
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    _voice_cache[cache_key] = audio_data
    _voice_cache_time[cache_key] = time.time()
    
    # Очищаем старый кэш если слишком много
    if len(_voice_cache) > 100:
        oldest_key = min(_voice_cache_time.items(), key=lambda x: x[1])[0]
        del _voice_cache[oldest_key]
        del _voice_cache_time[oldest_key]
        logger.info(f"🧹 Очищен старый кэш: {oldest_key}")


async def send_voice_message_async(
    message: Message,
    text: str,
    mode: str = "coach",
    delete_previous: bool = True,
    parse_mode: str = None
) -> bool:
    """
    Асинхронная отправка голосового сообщения
    
    Args:
        message: сообщение для ответа
        text: текст для озвучивания
        mode: режим общения (coach, psychologist, trainer)
        delete_previous: удалять предыдущее сообщение
        parse_mode: режим парсинга
        
    Returns:
        bool: успешность отправки
    """
    try:
        # Получаем настройки голоса для режима
        voice_config = VOICE_SETTINGS.get(mode, VOICE_SETTINGS["coach"])
        voice_id = voice_config["voice"]
        emotion = voice_config.get("emotion", "neutral")
        
        # Проверяем кэш
        cached_audio = get_cached_voice(text, voice_id, emotion)
        
        if cached_audio:
            # Отправляем из кэша
            success = send_voice_message(message.chat.id, cached_audio)
            if success:
                logger.info(f"✅ Отправлен кэшированный голос для {message.chat.id}")
                return True
        
        # Синтезируем речь через Yandex TTS
        logger.info(f"🎤 Синтез речи для текста: {len(text)} символов, режим: {mode}")
        
        audio_data = await synthesize_speech(
            text=text,
            voice=voice_id,
            emotion=emotion,
            speed=voice_config.get("speed", 1.0),
            format="ogg"
        )
        
        if not audio_data:
            logger.error(f"❌ Не удалось синтезировать речь")
            return False
        
        # Сохраняем в кэш
        cache_voice(text, voice_id, emotion, audio_data)
        
        # Отправляем голосовое сообщение
        success = send_voice_message(message.chat.id, audio_data)
        
        if success:
            logger.info(f"✅ Голосовое сообщение отправлено пользователю {message.chat.id}")
            return True
        else:
            logger.warning(f"⚠️ Не удалось отправить голосовое сообщение пользователю {message.chat.id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голосового сообщения: {e}")
        import traceback
        traceback.print_exc()
        return False


async def handle_voice_message(message: Message, user_id: int):
    """
    Обработчик голосовых сообщений
    
    Args:
        message: сообщение с голосом
        user_id: ID пользователя
    """
    logger.info(f"🎤 Получено голосовое сообщение от пользователя {user_id}")
    
    try:
        # Отправляем статус "печатает"
        await message.chat.send_action(action="typing")
        
        # Получаем URL голосового сообщения
        voice_url = get_voice_message_url(message.message_id)
        
        if not voice_url:
            await safe_send_message(
                message,
                "❌ Не удалось получить голосовое сообщение. Попробуйте позже.",
                delete_previous=True
            )
            return
        
        # Скачиваем голос
        audio_data = download_voice_message(voice_url)
        
        if not audio_data:
            await safe_send_message(
                message,
                "❌ Не удалось загрузить голосовое сообщение.",
                delete_previous=True
            )
            return
        
        # Распознаем голос
        if not DEEPGRAM_API_KEY:
            await safe_send_message(
                message,
                "❌ Сервис распознавания голоса не настроен. Пожалуйста, используйте текст.",
                delete_previous=True
            )
            return
        
        # Используем сервис распознавания
        transcript = await transcribe_audio(audio_data, DEEPGRAM_API_KEY)
        
        if not transcript:
            await safe_send_message(
                message,
                "❌ Не удалось распознать голосовое сообщение. Попробуйте говорить чётче или используйте текст.",
                delete_previous=True
            )
            return
        
        # Отправляем распознанный текст
        status_msg = await safe_send_message(
            message,
            f"🎤 *Распознано:*\n{transcript}\n\n_Обрабатываю..._",
            parse_mode="Markdown",
            delete_previous=True
        )
        
        # Получаем текущий режим пользователя
        from state import get_user_mode
        mode = get_user_mode(user_id)
        
        # Получаем системный промпт для режима
        mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
        system_prompt = mode_config.get("system_prompt", "")
        
        # Формируем запрос к LLM
        from services import get_llm_response
        
        llm_response = await get_llm_response(
            user_id=user_id,
            message=transcript,
            system_prompt=system_prompt,
            mode=mode
        )
        
        if not llm_response:
            await safe_send_message(
                message,
                "❌ Не удалось получить ответ. Попробуйте позже.",
                delete_previous=True
            )
            return
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                await safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        # Отправляем текстовый ответ
        await safe_send_message(
            message,
            llm_response,
            parse_mode=None,
            delete_previous=True
        )
        
        # Если нужно, отправляем голосовой ответ
        if mode_config.get("voice_enabled", True):
            await send_voice_message_async(
                message=message,
                text=llm_response,
                mode=mode,
                delete_previous=False
            )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}")
        import traceback
        traceback.print_exc()
        
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке голосового сообщения. Попробуйте позже.",
            delete_previous=True
        )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'send_voice_message',
    'send_voice_message_async',
    'get_voice_message_url',
    'download_voice_message',
    'handle_voice_message',
    'get_cached_voice',
    'cache_voice'
]
