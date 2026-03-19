#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИНИМАЛЬНАЯ ТЕСТОВАЯ ВЕРСИЯ
Проверка: FastAPI + PostgreSQL + Render
"""

import sys
import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== МИНИМАЛЬНЫЙ FASTAPI ==========
app = FastAPI(title="Тестовая версия")

@app.get("/")
async def root():
    """Корневой маршрут"""
    return {
        "status": "ok",
        "message": "API работает",
        "endpoints": {
            "health": "/health",
            "test_db": "/test-db",
            "test_pool": "/test-pool",
            "env": "/env"
        }
    }

@app.get("/health")
async def health():
    """Health check для Render"""
    return {"status": "ok"}

@app.get("/env")
async def show_env():
    """Показывает переменные окружения (без паролей)"""
    env_vars = {}
    
    # Безопасно показываем URL базы данных
    db_url = os.environ.get("DATABASE_URL", "не задан")
    if db_url and db_url != "не задан":
        # Маскируем пароль
        parts = db_url.split('@')
        if len(parts) > 1:
            env_vars["DATABASE_URL"] = f"postgresql://{parts[1]}"
        else:
            env_vars["DATABASE_URL"] = db_url[:50] + "..." if len(db_url) > 50 else db_url
    else:
        env_vars["DATABASE_URL"] = db_url
    
    # Другие переменные
    env_vars["EXTERNAL_DATABASE_URL"] = "задан" if os.environ.get("EXTERNAL_DATABASE_URL") else "не задан"
    env_vars["RENDER"] = os.environ.get("RENDER", "не задан")
    env_vars["PORT"] = os.environ.get("PORT", "не задан")
    
    return env_vars

@app.get("/test-db")
async def test_db():
    """
    Тест подключения к PostgreSQL через прямое соединение
    """
    logger.info("🔍 Тест подключения к БД...")
    
    try:
        import asyncpg
        
        # Получаем URL базы данных
        DATABASE_URL = os.environ.get(
            "EXTERNAL_DATABASE_URL",
            os.environ.get(
                "DATABASE_URL",
                "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
            )
        )
        
        # Логируем URL (без пароля)
        url_parts = DATABASE_URL.split('@')
        safe_url = f"postgresql://{url_parts[1]}" if len(url_parts) > 1 else DATABASE_URL[:50]
        logger.info(f"🔗 Подключение к: {safe_url}")
        
        # Пробуем подключиться с таймаутом
        conn = await asyncpg.connect(
            DATABASE_URL,
            timeout=10,
            command_timeout=10
        )
        
        # Проверяем версию
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Подключено, версия: {version.split()[0] if version else 'unknown'}")
        
        # Проверяем существование таблиц
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_names = [t['table_name'] for t in tables]
        logger.info(f"📊 Найдено таблиц: {len(table_names)}")
        
        await conn.close()
        
        return {
            "status": "ok",
            "database": "connected",
            "version": version.split()[0] if version else "unknown",
            "tables_count": len(table_names),
            "tables": table_names[:10]  # Первые 10 таблиц
        }
        
    except ImportError as e:
        logger.error(f"❌ asyncpg не установлен: {e}")
        return {
            "status": "error",
            "error": "asyncpg not installed",
            "message": "Установите asyncpg: pip install asyncpg"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/test-pool")
async def test_pool():
    """
    Тест создания пула соединений (как в вашем основном коде)
    """
    logger.info("🔍 Тест создания пула соединений...")
    
    try:
        import asyncpg
        
        DATABASE_URL = os.environ.get(
            "EXTERNAL_DATABASE_URL",
            os.environ.get(
                "DATABASE_URL",
                "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a.oregon-postgres.render.com/variatica"
            )
        )
        
        # Создаем пул (как в вашем db_instance.py)
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            timeout=10,
            command_timeout=10
        )
        
        logger.info("✅ Пул создан")
        
        # Пробуем выполнить запрос через пул
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info(f"✅ Запрос выполнен: {result}")
        
        await pool.close()
        logger.info("✅ Пул закрыт")
        
        return {
            "status": "ok",
            "pool": "created and tested",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания пула: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск тестового сервера на порту {port}")
    
    # Показываем информацию при старте
    logger.info(f"📌 Python версия: {sys.version}")
    logger.info(f"📌 FastAPI доступен по адресу: http://0.0.0.0:{port}")
    logger.info(f"📌 Health check: http://0.0.0.0:{port}/health")
    logger.info(f"📌 Тест БД: http://0.0.0.0:{port}/test-db")
    logger.info(f"📌 Тест пула: http://0.0.0.0:{port}/test-pool")
    logger.info(f"📌 Переменные окружения: http://0.0.0.0:{port}/env")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
