#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с PostgreSQL базой данных бота "Фреди"
Все таблицы имеют префикс fredi_ для избежания конфликтов

Версия 4.1 - ИСПРАВЛЕНА ПРОБЛЕМА С ПУЛОМ И КОНКУРЕНТНОСТЬЮ
"""

import asyncio
import asyncpg
import pickle
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BotDatabase:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self, dsn: str):
        """
        Инициализация подключения к БД
        
        Args:
            dsn: Строка подключения к PostgreSQL
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self._background_tasks: set = set()  # Для отслеживания фоновых задач
        self._initialized = False
        self._tables_checked = False
        self._reconnecting = False  # Флаг переподключения
    
    async def connect(self, min_size: int = 2, max_size: int = 10):
        """
        Создание пула соединений с БД
        
        Args:
            min_size: Минимальное количество соединений
            max_size: Максимальное количество соединений
        """
        try:
            if self.pool and not self.pool._closed:
                logger.info("✅ Пул соединений уже существует")
                return
            
            logger.info("🔄 Создаём пул соединений к PostgreSQL...")
            
            # Оптимальные настройки пула
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=min_size,
                max_size=max_size,
                command_timeout=30,
                max_inactive_connection_lifetime=300,  # 5 минут
                timeout=30,
                max_queries=50000,
                ssl='require'
            )
            
            # Проверяем соединение
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                logger.info("✅ Проверка соединения успешна")
            
            # Создаём таблицы
            await self.create_tables()
            
            self._initialized = True
            logger.info(f"✅ Пул соединений создан (min={min_size}, max={max_size})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            self.pool = None
            raise
    
    async def disconnect(self):
        """
        Корректное закрытие пула соединений с отменой всех фоновых задач
        """
        logger.info("🔄 Начинаем graceful shutdown...")
        
        # Отменяем все фоновые задачи
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Ждём завершения отмены
        if self._background_tasks:
            try:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass
            self._background_tasks.clear()
        
        # Закрываем пул
        if self.pool and not self.pool._closed:
            await self.pool.close()
            self.pool = None
        
        self._initialized = False
        logger.info("🔌 Пул соединений с PostgreSQL закрыт")
    
    def _add_background_task(self, task: asyncio.Task):
        """
        Добавляет фоновую задачу для отслеживания
        """
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Контекстный менеджер для получения соединения из пула
        с автоматической проверкой живости соединения
        """
        if not self.pool or self.pool._closed:
            error_msg = "Пул соединений не инициализирован или закрыт"
            logger.error(f"❌ {error_msg}")
            
            # Пытаемся переподключиться
            if not self._reconnecting:
                try:
                    self._reconnecting = True
                    await self.connect()
                    self._reconnecting = False
                except Exception as e:
                    self._reconnecting = False
                    raise RuntimeError(f"{error_msg}. Не удалось переподключиться: {e}")
            else:
                raise RuntimeError(error_msg)
        
        try:
            async with self.pool.acquire() as conn:
                # Проверяем живо ли соединение
                try:
                    await conn.execute("SELECT 1")
                except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                        asyncpg.exceptions.ConnectionClosedError,
                        asyncpg.exceptions.InterfaceError) as e:
                    logger.warning(f"⚠️ Соединение потеряно: {e}")
                    # Закрываем текущий пул и создаём новый
                    if self.pool and not self.pool._closed:
                        await self.pool.close()
                    self.pool = None
                    await self.connect()
                    async with self.pool.acquire() as new_conn:
                        yield new_conn
                else:
                    yield conn
        except Exception as e:
            logger.error(f"❌ Ошибка при получении соединения: {e}")
            raise
    
    # ====================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СЕРИАЛИЗАЦИИ ======================
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Рекурсивно преобразует объект в JSON-сериализуемый формат"""
        if obj is None:
            return None
        
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        if isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = self._make_json_serializable(value)
            return result
        
        if hasattr(obj, 'to_dict'):
            return self._make_json_serializable(obj.to_dict())
        
        return str(obj)
    
    def _safe_json_dumps(self, data: Any) -> Optional[str]:
        """Безопасно сериализует данные в JSON"""
        if data is None:
            return None
        
        try:
            return json.dumps(data, default=str, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка прямой сериализации JSON: {e}")
            try:
                serializable = self._make_json_serializable(data)
                return json.dumps(serializable, ensure_ascii=False)
            except Exception as e2:
                logger.error(f"❌ Не удалось сериализовать данные: {e2}")
                return "{}"
    
    # ====================== СОЗДАНИЕ ТАБЛИЦ ======================
    
    async def create_tables(self):
        """Создает все необходимые таблицы, если их нет"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                
                # Таблица пользователей Telegram
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language_code TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица контекста пользователей
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_user_contexts (
                        user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        name TEXT,
                        age INTEGER,
                        gender TEXT,
                        city TEXT,
                        birth_date DATE,
                        timezone TEXT DEFAULT 'Europe/Moscow',
                        timezone_offset INTEGER DEFAULT 3,
                        communication_mode TEXT DEFAULT 'coach',
                        last_context_update TIMESTAMP WITH TIME ZONE,
                        weather_cache JSONB,
                        weather_cache_time TIMESTAMP WITH TIME ZONE,
                        family_status TEXT,
                        has_children BOOLEAN DEFAULT FALSE,
                        children_ages TEXT,
                        work_schedule TEXT,
                        job_title TEXT,
                        commute_time INTEGER,
                        housing_type TEXT,
                        has_private_space BOOLEAN DEFAULT FALSE,
                        has_car BOOLEAN DEFAULT FALSE,
                        support_people TEXT,
                        resistance_people TEXT,
                        energy_level INTEGER,
                        life_context_complete BOOLEAN DEFAULT FALSE,
                        awaiting_context TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица данных пользователей
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_user_data (
                        user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        data JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица для хранения сериализованных объектов
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_context_objects (
                        user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        context_data BYTEA NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица маршрутов пользователей
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_user_routes (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        route_data JSONB NOT NULL,
                        current_step INTEGER DEFAULT 1,
                        progress JSONB DEFAULT '[]',
                        is_active BOOLEAN DEFAULT TRUE,
                        completed_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица результатов тестов
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_test_results (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        test_type TEXT NOT NULL,
                        results JSONB NOT NULL,
                        profile_code TEXT,
                        perception_type TEXT,
                        thinking_level INTEGER,
                        vectors JSONB,
                        behavioral_levels JSONB,
                        deep_patterns JSONB,
                        confinement_model JSONB,
                        current_destination JSONB,
                        current_route JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица ответов на тест
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_test_answers (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        test_result_id BIGINT REFERENCES fredi_test_results(id) ON DELETE CASCADE,
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
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица гипнотических якорей
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_hypno_anchors (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        anchor_name TEXT NOT NULL,
                        anchor_state TEXT NOT NULL,
                        anchor_phrase TEXT NOT NULL,
                        emoji TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_used TIMESTAMP WITH TIME ZONE,
                        use_count INTEGER DEFAULT 0,
                        UNIQUE(user_id, anchor_name)
                    )
                """)
                
                # Таблица напоминаний
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_reminders (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        reminder_type TEXT NOT NULL,
                        remind_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        data JSONB,
                        is_sent BOOLEAN DEFAULT FALSE,
                        sent_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица кэша идей на выходные
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_weekend_ideas_cache (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        ideas_text TEXT NOT NULL,
                        main_vector TEXT,
                        main_level INTEGER,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour'
                    )
                """)
                
                # Таблица анализов вопросов
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_question_analysis_cache (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        question_hash INTEGER NOT NULL,
                        question_text TEXT,
                        analysis JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '5 minutes'
                    )
                """)
                
                # Таблица мыслей психолога
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_psychologist_thoughts (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        test_result_id BIGINT REFERENCES fredi_test_results(id) ON DELETE SET NULL,
                        thought_type VARCHAR(50) NOT NULL DEFAULT 'psychologist_thought',
                        thought_text TEXT NOT NULL,
                        thought_summary VARCHAR(500),
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Таблица событий для статистики
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_events (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        event_type TEXT NOT NULL,
                        event_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Таблица целей пользователя
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_user_goals (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        goal_text TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        completed_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # ИНДЕКСЫ
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON fredi_reminders(remind_at) WHERE is_sent = FALSE")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON fredi_events(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON fredi_events(event_type)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON fredi_events(created_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON fredi_test_results(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_profile ON fredi_test_results(profile_code)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_weekend_cache_expires ON fredi_weekend_ideas_cache(expires_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_hash ON fredi_question_analysis_cache(user_id, question_hash)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_expires ON fredi_question_analysis_cache(expires_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_hypno_anchors_user ON fredi_hypno_anchors(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_goals_user_id ON fredi_user_goals(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_goals_status ON fredi_user_goals(status)")
                
                # Индексы для таблицы мыслей психолога
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_user_id ON fredi_psychologist_thoughts(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_test_result ON fredi_psychologist_thoughts(test_result_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_type ON fredi_psychologist_thoughts(thought_type)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_created ON fredi_psychologist_thoughts(created_at)")
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_psych_thoughts_text_gin 
                    ON fredi_psychologist_thoughts 
                    USING GIN(to_tsvector('russian', thought_text))
                """)
                
                self._tables_checked = True
                logger.info("✅ Все таблицы созданы или уже существуют")
    
    async def create_psychologist_thoughts_table(self):
        """Создаёт таблицу для мыслей психолога (отдельный вызов)"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fredi_psychologist_thoughts (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                        test_result_id BIGINT REFERENCES fredi_test_results(id) ON DELETE SET NULL,
                        thought_type VARCHAR(50) NOT NULL DEFAULT 'psychologist_thought',
                        thought_text TEXT NOT NULL,
                        thought_summary VARCHAR(500),
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_user_id ON fredi_psychologist_thoughts(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_test_result ON fredi_psychologist_thoughts(test_result_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_type ON fredi_psychologist_thoughts(thought_type)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_psych_thoughts_created ON fredi_psychologist_thoughts(created_at)")
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_psych_thoughts_text_gin 
                    ON fredi_psychologist_thoughts 
                    USING GIN(to_tsvector('russian', thought_text))
                """)
                
                logger.info("✅ Таблица fredi_psychologist_thoughts создана")
    
    # ====================== ПОЛЬЗОВАТЕЛИ ======================
    
    async def save_telegram_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> bool:
        """Сохранение или обновление информации о пользователе Telegram"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                existing = await conn.fetchval(
                    "SELECT user_id FROM fredi_users WHERE user_id = $1",
                    user_id
                )
                
                if existing:
                    await conn.execute("""
                        UPDATE fredi_users SET
                            username = $2,
                            first_name = $3,
                            last_name = $4,
                            language_code = $5,
                            updated_at = NOW(),
                            last_activity = NOW()
                        WHERE user_id = $1
                    """, user_id, username, first_name, last_name, language_code)
                    return False
                else:
                    await conn.execute("""
                        INSERT INTO fredi_users (
                            user_id, username, first_name, last_name, 
                            language_code, created_at, updated_at, last_activity
                        ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), NOW())
                    """, user_id, username, first_name, last_name, language_code)
                    return True
    
    async def get_telegram_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM fredi_users WHERE user_id = $1",
                    user_id
                )
                return dict(row) if row else None
    
    async def update_last_activity(self, user_id: int):
        """Обновляет время последней активности пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE fredi_users SET last_activity = NOW() WHERE user_id = $1
                """, user_id)
    
    # ====================== КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ ======================
    
    async def save_user_context(self, user_id: int, context_obj) -> None:
        """Сохраняет объект UserContext в БД"""
        await self.save_telegram_user(user_id)
        
        if isinstance(context_obj, dict):
            from types import SimpleNamespace
            context_obj = SimpleNamespace(**context_obj)
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO fredi_user_contexts (
                        user_id, name, age, gender, city, birth_date,
                        timezone, timezone_offset, communication_mode, last_context_update,
                        weather_cache, weather_cache_time,
                        family_status, has_children, children_ages, work_schedule,
                        job_title, commute_time, housing_type, has_private_space,
                        has_car, support_people, resistance_people, energy_level,
                        life_context_complete, awaiting_context, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6,
                        $7, $8, $9, $10,
                        $11, $12,
                        $13, $14, $15, $16,
                        $17, $18, $19, $20,
                        $21, $22, $23, $24,
                        $25, $26, NOW()
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        age = EXCLUDED.age,
                        gender = EXCLUDED.gender,
                        city = EXCLUDED.city,
                        birth_date = EXCLUDED.birth_date,
                        timezone = EXCLUDED.timezone,
                        timezone_offset = EXCLUDED.timezone_offset,
                        communication_mode = EXCLUDED.communication_mode,
                        last_context_update = EXCLUDED.last_context_update,
                        weather_cache = EXCLUDED.weather_cache,
                        weather_cache_time = EXCLUDED.weather_cache_time,
                        family_status = EXCLUDED.family_status,
                        has_children = EXCLUDED.has_children,
                        children_ages = EXCLUDED.children_ages,
                        work_schedule = EXCLUDED.work_schedule,
                        job_title = EXCLUDED.job_title,
                        commute_time = EXCLUDED.commute_time,
                        housing_type = EXCLUDED.housing_type,
                        has_private_space = EXCLUDED.has_private_space,
                        has_car = EXCLUDED.has_car,
                        support_people = EXCLUDED.support_people,
                        resistance_people = EXCLUDED.resistance_people,
                        energy_level = EXCLUDED.energy_level,
                        life_context_complete = EXCLUDED.life_context_complete,
                        awaiting_context = EXCLUDED.awaiting_context,
                        updated_at = NOW()
                """,
                    user_id,
                    getattr(context_obj, 'name', None),
                    getattr(context_obj, 'age', None),
                    getattr(context_obj, 'gender', None),
                    getattr(context_obj, 'city', None),
                    getattr(context_obj, 'birth_date', None),
                    getattr(context_obj, 'timezone', 'Europe/Moscow'),
                    getattr(context_obj, 'timezone_offset', 3),
                    getattr(context_obj, 'communication_mode', 'coach'),
                    getattr(context_obj, 'last_context_update', None),
                    self._safe_json_dumps(getattr(context_obj, 'weather_cache', {})),
                    getattr(context_obj, 'weather_cache_time', None),
                    getattr(context_obj, 'family_status', None),
                    getattr(context_obj, 'has_children', False),
                    getattr(context_obj, 'children_ages', None),
                    getattr(context_obj, 'work_schedule', None),
                    getattr(context_obj, 'job_title', None),
                    getattr(context_obj, 'commute_time', None),
                    getattr(context_obj, 'housing_type', None),
                    getattr(context_obj, 'has_private_space', False),
                    getattr(context_obj, 'has_car', False),
                    getattr(context_obj, 'support_people', None),
                    getattr(context_obj, 'resistance_people', None),
                    getattr(context_obj, 'energy_level', None),
                    getattr(context_obj, 'life_context_complete', False),
                    getattr(context_obj, 'awaiting_context', None)
                )
    
    async def load_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает данные для создания объекта UserContext"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM fredi_user_contexts WHERE user_id = $1",
                    user_id
                )
                
                if not row:
                    return None
                
                data = dict(row)
                
                if data.get('weather_cache'):
                    data['weather_cache'] = json.loads(data['weather_cache'])
                
                return data
    
    # ====================== ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ ======================
    
    async def save_user_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Сохраняет user_data[user_id] в JSONB поле"""
        await self.save_telegram_user(user_id)
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO fredi_user_data (user_id, data, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        data = $2,
                        updated_at = NOW()
                """, user_id, self._safe_json_dumps(data))
    
    async def load_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает user_data для пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT data FROM fredi_user_data WHERE user_id = $1",
                    user_id
                )
                
                if row and row['data']:
                    return json.loads(row['data'])
                
                return {}
    
    # ====================== СЕРИАЛИЗОВАННЫЕ ОБЪЕКТЫ ======================
    
    async def save_pickled_context(self, user_id: int, context_obj) -> None:
        """Сохраняет сериализованный объект UserContext"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                pickled = pickle.dumps(context_obj)
                await conn.execute("""
                    INSERT INTO fredi_context_objects (user_id, context_data, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        context_data = $2,
                        updated_at = NOW()
                """, user_id, pickled)
    
    async def load_pickled_context(self, user_id: int):
        """Загружает сериализованный объект UserContext"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT context_data FROM fredi_context_objects WHERE user_id = $1",
                    user_id
                )
                
                if row and row['context_data']:
                    try:
                        return pickle.loads(row['context_data'])
                    except Exception as e:
                        logger.error(f"Ошибка при десериализации контекста пользователя {user_id}: {e}")
                
                return None
    
    # ====================== МАРШРУТЫ ======================
    
    async def save_user_route(
        self,
        user_id: int,
        route_data: Dict[str, Any],
        current_step: int = 1,
        progress: List = None
    ) -> int:
        """Сохраняет маршрут пользователя"""
        if progress is None:
            progress = []
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE fredi_user_routes SET is_active = FALSE
                    WHERE user_id = $1 AND is_active = TRUE
                """, user_id)
                
                route_id = await conn.fetchval("""
                    INSERT INTO fredi_user_routes (
                        user_id, route_data, current_step, progress, is_active
                    ) VALUES ($1, $2, $3, $4, TRUE)
                    RETURNING id
                """, user_id, self._safe_json_dumps(route_data), current_step, self._safe_json_dumps(progress))
                
                return route_id
    
    async def load_user_route(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает активный маршрут пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    SELECT * FROM fredi_user_routes
                    WHERE user_id = $1 AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                """, user_id)
                
                if not row:
                    return None
                
                data = dict(row)
                data['route_data'] = json.loads(data['route_data'])
                data['progress'] = json.loads(data['progress'])
                
                return data
    
    async def update_user_route(
        self,
        route_id: int,
        current_step: int,
        progress: List,
        completed: bool = False
    ):
        """Обновляет прогресс по маршруту"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE fredi_user_routes SET
                        current_step = $2,
                        progress = $3,
                        is_active = NOT $4,
                        completed_at = CASE WHEN $4 THEN NOW() ELSE completed_at END,
                        updated_at = NOW()
                    WHERE id = $1
                """, route_id, current_step, self._safe_json_dumps(progress), completed)
    
    # ====================== РЕЗУЛЬТАТЫ ТЕСТОВ ======================
    
    async def save_test_result(
        self,
        user_id: int,
        test_type: str,
        results: Dict[str, Any],
        profile_code: Optional[str] = None,
        perception_type: Optional[str] = None,
        thinking_level: Optional[int] = None,
        vectors: Optional[Dict[str, float]] = None,
        behavioral_levels: Optional[Dict[str, List[int]]] = None,
        deep_patterns: Optional[Dict] = None,
        confinement_model: Optional[Dict] = None,
        current_destination: Optional[Dict] = None,
        current_route: Optional[Dict] = None
    ) -> int:
        """Сохраняет результат тестирования"""
        
        if vectors is None and 'behavioral_levels' in results:
            vectors = {}
            behavioral = results.get('behavioral_levels', {})
            for vector in ['СБ', 'ТФ', 'УБ', 'ЧВ']:
                levels = behavioral.get(vector, [])
                vectors[vector] = sum(levels) / len(levels) if levels else 3.0
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                test_id = await conn.fetchval("""
                    INSERT INTO fredi_test_results (
                        user_id, test_type, results, profile_code,
                        perception_type, thinking_level, vectors, behavioral_levels,
                        deep_patterns, confinement_model, current_destination, current_route
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING id
                """,
                    user_id,
                    test_type,
                    self._safe_json_dumps(results),
                    profile_code,
                    perception_type,
                    thinking_level,
                    self._safe_json_dumps(vectors) if vectors else None,
                    self._safe_json_dumps(behavioral_levels) if behavioral_levels else None,
                    self._safe_json_dumps(deep_patterns) if deep_patterns else None,
                    self._safe_json_dumps(confinement_model) if confinement_model else None,
                    self._safe_json_dumps(current_destination) if current_destination else None,
                    self._safe_json_dumps(current_route) if current_route else None
                )
                
                return test_id
    
    async def get_user_test_results(
        self,
        user_id: int,
        limit: int = 10,
        test_type: Optional[str] = None
    ) -> List[Dict]:
        """Получает последние результаты тестов пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                if test_type:
                    rows = await conn.fetch("""
                        SELECT * FROM fredi_test_results
                        WHERE user_id = $1 AND test_type = $2
                        ORDER BY created_at DESC
                        LIMIT $3
                    """, user_id, test_type, limit)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM fredi_test_results
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    """, user_id, limit)
                
                results = []
                for row in rows:
                    data = dict(row)
                    data['results'] = json.loads(data['results'])
                    if data.get('vectors'):
                        data['vectors'] = json.loads(data['vectors'])
                    if data.get('behavioral_levels'):
                        data['behavioral_levels'] = json.loads(data['behavioral_levels'])
                    if data.get('deep_patterns'):
                        data['deep_patterns'] = json.loads(data['deep_patterns'])
                    if data.get('confinement_model'):
                        data['confinement_model'] = json.loads(data['confinement_model'])
                    if data.get('current_destination'):
                        data['current_destination'] = json.loads(data['current_destination'])
                    if data.get('current_route'):
                        data['current_route'] = json.loads(data['current_route'])
                    results.append(data)
                
                return results
    
    async def get_latest_profile(self, user_id: int) -> Optional[Dict]:
        """Получает последний полный профиль пользователя"""
        results = await self.get_user_test_results(user_id, limit=1, test_type='full_profile')
        return results[0] if results else None
    
    # ====================== ОТВЕТЫ НА ТЕСТ ======================
    
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
    ):
        """Сохраняет отдельный ответ на вопрос теста"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO fredi_test_answers (
                        user_id, test_result_id, stage, question_index,
                        question_text, answer_text, answer_value,
                        scores, measures, strategy, dilts, pattern, target
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    user_id,
                    test_result_id,
                    stage,
                    question_index,
                    question_text,
                    answer_text,
                    answer_value,
                    self._safe_json_dumps(scores) if scores else None,
                    measures,
                    strategy,
                    dilts,
                    pattern,
                    target
                )
    
    async def get_test_answers(self, test_result_id: int) -> List[Dict]:
        """Получает все ответы для конкретного результата теста"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                rows = await conn.fetch("""
                    SELECT * FROM fredi_test_answers
                    WHERE test_result_id = $1
                    ORDER BY stage, question_index
                """, test_result_id)
                
                answers = []
                for row in rows:
                    data = dict(row)
                    if data.get('scores'):
                        data['scores'] = json.loads(data['scores'])
                    answers.append(data)
                
                return answers
    
    # ====================== ГИПНОТИЧЕСКИЕ ЯКОРЯ ======================
    
    async def save_hypno_anchor(
        self,
        user_id: int,
        anchor_name: str,
        anchor_state: str,
        anchor_phrase: str,
        emoji: Optional[str] = None
    ) -> int:
        """Сохраняет гипнотический якорь"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                anchor_id = await conn.fetchval("""
                    INSERT INTO fredi_hypno_anchors (user_id, anchor_name, anchor_state, anchor_phrase, emoji)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id, anchor_name) DO UPDATE SET
                        anchor_state = EXCLUDED.anchor_state,
                        anchor_phrase = EXCLUDED.anchor_phrase,
                        emoji = EXCLUDED.emoji,
                        last_used = NOW(),
                        use_count = fredi_hypno_anchors.use_count + 1
                    RETURNING id
                """, user_id, anchor_name, anchor_state, anchor_phrase, emoji)
                
                return anchor_id
    
    async def get_user_anchors(self, user_id: int) -> List[Dict]:
        """Получает все якоря пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                rows = await conn.fetch("""
                    SELECT * FROM fredi_hypno_anchors
                    WHERE user_id = $1
                    ORDER BY use_count DESC, last_used DESC
                """, user_id)
                
                return [dict(row) for row in rows]
    
    async def fire_anchor(self, user_id: int, anchor_name: str) -> Optional[str]:
        """Активирует якорь и обновляет статистику использования"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    UPDATE fredi_hypno_anchors
                    SET last_used = NOW(), use_count = use_count + 1
                    WHERE user_id = $1 AND anchor_name = $2
                    RETURNING anchor_phrase, emoji
                """, user_id, anchor_name)
                
                if row:
                    emoji = row['emoji'] or ''
                    return f"{emoji} {row['anchor_phrase']}".strip()
                
                return None
    
    # ====================== НАПОМИНАНИЯ ======================
    
    async def add_reminder(
        self,
        user_id: int,
        reminder_type: str,
        remind_at: datetime,
        data: Optional[Dict] = None
    ) -> int:
        """Добавляет напоминание"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                reminder_id = await conn.fetchval("""
                    INSERT INTO fredi_reminders (user_id, reminder_type, remind_at, data)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, user_id, reminder_type, remind_at, self._safe_json_dumps(data) if data else None)
                
                return reminder_id
    
    async def get_pending_reminders(self, limit: int = 100) -> List[Dict]:
        """Получает список неотправленных напоминаний"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                rows = await conn.fetch("""
                    SELECT * FROM fredi_reminders
                    WHERE is_sent = FALSE AND remind_at <= NOW()
                    ORDER BY remind_at
                    LIMIT $1
                """, limit)
                
                reminders = []
                for row in rows:
                    data = dict(row)
                    if data.get('data'):
                        data['data'] = json.loads(data['data'])
                    reminders.append(data)
                
                return reminders
    
    async def mark_reminder_sent(self, reminder_id: int):
        """Отмечает напоминание как отправленное"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE fredi_reminders
                    SET is_sent = TRUE, sent_at = NOW()
                    WHERE id = $1
                """, reminder_id)
    
    async def get_user_reminders(
        self,
        user_id: int,
        include_sent: bool = False
    ) -> List[Dict]:
        """Получает все напоминания пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                if include_sent:
                    rows = await conn.fetch("""
                        SELECT * FROM fredi_reminders
                        WHERE user_id = $1
                        ORDER BY remind_at DESC
                    """, user_id)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM fredi_reminders
                        WHERE user_id = $1 AND is_sent = FALSE
                        ORDER BY remind_at
                    """, user_id)
                
                reminders = []
                for row in rows:
                    data = dict(row)
                    if data.get('data'):
                        data['data'] = json.loads(data['data'])
                    reminders.append(data)
                
                return reminders
    
    # ====================== КЭШ ИДЕЙ НА ВЫХОДНЫЕ ======================
    
    async def cache_weekend_ideas(
        self,
        user_id: int,
        ideas_text: str,
        main_vector: str,
        main_level: int
    ) -> int:
        """Сохраняет сгенерированные идеи на выходные в кэш"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    DELETE FROM fredi_weekend_ideas_cache
                    WHERE user_id = $1
                """, user_id)
                
                cache_id = await conn.fetchval("""
                    INSERT INTO fredi_weekend_ideas_cache (user_id, ideas_text, main_vector, main_level)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, user_id, ideas_text, main_vector, main_level)
                
                return cache_id
    
    async def get_cached_weekend_ideas(self, user_id: int) -> Optional[str]:
        """Получает кэшированные идеи на выходные"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    SELECT ideas_text FROM fredi_weekend_ideas_cache
                    WHERE user_id = $1 AND expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT 1
                """, user_id)
                
                return row['ideas_text'] if row else None
    
    # ====================== КЭШ АНАЛИЗА ВОПРОСОВ ======================
    
    async def cache_question_analysis(
        self,
        user_id: int,
        question: str,
        analysis: Dict[str, Any]
    ) -> int:
        """Сохраняет анализ вопроса в кэш"""
        question_hash = hash(question) % 1000000
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    DELETE FROM fredi_question_analysis_cache
                    WHERE user_id = $1 AND question_hash = $2
                """, user_id, question_hash)
                
                cache_id = await conn.fetchval("""
                    INSERT INTO fredi_question_analysis_cache (user_id, question_hash, question_text, analysis)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, user_id, question_hash, question[:200], self._safe_json_dumps(analysis))
                
                return cache_id
    
    async def get_cached_question_analysis(self, user_id: int, question: str) -> Optional[Dict]:
        """Получает кэшированный анализ вопроса"""
        question_hash = hash(question) % 1000000
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    SELECT analysis FROM fredi_question_analysis_cache
                    WHERE user_id = $1 AND question_hash = $2 AND expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT 1
                """, user_id, question_hash)
                
                if row and row['analysis']:
                    return json.loads(row['analysis'])
                
                return None
    
    # ====================== МЫСЛИ ПСИХОЛОГА ======================
    
    async def save_psychologist_thought(
        self,
        user_id: int,
        thought_text: str,
        test_result_id: Optional[int] = None,
        thought_type: str = 'psychologist_thought',
        thought_summary: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """Сохраняет мысль психолога в отдельную таблицу"""
        try:
            if not self._tables_checked:
                await self.create_psychologist_thoughts_table()
            
            await self.save_telegram_user(user_id)
            
            async with self.get_connection() as conn:
                async with conn.transaction():
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
                        thought_summary, self._safe_json_dumps(metadata or {}))
                    
                    thought_id = row['id']
                    logger.info(f"💾 Мысль психолога сохранена: user={user_id}, id={thought_id}, type={thought_type}")
                    return thought_id
                    
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения мысли: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_psychologist_thought(
        self,
        user_id: int,
        thought_type: str = 'psychologist_thought',
        only_active: bool = True
    ) -> Optional[str]:
        """Получает последнюю мысль психолога"""
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
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
    
    async def get_psychologist_thought_history(
        self,
        user_id: int,
        thought_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Получает историю мыслей психолога"""
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
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
    
    # ====================== СОБЫТИЯ И СТАТИСТИКА ======================
    
    async def log_event(
        self,
        user_id: int,
        event_type: str,
        event_data: Optional[Dict] = None
    ):
        """Логирует событие для статистики"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO fredi_events (user_id, event_type, event_data)
                    VALUES ($1, $2, $3)
                """, user_id, event_type, self._safe_json_dumps(event_data) if event_data else None)
                
                await self.update_last_activity(user_id)
    
    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику за указанный период"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                since = datetime.now() - timedelta(days=days)
                
                total_users = await conn.fetchval("SELECT COUNT(*) FROM fredi_users")
                active_users = await conn.fetchval("""
                    SELECT COUNT(DISTINCT user_id) FROM fredi_events
                    WHERE created_at >= $1
                """, since)
                
                completed_tests = await conn.fetchval("""
                    SELECT COUNT(*) FROM fredi_test_results
                    WHERE created_at >= $1
                """, since)
                
                event_types = await conn.fetch("""
                    SELECT event_type, COUNT(*) as count
                    FROM fredi_events
                    WHERE created_at >= $1
                    GROUP BY event_type
                    ORDER BY count DESC
                """, since)
                
                perception_types = await conn.fetch("""
                    SELECT perception_type, COUNT(*) as count
                    FROM fredi_test_results
                    WHERE perception_type IS NOT NULL AND created_at >= $1
                    GROUP BY perception_type
                    ORDER BY count DESC
                """, since)
                
                thinking_levels = await conn.fetch("""
                    SELECT thinking_level, COUNT(*) as count
                    FROM fredi_test_results
                    WHERE thinking_level IS NOT NULL AND created_at >= $1
                    GROUP BY thinking_level
                    ORDER BY thinking_level
                """, since)
                
                profiles = await conn.fetch("""
                    SELECT profile_code, COUNT(*) as count
                    FROM fredi_test_results
                    WHERE profile_code IS NOT NULL AND created_at >= $1
                    GROUP BY profile_code
                    ORDER BY count DESC
                    LIMIT 20
                """, since)
                
                daily = await conn.fetch("""
                    SELECT DATE(created_at) as date,
                           COUNT(DISTINCT user_id) as users,
                           COUNT(*) as events
                    FROM fredi_events
                    WHERE created_at >= $1
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, since)
                
                return {
                    'period_days': days,
                    'total_users': total_users,
                    'active_users': active_users,
                    'completed_tests': completed_tests,
                    'event_types': [dict(et) for et in event_types],
                    'perception_types': [dict(pt) for pt in perception_types],
                    'thinking_levels': [dict(tl) for tl in thinking_levels],
                    'profiles': [dict(p) for p in profiles],
                    'daily': [dict(d) for d in daily]
                }
    
    # ====================== ОЧИСТКА СТАРЫХ ДАННЫХ ======================
    
    async def cleanup_old_data(self, days: int = 30):
        """Очищает старые данные"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                await conn.execute("""
                    DELETE FROM fredi_events
                    WHERE created_at < NOW() - INTERVAL '1 day' * $1
                """, days)
                
                await conn.execute("""
                    UPDATE fredi_user_routes
                    SET is_active = FALSE
                    WHERE is_active = TRUE
                      AND updated_at < NOW() - INTERVAL '90 days'
                """)
                
                await conn.execute("""
                    DELETE FROM fredi_reminders
                    WHERE (is_sent = TRUE AND sent_at < NOW() - INTERVAL '7 days')
                       OR (is_sent = FALSE AND remind_at < NOW() - INTERVAL '7 days')
                """)
                
                await conn.execute("""
                    DELETE FROM fredi_weekend_ideas_cache WHERE expires_at < NOW()
                """)
                await conn.execute("""
                    DELETE FROM fredi_question_analysis_cache WHERE expires_at < NOW()
                """)
                
                await conn.execute("""
                    DELETE FROM fredi_psychologist_thoughts
                    WHERE is_active = FALSE AND created_at < NOW() - INTERVAL '180 days'
                """)
                
                logger.info(f"🧹 Очистка старых данных выполнена")
    
    # ====================== ЦЕЛИ ПОЛЬЗОВАТЕЛЯ ======================
    
    async def save_user_goal(self, user_id: int, goal_text: str) -> Optional[int]:
        """Сохраняет цель пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                goal_id = await conn.fetchval("""
                    INSERT INTO fredi_user_goals (user_id, goal_text)
                    VALUES ($1, $2)
                    RETURNING id
                """, user_id, goal_text)
                
                return goal_id
    
    async def get_user_goals(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает цели пользователя"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                rows = await conn.fetch("""
                    SELECT id, goal_text, status, completed_at, created_at 
                    FROM fredi_user_goals 
                    WHERE user_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, user_id, limit)
                
                return [dict(row) for row in rows]
    
    # ====================== МИГРАЦИЯ ======================
    
    async def migrate_existing_users(
        self,
        user_data_dict: Dict[int, Dict],
        user_contexts_dict: Dict[int, Any],
        user_names_dict: Dict[int, str],
        user_routes_dict: Dict[int, Dict]
    ):
        """Мигрирует существующих пользователей из памяти в БД"""
        migrated_users = 0
        migrated_contexts = 0
        migrated_data = 0
        migrated_routes = 0
        migrated_tests = 0
        
        for user_id in set(
            list(user_data_dict.keys()) +
            list(user_contexts_dict.keys()) +
            list(user_names_dict.keys()) +
            list(user_routes_dict.keys())
        ):
            async with self.get_connection() as conn:
                async with conn.transaction():
                    first_name = user_names_dict.get(user_id)
                    if first_name:
                        await self.save_telegram_user(
                            user_id=user_id,
                            first_name=first_name
                        )
                        migrated_users += 1
                    
                    if user_id in user_contexts_dict:
                        context = user_contexts_dict[user_id]
                        if not hasattr(context, 'name') or not context.name:
                            context.name = user_names_dict.get(user_id)
                        await self.save_user_context(user_id, context)
                        migrated_contexts += 1
                    
                    if user_id in user_data_dict:
                        data = user_data_dict[user_id]
                        await self.save_user_data(user_id, data)
                        migrated_data += 1
                        
                        if data.get('profile_data') or data.get('ai_generated_profile'):
                            confinement_model_dict = None
                            if data.get('confinement_model'):
                                confinement_model_dict = self._make_json_serializable(data['confinement_model'])
                            
                            test_id = await self.save_test_result(
                                user_id=user_id,
                                test_type='full_profile',
                                results=data,
                                profile_code=data.get('profile_data', {}).get('display_name'),
                                perception_type=data.get('perception_type'),
                                thinking_level=data.get('thinking_level'),
                                vectors=data.get('behavioral_levels'),
                                deep_patterns=data.get('deep_patterns'),
                                confinement_model=confinement_model_dict
                            )
                            migrated_tests += 1
                            
                            if test_id and data.get('all_answers'):
                                for answer in data['all_answers']:
                                    await self.save_test_answer(
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
                    
                    if user_id in user_routes_dict:
                        route_data = user_routes_dict[user_id]
                        await self.save_user_route(
                            user_id=user_id,
                            route_data=route_data.get('route_data', {}),
                            current_step=route_data.get('current_step', 1),
                            progress=route_data.get('progress', [])
                        )
                        migrated_routes += 1
        
        logger.info(f"✅ Мигрировано: {migrated_users} пользователей, {migrated_contexts} контекстов, "
                   f"{migrated_data} наборов данных, {migrated_routes} маршрутов, {migrated_tests} тестов")
        
        return {
            'users': migrated_users,
            'contexts': migrated_contexts,
            'data': migrated_data,
            'routes': migrated_routes,
            'tests': migrated_tests
        }
