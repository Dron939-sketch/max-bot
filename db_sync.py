#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронные обертки для работы с БД - для вызовов из любого потока
"""

import logging
import time
from typing import Optional, Dict, Any

from db_instance import db_loop_manager, db

logger = logging.getLogger(__name__)

class SyncDB:
    """Синхронный интерфейс для БД"""
    
    @staticmethod
    def save_telegram_user(user_id: int, username: str = None, first_name: str = None) -> bool:
        """Синхронное сохранение пользователя"""
        try:
            async def _save():
                return await db.save_telegram_user(user_id, username, first_name)
            
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

# Создаем глобальный экземпляр
sync_db = SyncDB()
