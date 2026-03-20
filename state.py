#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль состояний и глобальных хранилищ для MAX
ВЕРСИЯ 2.1 - ИСПРАВЛЕНО: синхронное автосохранение
"""

import logging
import threading
import asyncio
import time
from typing import Dict, Any, Optional
from models import UserContext

logger = logging.getLogger(__name__)

# ============================================
# ГЛОБАЛЬНЫЕ ХРАНИЛИЩА
# ============================================

# Основные данные пользователей (результаты тестов, профили)
user_data: Dict[int, Dict[str, Any]] = {}

# Имена пользователей (для быстрого доступа)
user_names: Dict[int, str] = {}

# Контексты пользователей (город, пол, возраст, погода)
user_contexts: Dict[int, UserContext] = {}

# Данные состояний (для FSM)
user_state_data: Dict[int, Dict[str, Any]] = {}

# Текущие состояния пользователей
user_states: Dict[int, str] = {}

# Маршруты пользователей (для навигации по целям)
user_routes: Dict[int, Dict[str, Any]] = {}


# ============================================
# КЛАСС СОСТОЯНИЙ
# ============================================

class TestStates:
    """Класс-контейнер для состояний (как Enum)"""
    
    # Основные состояния
    stage_1 = "stage_1"
    stage_2 = "stage_2"
    stage_3 = "stage_3"
    stage_4 = "stage_4"
    stage_5 = "stage_5"
    results = "results"
    awaiting_question = "awaiting_question"
    pretest_question = "pretest_question"
    awaiting_context = "awaiting_context"
    mode_selection = "mode_selection"
    
    # Состояния коррекции
    profile_confirmation = "profile_confirmation"
    clarifying_selection = "clarifying_selection"
    clarifying_test = "clarifying_test"
    alternative_test = "alternative_test"
    
    # Состояния для работы с моделью
    viewing_confinement = "viewing_confinement"
    viewing_intervention = "viewing_intervention"
    
    # Состояния профиля и целей
    profile_generated = "profile_generated"
    destination_selection = "destination_selection"
    route_generation = "route_generation"
    route_active = "route_active"
    route_step_active = "route_step_active"
    
    # Состояния для проверки реальности
    collecting_life_context = "collecting_life_context"
    collecting_goal_context = "collecting_goal_context"
    theoretical_path_shown = "theoretical_path_shown"
    reality_check_active = "reality_check_active"
    feasibility_result = "feasibility_result"
    
    # Состояние для пользовательской цели
    awaiting_custom_goal = "awaiting_custom_goal"


# ============================================
# ФУНКЦИИ УПРАВЛЕНИЯ СОСТОЯНИЯМИ
# ============================================

def set_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state
    logger.debug(f"🔄 User {user_id} state set to: {state}")


def get_state(user_id: int) -> Optional[str]:
    """Возвращает текущее состояние пользователя"""
    return user_states.get(user_id)


def clear_state(user_id: int):
    """Очищает состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_state_data:
        del user_state_data[user_id]
    logger.debug(f"🧹 User {user_id} state cleared")


# ============================================
# ФУНКЦИИ УПРАВЛЕНИЯ ДАННЫМИ СОСТОЯНИЙ
# ============================================

def get_state_data(user_id: int) -> Dict[str, Any]:
    """Возвращает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]


def update_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)
    logger.debug(f"📝 User {user_id} state data updated: {list(kwargs.keys())}")


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНТЕКСТОМ
# ============================================

def get_user_context(user_id: int) -> Optional[UserContext]:
    """Возвращает контекст пользователя"""
    return user_contexts.get(user_id)


def get_user_context_dict(user_id: int) -> Dict[str, Any]:
    """Возвращает контекст пользователя в виде словаря"""
    context = user_contexts.get(user_id)
    if context:
        return {
            'city': context.city,
            'gender': context.gender,
            'age': context.age,
            'name': context.name,
            'communication_mode': context.communication_mode,
            'weather_cache': context.weather_cache
        }
    return {}


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С МАРШРУТАМИ
# ============================================

def get_user_route(user_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает активный маршрут пользователя"""
    return user_routes.get(user_id)


def set_user_route(user_id: int, route_data: Dict[str, Any]):
    """Устанавливает маршрут пользователя"""
    user_routes[user_id] = route_data
    logger.debug(f"🗺 User {user_id} route set")


def update_user_route(user_id: int, **kwargs):
    """Обновляет данные маршрута пользователя"""
    if user_id not in user_routes:
        user_routes[user_id] = {}
    user_routes[user_id].update(kwargs)
    logger.debug(f"🗺 User {user_id} route updated: {list(kwargs.keys())}")


def clear_user_route(user_id: int):
    """Очищает маршрут пользователя"""
    if user_id in user_routes:
        del user_routes[user_id]
    logger.debug(f"🗺 User {user_id} route cleared")


# ============================================
# ФУНКЦИИ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЯ
# ============================================

def get_user_name(user_id: int) -> str:
    """
    Получает имя пользователя по ID
    """
    return user_names.get(user_id, "друг")


def get_user_data(user_id: int) -> Dict[str, Any]:
    """
    Получает данные пользователя
    """
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# ============================================

async def load_user_from_db(user_id: int, db_instance) -> bool:
    """
    Загружает данные пользователя из БД в память
    Возвращает True, если данные были загружены
    
    Args:
        user_id: ID пользователя
        db_instance: Экземпляр BotDatabase из db_instance
    """
    try:
        # Загружаем контекст
        context_data = await db_instance.load_user_context(user_id)
        if context_data:
            from models import UserContext
            context = UserContext(user_id)
            
            # Заполняем поля из загруженных данных
            for key, value in context_data.items():
                if hasattr(context, key) and key != 'user_id':
                    setattr(context, key, value)
            
            user_contexts[user_id] = context
            logger.debug(f"📥 Загружен контекст для {user_id}")
        
        # Загружаем данные пользователя
        user_data_dict = await db_instance.load_user_data(user_id)
        if user_data_dict:
            user_data[user_id] = user_data_dict
            logger.debug(f"📥 Загружены данные для {user_id}")
        
        # Загружаем активный маршрут
        route = await db_instance.load_user_route(user_id)
        if route:
            user_routes[user_id] = route
            logger.debug(f"📥 Загружен маршрут для {user_id}")
        
        # Загружаем имя пользователя
        telegram_user = await db_instance.get_telegram_user(user_id)
        if telegram_user and telegram_user.get('first_name'):
            user_names[user_id] = telegram_user['first_name']
        
        return user_id in user_data or user_id in user_contexts
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователя {user_id} из БД: {e}")
        import traceback
        traceback.print_exc()
        return False


def setup_auto_save(interval_seconds: int = 300):
    """
    Настраивает автоматическое сохранение при изменениях
    Вызывается один раз при старте бота
    
    Args:
        interval_seconds: Интервал сохранения в секундах (по умолчанию 5 минут)
    """
    def auto_save_worker():
        """Фоновый поток для автосохранения - СИНХРОННАЯ ВЕРСИЯ"""
        while True:
            time.sleep(interval_seconds)
            try:
                # Используем sync_db вместо прямых вызовов
                from db_sync import sync_db
                
                saved_count = 0
                # Сохраняем всех пользователей, у которых есть данные
                all_users = set(
                    list(user_data.keys()) + 
                    list(user_contexts.keys()) + 
                    list(user_routes.keys())
                )
                
                for uid in all_users:
                    try:
                        if sync_db.save_user_to_db(uid):
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка автосохранения {uid}: {e}")
                
                if saved_count > 0:
                    logger.info(f"💾 Автосохранение: сохранено {saved_count} пользователей")
                
            except Exception as e:
                logger.error(f"❌ Ошибка в автосохранении: {e}")
    
    # Запускаем фоновый поток
    thread = threading.Thread(target=auto_save_worker, daemon=True)
    thread.start()
    logger.info(f"✅ Автосохранение запущено (интервал {interval_seconds} сек)")


def save_all_users_to_db() -> int:
    """
    Синхронно сохраняет всех пользователей в БД (при завершении работы)
    
    Returns:
        Количество сохраненных пользователей
    """
    logger.info("💾 Сохраняем всех пользователей перед завершением...")
    
    from db_sync import sync_db
    
    saved_count = 0
    all_users = set(
        list(user_data.keys()) + 
        list(user_contexts.keys()) + 
        list(user_routes.keys())
    )
    
    for uid in all_users:
        try:
            if sync_db.save_user_to_db(uid):
                saved_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка финального сохранения {uid}: {e}")
    
    logger.info(f"✅ Финальное сохранение: сохранено {saved_count} пользователей")
    return saved_count


def get_stats() -> Dict[str, Any]:
    """Возвращает статистику по данным в памяти"""
    return {
        'users_in_data': len(user_data),
        'users_in_contexts': len(user_contexts),
        'users_in_routes': len(user_routes),
        'users_in_states': len(user_states),
        'users_with_names': len(user_names),
        'total_unique': len(set(
            list(user_data.keys()) + 
            list(user_contexts.keys()) + 
            list(user_routes.keys()) + 
            list(user_states.keys()) + 
            list(user_names.keys())
        ))
    }


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Глобальные хранилища
    'user_data',
    'user_names',
    'user_contexts',
    'user_state_data',
    'user_states',
    'user_routes',
    
    # Класс состояний
    'TestStates',
    
    # Функции управления состояниями
    'set_state',
    'get_state',
    'clear_state',
    
    # Функции управления данными состояний
    'get_state_data',
    'update_state_data',
    
    # Функции для работы с контекстом
    'get_user_context',
    'get_user_context_dict',
    
    # Функции для работы с маршрутами
    'get_user_route',
    'set_user_route',
    'update_user_route',
    'clear_user_route',
    
    # Функции для получения данных пользователя
    'get_user_name',
    'get_user_data',
    
    # Функции для работы с БД
    'load_user_from_db',
    'setup_auto_save',
    'save_all_users_to_db',
    'get_stats'
]
