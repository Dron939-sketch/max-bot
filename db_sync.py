#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронные обертки для работы с БД - для вызовов из любого потока
ВЕРСИЯ 2.6 - ДОБАВЛЕНЫ ФУНКЦИИ ДЛЯ МЫСЛЕЙ ПСИХОЛОГА
"""

import logging
import time
import asyncio
import traceback
from typing import Optional, Dict, Any, List

from db_instance import db_loop_manager, db, save_user_to_db as db_save_user
from db_instance import save_telegram_user as db_save_telegram_user
from db_instance import save_test_result_full_async as async_save_test_result

logger = logging.getLogger(__name__)


class SyncDB:
    """Синхронный интерфейс для БД"""
    
    @staticmethod
    def ensure_connection() -> bool:
        """Синхронная проверка соединения с БД"""
        try:
            from db_instance import ensure_db_connection
            result = db_loop_manager.run_coro(ensure_db_connection, timeout=10)
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
            result = db_loop_manager.run_coro(
                db.save_telegram_user,
                user_id, username, first_name, last_name, language_code,
                timeout=10
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_telegram_user: {e}")
            return False
    
    @staticmethod
    def save_user_data(user_id: int, data: Dict) -> bool:
        """Синхронное сохранение данных пользователя"""
        try:
            result = db_loop_manager.run_coro(
                db.save_user_data,
                user_id, data,
                timeout=10
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_data: {e}")
            return False
    
    @staticmethod
    def save_user_to_db(user_id: int) -> bool:
        """Синхронное сохранение пользователя в БД"""
        try:
            result = db_save_user(user_id)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_to_db: {e}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def log_event(user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Синхронное логирование события"""
        try:
            result = db_loop_manager.run_coro(
                db.log_event,
                user_id, event_type, event_data,
                timeout=5
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка log_event: {e}")
            return False
    
    @staticmethod
    def add_reminder(user_id: int, reminder_type: str, remind_at, data: Dict = None) -> Optional[int]:
        """Синхронное добавление напоминания"""
        try:
            result = db_loop_manager.run_coro(
                db.add_reminder,
                user_id, reminder_type, remind_at, data,
                timeout=10
            )
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
            result = db_loop_manager.run_coro(
                db.get_pending_reminders,
                limit,
                timeout=10
            )
            return result if result is not None else []
        except Exception as e:
            logger.error(f"❌ Ошибка get_pending_reminders: {e}")
            return []
    
    @staticmethod
    def mark_reminder_sent(reminder_id: int) -> bool:
        """Синхронная отметка напоминания как отправленного"""
        try:
            result = db_loop_manager.run_coro(
                db.mark_reminder_sent,
                reminder_id,
                timeout=5
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка mark_reminder_sent: {e}")
            return False
    
    @staticmethod
    def get_user_test_results(user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
        """Синхронное получение результатов тестов пользователя"""
        try:
            result = db_loop_manager.run_coro(
                db.get_user_test_results,
                user_id, limit, test_type,
                timeout=10
            )
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
        deep_patterns: Dict = None,
        confinement_model: Dict = None
    ) -> Optional[int]:
        """
        Синхронное сохранение результата теста
        Принимает 9 параметров + results (всего 10 параметров)
        """
        try:
            # Вызываем асинхронную функцию сохранения
            result = db_loop_manager.run_coro(
                async_save_test_result,
                user_id, 
                test_type, 
                results, 
                profile_code,
                perception_type, 
                thinking_level, 
                vectors,
                deep_patterns, 
                confinement_model,
                timeout=30
            )
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка save_test_result: {e}")
            traceback.print_exc()
            return None
    
    # ============================================
    # НОВЫЕ ФУНКЦИИ ДЛЯ МЫСЛЕЙ ПСИХОЛОГА
    # ============================================
    
    @staticmethod
    def save_psychologist_thought(
        user_id: int,
        thought_text: str,
        test_result_id: int = None,
        thought_type: str = 'psychologist_thought',
        thought_summary: str = None,
        metadata: Dict = None
    ) -> Optional[int]:
        """
        Синхронное сохранение мысли психолога
        """
        try:
            from db_instance import save_psychologist_thought
            result = save_psychologist_thought(
                user_id, 
                thought_text, 
                test_result_id, 
                thought_type, 
                thought_summary, 
                metadata
            )
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка save_psychologist_thought: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_psychologist_thought(
        user_id: int,
        thought_type: str = 'psychologist_thought',
        only_active: bool = True
    ) -> Optional[str]:
        """
        Синхронное получение последней мысли психолога
        """
        try:
            from db_instance import get_psychologist_thought
            return get_psychologist_thought(user_id, thought_type, only_active)
        except Exception as e:
            logger.error(f"❌ Ошибка get_psychologist_thought: {e}")
            return None
    
    @staticmethod
    def get_psychologist_thought_history(
        user_id: int,
        thought_type: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Синхронное получение истории мыслей психолога
        """
        try:
            from db_instance import get_psychologist_thought_history
            return get_psychologist_thought_history(user_id, thought_type, limit)
        except Exception as e:
            logger.error(f"❌ Ошибка get_psychologist_thought_history: {e}")
            return []
    
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
            result = db_loop_manager.run_coro(
                db.save_test_answer,
                user_id, test_result_id, stage, question_index,
                question_text, answer_text, answer_value,
                scores, measures, strategy, dilts, pattern, target,
                timeout=10
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка save_test_answer: {e}")
            return False
    
    @staticmethod
    def get_cached_weekend_ideas(user_id: int) -> Optional[str]:
        """Синхронное получение кэшированных идей"""
        try:
            return db_loop_manager.run_coro(
                db.get_cached_weekend_ideas,
                user_id,
                timeout=5
            )
        except Exception as e:
            logger.error(f"❌ Ошибка get_cached_weekend_ideas: {e}")
            return None
    
    @staticmethod
    def cache_weekend_ideas(user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Синхронное сохранение идей в кэш"""
        try:
            result = db_loop_manager.run_coro(
                db.cache_weekend_ideas,
                user_id, ideas_text, main_vector, main_level,
                timeout=10
            )
            return result if result is not None else False
        except Exception as e:
            logger.error(f"❌ Ошибка cache_weekend_ideas: {e}")
            return False
    
    @staticmethod
    def get_user_reminders(user_id: int, include_sent: bool = False) -> List[Dict]:
        """Синхронное получение напоминаний пользователя"""
        try:
            result = db_loop_manager.run_coro(
                db.get_user_reminders,
                user_id, include_sent,
                timeout=10
            )
            return result if result is not None else []
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_reminders: {e}")
            return []
    
    @staticmethod
    def get_user_context(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение контекста пользователя"""
        try:
            result = db_loop_manager.run_coro(
                db.load_user_context,
                user_id,
                timeout=10
            )
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_context: {e}")
            return None
    
    @staticmethod
    def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение данных пользователя"""
        try:
            result = db_loop_manager.run_coro(
                db.load_user_data,
                user_id,
                timeout=10
            )
            return result if result is not None else {}
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_data: {e}")
            return {}
    
    @staticmethod
    def get_telegram_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение информации о пользователе Telegram"""
        try:
            result = db_loop_manager.run_coro(
                db.get_telegram_user,
                user_id,
                timeout=10
            )
            return result if result is not None else None
        except Exception as e:
            logger.error(f"❌ Ошибка get_telegram_user: {e}")
            return None
    
    @staticmethod
    def save_user_context(user_id: int, context: Dict[str, Any]) -> bool:
        """Синхронное сохранение контекста пользователя"""
        try:
            from db_instance import save_user_context
            return save_user_context(user_id, context)
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_context: {e}")
            return False
    
    @staticmethod
    def get_user_goals(user_id: int, limit: int = 10) -> List[Dict]:
        """Синхронное получение целей пользователя"""
        try:
            from db_instance import get_user_goals
            return get_user_goals(user_id, limit)
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_goals: {e}")
            return []
    
    @staticmethod
    def save_goal(user_id: int, goal_text: str) -> Optional[int]:
        """Синхронное сохранение цели"""
        try:
            from db_instance import save_goal
            return save_goal(user_id, goal_text)
        except Exception as e:
            logger.error(f"❌ Ошибка save_goal: {e}")
            return None


# Создаем глобальный экземпляр
sync_db = SyncDB()

logger.info("✅ sync_db инициализирован (версия 2.6 с поддержкой мыслей психолога)")
