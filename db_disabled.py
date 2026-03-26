#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Заглушка для базы данных (БД временно отключена)
Все операции работают в памяти, данные не сохраняются
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# КЛАССЫ-ЗАГЛУШКИ
# ============================================

class DummyDB:
    """Заглушка для BotDatabase"""
    
    def __init__(self):
        self.pool = None
        self._closed = False
    
    async def connect(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] connect()")
        return None
    
    async def disconnect(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] disconnect()")
        return None
    
    async def get_connection(self):
        logger.debug("⚠️ [ЗАГЛУШКА] get_connection()")
        return None
    
    async def create_tables(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] create_tables()")
        return None
    
    async def save_telegram_user(self, *args, **kwargs):
        logger.debug(f"💾 [ЗАГЛУШКА] save_telegram_user: {args[0] if args else '?'}")
        return True
    
    async def get_telegram_user(self, *args, **kwargs):
        return None
    
    async def update_last_activity(self, *args, **kwargs):
        pass
    
    async def save_user_context(self, *args, **kwargs):
        logger.debug(f"💾 [ЗАГЛУШКА] save_user_context: {args[0] if args else '?'}")
        return None
    
    async def load_user_context(self, *args, **kwargs):
        return None
    
    async def save_user_data(self, *args, **kwargs):
        logger.debug(f"💾 [ЗАГЛУШКА] save_user_data: {args[0] if args else '?'}")
        return None
    
    async def load_user_data(self, *args, **kwargs):
        return {}
    
    async def save_pickled_context(self, *args, **kwargs):
        pass
    
    async def load_pickled_context(self, *args, **kwargs):
        return None
    
    async def save_user_route(self, *args, **kwargs):
        return 1
    
    async def load_user_route(self, *args, **kwargs):
        return None
    
    async def update_user_route(self, *args, **kwargs):
        pass
    
    async def save_test_result(self, *args, **kwargs):
        return 1
    
    async def get_user_test_results(self, *args, **kwargs):
        return []
    
    async def get_latest_profile(self, *args, **kwargs):
        return None
    
    async def save_test_answer(self, *args, **kwargs):
        pass
    
    async def get_test_answers(self, *args, **kwargs):
        return []
    
    async def save_hypno_anchor(self, *args, **kwargs):
        return 1
    
    async def get_user_anchors(self, *args, **kwargs):
        return []
    
    async def fire_anchor(self, *args, **kwargs):
        return None
    
    async def add_reminder(self, *args, **kwargs):
        return 1
    
    async def get_pending_reminders(self, *args, **kwargs):
        return []
    
    async def mark_reminder_sent(self, *args, **kwargs):
        pass
    
    async def get_user_reminders(self, *args, **kwargs):
        return []
    
    async def cache_weekend_ideas(self, *args, **kwargs):
        return 1
    
    async def get_cached_weekend_ideas(self, *args, **kwargs):
        return None
    
    async def cache_question_analysis(self, *args, **kwargs):
        return 1
    
    async def get_cached_question_analysis(self, *args, **kwargs):
        return None
    
    async def save_psychologist_thought(self, *args, **kwargs):
        logger.debug(f"🧠 [ЗАГЛУШКА] save_psychologist_thought: {args[0] if args else '?'}")
        return 1
    
    async def get_psychologist_thought(self, *args, **kwargs):
        return None
    
    async def get_psychologist_thought_history(self, *args, **kwargs):
        return []
    
    async def log_event(self, *args, **kwargs):
        logger.debug(f"📝 [ЗАГЛУШКА] log_event: {args[0] if args else '?'} - {args[1] if len(args) > 1 else '?'}")
        return None
    
    async def get_stats(self, *args, **kwargs):
        return {}
    
    async def cleanup_old_data(self, *args, **kwargs):
        pass
    
    async def migrate_existing_users(self, *args, **kwargs):
        return {}
    
    async def save_user_goal(self, *args, **kwargs):
        return 1
    
    async def get_user_goals(self, *args, **kwargs):
        return []


class DummyLoopManager:
    """Заглушка для DBLoopManager"""
    
    def __init__(self):
        self.loop = None
        self._db_instance = DummyDB()
    
    def init(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] DBLoopManager.init()")
        pass
    
    def is_ready(self) -> bool:
        return False
    
    def run_coro(self, coro_func: Callable[..., Awaitable], *args, timeout: int = 45, **kwargs):
        """Заглушка — возвращает None или результат"""
        logger.debug(f"⚠️ [ЗАГЛУШКА] run_coro: {coro_func.__name__ if hasattr(coro_func, '__name__') else '?'}")
        
        # Для некоторых функций возвращаем значения по умолчанию
        func_name = coro_func.__name__ if hasattr(coro_func, '__name__') else str(coro_func)
        
        if 'save_telegram_user' in func_name:
            return True
        if 'save_user_data' in func_name:
            return True
        if 'save_user_to_db' in func_name:
            return True
        if 'log_event' in func_name:
            return True
        if 'save_psychologist_thought' in func_name:
            return 1
        if 'get_psychologist_thought' in func_name:
            return None
        if 'get_user_goals' in func_name:
            return []
        if 'save_goal' in func_name:
            return 1
        if 'ensure_db_connection' in func_name:
            return True
        if 'load_user_from_db' in func_name:
            return None
        
        return None
    
    def run_task(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] run_task()")
        return None
    
    def shutdown(self, *args, **kwargs):
        logger.debug("⚠️ [ЗАГЛУШКА] shutdown()")
        pass


# ============================================
# ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ
# ============================================

db = DummyDB()
db_loop_manager = DummyLoopManager()


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БД (ЗАГЛУШКИ)
# ============================================

async def init_db():
    """Инициализация БД (заглушка)"""
    logger.info("⚠️ БД ВРЕМЕННО ОТКЛЮЧЕНА — работаем в памяти")
    return True


async def close_db():
    """Закрытие БД (заглушка)"""
    logger.debug("⚠️ [ЗАГЛУШКА] close_db()")
    pass


async def ensure_db_connection(*args, **kwargs):
    """Проверка соединения (заглушка)"""
    return True


async def execute_with_retry(*args, **kwargs):
    """Выполнение с повторами (заглушка)"""
    return None


def load_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """Загрузка пользователя из БД (заглушка)"""
    logger.debug(f"📖 [ЗАГЛУШКА] load_user_from_db: {user_id}")
    return None


def save_telegram_user(*args, **kwargs) -> bool:
    """Сохранение пользователя (заглушка)"""
    return True


def save_user(*args, **kwargs) -> bool:
    """Сохранение пользователя (заглушка)"""
    return True


def save_user_to_db(*args, **kwargs) -> bool:
    """Сохранение пользователя в БД (заглушка)"""
    return True


def save_test_result_to_db(*args, **kwargs):
    """Сохранение результатов теста (заглушка)"""
    return 1


def save_test_result_to_db_full(*args, **kwargs):
    """Сохранение результатов теста (заглушка)"""
    return 1


def log_event(*args, **kwargs) -> bool:
    """Логирование события (заглушка)"""
    return True


def sync_db_call(coro_func):
    """Декоратор для синхронных функций (заглушка)"""
    def wrapper(*args, **kwargs):
        return None
    return wrapper


def save_user_data(*args, **kwargs) -> bool:
    """Сохранение данных пользователя (заглушка)"""
    return True


def get_user_data(*args, **kwargs) -> Optional[Dict]:
    """Получение данных пользователя (заглушка)"""
    return {}


def save_user_context(*args, **kwargs) -> bool:
    """Сохранение контекста пользователя (заглушка)"""
    return True


def get_user_context(*args, **kwargs) -> Optional[Dict]:
    """Получение контекста пользователя (заглушка)"""
    return None


def save_route_data(*args, **kwargs) -> bool:
    """Сохранение маршрута (заглушка)"""
    return True


def save_psychologist_thought(*args, **kwargs) -> Optional[int]:
    """Сохранение мысли психолога (заглушка)"""
    return 1


def get_psychologist_thought(*args, **kwargs) -> Optional[str]:
    """Получение мысли психолога (заглушка)"""
    return None


def get_psychologist_thought_history(*args, **kwargs) -> List[Dict]:
    """Получение истории мыслей (заглушка)"""
    return []


def get_all_psychologist_thoughts(*args, **kwargs) -> List[Dict]:
    """Получение всех мыслей (заглушка)"""
    return []


def delete_psychologist_thought(*args, **kwargs) -> bool:
    """Удаление мысли (заглушка)"""
    return True


def update_psychologist_thought(*args, **kwargs) -> bool:
    """Обновление мысли (заглушка)"""
    return True


def get_thoughts_by_test_result(*args, **kwargs) -> List[Dict]:
    """Получение мыслей по тесту (заглушка)"""
    return []


def get_psychologist_thoughts_stats(*args, **kwargs) -> Dict[str, Any]:
    """Статистика мыслей (заглушка)"""
    return {}


def get_user_goals(*args, **kwargs) -> List[Dict]:
    """Получение целей пользователя (заглушка)"""
    return []


def save_goal(*args, **kwargs) -> Optional[int]:
    """Сохранение цели (заглушка)"""
    return 1


def create_psychologist_thoughts_table(*args, **kwargs):
    """Создание таблицы (заглушка)"""
    return True


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
    'get_user_goals',
    'save_goal',
]

logger.info("✅ db_disabled инициализирован (БД полностью отключена, работа в памяти)")
