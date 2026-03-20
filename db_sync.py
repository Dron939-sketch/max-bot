#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронные обертки для работы с БД - для вызовов из любого потока
ВЕРСИЯ 2.1 - ИСПРАВЛЕНО: add_reminder, get_user_test_results, get_pending_reminders
"""

import logging
import time
import asyncio
import traceback
from typing import Optional, Dict, Any, List

from db_instance import db_loop_manager, db, save_user_to_db as db_save_user

logger = logging.getLogger(__name__)


class SyncDB:
    """Синхронный интерфейс для БД"""
    
    @staticmethod
    def ensure_connection() -> bool:
        """Синхронная проверка соединения с БД"""
        try:
            from db_instance import ensure_db_connection
            result = db_loop_manager.run_coro(ensure_db_connection(), timeout=10)
            return result if result is not None else False
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
            result = db_loop_manager.run_coro(_save(), timeout=10)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_data: {e}")
            return False
    
    @staticmethod
    def save_user_to_db(user_id: int) -> bool:
        """
        Синхронное сохранение пользователя в БД.
        Напрямую вызываем синхронную функцию из db_instance
        """
        try:
            # db_save_user уже синхронная функция из db_instance
            result = db_save_user(user_id)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_to_db: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Синхронное логирование события"""
        try:
            async def _log():
                await db.log_event(user_id, event_type, event_data)
                return True
            result = db_loop_manager.run_coro(_log(), timeout=5)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка log_event: {e}")
            return False
    
    @staticmethod
    def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
        """Синхронное добавление напоминания"""
        try:
            # ✅ ИСПРАВЛЕНО: создаем корутину и запускаем через run_coro
            async def _add():
                return await db.add_reminder(user_id, reminder_type, remind_at, data)
            
            result = db_loop_manager.run_coro(_add(), timeout=10)
            logger.debug(f"✅ add_reminder: user={user_id}, type={reminder_type}, result={result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка add_reminder: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_pending_reminders(limit: int = 100) -> List[Dict]:
        """Синхронное получение неотправленных напоминаний"""
        try:
            async def _get():
                return await db.get_pending_reminders(limit)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else []
        except Exception as e:
            logger.error(f"❌ Ошибка get_pending_reminders: {e}")
            return []
    
    @staticmethod
    def mark_reminder_sent(reminder_id: int) -> bool:
        """Синхронная отметка напоминания как отправленного"""
        try:
            async def _mark():
                await db.mark_reminder_sent(reminder_id)
                return True
            result = db_loop_manager.run_coro(_mark(), timeout=5)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка mark_reminder_sent: {e}")
            return False
    
    @staticmethod
    def get_user_test_results(user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
        """Синхронное получение результатов тестов пользователя"""
        try:
            async def _get():
                return await db.get_user_test_results(user_id, limit, test_type)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else []
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_test_results: {e}")
            return []
    
    @staticmethod
    def save_test_result(
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
        """Синхронное сохранение результата теста"""
        try:
            from db_instance import save_test_result_to_db as async_save_test
            async def _save():
                return await async_save_test(
                    user_id, test_type, results, profile_code,
                    perception_type, thinking_level, vectors,
                    behavioral_levels, deep_patterns, confinement_model
                )
            result = db_loop_manager.run_coro(_save(), timeout=30)
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка save_test_result: {e}")
            return None
    
    @staticmethod
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
        """Синхронное сохранение ответа на тест"""
        try:
            async def _save():
                await db.save_test_answer(
                    user_id, test_result_id, stage, question_index,
                    question_text, answer_text, answer_value,
                    scores, measures, strategy, dilts, pattern, target
                )
                return True
            result = db_loop_manager.run_coro(_save(), timeout=10)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_test_answer: {e}")
            return False
    
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
            result = db_loop_manager.run_coro(_cache(), timeout=10)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка cache_weekend_ideas: {e}")
            return False
    
    @staticmethod
    def get_user_reminders(user_id: int, include_sent: bool = False) -> List[Dict]:
        """Синхронное получение напоминаний пользователя"""
        try:
            async def _get():
                return await db.get_user_reminders(user_id, include_sent)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else []
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_reminders: {e}")
            return []
    
    @staticmethod
    def get_user_context(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение контекста пользователя"""
        try:
            async def _get():
                return await db.load_user_context(user_id)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_context: {e}")
            return None
    
    @staticmethod
    def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение данных пользователя"""
        try:
            async def _get():
                return await db.load_user_data(user_id)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else {}
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_data: {e}")
            return {}
    
    @staticmethod
    def get_telegram_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение информации о пользователе Telegram"""
        try:
            async def _get():
                return await db.get_telegram_user(user_id)
            result = db_loop_manager.run_coro(_get(), timeout=10)
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка get_telegram_user: {e}")
            return None


# Создаем глобальный экземпляр
sync_db = SyncDB()

# Для отладки
logger.info("✅ sync_db инициализирован")
logger.info(f"📌 db_loop_manager: {db_loop_manager}")
logger.info(f"📌 db: {db}")
