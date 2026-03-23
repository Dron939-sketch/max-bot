#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СОВМЕСТИМОСТНЫЙ МОДУЛЬ
Перенаправляет все вызовы на db_wrapper
Все остальные файлы не нужно менять!
"""

import logging
from db_wrapper import sync_db

logger = logging.getLogger(__name__)

# Экспортируем все те же имена
__all__ = ['sync_db']

logger.info("✅ db_sync загружен (перенаправляет на db_wrapper)")
