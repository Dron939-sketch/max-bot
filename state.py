#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Глобальное состояние бота для MAX
"""
from typing import Dict, Any, Optional
from models import UserContext

# Глобальные хранилища
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, UserContext] = {}
user_routes: Dict[int, Dict[str, Any]] = {}

# Хранилище состояний пользователей
user_states: Dict[int, str] = {}
user_state_data: Dict[int, Dict[str, Any]] = {}

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ СОСТОЯНИЯМИ
# ============================================

def get_state(user_id: int) -> str:
    """Получает состояние пользователя"""
    return user_states.get(user_id, "")

def set_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state

def clear_state(user_id: int):
    """Очищает состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_state_data:
        del user_state_data[user_id]

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ СОСТОЯНИЯ
# ============================================

def get_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Алиас для get_state_data (для обратной совместимости)"""
    return get_state_data(user_id)

def update_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def update_user_state_data(user_id: int, **kwargs):
    """Алиас для update_state_data (для обратной совместимости)"""
    update_state_data(user_id, **kwargs)

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНТЕКСТОМ
# ============================================

def get_user_context(user_id: int) -> Optional[UserContext]:
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_context_dict() -> Dict[int, UserContext]:
    """Возвращает словарь контекстов пользователей"""
    return user_contexts

def get_user_names(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "друг")

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОФИЛЕМ
# ============================================

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Получает профиль пользователя"""
    data = user_data.get(user_id, {})
    return data.get("profile_data", {})

def save_user_profile(user_id: int, profile_data: Dict[str, Any]):
    """Сохраняет профиль пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["profile_data"] = profile_data

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def is_test_completed(user_data_dict: dict) -> bool:
    """Проверяет, завершен ли тест"""
    if user_data_dict.get("profile_data"):
        return True
    if user_data_dict.get("ai_generated_profile"):
        return True
    required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
    if all(field in user_data_dict for field in required_minimal):
        return True
    return False


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Глобальные хранилища
    'user_data',
    'user_names',
    'user_contexts',
    'user_routes',
    'user_states',
    'user_state_data',
    
    # Функции для работы с состояниями
    'get_state',
    'set_state',
    'clear_state',
    
    # Функции для работы с данными состояния
    'get_state_data',
    'get_user_state_data',
    'update_state_data',
    'update_user_state_data',
    
    # Функции для работы с контекстом
    'get_user_context',
    'get_user_context_dict',
    'get_user_names',
    'get_user_data',
    
    # Функции для работы с профилем
    'get_user_profile',
    'save_user_profile',
    
    # Вспомогательные функции
    'is_test_completed'
]
