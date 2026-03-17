#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакет с обработчиками для MAX
Импортирует все обработчики команд и callback'ов
"""

import logging

logger = logging.getLogger(__name__)

# Импортируем все обработчики
from . import start
from . import modes
from . import stages
from . import profile
from . import goals
from . import context
from . import questions
from . import admin
from . import help
from . import reality
from . import routes
from . import voice  # 👈 ДОБАВЛЕНО

logger.info("✅ Все обработчики загружены")

# Список всех доступных модулей для удобства
__all__ = [
    'start',
    'modes', 
    'stages',
    'profile',
    'goals',
    'context',
    'questions',
    'admin',
    'help',
    'reality',
    'routes',
    'voice'  # 👈 ДОБАВЛЕНО
]
