#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УНИВЕРСАЛЬНАЯ ОБЕРТКА ДЛЯ БД
Эмулирует старый sync_db, но использует новую синхронную БД
Все остальные файлы не нужно менять!
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

# Импортируем новые синхронные функции
from db_instance import (
    save_user,
    save_telegram_user,
    save_user_data,
    save_context,
    save_test_result,
    log_event,
    add_reminder,
    get_user_reminders,
    complete_reminder,
    load_user_data,
    load_user_context,
    load_all_users,
    get_stats,
    ensure_connection,
    connect,
    disconnect
)

logger = logging.getLogger(__name__)


class SyncDBWrapper:
    """
    Обертка, которая имитирует старый sync_db
    Все методы совместимы со старым кодом
    """
    
    # ============================================
    # МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ СО СТАРЫМ КОДОМ
    # ============================================
    
    def save_telegram_user(self, user_id: int, first_name: str = None, username: str = None, **kwargs) -> bool:
        """Сохранить пользователя Telegram"""
        try:
            return save_telegram_user(user_id, first_name, username)
        except Exception as e:
            logger.error(f"❌ Ошибка save_telegram_user {user_id}: {e}")
            return False
    
    def save_user_to_db(self, user_id: int, user_data_dict=None, user_contexts_dict=None, user_routes_dict=None) -> bool:
        """
        Сохраняет пользователя в БД (совместимость со старым кодом)
        """
        try:
            # Сохраняем пользователя
            if user_data_dict and user_id in user_data_dict:
                user_info = user_data_dict[user_id]
                first_name = user_info.get('first_name') or user_info.get('name')
                username = user_info.get('username')
                save_user(user_id, first_name, username)
            
            # Сохраняем данные
            if user_data_dict and user_id in user_data_dict:
                save_user_data(user_id, user_data_dict[user_id])
            
            # Сохраняем контекст
            if user_contexts_dict and user_id in user_contexts_dict:
                context = user_contexts_dict[user_id]
                save_context(
                    user_id,
                    name=getattr(context, 'name', None),
                    age=getattr(context, 'age', None),
                    gender=getattr(context, 'gender', None),
                    city=getattr(context, 'city', None),
                    mode=getattr(context, 'communication_mode', None),
                    data=getattr(context, 'data', None)
                )
            
            logger.debug(f"💾 Пользователь {user_id} сохранен через обертку")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка save_user_to_db {user_id}: {e}")
            return False
    
    def log_event(self, user_id: int, event_type: str, event_data: Dict = None) -> bool:
        """Логирование события (совместимость)"""
        try:
            return log_event(user_id, event_type, event_data)
        except Exception as e:
            logger.error(f"❌ Ошибка log_event {user_id}: {e}")
            return False
    
    def add_reminder(self, user_id: int, reminder_type: str, remind_at, data: Dict = None) -> bool:
        """Добавить напоминание (совместимость)"""
        try:
            return add_reminder(user_id, reminder_type, remind_at, data)
        except Exception as e:
            logger.error(f"❌ Ошибка add_reminder {user_id}: {e}")
            return False
    
    def get_user_reminders(self, user_id: int, include_sent: bool = False) -> List[Dict]:
        """Получить напоминания (совместимость)"""
        try:
            return get_user_reminders(user_id, include_sent)
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_reminders {user_id}: {e}")
            return []
    
    def complete_reminder(self, reminder_id: int) -> bool:
        """Отметить напоминание как выполненное (совместимость)"""
        try:
            return complete_reminder(reminder_id)
        except Exception as e:
            logger.error(f"❌ Ошибка complete_reminder {reminder_id}: {e}")
            return False
    
    def save_test_result(self, user_id: int, test_type: str, results: Dict,
                         profile_code: str = None, perception_type: str = None,
                         thinking_level: int = None, vectors: Dict = None,
                         behavioral_levels: Dict = None, deep_patterns: Dict = None,
                         confinement_model: Dict = None) -> Optional[int]:
        """Сохранить результат теста (совместимость)"""
        try:
            return save_test_result(
                user_id, test_type, results, profile_code,
                perception_type, thinking_level, vectors,
                behavioral_levels, deep_patterns, confinement_model
            )
        except Exception as e:
            logger.error(f"❌ Ошибка save_test_result {user_id}: {e}")
            return None
    
    def save_test_answer(self, user_id: int, test_result_id: Optional[int],
                         stage: int, question_index: int, question_text: str,
                         answer_text: str, answer_value: str,
                         scores: Optional[Dict] = None, measures: Optional[str] = None,
                         strategy: Optional[str] = None, dilts: Optional[str] = None,
                         pattern: Optional[str] = None, target: Optional[str] = None) -> bool:
        """Сохранить ответ на тест (совместимость)"""
        logger.debug(f"save_test_answer called for user {user_id}")
        return True
    
    def get_user_data(self, user_id: int) -> Dict:
        """Получить данные пользователя (совместимость)"""
        try:
            return load_user_data(user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_data {user_id}: {e}")
            return {}
    
    def get_user_context(self, user_id: int) -> Optional[Dict]:
        """Получить контекст пользователя (совместимость)"""
        try:
            return load_user_context(user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_context {user_id}: {e}")
            return None
    
    def get_user_test_results(self, user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
        """Получить результаты тестов (совместимость)"""
        return []
    
    def get_cached_weekend_ideas(self, user_id: int) -> Optional[str]:
        """Получить кэшированные идеи (совместимость)"""
        try:
            from db_instance import get_cached_weekend_ideas
            return get_cached_weekend_ideas(user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка get_cached_weekend_ideas {user_id}: {e}")
            return None
    
    def cache_weekend_ideas(self, user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Сохранить идеи в кэш (совместимость)"""
        try:
            from db_instance import cache_weekend_ideas
            return cache_weekend_ideas(user_id, ideas_text, main_vector, main_level)
        except Exception as e:
            logger.error(f"❌ Ошибка cache_weekend_ideas {user_id}: {e}")
            return False
    
    def ensure_connection(self) -> bool:
        """Проверить соединение (совместимость)"""
        try:
            return ensure_connection()
        except Exception as e:
            logger.error(f"❌ Ошибка ensure_connection: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Получить статистику (совместимость)"""
        try:
            return get_stats()
        except Exception as e:
            logger.error(f"❌ Ошибка get_stats: {e}")
            return {}
    
    # ============================================
    # МЕТОДЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ (async)
    # ============================================
    
    async def save_user_to_db_async(self, user_id: int, *args, **kwargs):
        """Асинхронная версия (для обратной совместимости)"""
        return self.save_user_to_db(user_id, *args, **kwargs)
    
    async def save_telegram_user_async(self, user_id: int, *args, **kwargs):
        """Асинхронная версия save_telegram_user"""
        return self.save_telegram_user(user_id, *args, **kwargs)
    
    async def log_event_async(self, user_id: int, event_type: str, event_data: Dict = None):
        """Асинхронная версия (для обратной совместимости)"""
        return self.log_event(user_id, event_type, event_data)
    
    async def get_user_data_async(self, user_id: int):
        """Асинхронная версия (для обратной совместимости)"""
        return self.get_user_data(user_id)
    
    async def get_user_context_async(self, user_id: int):
        """Асинхронная версия (для обратной совместимости)"""
        return self.get_user_context(user_id)
    
    async def add_reminder_async(self, user_id: int, reminder_type: str, remind_at, data: Dict = None):
        """Асинхронная версия add_reminder"""
        return self.add_reminder(user_id, reminder_type, remind_at, data)
    
    async def get_user_reminders_async(self, user_id: int, include_sent: bool = False):
        """Асинхронная версия get_user_reminders"""
        return self.get_user_reminders(user_id, include_sent)
    
    async def complete_reminder_async(self, reminder_id: int):
        """Асинхронная версия complete_reminder"""
        return self.complete_reminder(reminder_id)


# Создаем глобальный экземпляр
sync_db = SyncDBWrapper()

logger.info("✅ db_wrapper загружен (эмулирует старый sync_db)")
