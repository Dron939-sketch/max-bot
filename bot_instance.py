#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экземпляр бота для MAX
"""
import logging
from maxibot import MaxiBot
from config import MAX_TOKEN

# Настройка логирования
logger = logging.getLogger(__name__)

# Проверяем наличие токена
if not MAX_TOKEN:
    logger.error("❌ MAX_TOKEN не найден в переменных окружения!")
    logger.error("Убедитесь, что токен задан в .env файле или в переменных окружения Render")
    MAX_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"  # Заглушка для локальной разработки

# Создаем экземпляр бота
try:
    bot = MaxiBot(MAX_TOKEN)
    logger.info("✅ Экземпляр бота MAX успешно создан")
except Exception as e:
    logger.error(f"❌ Ошибка при создании бота: {e}")
    raise

# Для удобства импорта
__all__ = ['bot']
