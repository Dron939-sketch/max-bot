#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ 2.8 - ИСПРАВЛЕНО: Патч применяется ДО ВСЕХ импортов
"""

import os
import json
import pickle
import logging
import asyncio
import sys
from typing import Dict, Any, Optional

# ========== КРИТИЧЕСКИЙ ПАТЧ ДЛЯ ASYNCPG (ДОЛЖЕН БЫТЬ В САМОМ НАЧАЛЕ) ==========
import asyncpg
from asyncpg.pool import Pool

logger = logging.getLogger(__name__)

# Сохраняем оригинальную функцию ДО любых изменений
original_create_pool = asyncpg.create_pool

async def patched_create_pool(*args, **kwargs):
    """
    Исправленная версия create_pool для Python 3.14
    Добавляет явный loop и таймауты
    """
    # Получаем или создаем цикл событий
    try:
        loop = asyncio.get_running_loop()
        logger.debug(f"✅ Используем текущий цикл событий: {loop}")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.warning("⚠️ Создан новый цикл событий для пула соединений")
    
    # Для Python 3.14 добавляем loop в kwargs
    if sys.version_info >= (3, 14):
        kwargs['loop'] = loop
        logger.debug("✅ Добавлен loop в kwargs для Python 3.14")
    
    # Убеждаемся, что есть таймауты
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 60
        logger.debug("✅ Добавлен timeout=60")
    if 'command_timeout' not in kwargs:
        kwargs['command_timeout'] = 60
        logger.debug("✅ Добавлен command_timeout=60")
    
    # Добавляем небольшую задержку для инициализации контекста
    await asyncio.sleep(0.1)
    
    try:
        result = await original_create_pool(*args, **kwargs)
        logger.info("✅ Пул соединений успешно создан через патч")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка при создании пула через патч: {e}")
        raise

# Принудительно применяем патч (перезаписываем функцию)
asyncpg.create_pool = patched_create_pool
logger.info("🔥🔥🔥 ПАТЧ ПРИМЕНЁН В db_instance.py 🔥🔥🔥")

# Проверяем, что патч действительно применился
if asyncpg.create_pool is patched_create_pool:
    logger.info("✅ ПАТЧ РАБОТАЕТ: create_pool заменён на patched_create_pool")
else:
    logger.error("❌ ПАТЧ НЕ ПРИМЕНИЛСЯ! create_pool остался оригинальным")
# =================================================================================

# Теперь импортируем database (после применения патча)
from database import BotDatabase

# URL базы данных из переменных окружения Render
# Сначала пробуем внешний URL, затем внутренний, затем захардкоженный
DATABASE_URL = os.environ.get(
    "EXTERNAL_DATABASE_URL",  # Сначала внешний URL (для кросс-регионального подключения)
    os.environ.get(
        "DATABASE_URL",        # Потом внутренний URL (для подключения в одном регионе)
        "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
    )
)

# Логируем используемый URL (без пароля для безопасности)
url_parts = DATABASE_URL.split('@')
if len(url_parts) > 1:
    safe_url = f"postgresql://{url_parts[1]}"
else:
    safe_url = DATABASE_URL[:50] + "..." if len(DATABASE_URL) > 50 else DATABASE_URL
logger.info(f"🔗 Используем URL базы данных: {safe_url}")

# Создаем единый экземпляр БД
db = BotDatabase(DATABASE_URL)

async def init_db():
    """Инициализация подключения к БД"""
    try:
        # Для Python 3.14 добавляем небольшую задержку
        if sys.version_info >= (3, 14):
            await asyncio.sleep(0.2)
            logger.debug("✅ Задержка 0.2с для инициализации контекста")
        
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
# ✅ ФУНКЦИЯ ПРОВЕРКИ СОЕДИНЕНИЯ С БД (С ПАУЗАМИ)
# ============================================

async def ensure_db_connection():
    """Проверяет, установлено ли соединение с БД, и подключается если нет"""
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Проверяем, существует ли пул
            if db.pool is None:
                logger.info("🔄 Пул соединений не инициализирован, подключаемся...")
                await db.connect()
                return True
            
            # Проверяем, работает ли соединение
            async with db.get_connection() as conn:
                await conn.execute("SELECT 1")
            logger.debug("✅ Соединение с БД работает")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"❌ Ошибка при проверке соединения с БД (попытка {attempt+1}/{max_retries}): {e}")
            
            # Проверяем, связана ли ошибка с соединением или циклом событий
            if any(phrase in error_str for phrase in [
                "пул закрыт", "pool is closed", "connection", 
                "timeout", "ssl", "network", "reset", "another operation",
                "different loop", "attached to a different loop"
            ]):
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Повторная попытка через {retry_delay}с...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку
                    
                    # Пробуем переподключиться
                    try:
                        await db.disconnect()
                    except:
                        pass
                    
                    # Для Python 3.14 принудительно создаем новый контекст
                    if sys.version_info >= (3, 14):
                        await asyncio.sleep(0.2)
                    
                    continue
                else:
                    logger.warning(f"⚠️ Не удалось восстановить соединение после {max_retries} попыток")
                    return False
            else:
                # Если это не ошибка соединения, возвращаем False
                logger.warning(f"⚠️ Не связанная с соединением ошибка: {e}")
                return False
    
    return False

# ============================================
# ✅ ФУНКЦИЯ ДЛЯ ВЫПОЛНЕНИЯ С ПОВТОРНЫМИ ПОПЫТКАМИ
# ============================================

async def execute_with_retry(coro_func, *args, max_retries=3, **kwargs):
    """
    Выполняет асинхронную функцию с повторными попытками при ошибках соединения
    
    Args:
        coro_func: асинхронная функция для выполнения
        *args: позиционные аргументы для функции
        max_retries: максимальное количество попыток
        **kwargs: именованные аргументы для функции
    
    Returns:
        Результат выполнения функции или None в случае ошибки
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Проверяем соединение перед выполнением
            if not await ensure_db_connection():
                logger.warning(f"⚠️ Не удалось установить соединение с БД (попытка {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = 1 * (attempt + 1)
                    logger.info(f"⏳ Ожидание {wait_time}с перед следующей попыткой...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Все попытки подключения исчерпаны")
                    return None
            
            # Выполняем функцию
            if asyncio.iscoroutinefunction(coro_func):
                result = await coro_func(*args, **kwargs)
            else:
                # Если функция не асинхронная, выполняем в executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: coro_func(*args, **kwargs))
            
            return result
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Проверяем, связана ли ошибка с соединением или циклом событий
            if any(phrase in error_str for phrase in [
                "пул закрыт", "pool is closed", "connection", 
                "timeout", "ssl", "network", "reset", "another operation",
                "different loop", "attached to a different loop"
            ]):
                logger.warning(f"⚠️ Ошибка соединения с БД (попытка {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Увеличиваем задержку с каждой попыткой
                    wait_time = 1 * (attempt + 1)
                    logger.info(f"⏳ Ожидание {wait_time}с перед следующей попыткой...")
                    await asyncio.sleep(wait_time)
                    
                    # Принудительно сбрасываем соединение
                    try:
                        await db.disconnect()
                    except:
                        pass
                    continue
            else:
                # Если это не ошибка соединения, пробрасываем исключение
                logger.error(f"❌ Неожиданная ошибка: {e}")
                raise e
    
    # Если все попытки исчерпаны
    logger.error(f"❌ Все {max_retries} попыток выполнения исчерпаны. Последняя ошибка: {last_error}")
    return None

# ============================================
# ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ ДАННЫХ
# ============================================

async def save_user_to_db(
    user_id: int, 
    user_data_dict: Dict[int, Dict] = None, 
    user_contexts_dict: Dict[int, Any] = None, 
    user_routes_dict: Dict[int, Dict] = None
):
    """
    Сохраняет данные конкретного пользователя в БД
    Универсальная функция, которая принимает данные из state.py
    """
    try:
        # ✅ Используем execute_with_retry для всех операций с БД
        async def _do_save():
            # Если данные не переданы, пытаемся импортировать из state
            nonlocal user_data_dict, user_contexts_dict, user_routes_dict
            if user_data_dict is None or user_contexts_dict is None or user_routes_dict is None:
                try:
                    from state import user_data as global_user_data, user_contexts as global_user_contexts, user_routes as global_user_routes
                    user_data_dict = global_user_data if user_data_dict is None else user_data_dict
                    user_contexts_dict = global_user_contexts if user_contexts_dict is None else user_contexts_dict
                    user_routes_dict = global_user_routes if user_routes_dict is None else user_routes_dict
                except ImportError:
                    logger.warning(f"⚠️ Не удалось импортировать глобальные данные для user {user_id}")
                    return False
            
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
            
            # Сохраняем user_data (результаты тестов, профиль)
            if user_id in user_data_dict:
                await db.save_user_data(user_id, user_data_dict[user_id])
            
            # Сохраняем контекст (UserContext объект)
            if user_id in user_contexts_dict:
                context = user_contexts_dict[user_id]
                await db.save_user_context(user_id, context)
                # Также сохраняем pickled версию как резерв
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
            
            logger.debug(f"💾 Данные пользователя {user_id} сохранены в БД")
            return True
        
        # Выполняем с повторными попытками
        return await execute_with_retry(_do_save, max_retries=3)
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id} в БД после всех попыток: {e}")
        import traceback
        traceback.print_exc()
        return False

async def save_test_result_to_db(
    user_id: int,
    test_type: str,
    user_data_dict: Dict[int, Dict]
):
    """Сохраняет результаты теста в БД"""
    try:
        async def _do_save():
            data = user_data_dict.get(user_id, {})
            
            # Получаем profile_code из данных
            profile_code = None
            if data.get("profile_data"):
                profile_code = data["profile_data"].get("display_name")
            
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
            
            return test_id
        
        # Выполняем с повторными попытками
        return await execute_with_retry(_do_save, max_retries=3)
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
