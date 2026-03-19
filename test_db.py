#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИНИМАЛЬНЫЙ ТЕСТ ПОДКЛЮЧЕНИЯ К БД
Без FastAPI, без бота, без ничего
"""

import asyncio
import asyncpg
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Тот же URL, что и в основном коде
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
)

async def test_connection():
    """Просто пробуем подключиться"""
    logger.info(f"🔄 Пробуем подключиться к БД...")
    
    try:
        # Минимальный тест без пула
        conn = await asyncpg.connect(
            DATABASE_URL,
            timeout=10,
            ssl=True
        )
        
        # Выполняем простой запрос
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Подключение успешно! Версия PostgreSQL: {version}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

async def test_with_pool():
    """Тест с пулом соединений"""
    logger.info(f"🔄 Пробуем создать пул соединений...")
    
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=2,
            timeout=10,
            command_timeout=10,
            ssl=True
        )
        
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"✅ Пул работает! Версия: {version}")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания пула: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

async def main():
    """Запускаем тесты"""
    logger.info("=" * 50)
    logger.info("ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    logger.info("=" * 50)
    
    # Тест 1: Простое подключение
    simple_result = await test_connection()
    logger.info(f"Тест 1 (простое подключение): {'✅ УСПЕХ' if simple_result else '❌ НЕУДАЧА'}")
    
    print()
    
    # Тест 2: Пул соединений
    pool_result = await test_with_pool()
    logger.info(f"Тест 2 (пул соединений): {'✅ УСПЕХ' if pool_result else '❌ НЕУДАЧА'}")
    
    logger.info("=" * 50)
    
    # Итоговый вердикт
    if simple_result and pool_result:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Проблема НЕ в БД")
    elif simple_result and not pool_result:
        logger.info("⚠️ Проблема ТОЛЬКО в пуле соединений")
    elif not simple_result:
        logger.info("❌ Проблема в самом подключении к БД")

if __name__ == "__main__":
    asyncio.run(main())
