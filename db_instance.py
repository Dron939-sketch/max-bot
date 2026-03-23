#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТАЯ СИНХРОННАЯ РАБОТА С БД
- Без asyncio
- Без event loops
- Без конфликтов
- Работает из любого потока
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import Json
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# ПОДКЛЮЧЕНИЕ
# ============================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
)

_conn = None
_connected = False


def connect() -> bool:
    """Подключиться к БД"""
    global _conn, _connected
    try:
        if _conn and not _conn.closed:
            return True
        _conn = psycopg2.connect(DATABASE_URL)
        _connected = True
        _create_tables()
        logger.info("✅ PostgreSQL подключена")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        _connected = False
        return False


def disconnect():
    """Закрыть соединение"""
    global _conn, _connected
    try:
        if _conn and not _conn.closed:
            _conn.close()
        _connected = False
        logger.info("🔒 PostgreSQL закрыта")
    except:
        pass


def ensure_connection() -> bool:
    """Проверить и восстановить соединение"""
    if not _connected or not _conn or _conn.closed:
        return connect()
    try:
        _conn.cursor().execute("SELECT 1")
        return True
    except:
        return connect()


# ============================================
# СОЗДАНИЕ ТАБЛИЦ
# ============================================

def _create_tables():
    """Создать таблицы если не существуют"""
    cur = _conn.cursor()
    
    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Данные пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_user_data (
            user_id BIGINT PRIMARY KEY,
            data JSONB NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Контекст
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_user_contexts (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            city TEXT,
            communication_mode TEXT DEFAULT 'coach',
            weather_cache JSONB,
            data JSONB,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Результаты тестов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_test_results (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            test_type TEXT,
            results JSONB,
            profile_code TEXT,
            perception_type TEXT,
            thinking_level INTEGER,
            vectors JSONB,
            deep_patterns JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # События
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_events (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            event_type TEXT,
            event_data JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Индексы
    cur.execute("CREATE INDEX IF NOT EXISTS idx_test_user ON fredi_test_results(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON fredi_events(user_id)")
    
    _conn.commit()
    cur.close()
    logger.info("✅ Таблицы созданы")


# ============================================
# СОХРАНЕНИЕ
# ============================================

def save_user(user_id: int, first_name: str = None, username: str = None) -> bool:
    """Сохранить пользователя"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_users (user_id, first_name, username, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                username = EXCLUDED.username,
                updated_at = NOW()
        """, (user_id, first_name, username))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ save_user {user_id}: {e}")
        return False


def save_user_data(user_id: int, data: Dict) -> bool:
    """Сохранить данные пользователя"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_user_data (user_id, data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = NOW()
        """, (user_id, Json(data)))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ save_user_data {user_id}: {e}")
        return False


def save_context(user_id: int, name: str = None, age: int = None, gender: str = None,
                 city: str = None, mode: str = None, data: Dict = None) -> bool:
    """Сохранить контекст пользователя"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_user_contexts (user_id, name, age, gender, city, communication_mode, data, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                name = EXCLUDED.name,
                age = EXCLUDED.age,
                gender = EXCLUDED.gender,
                city = EXCLUDED.city,
                communication_mode = EXCLUDED.communication_mode,
                data = EXCLUDED.data,
                updated_at = NOW()
        """, (user_id, name, age, gender, city, mode, Json(data) if data else None))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ save_context {user_id}: {e}")
        return False


def save_test_result(user_id: int, test_type: str, results: Dict,
                     profile_code: str = None, perception_type: str = None,
                     thinking_level: int = None, vectors: Dict = None,
                     deep_patterns: Dict = None) -> Optional[int]:
    """Сохранить результат теста"""
    if not ensure_connection():
        return None
    try:
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_test_results 
            (user_id, test_type, results, profile_code, perception_type, 
             thinking_level, vectors, deep_patterns, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (user_id, test_type, Json(results), profile_code, perception_type,
              thinking_level, Json(vectors) if vectors else None,
              Json(deep_patterns) if deep_patterns else None))
        test_id = cur.fetchone()[0]
        _conn.commit()
        cur.close()
        logger.info(f"📝 Тест {user_id} сохранен (ID: {test_id})")
        return test_id
    except Exception as e:
        logger.error(f"❌ save_test_result {user_id}: {e}")
        return None


def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Логировать событие"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_events (user_id, event_type, event_data, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, event_type, Json(event_data) if event_data else None))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ log_event: {e}")
        return False


# ============================================
# ЗАГРУЗКА
# ============================================

def load_user_data(user_id: int) -> Dict:
    """Загрузить данные пользователя"""
    if not ensure_connection():
        return {}
    try:
        cur = _conn.cursor()
        cur.execute("SELECT data FROM fredi_user_data WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else {}
    except Exception as e:
        logger.error(f"❌ load_user_data {user_id}: {e}")
        return {}


def load_user_context(user_id: int) -> Optional[Dict]:
    """Загрузить контекст пользователя"""
    if not ensure_connection():
        return None
    try:
        cur = _conn.cursor()
        cur.execute("""
            SELECT name, age, gender, city, communication_mode, data 
            FROM fredi_user_contexts WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            return {
                'name': row[0],
                'age': row[1],
                'gender': row[2],
                'city': row[3],
                'communication_mode': row[4],
                'data': row[5]
            }
        return None
    except Exception as e:
        logger.error(f"❌ load_user_context {user_id}: {e}")
        return None


def load_all_users() -> List[int]:
    """Загрузить всех пользователей"""
    if not ensure_connection():
        return []
    try:
        cur = _conn.cursor()
        cur.execute("SELECT user_id FROM fredi_users")
        rows = cur.fetchall()
        cur.close()
        return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"❌ load_all_users: {e}")
        return []


def get_stats() -> Dict:
    """Получить статистику"""
    if not ensure_connection():
        return {}
    try:
        cur = _conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fredi_users")
        users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_test_results")
        tests = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_events")
        events = cur.fetchone()[0]
        cur.close()
        return {
            'users': users,
            'tests': tests,
            'events': events
        }
    except Exception as e:
        logger.error(f"❌ get_stats: {e}")
        return {}


# ============================================
# ЭКСПОРТ (все функции синхронные)
# ============================================

__all__ = [
    'connect',
    'disconnect',
    'ensure_connection',
    'save_user',
    'save_user_data',
    'save_context',
    'save_test_result',
    'log_event',
    'load_user_data',
    'load_user_context',
    'load_all_users',
    'get_stats'
]

logger.info("✅ Простая синхронная БД загружена")
