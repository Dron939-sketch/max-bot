# db_instance.py
"""Централизованный доступ к экземпляру базы данных"""

import os
import logging
from database import BotDatabase

logger = logging.getLogger(__name__)

# URL базы данных из переменных окружения Render
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
)

# Создаем единый экземпляр БД
db = BotDatabase(DATABASE_URL)

async def init_db():
    """Инициализация подключения к БД"""
    await db.connect()
    logger.info("✅ Подключение к PostgreSQL установлено")

async def close_db():
    """Закрытие подключения к БД"""
    await db.disconnect()
    logger.info("🔒 Подключение к PostgreSQL закрыто")

# Функции для сохранения данных
async def save_user_to_db(user_id: int, user_data: dict, user_contexts: dict, user_routes: dict):
    """Сохраняет данные конкретного пользователя в БД"""
    try:
        # Сохраняем user_data
        if user_id in user_data:
            await db.save_user_data(user_id, user_data[user_id])
        
        # Сохраняем контекст
        if user_id in user_contexts:
            await db.save_user_context(user_id, user_contexts[user_id])
            # Также сохраняем pickled версию как резерв
            await db.save_pickled_context(user_id, user_contexts[user_id])
        
        # Сохраняем маршрут
        if user_id in user_routes:
            route = user_routes[user_id]
            await db.save_user_route(
                user_id=user_id,
                route_data=route.get('route_data', {}),
                current_step=route.get('current_step', 1),
                progress=route.get('progress', [])
            )
        
        logger.debug(f"💾 Данные пользователя {user_id} сохранены в БД")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user_id} в БД: {e}")
        return False
