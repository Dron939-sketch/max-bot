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
from . import smart_questions  # 👈 ДОБАВИТЬ ЭТУ СТРОКУ
from . import admin
from . import help
from . import reality
from . import routes
from . import voice

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
    'smart_questions',  # 👈 ДОБАВИТЬ
    'admin',
    'help',
    'reality',
    'routes',
    'voice'
]
