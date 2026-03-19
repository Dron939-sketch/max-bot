#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИНИМАЛЬНАЯ ВЕРСИЯ ДЛЯ ТЕСТА PostgreSQL и DeepSeek
БЕЗ бота MAX, БЕЗ обработчиков, ТОЛЬКО диагностика
"""

import sys
import asyncio
import logging
import threading
import time
from fastapi import FastAPI
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== ИМПОРТЫ ДЛЯ ТЕСТА =====
from db_instance import db, init_db, close_db
from services import call_deepseek

# ===== СОЗДАЁМ FASTAPI =====
api_app = FastAPI(title="Тестовая версия")

@api_app.get("/")
async def root():
    return {"status": "ok", "message": "Тестовая версия"}

@api_app.get("/health")
async def health():
    return {"status": "ok"}

@api_app.get("/test/db")
async def test_db():
    """Тест подключения к БД"""
    try:
        await init_db()
        return {"status": "ok", "message": "База данных подключена"}
    except Exception as e:
        return {"status": "error", "message": str(e), "type": str(type(e))}

@api_app.get("/test/deepseek")
async def test_deepseek():
    """Тест DeepSeek API"""
    try:
        result = await call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
        if result:
            return {"status": "ok", "response": result}
        else:
            return {"status": "error", "message": "Пустой ответ"}
    except Exception as e:
        return {"status": "error", "message": str(e), "type": str(type(e))}

# ===== ФУНКЦИЯ ЗАПУСКА FASTAPI =====
def run_fastapi():
    """Запуск FastAPI в отдельном потоке"""
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск FastAPI на порту {port}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    config = uvicorn.Config(api_app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())

# ===== ФУНКЦИЯ ТЕСТА БД =====
def test_database_connection():
    """Тест подключения к БД в отдельном потоке"""
    logger.info("🔄 Тестируем подключение к PostgreSQL...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(init_db())
        logger.info("✅ PostgreSQL ПОДКЛЮЧЕН!")
        
        # Проверяем, что можем выполнить запрос
        async def test_query():
            async with db.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result
        
        result = loop.run_until_complete(test_query())
        logger.info(f"✅ Тестовый запрос выполнен: {result}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка PostgreSQL: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
    finally:
        loop.close()

# ===== ФУНКЦИЯ ТЕСТА DEEPSEEK =====
def test_deepseek_api():
    """Тест DeepSeek API в отдельном потоке"""
    logger.info("🔄 Тестируем DeepSeek API...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
        )
        if result:
            logger.info(f"✅ DeepSeek API РАБОТАЕТ! Ответ: {result}")
        else:
            logger.error("❌ DeepSeek API вернул пустой ответ")
    except Exception as e:
        logger.error(f"❌ Ошибка DeepSeek: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
    finally:
        loop.close()

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
def main():
    print("\n" + "="*60)
    print("🔬 МИНИМАЛЬНАЯ ТЕСТОВАЯ ВЕРСИЯ")
    print("="*60)
    
    # Запускаем FastAPI в отдельном потоке
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    logger.info("✅ FastAPI запущен")
    
    # Даём время на инициализацию
    time.sleep(2)
    
    # Тестируем PostgreSQL
    test_database_connection()
    
    # Тестируем DeepSeek
    test_deepseek_api()
    
    print("\n" + "="*60)
    print("✅ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("📊 Проверьте логи выше")
    print("🌐 FastAPI доступен по адресу: http://localhost:10000")
    print("📝 Эндпоинты:")
    print("  • /test/db - тест БД")
    print("  • /test/deepseek - тест DeepSeek")
    print("  • /health - health check")
    print("="*60)
    
    # Держим программу работающей
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 Завершение работы")

if __name__ == "__main__":
    import os  # Добавляем импорт os
    main()
