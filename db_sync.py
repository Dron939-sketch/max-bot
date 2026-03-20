#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронные обертки для работы с БД - для вызовов из любого потока
ВЕРСИЯ 2.0 - ДОБАВЛЕНО ПОДРОБНОЕ ЛОГИРОВАНИЕ
"""

import logging
import time
import asyncio
import traceback
from typing import Optional, Dict, Any

from db_instance import db_loop_manager, db, save_user_to_db as db_save_user

logger = logging.getLogger(__name__)

# Включаем детальное логирование для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SyncDB:
    """Синхронный интерфейс для БД"""
    
    @staticmethod
    def ensure_connection() -> bool:
        """Синхронная проверка соединения с БД"""
        try:
            from db_instance import ensure_db_connection
            logger.debug(f"🔍 ensure_connection: вызываем run_coro")
            result = db_loop_manager.run_coro(ensure_db_connection(), timeout=10)
            logger.debug(f"🔍 ensure_connection: результат={result}, тип={type(result)}")
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка ensure_connection: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
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
            logger.debug(f"🔍 save_telegram_user: user={user_id}, first_name={first_name}")
            
            async def _save():
                return await db.save_telegram_user(
                    user_id, username, first_name, last_name, language_code
                )
            
            logger.debug(f"🔍 save_telegram_user: вызываем run_coro")
            result = db_loop_manager.run_coro(_save(), timeout=10)
            logger.debug(f"🔍 save_telegram_user: результат={result}, тип={type(result)}")
            return result if result is not None else False
            
        except Exception as e:
            logger.error(f"❌ Ошибка save_telegram_user: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def save_user_data(user_id: int, data: Dict) -> bool:
        """Синхронное сохранение данных пользователя"""
        try:
            logger.debug(f"🔍 save_user_data: user={user_id}, размер данных={len(str(data))}")
            
            async def _save():
                await db.save_user_data(user_id, data)
                return True
            
            logger.debug(f"🔍 save_user_data: вызываем run_coro")
            result = db_loop_manager.run_coro(_save(), timeout=10)
            logger.debug(f"🔍 save_user_data: результат={result}")
            return result if result is not None else False
            
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_data: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def save_user_to_db(user_id: int) -> bool:
        """
        Синхронное сохранение пользователя в БД.
        С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ
        """
        try:
            logger.info(f"🔍🔍🔍 save_user_to_db ВЫЗВАН для user {user_id}")
            logger.info(f"🔍🔍🔍 Стек вызовов:\n{''.join(traceback.format_stack()[-8:])}")
            
            # Получаем функцию из db_instance
            from db_instance import save_user_to_db as db_save_user
            
            logger.info(f"🔍 Тип db_save_user: {type(db_save_user)}")
            logger.info(f"🔍 db_save_user: {db_save_user}")
            
            # Вызываем функцию
            logger.info(f"🔍 Вызываем db_save_user({user_id})...")
            result = db_save_user(user_id)
            
            logger.info(f"🔍 Результат вызова db_save_user: тип={type(result)}")
            
            # Проверяем, что вернулось
            if asyncio.iscoroutine(result):
                logger.info(f"🔍 РЕЗУЛЬТАТ - КОРУТИНА! Запускаем через run_coro")
                result = db_loop_manager.run_coro(result, timeout=30)
                logger.info(f"🔍 После run_coro: результат={result}, тип={type(result)}")
            else:
                logger.info(f"🔍 Результат НЕ корутина: {result}")
            
            # Возвращаем результат
            if result is True:
                logger.info(f"✅ save_user_to_db: УСПЕШНО сохранен user {user_id}")
            else:
                logger.warning(f"⚠️ save_user_to_db: НЕ УДАЛОСЬ сохранить user {user_id}, result={result}")
            
            return result if result is not None else False
            
        except Exception as e:
            logger.error(f"❌❌❌ КРИТИЧЕСКАЯ ОШИБКА save_user_to_db: {e}")
            logger.error(f"❌❌❌ Полный стек:\n{traceback.format_exc()}")
            return False
    
    @staticmethod
    def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Синхронное логирование события"""
        try:
            logger.debug(f"🔍 log_event: user={user_id}, type={event_type}")
            
            async def _log():
                await db.log_event(user_id, event_type, event_data)
                return True
            
            result = db_loop_manager.run_coro(_log(), timeout=5)
            logger.debug(f"🔍 log_event: результат={result}")
            return result if result is not None else False
            
        except Exception as e:
            logger.error(f"❌ Ошибка log_event: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
        """Синхронное добавление напоминания"""
        try:
            logger.debug(f"🔍 add_reminder: user={user_id}, type={reminder_type}")
            
            async def _add():
                return await db.add_reminder(user_id, reminder_type, remind_at, data)
            
            result = db_loop_manager.run_coro(_add(), timeout=10)
            logger.debug(f"🔍 add_reminder: результат={result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка add_reminder: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def get_cached_weekend_ideas(user_id: int) -> Optional[str]:
        """Синхронное получение кэшированных идей"""
        try:
            logger.debug(f"🔍 get_cached_weekend_ideas: user={user_id}")
            
            async def _get():
                return await db.get_cached_weekend_ideas(user_id)
            
            result = db_loop_manager.run_coro(_get(), timeout=5)
            logger.debug(f"🔍 get_cached_weekend_ideas: результат={type(result)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка get_cached_weekend_ideas: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def cache_weekend_ideas(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Синхронное сохранение идей в кэш"""
        try:
            logger.debug(f"🔍 cache_weekend_ideas: user={user_id}")
            
            async def _cache():
                await db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level)
                return True
            
            result = db_loop_manager.run_coro(_cache(), timeout=10)
            logger.debug(f"🔍 cache_weekend_ideas: результат={result}")
            return result if result is not None else False
            
        except Exception as e:
            logger.error(f"❌ Ошибка cache_weekend_ideas: {e}")
            logger.error(f"❌ Стек: {traceback.format_exc()}")
            return False


# Создаем глобальный экземпляр
sync_db = SyncDB()

# Для отладки
logger.info("✅ sync_db инициализирован")
logger.info(f"📌 db_loop_manager: {db_loop_manager}")
logger.info(f"📌 db: {db}")
logger.info(f"📌 db_save_user: {db_save_user}")
