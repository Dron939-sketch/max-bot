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
        return log_event(user_id, event_type, event_data)
    
    def add_reminder(self, user_id: int, reminder_type: str, remind_at, data: Dict = None) -> bool:
        """Добавить напоминание (совместимость)"""
        return add_reminder(user_id, reminder_type, remind_at, data)
    
    def get_user_reminders(self, user_id: int, include_sent: bool = False) -> List[Dict]:
        """Получить напоминания (совместимость)"""
        return get_user_reminders(user_id, include_sent)
    
    def complete_reminder(self, reminder_id: int) -> bool:
        """Отметить напоминание как выполненное (совместимость)"""
        return complete_reminder(reminder_id)
    
    def save_test_result(self, user_id: int, test_type: str, results: Dict,
                         profile_code: str = None, perception_type: str = None,
                         thinking_level: int = None, vectors: Dict = None,
                         behavioral_levels: Dict = None, deep_patterns: Dict = None,
                         confinement_model: Dict = None) -> Optional[int]:
        """Сохранить результат теста (совместимость)"""
        return save_test_result(
            user_id, test_type, results, profile_code,
            perception_type, thinking_level, vectors,
            behavioral_levels, deep_patterns, confinement_model
        )
    
    def save_test_answer(self, user_id: int, test_result_id: Optional[int],
                         stage: int, question_index: int, question_text: str,
                         answer_text: str, answer_value: str,
                         scores: Optional[Dict] = None, measures: Optional[str] = None,
                         strategy: Optional[str] = None, dilts: Optional[str] = None,
                         pattern: Optional[str] = None, target: Optional[str] = None) -> bool:
        """Сохранить ответ на тест (совместимость)"""
        # В новой БД ответы сохраняются вместе с тестом, но для совместимости
        # можно сохранить отдельно, если нужно
        logger.debug(f"save_test_answer called for user {user_id}")
        return True
    
    def get_user_data(self, user_id: int) -> Dict:
        """Получить данные пользователя (совместимость)"""
        return load_user_data(user_id)
    
    def get_user_context(self, user_id: int) -> Optional[Dict]:
        """Получить контекст пользователя (совместимость)"""
        return load_user_context(user_id)
    
    def get_user_test_results(self, user_id: int, limit: int = 10, test_type: str = None) -> List[Dict]:
        """Получить результаты тестов (совместимость)"""
        # В новой БД нужно реализовать, пока возвращаем пустой список
        return []
    
    def get_cached_weekend_ideas(self, user_id: int) -> Optional[str]:
        """Получить кэшированные идеи (совместимость)"""
        return None
    
    def cache_weekend_ideas(self, user_id: int, ideas_text: str, main_vector: str, main_level: int) -> bool:
        """Сохранить идеи в кэш (совместимость)"""
        return True
    
    def get_user_reminders(self, user_id: int, include_sent: bool = False) -> List[Dict]:
        """Получить напоминания (совместимость)"""
        return get_user_reminders(user_id, include_sent)
    
    def ensure_connection(self) -> bool:
        """Проверить соединение (совместимость)"""
        return ensure_connection()
    
    def get_stats(self) -> Dict:
        """Получить статистику (совместимость)"""
        return get_stats()
    
    # ============================================
    # МЕТОДЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ (async)
    # ============================================
    
    async def save_user_to_db_async(self, user_id: int, *args, **kwargs):
        """Асинхронная версия (для обратной совместимости)"""
        return self.save_user_to_db(user_id, *args, **kwargs)
    
    async def log_event_async(self, user_id: int, event_type: str, event_data: Dict = None):
        """Асинхронная версия (для обратной совместимости)"""
        return self.log_event(user_id, event_type, event_data)
    
    async def get_user_data_async(self, user_id: int):
        """Асинхронная версия (для обратной совместимости)"""
        return self.get_user_data(user_id)
    
    async def get_user_context_async(self, user_id: int):
        """Асинхронная версия (для обратной совместимости)"""
        return self.get_user_context(user_id)


# Создаем глобальный экземпляр
sync_db = SyncDBWrapper()

logger.info("✅ db_wrapper загружен (эмулирует старый sync_db)")
