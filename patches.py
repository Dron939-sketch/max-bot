#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Глобальные патчи для Python 3.14
Исправляет проблемы с asyncio.timeout() в популярных библиотеках
"""

import asyncio
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================
# ПАТЧ ДЛЯ ASYNCIO.TIMEOUT
# ============================================

original_timeout = asyncio.timeout
original_timeout_at = asyncio.timeout_at

async def safe_sleep(delay: float, result: Optional[asyncio.Future] = None):
    """Безопасная версия sleep, которая не требует контекста задачи"""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    finally:
        if result and not result.done():
            result.set_result(True)

class SafeTimeout:
    """Безопасная замена asyncio.timeout"""
    
    def __init__(self, delay: float):
        self.delay = delay
        self._task: Optional[asyncio.Task] = None
    
    async def __aenter__(self):
        # Проверяем, есть ли текущая задача
        current_task = asyncio.current_task()
        
        if current_task is None:
            # Нет задачи - создаём фоновый таймер
            self._result = asyncio.get_running_loop().create_future()
            self._task = asyncio.create_task(safe_sleep(self.delay, self._result))
            return self
        else:
            # Есть задача - используем оригинальный timeout
            self._orig = original_timeout(self.delay)
            return await self._orig.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_orig'):
            return await self._orig.__aexit__(exc_type, exc_val, exc_tb)
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Проверяем, был ли таймаут
        if hasattr(self, '_result') and self._result.done():
            raise asyncio.TimeoutError()
        
        return False

def patched_timeout(delay: float):
    """Безопасная версия asyncio.timeout"""
    return SafeTimeout(delay)

def patched_timeout_at(when: float):
    """Безопасная версия asyncio.timeout_at"""
    # Конвертируем absolute time в relative delay
    loop = asyncio.get_running_loop()
    delay = when - loop.time()
    if delay < 0:
        delay = 0
    return SafeTimeout(delay)

# Применяем патчи к asyncio
if sys.version_info >= (3, 14):
    asyncio.timeout = patched_timeout
    asyncio.timeout_at = patched_timeout_at
    logger.info("🔥 Применён глобальный патч для asyncio.timeout")

# ============================================
# ПАТЧ ДЛЯ AIOHTTP
# ============================================

try:
    import aiohttp
    from aiohttp import connector
    
    original_ceil_timeout = connector.ceil_timeout
    
    async def patched_ceil_timeout(delay, ceil_threshold=0):
        """Исправленная версия ceil_timeout"""
        return patched_timeout(delay)
    
    connector.ceil_timeout = patched_ceil_timeout
    logger.info("🔥 Применён патч для aiohttp.ceil_timeout")
except ImportError:
    pass

# ============================================
# ПАТЧ ДЛЯ ASYNCPG
# ============================================

try:
    import asyncpg
    from asyncpg import connection
    
    # Сохраняем оригинальные методы
    original_connect = connection.Connection.__init__
    
    def patched_connection_init(self, *args, **kwargs):
        """Исправленная инициализация соединения"""
        # Убеждаемся, что есть loop
        if 'loop' not in kwargs:
            try:
                kwargs['loop'] = asyncio.get_running_loop()
            except RuntimeError:
                # Если нет запущенного цикла, создаём новый
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                kwargs['loop'] = loop
        
        return original_connect(self, *args, **kwargs)
    
    connection.Connection.__init__ = patched_connection_init
    logger.info("🔥 Применён патч для asyncpg.Connection")
    
except ImportError:
    pass
