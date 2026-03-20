#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ ДЛЯ PYTHON 3.11 - ИСПРАВЛЕНО: обработка None параметров
"""

import os
import json
import pickle
import logging
import asyncio
import threading
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from database import BotDatabase

logger = logging.getLogger(__name__)

# ============================================
# URL базы данных
# ============================================
DATABASE_URL = os.environ.get(
    "EXTERNAL_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
    )
)

url_parts = DATABASE_URL.split('@')
safe_url = f"postgresql://{url_parts[1]}" if len(url_parts) > 1 else DATABASE_URL[:50] + "..."
logger.info(f"🔗 Используем URL базы данных: {safe_url}")

db = BotDatabase(DATABASE_URL)

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================

async def init_db():
    """Инициализация подключения к БД"""
    try:
        await db.connect()
        logger.info("✅ Подключение к PostgreSQL установлено")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

async def close_db():
    """Закрытие подключения к БД"""
    try:
        await db.disconnect()
        logger.info("🔒 Подключение к PostgreSQL закрыто")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии подключения: {e}")

# ============================================
# ПРОВЕРКА СОЕДИНЕНИЯ
# ============================================

async def ensure_db_connection():
    """Проверяет соединение с БД"""
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            if db.pool is None:
                logger.info("🔄 Пул соединений не инициализирован, подключаемся...")
                await db.connect()
                return True
            
            # Простая проверка, что пул жив
            async with db.get_connection() as conn:
                await conn.execute("SELECT 1")
            logger.debug("✅ Соединение с БД работает")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке соединения (попытка {attempt+1}/{max_retries}): {e}")
            
            # Если пул умер, пробуем пересоздать
            if "connection was closed" in str(e) or "another operation" in str(e):
                try:
                    await db.disconnect()
                except:
                    pass
                db.pool = None
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Повтор через {retry_delay}с...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.warning(f"⚠️ Не удалось восстановить соединение")
                return False
    
    return False

# ============================================
# ВЫПОЛНЕНИЕ С ПОВТОРАМИ
# ============================================

async def execute_with_retry(coro_func, *args, max_retries=3, **kwargs):
    """
    Выполняет функцию с повторными попытками
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Проверяем соединение перед выполнением
            if not await ensure_db_connection():
                logger.warning(f"⚠️ Нет соединения с БД (попытка {attempt+1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                else:
                    logger.error(f"❌ Все попытки подключения исчерпаны")
                    return None
            
            if asyncio.iscoroutinefunction(coro_func):
                result = await coro_func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: coro_func(*args, **kwargs))
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ Ошибка (попытка {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))
            else:
                logger.error(f"❌ Все попытки исчерпаны: {last_error}")
    
    return None

# ============================================
# СОХРАНЕНИЕ ДАННЫХ - ИСПРАВЛЕННАЯ ВЕРСИЯ
# ============================================

async def save_user_to_db(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """
    Сохраняет данные пользователя в БД
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения {user_id}")
            return False
        
        # ✅ ИСПРАВЛЕНО: импортируем глобальные словари, если параметры не переданы
        if user_data_dict is None:
            from state import user_data as global_user_data
            user_data_dict = global_user_data
            logger.debug(f"📦 Используем глобальный user_data для {user_id}")
        
        if user_contexts_dict is None:
            from state import user_contexts as global_user_contexts
            user_contexts_dict = global_user_contexts
            logger.debug(f"📦 Используем глобальный user_contexts для {user_id}")
        
        if user_routes_dict is None:
            from state import user_routes as global_user_routes
            user_routes_dict = global_user_routes
            logger.debug(f"📦 Используем глобальный user_routes для {user_id}")
        
        # ✅ ИСПРАВЛЕНО: проверяем наличие user_id в словарях
        # Сохраняем пользователя в таблицу fredi_users
        if user_id in user_data_dict:
            user_info = user_data_dict[user_id]
            first_name = user_info.get('first_name') or user_info.get('name')
            username = user_info.get('username')
            
            await db.save_telegram_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            logger.debug(f"👤 Пользователь {user_id} сохранен в fredi_users")
        
        # Сохраняем user_data (результаты тестов, профиль)
        if user_id in user_data_dict:
            await db.save_user_data(user_id, user_data_dict[user_id])
            logger.debug(f"📊 Данные пользователя {user_id} сохранены в fredi_user_data")
        
        # Сохраняем контекст (UserContext объект)
        if user_id in user_contexts_dict:
            context = user_contexts_dict[user_id]
            await db.save_user_context(user_id, context)
            # Также сохраняем pickled версию как резерв
            await db.save_pickled_context(user_id, context)
            logger.debug(f"📍 Контекст пользователя {user_id} сохранен в БД")
        
        # Сохраняем маршрут
        if user_id in user_routes_dict:
            route = user_routes_dict[user_id]
            await db.save_user_route(
                user_id=user_id,
                route_data=route.get('route_data', {}),
                current_step=route.get('current_step', 1),
                progress=route.get('progress', [])
            )
            logger.debug(f"🗺 Маршрут пользователя {user_id} сохранен в БД")
        
        logger.info(f"💾 Пользователь {user_id} успешно сохранен в БД")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def save_test_result_to_db(user_id, test_type, user_data_dict=None):
    """
    Сохраняет результаты теста в БД
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения результатов {user_id}")
            return None
        
        # ✅ ИСПРАВЛЕНО: используем глобальный словарь, если не передан
        if user_data_dict is None:
            from state import user_data as global_user_data
            user_data_dict = global_user_data
            logger.debug(f"📦 Используем глобальный user_data для {user_id}")
        
        data = user_data_dict.get(user_id, {})
        
        if not data:
            logger.warning(f"⚠️ Нет данных для пользователя {user_id}")
            return None
        
        # Получаем profile_code
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        elif data.get("ai_generated_profile"):
            # Пытаемся извлечь код из AI профиля
            import re
            match = re.search(r'СБ-\d+_ТФ-\d+_УБ-\d+_ЧВ-\d+', data.get("ai_generated_profile", ""))
            if match:
                profile_code = match.group(0)
        
        # Сохраняем результат теста
        test_id = await db.save_test_result(
            user_id=user_id,
            test_type=test_type,
            results=data,
            profile_code=profile_code,
            perception_type=data.get("perception_type"),
            thinking_level=data.get("thinking_level"),
            vectors=data.get("behavioral_levels"),
            deep_patterns=data.get("deep_patterns"),
            confinement_model=data.get("confinement_model")
        )
        
        # Сохраняем все ответы, если есть
        all_answers = data.get("all_answers", [])
        if all_answers and test_id:
            for answer in all_answers:
                await db.save_test_answer(
                    user_id=user_id,
                    test_result_id=test_id,
                    stage=answer.get('stage', 0),
                    question_index=answer.get('question_index', 0),
                    question_text=answer.get('question', ''),
                    answer_text=answer.get('answer', ''),
                    answer_value=answer.get('option', ''),
                    scores=answer.get('scores'),
                    measures=answer.get('measures'),
                    strategy=answer.get('strategy'),
                    dilts=answer.get('dilts'),
                    pattern=answer.get('pattern'),
                    target=answer.get('target')
                )
        
        logger.info(f"📝 Результаты теста для пользователя {user_id} сохранены (ID: {test_id})")
        return test_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'db',
    'init_db',
    'close_db',
    'save_user_to_db',
    'save_test_result_to_db',
    'ensure_db_connection',
    'execute_with_retry'
]
