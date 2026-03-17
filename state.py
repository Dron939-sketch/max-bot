#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль состояний и глобальных хранилищ для MAX
"""

import logging
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
# ЭКСПОРТ
# ============================================

__all__ = [
    # Глобальные хранилища
    'user_data',
    'user_names',
    'user_contexts',
    'user_state_data',
    'user_states',
    
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
    
    # Функции для получения данных пользователя
    'get_user_name',      # ✅ ДОБАВЛЕНО
    'get_user_data',      # ✅ ДОБАВЛЕНО
]
