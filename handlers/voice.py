#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик голосовых сообщений для MAX
Версия 4.1 - ИСПРАВЛЕНО: добавлен chat_id при отправке сообщения
"""

import logging
import tempfile
import os
import asyncio
import requests
import time
import traceback
from typing import Optional, Dict, Any, List

from maxibot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import MAX_TOKEN, DEEPGRAM_API_KEY, YANDEX_API_KEY, VOICE_SETTINGS, COMMUNICATION_MODES, MAX_API_BASE_URL
from message_utils import safe_send_message, safe_delete_message
from services import speech_to_text, text_to_speech, call_deepseek
from state import user_data, user_contexts, get_state, set_state, TestStates, get_user_name
from question_analyzer import create_analyzer_from_user_data
from profiles import VECTORS

logger = logging.getLogger(__name__)

# Кэш для синтезированной речи
_voice_cache = {}
_voice_cache_time = {}


def send_voice_message(chat_id: int, audio_data: bytes, filename: str = "voice.ogg") -> bool:
    """
    Отправляет голосовое сообщение через официальное API MAX
    Документация: https://platform-api.max.ru/docs
    """
    if not MAX_TOKEN:
        logger.error("❌ MAX_TOKEN не задан в .env файле")
        return False
    
    # ✅ ПРАВИЛЬНЫЙ формат авторизации
    headers = {"Authorization": MAX_TOKEN}
    
    # 3 попытки
    for attempt in range(3):
        try:
            # ШАГ 1: Получаем URL для загрузки
            logger.info(f"📡 Попытка {attempt + 1}/3: запрос URL для загрузки аудио")
            response = requests.post(
                f"{MAX_API_BASE_URL}/uploads?type=audio",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Ошибка получения URL: {response.status_code} - {response.text}")
                continue
            
            data = response.json()
            upload_url = data.get("url")
            upload_token = data.get("token")
            
            if not upload_url or not upload_token:
                logger.error("❌ Нет url или token в ответе")
                continue
            
            logger.info(f"✅ Получен URL для загрузки")
            
            # ШАГ 2: Загружаем аудио
            logger.info(f"📡 Загрузка аудио ({len(audio_data)} байт)...")
            
            files = {
                'data': (filename, audio_data, 'audio/ogg')
            }
            
            upload_response = requests.post(
                upload_url,
                files=files,
                timeout=60
            )
            
            if upload_response.status_code not in [200, 201]:
                logger.error(f"❌ Ошибка загрузки: {upload_response.status_code} - {upload_response.text}")
                continue
            
            logger.info(f"✅ Аудио успешно загружено")
            
            # Небольшая пауза для обработки файла на сервере
            time.sleep(1)
            
            # ШАГ 3: Отправляем сообщение с вложением
            logger.info(f"📡 Отправка сообщения")
            
            # ✅ ИСПРАВЛЕНО: добавлен chat_id
            message_data = {
                "chat_id": chat_id,  # ← КЛЮЧЕВОЕ ПОЛЕ!
                "text": "",  # Пустой текст для голосового сообщения
                "attachments": [
                    {
                        "type": "audio",
                        "payload": {
                            "token": upload_token
                        }
                    }
                ]
            }
            
            send_response = requests.post(
                f"{MAX_API_BASE_URL}/messages",
                headers=headers,
                json=message_data,
                timeout=30
            )
            
            if send_response.status_code == 200:
                logger.info(f"✅ Голосовое сообщение отправлено")
                return True
            else:
                logger.error(f"❌ Ошибка отправки: {send_response.status_code} - {send_response.text}")
                continue
                
        except requests.exceptions.Timeout as e:
            logger.warning(f"⚠️ Таймаут (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"⚠️ Ошибка соединения (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logger.error(f"❌ Ошибка (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    
    logger.error("❌ Не удалось отправить голосовое сообщение после 3 попыток")
    return False


# Алиас для совместимости
send_voice_to_max = send_voice_message


def get_voice_message_url(message_id: int) -> Optional[str]:
    """Получает URL голосового сообщения"""
    try:
        if not MAX_TOKEN:
            return None
        
        headers = {"Authorization": MAX_TOKEN}
        
        for attempt in range(3):
            try:
                response = requests.get(
                    f"{MAX_API_BASE_URL}/messages/{message_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    attachments = data.get("attachments", [])
                    for attachment in attachments:
                        if attachment.get("type") == "audio":
                            return attachment.get("payload", {}).get("url")
                elif response.status_code == 401:
                    logger.warning(f"⚠️ Ошибка 401 при получении URL")
                else:
                    logger.warning(f"⚠️ Статус {response.status_code} при получении URL")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Таймаут при получении URL (попытка {attempt + 1}/3)")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"❌ Ошибка при получении URL: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
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
        logger.error(f"❌ Ошибка скачивания: {e}")
        return None


async def handle_voice_message(message: Message, state):
    """
    Обработка голосового сообщения - ИСПРАВЛЕННАЯ ВЕРСИЯ
    Использует правильное API MAX и передает system_prompt
    """
    user_id = message.from_user.id
    
    # 🔍 ОТЛАДКА: проверяем наличие голосового сообщения
    if not message.voice:
        logger.error("❌ Нет голосового сообщения в message")
        await safe_send_message(
            message,
            "❌ Не удалось получить голосовое сообщение. Попробуйте еще раз.",
            delete_previous=True
        )
        return
    
    logger.info(f"🎤 Получено голосовое сообщение от {user_id}")
    logger.info(f"📊 Информация о голосе: duration={message.voice.duration}s, file_id={message.voice.file_id[:20]}...")
    
    # Получаем данные пользователя
    data = user_data.get(user_id, {})
    user_name = get_user_name(user_id) or "друг"
    
    # Проверяем, пройден ли тест
    def is_test_completed(user_data_dict):
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
        logger.info("📥 Получаем файл голосового сообщения...")
        file_info = await message.bot.get_file(message.voice.file_id)
        logger.info(f"📁 file_info: path={file_info.file_path}, size={file_info.file_size}")
        
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            logger.info(f"💾 Создан временный файл: {temp_file}")
            await message.bot.download_file(file_info.file_path, destination=temp_file)
            
            # Проверяем размер скачанного файла
            file_size = os.path.getsize(temp_file)
            logger.info(f"📊 Скачано {file_size} байт")
            
            if file_size == 0:
                logger.error("❌ Скачан пустой файл")
                await status_msg.edit_text(
                    "❌ Не удалось загрузить голосовое сообщение (пустой файл).\n\n"
                    "Попробуйте еще раз."
                )
                return
        
        # ============================================
        # ДИАГНОСТИКА ПЕРЕД РАСПОЗНАВАНИЕМ
        # ============================================
        logger.info(f"🔑 DEEPGRAM_API_KEY настроен: {'✅' if DEEPGRAM_API_KEY else '❌'}")
        
        if not DEEPGRAM_API_KEY:
            logger.error("❌ DEEPGRAM_API_KEY не настроен")
            await status_msg.edit_text(
                "❌ Сервис распознавания голоса не настроен.\n\n"
                "Пожалуйста, используйте текст."
            )
            return
        
        # ✅ ДОБАВЛЯЕМ ЛОГИ ПЕРЕД ВЫЗОВОМ
        logger.info(f"🎤 ДО ВЫЗОВА speech_to_text, temp_file={temp_file}")
        logger.info(f"🎤 Файл существует: {os.path.exists(temp_file)}")
        logger.info(f"🎤 Размер файла: {os.path.getsize(temp_file)} байт")
        
        # Проверяем заголовок файла (первые 4 байта)
        try:
            with open(temp_file, 'rb') as f:
                header = f.read(4)
                logger.info(f"📊 Заголовок файла (hex): {header.hex()}")
                if header == b'OggS':
                    logger.info("✅ Файл в формате OGG")
                else:
                    logger.warning(f"⚠️ Файл НЕ в формате OGG! Заголовок: {header}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось прочитать заголовок файла: {e}")
        
        logger.info(f"🎙 Вызов speech_to_text для файла: {temp_file}")
        recognized_text = await speech_to_text(temp_file)
        
        # ✅ ДОБАВЛЯЕМ ЛОГИ ПОСЛЕ ВЫЗОВА
        logger.info(f"🎤 ПОСЛЕ ВЫЗОВА speech_to_text, recognized_text='{recognized_text}'")
        logger.info(f"🔍 РАСПОЗНАННЫЙ ТЕКСТ: '{recognized_text}'")
        logger.info(f"🔍 ТИП: {type(recognized_text)}")
        logger.info(f"🔍 ДЛИНА ТЕКСТА: {len(recognized_text) if recognized_text else 0}")
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file)
            logger.info(f"🗑️ Временный файл удалён: {temp_file}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        if not recognized_text or len(recognized_text.strip()) < 2:
            logger.warning(f"⚠️ Пустой или слишком короткий текст распознавания: '{recognized_text}'")
            await status_msg.edit_text(
                "❌ Не удалось распознать речь\n\n"
                "Возможные причины:\n"
                "• Говорите чётче и громче\n"
                "• Убедитесь, что микрофон работает\n"
                "• Попробуйте написать текстом"
            )
            return
        
        # Обновляем статусное сообщение
        await status_msg.edit_text(
            f"📝 Распознано: {recognized_text[:100]}...\n\n"
            "🧠 Анализирую вопрос...\n\n"
            "🔍 Использую конфайнтмент-модель..."
        )
        
        # СОЗДАЁМ АНАЛИЗАТОР ВОПРОСА
        analyzer = create_analyzer_from_user_data(data, user_name)
        
        # Получаем глубинный анализ вопроса
        reflection = ""
        if analyzer:
            reflection = analyzer.get_reflection_text(recognized_text)
            logger.info(f"🔍 Глубинный анализ вопроса: {reflection[:200]}...")
        
        # Получаем текущий режим пользователя
        context = user_contexts.get(user_id)
        mode_name = context.communication_mode if context else "coach"
        
        # ✅ ПОЛУЧАЕМ system_prompt ИЗ КОНФИГА
        mode_config = COMMUNICATION_MODES.get(mode_name, COMMUNICATION_MODES["coach"])
        system_prompt = mode_config.get("system_prompt", "")
        
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
        
        # Формируем промпт для DeepSeek
        prompt = f"""
Вопрос пользователя: {recognized_text}

{context_text}

Ответь пользователю в соответствии с твоей ролью.
"""
        
        # ✅ ВЫЗЫВАЕМ DeepSeek С system_prompt
        logger.info(f"📝 Вызов DeepSeek с system_prompt ({len(system_prompt)} символов)")
        response = await call_deepseek(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        
        if not response:
            response = "Извините, я немного задумался. Можете повторить вопрос?"
        
        # Сохраняем в историю
        history = data.get('history', [])
        history.append({"role": "user", "content": recognized_text})
        history.append({"role": "assistant", "content": response})
        data["history"] = history
        user_data[user_id] = data
        
        # Сохраняем в БД
        from db_sync import sync_db
        sync_db.save_user_to_db(user_id)
        
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
        
        # Очищаем ответ от форматирования
        clean_response = response
        
        # Отправляем текстовый ответ
        logger.info(f"📝 Отправляем текстовый ответ пользователю {user_id}")
        
        await safe_send_message(
            message,
            f"📝 <b>Вы сказали:</b>\n{recognized_text}\n\n"
            f"{mode_config['emoji']} <b>Ответ:</b>\n{clean_response}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        
        # ✅ ОТПРАВЛЯЕМ ГОЛОСОВОЙ ОТВЕТ ЧЕРЕЗ MAX API
        audio_text = clean_response
        if len(audio_text) > 500:
            audio_text = audio_text[:500] + "..."
        
        logger.info(f"🎤 Синтезируем речь для ответа ({len(audio_text)} символов)...")
        audio_data = await text_to_speech(audio_text, mode_name)
        
        if audio_data:
            logger.info(f"✅ Речь синтезирована: {len(audio_data)} байт")
            
            # Отправляем через MAX API
            success = send_voice_message(message.chat.id, audio_data, "response.ogg")
            
            if success:
                logger.info(f"🎙 Голосовой ответ отправлен пользователю {user_id}")
            else:
                logger.error(f"❌ Не удалось отправить голосовой ответ через MAX API")
        else:
            logger.error(f"❌ Не удалось синтезировать речь")
        
        # Устанавливаем состояние
        set_state(user_id, TestStates.awaiting_question)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}")
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
    """Отправляет голосовой ответ через MAX API"""
    try:
        import re
        clean_text = text
        # Очищаем от Markdown и HTML
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'__(.*?)__', r'\1', clean_text)
        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)
        clean_text = re.sub(r'_(.*?)_', r'\1', clean_text)
        
        # Ограничиваем длину
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        
        audio_data = await text_to_speech(clean_text, mode)
        
        if audio_data:
            success = send_voice_message(message.chat.id, audio_data, "response.ogg")
            if success:
                logger.info(f"✅ Голосовой ответ отправлен через MAX API")
            else:
                logger.warning(f"⚠️ Не удалось отправить голос через MAX API")
        else:
            logger.warning(f"⚠️ Не удалось синтезировать речь")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке голосового ответа: {e}")


def get_cached_voice(text: str, voice_id: str, emotion: str = "neutral") -> Optional[bytes]:
    """Получает синтезированную речь из кэша"""
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    
    if cache_key in _voice_cache:
        cache_time = _voice_cache_time.get(cache_key, 0)
        if time.time() - cache_time < 3600:
            logger.info(f"📦 Используем кэшированный голос")
            return _voice_cache[cache_key]
    
    return None


def cache_voice(text: str, voice_id: str, emotion: str, audio_data: bytes):
    """Сохраняет синтезированную речь в кэш"""
    cache_key = f"{voice_id}_{emotion}_{hash(text)}"
    _voice_cache[cache_key] = audio_data
    _voice_cache_time[cache_key] = time.time()
    
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
    'send_voice_to_max',
    'handle_voice_message',
    'send_voice_response',
    'get_voice_message_url',
    'download_voice_message',
    'get_cached_voice',
    'cache_voice'
]
