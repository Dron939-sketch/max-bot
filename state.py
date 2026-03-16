#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Глобальное состояние бота для MAX
"""
from typing import Dict, Any
from models import UserContext

# Глобальные хранилища
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, UserContext] = {}
user_routes: Dict[int, Dict[str, Any]] = {}

# Хранилище состояний пользователей
user_states: Dict[int, str] = {}
user_state_data: Dict[int, Dict[str, Any]] = {}

def get_state(user_id: int) -> str:
    return user_states.get(user_id, "")

def set_state(user_id: int, state: str):
    user_states[user_id] = state

def get_state_data(user_id: int) -> Dict[str, Any]:
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_state_data(user_id: int, **kwargs):
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def clear_state(user_id: int):
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_state_data:
        del user_state_data[user_id]

def get_user_context(user_id: int) -> UserContext:
    return user_contexts.get(user_id)

def get_user_context_dict() -> Dict[int, UserContext]:
    return user_contexts
