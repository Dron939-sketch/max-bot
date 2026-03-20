#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ ДЛЯ PYTHON 3.11 - БЕЗ ГЛОБАЛЬНОГО ЦИКЛА
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
# СОХРАНЕНИЕ ДАННЫХ - УПРОЩЕННЫЕ ВЕРСИИ
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
        
        # Сохраняем пользователя
        if user_id in user_data_dict:
            user_info = user_data_dict[user_id]
            first_name = user_info.get('first_name') or user_info.get('name')
            username = user_info.get('username')
            
            await db.save_telegram_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        
        # Сохраняем user_data
        if user_id in user_data_dict:
            await db.save_user_data(user_id, user_data_dict[user_id])
        
        # Сохраняем контекст
        if user_id in user_contexts_dict:
            context = user_contexts_dict[user_id]
            await db.save_user_context(user_id, context)
            await db.save_pickled_context(user_id, context)
        
        # Сохраняем маршрут
        if user_id in user_routes_dict:
            route = user_routes_dict[user_id]
            await db.save_user_route(
                user_id=user_id,
                route_data=route.get('route_data', {}),
                current_step=route.get('current_step', 1),
                progress=route.get('progress', [])
            )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
        return False

async def save_test_result_to_db(user_id, test_type, user_data_dict):
    """
    Сохраняет результаты теста в БД
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения результатов {user_id}")
            return None
        
        data = user_data_dict.get(user_id, {})
        
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        
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
        
        return test_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
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
