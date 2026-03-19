#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МИНИМАЛЬНАЯ ВЕРСИЯ ДЛЯ ТЕСТА
Только FastAPI + health check
"""

import sys
import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== МИНИМАЛЬНЫЙ FASTAPI ==========
app = FastAPI(title="Тест")

@app.get("/")
async def root():
    return {"status": "ok", "message": "API работает"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test-db")
async def test_db():
    """Тест подключения к БД"""
    try:
        from db_instance import db, init_db
        await init_db()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
