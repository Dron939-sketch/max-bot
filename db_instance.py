#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованный доступ к экземпляру базы данных
ИСПРАВЛЕНИЕ: Устранение циклического импорта с main.py
ВЕРСИЯ 2.0: Полная интеграция со state.py
"""

import os
import json
import pickle
import logging
from typing import Dict, Any, Optional
from database import BotDatabase

logger = logging.getLogger(__name__)

# URL базы данных из переменных окружения Render
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
)

# Создаем единый экземпляр БД
db = BotDatabase(DATABASE_URL)

async def init_db():
    """Инициализация подключения к БД"""
    try:
        await db.connect()
        logger.info("✅ Подключение к PostgreSQL установлено")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

async def close_db():
    """Закрытие подключения к БД"""
    try:
        await db.disconnect()
        logger.info("🔒 Подключение к PostgreSQL закрыто")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии подключения: {e}")

# ============================================
# ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ ДАННЫХ
# ============================================

async def save_user_to_db(
    user_id: int, 
    user_data_dict: Dict[int, Dict] = None, 
    user_contexts_dict: Dict[int, Any] = None, 
    user_routes_dict: Dict[int, Dict] = None
):
    """
    Сохраняет данные конкретного пользователя в БД
    Универсальная функция, которая принимает данные из state.py
    """
    try:
        # Если данные не переданы, пытаемся импортировать из state
        if user_data_dict is None or user_contexts_dict is None or user_routes_dict is None:
            try:
                from state import user_data as global_user_data, user_contexts as global_user_contexts, user_routes as global_user_routes
                user_data_dict = global_user_data if user_data_dict is None else user_data_dict
                user_contexts_dict = global_user_contexts if user_contexts_dict is None else user_contexts_dict
                user_routes_dict = global_user_routes if user_routes_dict is None else user_routes_dict
            except ImportError:
                logger.warning(f"⚠️ Не удалось импортировать глобальные данные для user {user_id}")
                return False
        
        # Сохраняем пользователя в таблицу fredi_users
        if user_id in user_data_dict:
            user_info = user_data_dict[user_id]
            first_name = user_info.get('first_name') or user_info.get('name')
            username = user_info.get('username')
            
            await db.save_telegram_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        
        # Сохраняем user_data (результаты тестов, профиль)
        if user_id in user_data_dict:
            await db.save_user_data(user_id, user_data_dict[user_id])
        
        # Сохраняем контекст (UserContext объект)
        if user_id in user_contexts_dict:
            context = user_contexts_dict[user_id]
            await db.save_user_context(user_id, context)
            # Также сохраняем pickled версию как резерв
            await db.save_pickled_context(user_id, context)
        
        # Сохраняем маршрут
        if user_id in user_routes_dict:
            route = user_routes_dict[user_id]
            await db.save_user_route(
                user_id=user_id,
                route_data=route.get('route_data', {}),
                current_step=route.get('current_step', 1),
                progress=route.get('progress', [])
            )
        
        logger.debug(f"💾 Данные пользователя {user_id} сохранены в БД")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id} в БД: {e}")
        import traceback
        traceback.print_exc()
        return False

async def save_test_result_to_db(
    user_id: int,
    test_type: str,
    user_data_dict: Dict[int, Dict]
):
    """Сохраняет результаты теста в БД"""
    try:
        data = user_data_dict.get(user_id, {})
        
        # Получаем profile_code из данных
        profile_code = None
        if data.get("profile_data"):
            profile_code = data["profile_data"].get("display_name")
        
        # Сохраняем результат теста
        test_id = await db.save_test_result(
            user_id=user_id,
            test_type=test_type,
            results=data,
            profile_code=profile_code,
            perception_type=data.get("perception_type"),
            thinking_level=data.get("thinking_level"),
            vectors=data.get("behavioral_levels"),
            deep_patterns=data.get("deep_patterns"),
            confinement_model=data.get("confinement_model")
        )
        
        # Сохраняем все ответы, если есть
        all_answers = data.get("all_answers", [])
        if all_answers and test_id:
            for answer in all_answers:
                await db.save_test_answer(
                    user_id=user_id,
                    test_result_id=test_id,
                    stage=answer.get('stage', 0),
                    question_index=answer.get('question_index', 0),
                    question_text=answer.get('question', ''),
                    answer_text=answer.get('answer', ''),
                    answer_value=answer.get('option', ''),
                    scores=answer.get('scores'),
                    measures=answer.get('measures'),
                    strategy=answer.get('strategy'),
                    dilts=answer.get('dilts'),
                    pattern=answer.get('pattern'),
                    target=answer.get('target')
                )
        
        return test_id
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов теста для {user_id}: {e}")
        return None

# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'db',
    'init_db',
    'close_db',
    'save_user_to_db',
    'save_test_result_to_db'
]
