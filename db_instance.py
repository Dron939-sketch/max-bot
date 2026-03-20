#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных PostgreSQL
Версия 2.7 - ИСПРАВЛЕНО: сигнатура save_test_result_to_db
"""

import asyncio
import logging
import asyncpg
import os
import threading
import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Глобальные переменные
_pool: Optional[asyncpg.Pool] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_initialized = False
_init_lock = threading.Lock()

# Параметры подключения
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


class DatabaseLoopManager:
    """Менеджер цикла событий для БД"""
    
    def __init__(self):
        self._loop = None
        self._thread = None
        self._initialized = False
        self._init_lock = threading.Lock()
    
    def _get_or_create_loop(self):
        """Получает или создает цикл событий"""
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def run_coro(self, coro_func: Callable, *args, timeout: int = 30, **kwargs):
        """Запускает корутину синхронно"""
        try:
            loop = self._get_or_create_loop()
            
            if loop.is_running():
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(
                    coro_func(*args, **kwargs),
                    loop
                )
                return future.result(timeout=timeout)
            else:
                return loop.run_until_complete(
                    asyncio.wait_for(
                        coro_func(*args, **kwargs),
                        timeout=timeout
                    )
                )
        except asyncio.TimeoutError:
            logger.error(f"❌ Таймаут {timeout} сек")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка в run_coro: {e}")
            return None


class Database:
    """Класс для работы с БД"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
    
    async def init_pool(self):
        """Инициализирует пул соединений"""
        async with self._init_lock:
            if self._initialized and self.pool is not None:
                return True
            
            try:
                if not DATABASE_URL:
                    logger.error("❌ DATABASE_URL не задан")
                    return False
                
                logger.info("🔄 Создаём пул соединений с PostgreSQL...")
                
                self.pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    command_timeout=30,
                    max_inactive_connection_lifetime=300
                )
                
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                
                await self._create_tables()
                
                self._initialized = True
                logger.info("✅ Пул соединений создан")
                return True
                
            except Exception as e:
                logger.error(f"❌ Ошибка при создании пула: {e}")
                if self.pool:
                    await self.pool.close()
                    self.pool = None
                return False
    
    async def _create_tables(self):
        """Создает таблицы"""
        try:
            async with self.pool.acquire() as conn:
                # Таблица пользователей
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS telegram_users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language_code TEXT,
                        registered_at TIMESTAMP DEFAULT NOW(),
                        last_active TIMESTAMP DEFAULT NOW(),
                        user_data JSONB DEFAULT '{}'::jsonb,
                        context_data JSONB DEFAULT '{}'::jsonb
                    )
                """)
                
                # Таблица результатов тестов
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_results (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        test_type TEXT NOT NULL,
                        results JSONB NOT NULL,
                        profile_code TEXT,
                        perception_type TEXT,
                        thinking_level INTEGER,
                        vectors JSONB,
                        behavioral_levels JSONB,
                        deep_patterns JSONB,
                        confinement_model JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Таблица ответов
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_answers (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        test_result_id INTEGER,
                        stage INTEGER NOT NULL,
                        question_index INTEGER NOT NULL,
                        question_text TEXT,
                        answer_text TEXT,
                        answer_value TEXT,
                        scores JSONB,
                        measures TEXT,
                        strategy TEXT,
                        dilts TEXT,
                        pattern TEXT,
                        target TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Таблица событий
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_data JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Таблица напоминаний
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        reminder_type TEXT NOT NULL,
                        remind_at TIMESTAMP NOT NULL,
                        data JSONB DEFAULT '{}'::jsonb,
                        sent BOOLEAN DEFAULT FALSE,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Индексы
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON test_results(user_id);
                    CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id);
                    CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at) WHERE sent = FALSE;
                """)
                
                logger.info("✅ Все таблицы созданы")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise
    
    async def ensure_connection(self) -> bool:
        """Проверяет соединение"""
        if not self._initialized or self.pool is None:
            return await self.init_pool()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка соединения: {e}")
            if self.pool:
                await self.pool.close()
                self.pool = None
            self._initialized = False
            return await self.init_pool()
    
    async def save_telegram_user(
        self,
        user_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language_code: str = None
    ) -> bool:
        """Сохраняет пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO telegram_users (user_id, username, first_name, last_name, language_code, last_active)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        language_code = EXCLUDED.language_code,
                        last_active = NOW()
                """, user_id, username, first_name, last_name, language_code)
            
            logger.info(f"💾 Пользователь {user_id} сохранен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения: {e}")
            return False
    
    async def save_user_data(self, user_id: int, data: Dict) -> bool:
        """Сохраняет данные пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE telegram_users 
                    SET user_data = $2, last_active = NOW()
                    WHERE user_id = $1
                """, user_id, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def load_user_data(self, user_id: int) -> Dict:
        """Загружает данные пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT user_data FROM telegram_users WHERE user_id = $1
                """, user_id)
                if row and row['user_data']:
                    return json.loads(row['user_data'])
                return {}
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {}
    
    async def log_event(self, user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Логирует событие"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO events (user_id, event_type, event_data)
                    VALUES ($1, $2, $3)
                """, user_id, event_type, json.dumps(event_data or {}, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def save_test_result(
        self,
        user_id: int,
        test_type: str,
        results: Dict,
        profile_code: str = None,
        perception_type: str = None,
        thinking_level: int = None,
        vectors: Dict = None,
        behavioral_levels: Dict = None,
        deep_patterns: Dict = None,
        confinement_model: Dict = None
    ) -> Optional[int]:
        """Сохраняет результат теста"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO test_results (
                        user_id, test_type, results, profile_code,
                        perception_type, thinking_level, vectors,
                        behavioral_levels, deep_patterns, confinement_model
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """, user_id, test_type, json.dumps(results, ensure_ascii=False),
                    profile_code, perception_type, thinking_level,
                    json.dumps(vectors or {}, ensure_ascii=False),
                    json.dumps(behavioral_levels or {}, ensure_ascii=False),
                    json.dumps(deep_patterns or {}, ensure_ascii=False),
                    json.dumps(confinement_model or {}, ensure_ascii=False))
                return row['id'] if row else None
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    async def save_test_answer(
        self,
        user_id: int,
        test_result_id: Optional[int],
        stage: int,
        question_index: int,
        question_text: str,
        answer_text: str,
        answer_value: str,
        scores: Optional[Dict] = None,
        measures: Optional[str] = None,
        strategy: Optional[str] = None,
        dilts: Optional[str] = None,
        pattern: Optional[str] = None,
        target: Optional[str] = None
    ) -> bool:
        """Сохраняет ответ на тест"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO test_answers (
                        user_id, test_result_id, stage, question_index,
                        question_text, answer_text, answer_value, scores,
                        measures, strategy, dilts, pattern, target
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, user_id, test_result_id, stage, question_index,
                    question_text, answer_text, answer_value,
                    json.dumps(scores or {}, ensure_ascii=False),
                    measures, strategy, dilts, pattern, target)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def add_reminder(
        self,
        user_id: int,
        reminder_type: str,
        remind_at,
        data: Dict = None
    ) -> Optional[int]:
        """Добавляет напоминание"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO reminders (user_id, reminder_type, remind_at, data)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, user_id, reminder_type, remind_at, json.dumps(data or {}, ensure_ascii=False))
                return row['id'] if row else None
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    async def get_pending_reminders(self, limit: int = 100) -> List[Dict]:
        """Получает неотправленные напоминания"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM reminders 
                    WHERE sent = FALSE AND remind_at <= NOW()
                    ORDER BY remind_at ASC LIMIT $1
                """, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return []
    
    async def mark_reminder_sent(self, reminder_id: int) -> bool:
        """Отмечает напоминание как отправленное"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE reminders 
                    SET sent = TRUE, sent_at = NOW()
                    WHERE id = $1
                """, reminder_id)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def get_user_reminders(self, user_id: int, include_sent: bool = False) -> List[Dict]:
        """Получает напоминания пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                if include_sent:
                    rows = await conn.fetch("""
                        SELECT * FROM reminders WHERE user_id = $1 ORDER BY remind_at DESC
                    """, user_id)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM reminders WHERE user_id = $1 AND sent = FALSE ORDER BY remind_at ASC
                    """, user_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return []
    
    async def get_user_test_results(self, user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
        """Получает результаты тестов"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                if test_type:
                    rows = await conn.fetch("""
                        SELECT * FROM test_results 
                        WHERE user_id = $1 AND test_type = $2
                        ORDER BY created_at DESC LIMIT $3
                    """, user_id, test_type, limit)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM test_results 
                        WHERE user_id = $1
                        ORDER BY created_at DESC LIMIT $2
                    """, user_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return []
    
    async def get_telegram_user(self, user_id: int) -> Optional[Dict]:
        """Получает пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM telegram_users WHERE user_id = $1
                """, user_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    async def get_cached_weekend_ideas(self, user_id: int) -> Optional[str]:
        """Получает кэшированные идеи"""
        try:
            data = await self.load_user_data(user_id)
            return data.get("cached_weekend_ideas")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    async def cache_weekend_ideas(self, user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Кэширует идеи"""
        try:
            data = await self.load_user_data(user_id)
            data["cached_weekend_ideas"] = ideas_text
            data["cached_weekend_ideas_vector"] = main_vector
            data["cached_weekend_ideas_level"] = main_level
            data["cached_weekend_ideas_at"] = datetime.now(timezone.utc).isoformat()
            return await self.save_user_data(user_id, data)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def load_user_context(self, user_id: int) -> Dict:
        """Загружает контекст пользователя"""
        try:
            await self.ensure_connection()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT context_data FROM telegram_users WHERE user_id = $1
                """, user_id)
                if row and row['context_data']:
                    return json.loads(row['context_data'])
                return {}
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {}
    
    async def close(self):
        """Закрывает пул"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("🔌 Пул закрыт")


# Глобальные экземпляры
db = Database()
db_loop_manager = DatabaseLoopManager()


# ✅ ИСПРАВЛЕНАЯ ФУНКЦИЯ - ПРИНИМАЕТ ВСЕ НУЖНЫЕ АРГУМЕНТЫ
async def save_test_result_to_db(
    user_id: int,
    test_type: str,
    results: Dict,
    profile_code: str = None,
    perception_type: str = None,
    thinking_level: int = None,
    vectors: Dict = None,
    behavioral_levels: Dict = None,
    deep_patterns: Dict = None,
    confinement_model: Dict = None
) -> Optional[int]:
    """Сохраняет результат теста в БД"""
    return await db.save_test_result(
        user_id, test_type, results, profile_code,
        perception_type, thinking_level, vectors,
        behavioral_levels, deep_patterns, confinement_model
    )


async def ensure_db_connection() -> bool:
    """Проверяет соединение с БД"""
    return await db.ensure_connection()


def save_user_to_db(user_id: int) -> bool:
    """Синхронное сохранение пользователя"""
    try:
        loop = db_loop_manager._get_or_create_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                db.save_telegram_user(user_id),
                loop
            )
            return future.result(timeout=10)
        else:
            return loop.run_until_complete(
                asyncio.wait_for(db.save_telegram_user(user_id), timeout=10)
            )
    except Exception as e:
        logger.error(f"❌ Ошибка save_user_to_db: {e}")
        return False


def save_telegram_user(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    language_code: str = None
) -> bool:
    """Синхронное сохранение пользователя Telegram"""
    try:
        loop = db_loop_manager._get_or_create_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                db.save_telegram_user(user_id, username, first_name, last_name, language_code),
                loop
            )
            return future.result(timeout=10)
        else:
            return loop.run_until_complete(
                asyncio.wait_for(
                    db.save_telegram_user(user_id, username, first_name, last_name, language_code),
                    timeout=10
                )
            )
    except Exception as e:
        logger.error(f"❌ Ошибка save_telegram_user: {e}")
        return False


# Инициализация
async def init_db():
    """Инициализирует БД"""
    await asyncio.sleep(0.5)
    return await db.init_pool()


try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(init_db())
    else:
        loop.run_until_complete(init_db())
except RuntimeError:
    asyncio.run(init_db())
except Exception as e:
    logger.error(f"❌ Ошибка инициализации: {e}")

logger.info("✅ db_instance инициализирован")
