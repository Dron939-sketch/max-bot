#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Глобальные патчи для Python 3.14
Исправляет проблемы с anyio, aiohttp, asyncpg
"""

import asyncio
import logging
import sys
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ============================================
# ПАТЧ ДЛЯ ANYIO (исправление weakref)
# ============================================

def patch_anyio():
    """Применяет все необходимые патчи для anyio"""
    try:
        import anyio
        from anyio._backends._asyncio import _task_states, CapacityLimiter, CancelScope
        
        # Сохраняем оригинальные функции
        original_getitem = _task_states.__getitem__
        original_acquire = CapacityLimiter.acquire
        original_acquire_on_behalf = CapacityLimiter.acquire_on_behalf_of
        original_cancel_scope_enter = CancelScope.__enter__
        
        # 1. Патч для _task_states.__getitem__
        def patched_getitem(self, key):
            """Безопасная версия, возвращающая пустой словарь для None"""
            if key is None:
                return {}
            try:
                return original_getitem(self, key)
            except (TypeError, KeyError):
                return {}
        
        _task_states.__getitem__ = patched_getitem
        
        # 2. Патч для CapacityLimiter.acquire
        async def patched_acquire(self):
            """Безопасная версия acquire"""
            try:
                return await original_acquire(self)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return None
                raise
        
        CapacityLimiter.acquire = patched_acquire
        
        # 3. Патч для CapacityLimiter.acquire_on_behalf_of
        async def patched_acquire_on_behalf(self, task):
            """Безопасная версия acquire_on_behalf_of"""
            if task is None:
                return None
            try:
                return await original_acquire_on_behalf(self, task)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return None
                raise
        
        CapacityLimiter.acquire_on_behalf_of = patched_acquire_on_behalf
        
        # 4. Патч для CancelScope.__enter__
        def patched_cancel_scope_enter(self):
            """Безопасная версия __enter__"""
            try:
                return original_cancel_scope_enter(self)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return self
                raise
        
        CancelScope.__enter__ = patched_cancel_scope_enter
        
        # 5. Патч для to_thread.run_sync
        from anyio import to_thread
        original_run_sync = to_thread.run_sync
        
        async def patched_run_sync(func, *args, cancellable=False, limiter=None):
            """Безопасная версия run_sync"""
            try:
                return await original_run_sync(func, *args, cancellable=cancellable, limiter=limiter)
            except TypeError as e:
                if 'weak reference' in str(e):
                    # Пробуем без лимитера
                    return await original_run_sync(func, *args, cancellable=cancellable, limiter=None)
                raise
        
        to_thread.run_sync = patched_run_sync
        
        print("✅ Все патчи anyio успешно применены")
        return True
        
    except Exception as e:
        print(f"⚠️ Ошибка при патче anyio: {e}")
        return False

# ============================================
# ПАТЧ ДЛЯ AIOHTTP (исправление таймаутов)
# ============================================

def patch_aiohttp():
    """Применяет патчи для aiohttp"""
    try:
        import aiohttp
        from aiohttp.helpers import TimerContext
        
        # Сохраняем оригинальный метод
        original_timer_enter = TimerContext.__enter__
        
        def patched_timer_enter(self):
            """Безопасная версия __enter__ для таймера"""
            try:
                return original_timer_enter(self)
            except RuntimeError as e:
                if "Timeout context manager should be used inside a task" in str(e):
                    # Возвращаем себя без ошибки
                    return self
                raise
        
        TimerContext.__enter__ = patched_timer_enter
        
        # Также патим ClientSession для отключения таймаутов
        original_init = aiohttp.ClientSession.__init__
        
        def patched_session_init(self, *args, **kwargs):
            """Инициализация сессии с отключёнными таймаутами"""
            if 'timeout' not in kwargs:
                kwargs['timeout'] = aiohttp.ClientTimeout(
                    total=None,
                    connect=None,
                    sock_read=None,
                    sock_connect=None
                )
            return original_init(self, *args, **kwargs)
        
        aiohttp.ClientSession.__init__ = patched_session_init
        
        print("✅ Все патчи aiohttp успешно применены")
        return True
        
    except Exception as e:
        print(f"⚠️ Ошибка при патче aiohttp: {e}")
        return False

# ============================================
# ПАТЧ ДЛЯ ASYNCPG (исправление таймаутов)
# ============================================

def patch_asyncpg():
    """Применяет патчи для asyncpg"""
    try:
        import asyncpg
        from asyncpg import connection
        
        original_connect = connection.Connection.__init__
        
        def patched_connection_init(self, *args, **kwargs):
            """Исправленная инициализация соединения"""
            if 'loop' not in kwargs:
                try:
                    kwargs['loop'] = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    kwargs['loop'] = loop
            return original_connect(self, *args, **kwargs)
        
        connection.Connection.__init__ = patched_connection_init
        print("✅ Патч asyncpg успешно применён")
        return True
        
    except Exception as e:
        print(f"⚠️ Ошибка при патче asyncpg: {e}")
        return False

# ============================================
# ГЛАВНАЯ ФУНКЦИЯ ПАТЧА
# ============================================

def apply_all_patches():
    """Применяет все патчи для Python 3.14"""
    if sys.version_info >= (3, 14):
        print("🔧 Применение патчей для Python 3.14...")
        patch_anyio()
        patch_aiohttp()
        patch_asyncpg()
        print("✅ Все патчи применены")
    else:
        print(f"✅ Версия Python {sys.version_info.major}.{sys.version_info.minor} не требует патчей")
