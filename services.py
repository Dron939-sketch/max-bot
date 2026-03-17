#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервисные функции для работы с API и генерации ответов
Версия 9.6: ПОЛНЫЕ ПРОМТЫ с жирным текстом и эмодзи
"""

import os
import json
import logging
import aiohttp
import asyncio
import re
import traceback
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


# ============================================
# ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ (дублируем для независимости)
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
    # Если ничего не подходит, преобразуем в строку
    return str(obj)


# ============================================
# DEEPSEEK API (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ============================================

async def call_deepseek(prompt: str, system_prompt: str = None, max_tokens: int = 1000, temperature: float = 0.7, retry_count: int = 2) -> Optional[str]:
    """
    Универсальная функция вызова DeepSeek API с повторными попытками
    """
    logger.info(f"📞 Вызов DeepSeek API")
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
    
    for attempt in range(retry_count + 1):
        try:
            logger.info(f"🔄 Попытка {attempt + 1}/{retry_count + 1}")
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    DEEPSEEK_API_URL, 
                    headers=headers, 
                    json=payload, 
                    timeout=60
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"⏱️ Время ответа: {elapsed:.2f} сек, статус: {response.status}")
                    
                    # ПОЛУЧАЕМ ТЕКСТ ОТВЕТА
                    response_text = await response.text()
                    logger.info(f"📄 Получен ответ, длина: {len(response_text)} символов")
                    logger.info(f"📄 Первые 200 символов ответа: {response_text[:200]}")
                    
                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            logger.info(f"✅ JSON распарсен, структура: {list(data.keys())}")
                            
                            # Проверяем структуру ответа
                            if 'choices' in data and len(data['choices']) > 0:
                                logger.info(f"✅ Найдены choices, количество: {len(data['choices'])}")
                                
                                if 'message' in data['choices'][0]:
                                    logger.info(f"✅ Найден message в первом choice")
                                    
                                    if 'content' in data['choices'][0]['message']:
                                        content = data['choices'][0]['message']['content'].strip()
                                        logger.info(f"✅ Найден content, длина: {len(content)} символов")
                                        logger.info(f"📝 Первые 200 символов content: {content[:200]}")
                                        
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
                        logger.error(f"❌ DeepSeek API error {response.status}: {response_text[:500]}")
                    
                    # Если дошли сюда, что-то пошло не так
                    if attempt < retry_count:
                        wait_time = 2 ** attempt
                        logger.info(f"🔄 Повторная попытка {attempt + 1}/{retry_count} через {wait_time}с...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None
                        
        except asyncio.TimeoutError:
            logger.error(f"❌ DeepSeek API timeout (попытка {attempt + 1}/{retry_count + 1})")
            if attempt < retry_count:
                wait_time = 2 ** attempt
                logger.info(f"🔄 Повтор через {wait_time}с...")
                await asyncio.sleep(wait_time)
                continue
            return None
            
        except Exception as e:
            logger.error(f"❌ DeepSeek API exception (попытка {attempt + 1}): {e}")
            logger.error(traceback.format_exc())
            if attempt < retry_count:
                wait_time = 2 ** attempt
                logger.info(f"🔄 Повтор через {wait_time}с...")
                await asyncio.sleep(wait_time)
                continue
            return None
    
    logger.error("❌ Все попытки вызова DeepSeek API исчерпаны")
    return None


# ============================================
# ГЕНЕРАЦИЯ ПСИХОЛОГИЧЕСКОГО ПОРТРЕТА (ПОЛНЫЙ ПРОМТ)
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
            # Проверяем элементы внутри
            if "elements" in confinement:
                elements = confinement["elements"]
                logger.info(f"   - elements: тип {type(elements)}")
                if isinstance(elements, dict):
                    logger.info(f"   - elements ключи: {list(elements.keys())}")
        else:
            logger.warning(f"⚠️ confinement_model не словарь: {type(confinement)}")
            # Пробуем преобразовать
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
    
    # Добавляем конфайнмент-модель, если есть (преобразуем в JSON-сериализуемый формат)
    if data.get("confinement_model"):
        try:
            profile_data["confinement_model"] = make_json_serializable(data["confinement_model"])
            logger.info("✅ confinement_model добавлен в profile_data")
        except Exception as e:
            logger.error(f"❌ Ошибка при сериализации confinement_model: {e}")
    
    logger.info(f"📊 profile_data подготовлен, размер: {len(str(profile_data))} символов")
    logger.info(f"📊 profile_data keys: {list(profile_data.keys())}")
    
    # Полный промт для генерации профиля
    prompt = f"""На основе данных теста создай глубокий, точный психологический портрет человека.

ДАННЫЕ ТЕСТА:
{json.dumps(profile_data, ensure_ascii=False, indent=2, default=str)}

ИНСТРУКЦИИ ПО ФОРМАТУ:
1. Пиши от первого лица, как будто ты напрямую обращаешься к человеку.
2. Используй живой, образный язык, метафоры, аналогии.
3. Избегай шаблонных фраз и психологического жаргона.
4. Будь честным, иногда ироничным, но всегда поддерживающим.
5. ОБЯЗАТЕЛЬНО используй эмодзи в заголовках блоков.

СТРУКТУРА ПОРТРЕТА (обязательно соблюдай):

БЛОК 1: КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА
(Опиши главную особенность личности пользователя одной яркой фразой или метафорой. Что определяет его способ взаимодействия с миром? Например: «Вы — архитектор, который строит системы, но забывает в них жить» или «Вы — разведчик, который всегда сканирует опасность, даже когда вокруг безопасно». Используй эмодзи 🔑 в начале блока.)

БЛОК 2: СИЛЬНЫЕ СТОРОНЫ
(Распиши 3-4 сильные стороны. Не просто перечисли, а покажи, как они проявляются в жизни. Например: «Ваша способность замечать детали позволяет вам находить неочевидные решения...» Используй эмодзи 💪 в начале блока.)

БЛОК 3: ЗОНЫ РОСТА
(Опиши, что мешает, какие паттерны повторяются. Укажи цену, которую человек платит за эти паттерны — энергией, отношениями, деньгами, временем. Например: «Стремление всё контролировать съедает вашу энергию и не даёт расслабиться даже в безопасной обстановке». Используй эмодзи 🎯 в начале блока.)

БЛОК 4: КАК ЭТО СФОРМИРОВАЛОСЬ
(Свяжи текущие паттерны с прошлым опытом, воспитанием, средой. Будь деликатен. Например: «Скорее всего, такая гиперответственность сформировалась, потому что в детстве вам приходилось быть «взрослым» раньше времени...» Используй эмодзи 🌱 в начале блока.)

БЛОК 5: ГЛАВНАЯ ЛОВУШКА
(Опиши цикл, в котором застревает пользователь. Как его сильные стороны превращаются в слабости, а попытки решить проблему её усугубляют. Например: «Вы боитесь ошибок → поэтому тщательно планируете → тратите на планирование всю энергию → на действие сил не остаётся → вы не достигаете цели → убеждаетесь, что «опять не получилось» → страх ошибок усиливается». Замкнутый круг. Используй эмодзи ⚠️ в начале блока.)

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
    logger.info(f"📝 Первые 500 символов промпта: {prompt[:500]}")
    
    # Проверяем длину промпта
    if len(prompt) > 15000:
        logger.warning(f"⚠️ Промпт очень длинный: {len(prompt)} символов. Может быть проблема с API.")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=2000,
        temperature=0.8
    )
    
    if response:
        logger.info(f"✅ AI-профиль сгенерирован ({len(response)} символов)")
        logger.info(f"📝 Первые 300 символов ответа: {response[:300]}")
        
        # Проверяем структуру ответа
        if "🔑" in response and "💪" in response and "🎯" in response:
            logger.info("✅ Ответ содержит все необходимые эмодзи")
        else:
            logger.warning("⚠️ В ответе отсутствуют некоторые обязательные эмодзи")
            logger.info(f"🔍 Содержимое ответа для отладки: {response[:500]}")
        
        # ВАЖНО: Принудительно возвращаем ответ
        return response
    else:
        logger.error("❌ Не удалось сгенерировать AI-профиль (пустой ответ)")
        
        # Для отладки: создаем тестовый профиль
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
# ГЕНЕРАЦИЯ МЫСЛЕЙ ПСИХОЛОГА (ПОЛНЫЙ ПРОМТ)
# ============================================

async def generate_psychologist_thought(user_id: int, data: dict) -> Optional[str]:
    """
    Генерирует мысли психолога на основе конфайнмент-модели
    """
    logger.info(f"🧠 Генерация мыслей психолога для пользователя {user_id}")
    logger.info(f"📊 Размер входных данных: {len(str(data))} символов")
    
    # 🔍 ОТЛАДКА
    logger.info("=== ДЕТАЛЬНАЯ ОТЛАДКА generate_psychologist_thought ===")
    
    confinement_data = data.get("confinement_model", {})
    logger.info(f"🔍 Тип confinement_data: {type(confinement_data)}")
    
    if isinstance(confinement_data, dict):
        logger.info(f"🔍 confinement_data ключи: {list(confinement_data.keys())}")
        
        # Проверяем наличие ключевых элементов
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
        # Пробуем преобразовать
        try:
            confinement_data = make_json_serializable(confinement_data)
            logger.info("✅ Преобразовали через make_json_serializable()")
        except Exception as e:
            logger.error(f"❌ Ошибка преобразования: {e}")
    
    system_prompt = """Ты — Фреди, виртуальный психолог. Твоя задача — давать глубинный анализ через конфайнмент-модель.

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
    
    # Полный промт для мыслей психолога
    prompt = f"""Проанализируй пользователя через конфайнмент-модель и дай 3 глубинные мысли.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{json.dumps(profile_data, ensure_ascii=False, indent=2, default=str)}

КОНФАЙНМЕНТ-МОДЕЛЬ:
{json.dumps(confinement_data, ensure_ascii=False, indent=2, default=str)}

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
- Каждая мысль должна быть связана с конфайнмент-моделью
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
        logger.info(f"📝 Первые 200 символов ответа: {response[:200]}")
        return response
    else:
        logger.error("❌ Не удалось сгенерировать мысли психолога")
        return None


# ============================================
# ГЕНЕРАЦИЯ МАРШРУТА (ПОЛНЫЙ ПРОМТ)
# ============================================

async def generate_route_ai(user_id: int, data: dict, goal: dict) -> Optional[Dict]:
    """
    Генерирует пошаговый маршрут к цели
    """
    logger.info(f"🧠 Генерация маршрута для пользователя {user_id}, цель: {goal.get('name')}")
    
    mode = data.get("communication_mode", "coach")
    
    # Описания режимов
    mode_descriptions = {
        "coach": {
            "name": "КОУЧ",
            "emoji": "🔮",
            "style": "Ты — коуч. Задаешь открытые вопросы, помогаешь найти ответы внутри себя. Не даешь готовых решений, но направляешь. Твой стиль — партнерский, поддерживающий, но не директивный.",
            "tone": "используй вопросы, размышления, метафоры. Избегай прямых указаний."
        },
        "psychologist": {
            "name": "ПСИХОЛОГ",
            "emoji": "🧠",
            "style": "Ты — психолог. Исследуешь глубинные паттерны, защитные механизмы, прошлый опыт. Работаешь с причинами, а не следствиями.",
            "tone": "будь эмпатичным, но профессиональным. Используй терапевтические техники, задавай вопросы о прошлом, чувствах."
        },
        "trainer": {
            "name": "ТРЕНЕР",
            "emoji": "⚡",
            "style": "Ты — тренер. Даешь четкие инструкции, упражнения, ставишь дедлайны. Формируешь навыки и требуешь выполнения.",
            "tone": "будь конкретным, структурированным, требовательным. Используй списки, алгоритмы, чек-листы."
        }
    }
    
    mode_info = mode_descriptions.get(mode, mode_descriptions["coach"])
    
    # Получаем данные профиля
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
    
    # Парсим профиль для более детального анализа
    sb_level = profile_data.get("sb_level", 4)
    tf_level = profile_data.get("tf_level", 4)
    ub_level = profile_data.get("ub_level", 4)
    chv_level = profile_data.get("chv_level", 4)
    
    logger.info(f"📊 Профиль: {profile_code}, СБ={sb_level}, ТФ={tf_level}, УБ={ub_level}, ЧВ={chv_level}")
    
    # Полный промт для генерации маршрута
    prompt = f"""Ты — {mode_info['emoji']} {mode_info['name']}, виртуальный помощник. Твоя задача — создать пошаговый маршрут для пользователя к его цели.

ЦЕЛЬ ПОЛЬЗОВАТЕЛЯ: {goal.get('name', 'цель')}
ОПИСАНИЕ ЦЕЛИ: {goal.get('description', '')}
СЛОЖНОСТЬ: {goal.get('difficulty', 'medium')}
ОРИЕНТИРОВОЧНОЕ ВРЕМЯ: {goal.get('time', '3-6 месяцев')}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {profile_code}
РАСШИФРОВКА ПРОФИЛЯ:
• СБ-{sb_level} — реакция на угрозу (1-2: замирает/избегает, 3-4: внешне спокоен, 5-6: защищает/атакует)
• ТФ-{tf_level} — деньги/ресурсы (1-2: хаотично, 3-4: стабильно, 5-6: системно/инвестиции)
• УБ-{ub_level} — понимание мира (1-2: верит в знаки, 3-4: доверяет экспертам, 5-6: анализирует сам)
• ЧВ-{chv_level} — отношения (1-2: привязывается, 3-4: хочет нравиться, 5-6: строит партнерство)

РЕЖИМ: {mode_info['emoji']} {mode_info['name']}
СТИЛЬ В ЭТОМ РЕЖИМЕ: {mode_info['style']}
ТОН: {mode_info['tone']}

ЗАДАЧА:
Создай маршрут из 3 ПОСЛЕДОВАТЕЛЬНЫХ ЭТАПОВ. Каждый этап должен быть конкретным, выполнимым и вести к следующему.

ДЛЯ КАЖДОГО ЭТАПА УКАЖИ:
📍 ЭТАП X: [НАЗВАНИЕ]
   • Что делаем: [конкретные действия, обсуждения, размышления]
   • 📝 Домашнее задание: [что нужно сделать между сессиями]
   • ✅ Критерий выполнения: [как понять, что этап пройден]

ВАЖНО:
1. Учитывай профиль пользователя:
   - Если СБ низкий (1-2) — будь мягче, избегай давления, давай техники заземления
   - Если ТФ низкий (1-2) — фокусируйся на маленьких шагах, базовой финансовой грамотности
   - Если УБ низкий (1-2) — давай больше структуры, объясняй простыми словами
   - Если ЧВ низкий (1-2) — работай с привязанностью, страхом отвержения

2. Адаптируй сложность под уровень пользователя:
   - Уровни 1-2: базовые, поддерживающие шаги
   - Уровни 3-4: развивающие, укрепляющие шаги
   - Уровни 5-6: продвинутые, масштабирующие шаги

3. Делай шаги маленькими и реалистичными:
   - Каждый этап должен занимать 1-2 недели
   - Домашнее задание — не более 15-20 минут в день
   - Критерии должны быть измеримыми

4. Используй метафоры и образы, соответствующие режиму:
   - Коуч: "путешествие", "карта", "компас"
   - Психолог: "глубина", "корни", "исцеление"
   - Тренер: "тренировка", "мышцы", "рекорды"

ФОРМАТ ОТВЕТА (строго соблюдай):

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

Напиши маршрут, соблюдая все инструкции."""
    
    logger.info(f"📝 Промпт для маршрута создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=f"Ты — {mode_info['emoji']} {mode_info['name']}, создающий эффективные маршруты развития.",
        max_tokens=1500,
        temperature=0.7
    )
    
    if response:
        logger.info(f"✅ Маршрут сгенерирован ({len(response)} символов)")
        logger.info(f"📝 Первые 200 символов ответа: {response[:200]}")
        return {
            "full_text": response,
            "steps": response.split("\n\n")  # Простое разбиение, можно улучшить
        }
    else:
        logger.error("❌ Не удалось сгенерировать маршрут")
        return None


# ============================================
# ГЕНЕРАЦИЯ ОТВЕТА НА ВОПРОС (ПОЛНЫЙ ПРОМТ)
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
    
    # Описания режимов
    mode_prompts = {
        "coach": {
            "role": "коуч",
            "style": """Ты — коуч. Твоя задача — помогать человеку находить ответы внутри себя через открытые вопросы и размышления.

ПРАВИЛА КОУЧА:
1. НЕ давай готовых ответов и советов
2. Задавай открытые вопросы: "Что ты чувствуешь?", "Как ты видишь эту ситуацию?", "Какие есть варианты?"
3. Отражай и перефразируй мысли человека
4. Помогай структурировать размышления
5. Верь, что человек сам знает ответы

ПРИМЕРЫ:
- "Расскажи подробнее об этой ситуации..."
- "Что для тебя самое важное в этом?"
- "Как бы ты хотел, чтобы это выглядело в идеале?"
- "Какие маленькие шаги ты можешь сделать уже сегодня?" """
        },
        "psychologist": {
            "role": "психолог",
            "style": """Ты — психолог. Твоя задача — исследовать глубинные паттерны, прошлый опыт, защитные механизмы.

ПРАВИЛА ПСИХОЛОГА:
1. Исследуй чувства и эмоции: "Что ты чувствуешь, когда думаешь об этом?"
2. Ищи связи с прошлым: "Было ли похожее раньше? Откуда это могло взяться?"
3. Обращай внимание на повторяющиеся сценарии
4. Работай с сопротивлением и защитами
5. Создавай безопасное пространство для исследования

ПРИМЕРЫ:
- "Когда ты впервые почувствовал это?"
- "Что для тебя самое страшное в этой ситуации?"
- "Если бы твоя тревога могла говорить, что бы она сказала?"
- "Как эта ситуация связана с твоим детством?" """
        },
        "trainer": {
            "role": "тренер",
            "style": """Ты — тренер. Твоя задача — давать четкие инструменты, навыки, упражнения для достижения результата.

ПРАВИЛА ТРЕНЕРА:
1. Давай конкретные, выполнимые задания
2. Структурируй процесс: "Сначала делаем А, потом Б, затем В"
3. Ставь дедлайны и требуй отчета
4. Формируй навыки через повторение
5. Измеряй прогресс

ПРИМЕРЫ:
- "Вот конкретное упражнение на эту неделю..."
- "Сделай это до следующей встречи и напиши результат"
- "Давай разберем это по шагам..."
- "Твоя задача на сегодня — сделать первый шаг" """
        }
    }
    
    mode_info = mode_prompts.get(mode, mode_prompts["coach"])
    
    # Формируем контекст
    profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
    
    context_text = ""
    if context:
        if hasattr(context, 'get_prompt_context'):
            context_text = context.get_prompt_context()
        else:
            context_text = str(context)
    
    history_text = ""
    if history and len(history) > 0:
        last_messages = history[-6:]  # последние 3 диалога (вопрос-ответ)
        history_text = "\n".join([
            f"{'🤖' if i%2==0 else '👤'}: {msg[:100]}..." 
            for i, msg in enumerate(last_messages)
        ])
    
    logger.info(f"📊 Контекст: профиль {profile_code}, история {len(history) if history else 0} сообщений")
    
    # Полный промт для ответа на вопрос
    prompt = f"""Ты — {mode_info['role']}, виртуальный помощник. Ответь на вопрос пользователя с учетом его профиля и контекста.

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{user_message}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {profile_code}
ДЕТАЛИ ПРОФИЛЯ:
{json.dumps(profile_data, ensure_ascii=False, indent=2, default=str)[:500]}

КОНТЕКСТ (время, погода, личные данные):
{context_text if context_text else "Контекст не указан"}

ИСТОРИЯ ДИАЛОГА (последние сообщения):
{history_text if history_text else "Нет истории"}

ТВОЙ СТИЛЬ КАК {mode_info['role'].upper()}:
{mode_info['style']}

ИНСТРУКЦИИ ПО ОТВЕТУ:
1. Учитывай профиль пользователя — его сильные стороны и зоны роста
2. Отвечай в стиле, соответствующем режиму ({mode_info['role']})
3. Используй эмодзи для эмоциональной окраски, но не перебарщивай
4. Не используй Markdown (**, __, и т.д.) — только обычный текст
5. Если нужно выделить важное, используй эмодзи или просто заглавные буквы
6. Ответ должен быть полезным и конкретным
7. Длина ответа: 3-5 предложений для простых вопросов, до 10 для сложных

ТВОЙ ОТВЕТ (без Markdown, с эмодзи где уместно):
"""
    
    logger.info(f"📝 Промпт для ответа создан, длина: {len(prompt)} символов")
    
    response = await call_deepseek(
        prompt=prompt,
        system_prompt=f"Ты — {mode_info['role']}, помогающий людям.",
        max_tokens=1000,
        temperature=0.7
    )
    
    # Генерируем предложения для дальнейшего диалога
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
    prompt = f"""На основе вопроса и ответа придумай 3 коротких варианта, что спросить дальше.

ВОПРОС: {question}
ОТВЕТ: {answer[:200]}...
ПРОФИЛЬ: {profile_code}
РЕЖИМ: {mode}

Требования:
- Каждый вариант не длиннее 7 слов
- Варианты должны быть связаны с темой
- Учитывай режим общения

Формат ответа: просто список, каждый вариант с новой строки, без нумерации
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
    
    logger.warning("⚠️ Не удалось сгенерировать предложения, используем стандартные")
    return [
        "Расскажи подробнее",
        "Что ты чувствуешь?",
        "Какие есть варианты?"
    ]


# ============================================
# РАСПОЗНАВАНИЕ РЕЧИ (DEEPGRAM)
# ============================================

async def speech_to_text(audio_file_path: str) -> Optional[str]:
    """
    Распознает речь из аудиофайла через Deepgram API
    """
    if not DEEPGRAM_API_KEY:
        logger.error("❌ DEEPGRAM_API_KEY не настроен")
        return None
    
    logger.info(f"🎤 Распознавание речи из файла: {audio_file_path}")
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg"
    }
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        logger.info(f"📊 Размер аудиофайла: {len(audio_data)} байт")
        
        params = {
            "model": "nova-2",
            "language": "ru",
            "punctuate": True,
            "diarize": False,
            "smart_format": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                DEEPGRAM_API_URL,
                headers=headers,
                params=params,
                data=audio_data,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
                    logger.info(f"✅ Речь распознана: {len(transcript)} символов")
                    logger.info(f"📝 Текст: {transcript[:200]}")
                    return transcript
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Deepgram API error {response.status}: {error_text[:200]}")
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка распознавания речи: {e}")
        logger.error(traceback.format_exc())
        return None


# ============================================
# СИНТЕЗ РЕЧИ (YANDEX)
# ============================================

async def text_to_speech(text: str, mode: str = "coach") -> Optional[bytes]:
    """
    Преобразует текст в речь через Yandex TTS
    """
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не настроен")
        return None
    
    logger.info(f"🎤 Синтез речи для текста: {len(text)} символов, режим: {mode}")
    
    # Выбираем голос в зависимости от режима
    voices = {
        "coach": "filipp",      # Филипп — коуч
        "psychologist": "ermil", # Эрмил — психолог
        "trainer": "filipp"      # Филипп — тренер (можно другой голос)
    }
    voice = voices.get(mode, "filipp")
    logger.info(f"🗣️ Выбран голос: {voice}")
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Ограничиваем длину текста (Yandex ограничение)
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
        async with aiohttp.ClientSession() as session:
            async with session.post(
                YANDEX_TTS_API_URL,
                headers=headers,
                data=data,
                timeout=30
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"✅ Речь синтезирована: {len(audio_data)} байт")
                    return audio_data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Yandex TTS API error {response.status}: {error_text[:200]}")
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка синтеза речи: {e}")
        logger.error(traceback.format_exc())
        return None


# ============================================
# ЭКСПОРТ ВСЕХ ФУНКЦИЙ
# ============================================

__all__ = [
    # Основные функции
    'generate_ai_profile',
    'generate_psychologist_thought',
    'generate_route_ai',
    'generate_response_with_full_context',
    'generate_suggestions',
    
    # Функции API
    'call_deepseek',
    
    # Функции для речи
    'speech_to_text',
    'text_to_speech',
    
    # Форматтеры
    'bold',
    'italic',
    'emoji_text',
    
    # Вспомогательные
    'make_json_serializable'
]
