#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронные обертки для работы с БД - для вызовов из любого потока
"""

import logging
import time
from typing import Optional, Dict, Any

from db_instance import db_loop_manager, db, ensure_db_connection

logger = logging.getLogger(__name__)

class SyncDB:
    """Синхронный интерфейс для БД"""
    
    @staticmethod
    def ensure_connection() -> bool:
        """Синхронная проверка соединения с БД"""
        try:
            async def _check():
                return await ensure_db_connection()
            return db_loop_manager.run_coro(_check(), timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка ensure_connection: {e}")
            return False
    
    @staticmethod
    def save_telegram_user(
        user_id: int, 
        username: str = None, 
        first_name: str = None,
        last_name: str = None,
        language_code: str = None
    ) -> bool:
        """Синхронное сохранение пользователя"""
        try:
            async def _save():
                return await db.save_telegram_user(
                    user_id, username, first_name, last_name, language_code
                )
            result = db_loop_manager.run_coro(_save(), timeout=10)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_telegram_user: {e}")
            return False
    
    @staticmethod
    def save_user_data(user_id: int, data: Dict) -> bool:
        """Синхронное сохранение данных пользователя"""
        try:
            async def _save():
                await db.save_user_data(user_id, data)
                return True
            return db_loop_manager.run_coro(_save(), timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_data: {e}")
            return False
    
    @staticmethod
    def save_user_to_db(user_id: int) -> bool:
        """Синхронное сохранение пользователя в БД"""
        try:
            from db_instance import save_user_to_db as async_save
            async def _save():
                return await async_save(user_id)
            return db_loop_manager.run_coro(_save(), timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_to_db: {e}")
            return False
    
    @staticmethod
    def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Синхронное логирование события"""
        try:
            async def _log():
                await db.log_event(user_id, event_type, event_data)
                return True
            return db_loop_manager.run_coro(_log(), timeout=5)
        except Exception as e:
            logger.error(f"❌ Ошибка log_event: {e}")
            return False
    
    @staticmethod
    def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
        """Синхронное добавление напоминания"""
        try:
            async def _add():
                return await db.add_reminder(user_id, reminder_type, remind_at, data)
            return db_loop_manager.run_coro(_add(), timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка add_reminder: {e}")
            return None
    
    @staticmethod
    def get_cached_weekend_ideas(user_id: int) -> Optional[str]:
        """Синхронное получение кэшированных идей"""
        try:
            async def _get():
                return await db.get_cached_weekend_ideas(user_id)
            return db_loop_manager.run_coro(_get(), timeout=5)
        except Exception as e:
            logger.error(f"❌ Ошибка get_cached_weekend_ideas: {e}")
            return None
    
    @staticmethod
    def cache_weekend_ideas(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Синхронное сохранение идей в кэш"""
        try:
            async def _cache():
                await db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level)
                return True
            return db_loop_manager.run_coro(_cache(), timeout=10)
        except Exception as e:
            logger.error(f"❌ Ошибка cache_weekend_ideas: {e}")
            return False

# Создаем глобальный экземпляр
sync_db = SyncDB()
