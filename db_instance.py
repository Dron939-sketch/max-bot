#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТАЯ СИНХРОННАЯ РАБОТА С БД
- Без asyncio
- Без event loops
- Без конфликтов
- Работает из любого потока
- С поддержкой напоминаний и событий
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# СЕРИАЛИЗАЦИЯ ОБЪЕКТОВ
# ============================================

def serialize_object(obj):
    """
    Рекурсивно сериализует объект в JSON-совместимый формат
    Работает с любыми вложенными объектами, включая ConfinementElement
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [serialize_object(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): serialize_object(v) for k, v in obj.items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # Для объектов пользовательских классов (ConfinementElement, UserContext и др.)
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):  # пропускаем приватные атрибуты
                result[key] = serialize_object(value)
        return result
    
    # Если у объекта есть метод to_dict
    if hasattr(obj, 'to_dict'):
        try:
            return serialize_object(obj.to_dict())
        except:
            pass
    
    # Пробуем преобразовать в строку
    try:
        return str(obj)
    except:
        return f"<{type(obj).__name__}>"


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
        _migrate_tables()
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
    
    # Ответы на тест
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_test_answers (
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
    
    # Напоминания (для утренних сообщений)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            reminder_type TEXT NOT NULL,
            remind_at TIMESTAMP NOT NULL,
            data JSONB,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Кэш идей на выходные
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_weekend_ideas_cache (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            ideas_text TEXT NOT NULL,
            main_vector TEXT,
            main_level INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '1 hour'
        )
    """)
    
    # Кэш анализа вопросов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fredi_question_analysis_cache (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            question_hash INTEGER NOT NULL,
            question_text TEXT,
            analysis JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '5 minutes'
        )
    """)
    
    # Индексы
    cur.execute("CREATE INDEX IF NOT EXISTS idx_test_user ON fredi_test_results(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_test_answers_user ON fredi_test_answers(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_test_answers_result ON fredi_test_answers(test_result_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON fredi_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON fredi_reminders(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_date ON fredi_reminders(remind_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_weekend_cache_user ON fredi_weekend_ideas_cache(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_weekend_cache_expires ON fredi_weekend_ideas_cache(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_hash ON fredi_question_analysis_cache(user_id, question_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_expires ON fredi_question_analysis_cache(expires_at)")
    
    _conn.commit()
    cur.close()
    logger.info("✅ Таблицы созданы")


def _migrate_tables():
    """Миграция: добавляем отсутствующие столбцы"""
    cur = _conn.cursor()
    
    # Добавляем completed_at в fredi_reminders если нет
    try:
        cur.execute("""
            ALTER TABLE fredi_reminders 
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP
        """)
        _conn.commit()
        logger.info("✅ Столбец completed_at добавлен в fredi_reminders")
    except Exception as e:
        logger.warning(f"⚠️ Столбец completed_at уже существует или ошибка: {e}")
    
    # Добавляем индекс для незавершенных напоминаний
    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_uncompleted 
            ON fredi_reminders(remind_at) WHERE completed_at IS NULL
        """)
        _conn.commit()
        logger.info("✅ Индекс для незавершенных напоминаний создан")
    except Exception as e:
        logger.warning(f"⚠️ Индекс уже существует или ошибка: {e}")
    
    cur.close()


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


def save_telegram_user(user_id: int, first_name: str = None, username: str = None, **kwargs) -> bool:
    """Сохранить пользователя Telegram (алиас для save_user)"""
    return save_user(user_id, first_name, username)


def save_user_data(user_id: int, data: Dict) -> bool:
    """Сохранить данные пользователя с сериализацией"""
    if not ensure_connection():
        return False
    try:
        # Сериализуем данные перед сохранением
        serialized_data = serialize_object(data)
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_user_data (user_id, data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = NOW()
        """, (user_id, Json(serialized_data)))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ save_user_data {user_id}: {e}")
        return False


def save_context(user_id: int, name: str = None, age: int = None, gender: str = None,
                 city: str = None, mode: str = None, data: Dict = None) -> bool:
    """Сохранить контекст пользователя с сериализацией"""
    if not ensure_connection():
        return False
    try:
        # Сериализуем данные перед сохранением
        serialized_data = serialize_object(data) if data else None
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_user_contexts (user_id, name, age, gender, city, communication_mode, weather_cache, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                name = EXCLUDED.name,
                age = EXCLUDED.age,
                gender = EXCLUDED.gender,
                city = EXCLUDED.city,
                communication_mode = EXCLUDED.communication_mode,
                weather_cache = EXCLUDED.weather_cache,
                updated_at = NOW()
        """, (user_id, name, age, gender, city, mode, Json(serialized_data) if serialized_data else None))
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
    """Сохранить результат теста с сериализацией"""
    if not ensure_connection():
        return None
    try:
        # Сериализуем результаты перед сохранением
        serialized_results = serialize_object(results)
        serialized_vectors = serialize_object(vectors) if vectors else None
        serialized_deep_patterns = serialize_object(deep_patterns) if deep_patterns else None
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_test_results 
            (user_id, test_type, results, profile_code, perception_type, 
             thinking_level, vectors, deep_patterns, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (user_id, test_type, Json(serialized_results), profile_code, perception_type,
              thinking_level, Json(serialized_vectors) if serialized_vectors else None,
              Json(serialized_deep_patterns) if serialized_deep_patterns else None))
        test_id = cur.fetchone()[0]
        _conn.commit()
        cur.close()
        logger.info(f"📝 Тест {user_id} сохранен (ID: {test_id})")
        return test_id
    except Exception as e:
        logger.error(f"❌ save_test_result {user_id}: {e}")
        return None


def save_test_answer(
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
    """Сохранить ответ на тест"""
    if not ensure_connection():
        return False
    try:
        # Сериализуем scores если есть
        serialized_scores = serialize_object(scores) if scores else None
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_test_answers 
            (user_id, test_result_id, stage, question_index, question_text, 
             answer_text, answer_value, scores, measures, strategy, dilts, pattern, target, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id, test_result_id, stage, question_index, question_text,
            answer_text, answer_value, 
            Json(serialized_scores) if serialized_scores else None,
            measures, strategy, dilts, pattern, target
        ))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ save_test_answer {user_id}: {e}")
        return False


def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """Логировать событие с сериализацией"""
    if not ensure_connection():
        return False
    try:
        # Сериализуем данные перед сохранением
        serialized_data = serialize_object(event_data) if event_data else None
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_events (user_id, event_type, event_data, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, event_type, Json(serialized_data) if serialized_data else None))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ log_event: {e}")
        return False


# ============================================
# НАПОМИНАНИЯ
# ============================================

def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> bool:
    """Добавить напоминание с сериализацией"""
    if not ensure_connection():
        return False
    try:
        # Сериализуем данные перед сохранением
        serialized_data = serialize_object(data) if data else None
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_reminders (user_id, reminder_type, remind_at, data, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (user_id, reminder_type, remind_at, Json(serialized_data) if serialized_data else None))
        _conn.commit()
        cur.close()
        logger.debug(f"📅 Напоминание {reminder_type} для {user_id} на {remind_at}")
        return True
    except Exception as e:
        logger.error(f"❌ add_reminder: {e}")
        return False


def get_user_reminders(user_id: int, include_sent: bool = False) -> List[Dict]:
    """Получить напоминания пользователя"""
    if not ensure_connection():
        return []
    try:
        cur = _conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT id, reminder_type, remind_at, data, completed_at, created_at
            FROM fredi_reminders
            WHERE user_id = %s
        """
        if not include_sent:
            query += " AND (completed_at IS NULL OR completed_at = '1970-01-01')"
        query += " ORDER BY remind_at DESC LIMIT 100"
        
        cur.execute(query, (user_id,))
        rows = cur.fetchall()
        cur.close()
        
        result = []
        for row in rows:
            # Данные могут быть уже десериализованы
            data = row['data']
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass
            
            result.append({
                'id': row['id'],
                'reminder_type': row['reminder_type'],
                'remind_at': row['remind_at'],
                'data': data,
                'completed_at': row['completed_at'],
                'created_at': row['created_at']
            })
        return result
    except Exception as e:
        logger.error(f"❌ get_user_reminders: {e}")
        return []


def complete_reminder(reminder_id: int) -> bool:
    """Отметить напоминание как выполненное"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        cur.execute("""
            UPDATE fredi_reminders 
            SET completed_at = NOW() 
            WHERE id = %s
        """, (reminder_id,))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ complete_reminder: {e}")
        return False


# ============================================
# КЭШ ИДЕЙ НА ВЫХОДНЫЕ
# ============================================

def get_cached_weekend_ideas(user_id: int) -> Optional[str]:
    """Получить кэшированные идеи на выходные"""
    if not ensure_connection():
        return None
    try:
        cur = _conn.cursor()
        cur.execute("""
            SELECT ideas_text FROM fredi_weekend_ideas_cache
            WHERE user_id = %s AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"❌ get_cached_weekend_ideas: {e}")
        return None


def cache_weekend_ideas(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
    """Сохранить идеи на выходные в кэш"""
    if not ensure_connection():
        return False
    try:
        cur = _conn.cursor()
        # Удаляем старые
        cur.execute("DELETE FROM fredi_weekend_ideas_cache WHERE user_id = %s", (user_id,))
        # Вставляем новые
        cur.execute("""
            INSERT INTO fredi_weekend_ideas_cache (user_id, ideas_text, main_vector, main_level, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + INTERVAL '1 hour')
        """, (user_id, ideas_text, main_vector, main_level))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ cache_weekend_ideas: {e}")
        return False


# ============================================
# КЭШ АНАЛИЗА ВОПРОСОВ
# ============================================

def get_cached_question_analysis(user_id: int, question: str) -> Optional[Dict]:
    """Получить кэшированный анализ вопроса"""
    if not ensure_connection():
        return None
    question_hash = hash(question) % 1000000
    try:
        cur = _conn.cursor()
        cur.execute("""
            SELECT analysis FROM fredi_question_analysis_cache
            WHERE user_id = %s AND question_hash = %s AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, question_hash))
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"❌ get_cached_question_analysis: {e}")
        return None


def cache_question_analysis(user_id: int, question: str, analysis: Dict) -> bool:
    """Сохранить анализ вопроса в кэш с сериализацией"""
    if not ensure_connection():
        return False
    question_hash = hash(question) % 1000000
    try:
        # Сериализуем анализ перед сохранением
        serialized_analysis = serialize_object(analysis)
        
        cur = _conn.cursor()
        cur.execute("""
            INSERT INTO fredi_question_analysis_cache (user_id, question_hash, question_text, analysis, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + INTERVAL '5 minutes')
            ON CONFLICT (user_id, question_hash) DO UPDATE SET
                analysis = EXCLUDED.analysis,
                expires_at = NOW() + INTERVAL '5 minutes'
        """, (user_id, question_hash, question[:500], Json(serialized_analysis)))
        _conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"❌ cache_question_analysis: {e}")
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
        data = row[0] if row else {}
        
        # Если данные в виде строки, парсим JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                pass
        
        return data
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
            SELECT name, age, gender, city, communication_mode, weather_cache
            FROM fredi_user_contexts WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            weather_cache = row[5]
            if isinstance(weather_cache, str):
                try:
                    weather_cache = json.loads(weather_cache)
                except:
                    pass
            
            return {
                'name': row[0],
                'age': row[1],
                'gender': row[2],
                'city': row[3],
                'communication_mode': row[4],
                'weather_cache': weather_cache
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
        cur.execute("SELECT COUNT(*) FROM fredi_test_answers")
        answers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_events")
        events = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_reminders")
        reminders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_weekend_ideas_cache")
        weekend_cache = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fredi_question_analysis_cache")
        question_cache = cur.fetchone()[0]
        cur.close()
        return {
            'users': users,
            'tests': tests,
            'answers': answers,
            'events': events,
            'reminders': reminders,
            'weekend_cache': weekend_cache,
            'question_cache': question_cache
        }
    except Exception as e:
        logger.error(f"❌ get_stats: {e}")
        return {}


# ============================================
# ЗАГЛУШКА ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================

def db_loop_manager():
    """Заглушка для обратной совместимости (для старых файлов)"""
    import asyncio
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'connect',
    'disconnect',
    'ensure_connection',
    'save_user',
    'save_telegram_user',
    'save_user_data',
    'save_context',
    'save_test_result',
    'save_test_answer',
    'log_event',
    'add_reminder',
    'get_user_reminders',
    'complete_reminder',
    'get_cached_weekend_ideas',
    'cache_weekend_ideas',
    'get_cached_question_analysis',
    'cache_question_analysis',
    'load_user_data',
    'load_user_context',
    'load_all_users',
    'get_stats',
    'db_loop_manager',
    'serialize_object'
]

logger.info("✅ Простая синхронная БД загружена")
