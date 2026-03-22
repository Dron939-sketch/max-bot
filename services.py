#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервисные функции для работы с API и генерации ответов
Версия 9.8.3 - С ДИАГНОСТИКОЙ speech_to_text
"""

import os
import json
import logging
import asyncio
import re
import sys
import traceback
import httpx
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime

from config import (
    DEEPSEEK_API_KEY,
    DEEPGRAM_API_KEY,
    YANDEX_API_KEY,
    OPENWEATHER_API_KEY,
    DEEPSEEK_API_URL,
    DEEPGRAM_API_URL,
    YANDEX_TTS_API_URL
)

logger = logging.getLogger(__name__)


# ========== ГЛОБАЛЬНЫЙ КЛИЕНТ ДЛЯ HTTPX ==========
_http_client = None
_client_lock = asyncio.Lock()
_current_loop_id = None

async def get_http_client():
    """
    Возвращает глобальный HTTPX клиент для всех API-вызовов.
    Создает новый клиент, если цикл изменился.
    """
    global _http_client, _current_loop_id
    
    try:
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
    except RuntimeError:
        # Нет запущенного цикла - создаем временный
        current_loop_id = None
    
    # Если клиент существует и цикл не изменился - используем его
    if _http_client is not None and _current_loop_id == current_loop_id:
        return _http_client
    
    # Иначе создаем новый клиент
    async with _client_lock:
        # Проверяем еще раз после получения блокировки
        if _http_client is not None and _current_loop_id == current_loop_id:
            return _http_client
        
        # Закрываем старый клиент, если есть
        if _http_client is not None:
            try:
                await _http_client.aclose()
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при закрытии старого клиента: {e}")
        
        logger.info(f"🔄 Создаём новый HTTPX клиент для цикла {current_loop_id}")
        
        # Настройки лимитов соединений
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=50,
            keepalive_expiry=30
        )
        
        # Настройки таймаутов
        timeouts = httpx.Timeout(
            connect=30.0,
            read=60.0,
            write=30.0,
            pool=None
        )
        
        # Создаём клиент
        _http_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeouts,
            follow_redirects=True
        )
        _current_loop_id = current_loop_id
        logger.info("✅ Глобальный HTTPX клиент создан")
    
    return _http_client


async def close_http_client():
    """Закрывает глобальный HTTPX клиент при завершении работы"""
    global _http_client, _current_loop_id
    if _http_client:
        logger.info("🔒 Закрываем глобальный HTTPX клиент")
        try:
            await _http_client.aclose()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при закрытии клиента: {e}")
        _http_client = None
        _current_loop_id = None
# =================================================


# ============================================
# ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ
# ============================================

def bold(text: str) -> str:
    """Жирный текст для HTML"""
    return f"<b>{text}</b>"


def italic(text: str) -> str:
    """Курсив для HTML"""
    return f"<i>{text}</i>"


def emoji_text(emoji: str, text: str) -> str:
    """Текст с эмодзи"""
    return f"{emoji} {text}"


# ============================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ JSON-СЕРИАЛИЗАЦИИ
# ============================================

def make_json_serializable(obj):
    """Рекурсивно преобразует объект в JSON-сериализуемый формат"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    if hasattr(obj, 'to_dict'):
        return make_json_serializable(obj.to_dict())
    if hasattr(obj, '__dict__'):
        return make_json_serializable(obj.__dict__)
    return str(obj)


# ============================================
# DEEPSEEK API (С ИСПОЛЬЗОВАНИЕМ HTTPX)
# ============================================

async def call_deepseek(
    prompt: str,
    system_prompt: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    retries: int = 3
) -> Optional[str]:
    """
    Вызов DeepSeek API с использованием httpx
    """
    # Гарантируем наличие цикла событий
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Нет цикла - создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("🔄 Создан новый цикл событий для DeepSeek")
    
    logger.info(f"📞 Вызов DeepSeek API (httpx)")
    logger.info(f"📏 Длина промпта: {len(prompt)} символов")
    logger.info(f"🎯 max_tokens: {max_tokens}, temperature: {temperature}")
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ DEEPSEEK_API_KEY не настроен")
        return None
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        logger.info(f"📝 Системный промпт: {len(system_prompt)} символов")
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.3
    }
    
    logger.info(f"📦 Payload размер: {len(str(payload))} символов")
    
    for attempt in range(retries):
        try:
            logger.info(f"🔄 Попытка {attempt + 1}/{retries}")
            start_time = datetime.now()
            
            # Используем глобальный HTTPX клиент
            client = await get_http_client()
            if client is None:
                logger.error("❌ Не удалось получить HTTPX клиент")
                continue
            
            response = await client.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"⏱️ Время ответа: {elapsed:.2f} сек, статус: {response.status_code}")
            
            response_text = response.text
            logger.info(f"📄 Получен ответ, длина: {len(response_text)} символов")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"✅ JSON распарсен, структура: {list(data.keys())}")
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        logger.info(f"✅ Найдены choices, количество: {len(data['choices'])}")
                        
                        if 'message' in data['choices'][0]:
                            logger.info(f"✅ Найден message в первом choice")
                            
                            if 'content' in data['choices'][0]['message']:
                                content = data['choices'][0]['message']['content'].strip()
                                logger.info(f"✅ Найден content, длина: {len(content)} символов")
                                
                                if content:
                                    logger.info(f"✅ Возвращаем ответ пользователю")
                                    return content
                                else:
                                    logger.error("❌ Content пустой")
                            else:
                                logger.error(f"❌ Нет content в message: {data['choices'][0]['message'].keys()}")
                        else:
                            logger.error(f"❌ Нет message в choices[0]: {data['choices'][0].keys()}")
                    else:
                        logger.error(f"❌ Нет choices в ответе: {data.keys()}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка парсинга JSON: {e}")
                    logger.error(f"❌ Текст ответа: {response_text[:500]}")
            else:
                logger.error(f"❌ DeepSeek API error {response.status_code}: {response_text[:500]}")
            
        except httpx.TimeoutException as e:
            logger.error(f"❌ DeepSeek API timeout (попытка {attempt + 1}): {e}")
            logger.error(traceback.format_exc())
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ DeepSeek API HTTP error (попытка {attempt + 1}): {e}")
            logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"❌ DeepSeek API exception (попытка {attempt + 1}): {e}")
            logger.error(traceback.format_exc())
        
        if attempt < retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"🔄 Повтор через {wait_time}с...")
            await asyncio.sleep(wait_time)
    
    logger.error("❌ Все попытки вызова DeepSeek API исчерпаны")
    return None

# ============================================
# DEEPSEEK API С КОНТЕКСТОМ
# ============================================

async def call_deepseek_with_context(
    user_id: int,
    user_message: str,
    context: Any,
    mode: str,
    profile_data: dict
) -> Optional[str]:
    """
    Вызов DeepSeek API с учетом контекста пользователя
    """
    logger.info(f"📞 call_deepseek_with_context для пользователя {user_id}")
    logger.info(f"📝 Сообщение: {user_message[:100]}...")
    logger.info(f"🎭 Режим: {mode}")
    
    # Получаем системный промпт из режима
    from config import COMMUNICATION_MODES
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    system_prompt = mode_config.get("system_prompt", "")
    
    # Формируем контекст
    context_text = ""
    if context:
        if hasattr(context, 'name') and context.name:
            context_text += f"👤 Имя пользователя: {context.name}\n"
        if hasattr(context, 'city') and context.city:
            context_text += f"📍 Город: {context.city}\n"
        if hasattr(context, 'age') and context.age:
            context_text += f"📅 Возраст: {context.age}\n"
        if hasattr(context, 'gender') and context.gender:
            gender_text = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
            context_text += f"👤 Пол: {gender_text}\n"
    
    # Добавляем профиль
    profile_code = profile_data.get("display_name", "не определен")
    perception_type = profile_data.get("perception_type", "не определен")
    thinking_level = profile_data.get("thinking_level", 5)
    scores = profile_data.get("scores", {})
    
    profile_text = f"""
📊 **ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:**
• Код профиля: {profile_code}
• Тип восприятия: {perception_type}
• Уровень мышления: {thinking_level}/9
"""
    
    if scores:
        sb = scores.get("СБ", 3)
        tf = scores.get("ТФ", 3)
        ub = scores.get("УБ", 3)
        chv = scores.get("ЧВ", 3)
        profile_text += f"• Вектора: СБ={sb}, ТФ={tf}, УБ={ub}, ЧВ={chv}\n"
    
    # Формируем полный промпт
    prompt = f"""
{system_prompt}

{profile_text}

{context_text}

Вопрос пользователя: {user_message}

Ответь пользователю в соответствии с твоей ролью. Используй живой, разговорный язык. Не используй Markdown (**, __, и т.д.). Используй эмодзи для эмоциональной окраски. Длина ответа: 2-5 предложений для простых вопросов.
"""
    
    logger.info(f"📝 Промпт создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=1000,
        temperature=0.7
    )
    
    if response:
        logger.info(f"✅ Ответ получен, длина: {len(response)} символов")
        return response
    else:
        logger.error("❌ Не удалось получить ответ от DeepSeek")
        return "Извините, я немного задумался. Можете повторить вопрос?"


# ============================================
# DEEPGRAM API (РАСПОЗНАВАНИЕ РЕЧИ) - С ДИАГНОСТИКОЙ
# ============================================

async def speech_to_text(audio_file_path: str) -> Optional[str]:
    """
    Распознает речь из аудиофайла через Deepgram API
    """
    import time
    import json
    
    logger.info("=" * 100)
    logger.info("🎤🎤🎤 НАЧАЛО speech_to_text 🎤🎤🎤")
    logger.info("=" * 100)
    
    if not DEEPGRAM_API_KEY:
        logger.error("❌ DEEPGRAM_API_KEY не настроен")
        return None
    
    if not os.path.exists(audio_file_path):
        logger.error(f"❌ Файл НЕ СУЩЕСТВУЕТ: {audio_file_path}")
        return None
    
    file_size = os.path.getsize(audio_file_path)
    logger.info(f"📊 Размер файла: {file_size} байт ({round(file_size/1024, 2)} KB)")
    
    if file_size == 0:
        logger.error("❌ Файл ПУСТОЙ (0 байт)")
        return None
    
    # Определяем MIME тип по расширению
    if audio_file_path.endswith('.webm'):
        content_type = 'audio/webm'
    elif audio_file_path.endswith('.ogg'):
        content_type = 'audio/ogg'
    elif audio_file_path.endswith('.wav'):
        content_type = 'audio/wav'
    elif audio_file_path.endswith('.mp3'):
        content_type = 'audio/mpeg'
    else:
        content_type = 'audio/ogg'  # по умолчанию
    
    logger.info(f"📁 Content-Type: {content_type}")
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type
    }
    
    params = {
        "model": "nova-2",
        "language": "ru",
        "punctuate": "true",
        "diarize": "false",
        "smart_format": "true"
    }
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        logger.info(f"📊 Аудио данные прочитаны: {len(audio_data)} байт")
        
        client = await get_http_client()
        
        response = await client.post(
            DEEPGRAM_API_URL,
            headers=headers,
            params=params,
            content=audio_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            
            try:
                transcript = data['results']['channels'][0]['alternatives'][0].get('transcript', '')
                confidence = data['results']['channels'][0]['alternatives'][0].get('confidence', 0)
                logger.info(f"🎤 РАСПОЗНАННЫЙ ТЕКСТ: '{transcript}'")
                logger.info(f"🎤 УВЕРЕННОСТЬ: {confidence}")
                
                if transcript and transcript.strip():
                    return transcript.strip()
                else:
                    logger.warning("⚠️ Deepgram вернул пустой текст")
                    return None
                    
            except (KeyError, IndexError) as e:
                logger.error(f"❌ Не удалось извлечь транскрипт: {e}")
                return None
                
        else:
            logger.error(f"❌ Deepgram API error {response.status_code}: {response.text[:500]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка распознавания речи: {e}")
        return None
    
    # ============================================
    # ПРОВЕРКА 2: Что за формат файла?
    # ============================================
    try:
        with open(audio_file_path, 'rb') as f:
            header = f.read(16)
            logger.info(f"📊 Заголовок файла (hex): {header.hex()}")
            
            if header[:4] == b'OggS':
                logger.info("✅ Файл ОПОЗНАН как OGG (Opus/Vorbis)")
            elif header[:4] == b'RIFF':
                logger.info("✅ Файл ОПОЗНАН как WAV")
            elif header[:3] == b'ID3':
                logger.info("✅ Файл ОПОЗНАН как MP3")
            else:
                logger.warning(f"⚠️ НЕИЗВЕСТНЫЙ формат: {header[:4]}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось прочитать заголовок: {e}")
    
    # ============================================
    # ПОДГОТОВКА ЗАПРОСА
    # ============================================
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg"
    }
    
    params = {
        "model": "nova-2",
        "language": "ru",
        "punctuate": "true",
        "diarize": "false",
        "smart_format": "true"
    }
    
    logger.info("📡 ПОДГОТОВЛЕН ЗАПРОС К DEEPGRAM:")
    logger.info(f"   Headers: Authorization: Token ***, Content-Type: audio/ogg")
    logger.info(f"   Params: {json.dumps(params, ensure_ascii=False)}")
    
    # ============================================
    # ЧТЕНИЕ ФАЙЛА
    # ============================================
    try:
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        logger.info(f"📊 Аудио данные прочитаны: {len(audio_data)} байт")
        
        # СОХРАНЯЕМ КОПИЮ ДЛЯ ОТЛАДКИ
        debug_path = f"/tmp/debug_voice_{int(time.time())}.ogg"
        try:
            with open(debug_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f"💾 СОХРАНЕНА КОПИЯ ДЛЯ ОТЛАДКИ: {debug_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить копию: {e}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка чтения файла: {e}")
        return None
    
    # ============================================
    # ОТПРАВКА ЗАПРОСА
    # ============================================
    try:
        client = await get_http_client()
        if client is None:
            logger.error("❌ Не удалось получить HTTPX клиент")
            return None
        
        logger.info("📡 ОТПРАВКА ЗАПРОСА В DEEPGRAM...")
        
        response = await client.post(
            DEEPGRAM_API_URL,
            headers=headers,
            params=params,
            content=audio_data,
            timeout=30.0
        )
        
        logger.info(f"📡 ПОЛУЧЕН ОТВЕТ ОТ DEEPGRAM:")
        logger.info(f"   Статус: {response.status_code}")
        logger.info(f"   Заголовки: {dict(response.headers)}")
        
        # Получаем текст ответа
        response_text = response.text
        logger.info(f"📄 Текст ответа (первые 1000 символов):")
        logger.info(f"{response_text[:1000]}")
        
        if response.status_code == 200:
            # Парсим JSON
            try:
                data = response.json()
                logger.info(f"✅ JSON успешно распарсен")
                logger.info(f"📊 Структура ответа: {list(data.keys())}")
                
                # Извлекаем транскрипт
                transcript = None
                confidence = 0
                
                try:
                    transcript = data['results']['channels'][0]['alternatives'][0].get('transcript', '')
                    confidence = data['results']['channels'][0]['alternatives'][0].get('confidence', 0)
                    logger.info(f"🎤 РАСПОЗНАННЫЙ ТЕКСТ: '{transcript}'")
                    logger.info(f"🎤 УВЕРЕННОСТЬ: {confidence}")
                    logger.info(f"🎤 ДЛИНА ТЕКСТА: {len(transcript)}")
                    
                except (KeyError, IndexError) as e:
                    logger.error(f"❌ Не удалось извлечь транскрипт: {e}")
                    logger.info(f"📄 Полная структура data: {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
                
                logger.info("=" * 100)
                logger.info(f"🎤🎤🎤 РЕЗУЛЬТАТ speech_to_text: {transcript if transcript else 'НЕТ ТЕКСТА'} 🎤🎤🎤")
                logger.info("=" * 100)
                
                if transcript and transcript.strip():
                    return transcript.strip()
                else:
                    logger.warning("⚠️ Deepgram вернул пустой текст")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
                logger.error(f"❌ Текст ответа: {response_text[:500]}")
                return None
                
        elif response.status_code == 400:
            logger.error("❌ Deepgram вернул 400 Bad Request")
            logger.error(f"❌ Сообщение: {response_text[:500]}")
            logger.error("❌ Возможные причины:")
            logger.error("   • Неподдерживаемый формат аудио")
            logger.error("   • Аудио повреждено")
            logger.error("   • Неправильные параметры")
            return None
        elif response.status_code == 401:
            logger.error("❌ Deepgram вернул 401 Unauthorized")
            logger.error("❌ Неверный API ключ")
            return None
        elif response.status_code == 429:
            logger.error("❌ Deepgram вернул 429 Too Many Requests")
            logger.error("❌ Превышен лимит запросов")
            return None
        else:
            logger.error(f"❌ Deepgram API error {response.status_code}: {response_text[:500]}")
            return None
            
    except httpx.TimeoutException as e:
        logger.error(f"❌ Таймаут Deepgram: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка распознавания речи: {e}")
        logger.error(traceback.format_exc())
        return None

# ============================================
# YANDEX TTS (СИНТЕЗ РЕЧИ)
# ============================================

async def text_to_speech(text: str, mode: str = "coach") -> Optional[bytes]:
    """
    Преобразует текст в речь через Yandex TTS
    """
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не настроен")
        return None
    
    logger.info(f"🎤 Синтез речи для текста: {len(text)} символов, режим: {mode}")
    
    voices = {
        "coach": "filipp",
        "psychologist": "ermil",
        "trainer": "filipp"
    }
    voice = voices.get(mode, "filipp")
    logger.info(f"🗣️ Выбран голос: {voice}")
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Ограничиваем длину текста
    original_length = len(text)
    if len(text) > 5000:
        text = text[:5000] + "..."
        logger.warning(f"⚠️ Текст обрезан с {original_length} до 5000 символов")
    
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "emotion": "neutral",
        "speed": 1.0,
        "format": "oggopus"
    }
    
    try:
        client = await get_http_client()
        if client is None:
            logger.error("❌ Не удалось получить HTTPX клиент")
            return None
        
        response = await client.post(
            YANDEX_TTS_API_URL,
            headers=headers,
            data=data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            audio_data = response.content
            logger.info(f"✅ Речь синтезирована: {len(audio_data)} байт")
            return audio_data
        else:
            logger.error(f"❌ Yandex TTS API error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка синтеза речи: {e}")
        logger.error(traceback.format_exc())
        return None


# ============================================
# ГЕНЕРАЦИЯ ПСИХОЛОГИЧЕСКОГО ПОРТРЕТА
# ============================================

async def generate_ai_profile(user_id: int, data: dict) -> Optional[str]:
    """
    Генерирует психологический портрет на основе данных теста
    """
    logger.info(f"🧠 Генерация AI-профиля для пользователя {user_id}")
    logger.info(f"📊 Размер входных данных: {len(str(data))} символов")
    
    # 🔍 ДЕТАЛЬНАЯ ОТЛАДКА - проверяем все поля
    logger.info("=== ДЕТАЛЬНАЯ ОТЛАДКА generate_ai_profile ===")
    
    # 1. Проверяем наличие всех ключевых полей
    required_fields = ["perception_type", "thinking_level", "behavioral_levels", "dilts_counts", "deep_patterns"]
    for field in required_fields:
        if field in data:
            value = data[field]
            logger.info(f"✅ {field}: присутствует, тип {type(value)}")
            if isinstance(value, dict):
                logger.info(f"   - количество ключей: {len(value)}")
                if value:
                    logger.info(f"   - пример: {str(value)[:100]}")
        else:
            logger.warning(f"⚠️ {field}: отсутствует в данных")
    
    # 2. Проверяем confinement_model отдельно
    if data.get("confinement_model"):
        confinement = data["confinement_model"]
        logger.info(f"🔍 confinement_model: тип {type(confinement)}")
        
        if isinstance(confinement, dict):
            logger.info(f"   - ключи: {list(confinement.keys())}")
            if "elements" in confinement:
                elements = confinement["elements"]
                logger.info(f"   - elements: тип {type(elements)}")
                if isinstance(elements, dict):
                    logger.info(f"   - elements ключи: {list(elements.keys())}")
        else:
            logger.warning(f"⚠️ confinement_model не словарь: {type(confinement)}")
            try:
                data["confinement_model"] = make_json_serializable(confinement)
                logger.info("✅ Преобразовали через make_json_serializable()")
            except Exception as e:
                logger.error(f"❌ Ошибка преобразования: {e}")
    else:
        logger.warning("⚠️ confinement_model отсутствует")
    
    # 3. Проверяем deep_patterns детально
    if data.get("deep_patterns"):
        deep = data["deep_patterns"]
        logger.info(f"🔍 deep_patterns: тип {type(deep)}")
        if isinstance(deep, dict):
            logger.info(f"   - ключи: {list(deep.keys())}")
            for k, v in deep.items():
                logger.info(f"   - {k}: {type(v)} = {v}")
    else:
        logger.warning("⚠️ deep_patterns отсутствует")
    
    system_prompt = """Ты — Фреди, виртуальный психолог, цифровая копия Андрея Мейстера. 
Твоя задача — создавать глубокие, точные психологические портреты на основе теста «Матрица поведений 4×6».

ТВОЙ СТИЛЬ:
- Говоришь от первого лица, напрямую обращаясь к человеку
- Используешь живой, образный язык, метафоры, аналогии
- Избегаешь шаблонных фраз и психологического жаргона
- Будь честным, иногда ироничным, но всегда поддерживающим
- Используй эмодзи для эмоциональной окраски, но не перебарщивай

ВАЖНО: 
- Твои портреты помогают людям увидеть себя со стороны
- Они должны быть узнаваемыми и полезными
- Никакой воды — только суть"""
    
    # Подготавливаем данные для анализа
    profile_data = {
        "perception_type": data.get("perception_type", "не определен"),
        "thinking_level": data.get("thinking_level", 5),
        "behavioral_levels": data.get("behavioral_levels", {}),
        "dilts_counts": data.get("dilts_counts", {}),
        "dominant_dilts": data.get("dominant_dilts", "BEHAVIOR"),
        "final_level": data.get("final_level", 5),
        "deep_patterns": data.get("deep_patterns", {})
    }
    
    # Добавляем конфайнмент-модель, если есть
    if data.get("confinement_model"):
        try:
            profile_data["confinement_model"] = make_json_serializable(data["confinement_model"])
            logger.info("✅ confinement_model добавлен в profile_data")
        except Exception as e:
            logger.error(f"❌ Ошибка при сериализации confinement_model: {e}")
    
    logger.info(f"📊 profile_data подготовлен, размер: {len(str(profile_data))} символов")
    logger.info(f"📊 profile_data keys: {list(profile_data.keys())}")
    
    # Полный промт для генерации профиля
    try:
        profile_json = json.dumps(profile_data, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"❌ Ошибка сериализации profile_data: {e}")
        simplified = {}
        for k, v in profile_data.items():
            try:
                simplified[k] = str(v)[:500] if not isinstance(v, (int, float, bool, str)) else v
            except:
                simplified[k] = str(v)[:200]
        profile_json = json.dumps(simplified, ensure_ascii=False, indent=2)
        logger.warning("⚠️ Используем упрощенные данные")
    
    prompt = f"""На основе данных теста создай глубокий, точный психологический портрет человека.

ДАННЫЕ ТЕСТА:
{profile_json}

ИНСТРУКЦИИ ПО ФОРМАТУ:
1. Пиши от первого лица, как будто ты напрямую обращаешься к человеку.
2. Используй живой, образный язык, метафоры, аналогии.
3. Избегай шаблонных фраз и психологического жаргона.
4. Будь честным, иногда ироничным, но всегда поддерживающим.
5. ОБЯЗАТЕЛЬНО используй эмодзи в заголовках блоков.

СТРУКТУРА ПОРТРЕТА (обязательно соблюдай):

БЛОК 1: КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА
(Опиши главную особенность личности пользователя одной яркой фразой или метафорой. Что определяет его способ взаимодействия с миром? Используй эмодзи 🔑)

БЛОК 2: СИЛЬНЫЕ СТОРОНЫ
(Распиши 3-4 сильные стороны. Не просто перечисли, а покажи, как они проявляются в жизни. Используй эмодзи 💪)

БЛОК 3: ЗОНЫ РОСТА
(Опиши, что мешает, какие паттерны повторяются. Укажи цену, которую человек платит за эти паттерны. Используй эмодзи 🎯)

БЛОК 4: КАК ЭТО СФОРМИРОВАЛОСЬ
(Свяжи текущие паттерны с прошлым опытом, воспитанием, средой. Будь деликатен. Используй эмодзи 🌱)

БЛОК 5: ГЛАВНАЯ ЛОВУШКА
(Опиши цикл, в котором застревает пользователь. Как его сильные стороны превращаются в слабости. Используй эмодзи ⚠️)

ТОН И СТИЛЬ:
- Представь, что ты разговариваешь с человеком в уютной комнате за чашкой чая.
- Используй разговорные обороты: «Слушай...», «Понимаешь...», «Дело в том, что...».
- Добавляй лёгкую иронию, но не сарказм.
- Завершай портрет вопросом или приглашением к размышлению.

НАПИШИ ПОРТРЕТ, СОБЛЮДАЯ ВСЕ 5 БЛОКОВ С ЭМОДЗИ В ЗАГОЛОВКАХ:
🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА
💪 СИЛЬНЫЕ СТОРОНЫ
🎯 ЗОНЫ РОСТА
🌱 КАК ЭТО СФОРМИРОВАЛОСЬ
⚠️ ГЛАВНАЯ ЛОВУШКА
"""
    
    logger.info(f"📝 Промпт создан, длина: {len(prompt)} символов")
    
    if len(prompt) > 15000:
        logger.warning(f"⚠️ Промпт очень длинный: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=2000,
        temperature=0.8
    )
    
    if response:
        logger.info(f"✅ AI-профиль сгенерирован ({len(response)} символов)")
        
        if "🔑" in response and "💪" in response and "🎯" in response:
            logger.info("✅ Ответ содержит все необходимые эмодзи")
        else:
            logger.warning("⚠️ В ответе отсутствуют некоторые обязательные эмодзи")
            logger.info(f"📄 Начало ответа: {response[:200]}...")
        
        return response
    else:
        logger.error("❌ Не удалось сгенерировать AI-профиль (пустой ответ)")
        
        logger.info("🔄 Создаем тестовый профиль для отладки")
        test_profile = f"""
🧠 **ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ** (ТЕСТОВАЯ ВЕРСИЯ)

🔑 **КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА**
Вы — исследователь глубин. Ваш ум постоянно ищет закономерности и смыслы там, где другие видят хаос.

💪 **СИЛЬНЫЕ СТОРОНЫ**
• Способность глубоко анализировать ситуации
• Развитая интуиция и эмпатия
• Умение находить нестандартные решения

🎯 **ЗОНЫ РОСТА**
• Иногда анализ превращается в бесконечный цикл
• Страх ошибки может блокировать действие
• Важно научиться доверять спонтанности

🌱 **КАК ЭТО СФОРМИРОВАЛОСЬ**
Ваш тип мышления — результат глубокой внутренней работы. Вы научились выживать в хаосе, создавая свои системы порядка.

⚠️ **ГЛАВНАЯ ЛОВУШКА**
Анализ → Поиск идеального решения → Страх ошибки → Ещё больший анализ
"""
        logger.info(f"✅ Тестовый профиль создан ({len(test_profile)} символов)")
        return test_profile


# ============================================
# ГЕНЕРАЦИЯ МЫСЛЕЙ ПСИХОЛОГА
# ============================================

async def generate_psychologist_thought(user_id: int, data: dict) -> Optional[str]:
    """
    Генерирует мысли психолога на основе конфайнтмент-модели
    """
    logger.info(f"🧠 Генерация мыслей психолога для пользователя {user_id}")
    logger.info(f"📊 Размер входных данных: {len(str(data))} символов")
    
    # 🔍 ОТЛАДКА
    logger.info("=== ДЕТАЛЬНАЯ ОТЛАДКА generate_psychologist_thought ===")
    
    confinement_data = data.get("confinement_model", {})
    logger.info(f"🔍 Тип confinement_data: {type(confinement_data)}")
    
    if isinstance(confinement_data, dict):
        logger.info(f"🔍 confinement_data ключи: {list(confinement_data.keys())}")
        if "key_confinement" in confinement_data:
            logger.info(f"✅ key_confinement: {confinement_data['key_confinement']}")
        if "elements" in confinement_data:
            elements = confinement_data["elements"]
            logger.info(f"✅ elements: {len(elements) if isinstance(elements, dict) else 'не словарь'}")
        if "loops" in confinement_data:
            loops = confinement_data["loops"]
            logger.info(f"✅ loops: {len(loops) if isinstance(loops, list) else 'не список'}")
    else:
        logger.warning(f"⚠️ confinement_data не словарь: {type(confinement_data)}")
        try:
            confinement_data = make_json_serializable(confinement_data)
            logger.info("✅ Преобразовали через make_json_serializable()")
        except Exception as e:
            logger.error(f"❌ Ошибка преобразования: {e}")
    
    system_prompt = """Ты — Фреди, виртуальный психолог. Твоя задача — давать глубинный анализ через конфайнтмент-модель.

ТВОЙ СТИЛЬ:
- Говоришь как опытный психолог, но простым языком
- Используешь метафоры и образы
- Видишь систему, а не отдельные симптомы
- Будь честным, иногда жестким, но всегда заботливым
- Используй эмодзи для выделения ключевых моментов"""
    
    profile_data = {
        "perception_type": data.get("perception_type", "не определен"),
        "thinking_level": data.get("thinking_level", 5),
        "behavioral_levels": data.get("behavioral_levels", {}),
        "profile_code": data.get("profile_data", {}).get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
    }
    
    logger.info(f"📊 profile_data подготовлен: {list(profile_data.keys())}")
    
    try:
        profile_json = json.dumps(profile_data, ensure_ascii=False, indent=2, default=str)
        confinement_json = json.dumps(confinement_data, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"❌ Ошибка сериализации: {e}")
        profile_json = str(profile_data)[:1000]
        confinement_json = str(confinement_data)[:1000]
    
    prompt = f"""Проанализируй пользователя через конфайнтмент-модель и дай 3 глубинные мысли.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{profile_json}

КОНФАЙНМЕНТ-МОДЕЛЬ:
{confinement_json}

Дай 3 мысли, строго соблюдая формат:

МЫСЛЬ 1 — КЛЮЧЕВОЙ ЭЛЕМЕНТ 🔐
Какой элемент в системе самый важный? Что держит всю конструкцию? Опиши его простыми словами, метафорой. Почему именно он — центр? (2-3 предложения)

МЫСЛЬ 2 — ПЕТЛЯ 🔄
Опиши основной цикл, в котором застревает пользователь. Как его действия (или бездействие) приводят к тому же результату? Где здесь «замкнутый круг»? Покажи связь между разными уровнями (поведение, способности, ценности, идентичность). (3-4 предложения)

МЫСЛЬ 3 — ТОЧКА ВХОДА 🚪 И ПРОГНОЗ 📊
Если бы нужно было разорвать эту петлю одним маленьким действием, где находится эта точка? Самый слабый узел, потянув за который, можно начать распутывать весь клубок. И какой прогноз — что изменится, если начать с этой точки? Что будет через месяц, через полгода? (3-4 предложения)

ФОРМАТ ОТВЕТА (строго соблюдай заголовки с эмодзи):

🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ:
[текст]

🔄 ПЕТЛЯ:
[текст]

🚪 ТОЧКА ВХОДА:
[текст]

📊 ПРОГНОЗ:
[текст]

ВАЖНО:
- Не используй Markdown, только обычный текст
- Не ставь лишних символов вроде "###"
- Каждая мысль должна быть связана с конфайнтмент-моделью
- Пиши на русском, живым языком
"""
    
    logger.info(f"📝 Промпт создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=1500,
        temperature=0.7
    )
    
    if response:
        logger.info(f"✅ Мысли психолога сгенерированы ({len(response)} символов)")
        return response
    else:
        logger.error("❌ Не удалось сгенерировать мысли психолога")
        return None


# ============================================
# ГЕНЕРАЦИЯ МАРШРУТА
# ============================================

async def generate_route_ai(user_id: int, data: dict, goal: dict) -> Optional[Dict]:
    """
    Генерирует пошаговый маршрут к цели
    """
    logger.info(f"🧠 Генерация маршрута для пользователя {user_id}, цель: {goal.get('name')}")
    
    mode = data.get("communication_mode", "coach")
    
    mode_descriptions = {
        "coach": {
            "name": "КОУЧ",
            "emoji": "🔮",
            "style": "Ты — коуч. Задаешь открытые вопросы, помогаешь найти ответы внутри себя. Не даешь готовых решений, но направляешь.",
            "tone": "используй вопросы, размышления, метафоры."
        },
        "psychologist": {
            "name": "ПСИХОЛОГ",
            "emoji": "🧠",
            "style": "Ты — психолог. Исследуешь глубинные паттерны, защитные механизмы, прошлый опыт.",
            "tone": "будь эмпатичным, но профессиональным."
        },
        "trainer": {
            "name": "ТРЕНЕР",
            "emoji": "⚡",
            "style": "Ты — тренер. Даешь четкие инструкции, упражнения, ставишь дедлайны.",
            "tone": "будь конкретным, структурированным, требовательным."
        }
    }
    
    mode_info = mode_descriptions.get(mode, mode_descriptions["coach"])
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
    
    sb_level = profile_data.get("sb_level", 4)
    tf_level = profile_data.get("tf_level", 4)
    ub_level = profile_data.get("ub_level", 4)
    chv_level = profile_data.get("chv_level", 4)
    
    logger.info(f"📊 Профиль: {profile_code}, СБ={sb_level}, ТФ={tf_level}, УБ={ub_level}, ЧВ={chv_level}")
    
    prompt = f"""Ты — {mode_info['emoji']} {mode_info['name']}, виртуальный помощник. Создай пошаговый маршрут для пользователя к его цели.

ЦЕЛЬ: {goal.get('name', 'цель')}
ВРЕМЯ: {goal.get('time', '3-6 месяцев')}
ПРОФИЛЬ: {profile_code}

Создай маршрут из 3 последовательных этапов. Для каждого этапа укажи:
📍 ЭТАП X: [НАЗВАНИЕ]
   • Что делаем: [конкретные действия]
   • 📝 Домашнее задание: [что нужно сделать между сессиями]
   • ✅ Критерий выполнения: [как понять, что этап пройден]

ФОРМАТ ОТВЕТА:

📍 ЭТАП 1: [НАЗВАНИЕ]
   • Что делаем: [описание]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]

📍 ЭТАП 2: [НАЗВАНИЕ]
   • Что делаем: [описание]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]

📍 ЭТАП 3: [НАЗВАНИЕ]
   • Что делаем: [описание]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]
"""
    
    logger.info(f"📝 Промпт для маршрута создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=f"Ты — {mode_info['emoji']} {mode_info['name']}, создающий эффективные маршруты развития.",
        max_tokens=1500,
        temperature=0.7
    )
    
    if response:
        logger.info(f"✅ Маршрут сгенерирован ({len(response)} символов)")
        return {
            "full_text": response,
            "steps": response.split("\n\n")
        }
    else:
        logger.error("❌ Не удалось сгенерировать маршрут")
        return None


# ============================================
# ГЕНЕРАЦИЯ ОТВЕТА НА ВОПРОС
# ============================================

async def generate_response_with_full_context(
    user_id: int,
    user_message: str,
    profile_data: dict,
    mode: str,
    context: Any = None,
    history: list = None
) -> Dict[str, Any]:
    """
    Генерирует ответ с учетом полного контекста пользователя
    """
    logger.info(f"🧠 Генерация ответа для пользователя {user_id}, режим: {mode}")
    logger.info(f"📝 Сообщение пользователя: {user_message[:100]}...")
    
    mode_prompts = {
        "coach": {
            "role": "коуч",
            "style": """Ты — коуч. Твоя задача — помогать человеку находить ответы внутри себя через открытые вопросы и размышления.

ПРАВИЛА КОУЧА:
1. НЕ давай готовых ответов и советов
2. Задавай открытые вопросы
3. Отражай и перефразируй мысли человека
4. Помогай структурировать размышления

ПРИМЕРЫ:
- "Расскажи подробнее об этой ситуации..."
- "Что для тебя самое важное в этом?"
- "Как бы ты хотел, чтобы это выглядело в идеале?" """
        },
        "psychologist": {
            "role": "психолог",
            "style": """Ты — психолог. Твоя задача — исследовать глубинные паттерны, прошлый опыт, защитные механизмы.

ПРАВИЛА ПСИХОЛОГА:
1. Исследуй чувства и эмоции
2. Ищи связи с прошлым
3. Обращай внимание на повторяющиеся сценарии
4. Создавай безопасное пространство для исследования

ПРИМЕРЫ:
- "Когда ты впервые почувствовал это?"
- "Что для тебя самое страшное в этой ситуации?"
- "Как эта ситуация связана с твоим детством?" """
        },
        "trainer": {
            "role": "тренер",
            "style": """Ты — тренер. Твоя задача — давать четкие инструменты, навыки, упражнения для достижения результата.

ПРАВИЛА ТРЕНЕРА:
1. Давай конкретные, выполнимые задания
2. Структурируй процесс
3. Ставь дедлайны и требуй отчета
4. Формируй навыки через повторение

ПРИМЕРЫ:
- "Вот конкретное упражнение на эту неделю..."
- "Сделай это до следующей встречи"
- "Давай разберем это по шагам..." """
        }
    }
    
    mode_info = mode_prompts.get(mode, mode_prompts["coach"])
    profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
    
    context_text = ""
    if context:
        if hasattr(context, 'get_prompt_context'):
            context_text = context.get_prompt_context()
        else:
            context_text = str(context)
    
    history_text = ""
    if history and len(history) > 0:
        last_messages = history[-6:]
        history_text = "\n".join([
            f"{'🤖' if i%2==0 else '👤'}: {msg[:100]}..." 
            for i, msg in enumerate(last_messages)
        ])
    
    logger.info(f"📊 Контекст: профиль {profile_code}, история {len(history) if history else 0} сообщений")
    
    prompt = f"""Ты — {mode_info['role']}, виртуальный помощник. Ответь на вопрос пользователя с учетом его профиля и контекста.

ВОПРОС: {user_message}

ПРОФИЛЬ: {profile_code}

КОНТЕКСТ: {context_text if context_text else "Контекст не указан"}

ИСТОРИЯ: {history_text if history_text else "Нет истории"}

{mode_info['style']}

ИНСТРУКЦИИ:
- Не используй Markdown (**, __, и т.д.)
- Используй эмодзи для эмоциональной окраски
- Длина ответа: 3-5 предложений для простых вопросов

ТВОЙ ОТВЕТ:
"""
    
    logger.info(f"📝 Промпт для ответа создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=f"Ты — {mode_info['role']}, помогающий людям.",
        max_tokens=1000,
        temperature=0.7
    )
    
    suggestions = await generate_suggestions(user_message, response, profile_code, mode)
    
    result = {
        "response": response or "Извините, не удалось сгенерировать ответ. Попробуйте переформулировать вопрос.",
        "suggestions": suggestions or []
    }
    
    logger.info(f"✅ Ответ сгенерирован, длина: {len(result['response'])} символов")
    return result


async def generate_suggestions(question: str, answer: str, profile_code: str, mode: str) -> list:
    """
    Генерирует предложения для продолжения диалога
    """
    if not answer:
        return [
            "Расскажи подробнее",
            "Что ты чувствуешь?",
            "Какие есть варианты?"
        ]
    
    prompt = f"""На основе вопроса и ответа придумай 3 коротких варианта, что спросить дальше.

ВОПРОС: {question}
ОТВЕТ: {answer[:200]}...
ПРОФИЛЬ: {profile_code}
РЕЖИМ: {mode}

Требования:
- Каждый вариант не длиннее 7 слов
- Варианты должны быть связаны с темой

Формат ответа: просто список, каждый вариант с новой строки
"""
    
    response = await call_deepseek(
        prompt=prompt,
        max_tokens=200,
        temperature=0.8
    )
    
    if response:
        suggestions = [s.strip() for s in response.split('\n') if s.strip()]
        logger.info(f"✅ Сгенерировано {len(suggestions)} предложений")
        return suggestions[:3]
    
    logger.warning("⚠️ Не удалось сгенерировать предложения")
    return [
        "Расскажи подробнее",
        "Что ты чувствуешь?",
        "Какие есть варианты?"
    ]


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'generate_ai_profile',
    'generate_psychologist_thought',
    'generate_route_ai',
    'generate_response_with_full_context',
    'generate_suggestions',
    'call_deepseek',
    'speech_to_text',
    'text_to_speech',
    'bold',
    'italic',
    'emoji_text',
    'make_json_serializable',
    'close_http_client'
]
