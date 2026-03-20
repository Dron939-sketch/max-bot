#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ ДЛЯ PYTHON 3.11 - ИСПРАВЛЕНО: единый цикл событий + save_telegram_user
"""

import os
import json
import pickle
import logging
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import wraps
import signal
import sys

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

# Маскируем пароль в логах
url_parts = DATABASE_URL.split('@')
safe_url = f"postgresql://{url_parts[1]}" if len(url_parts) > 1 else DATABASE_URL[:50] + "..."
logger.info(f"🔗 Используем URL базы данных: {safe_url}")

# ============================================
# ГЛОБАЛЬНЫЙ МЕНЕДЖЕР ЦИКЛА БД
# ============================================

class DBLoopManager:
    """
    Единый менеджер для работы с циклом событий БД.
    Все асинхронные операции с БД должны выполняться через этот менеджер.
    """
    
    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._tasks = set()
        self._running = False
        self._db_instance: Optional[BotDatabase] = None
    
    def init(self, db_instance: BotDatabase):
        """Инициализирует цикл событий в отдельном потоке"""
        with self._lock:
            if self.loop is not None:
                logger.warning("⚠️ Цикл БД уже инициализирован")
                return
            
            self._db_instance = db_instance
            
            # Создаем новый цикл
            self.loop = asyncio.new_event_loop()
            
            # Запускаем поток с циклом
            self.thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="DB-Loop"
            )
            self.thread.start()
            
            # Ждем, пока цикл запустится
            future = asyncio.run_coroutine_threadsafe(
                self._init_db_in_loop(),
                self.loop
            )
            try:
                future.result(timeout=30)
                logger.info("✅ Глобальный цикл БД инициализирован")
            except TimeoutError:
                logger.error("❌ Таймаут инициализации цикла БД")
                raise
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации цикла БД: {e}")
                raise
    
    def _run_loop(self):
        """Запускает цикл событий в потоке"""
        asyncio.set_event_loop(self.loop)
        self._running = True
        try:
            self.loop.run_forever()
        finally:
            self._running = False
            # Закрываем все незавершенные задачи
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
            logger.info("🔒 Цикл БД остановлен")
    
    async def _init_db_in_loop(self):
        """Инициализирует БД внутри правильного цикла"""
        if self._db_instance:
            await self._db_instance.connect()
            logger.info("✅ Подключение к БД установлено в цикле")
    
    def run_coro(self, coro_func: Callable[..., Awaitable], *args, timeout: int = 30, **kwargs):
        """
        Запускает корутину в цикле БД и возвращает результат.
        Это основной метод для вызова из любого потока.
        
        Args:
            coro_func: Асинхронная функция
            *args: Аргументы для функции
            timeout: Таймаут в секундах
            **kwargs: Именованные аргументы
        
        Returns:
            Результат выполнения корутины
        
        Raises:
            TimeoutError: При превышении таймаута
            Exception: Любое исключение из корутины
        """
        if self.loop is None:
            raise RuntimeError("Цикл БД не инициализирован. Вызовите init()")
        
        # Проверяем, не вызваны ли мы уже из правильного цикла
        try:
            current_loop = asyncio.get_event_loop()
            if current_loop is self.loop:
                # Уже в правильном цикле - выполняем напрямую
                future = asyncio.ensure_future(coro_func(*args, **kwargs), loop=self.loop)
                return self.loop.run_until_complete(
                    asyncio.wait_for(future, timeout=timeout)
                )
        except RuntimeError:
            # Нет текущего цикла
            pass
        
        # Создаем Future в цикле БД
        future = asyncio.run_coroutine_threadsafe(
            coro_func(*args, **kwargs),
            self.loop
        )
        
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            logger.error(f"❌ Таймаут {timeout}с при выполнении {coro_func.__name__}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении {coro_func.__name__}: {e}")
            raise
    
    def run_task(self, coro_func: Callable[..., Awaitable], *args, **kwargs):
        """
        Запускает корутину как фоновую задачу (fire-and-forget)
        
        Args:
            coro_func: Асинхронная функция
            *args: Аргументы
            **kwargs: Именованные аргументы
        
        Returns:
            asyncio.Task: Задача (можно отменить при необходимости)
        """
        if self.loop is None:
            raise RuntimeError("Цикл БД не инициализирован")
        
        async def _wrapped():
            try:
                return await coro_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой задаче {coro_func.__name__}: {e}")
                return None
        
        task = asyncio.run_coroutine_threadsafe(_wrapped(), self.loop)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task
    
    def shutdown(self):
        """Корректное завершение работы"""
        if self.loop and self.loop.is_running():
            logger.info("🛑 Останавливаем цикл БД...")
            
            # Отменяем все задачи
            for task in list(self._tasks):
                task.cancel()
            
            # Останавливаем цикл
            self.loop.call_soon_threadsafe(self.loop.stop)
            
            # Ждем завершения потока
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=10)
            
            logger.info("✅ Цикл БД остановлен")

# ============================================
# ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ
# ============================================

# Создаем экземпляр БД
db = BotDatabase(DATABASE_URL)

# Создаем менеджер цикла
db_loop_manager = DBLoopManager()

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================

async def init_db():
    """Инициализация подключения к БД"""
    try:
        # Инициализируем менеджер цикла (он сам создаст подключение)
        db_loop_manager.init(db)
        logger.info("✅ Подключение к PostgreSQL установлено")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

async def close_db():
    """Закрытие подключения к БД"""
    try:
        if db and db.pool:
            # Закрываем через менеджер
            db_loop_manager.run_coro(db.disconnect, timeout=10)
            logger.info("🔒 Подключение к PostgreSQL закрыто")
        
        # Останавливаем менеджер
        db_loop_manager.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии подключения: {e}")

# ============================================
# ПРОВЕРКА СОЕДИНЕНИЯ
# ============================================

async def ensure_db_connection():
    """Проверяет соединение с БД через менеджер"""
    try:
        if db.pool is None:
            logger.info("🔄 Пул соединений не инициализирован, подключаемся...")
            await db.connect()
            return True
        
        # Проверяем соединение
        async with db.get_connection() as conn:
            await conn.execute("SELECT 1")
        
        logger.debug("✅ Соединение с БД работает")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке соединения: {e}")
        
        # Пробуем переподключиться
        try:
            if db.pool:
                await db.disconnect()
            await db.connect()
            logger.info("✅ Соединение восстановлено")
            return True
        except Exception as e2:
            logger.error(f"❌ Не удалось восстановить соединение: {e2}")
            return False

# ============================================
# ВЫПОЛНЕНИЕ С ПОВТОРАМИ
# ============================================

async def execute_with_retry(coro_func, *args, max_retries=3, **kwargs):
    """
    Выполняет функцию с повторными попытками через менеджер цикла
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Используем менеджер для выполнения
            result = db_loop_manager.run_coro(
                coro_func, *args, timeout=30, **kwargs
            )
            return result
            
        except TimeoutError as e:
            last_error = e
            logger.warning(f"⚠️ Таймаут (попытка {attempt+1}/{max_retries})")
            
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ Ошибка (попытка {attempt+1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(1 * (attempt + 1))
    
    logger.error(f"❌ Все попытки исчерпаны: {last_error}")
    return None

# ============================================
# ОБЕРТКА ДЛЯ СИНХРОННЫХ ВЫЗОВОВ
# ============================================

def sync_db_call(coro_func):
    """
    Декоратор для синхронных функций, которые нужно выполнить в цикле БД
    
    Пример:
        @sync_db_call
        def save_user(user_id):
            return db_loop_manager.run_coro(save_user_to_db, user_id)
    """
    @wraps(coro_func)
    def wrapper(*args, **kwargs):
        return db_loop_manager.run_coro(coro_func, *args, **kwargs)
    return wrapper

# ============================================
# СОХРАНЕНИЕ ДАННЫХ
# ============================================

async def save_telegram_user_async(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    language_code: str = None
) -> bool:
    """
    Асинхронная версия сохранения пользователя Telegram
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения пользователя {user_id}")
            return False
        
        # Сохраняем пользователя
        result = await db.save_telegram_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
        logger.debug(f"💾 Пользователь {user_id} сохранен в БД")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
        return False


def save_telegram_user(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    language_code: str = None
) -> bool:
    """
    СИНХРОННАЯ обертка для сохранения пользователя Telegram
    """
    return db_loop_manager.run_coro(
        save_telegram_user_async,
        user_id,
        username,
        first_name,
        last_name,
        language_code,
        timeout=30
    )


async def save_user_to_db_async(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """
    Асинхронная версия сохранения (для вызова через менеджер)
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения {user_id}")
            return False
        
        # Импортируем глобальные словари, если параметры не переданы
        if user_data_dict is None:
            from state import user_data as global_user_data
            user_data_dict = global_user_data
        
        if user_contexts_dict is None:
            from state import user_contexts as global_user_contexts
            user_contexts_dict = global_user_contexts
        
        if user_routes_dict is None:
            from state import user_routes as global_user_routes
            user_routes_dict = global_user_routes
        
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
        
        logger.info(f"💾 Пользователь {user_id} успешно сохранен в БД")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_user_to_db(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """
    Синхронная обертка для сохранения (вызывается из любого потока)
    """
    return db_loop_manager.run_coro(
        save_user_to_db_async,
        user_id,
        user_data_dict,
        user_contexts_dict,
        user_routes_dict,
        timeout=30
    )


async def save_test_result_to_db_async(user_id, test_type, user_data_dict=None):
    """
    Асинхронная версия сохранения результатов теста
    """
    try:
        # Проверяем соединение
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения результатов {user_id}")
            return None
        
        if user_data_dict is None:
            from state import user_data as global_user_data
            user_data_dict = global_user_data
        
        data = user_data_dict.get(user_id, {})
        
        if not data:
            logger.warning(f"⚠️ Нет данных для пользователя {user_id}")
            return None
        
        # Получаем profile_code
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        elif data.get("ai_generated_profile"):
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
        
        # Сохраняем все ответы
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


def save_test_result_to_db(user_id, test_type, user_data_dict=None):
    """
    Синхронная обертка для сохранения результатов теста
    """
    return db_loop_manager.run_coro(
        save_test_result_to_db_async,
        user_id,
        test_type,
        user_data_dict,
        timeout=30
    )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'db',
    'db_loop_manager',
    'init_db',
    'close_db',
    'save_telegram_user',
    'save_user_to_db',
    'save_test_result_to_db',
    'ensure_db_connection',
    'execute_with_retry',
    'sync_db_call'
]
