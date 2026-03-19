#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ ДЛЯ PYTHON 3.14 - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ
"""

import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ========== КРИТИЧЕСКИЕ ПАТЧИ ДЛЯ PYTHON 3.14 ==========
if sys.version_info >= (3, 14):
    try:
        # Сначала применяем все патчи
        print("🔧 Применение глобальных патчей для Python 3.14...")
        
        # ===== ПАТЧИ ДЛЯ ANYIO =====
        import anyio
        from anyio._backends._asyncio import _task_states, CapacityLimiter, CancelScope
        from anyio import to_thread
        
        # Сохраняем оригинальные функции
        original_getitem = _task_states.__getitem__
        original_acquire = CapacityLimiter.acquire
        original_acquire_on_behalf = CapacityLimiter.acquire_on_behalf_of
        original_cancel_scope_enter = CancelScope.__enter__
        original_run_sync = to_thread.run_sync
        
        # 1. Патч для _task_states.__getitem__
        def patched_getitem(self, key):
            if key is None:
                return {}
            try:
                return original_getitem(self, key)
            except (TypeError, KeyError):
                return {}
        _task_states.__getitem__ = patched_getitem
        
        # 2. Патч для CapacityLimiter.acquire
        async def patched_acquire(self):
            try:
                return await original_acquire(self)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return None
                raise
        CapacityLimiter.acquire = patched_acquire
        
        # 3. Патч для CapacityLimiter.acquire_on_behalf_of
        async def patched_acquire_on_behalf(self, task):
            if task is None:
                return None
            try:
                return await original_acquire_on_behalf(self, task)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return None
                raise
        CapacityLimiter.acquire_on_behalf_of = patched_acquire_on_behalf
        
        # 4. Патч для CancelScope.__enter__
        def patched_cancel_scope_enter(self):
            try:
                return original_cancel_scope_enter(self)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return self
                raise
        CancelScope.__enter__ = patched_cancel_scope_enter
        
        # 5. Патч для to_thread.run_sync
        async def patched_run_sync(func, *args, cancellable=False, limiter=None):
            try:
                return await original_run_sync(func, *args, cancellable=cancellable, limiter=limiter)
            except TypeError as e:
                if 'weak reference' in str(e):
                    return await original_run_sync(func, *args, cancellable=cancellable, limiter=None)
                raise
        to_thread.run_sync = patched_run_sync
        
        print("✅ Патчи anyio применены")
        
        # ===== ПАТЧИ ДЛЯ AIOHTTP =====
        import aiohttp
        from aiohttp.helpers import TimerContext
        from aiohttp.client import ClientSession
        
        original_timer_enter = TimerContext.__enter__
        
        def patched_timer_enter(self):
            try:
                return original_timer_enter(self)
            except RuntimeError as e:
                if "Timeout context manager should be used inside a task" in str(e):
                    return self
                raise
        TimerContext.__enter__ = patched_timer_enter
        
        original_session_init = ClientSession.__init__
        
        def patched_session_init(self, *args, **kwargs):
            if 'timeout' not in kwargs:
                kwargs['timeout'] = aiohttp.ClientTimeout(
                    total=None,
                    connect=None,
                    sock_read=None,
                    sock_connect=None
                )
            return original_session_init(self, *args, **kwargs)
        ClientSession.__init__ = patched_session_init
        
        print("✅ Патчи aiohttp применены")
        
        # ===== ПАТЧИ ДЛЯ ASYNCPG =====
        import asyncpg
        from asyncpg import connection
        
        original_connection_init = connection.Connection.__init__
        
        def patched_connection_init(self, *args, **kwargs):
            if 'loop' not in kwargs:
                try:
                    kwargs['loop'] = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    kwargs['loop'] = loop
            return original_connection_init(self, *args, **kwargs)
        connection.Connection.__init__ = patched_connection_init
        
        print("✅ Патчи asyncpg применены")
        print("🔥 ВСЕ ПАТЧИ УСПЕШНО ПРИМЕНЕНЫ")
        
    except Exception as e:
        print(f"⚠️ Ошибка при применении патчей: {e}")
        import traceback
        traceback.print_exc()
# =========================================================

import os
import json
import logging
import random
import re
import time
import threading
import fcntl
import socket
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime, timedelta

# ========== ИСПРАВЛЕНИЕ ПРОБЛЕМ ASYNCIO ==========
import nest_asyncio
nest_asyncio.apply()

import sniffio
def _fixed_current_async_library():
    return "asyncio"
sniffio.current_async_library = _fixed_current_async_library

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# =================================================

# ========== ИМПОРТЫ ДЛЯ FASTAPI ==========
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, HTMLResponse
import uvicorn
# =========================================

# ========== ИМПОРТЫ ДЛЯ БАЗЫ ДАННЫХ ==========
from db_instance import db, init_db, close_db, save_user_to_db, save_test_result_to_db
from db_instance import ensure_db_connection, execute_with_retry
import asyncpg
# =============================================

# ========== ЗАЩИТА ОТ ДВОЙНОГО ЗАПУСКА ==========
PID_FILE = '/tmp/max-bot.pid'
LOCK_FILE = '/tmp/max-bot.lock'

def check_single_instance():
    is_render = os.environ.get('RENDER') is not None
    
    try:
        lock_fp = open(LOCK_FILE, 'w')
        try:
            fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            check_single_instance.lock_fp = lock_fp
        except (IOError, OSError):
            if is_render:
                print("⚠️ Не удалось получить блокировку, но продолжаем (Render)")
            else:
                print("❌ Не удалось получить блокировку - бот уже запущен")
                return False
        
        if not is_render and os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    old_pid = f.read().strip()
                if old_pid:
                    try:
                        os.kill(int(old_pid), 0)
                        print(f"❌ Процесс с PID {old_pid} уже запущен")
                        return False
                    except OSError:
                        pass
            except Exception as e:
                print(f"⚠️ Ошибка при чтении PID файла: {e}")
        
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        print(f"✅ Бот запущен с PID {os.getpid()}")
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        if is_render:
            return True
        return False

if not check_single_instance():
    print("❌ Бот уже запущен. Завершаем работу.")
    sys.exit(1)

# Импорты из maxibot
from maxibot import MaxiBot, types
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# Импорты из наших модулей
from config import (
    MAX_TOKEN, ADMIN_IDS, COMMUNICATION_MODES,
    DEEPSEEK_API_KEY, DEEPGRAM_API_KEY, YANDEX_API_KEY, OPENWEATHER_API_KEY
)
from models import (
    UserContext, ReminderManager, DestinationManager, Statistics,
    ConfinementModel9, level, DelayedTaskManager
)
from services import *
from reality_check import *
from modes import *
from morning_messages import MorningMessageManager
from profiles import *
from questions import *
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring
from weekend_planner import WeekendPlanner, get_weekend_ideas_keyboard
from keyboards import *
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from state import *
from scheduler import TaskScheduler
from question_analyzer import QuestionAnalyzer, create_analyzer_from_user_data

# Импорты из formatters.py
from formatters import (
    bold, italic, emoji_text, clean_text_for_safe_display,
    format_profile_text, format_psychologist_text, strip_html, split_long_message
)

# Импорты из обработчиков
from handlers.context import handle_context_message, start_context, show_context_complete
from handlers.reality import process_life_context, process_goal_context
from handlers.callback import callback_handler
from handlers.modes import show_mode_selection, show_mode_selected, show_main_menu_after_mode
from handlers.start import cmd_start as start_cmd, show_why_details
from handlers.profile import (
    show_profile, show_ai_profile, show_psychologist_thought, show_final_profile,
    set_morning_manager
)
from handlers.stages import *
from handlers.help import show_help, show_tale, show_benefits
from handlers.goals import *
from handlers.questions import *
from handlers.admin import *
from handlers.voice import handle_voice_message, send_voice_to_max

# Дополнительные импорты
from profiles import VECTORS
from services import generate_psychologist_thought
from weekend_planner import WeekendPlanner

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# ЭКЗЕМПЛЯР БОТА
# ============================================

if not MAX_TOKEN:
    logger.error("❌ MAX_TOKEN не найден в переменных окружения!")
    MAX_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

bot = MaxiBot(MAX_TOKEN)
logger.info("✅ Экземпляр бота MAX создан")

# ============================================
# ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРОВ
# ============================================

reminder_manager = ReminderManager()
destination_manager = DestinationManager()
stats = Statistics()
delayed_task_manager = DelayedTaskManager()
morning_manager = MorningMessageManager()
hypno = HypnoOrchestrator()
tales = TherapeuticTales()
anchoring = Anchoring()
weekend_planner = WeekendPlanner()
scheduler = TaskScheduler()

set_morning_manager(morning_manager)
morning_manager.set_bot(bot)
morning_manager.set_contexts(user_contexts, user_data)

# ============================================
# FASTAPI ДЛЯ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

api_app = FastAPI(title="Фреди - Мини-приложение")

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Путь к папке с мини-приложением
MINIAPP_PATH = os.path.join(os.path.dirname(__file__), 'miniapp')
os.makedirs(MINIAPP_PATH, exist_ok=True)

# ============================================
# БЕЗОПАСНЫЙ ОБРАБОТЧИК СТАТИЧЕСКИХ ФАЙЛОВ
# ============================================
import mimetypes

@api_app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Безопасно отдаёт статические файлы без anyio"""
    try:
        # Защита от directory traversal
        if '..' in file_path or file_path.startswith('/'):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid file path"}
            )
        
        full_path = os.path.join(MINIAPP_PATH, file_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'rb') as f:
                content = f.read()
            
            media_type, _ = mimetypes.guess_type(file_path)
            if not media_type:
                media_type = 'application/octet-stream'
            
            return Response(content=content, media_type=media_type)
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "File not found"}
            )
    except Exception as e:
        logger.error(f"❌ Ошибка при обслуживании {file_path}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

# ============================================
# КОРНЕВОЙ МАРШРУТ - ВСЕГДА JSON
# ============================================

@api_app.get("/")
async def root():
    """Корневой маршрут - всегда возвращает JSON"""
    return JSONResponse({
        "name": "MAX Bot",
        "version": "9.8",
        "status": "online",
        "api": "работает",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "api": "/api/*",
            "static": "/static/*"
        }
    })

@api_app.get("/health")
async def health_check():
    return {"status": "ok"}

# ============================================
# API ЭНДПОИНТЫ
# ============================================

@api_app.post("/api/save-profile")
async def save_profile(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        profile = data.get('profile')
        
        if not user_id or not profile:
            raise HTTPException(status_code=400, detail="user_id and profile required")
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['ai_generated_profile'] = profile
        user_data[user_id]['profile_data'] = profile.get('profile_data', {})
        
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"❌ Error in save_profile: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@api_app.post("/api/save-test-progress")
async def save_test_progress(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        stage = data.get('stage')
        answers = data.get('answers', [])
        
        if not user_id or stage is None:
            raise HTTPException(status_code=400, detail="user_id and stage required")
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'all_answers' not in user_data[user_id]:
            user_data[user_id]['all_answers'] = []
        
        stage_key = f'stage{stage}_answers'
        if stage_key not in user_data[user_id]:
            user_data[user_id][stage_key] = []
        
        for answer in answers:
            user_data[user_id]['all_answers'].append({
                'stage': stage,
                'question_index': answer.get('question'),
                'answer': answer.get('answer'),
                'option': answer.get('option'),
                'timestamp': datetime.now().isoformat()
            })
            user_data[user_id][stage_key].append(answer)
        
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"❌ Error in save_test_progress: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@api_app.post("/api/save-mode")
async def save_mode(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        mode = data.get('mode')
        
        if not user_id or not mode:
            raise HTTPException(status_code=400, detail="user_id and mode required")
        
        if user_id in user_contexts:
            user_contexts[user_id].communication_mode = mode
        
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['communication_mode'] = mode
        
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"❌ Error in save_mode: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@api_app.get("/api/get-profile")
async def get_profile_miniapp(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        return JSONResponse({
            "ai_generated_profile": data.get("ai_generated_profile"),
            "profile_data": data.get("profile_data"),
            "perception_type": data.get("perception_type"),
            "thinking_level": data.get("thinking_level"),
            "behavioral_levels": data.get("behavioral_levels"),
            "deep_patterns": data.get("deep_patterns")
        })
    except Exception as e:
        logger.error(f"❌ Error in get_profile_miniapp: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_app.get("/api/get-test-progress")
async def get_test_progress(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        return JSONResponse({
            "stage1_complete": 'perception_type' in data,
            "stage2_complete": 'thinking_level' in data,
            "stage3_complete": 'behavioral_levels' in data and len(data.get('behavioral_levels', {})) > 0,
            "stage4_complete": 'dilts_counts' in data,
            "stage5_complete": 'deep_patterns' in data,
            "answers_count": len(data.get('all_answers', [])),
            "current_stage": data.get('current_stage', 1)
        })
    except Exception as e:
        logger.error(f"❌ Error in get_test_progress: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_app.get("/api/user-data")
async def get_user_data_api(user_id: int):
    try:
        user_id = int(user_id)
        context = user_contexts.get(user_id)
        
        return {
            "user_id": user_id,
            "user_name": context.name if context else user_names.get(user_id, "друг"),
            "has_profile": bool(user_data.get(user_id, {}).get("ai_generated_profile")) or 
                          bool(user_data.get(user_id, {}).get("profile_data"))
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_app.get("/api/thought")
async def get_thought(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        thought = data.get("psychologist_thought")
        if not thought:
            thought = await generate_psychologist_thought(user_id, data)
            if thought:
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]["psychologist_thought"] = thought
                asyncio.create_task(execute_with_retry(
                    save_user_to_db, user_id, user_data, user_contexts, user_routes,
                    max_retries=3
                ))
            else:
                thought = "Мысли психолога еще не сгенерированы."
        
        return {"thought": thought}
    except Exception as e:
        logger.error(f"API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_app.get("/api/ideas")
async def get_ideas(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        context = user_contexts.get(user_id)
        user_name = context.name if context else user_names.get(user_id, "друг")
        
        cached_ideas = await db.get_cached_weekend_ideas(user_id)
        if cached_ideas:
            return {"ideas": [{"title": "Идеи на выходные", "description": cached_ideas}]}
        
        scores = {}
        for k in VECTORS:
            levels = data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        profile_data = data.get("profile_data", {})
        
        ideas_text = await weekend_planner.get_weekend_ideas(
            user_id=user_id,
            user_name=user_name,
            scores=scores,
            profile_data=profile_data,
            context=context
        )
        
        if scores:
            main_vector = max(scores.items(), key=lambda x: x[1])[0]
            main_level = int(scores.get(main_vector, 3))
            asyncio.create_task(db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level))
        
        ideas = []
        paragraphs = ideas_text.split('\n\n')
        for p in paragraphs:
            if p.strip() and not p.startswith('#'):
                ideas.append({
                    "title": p[:50] + "..." if len(p) > 50 else p,
                    "description": p
                })
        
        return {"ideas": ideas[:5]}
    except Exception as e:
        logger.error(f"API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================
# ФУНКЦИИ БАЗЫ ДАННЫХ
# ============================================

async def init_database():
    try:
        await init_db()
        logger.info("✅ Подключение к PostgreSQL установлено")
        await ensure_db_connection()
        await load_all_users_from_db()
        setup_auto_save(interval_seconds=300)
        asyncio.create_task(periodic_save_to_db())
        asyncio.create_task(periodic_cleanup_db())
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

async def load_all_users_from_db():
    global user_data, user_names, user_contexts, user_routes
    
    logger.info("🔄 Загрузка данных из PostgreSQL...")
    
    try:
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, first_name, username FROM fredi_users")
            for row in rows:
                user_names[row['user_id']] = row['first_name'] or row['username'] or f"user_{row['user_id']}"
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT * FROM fredi_user_contexts")
            for row in rows:
                user_id = row['user_id']
                context = UserContext(user_id)
                context.name = row.get('name')
                context.age = row.get('age')
                context.gender = row.get('gender')
                context.city = row.get('city')
                context.birth_date = row.get('birth_date')
                context.timezone = row.get('timezone', 'Europe/Moscow')
                context.timezone_offset = row.get('timezone_offset', 3)
                context.communication_mode = row.get('communication_mode', 'coach')
                context.last_context_update = row.get('last_context_update')
                if row.get('weather_cache'):
                    context.weather_cache = json.loads(row['weather_cache'])
                context.weather_cache_time = row.get('weather_cache_time')
                context.family_status = row.get('family_status')
                context.has_children = row.get('has_children', False)
                context.children_ages = row.get('children_ages')
                context.work_schedule = row.get('work_schedule')
                context.job_title = row.get('job_title')
                context.commute_time = row.get('commute_time')
                context.housing_type = row.get('housing_type')
                context.has_private_space = row.get('has_private_space', False)
                context.has_car = row.get('has_car', False)
                context.support_people = row.get('support_people')
                context.resistance_people = row.get('resistance_people')
                context.energy_level = row.get('energy_level')
                context.life_context_complete = row.get('life_context_complete', False)
                context.awaiting_context = row.get('awaiting_context')
                user_contexts[user_id] = context
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, data FROM fredi_user_data")
            for row in rows:
                data = row['data']
                if isinstance(data, str):
                    data = json.loads(data)
                user_data[row['user_id']] = data
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT user_id, route_data, current_step, progress 
                FROM fredi_user_routes 
                WHERE is_active = TRUE
            """)
            for row in rows:
                route_data = row['route_data']
                if isinstance(route_data, str):
                    route_data = json.loads(route_data)
                progress = row['progress']
                if isinstance(progress, str):
                    progress = json.loads(progress)
                user_routes[row['user_id']] = {
                    'route_data': route_data,
                    'current_step': row['current_step'],
                    'progress': progress
                }
        
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, context_data FROM fredi_context_objects")
            for row in rows:
                user_id = row['user_id']
                if user_id not in user_contexts:
                    try:
                        import pickle
                        context = pickle.loads(row['context_data'])
                        user_contexts[user_id] = context
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось загрузить pickled контекст для {user_id}: {e}")
        
        logger.info(f"✅ Загружено: {len(user_data)} пользователей, "
                   f"{len(user_contexts)} контекстов, "
                   f"{len(user_routes)} маршрутов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных из БД: {e}")
        import traceback
        traceback.print_exc()

async def periodic_save_to_db():
    while True:
        await asyncio.sleep(300)
        logger.info("🔄 Периодическое сохранение данных в БД...")
        saved_count = 0
        for user_id in list(user_data.keys()):
            try:
                result = await execute_with_retry(
                    save_user_to_db, user_id, user_data, user_contexts, user_routes,
                    max_retries=3
                )
                if result:
                    saved_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения {user_id}: {e}")
        logger.info(f"✅ Сохранено {saved_count} пользователей")

async def periodic_cleanup_db():
    while True:
        await asyncio.sleep(86400)
        try:
            await db.cleanup_old_data(days=30)
            logger.info("🧹 Очистка старых данных выполнена")
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке данных: {e}")

# ============================================
# HEALTH CHECK СЕРВЕР
# ============================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_HEAD(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_health_server():
    ports = [10001, 10002, 10003, 10004, 10005]
    for port in ports:
        try:
            server = HTTPServer(('0.0.0.0', port), HealthHandler)
            logger.info(f"✅ Health check server started on port {port}")
            server.serve_forever()
            return
        except OSError:
            logger.warning(f"⚠️ Port {port} is busy, trying next...")
            continue
        except Exception as e:
            logger.error(f"❌ Error on port {port}: {e}")
            continue
    logger.error("❌ Could not start health check server on any port")

# ============================================
# ФУНКЦИИ ЗАПУСКА
# ============================================

def run_fastapi():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск FastAPI на порту {port}")
    
    config = uvicorn.Config(
        api_app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Создаём и устанавливаем цикл событий для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())

def run_bot_polling():
    """Запускает polling бота в отдельном потоке"""
    try:
        bot.polling()
    except Exception as e:
        logger.error(f"❌ Ошибка в polling: {e}")

async def check_api_on_startup():
    logger.info("🔍 Проверка API при запуске...")
    
    results = {
        "deepseek": False,
        "deepgram": False,
        "yandex": False,
        "openweather": False
    }
    
    if DEEPSEEK_API_KEY:
        try:
            test_response = await call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
            results["deepseek"] = test_response is not None
            logger.info(f"✅ DeepSeek API: {'работает' if results['deepseek'] else 'ошибка'}")
        except Exception as e:
            logger.error(f"❌ DeepSeek API ошибка: {e}")
    
    if DEEPGRAM_API_KEY:
        results["deepgram"] = True
        logger.info("✅ Deepgram API ключ найден")
    
    if YANDEX_API_KEY:
        results["yandex"] = True
        logger.info("✅ Yandex TTS ключ найден")
    
    if OPENWEATHER_API_KEY:
        results["openweather"] = True
        logger.info("✅ OpenWeather API ключ найден")
    
    return results

def run_async_tasks():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    
    try:
        loop.run_until_complete(check_api_on_startup())
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке API: {e}")

def cleanup_resources():
    is_render = os.environ.get('RENDER') is not None
    try:
        if not is_render and os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info(f"🗑️ Удален PID файл {PID_FILE}")
        
        if hasattr(check_single_instance, 'lock_fp'):
            try:
                check_single_instance.lock_fp.close()
                logger.info("🔒 Закрыт файл блокировки")
            except:
                pass
        
        if not is_render and os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.info(f"🗑️ Удален файл блокировки {LOCK_FILE}")
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке ресурсов: {e}")

async def shutdown_handler():
    logger.info("🛑 Завершение работы, сохраняем данные в БД...")
    
    try:
        from state import save_all_users_to_db
        saved_count = await execute_with_retry(save_all_users_to_db, db, max_retries=3)
        logger.info(f"✅ Сохранено {saved_count} пользователей")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
    
    try:
        await close_db()
        logger.info("✅ База данных закрыта")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии БД: {e}")

# ============================================
# ОБРАБОТЧИКИ БОТА
# ============================================

@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    from handlers.start import cmd_start
    cmd_start(message)

@bot.message_handler(commands=['menu'])
def cmd_menu(message: types.Message):
    from handlers.start import cmd_menu
    cmd_menu(message)

@bot.message_handler(commands=['mode'])
def cmd_mode(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    show_mode_selection(message)

@bot.message_handler(commands=['stats'])
def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    safe_send_message(message, stats.get_stats_text())

@bot.message_handler(commands=['apistatus'])
def cmd_apistatus(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    text = f"📊 Статус API:\n\n"
    text += f"• DeepSeek: {'✅' if DEEPSEEK_API_KEY else '❌'}\n"
    text += f"• Deepgram: {'✅' if DEEPGRAM_API_KEY else '❌'}\n"
    text += f"• Yandex TTS: {'✅' if YANDEX_API_KEY else '❌'}\n"
    text += f"• OpenWeather: {'✅' if OPENWEATHER_API_KEY else '❌'}\n\n"
    safe_send_message(message, text)

@bot.message_handler(commands=['context'])
def cmd_context(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    context.city = None
    context.gender = None
    context.age = None
    context.weather_cache = {}
    
    safe_send_message(message, "🔄 Давайте обновим ваш контекст")
    start_context(message)

@bot.message_handler(commands=['weekend'])
def cmd_weekend(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    
    if not data.get("profile_data") and not data.get("ai_generated_profile"):
        safe_send_message(
            message,
            "❓ Сначала нужно пройти тест, чтобы я понимал твой профиль. Используй /start",
            delete_previous=True
        )
        return
    
    def run_async():
        asyncio.run(show_weekend_ideas(message, user_id))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['dbstats'])
def cmd_dbstats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    from state import get_stats
    stats_data = get_stats()
    
    text = "📊 **Статистика БД в памяти:**\n\n"
    text += f"👤 Пользователей с данными: {stats_data['users_in_data']}\n"
    text += f"📍 Контекстов: {stats_data['users_in_contexts']}\n"
    text += f"🗺 Маршрутов: {stats_data['users_in_routes']}\n"
    text += f"🔄 В состояниях: {stats_data['users_in_states']}\n"
    text += f"📛 С именами: {stats_data['users_with_names']}\n"
    text += f"✨ Всего уникальных: {stats_data['total_unique']}"
    
    safe_send_message(message, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: types.CallbackQuery):
    callback_handler(call)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.collecting_life_context)
def handle_life_context_wrapper(message: types.Message):
    process_life_context(message)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.collecting_goal_context)
def handle_goal_context_wrapper(message: types.Message):
    process_goal_context(message)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_context)
def handle_context_message_wrapper(message: types.Message):
    handled = handle_context_message(message)
    if not handled:
        safe_send_message(
            message,
            "Пожалуйста, ответьте на вопрос или используйте кнопки",
            delete_previous=True,
            keep_last=1
        )

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_question)
def handle_question_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    def run_sync():
        from handlers.questions import process_text_question_sync
        process_text_question_sync(message, user_id, text)
    
    threading.Thread(target=run_sync, daemon=True).start()

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_custom_goal)
def handle_custom_goal_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    def run_async():
        asyncio.run(process_custom_goal_async(message, user_id, text))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.pretest_question)
def handle_pretest_question(message: types.Message):
    user_id = message.from_user.id
    
    safe_send_message(
        message,
        "Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. "
        "Пройдите тест — это займёт 15 минут.",
        delete_previous=True
    )
    clear_state(user_id)

@bot.message_handler(content_types=['voice'])
def handle_voice_wrapper(message: types.Message):
    def run_async():
        asyncio.run(handle_voice_message(message))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(func=lambda message: True)
def handle_unknown_message(message: types.Message):
    user_id = message.from_user.id
    state = get_state(user_id)
    
    if state == TestStates.awaiting_context:
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results"),
        InlineKeyboardButton("🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")
    )
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(
        message,
        "Используйте кнопки для навигации:",
        reply_markup=keyboard,
        keep_last=1
    )

async def show_weekend_ideas(message: types.Message, user_id: int):
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = user_names.get(user_id, "друг")
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    profile_data = data.get("profile_data", {})
    
    status_msg = await safe_send_message(
        message,
        "🎨 Генерирую идеи специально для тебя...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    try:
        ideas_text = await weekend_planner.get_weekend_ideas(
            user_id=user_id,
            user_name=user_name,
            scores=scores,
            profile_data=profile_data,
            context=context
        )
        
        await safe_delete_message(message.chat.id, status_msg.message_id)
        
        keyboard = get_weekend_ideas_keyboard()
        
        await safe_send_message(
            message,
            ideas_text,
            reply_markup=keyboard,
            delete_previous=True
        )
    except Exception as e:
        logger.error(f"Ошибка генерации идей: {e}")
        await safe_delete_message(message.chat.id, status_msg.message_id)
        await safe_send_message(
            message,
            "😔 Что-то пошло не так. Попробуй позже.",
            delete_previous=True
        )

async def process_custom_goal_async(message: types.Message, user_id: int, text: str):
    try:
        from handlers.goals import process_custom_goal_async as process_goal
        await process_goal(message, user_id, text)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке пользовательской цели: {e}")
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке цели. Пожалуйста, попробуйте еще раз.",
            delete_previous=True
        )

# ============================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================

def main():
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v9.8 (MAX)")
    print("="*80)
    print(f"👤 Ваш ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print(f"🎙 Распознавание: {'✅' if DEEPGRAM_API_KEY else '❌'}")
    print(f"🎙 Синтез речи: {'✅' if YANDEX_API_KEY else '❌'}")
    print(f"🌍 Погода: {'✅' if OPENWEATHER_API_KEY else '❌'}")
    print(f"🎭 Режимы: 🔮 КОУЧ | 🧠 ПСИХОЛОГ | ⚡ ТРЕНЕР")
    print(f"📊 5 этапов тестирования: ✅")
    print(f"🎯 Динамический подбор целей: ✅")
    print(f"🔍 Проверка реальности: ✅")
    print(f"🎤 Голосовые сообщения: {'✅' if DEEPGRAM_API_KEY and YANDEX_API_KEY else '❌'}")
    print(f"🗓 Планировщик задач: ✅")
    print(f"🎨 Идеи на выходные: ✅")
    print(f"🔬 Глубинный анализ вопросов: ✅")
    print(f"📱 Мини-приложение: ✅ (FastAPI + JSON API)")
    print(f"🗄️ Постоянное хранение: ✅ (PostgreSQL)")
    print("="*80 + "\n")
    
    logger.info("🚀 Бот для MAX запущен!")
    
    # Создаём новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Инициализируем БД
    try:
        loop.run_until_complete(init_database())
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        logger.warning("⚠️ Продолжаем работу БЕЗ PostgreSQL (только память)")
    
    # Запускаем планировщик
    scheduler.start()
    
    # Запускаем асинхронные задачи в отдельном потоке
    async_thread = threading.Thread(target=run_async_tasks, daemon=True)
    async_thread.start()
    
    # Запускаем health check сервер
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Запускаем FastAPI в отдельном потоке
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    logger.info("✅ FastAPI сервер запущен")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    logger.info("✅ Бот запущен")
    
    # Добавляем обработчик сигналов
    try:
        import signal
        
        def signal_handler():
            asyncio.create_task(shutdown_handler())
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось установить обработчик сигналов: {e}")
    
    # Держим главный поток живым
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
        loop.run_until_complete(shutdown_handler())
    finally:
        cleanup_resources()

if __name__ == "__main__":
    main()
