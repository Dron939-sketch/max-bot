#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ 3.1 - ИСПРАВЛЕНО: блокировка операций и правильная обработка соединений
"""

import os
import json
import pickle
import logging
import asyncio
import threading
import inspect
import traceback
from typing import Dict, Any, Optional, Callable, Awaitable, List
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
        self._operation_lock = asyncio.Lock()  # Блокировка для операций
    
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
            try:
                await self._db_instance.connect()
                logger.info("✅ Подключение к БД установлено в цикле")
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к БД: {e}")
                raise
    
    def run_coro(self, coro_func: Callable[..., Awaitable], *args, timeout: int = 30, **kwargs):
        """
        Запускает корутину в цикле БД и возвращает результат.
        Это основной метод для вызова из любого потока.
        """
        if self.loop is None:
            raise RuntimeError("Цикл БД не инициализирован. Вызовите init()")
        
        # Проверяем тип переданного объекта
        is_coro_func = inspect.iscoroutinefunction(coro_func)
        is_coro = inspect.iscoroutine(coro_func)
        
        if not is_coro_func and not is_coro:
            raise TypeError(f"{coro_func} is not a coroutine or coroutine function")
        
        # Оборачиваем в блокировку для предотвращения конфликтов
        async def _wrapped():
            try:
                async with self._operation_lock:
                    if is_coro:
                        return await coro_func
                    else:
                        return await coro_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в _wrapped: {e}")
                raise
        
        future = asyncio.run_coroutine_threadsafe(_wrapped(), self.loop)
        
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            logger.error(f"❌ Таймаут {timeout}с при выполнении")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении: {e}")
            raise
    
    def run_task(self, coro_func: Callable[..., Awaitable], *args, **kwargs):
        """
        Запускает корутину как фоновую задачу (fire-and-forget)
        """
        if self.loop is None:
            raise RuntimeError("Цикл БД не инициализирован")
        
        is_coro_func = inspect.iscoroutinefunction(coro_func)
        is_coro = inspect.iscoroutine(coro_func)
        
        if not is_coro_func and not is_coro:
            raise TypeError(f"{coro_func} is not a coroutine or coroutine function")
        
        async def _wrapped():
            try:
                async with self._operation_lock:
                    if is_coro:
                        return await coro_func
                    else:
                        return await coro_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой задаче: {e}")
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
            # Используем run_coro для закрытия
            db_loop_manager.run_coro(db.disconnect, timeout=10)
            logger.info("🔒 Подключение к PostgreSQL закрыто")
        
        # Останавливаем менеджер
        db_loop_manager.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии подключения: {e}")

# ============================================
# ПРОВЕРКА СОЕДИНЕНИЯ С ПОВТОРНЫМИ ПОПЫТКАМИ
# ============================================

async def ensure_db_connection(max_retries: int = 3, delay: float = 1.0):
    """
    Проверяет соединение с БД с повторными попытками
    """
    for attempt in range(max_retries):
        try:
            # Добавляем задержку между попытками
            if attempt > 0:
                await asyncio.sleep(delay * (2 ** attempt))
            
            # Если пула нет - подключаемся
            if db.pool is None:
                logger.info(f"🔄 Подключаемся... (попытка {attempt + 1}/{max_retries})")
                await db.connect()
                logger.info("✅ Подключение к БД установлено")
                return True
            
            # Используем короткий таймаут для проверки
            try:
                async with asyncio.timeout(5):
                    async with db.get_connection() as conn:
                        await conn.execute("SELECT 1")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Таймаут проверки соединения (попытка {attempt + 1})")
                if db.pool:
                    await db.disconnect()
                    db.pool = None
                continue
            
            logger.debug("✅ Соединение с БД работает")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка (попытка {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
            
            if attempt < max_retries - 1:
                try:
                    if db.pool:
                        await db.disconnect()
                        db.pool = None
                        logger.info("🔌 Пул закрыт")
                except Exception as disconnect_error:
                    logger.warning(f"⚠️ Ошибка при закрытии: {disconnect_error}")
                
                await asyncio.sleep(delay * (2 ** attempt))
            else:
                logger.error(f"❌ Все попытки ({max_retries}) исчерпаны")
                return False
    
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
            wait_time = 1 * (attempt + 1)
            await asyncio.sleep(wait_time)
    
    logger.error(f"❌ Все попытки исчерпаны: {last_error}")
    return None

# ============================================
# ОБЕРТКА ДЛЯ СИНХРОННЫХ ВЫЗОВОВ
# ============================================

def sync_db_call(coro_func):
    """
    Декоратор для синхронных функций, которые нужно выполнить в цикле БД
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
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения пользователя {user_id}")
            return False
        
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
        logger.error(traceback.format_exc())
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
    try:
        result = db_loop_manager.run_coro(
            save_telegram_user_async,
            user_id,
            username,
            first_name,
            last_name,
            language_code,
            timeout=30
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_telegram_user: {e}")
        return False


async def log_event_async(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Асинхронная версия логирования"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для логирования {user_id}")
            return False
        
        return await db.log_event(user_id, event_type, event_data or {})
    except Exception as e:
        logger.error(f"❌ Ошибка логирования: {e}")
        return False


def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Синхронная обертка для логирования"""
    try:
        result = db_loop_manager.run_coro(
            log_event_async,
            user_id,
            event_type,
            event_data,
            timeout=10
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка log_event: {e}")
        return False


async def save_user_to_db_async(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """
    Асинхронная версия сохранения (для вызова через менеджер)
    """
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения {user_id}")
            return False
        
        if user_data_dict is None:
            from state import user_data as global_user_data
            user_data_dict = global_user_data
        
        if user_contexts_dict is None:
            from state import user_contexts as global_user_contexts
            user_contexts_dict = global_user_contexts
        
        if user_routes_dict is None:
            from state import user_routes as global_user_routes
            user_routes_dict = global_user_routes
        
        if user_id in user_data_dict:
            user_info = user_data_dict[user_id]
            first_name = user_info.get('first_name') or user_info.get('name')
            username = user_info.get('username')
            
            await db.save_telegram_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        
        if user_id in user_data_dict:
            await db.save_user_data(user_id, user_data_dict[user_id])
        
        if user_id in user_contexts_dict:
            context = user_contexts_dict[user_id]
            await db.save_user_context(user_id, context)
            await db.save_pickled_context(user_id, context)
        
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
    try:
        result = db_loop_manager.run_coro(
            save_user_to_db_async,
            user_id,
            user_data_dict,
            user_contexts_dict,
            user_routes_dict,
            timeout=30
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_user_to_db: {e}")
        return False


# ============================================
# СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ТЕСТА
# ============================================

async def save_test_result_to_db_async(
    user_id: int, 
    test_type: str, 
    results: Dict = None,
    profile_code: str = None,
    perception_type: str = None,
    thinking_level: int = None,
    vectors: Dict = None,
    behavioral_levels: Dict = None,
    deep_patterns: Dict = None,
    confinement_model: Dict = None,
    user_data_dict: Dict = None
) -> Optional[int]:
    """
    Асинхронная версия сохранения результатов теста
    Принимает все параметры, которые передаются из db_sync.py
    """
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения результатов {user_id}")
            return None
        
        # Получаем данные пользователя
        if user_data_dict is not None:
            data = user_data_dict.get(user_id, {})
        else:
            try:
                from state import user_data as global_user_data
                data = global_user_data.get(user_id, {})
            except ImportError:
                data = results or {}
        
        if not data and results:
            data = results
        
        if not data:
            logger.warning(f"⚠️ Нет данных для пользователя {user_id}")
            return None
        
        # Получаем profile_code если не передан
        if not profile_code:
            if data.get("profile_data"):
                profile_code = data["profile_data"].get("display_name")
            elif data.get("ai_generated_profile"):
                import re
                match = re.search(r'СБ-\d+_ТФ-\d+_УБ-\d+_ЧВ-\d+', data.get("ai_generated_profile", ""))
                if match:
                    profile_code = match.group(0)
        
        # Используем переданные значения или берем из data
        final_perception_type = perception_type or data.get("perception_type")
        final_thinking_level = thinking_level or data.get("thinking_level")
        final_vectors = vectors or data.get("behavioral_levels")
        final_behavioral_levels = behavioral_levels or data.get("behavioral_levels")
        final_deep_patterns = deep_patterns or data.get("deep_patterns")
        final_confinement_model = confinement_model or data.get("confinement_model")
        
        test_id = await db.save_test_result(
            user_id=user_id,
            test_type=test_type,
            results=data,
            profile_code=profile_code,
            perception_type=final_perception_type,
            thinking_level=final_thinking_level,
            vectors=final_vectors,
            behavioral_levels=final_behavioral_levels,
            deep_patterns=final_deep_patterns,
            confinement_model=final_confinement_model
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
        
        logger.info(f"📝 Результаты теста для пользователя {user_id} сохранены (ID: {test_id})")
        return test_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_test_result_to_db(
    user_id: int, 
    test_type: str, 
    results: Dict = None,
    profile_code: str = None,
    perception_type: str = None,
    thinking_level: int = None,
    vectors: Dict = None,
    behavioral_levels: Dict = None,
    deep_patterns: Dict = None,
    confinement_model: Dict = None,
    user_data_dict: Dict = None
) -> Optional[int]:
    """
    Синхронная обертка для сохранения результатов теста
    """
    try:
        result = db_loop_manager.run_coro(
            save_test_result_to_db_async,
            user_id,
            test_type,
            results,
            profile_code,
            perception_type,
            thinking_level,
            vectors,
            behavioral_levels,
            deep_patterns,
            confinement_model,
            user_data_dict,
            timeout=30
        )
        return result if result is not None else None
    except Exception as e:
        logger.error(f"❌ Ошибка save_test_result_to_db: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ
# ============================================

async def get_user_context_async(user_id: int) -> Optional[Dict]:
    """Асинхронное получение контекста пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения контекста {user_id}")
            return None
        return await db.load_user_context(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_context_async: {e}")
        return None

def get_user_context(user_id: int) -> Optional[Dict]:
    """Синхронное получение контекста пользователя"""
    try:
        return db_loop_manager.run_coro(get_user_context_async, user_id, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_context: {e}")
        return None


async def get_user_data_async(user_id: int) -> Optional[Dict]:
    """Асинхронное получение данных пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения данных {user_id}")
            return None
        return await db.load_user_data(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_data_async: {e}")
        return None

def get_user_data(user_id: int) -> Optional[Dict]:
    """Синхронное получение данных пользователя"""
    try:
        return db_loop_manager.run_coro(get_user_data_async, user_id, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_data: {e}")
        return None


async def get_telegram_user_async(user_id: int) -> Optional[Dict]:
    """Асинхронное получение пользователя Telegram"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения пользователя {user_id}")
            return None
        return await db.get_telegram_user(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка get_telegram_user_async: {e}")
        return None

def get_telegram_user(user_id: int) -> Optional[Dict]:
    """Синхронное получение пользователя Telegram"""
    try:
        return db_loop_manager.run_coro(get_telegram_user_async, user_id, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_telegram_user: {e}")
        return None


async def get_user_test_results_async(user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
    """Асинхронное получение результатов тестов"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения результатов {user_id}")
            return []
        return await db.get_user_test_results(user_id, limit, test_type)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_test_results_async: {e}")
        return []

def get_user_test_results(user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
    """Синхронное получение результатов тестов"""
    try:
        return db_loop_manager.run_coro(get_user_test_results_async, user_id, limit, test_type, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_test_results: {e}")
        return []


async def add_reminder_async(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
    """Асинхронное добавление напоминания"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для добавления напоминания {user_id}")
            return None
        return await db.add_reminder(user_id, reminder_type, remind_at, data)
    except Exception as e:
        logger.error(f"❌ Ошибка add_reminder_async: {e}")
        return None

def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
    """Синхронное добавление напоминания"""
    try:
        return db_loop_manager.run_coro(add_reminder_async, user_id, reminder_type, remind_at, data, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка add_reminder: {e}")
        return None


async def get_pending_reminders_async(limit: int = 100) -> List[Dict]:
    """Асинхронное получение неотправленных напоминаний"""
    try:
        if not await ensure_db_connection():
            logger.error("❌ Нет соединения с БД для получения напоминаний")
            return []
        return await db.get_pending_reminders(limit)
    except Exception as e:
        logger.error(f"❌ Ошибка get_pending_reminders_async: {e}")
        return []

def get_pending_reminders(limit: int = 100) -> List[Dict]:
    """Синхронное получение неотправленных напоминаний"""
    try:
        return db_loop_manager.run_coro(get_pending_reminders_async, limit, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_pending_reminders: {e}")
        return []


async def get_cached_weekend_ideas_async(user_id: int) -> Optional[str]:
    """Асинхронное получение кэшированных идей"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения идей {user_id}")
            return None
        return await db.get_cached_weekend_ideas(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка get_cached_weekend_ideas_async: {e}")
        return None

def get_cached_weekend_ideas(user_id: int) -> Optional[str]:
    """Синхронное получение кэшированных идей"""
    try:
        return db_loop_manager.run_coro(get_cached_weekend_ideas_async, user_id, timeout=5)
    except Exception as e:
        logger.error(f"❌ Ошибка get_cached_weekend_ideas: {e}")
        return None


async def cache_weekend_ideas_async(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
    """Асинхронное сохранение идей в кэш"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения идей {user_id}")
            return False
        return await db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level)
    except Exception as e:
        logger.error(f"❌ Ошибка cache_weekend_ideas_async: {e}")
        return False

def cache_weekend_ideas(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
    """Синхронное сохранение идей в кэш"""
    try:
        return db_loop_manager.run_coro(cache_weekend_ideas_async, user_id, ideas_text, main_vector, main_level, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка cache_weekend_ideas: {e}")
        return False


async def get_user_reminders_async(user_id: int, include_sent: bool = False) -> List[Dict]:
    """Асинхронное получение напоминаний пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения напоминаний {user_id}")
            return []
        return await db.get_user_reminders(user_id, include_sent)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_reminders_async: {e}")
        return []

def get_user_reminders(user_id: int, include_sent: bool = False) -> List[Dict]:
    """Синхронное получение напоминаний пользователя"""
    try:
        return db_loop_manager.run_coro(get_user_reminders_async, user_id, include_sent, timeout=10)
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_reminders: {e}")
        return []


async def mark_reminder_sent_async(reminder_id: int) -> bool:
    """Асинхронная отметка напоминания как отправленного"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для отметки напоминания {reminder_id}")
            return False
        await db.mark_reminder_sent(reminder_id)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка mark_reminder_sent_async: {e}")
        return False

def mark_reminder_sent(reminder_id: int) -> bool:
    """Синхронная отметка напоминания как отправленного"""
    try:
        return db_loop_manager.run_coro(mark_reminder_sent_async, reminder_id, timeout=5)
    except Exception as e:
        logger.error(f"❌ Ошибка mark_reminder_sent: {e}")
        return False


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'db',
    'db_loop_manager',
    'init_db',
    'close_db',
    'save_telegram_user',
    'save_telegram_user_async',
    'save_user_to_db',
    'save_user_to_db_async',
    'save_test_result_to_db',
    'save_test_result_to_db_async',
    'log_event',
    'log_event_async',
    'ensure_db_connection',
    'execute_with_retry',
    'sync_db_call',
    'get_user_context',
    'get_user_context_async',
    'get_user_data',
    'get_user_data_async',
    'get_telegram_user',
    'get_telegram_user_async',
    'get_user_test_results',
    'get_user_test_results_async',
    'add_reminder',
    'add_reminder_async',
    'get_pending_reminders',
    'get_pending_reminders_async',
    'get_cached_weekend_ideas',
    'get_cached_weekend_ideas_async',
    'cache_weekend_ideas',
    'cache_weekend_ideas_async',
    'get_user_reminders',
    'get_user_reminders_async',
    'mark_reminder_sent',
    'mark_reminder_sent_async'
]

logger.info("✅ db_instance инициализирован")
