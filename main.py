#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ ДЛЯ PYTHON 3.11 - С ЕДИНЫМ ЦИКЛОМ ДЛЯ БД И ДИАГНОСТИКОЙ
"""

import os
import sys
import json
import logging
import random
import re
import time
import threading
import fcntl
import socket
import asyncio
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# ========== ИМПОРТЫ ДЛЯ FASTAPI ==========
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import requests
# =========================================

# ========== ИМПОРТЫ ДЛЯ БАЗЫ ДАННЫХ ==========
from db_instance import db, init_db, close_db, ensure_db_connection, execute_with_retry
from db_sync import sync_db
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
from handlers.help import show_help, show_benefits
from handlers.tales import show_tale
from handlers.goals import *
from handlers.questions import *
from handlers.admin import *
from handlers.voice import handle_voice_message, send_voice_to_max

from voice_handler import register_voice_handler

# Дополнительные импорты для API эндпоинтов
from profiles import VECTORS
from services import generate_psychologist_thought
from weekend_planner import WeekendPlanner

# ============================================
# ЭКЗЕМПЛЯР БОТА
# ============================================

if not MAX_TOKEN:
    logger.error("❌ MAX_TOKEN не найден в переменных окружения!")
    MAX_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

bot = MaxiBot(MAX_TOKEN)
logger.info("✅ Экземпляр бота MAX создан")

from voice_handler import register_voice_handler
voice_handler = register_voice_handler(bot)
logger.info("✅ Простой обработчик голоса зарегистрирован")

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
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================

async def init_database():
    """Инициализация базы данных"""
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
        raise

async def load_all_users_from_db():
    """Загружает всех пользователей из БД в словари памяти"""
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
                        logger.debug(f"📦 Загружен pickled контекст для {user_id}")
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
    """Периодически сохраняет всех пользователей в БД"""
    while True:
        await asyncio.sleep(300)
        logger.info("🔄 Периодическое сохранение данных в БД...")
        saved_count = 0
        for user_id in list(user_data.keys()):
            try:
                if sync_db.save_user_to_db(user_id):
                    saved_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения {user_id}: {e}")
        logger.info(f"✅ Сохранено {saved_count} пользователей")

async def periodic_cleanup_db():
    """Периодическая очистка старых данных"""
    while True:
        await asyncio.sleep(86400)
        try:
            await db.cleanup_old_data(days=30)
            logger.info("🧹 Очистка старых данных выполнена")
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке данных: {e}")

# ============================================
# FASTAPI ДЛЯ МИНИ-ПРИЛОЖЕНИЯ (ИСПРАВЛЕННЫЙ)
# ============================================

import mimetypes

# Регистрируем MIME типы ДО монтирования статики
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('application/manifest+json', '.json')
mimetypes.add_type('image/x-icon', '.ico')
mimetypes.add_type('audio/ogg', '.ogg')
mimetypes.add_type('audio/webm', '.webm')

api_app = FastAPI(title="Фреди - Мини-приложение")

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fredi-app.onrender.com",   # статический сайт
        "https://max-bot-1-ywpz.onrender.com",   # бэкенд
        "http://localhost:10000",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

MINIAPP_PATH = os.path.dirname(__file__)
os.makedirs(MINIAPP_PATH, exist_ok=True)


@api_app.get("/health")
async def health_check():
    """Health check для Render"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "static_files_available": os.path.exists(os.path.join(MINIAPP_PATH, "styles.css")),
        "index_available": os.path.exists(os.path.join(MINIAPP_PATH, "index.html")),
        "miniapp_path": MINIAPP_PATH,
        "files_count": len(os.listdir(MINIAPP_PATH)) if os.path.exists(MINIAPP_PATH) else 0
    }

# ============================================
# API ЭНДПОИНТЫ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

@api_app.post("/api/save-context")
async def save_context(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        context_data = data.get('context', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        if user_id not in user_contexts:
            user_contexts[user_id] = UserContext(user_id)
        
        context = user_contexts[user_id]
        
        if 'city' in context_data:
            context.city = context_data['city']
        if 'gender' in context_data:
            context.gender = context_data['gender']
        if 'age' in context_data:
            context.age = context_data['age']
        
        logger.info(f"📝 Контекст сохранен для пользователя {user_id}: {context_data}")
        
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"❌ Error in save_context: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

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
        
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": "Profile saved"
        })
    except Exception as e:
        logger.error(f"❌ Error in save_profile: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

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
        
        sync_db.save_user_to_db(user_id)
        
        stage_questions_count = {1: 4, 2: 6, 3: 24, 4: 12, 5: 8}
        total = stage_questions_count.get(stage, 4)
        stage_answers = [a for a in user_data[user_id].get('all_answers', []) 
                        if a.get('stage') == stage]
        stage_complete = len(stage_answers) >= total
        
        if stage_complete:
            if stage == 1 and 'perception_type' not in user_data[user_id]:
                user_data[user_id]['perception_type'] = 'visual'
            elif stage == 2 and 'thinking_level' not in user_data[user_id]:
                user_data[user_id]['thinking_level'] = 5
            elif stage == 3 and 'behavioral_levels' not in user_data[user_id]:
                user_data[user_id]['behavioral_levels'] = {
                    'extraversion': [3,4,3,4,3,4],
                    'neuroticism': [3,3,3,3,3,3],
                    'agreeableness': [4,4,4,4,4,4],
                    'conscientiousness': [4,4,4,4,4,4]
                }
            if stage < 5:
                user_data[user_id]['current_stage'] = stage + 1
            else:
                user_data[user_id]['current_stage'] = 5
        
        return JSONResponse({
            "success": True,
            "stageComplete": stage_complete
        })
    except Exception as e:
        logger.error(f"❌ Error in save_test_progress: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

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
        
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": f"Mode {mode} saved"
        })
    except Exception as e:
        logger.error(f"❌ Error in save_mode: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.post("/api/sync")
async def sync_data(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        sync_data = data.get('data', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'answers' in sync_data:
            if 'all_answers' not in user_data[user_id]:
                user_data[user_id]['all_answers'] = []
            user_data[user_id]['all_answers'].extend(sync_data['answers'])
        
        if 'profile' in sync_data:
            user_data[user_id]['ai_generated_profile'] = sync_data['profile']
        
        if 'mode' in sync_data and user_id in user_contexts:
            user_contexts[user_id].communication_mode = sync_data['mode']
        
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": "Data synchronized"
        })
    except Exception as e:
        logger.error(f"❌ Error in sync: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/get-profile")
async def get_profile_miniapp(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        profile = {
            "ai_generated_profile": data.get("ai_generated_profile"),
            "profile_data": data.get("profile_data"),
            "perception_type": data.get("perception_type"),
            "thinking_level": data.get("thinking_level"),
            "behavioral_levels": data.get("behavioral_levels"),
            "deep_patterns": data.get("deep_patterns")
        }
        return JSONResponse(profile)
    except Exception as e:
        logger.error(f"❌ Error in get_profile_miniapp: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@api_app.get("/api/get-test-progress")
async def get_test_progress(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        progress = {
            "stage1_complete": 'perception_type' in data,
            "stage2_complete": 'thinking_level' in data,
            "stage3_complete": 'behavioral_levels' in data and len(data.get('behavioral_levels', {})) > 0,
            "stage4_complete": 'dilts_counts' in data,
            "stage5_complete": 'deep_patterns' in data,
            "answers_count": len(data.get('all_answers', [])),
            "current_stage": data.get('current_stage', 1)
        }
        return JSONResponse(progress)
    except Exception as e:
        logger.error(f"❌ Error in get_test_progress: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ============================================
# ДОБАВЛЕННЫЕ ЭНДПОИНТЫ ДЛЯ ТЕСТА
# ============================================

@api_app.post("/api/save-test-results")
async def save_test_results(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        results = data.get('results', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['perception_type'] = results.get('perception_type')
        user_data[user_id]['thinking_level'] = results.get('thinking_level')
        user_data[user_id]['behavioral_levels'] = results.get('behavioral_levels')
        user_data[user_id]['dilts_counts'] = results.get('dilts_counts')
        user_data[user_id]['deep_patterns'] = results.get('deep_patterns')
        user_data[user_id]['profile_data'] = results.get('profile_data')
        user_data[user_id]['all_answers'] = results.get('all_answers')
        user_data[user_id]['test_completed'] = True
        user_data[user_id]['test_completed_at'] = datetime.now().isoformat()
        
        sync_db.save_user_to_db(user_id)
        
        def run_generation():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(generate_profile_interpretation_async(user_id))
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Ошибка в потоке генерации: {e}")
        
        threading.Thread(target=run_generation, daemon=True).start()
        
        logger.info(f"✅ Результаты теста для пользователя {user_id} сохранены")
        
        return JSONResponse({
            "success": True,
            "message": "Результаты сохранены, интерпретация формируется"
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/get-test-interpretation")
async def get_test_interpretation(user_id: int):
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        if user_info.get("ai_generated_profile"):
            return JSONResponse({
                "success": True,
                "interpretation": user_info["ai_generated_profile"],
                "ready": True
            })
        
        if user_info.get("profile_data") and user_info.get("test_completed"):
            return JSONResponse({
                "success": True,
                "interpretation": None,
                "ready": False,
                "message": "Интерпретация формируется..."
            })
        
        return JSONResponse({
            "success": False,
            "ready": False,
            "message": "Тест еще не завершен"
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения интерпретации: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/user-status")
async def get_user_status(user_id: int):
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        return JSONResponse({
            "success": True,
            "has_profile": bool(user_info.get('profile_data')),
            "has_interpretation": bool(user_info.get('ai_generated_profile')),
            "test_completed": user_info.get('test_completed', False),
            "interpretation_ready": bool(user_info.get('ai_generated_profile')),
            "profile_code": user_info.get('profile_data', {}).get('display_name')
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/check-db")
async def check_db():
    try:
        await ensure_db_connection()
        async with db.get_connection() as conn:
            users = await conn.fetchval("SELECT COUNT(*) FROM fredi_users")
            tests = await conn.fetchval("SELECT COUNT(*) FROM fredi_test_results")
            contexts = await conn.fetchval("SELECT COUNT(*) FROM fredi_user_contexts")
            return {
                "status": "ok",
                "users": users or 0,
                "tests": tests or 0,
                "contexts": contexts or 0,
                "message": "✅ База данных работает"
            }
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке БД: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "❌ База данных НЕ работает"
        }

@api_app.get("/api/logs/{user_id}")
async def get_user_logs(user_id: int):
    try:
        await ensure_db_connection()
        result = {}
        async with db.get_connection() as conn:
            events = await conn.fetch("""
                SELECT event_type, event_data, created_at 
                FROM fredi_events 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT 20
            """, user_id)
            if events:
                result['events'] = [
                    {
                        'type': e['event_type'],
                        'data': e['event_data'],
                        'time': e['created_at'].isoformat() if e['created_at'] else None
                    }
                    for e in events
                ]
            tests = await conn.fetch("""
                SELECT id, test_type, created_at 
                FROM fredi_test_results 
                WHERE user_id = $1 
                ORDER BY created_at DESC
            """, user_id)
            if tests:
                result['tests'] = [
                    {
                        'id': t['id'],
                        'type': t['test_type'],
                        'time': t['created_at'].isoformat() if t['created_at'] else None
                    }
                    for t in tests
                ]
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

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
        logger.error(f"API error in get_user_data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@api_app.get("/api/profile")
async def get_profile(user_id: int):
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        profile = data.get("ai_generated_profile")
        if not profile:
            scores = {}
            for k in VECTORS:
                levels = data.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            perception_type = data.get("perception_type", "не определен")
            thinking_level = data.get("thinking_level", 5)
            dilts_counts = data.get("dilts_counts", {})
            dominant_dilts = determine_dominant_dilts(dilts_counts)
            profile = get_human_readable_profile(
                scores,
                perception_type=perception_type,
                thinking_level=thinking_level,
                dominant_dilts=dominant_dilts
            )
        return {"profile": profile}
    except Exception as e:
        logger.error(f"API error in get_profile: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

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
                sync_db.save_user_to_db(user_id)
            else:
                thought = "Мысли психолога еще не сгенерированы."
        return {"thought": thought}
    except Exception as e:
        logger.error(f"API error in get_thought: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

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
            await db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level)
        
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
        logger.error(f"API error in get_ideas: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@api_app.get("/health")
async def health_check():
    return {"status": "ok"}

@api_app.get("/api/chat/history")
async def get_chat_history(user_id: int, limit: int = 50):
    try:
        user_id = int(user_id)
        return JSONResponse({
            "success": True,
            "history": []
        })
    except Exception as e:
        logger.error(f"❌ Error in get_chat_history: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "history": []}
        )

@api_app.post("/api/voice/process")
async def process_voice(request: Request):
    """Обработка голосового сообщения"""
    try:
        import time
        
        form = await request.form()
        user_id = form.get('user_id')
        voice_file = form.get('voice')
        
        if not user_id or not voice_file:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "user_id and voice file required"}
            )
        
        try:
            user_id = int(user_id)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "invalid user_id"}
            )
        
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp_path = tmp.name
        
        content = await voice_file.read()
        with open(tmp_path, 'wb') as f:
            f.write(content)
        
        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            os.unlink(tmp_path)
            return JSONResponse({
                "success": False,
                "error": "Пустой аудиофайл",
                "answer": "Не удалось записать голос. Попробуйте еще раз."
            })
        
        try:
            from services import speech_to_text
            recognized_text = await speech_to_text(tmp_path)
            
            if not recognized_text:
                return JSONResponse({
                    "success": False,
                    "error": "Не удалось распознать речь",
                    "answer": "Не удалось распознать голос. Попробуйте говорить четче или напишите текстом."
                })
            
            context = user_contexts.get(user_id)
            mode = context.communication_mode if context else "coach"
            profile = user_data.get(user_id, {})
            
            from services import call_deepseek_with_context
            response = await call_deepseek_with_context(
                user_id=user_id,
                user_message=recognized_text,
                context=context,
                mode=mode,
                profile_data=profile
            )
            
            if not response:
                response = "Я понял ваш вопрос. Дайте подумать..."
            
            # Генерируем голосовой ответ через Yandex TTS
            audio_response = await text_to_speech(response, mode)
            
            audio_url = None
            if audio_response:
                audio_filename = f"voice_response_{user_id}_{int(time.time())}.ogg"
                audio_path = os.path.join(MINIAPP_PATH, "audio", audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                
                with open(audio_path, 'wb') as f:
                    f.write(audio_response)
                
                audio_url = f"https://max-bot-1-ywpz.onrender.com/audio/{audio_filename}"
            
            return JSONResponse({
                "success": True,
                "recognized_text": recognized_text,
                "answer": response,
                "audio_url": audio_url
            })
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
    except Exception as e:
        logger.error(f"❌ Error in process_voice: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "answer": "Ошибка обработки голоса. Попробуйте позже."}
        )
@api_app.post("/api/chat/action")
async def chat_action(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        action = data.get('action')
        action_data = data.get('data', {})
        
        if not user_id or not action:
            raise HTTPException(status_code=400, detail="user_id and action required")
        
        user_id = int(user_id)
        
        if action == "start_test":
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {
                    "stage": 1,
                    "question_index": 0,
                    "message": "Начинаем тест. Этап 1: Тип восприятия"
                }
            })
        elif action == "show_profile":
            profile_data = await get_profile(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": profile_data
            })
        elif action == "show_thoughts":
            thoughts = await get_thought(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": thoughts
            })
        elif action == "show_weekend":
            ideas = await get_ideas(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": ideas
            })
        elif action == "ask_question":
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"message": "Задайте ваш вопрос"}
            })
        
        return JSONResponse({"success": True, "action": action})
        
    except Exception as e:
        logger.error(f"❌ Error in chat_action: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ API
# ============================================

def determine_dominant_dilts(dilts_counts: dict) -> str:
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def get_human_readable_profile(scores: dict, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    lines = []
    lines.append(f"🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ")
    lines.append("")
    lines.append(f"🔍 Тип восприятия: {perception_type}")
    lines.append(f"🧠 Уровень мышления: {thinking_level}/9")
    lines.append("")
    lines.append(f"🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА")
    lines.append("Информация уточняется")
    lines.append("")
    lines.append(f"💪 СИЛЬНЫЕ СТОРОНЫ")
    lines.append("• Высокоразвитые социальные навыки")
    lines.append("• Системное мышление")
    lines.append("• Устойчивость к стрессу")
    lines.append("• Прагматизм")
    lines.append("")
    lines.append(f"🎯 ЗОНЫ РОСТА")
    lines.append("• Информация уточняется")
    lines.append("")
    lines.append(f"⚠️ ГЛАВНАЯ ЛОВУШКА")
    lines.append("⚡ Поведение")
    return "\n".join(lines)

# ============================================
# ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ПРОФИЛЯ
# ============================================

async def generate_profile_interpretation_async(user_id: int):
    """Фоновая генерация интерпретации профиля"""
    try:
        logger.info(f"🧠 Начинаю генерацию интерпретации для пользователя {user_id}")
        
        await asyncio.sleep(2)
        
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('profile_data'):
            logger.warning(f"⚠️ Нет данных профиля для пользователя {user_id}")
            return
        
        from services import generate_ai_profile
        ai_profile = await generate_ai_profile(user_id, user_info)
        
        if ai_profile:
            user_data[user_id]['ai_generated_profile'] = ai_profile
            sync_db.save_user_to_db(user_id)
            logger.info(f"✅ Интерпретация для пользователя {user_id} сгенерирована")
            await send_to_telegram(user_id, ai_profile)
        else:
            profile = user_info.get('profile_data', {})
            deep = user_info.get('deep_patterns', {})
            
            fallback_profile = f"""🧠 <b>ВАШ ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ</b>

<b>Профиль:</b> {profile.get('display_name', 'не определен')}
<b>Тип восприятия:</b> {user_info.get('perception_type', 'не определен')}
<b>Уровень мышления:</b> {user_info.get('thinking_level', 5)}/9

<b>Глубинный паттерн:</b> {deep.get('attachment', '🤗 Надежный')}

Хотите получить более подробную интерпретацию? Задайте вопрос в чате."""
            
            user_data[user_id]['ai_generated_profile'] = fallback_profile
            sync_db.save_user_to_db(user_id)
            await send_to_telegram(user_id, fallback_profile)
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации интерпретации для {user_id}: {e}")
        import traceback
        traceback.print_exc()

async def send_to_telegram(user_id: int, text: str):
    """Отправляет интерпретацию в Telegram"""
    try:
        context = user_contexts.get(user_id)
        user_name = context.name if context else "друг"
        
        full_text = f"🧠 {user_name}, {text.lower() if text.startswith('🧠') else text}"
        
        keyboard = InlineKeyboardMarkup(keyboard=[
            [
                InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"),
                InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")
            ],
            [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
        ])
        
        await bot.send_message(
            user_id,
            full_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
        logger.info(f"📨 Интерпретация отправлена в Telegram пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")

# ============================================
# API ЭНДПОИНТЫ ДЛЯ ТЕСТА (продолжение)
# ============================================

@api_app.get("/api/test/question")
async def get_test_question(user_id: int, stage: int, index: int):
    try:
        user_id = int(user_id)
        stage = int(stage)
        index = int(index)
        
        stage_questions_count = {1: 4, 2: 6, 3: 24, 4: 12, 5: 8}
        total = stage_questions_count.get(stage, 4)
        
        stage1_questions = [
            {"text": "Как вы обычно воспринимаете новую информацию?", "options": [
                {"id": "A", "text": "Через визуальные образы и картинки", "value": "visual"},
                {"id": "B", "text": "Через ощущения и телесный опыт", "value": "kinesthetic"},
                {"id": "C", "text": "Через логические схемы и структуры", "value": "auditory"},
                {"id": "D", "text": "Через интуицию и общее впечатление", "value": "digital"}
            ]},
            {"text": "Что для вас важнее при принятии решения?", "options": [
                {"id": "A", "text": "Как это будет выглядеть", "value": "visual"},
                {"id": "B", "text": "Что я чувствую по этому поводу", "value": "kinesthetic"},
                {"id": "C", "text": "Логика и факты", "value": "auditory"},
                {"id": "D", "text": "Общая картина и смысл", "value": "digital"}
            ]},
            {"text": "Как вы лучше запоминаете?", "options": [
                {"id": "A", "text": "Когда вижу схему или изображение", "value": "visual"},
                {"id": "B", "text": "Когда записываю или проживаю", "value": "kinesthetic"},
                {"id": "C", "text": "Когда проговариваю вслух", "value": "auditory"},
                {"id": "D", "text": "Когда понимаю суть", "value": "digital"}
            ]},
            {"text": "Что вас вдохновляет?", "options": [
                {"id": "A", "text": "Красота и гармония", "value": "visual"},
                {"id": "B", "text": "Глубокие переживания", "value": "kinesthetic"},
                {"id": "C", "text": "Идеи и концепции", "value": "auditory"},
                {"id": "D", "text": "Смысл и предназначение", "value": "digital"}
            ]}
        ]
        
        stage2_questions = [
            {"text": "Я часто анализирую свои мысли и чувства", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]},
            {"text": "Мне важно понимать причины своих поступков", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]},
            {"text": "Я вижу взаимосвязи между разными событиями", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]},
            {"text": "Я задумываюсь о смысле жизни", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]},
            {"text": "Мне интересно изучать новые концепции", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]},
            {"text": "Я замечаю, как меняются мои взгляды со временем", "options": [
                {"id": "A", "text": "Совершенно не согласен", "value": 1},
                {"id": "B", "text": "Скорее не согласен", "value": 2},
                {"id": "C", "text": "Нейтрально", "value": 3},
                {"id": "D", "text": "Скорее согласен", "value": 4},
                {"id": "E", "text": "Полностью согласен", "value": 5}
            ]}
        ]
        
        if stage == 1 and index < len(stage1_questions):
            question = stage1_questions[index]
        elif stage == 2 and index < len(stage2_questions):
            question = stage2_questions[index]
        else:
            question = {
                "text": f"Вопрос {index + 1} этапа {stage}",
                "options": [
                    {"id": "A", "text": "Вариант А", "value": "A"},
                    {"id": "B", "text": "Вариант Б", "value": "B"},
                    {"id": "C", "text": "Вариант В", "value": "C"},
                    {"id": "D", "text": "Вариант Г", "value": "D"}
                ]
            }
        
        has_answer = False
        if user_id in user_data:
            answers = user_data[user_id].get('all_answers', [])
            for ans in answers:
                if ans.get('stage') == stage and ans.get('question_index') == index:
                    has_answer = True
                    break
        
        return JSONResponse({
            "success": True,
            "stage": stage,
            "index": index,
            "total": total,
            "text": question["text"],
            "options": question["options"],
            "hasAnswer": has_answer
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_test_question: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.post("/api/test/answer")
async def submit_test_answer(request: Request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        stage = data.get('stage')
        question_index = data.get('question_index')
        answer = data.get('answer')
        option = data.get('option')
        
        if not user_id or stage is None or question_index is None or answer is None:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        user_id = int(user_id)
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'all_answers' not in user_data[user_id]:
            user_data[user_id]['all_answers'] = []
        
        answer_record = {
            'stage': stage,
            'question_index': question_index,
            'answer': answer,
            'option': option,
            'timestamp': datetime.now().isoformat()
        }
        
        user_data[user_id]['all_answers'].append(answer_record)
        
        stage_key = f'stage{stage}_answers'
        if stage_key not in user_data[user_id]:
            user_data[user_id][stage_key] = []
        user_data[user_id][stage_key].append(answer_record)
        
        sync_db.save_user_to_db(user_id)
        
        stage_questions_count = {1: 4, 2: 6, 3: 24, 4: 12, 5: 8}
        total = stage_questions_count.get(stage, 4)
        stage_answers = [a for a in user_data[user_id].get('all_answers', []) 
                        if a.get('stage') == stage]
        stage_complete = len(stage_answers) >= total
        
        if stage_complete:
            if stage == 1 and 'perception_type' not in user_data[user_id]:
                user_data[user_id]['perception_type'] = 'visual'
            elif stage == 2 and 'thinking_level' not in user_data[user_id]:
                user_data[user_id]['thinking_level'] = 5
            elif stage == 3 and 'behavioral_levels' not in user_data[user_id]:
                user_data[user_id]['behavioral_levels'] = {
                    'extraversion': [3,4,3,4,3,4],
                    'neuroticism': [3,3,3,3,3,3],
                    'agreeableness': [4,4,4,4,4,4],
                    'conscientiousness': [4,4,4,4,4,4]
                }
            if stage < 5:
                user_data[user_id]['current_stage'] = stage + 1
            else:
                user_data[user_id]['current_stage'] = 5
        
        return JSONResponse({
            "success": True,
            "stageComplete": stage_complete
        })
        
    except Exception as e:
        logger.error(f"❌ Error in submit_test_answer: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/test/results")
async def get_test_stage_results(user_id: int, stage: int):
    try:
        user_id = int(user_id)
        stage = int(stage)
        data = user_data.get(user_id, {})
        
        results = {}
        
        if stage == 1:
            results = {
                "perception_type": data.get('perception_type', 'не определен'),
                "answers": data.get('stage1_answers', [])
            }
        elif stage == 2:
            results = {
                "thinking_level": data.get('thinking_level', 5),
                "answers": data.get('stage2_answers', [])
            }
        elif stage == 3:
            results = {
                "behavioral_levels": data.get('behavioral_levels', {}),
                "answers": data.get('stage3_answers', [])
            }
        elif stage == 4:
            results = {
                "dilts_counts": data.get('dilts_counts', {}),
                "answers": data.get('stage4_answers', [])
            }
        elif stage == 5:
            results = {
                "deep_patterns": data.get('deep_patterns', {}),
                "answers": data.get('stage5_answers', [])
            }
        
        return JSONResponse({
            "success": True,
            "stage": stage,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_test_stage_results: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# HEALTH CHECK ДЛЯ RENDER (HTTP сервер)
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
    """Запускает HTTP сервер для health check на порту, отличном от основного"""
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

health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДЛИННЫМИ СООБЩЕНИЯМИ
# ============================================

def generate_unique_callback(prefix: str, user_id: int, question: int, option: str, extra: str = "") -> str:
    """Генерирует уникальный callback"""
    timestamp = int(time.time() * 1000) % 10000
    return f"{prefix}_{question}_{option}_{extra}_{user_id}_{timestamp}"

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (УНИКАЛЬНЫЕ ДЛЯ MAIN)
# ============================================

def should_be_ironic(text: str) -> bool:
    """Проверяет, должен ли ответ быть ироничным"""
    ironic_markers = [
        "очевидно", "разумеется", "конечно", "естественно",
        "неужели", "серьёзно", "правда?", "интересно",
        "ха", "хм", "ну-ну", "ага"
    ]
    return any(marker in text.lower() for marker in ironic_markers)

def needs_clarification(avg: float) -> bool:
    """Проверяет, нужно ли уточнение"""
    CLARIFICATION_ZONES = [1.49, 2.00, 2.50, 3.00, 3.50]
    CLARIFICATION_MARGIN = 0.12
    return any(abs(avg - b) <= CLARIFICATION_MARGIN for b in CLARIFICATION_ZONES)

def check_consistency(scores_list: list) -> bool:
    """Проверяет согласованность ответов"""
    if len(scores_list) < 4:
        return True
    avg = sum(scores_list) / len(scores_list)
    variance = sum((x - avg) ** 2 for x in scores_list) / len(scores_list)
    std_dev = variance ** 0.5
    return std_dev <= 1.3

# ============================================
# ФУНКЦИЯ show_context_complete (вынесена из stages.py)
# ============================================

def show_context_complete(message: types.Message, context: UserContext):
    """Показывает итоговый экран после сбора контекста"""
    
    context.update_weather()
    
    summary = f"✅ {bold('Отлично! Теперь я знаю о вас:')}\n\n"
    
    if context.city:
        summary += f"📍 {bold('Город:')} {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        summary += f"👤 {bold('Пол:')} {gender_str}\n"
    if context.age:
        summary += f"📅 {bold('Возраст:')} {context.age}\n"
    if context.weather_cache:
        summary += f"{context.weather_cache['icon']} {bold('Погода:')} {context.weather_cache['description']}, {context.weather_cache['temp']}°C\n"
    
    summary += f"\n🎯 Теперь я буду учитывать это в наших разговорах!\n\n"
    summary += f"🧠 {bold('ЧТО ДАЛЬШЕ?')}\n\n"
    summary += "Чтобы я мог помочь по-настоящему, нужно пройти тест (15 минут).\n"
    summary += "Он определит ваш психологический профиль по 4 векторам и глубинным паттернам.\n\n"
    summary += f"👇 {bold('Начинаем?')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro"))
    keyboard.row(InlineKeyboardButton("📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest"))
    
    safe_send_message(message, summary, reply_markup=keyboard, delete_previous=True, keep_last=1)
    
    clear_state(message.from_user.id)

# ============================================
# ФУНКЦИИ ДЛЯ ГЛАВНОГО МЕНЮ (вынесены из modes.py)
# ============================================

def show_main_menu(message: types.Message, context: UserContext):
    """Показывает главное меню до теста"""
    
    context.update_weather()
    
    day_context = context.get_day_context()
    
    welcome_text = f"{context.get_greeting(context.name)}\n\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        welcome_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n"
    
    if day_context['is_weekend']:
        welcome_text += f"🏖 Сегодня выходной! Как настроение?\n\n"
    elif 9 <= day_context['hour'] < 18:
        welcome_text += f"💼 Рабочее время. Чем займёмся?\n\n"
    else:
        welcome_text += f"🏡 Личное время. Есть что обсудить?\n\n"
    
    welcome_text += f"👇 {bold('Выберите действие:')}"
    
    keyboard = get_main_menu_keyboard()
    
    safe_send_message(message, welcome_text, reply_markup=keyboard, delete_previous=True, keep_last=1)

def show_main_menu_after_mode(message: types.Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    context.update_weather()
    day_context = context.get_day_context()
    
    mode_name = mode_config['display_name']
    text = f"{mode_config['emoji']} {bold(f'РЕЖИМ {mode_name}')}\n\n"
    text += context.get_greeting(context.name) + "\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n\n"
    
    text += f"🧠 {bold('ЧЕМ ЗАЙМЁМСЯ?')}\n\n"
    
    if context.communication_mode == "coach":
        text += "• Задать вопрос — я помогу найти ответ внутри себя\n"
    elif context.communication_mode == "psychologist":
        text += "• Расскажите, что у вас на душе — я помогу исследовать глубинные паттерны\n"
    elif context.communication_mode == "trainer":
        text += "• Поставьте задачу — я дам конкретные шаги\n"
    
    text += "• Выбрать тему — отношения, деньги, самоощущение\n"
    text += "• Послушать сказку — для глубокой работы\n"
    text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    keyboard = get_main_menu_after_mode_keyboard()
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True, keep_last=1)

# ============================================
# ОБРАБОТЧИКИ КОМАНД
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

@bot.message_handler(commands=['test_yandex'])
def cmd_test_yandex(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    def run_async():
        asyncio.run(test_yandex_async(message))
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_weather'])
def cmd_test_weather(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    def run_async():
        asyncio.run(test_weather_async(message))
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_voices'])
def cmd_test_voices(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    def run_async():
        asyncio.run(test_voices_async(message))
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_voice_send'])
def cmd_test_voice_send(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    def run_async():
        asyncio.run(test_voice_send_async(message))
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['weekend'])
def cmd_weekend(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    if not data.get("profile_data") and not data.get("ai_generated_profile"):
        safe_send_message(message, "❓ Сначала нужно пройти тест, чтобы я понимал твой профиль. Используй /start", delete_previous=True)
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

# ============================================
# АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ
# ============================================

async def test_yandex_async(message: types.Message):
    status_msg = safe_send_message(message, "🎧 Тестирую Yandex TTS...", delete_previous=True)
    test_text = "Привет! Это тестовое голосовое сообщение."
    results = []
    for mode in ["coach", "psychologist", "trainer"]:
        audio = await text_to_speech(test_text, mode)
        if audio:
            results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']}")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']}")
        await asyncio.sleep(0.5)
    safe_delete_message(message.chat.id, status_msg.message_id)
    safe_send_message(message, "📊 Результаты тестирования Yandex TTS:\n" + "\n".join(results), delete_previous=True)

async def test_weather_async(message: types.Message):
    if not OPENWEATHER_API_KEY:
        safe_send_message(message, "❌ OPENWEATHER_API_KEY не настроен", delete_previous=True)
        return
    test_city = "Москва"
    status_msg = safe_send_message(message, f"🌍 Тестирую погоду для города {test_city}...", delete_previous=True)
    try:
        from services import get_http_client
        url = f"http://api.openweathermap.org/data/2.5/weather?q={test_city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        client = await get_http_client()
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            desc = data['weather'][0]['description']
            humidity = data['main']['humidity']
            wind = data['wind']['speed']
            text = f"✅ Погода работает!\n\n📍 Город: {test_city}\n🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n☁️ Описание: {desc}\n💧 Влажность: {humidity}%\n💨 Ветер: {wind} м/с"
            safe_delete_message(message.chat.id, status_msg.message_id)
            safe_send_message(message, text, delete_previous=True)
        else:
            error_text = response.text
            safe_delete_message(message.chat.id, status_msg.message_id)
            safe_send_message(message, f"❌ Ошибка {response.status_code}: {error_text[:200]}", delete_previous=True)
    except Exception as e:
        safe_delete_message(message.chat.id, status_msg.message_id)
        safe_send_message(message, f"❌ Ошибка: {e}", delete_previous=True)

async def test_voices_async(message: types.Message):
    safe_send_message(message, "🎙 Функция тестирования голосов в разработке", delete_previous=True)

async def test_voice_send_async(message: types.Message):
    status_msg = safe_send_message(message, "🎧 Тестирую отправку голоса...", delete_previous=True)
    test_text = "Привет! Это тестовое голосовое сообщение."
    results = []
    for mode in ["coach", "psychologist", "trainer"]:
        audio = await text_to_speech(test_text, mode)
        if audio:
            success = await send_voice_to_max(message.chat.id, audio, f"Тест режима {mode}")
            if success:
                results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']} (отправлен)")
            else:
                results.append(f"⚠️ {COMMUNICATION_MODES[mode]['display_name']} (ошибка отправки)")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']} (не сгенерирован)")
        await asyncio.sleep(1)
    safe_delete_message(message.chat.id, status_msg.message_id)
    safe_send_message(message, "📊 Результаты тестирования отправки голоса:\n" + "\n".join(results), delete_previous=True)

async def show_weekend_ideas(message: types.Message, user_id: int):
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = user_names.get(user_id, "друг")
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    profile_data = data.get("profile_data", {})
    status_msg = safe_send_message(message, "🎨 Генерирую идеи специально для тебя...\n\nЭто займёт несколько секунд.", delete_previous=True)
    try:
        ideas_text = await weekend_planner.get_weekend_ideas(
            user_id=user_id,
            user_name=user_name,
            scores=scores,
            profile_data=profile_data,
            context=context
        )
        safe_delete_message(message.chat.id, status_msg.message_id)
        keyboard = get_weekend_ideas_keyboard()
        safe_send_message(message, ideas_text, reply_markup=keyboard, delete_previous=True)
    except Exception as e:
        logger.error(f"Ошибка генерации идей: {e}")
        safe_delete_message(message.chat.id, status_msg.message_id)
        safe_send_message(message, "😔 Что-то пошло не так. Попробуй позже.", delete_previous=True)
# ============================================
# CALLBACK-ОБРАБОТЧИК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: types.CallbackQuery):
    callback_handler(call)

# ============================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ============================================

# 🔥🔥🔥 ОБРАБОТЧИК ГОЛОСОВЫХ СООБЩЕНИЙ 🔥🔥🔥
@bot.message_handler(content_types=['voice'])
def handle_voice_wrapper(message: types.Message):
    """Обработчик голосовых сообщений"""
    logger.error("=" * 80)
    logger.error("🎤🎤🎤 ПОЛУЧЕНО ГОЛОСОВОЕ СООБЩЕНИЕ 🎤🎤🎤")
    logger.error(f"   user_id: {message.from_user.id}")
    logger.error(f"   длительность: {message.voice.duration if message.voice else 'неизвестно'}")
    logger.error(f"   file_id: {message.voice.file_id if message.voice else 'нет'}")
    logger.error("=" * 80)
    
    def run_async():
        asyncio.run(handle_voice_message(message))
    
    threading.Thread(target=run_async, daemon=True).start()

# ============================================
# ОСТАЛЬНЫЕ ОБРАБОТЧИКИ (ОСТАЮТСЯ КАК ЕСТЬ)
# ============================================

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
        safe_send_message(message, "Пожалуйста, ответьте на вопрос или используйте кнопки", delete_previous=True, keep_last=1)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_question)
def handle_question_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    logger.info(f"❓ Получен вопрос от пользователя {user_id} в состоянии awaiting_question: {text[:50]}...")
    def run_sync():
        from handlers.questions import process_text_question_sync
        process_text_question_sync(message, user_id, text)
    threading.Thread(target=run_sync, daemon=True).start()

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_custom_goal)
def handle_custom_goal_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    logger.info(f"🎯 Получена пользовательская цель от пользователя {user_id}: {text[:50]}...")
    def run_async():
        asyncio.run(process_custom_goal_async(message, user_id, text))
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.pretest_question)
def handle_pretest_question(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    logger.info(f"❓ Получен вопрос до теста от пользователя {user_id}")
    safe_send_message(message, "Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. Пройдите тест — это займёт 15 минут.", delete_previous=True)
    clear_state(user_id)


# ПОСЛЕДНИЙ ОБРАБОТЧИК: ВСЕ НЕИЗВЕСТНЫЕ СООБЩЕНИЯ
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
    safe_send_message(message, "Используйте кнопки для навигации:", reply_markup=keyboard, keep_last=1)
    
# ============================================
# АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ ОБРАБОТКИ СООБЩЕНИЙ
# ============================================

async def process_custom_goal_async(message: types.Message, user_id: int, text: str):
    try:
        from handlers.goals import process_custom_goal_async as process_goal
        await process_goal(message, user_id, text)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке пользовательской цели: {e}")
        import traceback
        traceback.print_exc()
        await safe_send_message(message, "❌ Произошла ошибка при обработке цели. Пожалуйста, попробуйте еще раз.", delete_previous=True)

# ============================================
# ФУНКЦИЯ ПРОВЕРКИ API ПРИ СТАРТЕ
# ============================================

async def check_api_on_startup():
    logger.info("🔍 Проверка API при запуске...")
    results = {"deepseek": False, "deepgram": False, "yandex": False, "openweather": False}
    
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

# ============================================
# ФУНКЦИЯ ЗАПУСКА FASTAPI
# ============================================

def run_fastapi():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск FastAPI на порту {port}")
    uvicorn.run(api_app, host="0.0.0.0", port=port, log_level="info")

def run_async_tasks():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(check_api_on_startup())
    finally:
        loop.close()

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
        saved_count = save_all_users_to_db()
        logger.info(f"✅ Сохранено {saved_count} пользователей")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
    try:
        await close_db()
        logger.info("✅ База данных закрыта")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии БД: {e}")

def main():
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v9.6 (MAX)")
    print("="*80)
    print(f"👤 Ваш ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("🎙 Распознавание: " + ("✅" if DEEPGRAM_API_KEY else "❌"))
    print("🎙 Синтез речи: " + ("✅" if YANDEX_API_KEY else "❌"))
    print("🌍 Погода: " + ("✅" if OPENWEATHER_API_KEY else "❌"))
    print("🎭 Режимы: 🔮 КОУЧ | 🧠 ПСИХОЛОГ | ⚡ ТРЕНЕР")
    print("📊 5 этапов тестирования: ✅")
    print("🎯 Динамический подбор целей: ✅")
    print("🔍 Проверка реальности: ✅")
    print("🎤 Голосовые сообщения: " + ("✅" if DEEPGRAM_API_KEY and YANDEX_API_KEY else "❌"))
    print("🗓 Планировщик задач: ✅")
    print("🎨 Идеи на выходные: ✅")
    print("🔬 Глубинный анализ вопросов: ✅")
    print("📱 Мини-приложение: ✅ (FastAPI + полная синхронизация)")
    print("🗄️ Постоянное хранение: ✅ (PostgreSQL)")
    print("="*80 + "\n")
    
    logger.info("🚀 Бот для MAX запущен!")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(init_database())
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        logger.warning("⚠️ Продолжаем работу БЕЗ PostgreSQL (только память)")
    
    scheduler.start()
    async_thread = threading.Thread(target=run_async_tasks, daemon=True)
    async_thread.start()
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    logger.info("✅ FastAPI сервер запущен")
    
    try:
        import signal
        def signal_handler():
            asyncio.create_task(shutdown_handler())
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось установить обработчик сигналов: {e}")
    
    is_render = os.environ.get('RENDER') is not None
    retry_count = 0
    max_retries = 5 if not is_render else 1
    
    try:
        while retry_count < max_retries:
            try:
                bot.polling()
            except KeyboardInterrupt:
                logger.info("👋 Бот остановлен пользователем")
                loop.run_until_complete(shutdown_handler())
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Ошибка: {e}")
                if retry_count < max_retries:
                    delay = random.randint(3, 7)
                    logger.info(f"🔄 Перезапуск {retry_count}/{max_retries} через {delay}с...")
                    time.sleep(delay)
                else:
                    logger.error("❌ Превышено количество попыток")
                    loop.run_until_complete(shutdown_handler())
    finally:
        cleanup_resources()

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ API ЭНДПОИНТЫ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

@api_app.get("/api/goals")
async def get_goals(user_id: int, mode: str = "coach"):
    """
    Получает динамически подобранные цели для пользователя
    """
    try:
        user_id = int(user_id)
        
        # Получаем данные пользователя
        data = user_data.get(user_id, {})
        profile_data = data.get("profile_data", {})
        profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
        
        # Получаем scores из профиля
        scores = {
            "СБ": profile_data.get("sb_level", 4),
            "ТФ": profile_data.get("tf_level", 4),
            "УБ": profile_data.get("ub_level", 4),
            "ЧВ": profile_data.get("chv_level", 4)
        }
        
        # Определяем слабый вектор
        weakest = min(scores.items(), key=lambda x: x[1])[0] if scores else "СБ"
        
        # База целей для разных режимов
        goals_db = {
            "coach": {
                "weak": {
                    "СБ": [
                        {"id": "fear_work", "name": "Проработать страхи", "time": "3-4 недели", "difficulty": "medium", "emoji": "🛡️"},
                        {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "emoji": "🔒"},
                        {"id": "calm", "name": "Найти внутреннее спокойствие", "time": "3-5 недель", "difficulty": "hard", "emoji": "🧘"}
                    ],
                    "ТФ": [
                        {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "emoji": "💰"},
                        {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "emoji": "📈"},
                        {"id": "financial_plan", "name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy", "emoji": "📊"}
                    ],
                    "УБ": [
                        {"id": "meaning", "name": "Найти смысл и предназначение", "time": "4-6 недель", "difficulty": "hard", "emoji": "🎯"},
                        {"id": "system_thinking", "name": "Развить системное мышление", "time": "3-5 недель", "difficulty": "medium", "emoji": "🧩"},
                        {"id": "trust", "name": "Научиться доверять миру", "time": "3-4 недели", "difficulty": "medium", "emoji": "🤝"}
                    ],
                    "ЧВ": [
                        {"id": "relations", "name": "Улучшить отношения", "time": "4-6 недель", "difficulty": "hard", "emoji": "💕"},
                        {"id": "boundaries_people", "name": "Выстроить границы с людьми", "time": "3-4 недели", "difficulty": "medium", "emoji": "🚧"},
                        {"id": "attachment", "name": "Проработать тип привязанности", "time": "5-7 недель", "difficulty": "hard", "emoji": "🪢"}
                    ]
                },
                "general": [
                    {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "emoji": "🌟"},
                    {"id": "balance", "name": "Обрести баланс", "time": "4-6 недель", "difficulty": "medium", "emoji": "⚖️"},
                    {"id": "growth", "name": "Личностный рост", "time": "6-8 недель", "difficulty": "medium", "emoji": "🌱"}
                ]
            },
            "psychologist": {
                "weak": {
                    "СБ": [
                        {"id": "fear_origin", "name": "Найти источник страхов", "time": "4-6 недель", "difficulty": "hard", "emoji": "🔍"},
                        {"id": "trauma", "name": "Проработать травму", "time": "6-8 недель", "difficulty": "hard", "emoji": "🩹"},
                        {"id": "safety", "name": "Сформировать чувство безопасности", "time": "5-7 недель", "difficulty": "hard", "emoji": "🛡️"}
                    ],
                    "ТФ": [
                        {"id": "money_psychology", "name": "Понять психологию денег", "time": "4-5 недель", "difficulty": "medium", "emoji": "🧠💰"},
                        {"id": "worth", "name": "Проработать чувство ценности", "time": "5-7 недель", "difficulty": "hard", "emoji": "💎"},
                        {"id": "scarcity", "name": "Проработать сценарий дефицита", "time": "4-6 недель", "difficulty": "medium", "emoji": "🔄"}
                    ],
                    "УБ": [
                        {"id": "core_beliefs", "name": "Найти глубинные убеждения", "time": "5-7 недель", "difficulty": "hard", "emoji": "🏛️"},
                        {"id": "schemas", "name": "Проработать жизненные сценарии", "time": "6-8 недель", "difficulty": "hard", "emoji": "📜"},
                        {"id": "meaning_deep", "name": "Экзистенциальный поиск", "time": "7-9 недель", "difficulty": "hard", "emoji": "🌌"}
                    ],
                    "ЧВ": [
                        {"id": "attachment_style", "name": "Проработать тип привязанности", "time": "6-8 недель", "difficulty": "hard", "emoji": "🪢"},
                        {"id": "inner_child", "name": "Исцелить внутреннего ребёнка", "time": "5-7 недель", "difficulty": "hard", "emoji": "🧸"},
                        {"id": "family_system", "name": "Проработать семейную систему", "time": "6-8 недель", "difficulty": "hard", "emoji": "🏠"}
                    ]
                },
                "general": [
                    {"id": "self_discovery", "name": "Глубинное самопознание", "time": "7-9 недель", "difficulty": "hard", "emoji": "🔮"},
                    {"id": "healing", "name": "Исцеление внутренних ран", "time": "8-10 недель", "difficulty": "hard", "emoji": "💖"},
                    {"id": "integration", "name": "Интеграция личности", "time": "9-12 недель", "difficulty": "hard", "emoji": "🧩"}
                ]
            },
            "trainer": {
                "weak": {
                    "СБ": [
                        {"id": "assertiveness", "name": "Развить ассертивность", "time": "3-4 недели", "difficulty": "medium", "emoji": "💪"},
                        {"id": "conflict_skills", "name": "Освоить навыки конфликта", "time": "4-5 недель", "difficulty": "medium", "emoji": "⚔️"},
                        {"id": "courage", "name": "Тренировка смелости", "time": "3-5 недель", "difficulty": "hard", "emoji": "🦁"}
                    ],
                    "ТФ": [
                        {"id": "money_skills", "name": "Освоить навыки управления деньгами", "time": "3-4 недели", "difficulty": "easy", "emoji": "💰"},
                        {"id": "income_skills", "name": "Навыки увеличения дохода", "time": "4-6 недель", "difficulty": "medium", "emoji": "📊"},
                        {"id": "investment_skills", "name": "Навыки инвестирования", "time": "5-7 недель", "difficulty": "hard", "emoji": "📈"}
                    ],
                    "УБ": [
                        {"id": "thinking_tools", "name": "Освоить инструменты мышления", "time": "4-5 недель", "difficulty": "medium", "emoji": "🧠"},
                        {"id": "triz", "name": "Научиться ТРИЗ", "time": "5-7 недель", "difficulty": "hard", "emoji": "💡"},
                        {"id": "decision_making", "name": "Навыки принятия решений", "time": "3-4 недели", "difficulty": "easy", "emoji": "✅"}
                    ],
                    "ЧВ": [
                        {"id": "communication_skills", "name": "Развить навыки общения", "time": "3-4 недели", "difficulty": "easy", "emoji": "💬"},
                        {"id": "negotiation", "name": "Навыки переговоров", "time": "4-6 недель", "difficulty": "medium", "emoji": "🤝"},
                        {"id": "influence", "name": "Навыки влияния", "time": "5-7 недель", "difficulty": "hard", "emoji": "⚡"}
                    ]
                },
                "general": [
                    {"id": "productivity", "name": "Повысить продуктивность", "time": "4-6 недель", "difficulty": "medium", "emoji": "⚡"},
                    {"id": "habit_building", "name": "Сформировать полезные привычки", "time": "3-5 недель", "difficulty": "easy", "emoji": "🔄"},
                    {"id": "skill_mastery", "name": "Мастерство в ключевых навыках", "time": "8-10 недель", "difficulty": "hard", "emoji": "🏆"}
                ]
            }
        }
        
        mode_db = goals_db.get(mode, goals_db["coach"])
        goals = []
        
        # Добавляем цели для слабого вектора
        if weakest in mode_db["weak"]:
            goals.extend(mode_db["weak"][weakest])
        
        # Добавляем общие цели
        goals.extend(mode_db["general"])
        
        # Возвращаем первые 6 целей
        return JSONResponse({
            "success": True,
            "goals": goals[:6],
            "profile_code": profile_code
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_goals: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/modes")
async def get_modes():
    """
    Получает список доступных режимов общения
    """
    try:
        modes = [
            {
                "id": "coach",
                "name": "КОУЧ",
                "emoji": "🔮",
                "description": "Если хочешь, чтобы я помог тебе самому найти решения.",
                "what": "Задавать открытые вопросы, отражать твои мысли, направлять.",
                "get": "• Жить станет легче\n• Появится больше радости от простых вещей\n• Начнёшь замечать возможности вместо проблем"
            },
            {
                "id": "psychologist",
                "name": "ПСИХОЛОГ",
                "emoji": "🧠",
                "description": "Если хочешь копнуть вглубь, разобраться с причинами, а не следствиями.",
                "what": "Исследовать твои глубинные паттерны, защитные механизмы, прошлый опыт.",
                "get": "• Перестанешь реагировать на триггеры\n• Исчезнут старые сценарии\n• Поймёшь, откуда растут ноги у твоих страхов"
            },
            {
                "id": "trainer",
                "name": "ТРЕНЕР",
                "emoji": "⚡",
                "description": "Если нужны чёткие инструменты, навыки и результат.",
                "what": "Формировать твои поведенческие и мыслительные навыки.",
                "get": "• Научишься чётко формулировать мысли\n• Освоишь алгоритмы ведения переговоров\n• Сформируешь полезные привычки"
            }
        ]
        
        return JSONResponse({
            "success": True,
            "modes": modes
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_modes: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# ЭНДПОИНТ ДЛЯ УМНЫХ ВОПРОСОВ
# ============================================

@api_app.get("/api/smart-questions")
async def get_smart_questions(user_id: int):
    """
    Получает умные вопросы для пользователя на основе его профиля
    """
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        # Получаем scores из профиля
        scores = {}
        for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
            levels = data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        # Генерируем вопросы
        questions = []
        
        tf = scores.get("ТФ", 3)
        sb = scores.get("СБ", 3)
        ub = scores.get("УБ", 3)
        cv = scores.get("ЧВ", 3)
        
        # Вопросы про деньги
        if tf <= 2:
            questions.append("Как начать зарабатывать, если нет денег?")
            questions.append("Почему мне не везет с деньгами?")
        elif tf <= 4:
            questions.append("Как увеличить доход без новых вложений?")
            questions.append("Как создать финансовую подушку?")
        
        # Вопросы про давление и конфликты
        if sb <= 2:
            questions.append("Как перестать бояться конфликтов?")
            questions.append("Как научиться говорить 'нет'?")
        elif sb <= 4:
            questions.append("Почему я злюсь внутри, но молчу?")
            questions.append("Как защищать границы без агрессии?")
        
        # Вопросы про понимание мира
        if ub <= 2:
            questions.append("Как понять, что происходит в жизни?")
        elif ub == 4:
            questions.append("Как перестать искать заговоры?")
        
        # Вопросы про отношения
        if cv <= 2:
            questions.append("Как перестать зависеть от других?")
        elif cv <= 4:
            questions.append("Почему отношения поверхностные?")
        
        # Общие вопросы, если не хватает
        general = [
            "С чего начать изменения?",
            "Что мне делать с этой ситуацией?",
            "Как не срываться на близких?"
        ]
        
        while len(questions) < 5:
            for q in general:
                if q not in questions and len(questions) < 5:
                    questions.append(q)
        
        # Ограничиваем 5 вопросами
        questions = questions[:5]
        
        return JSONResponse({
            "success": True,
            "questions": questions
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_smart_questions: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "questions": []}
        )

# ============================================
# НЕДОСТАЮЩИЕ API ЭНДПОИНТЫ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

@api_app.get("/api/max-status")
async def get_max_api_status():
    """Проверяет доступность MAX API"""
    status = {
        "available": False,
        "message": "MAX API недоступен",
        "token_configured": bool(MAX_TOKEN)
    }
    
    if not MAX_TOKEN:
        return JSONResponse(status)
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://platform-api.max.ru/bot/{MAX_TOKEN}/getMe"
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    status["available"] = True
                    status["message"] = "MAX API доступен"
                    bot_info = await response.json()
                    status["bot_name"] = bot_info.get("result", {}).get("first_name", "MAX Bot")
                else:
                    status["message"] = f"MAX API ответил с ошибкой {response.status}"
    except asyncio.TimeoutError:
        status["message"] = "MAX API не отвечает (таймаут)"
    except Exception as e:
        status["message"] = f"Ошибка: {str(e)}"
    
    return JSONResponse(status)


@api_app.post("/api/send-message")
async def send_message_via_max(request: Request):
    """Отправляет сообщение через MAX API"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        text = data.get('text')
        keyboard = data.get('keyboard')
        
        if not user_id or not text:
            raise HTTPException(status_code=400, detail="user_id and text required")
        
        if not MAX_TOKEN:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "MAX API не настроен"}
            )
        
        url = f"https://platform-api.max.ru/bot/{MAX_TOKEN}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if keyboard:
            payload["reply_markup"] = keyboard
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    return JSONResponse({"success": True, "result": result})
                else:
                    error_text = await response.text()
                    logger.error(f"MAX API error: {response.status} - {error_text}")
                    return JSONResponse(
                        status_code=response.status,
                        content={"success": False, "error": error_text}
                    )
                    
    except Exception as e:
        logger.error(f"❌ Error in send_message_via_max: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/user-status")
async def api_user_status(user_id: int):
    """Получить статус пользователя (есть ли профиль, интерпретация)"""
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        return JSONResponse({
            "success": True,
            "has_profile": bool(user_info.get('profile_data')) or bool(user_info.get('ai_generated_profile')),
            "has_interpretation": bool(user_info.get('ai_generated_profile')),
            "test_completed": user_info.get('test_completed', False),
            "interpretation_ready": bool(user_info.get('ai_generated_profile')),
            "profile_code": user_info.get('profile_data', {}).get('display_name'),
            "max_api_available": bool(MAX_TOKEN)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in api_user_status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/chat/action")
async def api_chat_action(request: Request):
    """Обработка действий из чата (кнопки)"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        action = data.get('action')
        action_data = data.get('data', {})
        
        if not user_id or not action:
            raise HTTPException(status_code=400, detail="user_id and action required")
        
        user_id = int(user_id)
        
        if action == "start_test":
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"stage": 1, "question_index": 0}
            })
        elif action == "show_profile":
            profile_data = user_data.get(user_id, {}).get('ai_generated_profile')
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"profile": profile_data}
            })
        elif action == "show_thoughts":
            thought = user_data.get(user_id, {}).get('psychologist_thought')
            if not thought:
                thought = await generate_psychologist_thought(user_id, user_data.get(user_id, {}))
                if thought:
                    if user_id not in user_data:
                        user_data[user_id] = {}
                    user_data[user_id]['psychologist_thought'] = thought
                    sync_db.save_user_to_db(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"thought": thought or "Мысли психолога еще не сгенерированы."}
            })
        elif action == "show_weekend":
            ideas = await api_get_ideas_internal(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"ideas": ideas}
            })
        elif action == "ask_question":
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"message": "Задайте ваш вопрос"}
            })
        
        return JSONResponse({"success": True, "action": action})
        
    except Exception as e:
        logger.error(f"❌ Error in api_chat_action: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/voice/process")
async def process_voice(request: Request):
    """Обработка голосового сообщения"""
    try:
        import time  # ✅ ДОБАВИТЬ импорт
        
        form = await request.form()
        user_id = form.get('user_id')
        voice_file = form.get('voice')
        
        if not user_id or not voice_file:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "user_id and voice file required"}
            )
        
        # ✅ ПРЕОБРАЗУЕМ user_id В INT
        try:
            user_id = int(user_id)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "invalid user_id"}
            )
        
        # Сохраняем временно файл
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp_path = tmp.name
        
        content = await voice_file.read()
        with open(tmp_path, 'wb') as f:
            f.write(content)
        
        # Проверяем размер файла
        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            os.unlink(tmp_path)
            return JSONResponse({
                "success": False,
                "error": "Пустой аудиофайл",
                "answer": "Не удалось записать голос. Попробуйте еще раз."
            })
        
        try:
            # ✅ ДЛЯ WEBM ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ CONTENT-TYPE
            from services import speech_to_text
            recognized_text = await speech_to_text(tmp_path)
            
            if not recognized_text:
                return JSONResponse({
                    "success": False,
                    "error": "Не удалось распознать речь",
                    "answer": "Не удалось распознать голос. Попробуйте говорить четче или напишите текстом."
                })
            
            # Отправляем текст в DeepSeek
            context = user_contexts.get(user_id)
            mode = context.communication_mode if context else "coach"
            profile = user_data.get(user_id, {})
            
            from services import call_deepseek_with_context
            response = await call_deepseek_with_context(
                user_id=user_id,
                user_message=recognized_text,
                context=context,
                mode=mode,
                profile_data=profile
            )
            
            if not response:
                response = "Я понял ваш вопрос. Дайте подумать..."
            
            # Генерируем голосовой ответ через Yandex TTS
            audio_response = await text_to_speech(response, mode)
            
            audio_url = None
            if audio_response:
                audio_filename = f"voice_response_{user_id}_{int(time.time())}.ogg"
                audio_path = os.path.join(MINIAPP_PATH, "audio", audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                
                with open(audio_path, 'wb') as f:
                    f.write(audio_response)
                
                audio_url = f"/audio/{audio_filename}"
            
            return JSONResponse({
                "success": True,
                "recognized_text": recognized_text,
                "answer": response,
                "audio_url": audio_url
            })
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
    except Exception as e:
        logger.error(f"❌ Error in process_voice: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "answer": "Ошибка обработки голоса. Попробуйте позже."}
        )


@api_app.post("/api/tts")
async def text_to_speech_api(request: Request):
    """Преобразование текста в речь"""
    try:
        data = await request.json()
        text = data.get('text')
        mode = data.get('mode', 'coach')
        
        if not text:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "text required"}
            )
        
        from services import text_to_speech
        audio = await text_to_speech(text, mode)
        
        if audio:
            import base64
            audio_base64 = base64.b64encode(audio).decode('utf-8')
            return JSONResponse({
                "success": True,
                "audio_base64": audio_base64
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to generate speech"
            })
            
    except Exception as e:
        logger.error(f"❌ Error in tts: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# WEBHOOK ДЛЯ MAX
# ============================================

@api_app.get("/webhook")
async def webhook_get():
    """GET-обработчик для проверки вебхука платформой MAX"""
    logger.info("✅ GET-запрос на /webhook (проверка доступности)")
    return JSONResponse({
        "status": "ok",
        "message": "Webhook is active",
        "method": "GET"
    })


@api_app.post("/webhook")
async def webhook(request: Request):
    """POST-обработчик для получения обновлений от MAX"""
    try:
        data = await request.json()
        logger.info(f"📨 Получен POST-запрос на webhook: {data}")
        
        # Здесь можно обработать входящие обновления
        # и извлечь user_id из данных
        
        return JSONResponse({"status": "ok", "message": "Webhook received"})
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def api_get_ideas_internal(user_id: int) -> list:
    """Внутренняя функция для получения идей"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context else user_names.get(user_id, "друг")
    
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
    
    ideas = []
    paragraphs = ideas_text.split('\n\n') if ideas_text else []
    for p in paragraphs:
        if p.strip() and not p.startswith('#'):
            ideas.append({
                "title": p[:50] + "..." if len(p) > 50 else p,
                "description": p
            })
    
    return ideas[:5]


# Обновляем существующий эндпоинт /api/ideas
@api_app.get("/api/ideas")
async def api_ideas(user_id: int):
    """Получить идеи на выходные"""
    try:
        ideas = await api_get_ideas_internal(user_id)
        return JSONResponse({"success": True, "ideas": ideas})
    except Exception as e:
        logger.error(f"❌ Error in api_ideas: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "ideas": []}
        )

# ============================================
# ДОПОЛНИТЕЛЬНЫЙ ЭНДПОИНТ ДЛЯ СТАТУСА ПОЛЬЗОВАТЕЛЯ (уже есть, но оставляем для совместимости)
# ============================================

# Обратите внимание: эндпоинт /api/user-status уже есть выше
# Этот нужен для единообразия
@api_app.get("/api/user-full-status")
async def get_user_full_status(user_id: int):
    """Полный статус пользователя (для дашборда)"""
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        context = user_contexts.get(user_id)
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "user_name": context.name if context else user_names.get(user_id, "друг"),
            "has_profile": bool(user_info.get('profile_data')) or bool(user_info.get('ai_generated_profile')),
            "has_interpretation": bool(user_info.get('ai_generated_profile')),
            "test_completed": user_info.get('test_completed', False),
            "interpretation_ready": bool(user_info.get('ai_generated_profile')),
            "profile_code": user_info.get('profile_data', {}).get('display_name'),
            "profile_scores": {
                "sb": user_info.get('profile_data', {}).get('sb_level', 4),
                "tf": user_info.get('profile_data', {}).get('tf_level', 4),
                "ub": user_info.get('profile_data', {}).get('ub_level', 4),
                "chv": user_info.get('profile_data', {}).get('chv_level', 4)
            },
            "days_active": 3,  # можно вычислить из БД
            "sessions_count": len(user_info.get('all_answers', [])) // 3  # примерная статистика
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_user_full_status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# ЭНДПОИНТ ДЛЯ ОТДАЧИ АУДИОФАЙЛОВ
# ============================================

@api_app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Отдаёт аудиофайлы для воспроизведения"""
    audio_path = os.path.join(MINIAPP_PATH, "audio", filename)
    if os.path.exists(audio_path):
        return FileResponse(audio_path, media_type="audio/ogg")
    return JSONResponse(status_code=404, content={"error": "Audio not found"})

# ============================================
# 🚀 НЕДОСТАЮЩИЕ API ЭНДПОИНТЫ ДЛЯ ДАШБОРДА 🚀
# ============================================

@api_app.get("/api/challenge/stats")
async def get_challenge_stats(user_id: int):
    """Получить статистику челленджей пользователя"""
    try:
        user_id = int(user_id)
        
        # Получаем данные пользователя
        user_info = user_data.get(user_id, {})
        
        # Пока возвращаем заглушку
        return JSONResponse({
            "success": True,
            "stats": {
                "total": 0,
                "completed": 0,
                "points": user_info.get('points', 0),
                "streak": user_info.get('streak', 0),
                "daily_completed": False,
                "weekly_completed": False,
                "level": 1,
                "next_level_points": 100
            }
        })
    except Exception as e:
        logger.error(f"❌ Error in get_challenge_stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/challenges")
async def get_challenges(user_id: int):
    """Получить список активных челленджей"""
    try:
        user_id = int(user_id)
        
        # Получаем профиль пользователя
        user_info = user_data.get(user_id, {})
        profile_data = user_info.get('profile_data', {})
        
        # Базовые челленджи
        challenges = [
            {
                "id": 1,
                "name": "Ежедневное общение",
                "description": "Напиши сообщение в чат",
                "progress": 0,
                "target": 1,
                "reward": 10,
                "emoji": "💬",
                "type": "daily",
                "completed": False
            },
            {
                "id": 2,
                "name": "Анализ мыслей",
                "description": "Запиши 3 мысли в дневник",
                "progress": 0,
                "target": 3,
                "reward": 30,
                "emoji": "📝",
                "type": "daily",
                "completed": False
            },
            {
                "id": 3,
                "name": "Осознанность",
                "description": "Практика осознанности",
                "progress": 0,
                "target": 1,
                "reward": 20,
                "emoji": "🧘",
                "type": "daily",
                "completed": False
            }
        ]
        
        # Добавляем персонализированные челленджи
        if profile_data:
            sb = profile_data.get('sb_level', 4)
            tf = profile_data.get('tf_level', 4)
            
            if sb < 3:
                challenges.append({
                    "id": 4,
                    "name": "Преодоление страхов",
                    "description": "Сделай одно действие, которое пугает",
                    "progress": 0,
                    "target": 1,
                    "reward": 50,
                    "emoji": "🛡️",
                    "type": "personalized",
                    "completed": False
                })
            
            if tf < 3:
                challenges.append({
                    "id": 5,
                    "name": "Финансовая осознанность",
                    "description": "Запиши все расходы",
                    "progress": 0,
                    "target": 1,
                    "reward": 40,
                    "emoji": "💰",
                    "type": "personalized",
                    "completed": False
                })
        
        return JSONResponse({
            "success": True,
            "challenges": challenges
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_challenges: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "challenges": []}
        )


@api_app.get("/api/psychometric/find-doubles")
async def find_doubles(user_id: int, limit: int = 10):
    """Найти психометрических двойников"""
    try:
        user_id = int(user_id)
        
        # Получаем профиль пользователя
        user_info = user_data.get(user_id, {})
        profile_data = user_info.get('profile_data', {})
        
        if not profile_data:
            return JSONResponse({
                "success": True,
                "doubles": [],
                "total": 0,
                "message": "Пройдите тест, чтобы найти двойников"
            })
        
        # Ищем пользователей с похожим профилем
        doubles = []
        user_code = profile_data.get('display_name', '')
        
        # Проходим по всем пользователям в памяти
        for other_id, other_info in user_data.items():
            if other_id == user_id:
                continue
            
            other_profile = other_info.get('profile_data', {})
            if not other_profile:
                continue
            
            other_code = other_profile.get('display_name', '')
            
            # Сравниваем коды профилей
            if user_code and other_code and user_code == other_code:
                other_context = user_contexts.get(other_id)
                doubles.append({
                    "user_id": other_id,
                    "name": other_context.name if other_context else f"Пользователь {other_id}",
                    "profile_code": other_code,
                    "similarity": 0.85,
                    "common_traits": ["Аналитическое мышление", "Эмоциональный интеллект"]
                })
        
        # Ограничиваем количество
        doubles = doubles[:limit]
        
        return JSONResponse({
            "success": True,
            "doubles": doubles,
            "total": len(doubles),
            "profile_code": user_code
        })
        
    except Exception as e:
        logger.error(f"❌ Error in find_doubles: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "doubles": []}
        )


@api_app.get("/api/notification/settings")
async def get_notification_settings(user_id: int):
    """Получить настройки уведомлений пользователя"""
    try:
        user_id = int(user_id)
        
        # Получаем настройки из БД или памяти
        user_info = user_data.get(user_id, {})
        notification_settings = user_info.get('notification_settings', {})
        
        return JSONResponse({
            "success": True,
            "settings": {
                "push_enabled": notification_settings.get('push_enabled', True),
                "email_enabled": notification_settings.get('email_enabled', False),
                "daily_summary": notification_settings.get('daily_summary', True),
                "weekly_report": notification_settings.get('weekly_report', True),
                "challenge_reminders": notification_settings.get('challenge_reminders', True),
                "quiet_hours_start": notification_settings.get('quiet_hours_start', 22),
                "quiet_hours_end": notification_settings.get('quiet_hours_end', 8)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_notification_settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/notification/vapid-key")
async def get_vapid_key():
    """Получить VAPID ключ для push-уведомлений"""
    try:
        # Пока возвращаем заглушку
        # В будущем нужно будет сгенерировать реальный VAPID ключ
        return JSONResponse({
            "success": True,
            "public_key": "BDc3ZqHx8YzW2XkL9mNpQrSvTyUwIeJfKgLhMiNjOkPlQmRnSoTpUqVrWsXtYuZvAxByCzD"
        })
    except Exception as e:
        logger.error(f"❌ Error in get_vapid_key: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/notification/history")
async def get_notification_history(user_id: int, limit: int = 20):
    """Получить историю уведомлений"""
    try:
        user_id = int(user_id)
        
        # Получаем историю из БД
        user_info = user_data.get(user_id, {})
        notifications = user_info.get('notifications', [])
        
        # Если нет истории, возвращаем заглушку
        if not notifications:
            notifications = [
                {
                    "id": 1,
                    "title": "Добро пожаловать!",
                    "body": "Рады видеть вас в приложении",
                    "type": "welcome",
                    "read": True,
                    "created_at": datetime.now().isoformat()
                }
            ]
        
        return JSONResponse({
            "success": True,
            "notifications": notifications[:limit],
            "unread_count": sum(1 for n in notifications if not n.get('read', False))
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_notification_history: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "notifications": []}
        )


@api_app.post("/api/notification/mark-read")
async def mark_notification_read(request: Request):
    """Отметить уведомление как прочитанное"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        notification_id = data.get('notification_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        
        # Обновляем статус в памяти
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'notifications' not in user_data[user_id]:
            user_data[user_id]['notifications'] = []
        
        for n in user_data[user_id]['notifications']:
            if n.get('id') == notification_id:
                n['read'] = True
                break
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"❌ Error in mark_notification_read: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/notification/update-settings")
async def update_notification_settings(request: Request):
    """Обновить настройки уведомлений"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        settings = data.get('settings', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['notification_settings'] = settings
        
        # Сохраняем в БД
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"❌ Error in update_notification_settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# ДОПОЛНИТЕЛЬНЫЙ ЭНДПОИНТ ДЛЯ ПРИНУДИТЕЛЬНОЙ ЗАГРУЗКИ ПОЛЬЗОВАТЕЛЯ
# ============================================

@api_app.post("/api/force-load-user")
async def force_load_user(request: Request):
    """Принудительно загружает пользователя из БД"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return JSONResponse({"success": False, "error": "user_id required"})
        
        user_id = int(user_id)
        
        # Проверяем, есть ли пользователь в памяти
        if user_id in user_data:
            logger.info(f"✅ Пользователь {user_id} уже в памяти")
            return JSONResponse({
                "success": True,
                "message": "Пользователь уже в памяти",
                "has_profile": bool(user_data[user_id].get('profile_data')),
                "profile_code": user_data[user_id].get('profile_data', {}).get('display_name')
            })
        
        # Пытаемся загрузить из БД
        try:
            async with db.get_connection() as conn:
                # Проверяем, есть ли пользователь в БД
                user_row = await conn.fetchrow(
                    "SELECT user_id, first_name, username FROM fredi_users WHERE user_id = $1",
                    user_id
                )
                
                if not user_row:
                    logger.warning(f"⚠️ Пользователь {user_id} не найден в БД")
                    return JSONResponse({
                        "success": False,
                        "message": "Пользователь не найден в БД",
                        "exists": False
                    })
                
                # Сохраняем имя
                user_names[user_id] = user_row['first_name'] or user_row['username'] or f"user_{user_id}"
                
                # Загружаем контекст
                context_row = await conn.fetchrow(
                    "SELECT * FROM fredi_user_contexts WHERE user_id = $1",
                    user_id
                )
                
                if context_row:
                    from models import UserContext
                    context = UserContext(user_id)
                    context.name = context_row.get('name')
                    context.age = context_row.get('age')
                    context.gender = context_row.get('gender')
                    context.city = context_row.get('city')
                    context.communication_mode = context_row.get('communication_mode', 'coach')
                    user_contexts[user_id] = context
                    logger.info(f"📦 Контекст загружен для {user_id}")
                
                # Загружаем данные
                data_row = await conn.fetchrow(
                    "SELECT data FROM fredi_user_data WHERE user_id = $1",
                    user_id
                )
                
                if data_row:
                    user_data_raw = data_row['data']
                    if isinstance(user_data_raw, str):
                        user_data_raw = json.loads(user_data_raw)
                    user_data[user_id] = user_data_raw
                    logger.info(f"📊 Данные загружены для {user_id}")
                
                logger.info(f"✅ Пользователь {user_id} успешно загружен из БД")
                
                return JSONResponse({
                    "success": True,
                    "message": "Пользователь загружен из БД",
                    "has_profile": bool(user_data.get(user_id, {}).get('profile_data')),
                    "profile_code": user_data.get(user_id, {}).get('profile_data', {}).get('display_name'),
                    "test_completed": user_data.get(user_id, {}).get('test_completed', False)
                })
                
        except Exception as db_error:
            logger.error(f"❌ Ошибка БД: {db_error}")
            return JSONResponse({
                "success": False,
                "error": f"Ошибка базы данных: {str(db_error)}"
            })
        
    except Exception as e:
        logger.error(f"❌ Error in force_load_user: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

if __name__ == "__main__":
    main()
