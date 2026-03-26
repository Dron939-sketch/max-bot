#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ВЕРСИЯ 3.9 - ИСПРАВЛЕНА ПРОБЛЕМА С ЗАКРЫТЫМ ПУЛОМ
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
from datetime import datetime

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
        self._execution_lock = None
        self._shutting_down = False
    
    def init(self, db_instance: BotDatabase):
        """Инициализирует цикл событий в отдельном потоке"""
        with self._lock:
            if self.loop is not None:
                logger.warning("⚠️ Цикл БД уже инициализирован")
                return
            
            self._db_instance = db_instance
            self._shutting_down = False
            
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
                try:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
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
    
    async def _create_lock(self):
        """Создает блокировку в цикле БД"""
        return asyncio.Lock()
    
    def is_ready(self) -> bool:
        """Проверяет, готов ли менеджер к работе"""
        return (self.loop is not None and 
                self.loop.is_running() and 
                not self._shutting_down and
                self._db_instance is not None and
                self._db_instance.pool is not None)
    
    def run_coro(self, coro_func: Callable[..., Awaitable], *args, timeout: int = 45, **kwargs):
        """
        Запускает корутину в цикле БД и возвращает результат.
        """
        if not self.is_ready():
            raise RuntimeError(f"Цикл БД не готов: loop={self.loop is not None}, "
                             f"running={self.loop.is_running() if self.loop else False}, "
                             f"shutting_down={self._shutting_down}, "
                             f"db_pool={self._db_instance.pool is not None if self._db_instance else False}")
        
        # Проверяем тип переданного объекта
        is_coro_func = inspect.iscoroutinefunction(coro_func)
        is_coro = inspect.iscoroutine(coro_func)
        
        if not is_coro_func and not is_coro:
            raise TypeError(f"{coro_func} is not a coroutine or coroutine function")
        
        # Создаем блокировку в цикле, если её нет
        if self._execution_lock is None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._create_lock(),
                    self.loop
                )
                self._execution_lock = future.result(timeout=5)
                logger.debug("✅ Блокировка создана в цикле БД")
            except Exception as e:
                logger.error(f"❌ Ошибка создания блокировки: {e}")
                self._execution_lock = asyncio.Lock()
                logger.warning("⚠️ Используется блокировка из основного потока")
        
        async def _wrapped():
            try:
                # Проверяем пул перед выполнением
                if self._db_instance and self._db_instance.pool is None:
                    logger.warning("⚠️ Пул закрыт, пробуем переподключиться")
                    await self._db_instance.connect()
                
                async with self._execution_lock:
                    if is_coro:
                        return await coro_func
                    else:
                        return await coro_func(*args, **kwargs)
            except asyncio.CancelledError:
                logger.debug("Задача отменена")
                raise
            except Exception as e:
                logger.error(f"❌ Ошибка в _wrapped: {e}")
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
        if not self.is_ready():
            logger.warning("⚠️ Цикл БД не готов, задача не будет запущена")
            return None
        
        is_coro_func = inspect.iscoroutinefunction(coro_func)
        is_coro = inspect.iscoroutine(coro_func)
        
        if not is_coro_func and not is_coro:
            raise TypeError(f"{coro_func} is not a coroutine or coroutine function")
        
        async def _wrapped():
            try:
                if self._db_instance and self._db_instance.pool is None:
                    await self._db_instance.connect()
                
                if is_coro:
                    return await coro_func
                else:
                    return await coro_func(*args, **kwargs)
            except asyncio.CancelledError:
                logger.debug(f"Фоновая задача отменена: {coro_func.__name__}")
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой задаче {coro_func.__name__}: {e}")
                logger.error(traceback.format_exc())
            return None
        
        task = asyncio.run_coroutine_threadsafe(_wrapped(), self.loop)
        self._tasks.add(task)
        
        def _cleanup(t):
            self._tasks.discard(t)
            if t.exception() and not isinstance(t.exception(), asyncio.CancelledError):
                logger.error(f"Фоновая задача завершилась с ошибкой: {t.exception()}")
        
        task.add_done_callback(_cleanup)
        return task
    
    def shutdown(self):
        """Корректное завершение работы"""
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True
        
        if not self.loop or not self.loop.is_running():
            logger.info("Цикл БД уже остановлен")
            return
        
        logger.info("🛑 Останавливаем цикл БД...")
        
        # Создаём задачу остановки в цикле
        async def _shutdown():
            # Отменяем все задачи
            for task in list(self._tasks):
                if not task.done():
                    task.cancel()
            
            # Ждём завершения отмены с таймаутом
            if self._tasks:
                try:
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    pass
            
            # Закрываем пул БД
            if self._db_instance and self._db_instance.pool:
                try:
                    await self._db_instance.disconnect()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии пула: {e}")
        
        # Запускаем shutdown в цикле
        future = asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
        try:
            future.result(timeout=10)
        except TimeoutError:
            logger.warning("⚠️ Таймаут при остановке задач")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")
        
        # Останавливаем цикл
        self.loop.call_soon_threadsafe(self.loop.stop)
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("⚠️ Поток БД не завершился")
        
        logger.info("✅ Цикл БД остановлен")

# ============================================
# ФУНКЦИИ ДЛЯ ЦЕЛЕЙ ПОЛЬЗОВАТЕЛЯ
# ============================================

async def get_user_goals_async(user_id: int, limit: int = 10) -> List[Dict]:
    """Асинхронное получение целей пользователя"""
    try:
        if not await ensure_db_connection():
            return []
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT id, goal_text, status, completed_at, created_at 
                FROM fredi_user_goals 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, user_id, limit)
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения целей: {e}")
        return []


def get_user_goals(user_id: int, limit: int = 10) -> List[Dict]:
    """Синхронная обертка для получения целей"""
    try:
        result = db_loop_manager.run_coro(
            get_user_goals_async,
            user_id,
            limit,
            timeout=10
        )
        return result if result is not None else []
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_goals: {e}")
        return []


async def save_goal_async(user_id: int, goal_text: str) -> Optional[int]:
    """Асинхронное сохранение цели"""
    try:
        if not await ensure_db_connection():
            return None
        
        async with db.get_connection() as conn:
            goal_id = await conn.fetchval("""
                INSERT INTO fredi_user_goals (user_id, goal_text)
                VALUES ($1, $2)
                RETURNING id
            """, user_id, goal_text)
            
            return goal_id
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения цели: {e}")
        return None


def save_goal(user_id: int, goal_text: str) -> Optional[int]:
    """Синхронная обертка для сохранения цели"""
    try:
        result = db_loop_manager.run_coro(
            save_goal_async,
            user_id,
            goal_text,
            timeout=10
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка save_goal: {e}")
        return None

# ============================================
# ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ
# ============================================

db = BotDatabase(DATABASE_URL)
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
        db_loop_manager.shutdown()
        logger.info("🔒 Подключение к PostgreSQL закрыто")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии подключения: {e}")

# ============================================
# ПРОВЕРКА СОЕДИНЕНИЯ С ПОВТОРНЫМИ ПОПЫТКАМИ
# ============================================

_ensure_db_lock = None

async def _get_ensure_lock():
    global _ensure_db_lock
    if _ensure_db_lock is None:
        _ensure_db_lock = asyncio.Lock()
    return _ensure_db_lock


async def ensure_db_connection(max_retries: int = 3, delay: float = 1.0):
    """
    Проверяет соединение с БД с автоматическим восстановлением.
    """
    lock = await _get_ensure_lock()
    
    async with lock:
        for attempt in range(max_retries):
            try:
                # Проверяем, готов ли менеджер
                if not db_loop_manager.is_ready():
                    logger.info(f"🔄 Менеджер БД не готов, инициализация... (попытка {attempt + 1})")
                    await init_db()
                
                # Если пула нет - подключаемся
                if db.pool is None:
                    logger.info("🔄 Подключаемся к БД...")
                    async with asyncio.timeout(10):
                        await db.connect()
                    logger.info("✅ Подключение к БД установлено")
                    return True
                
                # Быстрая проверка соединения
                try:
                    async with asyncio.timeout(3.0):
                        async with db.get_connection() as conn:
                            await conn.execute("SELECT 1")
                    logger.debug("✅ Соединение с БД активно")
                    return True
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Таймаут проверки соединения")
                except Exception as conn_error:
                    logger.warning(f"⚠️ Ошибка соединения: {conn_error}")
                
                # Если дошли сюда - соединение потеряно, переподключаемся
                logger.info("🔄 Переподключаемся к БД...")
                try:
                    async with asyncio.timeout(5):
                        await db.disconnect()
                except:
                    pass
                
                async with asyncio.timeout(15):
                    await db.connect()
                logger.info("✅ Переподключение к БД выполнено")
                return True
                
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Таймаут (попытка {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка (попытка {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("❌ Все попытки исчерпаны")
                return False
    
    return False

# ============================================
# ВЫПОЛНЕНИЕ С ПОВТОРАМИ
# ============================================

async def execute_with_retry(coro_func, *args, max_retries=3, **kwargs):
    """Выполняет функцию с повторными попытками"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Проверяем соединение перед выполнением
            if not await ensure_db_connection(max_retries=1):
                logger.warning(f"⚠️ Нет соединения с БД, попытка {attempt + 1}")
                await asyncio.sleep(1)
                continue
            
            result = db_loop_manager.run_coro(
                coro_func, *args, timeout=25, **kwargs
            )
            return result
            
        except TimeoutError as e:
            last_error = e
            logger.warning(f"⚠️ Таймаут (попытка {attempt+1}/{max_retries})")
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ Ошибка (попытка {attempt+1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))
    
    logger.error(f"❌ Все попытки исчерпаны: {last_error}")
    return None

# ============================================
# ОБЕРТКА ДЛЯ СИНХРОННЫХ ВЫЗОВОВ
# ============================================

def sync_db_call(coro_func):
    """Декоратор для синхронных функций"""
    @wraps(coro_func)
    def wrapper(*args, **kwargs):
        try:
            return db_loop_manager.run_coro(coro_func, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Ошибка в sync_db_call: {e}")
            return None
    return wrapper

# ============================================
# ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ ПОЛЬЗОВАТЕЛЯ (ДОБАВЛЕНА!)
# ============================================

async def load_user_from_db_async(user_id: int) -> Optional[Dict[str, Any]]:
    """Асинхронная загрузка пользователя из БД"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для загрузки пользователя {user_id}")
            return None
        
        user_data = await db.load_user_data(user_id)
        user_context = await db.load_user_context(user_id)
        
        if not user_data and not user_context:
            return None
        
        return {
            'user_data': user_data or {},
            'user_context': user_context or {}
        }
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователя {user_id}: {e}")
        return None


def load_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """Синхронная обертка для загрузки пользователя"""
    try:
        if not db_loop_manager.is_ready():
            logger.warning(f"⚠️ Цикл БД не готов, пропускаем загрузку {user_id}")
            return None
        
        result = db_loop_manager.run_coro(
            load_user_from_db_async,
            user_id,
            timeout=15
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка load_user_from_db: {e}")
        return None


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
    """Асинхронная версия сохранения пользователя Telegram"""
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
    """СИНХРОННАЯ обертка для сохранения пользователя Telegram"""
    try:
        if not db_loop_manager.is_ready():
            logger.warning(f"⚠️ Цикл БД не готов, пропускаем сохранение {user_id}")
            return False
        
        result = db_loop_manager.run_coro(
            save_telegram_user_async,
            user_id,
            username,
            first_name,
            last_name,
            language_code,
            timeout=25
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_telegram_user: {e}")
        return False


def save_user(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    language_code: str = None
) -> bool:
    """Алиас для save_telegram_user"""
    return save_telegram_user(user_id, username, first_name, last_name, language_code)


async def log_event_async(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Асинхронная версия логирования"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для логирования {user_id}")
            return False
        
        await db.log_event(user_id, event_type, event_data or {})
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка логирования: {e}")
        return False


def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Синхронная обертка для логирования"""
    try:
        if not db_loop_manager.is_ready():
            logger.warning(f"⚠️ Цикл БД не готов, пропускаем логирование {user_id}")
            return False
        
        result = db_loop_manager.run_coro(
            log_event_async,
            user_id,
            event_type,
            event_data,
            timeout=8
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка log_event: {e}")
        return False


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ПОЛЬЗОВАТЕЛЯ
# ============================================

async def save_user_data_async(user_id: int, data: Dict[str, Any]) -> bool:
    """Асинхронное сохранение данных пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения данных пользователя {user_id}")
            return False
        
        await db.save_user_data(user_id, data)
        logger.debug(f"💾 Данные пользователя {user_id} сохранены в БД")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных пользователя {user_id}: {e}")
        return False


def save_user_data(user_id: int, data: Dict[str, Any]) -> bool:
    """Синхронная обертка для сохранения данных пользователя"""
    try:
        if not db_loop_manager.is_ready():
            return False
        
        result = db_loop_manager.run_coro(
            save_user_data_async,
            user_id,
            data,
            timeout=25
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_user_data: {e}")
        return False


async def get_user_data_async(user_id: int) -> Optional[Dict[str, Any]]:
    """Асинхронное получение данных пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения данных пользователя {user_id}")
            return None
        
        data = await db.load_user_data(user_id)
        return data
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных пользователя {user_id}: {e}")
        return None


def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Синхронная обертка для получения данных пользователя"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            get_user_data_async,
            user_id,
            timeout=8
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_data: {e}")
        return None


async def save_user_context_async(user_id: int, context: Dict[str, Any]) -> bool:
    """Асинхронное сохранение контекста пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения контекста пользователя {user_id}")
            return False
        
        await db.save_user_context(user_id, context)
        logger.debug(f"💾 Контекст пользователя {user_id} сохранен в БД")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения контекста пользователя {user_id}: {e}")
        return False


def save_user_context(user_id: int, context: Dict[str, Any]) -> bool:
    """Синхронная обертка для сохранения контекста пользователя"""
    try:
        if not db_loop_manager.is_ready():
            return False
        
        result = db_loop_manager.run_coro(
            save_user_context_async,
            user_id,
            context,
            timeout=25
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_user_context: {e}")
        return False


async def get_user_context_async(user_id: int) -> Optional[Dict[str, Any]]:
    """Асинхронное получение контекста пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для получения контекста пользователя {user_id}")
            return None
        
        context = await db.load_user_context(user_id)
        return context
    except Exception as e:
        logger.error(f"❌ Ошибка получения контекста пользователя {user_id}: {e}")
        return None


def get_user_context(user_id: int) -> Optional[Dict[str, Any]]:
    """Синхронная обертка для получения контекста пользователя"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            get_user_context_async,
            user_id,
            timeout=8
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка get_user_context: {e}")
        return None


async def save_route_data_async(user_id: int, route_data: Dict[str, Any]) -> bool:
    """Асинхронное сохранение маршрута пользователя"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения маршрута пользователя {user_id}")
            return False
        
        await db.save_user_route(
            user_id=user_id,
            route_data=route_data,
            current_step=route_data.get('current_step', 1),
            progress=route_data.get('progress', [])
        )
        logger.debug(f"💾 Маршрут пользователя {user_id} сохранен в БД")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения маршрута пользователя {user_id}: {e}")
        return False


def save_route_data(user_id: int, route_data: Dict[str, Any]) -> bool:
    """Синхронная обертка для сохранения маршрута пользователя"""
    try:
        if not db_loop_manager.is_ready():
            return False
        
        result = db_loop_manager.run_coro(
            save_route_data_async,
            user_id,
            route_data,
            timeout=25
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_route_data: {e}")
        return False


async def save_user_to_db_async(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """Асинхронная версия сохранения"""
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
        return False


def save_user_to_db(user_id, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None):
    """Синхронная обертка для сохранения"""
    try:
        if not db_loop_manager.is_ready():
            logger.warning(f"⚠️ Цикл БД не готов, пропускаем сохранение {user_id}")
            return False
        
        result = db_loop_manager.run_coro(
            save_user_to_db_async,
            user_id,
            user_data_dict,
            user_contexts_dict,
            user_routes_dict,
            timeout=25
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка save_user_to_db: {e}")
        return False


# ============================================
# ФУНКЦИИ ДЛЯ МЫСЛЕЙ ПСИХОЛОГА
# ============================================

async def create_psychologist_thoughts_table():
    """Создает таблицу для хранения мыслей психолога"""
    try:
        if not await ensure_db_connection():
            logger.error("❌ Нет соединения с БД")
            return False
        
        async with db.get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_psychologist_thoughts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    test_result_id INTEGER,
                    thought_type VARCHAR(50) NOT NULL DEFAULT 'psychologist_thought',
                    thought_text TEXT NOT NULL,
                    thought_summary VARCHAR(500),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thoughts_user_id 
                ON fredi_psychologist_thoughts(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thoughts_test_result 
                ON fredi_psychologist_thoughts(test_result_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thoughts_type 
                ON fredi_psychologist_thoughts(thought_type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thoughts_created 
                ON fredi_psychologist_thoughts(created_at)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thoughts_text_gin 
                ON fredi_psychologist_thoughts 
                USING GIN(to_tsvector('russian', thought_text))
            """)
            
            logger.info("✅ Таблица fredi_psychologist_thoughts создана")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы: {e}")
        return False


async def save_psychologist_thought_async(
    user_id: int,
    thought_text: str,
    test_result_id: int = None,
    thought_type: str = 'psychologist_thought',
    thought_summary: str = None,
    metadata: Dict = None
) -> Optional[int]:
    """Сохраняет мысль психолога"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД")
            return None
        
        await create_psychologist_thoughts_table()
        
        async with db.get_connection() as conn:
            if test_result_id is None:
                row = await conn.fetchrow("""
                    SELECT id FROM fredi_test_results 
                    WHERE user_id = $1 
                    ORDER BY created_at DESC LIMIT 1
                """, user_id)
                if row:
                    test_result_id = row['id']
            
            await conn.execute("""
                UPDATE fredi_psychologist_thoughts 
                SET is_active = FALSE 
                WHERE user_id = $1 AND thought_type = $2 AND is_active = TRUE
            """, user_id, thought_type)
            
            row = await conn.fetchrow("""
                INSERT INTO fredi_psychologist_thoughts (
                    user_id, test_result_id, thought_type, thought_text, 
                    thought_summary, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, user_id, test_result_id, thought_type, thought_text,
                thought_summary, json.dumps(metadata or {}))
            
            thought_id = row['id']
            
            try:
                from state import user_data
                if user_id in user_data:
                    user_data[user_id]['psychologist_thought'] = thought_text
                    user_data[user_id]['psychologist_thought_id'] = thought_id
                    user_data[user_id]['psychologist_thought_type'] = thought_type
                    user_data[user_id]['psychologist_thought_metadata'] = metadata
                    save_user_data(user_id, user_data[user_id])
            except Exception as e:
                logger.warning(f"⚠️ Не удалось сохранить мысль в user_data: {e}")
            
            logger.info(f"💾 Мысль психолога сохранена: user={user_id}, id={thought_id}")
            return thought_id
            
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения мысли: {e}")
        return None


def save_psychologist_thought(
    user_id: int,
    thought_text: str,
    test_result_id: int = None,
    thought_type: str = 'psychologist_thought',
    thought_summary: str = None,
    metadata: Dict = None
) -> Optional[int]:
    """Синхронная обертка для сохранения мысли психолога"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            save_psychologist_thought_async,
            user_id,
            thought_text,
            test_result_id,
            thought_type,
            thought_summary,
            metadata,
            timeout=25
        )
        return result if result is not None else None
    except Exception as e:
        logger.error(f"❌ Ошибка save_psychologist_thought: {e}")
        return None


async def get_psychologist_thought_async(
    user_id: int,
    thought_type: str = 'psychologist_thought',
    only_active: bool = True
) -> Optional[str]:
    """Получает последнюю мысль психолога"""
    try:
        if not await ensure_db_connection():
            return None
        
        async with db.get_connection() as conn:
            query = """
                SELECT thought_text FROM fredi_psychologist_thoughts 
                WHERE user_id = $1 AND thought_type = $2
            """
            params = [user_id, thought_type]
            
            if only_active:
                query += " AND is_active = TRUE"
            
            query += " ORDER BY created_at DESC LIMIT 1"
            
            row = await conn.fetchrow(query, *params)
            return row['thought_text'] if row else None
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения мысли: {e}")
        return None


def get_psychologist_thought(
    user_id: int,
    thought_type: str = 'psychologist_thought',
    only_active: bool = True
) -> Optional[str]:
    """Синхронная обертка для получения мысли психолога"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            get_psychologist_thought_async,
            user_id,
            thought_type,
            only_active,
            timeout=8
        )
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка get_psychologist_thought: {e}")
        return None


async def get_psychologist_thought_history_async(
    user_id: int,
    thought_type: str = None,
    limit: int = 10
) -> List[Dict]:
    """Получает историю мыслей психолога"""
    try:
        if not await ensure_db_connection():
            return []
        
        async with db.get_connection() as conn:
            query = """
                SELECT 
                    id, thought_type, thought_text, thought_summary,
                    created_at, is_active, metadata
                FROM fredi_psychologist_thoughts 
                WHERE user_id = $1
            """
            params = [user_id]
            
            if thought_type:
                query += " AND thought_type = $2"
                params.append(thought_type)
            
            query += " ORDER BY created_at DESC LIMIT $3"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    'id': row['id'],
                    'type': row['thought_type'],
                    'text': row['thought_text'],
                    'summary': row['thought_summary'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'is_active': row['is_active'],
                    'metadata': row['metadata']
                }
                for row in rows
            ]
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории мыслей: {e}")
        return []


def get_psychologist_thought_history(
    user_id: int,
    thought_type: str = None,
    limit: int = 10
) -> List[Dict]:
    """Синхронная обертка для получения истории мыслей"""
    try:
        if not db_loop_manager.is_ready():
            return []
        
        result = db_loop_manager.run_coro(
            get_psychologist_thought_history_async,
            user_id,
            thought_type,
            limit,
            timeout=8
        )
        return result if result is not None else []
    except Exception as e:
        logger.error(f"❌ Ошибка get_psychologist_thought_history: {e}")
        return []


async def get_all_psychologist_thoughts_async(
    user_id: int,
    limit: int = 50,
    include_inactive: bool = False
) -> List[Dict]:
    """Получает все мысли психолога для пользователя"""
    try:
        if not await ensure_db_connection():
            return []
        
        async with db.get_connection() as conn:
            query = """
                SELECT 
                    id, thought_type, thought_text, thought_summary,
                    created_at, is_active, metadata,
                    test_result_id
                FROM fredi_psychologist_thoughts 
                WHERE user_id = $1
            """
            params = [user_id]
            
            if not include_inactive:
                query += " AND is_active = TRUE"
            
            query += " ORDER BY created_at DESC LIMIT $2"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    'id': row['id'],
                    'type': row['thought_type'],
                    'text': row['thought_text'],
                    'summary': row['thought_summary'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'is_active': row['is_active'],
                    'metadata': row['metadata'],
                    'test_result_id': row['test_result_id']
                }
                for row in rows
            ]
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех мыслей: {e}")
        return []


def get_all_psychologist_thoughts(
    user_id: int,
    limit: int = 50,
    include_inactive: bool = False
) -> List[Dict]:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return []
        
        result = db_loop_manager.run_coro(
            get_all_psychologist_thoughts_async,
            user_id,
            limit,
            include_inactive,
            timeout=10
        )
        return result if result is not None else []
    except Exception as e:
        logger.error(f"❌ Ошибка get_all_psychologist_thoughts: {e}")
        return []


async def delete_psychologist_thought_async(thought_id: int) -> bool:
    """Удаляет мысль психолога по ID"""
    try:
        if not await ensure_db_connection():
            return False
        
        async with db.get_connection() as conn:
            result = await conn.execute("""
                DELETE FROM fredi_psychologist_thoughts 
                WHERE id = $1
            """, thought_id)
            
            deleted = int(result.split()[-1]) > 0
            if deleted:
                logger.info(f"🗑️ Удалена мысль психолога id={thought_id}")
            return deleted
            
    except Exception as e:
        logger.error(f"❌ Ошибка удаления мысли: {e}")
        return False


def delete_psychologist_thought(thought_id: int) -> bool:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return False
        
        result = db_loop_manager.run_coro(
            delete_psychologist_thought_async,
            thought_id,
            timeout=10
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка delete_psychologist_thought: {e}")
        return False


async def update_psychologist_thought_async(
    thought_id: int,
    thought_text: str = None,
    thought_summary: str = None,
    is_active: bool = None,
    metadata: Dict = None
) -> bool:
    """Обновляет мысль психолога"""
    try:
        if not await ensure_db_connection():
            return False
        
        async with db.get_connection() as conn:
            updates = []
            params = []
            param_index = 2
            
            if thought_text is not None:
                updates.append(f"thought_text = ${param_index}")
                params.append(thought_text)
                param_index += 1
            
            if thought_summary is not None:
                updates.append(f"thought_summary = ${param_index}")
                params.append(thought_summary)
                param_index += 1
            
            if is_active is not None:
                updates.append(f"is_active = ${param_index}")
                params.append(is_active)
                param_index += 1
            
            if metadata is not None:
                updates.append(f"metadata = ${param_index}")
                params.append(json.dumps(metadata))
                param_index += 1
            
            if not updates:
                logger.warning(f"⚠️ Нет полей для обновления мысли {thought_id}")
                return False
            
            updates.append("updated_at = NOW()")
            
            query = f"""
                UPDATE fredi_psychologist_thoughts 
                SET {', '.join(updates)}
                WHERE id = $1
            """
            params.insert(0, thought_id)
            
            result = await conn.execute(query, *params)
            updated = int(result.split()[-1]) > 0
            
            if updated:
                logger.info(f"✏️ Обновлена мысль психолога id={thought_id}")
            return updated
            
    except Exception as e:
        logger.error(f"❌ Ошибка обновления мысли: {e}")
        return False


def update_psychologist_thought(
    thought_id: int,
    thought_text: str = None,
    thought_summary: str = None,
    is_active: bool = None,
    metadata: Dict = None
) -> bool:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return False
        
        result = db_loop_manager.run_coro(
            update_psychologist_thought_async,
            thought_id,
            thought_text,
            thought_summary,
            is_active,
            metadata,
            timeout=10
        )
        return result if result is not None else False
    except Exception as e:
        logger.error(f"❌ Ошибка update_psychologist_thought: {e}")
        return False


async def get_thoughts_by_test_result_async(test_result_id: int) -> List[Dict]:
    """Получает мысли по результату теста"""
    try:
        if not await ensure_db_connection():
            return []
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id, thought_type, thought_text, thought_summary,
                    created_at, is_active, metadata, user_id
                FROM fredi_psychologist_thoughts 
                WHERE test_result_id = $1
                ORDER BY created_at DESC
            """, test_result_id)
            
            return [
                {
                    'id': row['id'],
                    'type': row['thought_type'],
                    'text': row['thought_text'],
                    'summary': row['thought_summary'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'is_active': row['is_active'],
                    'metadata': row['metadata'],
                    'user_id': row['user_id']
                }
                for row in rows
            ]
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения мыслей по тесту: {e}")
        return []


def get_thoughts_by_test_result(test_result_id: int) -> List[Dict]:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return []
        
        result = db_loop_manager.run_coro(
            get_thoughts_by_test_result_async,
            test_result_id,
            timeout=10
        )
        return result if result is not None else []
    except Exception as e:
        logger.error(f"❌ Ошибка get_thoughts_by_test_result: {e}")
        return []


async def get_psychologist_thoughts_stats_async(user_id: int) -> Dict[str, Any]:
    """Получает статистику по мыслям"""
    try:
        if not await ensure_db_connection():
            return {}
        
        async with db.get_connection() as conn:
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM fredi_psychologist_thoughts 
                WHERE user_id = $1
            """, user_id)
            
            active = await conn.fetchval("""
                SELECT COUNT(*) FROM fredi_psychologist_thoughts 
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
            
            by_type = await conn.fetch("""
                SELECT thought_type, COUNT(*) as count 
                FROM fredi_psychologist_thoughts 
                WHERE user_id = $1 
                GROUP BY thought_type
            """, user_id)
            
            last = await conn.fetchrow("""
                SELECT thought_text, thought_type, created_at 
                FROM fredi_psychologist_thoughts 
                WHERE user_id = $1 
                ORDER BY created_at DESC LIMIT 1
            """, user_id)
            
            return {
                'total': total or 0,
                'active': active or 0,
                'inactive': (total or 0) - (active or 0),
                'by_type': {row['thought_type']: row['count'] for row in by_type},
                'last_thought': {
                    'text': last['thought_text'][:100] if last else None,
                    'type': last['thought_type'] if last else None,
                    'created_at': last['created_at'].isoformat() if last and last['created_at'] else None
                } if last else None
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return {}


def get_psychologist_thoughts_stats(user_id: int) -> Dict[str, Any]:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return {}
        
        result = db_loop_manager.run_coro(
            get_psychologist_thoughts_stats_async,
            user_id,
            timeout=10
        )
        return result if result is not None else {}
    except Exception as e:
        logger.error(f"❌ Ошибка get_psychologist_thoughts_stats: {e}")
        return {}


# ============================================
# ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ ТЕСТА
# ============================================

async def save_test_result_to_db_async(user_id, test_type, user_data_dict=None):
    """Асинхронная версия сохранения результатов теста"""
    try:
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
        
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        elif data.get("ai_generated_profile"):
            import re
            match = re.search(r'СБ-\d+_ТФ-\d+_УБ-\d+_ЧВ-\d+', data.get("ai_generated_profile", ""))
            if match:
                profile_code = match.group(0)
        
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
        
        thought = data.get('psychologist_thought')
        if thought:
            await save_psychologist_thought_async(
                user_id=user_id,
                thought_text=thought,
                test_result_id=test_id,
                thought_type='psychologist_thought',
                metadata={
                    'model_version': data.get('model_version', 'deepseek'),
                    'generation_time_ms': data.get('generation_time_ms'),
                    'profile_code': profile_code
                }
            )
        
        profile_description = data.get('ai_generated_profile')
        if profile_description:
            await save_psychologist_thought_async(
                user_id=user_id,
                thought_text=profile_description,
                test_result_id=test_id,
                thought_type='profile_description',
                thought_summary=profile_description[:200],
                metadata={
                    'profile_code': profile_code,
                    'vectors': data.get('behavioral_levels'),
                    'perception_type': data.get('perception_type'),
                    'thinking_level': data.get('thinking_level')
                }
            )
        
        logger.info(f"📝 Результаты теста для пользователя {user_id} сохранены (ID: {test_id})")
        return test_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
        return None


def save_test_result_to_db(user_id, test_type, user_data_dict=None):
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            save_test_result_to_db_async,
            user_id,
            test_type,
            user_data_dict,
            timeout=25
        )
        return result if result is not None else None
    except Exception as e:
        logger.error(f"❌ Ошибка save_test_result_to_db: {e}")
        return None


async def save_test_result_full_async(
    user_id: int,
    test_type: str,
    results: Dict,
    profile_code: str = None,
    perception_type: str = None,
    thinking_level: int = None,
    vectors: Dict = None,
    deep_patterns: Dict = None,
    confinement_model: Dict = None
) -> Optional[int]:
    """Асинхронная версия с полными параметрами"""
    try:
        if not await ensure_db_connection():
            logger.error(f"❌ Нет соединения с БД для сохранения результатов {user_id}")
            return None
        
        if vectors is None and results.get("behavioral_levels"):
            vectors = results.get("behavioral_levels")
        
        if profile_code is None:
            if results.get("profile_data"):
                profile_code = results["profile_data"].get("display_name")
            elif results.get("ai_generated_profile"):
                import re
                match = re.search(r'СБ-\d+_ТФ-\d+_УБ-\d+_ЧВ-\d+', results.get("ai_generated_profile", ""))
                if match:
                    profile_code = match.group(0)
        
        if perception_type is None:
            perception_type = results.get("perception_type")
        
        if thinking_level is None:
            thinking_level = results.get("thinking_level")
        
        if deep_patterns is None:
            deep_patterns = results.get("deep_patterns")
        
        if confinement_model is None:
            confinement_model = results.get("confinement_model")
        
        test_id = await db.save_test_result(
            user_id=user_id,
            test_type=test_type,
            results=results,
            profile_code=profile_code,
            perception_type=perception_type,
            thinking_level=thinking_level,
            vectors=vectors,
            deep_patterns=deep_patterns,
            confinement_model=confinement_model
        )
        
        all_answers = results.get("all_answers", [])
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
        
        thought = results.get('psychologist_thought')
        if thought:
            await save_psychologist_thought_async(
                user_id=user_id,
                thought_text=thought,
                test_result_id=test_id,
                thought_type='psychologist_thought',
                metadata={
                    'model_version': results.get('model_version', 'deepseek'),
                    'generation_time_ms': results.get('generation_time_ms'),
                    'profile_code': profile_code
                }
            )
        
        profile_description = results.get('ai_generated_profile')
        if profile_description:
            await save_psychologist_thought_async(
                user_id=user_id,
                thought_text=profile_description,
                test_result_id=test_id,
                thought_type='profile_description',
                thought_summary=profile_description[:200],
                metadata={
                    'profile_code': profile_code,
                    'vectors': vectors,
                    'perception_type': perception_type,
                    'thinking_level': thinking_level
                }
            )
        
        logger.info(f"📝 Результаты теста для пользователя {user_id} сохранены (ID: {test_id})")
        return test_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
        return None


def save_test_result_to_db_full(
    user_id: int,
    test_type: str,
    results: Dict,
    profile_code: str = None,
    perception_type: str = None,
    thinking_level: int = None,
    vectors: Dict = None,
    deep_patterns: Dict = None,
    confinement_model: Dict = None
) -> Optional[int]:
    """Синхронная обертка"""
    try:
        if not db_loop_manager.is_ready():
            return None
        
        result = db_loop_manager.run_coro(
            save_test_result_full_async,
            user_id,
            test_type,
            results,
            profile_code,
            perception_type,
            thinking_level,
            vectors,
            deep_patterns,
            confinement_model,
            timeout=25
        )
        return result if result is not None else None
    except Exception as e:
        logger.error(f"❌ Ошибка save_test_result_to_db_full: {e}")
        return None


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'db',
    'db_loop_manager',
    'init_db',
    'close_db',
    'save_telegram_user',
    'save_user',
    'save_user_to_db',
    'load_user_from_db',
    'save_test_result_to_db',
    'save_test_result_to_db_full',
    'log_event',
    'ensure_db_connection',
    'execute_with_retry',
    'sync_db_call',
    'save_user_data',
    'get_user_data',
    'save_user_context',
    'get_user_context',
    'save_route_data',
    'create_psychologist_thoughts_table',
    'save_psychologist_thought',
    'get_psychologist_thought',
    'get_psychologist_thought_history',
    'get_all_psychologist_thoughts',
    'delete_psychologist_thought',
    'update_psychologist_thought',
    'get_thoughts_by_test_result',
    'get_psychologist_thoughts_stats',
    'get_user_goals',      # ✅ ДОБАВИТЬ
    'save_goal', 
]

logger.info("✅ db_instance инициализирован (версия 3.9 - добавлена load_user_from_db, исправлен пул)")
