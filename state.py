#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для управления состояниями пользователей и FSM
"""

from typing import Dict, Any, Optional

# ============================================
# ГЛОБАЛЬНЫЕ ХРАНИЛИЩА
# ============================================

# Данные пользователей
user_data: Dict[int, Dict[str, Any]] = {}

# Имена пользователей
user_names: Dict[int, str] = {}

# Состояния пользователей
user_states: Dict[int, str] = {}

# Дополнительные данные состояний
user_state_data: Dict[int, Dict[str, Any]] = {}

# Контексты пользователей (будут импортироваться из models)
# Чтобы избежать циклических импортов, импортируем внутри функций
# user_contexts = {}


# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class TestStates:
    """Состояния для FSM тестирования и взаимодействия"""
    
    # Этапы тестирования
    stage_1 = "stage_1"
    stage_2 = "stage_2"
    stage_3 = "stage_3"
    stage_4 = "stage_4"
    stage_5 = "stage_5"
    
    # Результаты и вопросы
    results = "results"
    awaiting_question = "awaiting_question"
    pretest_question = "pretest_question"
    
    # Контекст и режимы
    awaiting_context = "awaiting_context"
    mode_selection = "mode_selection"
    
    # Коррекция профиля
    profile_confirmation = "profile_confirmation"
    clarifying_selection = "clarifying_selection"
    clarifying_test = "clarifying_test"
    alternative_test = "alternative_test"
    
    # Модели и интервенции
    viewing_confinement = "viewing_confinement"
    viewing_intervention = "viewing_intervention"
    
    # Профиль и цели
    profile_generated = "profile_generated"
    destination_selection = "destination_selection"
    route_generation = "route_generation"
    route_active = "route_active"
    route_step_active = "route_step_active"
    
    # Проверка реальности
    collecting_life_context = "collecting_life_context"
    collecting_goal_context = "collecting_goal_context"
    theoretical_path_shown = "theoretical_path_shown"
    reality_check_active = "reality_check_active"
    feasibility_result = "feasibility_result"


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С СОСТОЯНИЯМИ
# ============================================

def get_state(user_id: int) -> str:
    """Получает состояние пользователя"""
    return user_states.get(user_id, "")


def set_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state


def get_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]


def update_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)


def clear_state(user_id: int):
    """Очищает состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_state_data:
        del user_state_data[user_id]


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНТЕКСТОМ
# ============================================

def get_user_context(user_id: int):
    """Получает контекст пользователя"""
    # Импортируем здесь, чтобы избежать циклических импортов
    from models import UserContext
    from main import user_contexts
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    return user_contexts[user_id]


def get_user_context_dict(user_id: int) -> Dict[str, Any]:
    """Получает контекст пользователя в виде словаря"""
    context = get_user_context(user_id)
    if context:
        return {
            'name': context.name,
            'city': context.city,
            'gender': context.gender,
            'age': context.age,
            'communication_mode': context.communication_mode,
            'weather_cache': context.weather_cache
        }
    return {}


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Глобальные хранилища
    'user_data',
    'user_names',
    'user_states',
    'user_state_data',
    
    # Состояния
    'TestStates',
    
    # Функции для работы с состояниями
    'get_state',
    'set_state',
    'get_state_data',
    'update_state_data',
    'clear_state',
    
    # Функции для работы с контекстом
    'get_user_context',
    'get_user_context_dict'
]
