#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ ДЛЯ PYTHON 3.11 - С ГЛОБАЛЬНЫМ ЦИКЛОМ
"""

import os
import json
import pickle
import logging
import asyncio
import threading
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# Импортируем класс БД
from database import BotDatabase

logger = logging.getLogger(__name__)

# ============================================
# ГЛОБАЛЬНЫЙ ЦИКЛ СОБЫТИЙ ДЛЯ БАЗЫ ДАННЫХ
# ============================================
_db_loop = None
_db_loop_thread = None
_db_executor = ThreadPoolExecutor(max_workers=2)
_db_lock = threading.Lock()

def get_db_loop():
    """Возвращает глобальный цикл событий для БД, создавая его при необходимости"""
    global _db_loop, _db_loop_thread
    
    with _db_lock:
        if _db_loop is None or (_db_loop_thread and not _db_loop_thread.is_alive()):
            _db_loop = asyncio.new_event_loop()
            _db_loop_thread = threading.Thread(target=_run_db_loop, daemon=True, name="DB-Loop")
            _db_loop_thread.start()
            logger.info("✅ Создан новый глобальный цикл для БД")
    
    return _db_loop

def _run_db_loop():
    """Запускает цикл событий БД в отдельном потоке"""
    global _db_loop
    asyncio.set_event_loop(_db_loop)
    try:
        _db_loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка в цикле БД: {e}")
    finally:
        logger.info("🔚 Цикл БД завершен")

def run_db_coro(coro):
    """
    Безопасно запускает корутину в глобальном цикле БД
    Возвращает Future, который можно await
    """
    loop = get_db_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop)

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

# Логируем URL без пароля
url_parts = DATABASE_URL.split('@')
safe_url = f"postgresql://{url_parts[1]}" if len(url_parts) > 1 else DATABASE_URL[:50] + "..."
logger.info(f"🔗 Используем URL базы данных: {safe_url}")

# Создаем единый экземпляр БД
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
    global _db_loop
    try:
        await db.disconnect()
        logger.info("🔒 Подключение к PostgreSQL закрыто")
        
        # Останавливаем цикл БД
        if _db_loop:
            _db_loop.call_soon_threadsafe(_db_loop.stop)
            logger.info("🛑 Цикл БД остановлен")
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
            
            async with db.get_connection() as conn:
                await conn.execute("SELECT 1")
            logger.debug("✅ Соединение с БД работает")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке соединения (попытка {attempt+1}/{max_retries}): {e}")
            
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
# СОХРАНЕНИЕ ДАННЫХ (обернуто в глобальный цикл)
# ============================================

def _save_user_to_db_sync(user_id, user_data_dict, user_contexts_dict, user_routes_dict):
    """
    Синхронная обертка для сохранения пользователя
    Запускается в отдельном потоке
    """
    try:
        # Создаем временный цикл для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _save():
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
        
        result = loop.run_until_complete(_save())
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
        return False

async def save_user_to_db(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """
    Сохраняет данные пользователя в БД (асинхронная версия)
    """
    try:
        # Запускаем в отдельном потоке через executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _db_executor,
            _save_user_to_db_sync,
            user_id, user_data_dict, user_contexts_dict, user_routes_dict
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении пользователя {user_id}: {e}")
        return False

async def save_test_result_to_db(user_id, test_type, user_data_dict):
    """
    Сохраняет результаты теста в БД
    """
    try:
        data = user_data_dict.get(user_id, {})
        
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        
        # Запускаем сохранение в отдельном потоке
        loop = asyncio.get_event_loop()
        
        def _save_sync():
            save_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(save_loop)
            
            async def _save():
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
                
                # Сохраняем ответы
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
            
            result = save_loop.run_until_complete(_save())
            save_loop.close()
            return result
        
        return await loop.run_in_executor(_db_executor, _save_sync)
        
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
    'execute_with_retry',
    'run_db_coro',
    'get_db_loop'
]
