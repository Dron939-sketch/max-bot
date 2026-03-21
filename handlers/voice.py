#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик голосовых сообщений для MAX
Версия 5.1 - МАКСИМАЛЬНАЯ ДИАГНОСТИКА ВСЕХ ЭТАПОВ
"""

import logging
import tempfile
import os
import asyncio
import requests
import time
import traceback
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

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


# ============================================
# ДИАГНОСТИЧЕСКИЕ ФУНКЦИИ
# ============================================

def log_stage(stage_name: str, data: Dict[str, Any] = None):
    """Логирует этап обработки с красивым форматированием"""
    logger.info("")
    logger.info("█" * 100)
    logger.info(f"🔊🔊🔊 ЭТАП: {stage_name} 🔊🔊🔊")
    logger.info(f"⏰ ВРЕМЯ: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    if data:
        for key, value in data.items():
            # Обрезаем слишком длинные значения
            if isinstance(value, str) and len(value) > 500:
                value = value[:500] + "... [обрезано]"
            logger.info(f"   📌 {key}: {value}")
    logger.info("█" * 100)
    logger.info("")


def log_error(stage_name: str, error: Exception, context: Dict[str, Any] = None):
    """Логирует ошибку"""
    logger.error("")
    logger.error("█" * 100)
    logger.error(f"❌❌❌ ОШИБКА В ЭТАПЕ: {stage_name} ❌❌❌")
    logger.error(f"⏰ ВРЕМЯ: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    logger.error(f"🔍 ОШИБКА: {type(error).__name__}: {error}")
    if context:
        for key, value in context.items():
            logger.error(f"   📌 {key}: {value}")
    logger.error("█" * 100)
    logger.error("")
    traceback.print_exc()


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def send_voice_message(chat_id: int, audio_data: bytes, filename: str = "voice.ogg") -> bool:
    """
    Отправляет голосовое сообщение через официальное API MAX
    Документация: https://dev.max.ru/docs-api/methods/POST/messages
    """
    log_stage("SEND_VOICE_START", {
        "chat_id": chat_id,
        "audio_size": len(audio_data),
        "filename": filename
    })
    
    if not MAX_TOKEN:
        log_error("SEND_VOICE", Exception("MAX_TOKEN не задан"), {})
        return False
    
    headers = {"Authorization": MAX_TOKEN}
    
    for attempt in range(3):
        try:
            # ШАГ 1: Получаем URL для загрузки
            log_stage(f"SEND_VOICE_ATTEMPT_{attempt+1}_STEP1", {
                "action": "requesting upload URL"
            })
            
            response = requests.post(
                f"{MAX_API_BASE_URL}/uploads?type=audio",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                log_error("SEND_VOICE_STEP1", Exception(f"HTTP {response.status_code}"), {
                    "response": response.text[:200]
                })
                continue
            
            data = response.json()
            upload_url = data.get("url")
            upload_token = data.get("token")
            
            if not upload_url or not upload_token:
                log_error("SEND_VOICE_STEP1", Exception("Нет url или token"), {
                    "data": data
                })
                continue
            
            log_stage("SEND_VOICE_STEP1_SUCCESS", {
                "upload_url": upload_url[:50] + "...",
                "upload_token": upload_token[:30] + "..."
            })
            
            # ШАГ 2: Загружаем аудио
            log_stage(f"SEND_VOICE_ATTEMPT_{attempt+1}_STEP2", {
                "action": "uploading audio",
                "size": len(audio_data)
            })
            
            files = {'data': (filename, audio_data, 'audio/ogg')}
            upload_response = requests.post(upload_url, files=files, timeout=60)
            
            if upload_response.status_code not in [200, 201]:
                log_error("SEND_VOICE_STEP2", Exception(f"HTTP {upload_response.status_code}"), {
                    "response": upload_response.text[:200]
                })
                continue
            
            log_stage("SEND_VOICE_STEP2_SUCCESS", {
                "upload_response": upload_response.status_code
            })
            
            time.sleep(2)
            
            # ШАГ 3: Отправляем сообщение
            log_stage(f"SEND_VOICE_ATTEMPT_{attempt+1}_STEP3", {
                "action": "sending message"
            })
            
            message_data = {
                "text": "",
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
                f"{MAX_API_BASE_URL}/messages?chat_id={chat_id}",
                headers=headers,
                json=message_data,
                timeout=30
            )
            
            log_stage("SEND_VOICE_STEP3_RESPONSE", {
                "status_code": send_response.status_code,
                "response_preview": send_response.text[:300]
            })
            
            if send_response.status_code == 400 and "attachment.not.ready" in send_response.text:
                log_stage("SEND_VOICE_RETRY", {"reason": "attachment not ready"})
                time.sleep(2)
                
                send_response = requests.post(
                    f"{MAX_API_BASE_URL}/messages?chat_id={chat_id}",
                    headers=headers,
                    json=message_data,
                    timeout=30
                )
                
                log_stage("SEND_VOICE_RETRY_RESPONSE", {
                    "status_code": send_response.status_code
                })
            
            if send_response.status_code == 200:
                log_stage("SEND_VOICE_SUCCESS", {"attempt": attempt + 1})
                return True
            else:
                log_error("SEND_VOICE_STEP3", Exception(f"HTTP {send_response.status_code}"), {
                    "response": send_response.text[:200]
                })
                continue
                
        except requests.exceptions.Timeout as e:
            log_error("SEND_VOICE_TIMEOUT", e, {"attempt": attempt + 1})
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
        except requests.exceptions.ConnectionError as e:
            log_error("SEND_VOICE_CONNECTION_ERROR", e, {"attempt": attempt + 1})
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
        except Exception as e:
            log_error("SEND_VOICE_UNKNOWN_ERROR", e, {"attempt": attempt + 1})
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    
    log_error("SEND_VOICE_FAILED", Exception("Все попытки исчерпаны"), {})
    return False


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
            except Exception as e:
                logger.warning(f"Ошибка при получении URL (попытка {attempt+1}): {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
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


async def handle_voice_message(message: Message, state=None):
    """
    Обработка голосового сообщения - МАКСИМАЛЬНАЯ ДИАГНОСТИКА
    """
    start_time = time.time()
    user_id = message.from_user.id
    
    log_stage("HANDLE_VOICE_START", {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "has_voice": message.voice is not None
    })
    
    # Проверка наличия голосового сообщения
    if not message.voice:
        log_error("NO_VOICE", Exception("message.voice is None"), {
            "content_type": message.content_type
        })
        await safe_send_message(
            message,
            "❌ Не удалось получить голосовое сообщение. Попробуйте еще раз.",
            delete_previous=True
        )
        return
    
    log_stage("VOICE_INFO", {
        "duration": message.voice.duration,
        "file_id": message.voice.file_id[:30] + "...",
        "content_type": message.content_type
    })
    
    # Получаем данные пользователя
    data = user_data.get(user_id, {})
    user_name = get_user_name(user_id) or "друг"
    
    log_stage("USER_DATA", {
        "user_name": user_name,
        "has_profile_data": bool(data.get("profile_data")),
        "has_ai_profile": bool(data.get("ai_generated_profile")),
        "perception_type": data.get("perception_type", "не определен"),
        "thinking_level": data.get("thinking_level", "не определен"),
        "communication_mode": user_contexts.get(user_id).communication_mode if user_contexts.get(user_id) else "coach"
    })
    
    # Проверка прохождения теста
    def is_test_completed(user_data_dict):
        if user_data_dict.get("profile_data"):
            return True
        if user_data_dict.get("ai_generated_profile"):
            return True
        required = ["perception_type", "thinking_level", "behavioral_levels"]
        if all(field in user_data_dict for field in required):
            return True
        return False
    
    test_completed = is_test_completed(data)
    log_stage("TEST_CHECK", {"test_completed": test_completed})
    
    if not test_completed:
        log_stage("TEST_NOT_COMPLETED", {})
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
    recognized_text = None
    response = None
    
    try:
        # ========== ЭТАП 1: СКАЧИВАНИЕ ФАЙЛА ==========
        log_stage("STEP1_GET_FILE", {"action": "getting file from MAX"})
        
        file_info = await message.bot.get_file(message.voice.file_id)
        log_stage("STEP1_FILE_INFO", {
            "file_path": file_info.file_path,
            "file_size": file_info.file_size
        })
        
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            log_stage("STEP1_TEMP_FILE", {"temp_file": temp_file})
            
            await message.bot.download_file(file_info.file_path, destination=temp_file)
            
            file_size = os.path.getsize(temp_file)
            log_stage("STEP1_DOWNLOAD_COMPLETE", {
                "size_bytes": file_size,
                "size_kb": round(file_size / 1024, 2),
                "file_exists": os.path.exists(temp_file)
            })
            
            if file_size == 0:
                log_error("STEP1_EMPTY_FILE", Exception("Downloaded file is empty"), {})
                await status_msg.edit_text(
                    "❌ Не удалось загрузить голосовое сообщение (пустой файл).\n\n"
                    "Попробуйте еще раз."
                )
                return
        
        # Проверка формата файла
        try:
            with open(temp_file, 'rb') as f:
                header = f.read(4)
                log_stage("STEP1_FILE_HEADER", {
                    "hex": header.hex(),
                    "is_ogg": header == b'OggS'
                })
                if header != b'OggS':
                    log_stage("STEP1_WARNING", {"message": "File may not be in OGG format"})
        except Exception as e:
            log_error("STEP1_HEADER_READ", e, {})
        
        # ========== ЭТАП 2: РАСПОЗНАВАНИЕ РЕЧИ (DEEPGRAM) ==========
        log_stage("STEP2_STT_START", {
            "api_key_configured": bool(DEEPGRAM_API_KEY),
            "temp_file": temp_file
        })
        
        if not DEEPGRAM_API_KEY:
            log_error("STEP2_NO_API_KEY", Exception("DEEPGRAM_API_KEY not configured"), {})
            await status_msg.edit_text(
                "❌ Сервис распознавания голоса не настроен.\n\n"
                "Пожалуйста, используйте текст."
            )
            return
        
        stt_start = time.time()
        recognized_text = await speech_to_text(temp_file)
        stt_duration = time.time() - stt_start
        
        # 🔥 ДИАГНОСТИКА: ЧТО ПРИШЛО С DEEPGRAM
        log_stage("DEEPGRAM_OUTPUT", {
            "raw_text": recognized_text,
            "text_length": len(recognized_text) if recognized_text else 0,
            "is_empty": not recognized_text,
            "first_100_chars": recognized_text[:100] if recognized_text else "None"
        })
        
        log_stage("STEP2_STT_COMPLETE", {
            "text": recognized_text,
            "text_length": len(recognized_text) if recognized_text else 0,
            "duration_seconds": round(stt_duration, 2),
            "success": recognized_text is not None and len(recognized_text) > 2
        })
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file)
            log_stage("STEP2_TEMP_CLEANUP", {"file_deleted": temp_file})
        except Exception as e:
            log_error("STEP2_TEMP_CLEANUP_ERROR", e, {"file": temp_file})
        
        if not recognized_text or len(recognized_text.strip()) < 2:
            log_stage("STEP2_STT_FAILED", {"recognized_text": recognized_text})
            await status_msg.edit_text(
                "❌ Не удалось распознать речь\n\n"
                "Возможные причины:\n"
                "• Говорите чётче и громче\n"
                "• Убедитесь, что микрофон работает\n"
                "• Попробуйте написать текстом"
            )
            return
        
        # ========== ЭТАП 3: АНАЛИЗ ВОПРОСА ==========
        log_stage("STEP3_ANALYSIS_START", {})
        
        await status_msg.edit_text(
            f"📝 Распознано: {recognized_text[:100]}...\n\n"
            "🧠 Анализирую вопрос..."
        )
        
        analyzer = create_analyzer_from_user_data(data, user_name)
        reflection = ""
        if analyzer:
            reflection = analyzer.get_reflection_text(recognized_text)
            log_stage("STEP3_ANALYSIS_COMPLETE", {
                "reflection": reflection[:200] + "..." if len(reflection) > 200 else reflection
            })
        else:
            log_stage("STEP3_NO_ANALYZER", {})
        
        # ========== ЭТАП 4: ПОЛУЧЕНИЕ РЕЖИМА И КОНТЕКСТА ==========
        context = user_contexts.get(user_id)
        mode_name = context.communication_mode if context else "coach"
        mode_config = COMMUNICATION_MODES.get(mode_name, COMMUNICATION_MODES["coach"])
        system_prompt = mode_config.get("system_prompt", "")
        
        profile_data = data.get("profile_data", {})
        scores = {}
        for k in VECTORS:
            levels = data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        # Формируем контекст
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
        
        if reflection:
            context_text += f"\nГлубинный анализ вопроса:\n{reflection}\n"
        
        log_stage("STEP4_CONTEXT_BUILT", {
            "mode": mode_name,
            "profile": profile_data.get('display_name', 'не определен'),
            "perception": data.get('perception_type', 'не определен'),
            "thinking_level": data.get('thinking_level', 5),
            "context_text_length": len(context_text),
            "system_prompt_length": len(system_prompt)
        })
        
        # ========== ЭТАП 5: ВЫЗОВ DEEPSEEK ==========
        await status_msg.edit_text(
            f"📝 Распознано: {recognized_text[:100]}...\n\n"
            "🧠 Формирую ответ с учётом твоего профиля..."
        )
        
        prompt = f"""
Вопрос пользователя: {recognized_text}

{context_text}

Ответь пользователю в соответствии с твоей ролью.
"""
        
        log_stage("STEP5_DEEPSEEK_START", {
            "prompt_length": len(prompt),
            "system_prompt_length": len(system_prompt),
            "max_tokens": 1000,
            "temperature": 0.7,
            "prompt_preview": prompt[:300] + "..."
        })
        
        deepseek_start = time.time()
        response = await call_deepseek(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        deepseek_duration = time.time() - deepseek_start
        
        # 🔥 ДИАГНОСТИКА: ЧТО ПРИШЛО С DEEPSEEK
        log_stage("DEEPSEEK_OUTPUT", {
            "raw_response": response,
            "response_length": len(response) if response else 0,
            "is_empty": not response,
            "first_200_chars": response[:200] if response else "None"
        })
        
        log_stage("STEP5_DEEPSEEK_COMPLETE", {
            "response_preview": response[:200] + "..." if response and len(response) > 200 else response,
            "response_length": len(response) if response else 0,
            "duration_seconds": round(deepseek_duration, 2),
            "success": response is not None
        })
        
        if not response:
            response = "Извините, я немного задумался. Можете повторить вопрос?"
        
        # Сохраняем в историю
        history = data.get('history', [])
        history.append({"role": "user", "content": recognized_text})
        history.append({"role": "assistant", "content": response})
        data["history"] = history
        user_data[user_id] = data
        
        # Сохраняем в БД
        try:
            from db_sync import sync_db
            sync_db.save_user_to_db(user_id)
            log_stage("STEP5_DB_SAVE", {"success": True})
        except Exception as e:
            log_error("STEP5_DB_SAVE", e, {})
        
        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
            log_stage("STEP5_STATUS_DELETED", {})
        except Exception as e:
            log_error("STEP5_STATUS_DELETE", e, {})
        
        # ========== ЭТАП 6: ОТПРАВКА ТЕКСТОВОГО ОТВЕТА ==========
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎤 ЗАДАТЬ ЕЩЁ", callback_data="ask_question"),
                InlineKeyboardButton(text="🎯 К ЦЕЛИ", callback_data="show_dynamic_destinations")
            ],
            [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought")],
            [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
        ])
        
        log_stage("STEP6_TEXT_SEND", {
            "text_length": len(response),
            "user_id": user_id,
            "text_to_send": response
        })
        
        await safe_send_message(
            message,
            f"📝 <b>Вы сказали:</b>\n{recognized_text}\n\n"
            f"{mode_config['emoji']} <b>Ответ:</b>\n{response}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        
        log_stage("STEP6_TEXT_SENT", {"success": True})
        
        # ========== ЭТАП 7: СИНТЕЗ РЕЧИ (YANDEX TTS) ==========
        audio_text = response
        if len(audio_text) > 500:
            audio_text = audio_text[:500] + "..."
        
        # 🔥 ДИАГНОСТИКА: ЧТО ОТПРАВЛЯЕМ НА ОЗВУЧКУ
        log_stage("TTS_INPUT", {
            "text_for_tts": audio_text,
            "text_length": len(audio_text),
            "mode": mode_name,
            "voice": mode_config.get("voice", "filipp"),
            "emotion": mode_config.get("voice_emotion", "neutral")
        })
        
        log_stage("STEP7_TTS_START", {
            "text_length": len(audio_text),
            "mode": mode_name,
            "voice": mode_config.get("voice", "filipp")
        })
        
        tts_start = time.time()
        audio_data = await text_to_speech(audio_text, mode_name)
        tts_duration = time.time() - tts_start
        
        log_stage("STEP7_TTS_COMPLETE", {
            "audio_size_bytes": len(audio_data) if audio_data else 0,
            "duration_seconds": round(tts_duration, 2),
            "success": audio_data is not None
        })
        
        if audio_data:
            # ========== ЭТАП 8: ОТПРАВКА ГОЛОСОВОГО ОТВЕТА ==========
            log_stage("STEP8_VOICE_SEND_START", {
                "audio_size": len(audio_data),
                "chat_id": message.chat.id
            })
            
            voice_send_start = time.time()
            success = send_voice_message(message.chat.id, audio_data, "response.ogg")
            voice_send_duration = time.time() - voice_send_start
            
            log_stage("STEP8_VOICE_SEND_COMPLETE", {
                "success": success,
                "duration_seconds": round(voice_send_duration, 2)
            })
            
            if success:
                log_stage("VOICE_PROCESSING_SUCCESS", {
                    "total_duration_seconds": round(time.time() - start_time, 2),
                    "stt_duration": round(stt_duration, 2),
                    "deepseek_duration": round(deepseek_duration, 2),
                    "tts_duration": round(tts_duration, 2),
                    "send_duration": round(voice_send_duration, 2),
                    "recognized_text": recognized_text,
                    "deepseek_response": response,
                    "tts_text": audio_text
                })
            else:
                log_error("STEP8_VOICE_SEND_FAILED", Exception("send_voice_message returned False"), {})
        else:
            log_error("STEP7_TTS_FAILED", Exception("text_to_speech returned None"), {
                "text": audio_text[:100],
                "mode": mode_name
            })
        
        # Устанавливаем состояние
        set_state(user_id, TestStates.awaiting_question)
        
    except Exception as e:
        log_error("VOICE_PROCESSING", e, {
            "user_id": user_id,
            "temp_file": temp_file,
            "recognized_text": recognized_text[:100] if recognized_text else None,
            "response": response[:100] if response else None
        })
        
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
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'__(.*?)__', r'\1', clean_text)
        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)
        clean_text = re.sub(r'_(.*?)_', r'\1', clean_text)
        
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        
        log_stage("SEND_VOICE_RESPONSE_START", {
            "text_length": len(clean_text),
            "mode": mode,
            "original_text": text[:100]
        })
        
        audio_data = await text_to_speech(clean_text, mode)
        
        if audio_data:
            success = send_voice_message(message.chat.id, audio_data, "response.ogg")
            log_stage("SEND_VOICE_RESPONSE_COMPLETE", {
                "success": success,
                "audio_size": len(audio_data)
            })
        else:
            log_error("SEND_VOICE_RESPONSE", Exception("text_to_speech failed"), {
                "text": clean_text[:100]
            })
            
    except Exception as e:
        log_error("SEND_VOICE_RESPONSE", e, {})


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
    'cache_voice',
    'log_stage',
    'log_error'
]
