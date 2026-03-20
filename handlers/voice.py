#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик голосовых сообщений для MAX
Версия 3.2 - С ИСПОЛЬЗОВАНИЕМ QUESTION_ANALYZER
"""

import logging
import tempfile
import os
import asyncio
import requests
import time
from typing import Optional, Dict, Any, List

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import MAX_TOKEN, DEEPGRAM_API_KEY, YANDEX_API_KEY, VOICE_SETTINGS, COMMUNICATION_MODES
from message_utils import safe_send_message, safe_delete_message
from services import speech_to_text, text_to_speech
from state import user_data, user_contexts, get_state, set_state, TestStates, get_user_name
from modes import get_mode
from question_analyzer import create_analyzer_from_user_data
from profiles import VECTORS

logger = logging.getLogger(__name__)

# Кэш для синтезированной речи
_voice_cache = {}
_voice_cache_time = {}


def send_voice_message(chat_id: int, audio_data: bytes, filename: str = "voice.ogg") -> bool:
    """
    Отправляет голосовое сообщение через API MAX
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
                        "https://api.max.ru/v1/voice/upload",
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
                        "https://api.max.ru/v1/voice/upload",
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
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при запросе через {method['name']}: {e}")
                continue
        
        if not upload_url:
            logger.error("❌ Не удалось получить URL для загрузки")
            return False
        
        # ШАГ 2: Загружаем аудио
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
        
        # ШАГ 3: Отправляем сообщение
        logger.info(f"📡 ШАГ 3: отправляем сообщение с голосом...")
        
        try:
            if upload_method == "X-API-Key":
                headers = {"X-API-Key": MAX_TOKEN}
            elif upload_method == "Bearer":
                headers = {"Authorization": f"Bearer {MAX_TOKEN}"}
            else:
                headers = {}
            
            response = requests.post(
                "https://api.max.ru/v1/voice/send",
                headers=headers,
                json={
                    "chat_id": chat_id,
                    "voice_file": upload_url,
                    "type": "voice"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Голосовое сообщение отправлено")
                return True
            else:
                logger.error(f"❌ Ошибка отправки: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return False


def get_voice_message_url(message_id: int) -> Optional[str]:
    """Получает URL голосового сообщения"""
    try:
        if not MAX_TOKEN:
            return None
        
        auth_methods = [
            {"name": "X-API-Key", "headers": {"X-API-Key": MAX_TOKEN}},
            {"name": "Bearer", "headers": {"Authorization": f"Bearer {MAX_TOKEN}"}}
        ]
        
        for method in auth_methods:
            try:
                response = requests.get(
                    f"https://api.max.ru/v1/voice/message/{message_id}",
                    headers=method["headers"],
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    voice_url = data.get("voice_url") or data.get("audio_url")
                    if voice_url:
                        logger.info(f"✅ Получен URL голоса")
                        return voice_url
                        
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None


def download_voice_message(voice_url: str) -> Optional[bytes]:
    """Скачивает голосовое сообщение"""
    try:
        response = requests.get(voice_url, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Голос скачан: {len(response.content)} байт")
            return response.content
        else:
            logger.error(f"❌ Ошибка скачивания: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None


async def handle_voice_message(message: Message, state):
    """
    Обработка голосового сообщения - С ИСПОЛЬЗОВАНИЕМ QUESTION_ANALYZER
    
    Алгоритм:
    1. Проверяем, пройден ли тест
    2. Сохраняем голос во временный файл
    3. Распознаём речь через Deepgram
    4. Создаём анализатор вопроса (конфайнмент-модель)
    5. Получаем глубинный анализ вопроса
    6. Получаем текущий режим пользователя
    7. Обрабатываем текст через режим (коуч/психолог/тренер) с учётом анализа
    8. Отправляем текстовый ответ
    9. Отправляем голосовой ответ
    """
    user_id = message.from_user.id
    
    # Получаем данные пользователя
    data = user_data.get(user_id, {})
    user_name = get_user_name(user_id) or "друг"
    
    # Проверяем, пройден ли тест
    def is_test_completed(user_data_dict):
        """Проверяет, завершен ли тест"""
        if user_data_dict.get("profile_data"):
            return True
        if user_data_dict.get("ai_generated_profile"):
            return True
        required = ["perception_type", "thinking_level", "behavioral_levels"]
        if all(field in user_data_dict for field in required):
            return True
        return False
    
    if not is_test_completed(data):
        await safe_send_message(
            message,
            "🎙 Голосовые сообщения доступны только после завершения теста.\n\n"
            "Пожалуйста, пройдите тест с помощью команды /start",
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
        file_info = await message.bot.get_file(message.voice.file_id)
        
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            await message.bot.download_file(file_info.file_path, destination=temp_file)
        
        # Распознаём речь
        if not DEEPGRAM_API_KEY:
            await status_msg.edit_text(
                "❌ Сервис распознавания голоса не настроен.\n\n"
                "Пожалуйста, используйте текст."
            )
            return
        
        recognized_text = await speech_to_text(temp_file)
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file)
        except:
            pass
        
        if not recognized_text:
            await status_msg.edit_text(
                "❌ Не удалось распознать речь\n\n"
                "Попробуйте еще раз или напишите текстом."
            )
            return
        
        # Обновляем статусное сообщение
        await status_msg.edit_text(
            f"📝 Распознано: {recognized_text[:100]}...\n\n"
            "🧠 Анализирую вопрос...\n\n"
            "🔍 Использую конфайнтмент-модель..."
        )
        
        # 🔥 СОЗДАЁМ АНАЛИЗАТОР ВОПРОСА (как в оригинальном коде)
        analyzer = create_analyzer_from_user_data(data, user_name)
        
        # Получаем глубинный анализ вопроса
        reflection = ""
        if analyzer:
            reflection = analyzer.get_reflection_text(recognized_text)
            logger.info(f"🔍 Глубинный анализ вопроса: {reflection[:200]}...")
        
        # Получаем текущий режим пользователя
        context = user_contexts.get(user_id)
        mode_name = context.communication_mode if context else "coach"
        
        # Получаем данные профиля для контекста
        profile_data = data.get("profile_data", {})
        scores = {}
        for k in VECTORS:
            levels = data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        # Формируем контекст для ответа
        context_text = f"Профиль пользователя: {profile_data.get('display_name', 'не определен')}\n"
        context_text += f"Тип восприятия: {data.get('perception_type', 'не определен')}\n"
        context_text += f"Уровень мышления: {data.get('thinking_level', 5)}/9\n"
        
        if scores:
            weakest = min(scores.items(), key=lambda x: x[1])
            strongest = max(scores.items(), key=lambda x: x[1])
            vector_names = {"СБ": "реакция на давление", "ТФ": "отношение к деньгам", 
                           "УБ": "понимание мира", "ЧВ": "отношения с людьми"}
            context_text += f"Зона роста: {vector_names.get(weakest[0], weakest[0])}\n"
            context_text += f"Сильная сторона: {vector_names.get(strongest[0], strongest[0])}\n"
        
        # Добавляем анализ в контекст
        if reflection:
            context_text += f"\nГлубинный анализ вопроса:\n{reflection}\n"
            context_text += "ВАЖНО: В ответе НЕ ДАВАЙ СОВЕТОВ И ИНСТРУКЦИЙ. Просто отрази то, что видишь."
        
        # Обновляем статусное сообщение
        await status_msg.edit_text(
            f"📝 Распознано: {recognized_text[:100]}...\n\n"
            "🧠 Формирую ответ с учётом твоего профиля..."
        )
        
        # Создаём режим и обрабатываем вопрос с учётом контекста
        mode = get_mode(mode_name, user_id, data, context)
        
        # Если есть анализатор, добавляем рефлексию в историю для контекста
        if analyzer and reflection:
            # Временно добавляем анализ в историю для лучшего ответа
            temp_history = mode.history.copy() if hasattr(mode, 'history') else []
            # Используем стандартный процесс вопроса
            result = mode.process_question(recognized_text)
        else:
            result = mode.process_question(recognized_text)
        
        response = result["response"]
        
        # Обновляем данные с новой историей
        if hasattr(mode, 'history'):
            data['history'] = mode.history
            user_data[user_id] = data
        
        # Очищаем ответ от форматирования
        clean_response = response
        
        # Удаляем статусное сообщение
        await status_msg.delete()
        
        # Создаём клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎤 ЗАДАТЬ ЕЩЁ", callback_data="ask_question"),
                InlineKeyboardButton(text="🎯 К ЦЕЛИ", callback_data="show_dynamic_destinations")
            ],
            [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought")],
            [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
        ])
        
        # Добавляем предложения, если есть
        suggestions_text = ""
        if result.get("suggestions"):
            suggestions_text = "\n\n" + "\n".join(result["suggestions"])
        
        # Добавляем рефлексию, если есть и не включена в ответ
        if reflection and "анализ" not in clean_response.lower() and "вижу" not in clean_response.lower():
            reflection_text = f"\n\n🔍 {reflection}"
        else:
            reflection_text = ""
        
        # Отправляем текстовый ответ
        mode_config = COMMUNICATION_MODES.get(mode_name, COMMUNICATION_MODES["coach"])
        
        await safe_send_message(
            message,
            f"📝 <b>Вы сказали:</b>\n{recognized_text}\n\n"
            f"{mode_config['emoji']} <b>Ответ:</b>\n{clean_response}{suggestions_text}{reflection_text}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        
        # Отправляем голосовой ответ (без рефлексии, чтобы не перегружать)
        audio_text = clean_response
        if len(audio_text) > 500:
            audio_text = audio_text[:500] + "..."
        
        audio_data = await text_to_speech(audio_text, mode_name)
        if audio_data:
            from maxibot.types import BufferedInputFile
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption=f"🎙 Голосовой ответ ({mode_config['display_name']})"
            )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}")
        import traceback
        traceback.print_exc()
        
        if status_msg:
            try:
                await status_msg.delete()
            except:
                pass
        
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке голосового сообщения.\n\n"
            "Попробуйте еще раз или напишите текстом.",
            delete_previous=True
        )


async def send_voice_response(message: Message, text: str, mode: str = "coach"):
    """
    Отправляет голосовой ответ (синтезирует речь и отправляет)
    """
    try:
        # Очищаем текст от HTML и Markdown для синтеза
        import re
        clean_text = text
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'__(.*?)__', r'\1', clean_text)
        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)
        clean_text = re.sub(r'_(.*?)_', r'\1', clean_text)
        
        # Синтезируем речь
        audio_data = await text_to_speech(clean_text, mode)
        
        if audio_data:
            from maxibot.types import BufferedInputFile
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            
            mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
            await message.answer_voice(
                audio_file,
                caption=f"🎙 {mode_config['emoji']} {mode_config['name']}"
            )
            logger.info(f"✅ Голосовой ответ отправлен, режим: {mode}")
        else:
            logger.warning(f"⚠️ Не удалось синтезировать речь для режима {mode}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голосового ответа: {e}")


def get_cached_voice(text: str, voice_id: str, emotion: str = "neutral") -> Optional[bytes]:
    """Получает синтезированную речь из кэша"""
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    
    if cache_key in _voice_cache:
        cache_time = _voice_cache_time.get(cache_key, 0)
        if time.time() - cache_time < 3600:  # 1 час
            logger.info(f"📦 Используем кэшированный голос")
            return _voice_cache[cache_key]
    
    return None


def cache_voice(text: str, voice_id: str, emotion: str, audio_data: bytes):
    """Сохраняет синтезированную речь в кэш"""
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    _voice_cache[cache_key] = audio_data
    _voice_cache_time[cache_key] = time.time()
    
    # Очищаем старый кэш
    if len(_voice_cache) > 100:
        oldest_key = min(_voice_cache_time.items(), key=lambda x: x[1])[0]
        del _voice_cache[oldest_key]
        del _voice_cache_time[oldest_key]
        logger.info(f"🧹 Очищен старый кэш")


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'send_voice_message',
    'handle_voice_message',
    'send_voice_response',
    'get_voice_message_url',
    'download_voice_message',
    'get_cached_voice',
    'cache_voice'
]
