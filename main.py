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

# Настройка логирования — ВСЕ логи в stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
import fcntl
import socket
import asyncio
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# ============================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================
print('✅ Подключаем реальную PostgreSQL БД...')

# ========== ИМПОРТЫ ДЛЯ FASTAPI ==========
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import requests
# =========================================
from confinement_model import ConfinementModel9
from loop_analyzer import LoopAnalyzer
from key_confinement import KeyConfinementDetector
from intervention_library import InterventionLibrary
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring

# ========== ИМПОРТЫ ДЛЯ БАЗЫ ДАННЫХ ==========
from db_instance import (
    db, db_loop_manager, init_db, close_db,
    ensure_db_connection, execute_with_retry,
    load_user_from_db, save_telegram_user, save_user,
    save_user_to_db, log_event,
    save_psychologist_thought, get_psychologist_thought,
    get_user_goals, save_goal
)
from db_sync import sync_db
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
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ (ВРЕМЕННО ОТКЛЮЧЕНО)
# ============================================

async def init_database():
    """Инициализация базы данных"""
    try:
        result = await init_db()
        if result:
            logger.info("✅ PostgreSQL БД подключена")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        logger.warning("⚠️ Продолжаем без БД — данные в памяти")
        return False

async def load_all_users_from_db():
    """Загрузка активных пользователей из БД при старте"""
    try:
        if not db_loop_manager.is_ready():
            logger.warning("⚠️ БД не готова для загрузки пользователей")
            return
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT u.user_id, u.first_name, u.username,
                       ud.data as user_data,
                       uc.communication_mode, uc.name, uc.city,
                       uc.age, uc.gender
                FROM fredi_users u
                LEFT JOIN fredi_user_data ud ON u.user_id = ud.user_id
                LEFT JOIN fredi_user_contexts uc ON u.user_id = uc.user_id
                WHERE u.last_activity > NOW() - INTERVAL '30 days'
                ORDER BY u.last_activity DESC
                LIMIT 100
            """)
            loaded = 0
            for row in rows:
                uid = row['user_id']
                if row['first_name']:
                    user_names[uid] = row['first_name']
                if row['user_data']:
                    data = row['user_data'] if isinstance(row['user_data'], dict) else json.loads(row['user_data'])
                    user_data[uid] = data
                if uid not in user_contexts:
                    ctx = UserContext(uid)
                    if row['name']:              ctx.name = row['name']
                    if row['city']:              ctx.city = row['city']
                    if row['age']:               ctx.age = row['age']
                    if row['gender']:            ctx.gender = row['gender']
                    if row['communication_mode']:
                        ctx.communication_mode = row['communication_mode']
                    user_contexts[uid] = ctx
                loaded += 1
            logger.info(f"✅ Загружено {loaded} пользователей из БД")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователей: {e}")

async def periodic_save_to_db():
    """Периодическое сохранение всех пользователей в БД каждые 5 минут"""
    while True:
        await asyncio.sleep(300)
        try:
            if not db_loop_manager.is_ready():
                continue
            saved = 0
            for uid in list(user_data.keys()):
                try:
                    save_user_to_db(uid)
                    saved += 1
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения {uid}: {e}")
            if saved > 0:
                logger.info(f"💾 Периодически сохранено {saved} пользователей")
        except Exception as e:
            logger.error(f"❌ Ошибка periodic_save: {e}")

async def periodic_cleanup_db():
    """Очистка старых данных раз в сутки"""
    while True:
        await asyncio.sleep(86400)
        try:
            if db_loop_manager.is_ready():
                await db.cleanup_old_data(days=30)
                logger.info("🧹 Очистка старых данных выполнена")
        except Exception as e:
            logger.error(f"❌ Ошибка cleanup: {e}")

async def keep_db_alive():
    """Пинг БД каждые 10 минут чтобы не разрывалось соединение"""
    while True:
        await asyncio.sleep(600)
        try:
            if db_loop_manager.is_ready():
                async with db.get_connection() as conn:
                    await conn.execute("SELECT 1")
        except Exception as e:
            logger.warning(f"⚠️ keep_db_alive: {e}")

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
        
        # Планируем через единый event loop менеджера БД,
        # чтобы избежать "Event loop is closed" / "Future attached to a different loop"
        try:
            from db_instance import db_loop_manager
            if db_loop_manager.is_ready():
                asyncio.run_coroutine_threadsafe(
                    generate_profile_interpretation_async(user_id),
                    db_loop_manager.loop
                )
            else:
                logger.warning("⚠️ db_loop_manager не готов для генерации профиля")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования генерации профиля: {e}")
            import traceback
            traceback.print_exc()
        
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
            
            # 👇👇👇 ДОБАВИТЬ СОХРАНЕНИЕ В ТАБЛИЦУ МЫСЛЕЙ 👇👇👇
            sync_db.save_psychologist_thought(
                user_id=user_id,
                thought_text=ai_profile,
                thought_type='profile_description',
                thought_summary=ai_profile[:200],
                metadata={
                    'profile_code': user_info.get('profile_data', {}).get('display_name'),
                    'vectors': user_info.get('behavioral_levels'),
                    'perception_type': user_info.get('perception_type'),
                    'thinking_level': user_info.get('thinking_level')
                }
            )
            
            logger.info(f"✅ Интерпретация для пользователя {user_id} сгенерирована и сохранена в БД")
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
            
            # 👇👇👇 СОХРАНЯЕМ И FALLBACK ПРОФИЛЬ 👇👇👇
            sync_db.save_psychologist_thought(
                user_id=user_id,
                thought_text=fallback_profile,
                thought_type='profile_description',
                thought_summary=fallback_profile[:200],
                metadata={
                    'profile_code': profile.get('display_name'),
                    'is_fallback': True
                }
            )
            
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
    try:
        save_telegram_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        log_event(message.from_user.id, 'start', {'username': message.from_user.username})
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сохранить пользователя: {e}")
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
    try:
        from db_instance import db_loop_manager
        if db_loop_manager.is_ready():
            asyncio.run_coroutine_threadsafe(
                show_weekend_ideas(message, user_id),
                db_loop_manager.loop
            )
        else:
            logger.warning("⚠️ db_loop_manager не готов для weekend ideas")
    except Exception as e:
        logger.error(f"❌ Ошибка планирования weekend ideas: {e}")

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
    
    # Через единый event loop менеджера БД
    try:
        from db_instance import db_loop_manager
        if db_loop_manager.is_ready():
            asyncio.run_coroutine_threadsafe(
                handle_voice_message(message),
                db_loop_manager.loop
            )
        else:
            logger.warning("⚠️ db_loop_manager не готов для голосового сообщения")
    except Exception as e:
        logger.error(f"❌ Ошибка планирования голосового сообщения: {e}")

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
    try:
        from db_instance import db_loop_manager
        if db_loop_manager.is_ready():
            asyncio.run_coroutine_threadsafe(
                process_custom_goal_async(message, user_id, text),
                db_loop_manager.loop
            )
        else:
            logger.warning("⚠️ db_loop_manager не готов для обработки цели")
    except Exception as e:
        logger.error(f"❌ Ошибка планирования цели: {e}")

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

def remove_webhook_subscription():
    """Удаляет webhook-подписку чтобы polling работал."""
    max_token = os.environ.get("MAX_TOKEN", "").strip()
    bot_url = os.environ.get("BOT_URL", "https://max-bot-1-ywpz.onrender.com").strip()
    if not max_token:
        print("⚠️ MAX_TOKEN не найден, пропускаем удаление webhook")
        return
    try:
        import requests as req
        webhook_url = f"{bot_url}/webhook"
        # Max API: url передаётся как query-параметр
        resp = req.delete(
            f"https://platform-api.max.ru/subscriptions?url={webhook_url}",
            headers={"Authorization": max_token},
            timeout=15,
        )
        print(f"🗑 Webhook DELETE: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"🗑 Webhook unsubscribe error: {e}")


def setup_bot_started_webhook():
    """Регистрирует webhook для bot_started (deep-link) событий. ОТКЛЮЧЕНО — конфликтует с polling."""
    max_token = os.environ.get("MAX_TOKEN", "").strip()
    bot_url = os.environ.get("BOT_URL", "https://max-bot-1-ywpz.onrender.com").strip()
    if not max_token:
        return
    try:
        import requests as req
        resp = req.post(
            "https://platform-api.max.ru/subscriptions",
            json={"url": f"{bot_url}/webhook", "update_types": ["bot_started"]},
            headers={"Authorization": max_token},
            timeout=15,
        )
        logger.info(f"🪞 Webhook subscription: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.error(f"🪞 Webhook subscription error: {e}")


def run_fastapi():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск FastAPI на порту {port}")
    # bot_started обрабатывается Frederick бэкендом через его webhook
    # Max бот использует только polling для message_created и message_callback
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
            except Exception:
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
    
    # bot_started → Frederick backend webhook
    # message_created + message_callback → polling здесь
    print("✅ Запускаем polling (bot_started → Frederick backend)...")

    is_render = os.environ.get('RENDER') is not None
    retry_count = 0
    max_retries = 5 if not is_render else 1

    try:
        while retry_count < max_retries:
            try:
                bot.polling(allowed_updates=["message_created", "message_callback"])
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
# API ЭНДПОИНТЫ ДЛЯ МЫСЛЕЙ ПСИХОЛОГА
# ============================================

@api_app.get("/api/psychologist-thoughts")
async def get_psychologist_thoughts(
    user_id: int, 
    thought_type: str = None,
    limit: int = 10,
    include_inactive: bool = False
):
    """
    Получить историю мыслей психолога
    """
    try:
        user_id = int(user_id)
        
        if include_inactive:
            thoughts = sync_db.get_all_psychologist_thoughts(user_id, limit, include_inactive)
        else:
            if thought_type:
                thoughts = sync_db.get_psychologist_thought_history(user_id, thought_type, limit)
            else:
                thoughts = sync_db.get_psychologist_thought_history(user_id, None, limit)
        
        stats = sync_db.get_psychologist_thoughts_stats(user_id)
        
        return JSONResponse({
            "success": True,
            "thoughts": thoughts,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_psychologist_thoughts: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "thoughts": []}
        )


@api_app.get("/api/psychologist-thoughts/{thought_id}")
async def get_psychologist_thought_by_id(thought_id: int):
    """
    Получить конкретную мысль психолога по ID
    """
    try:
        thoughts = sync_db.get_all_psychologist_thoughts(0, 1000, True)
        for thought in thoughts:
            if thought.get('id') == thought_id:
                return JSONResponse({
                    "success": True,
                    "thought": thought
                })
        
        return JSONResponse({
            "success": False,
            "error": "Thought not found"
        }, status_code=404)
        
    except Exception as e:
        logger.error(f"❌ Error in get_psychologist_thought_by_id: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.put("/api/psychologist-thoughts/{thought_id}")
async def update_psychologist_thought(thought_id: int, request: Request):
    """
    Обновить мысль психолога
    """
    try:
        data = await request.json()
        
        result = sync_db.update_psychologist_thought(
            thought_id=thought_id,
            thought_text=data.get('thought_text'),
            thought_summary=data.get('thought_summary'),
            is_active=data.get('is_active'),
            metadata=data.get('metadata')
        )
        
        return JSONResponse({
            "success": result,
            "message": "Мысль обновлена" if result else "Не удалось обновить мысль"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in update_psychologist_thought: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.delete("/api/psychologist-thoughts/{thought_id}")
async def delete_psychologist_thought(thought_id: int):
    """
    Удалить мысль психолога
    """
    try:
        result = sync_db.delete_psychologist_thought(thought_id)
        
        return JSONResponse({
            "success": result,
            "message": "Мысль удалена" if result else "Не удалось удалить мысль"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in delete_psychologist_thought: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/psychologist-thoughts/generate")
async def generate_psychologist_thought_api(request: Request):
    """
    Сгенерировать новую мысль психолога
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        test_result_id = data.get('test_result_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('profile_data') and not user_info.get('behavioral_levels'):
            return JSONResponse({
                "success": False,
                "error": "Сначала пройдите тест"
            })
        
        from services import generate_psychologist_thought
        thought = await generate_psychologist_thought(user_id, user_info)
        
        if thought:
            thought_id = sync_db.save_psychologist_thought(
                user_id=user_id,
                thought_text=thought,
                test_result_id=test_result_id,
                thought_type='psychologist_thought'
            )
            
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['psychologist_thought'] = thought
            
            return JSONResponse({
                "success": True,
                "thought": thought,
                "thought_id": thought_id
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Не удалось сгенерировать мысль"
            })
        
    except Exception as e:
        logger.error(f"❌ Error in generate_psychologist_thought_api: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/psychologist-thoughts/stats/{user_id}")
async def get_psychologist_thoughts_stats_api(user_id: int):
    """
    Получить статистику по мыслям психолога
    """
    try:
        user_id = int(user_id)
        stats = sync_db.get_psychologist_thoughts_stats(user_id)
        
        return JSONResponse({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_psychologist_thoughts_stats_api: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
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
        logger.info(f"📨 Webhook: {data}")

        update_type = data.get("update_type", "")

        # Обработка bot_started с mirror payload
        if update_type == "bot_started":
            payload = data.get("payload", "")
            user_info = data.get("user", {})
            user_id = user_info.get("user_id")
            user_name = user_info.get("name", "Друг")
            logger.info(f"🪞 bot_started: user={user_id}, payload={payload}, name={user_name}")

            if user_id:
                # Сохраняем mirror_code если есть
                if payload and payload.startswith("mirror_"):
                    from state import user_data
                    if user_id not in user_data:
                        user_data[user_id] = {}
                    user_data[user_id]["mirror_code"] = payload
                    logger.info(f"🪞 Mirror code saved via webhook: user={user_id}, code={payload}")

                    # Отправляем приветствие через Max API
                    try:
                        requests.post(
                            f"https://api.max.ru/bot/{MAX_TOKEN}/sendMessage",
                            json={"chat_id": user_id, "text": (
                                f"🪞 {user_name}, привет! Тебя пригласили пройти психологический тест от Фреди.\n\n"
                                f"⏱ 15 минут — и ты узнаешь свой профиль, а друг увидит сравнение.\n\n"
                                f"👇 Напиши /start чтобы начать!"
                            )},
                            timeout=10
                        )
                        logger.info(f"🪞 Mirror welcome sent to user {user_id}")
                    except Exception as e:
                        logger.error(f"🪞 Failed to send mirror welcome: {e}")

                elif not payload or not payload.startswith("web_"):
                    # Обычный bot_started без payload — отправляем приветствие
                    try:
                        requests.post(
                            f"https://api.max.ru/bot/{MAX_TOKEN}/sendMessage",
                            json={"chat_id": user_id, "text": (
                                f"👋 {user_name}, привет! Я Фреди — виртуальный психолог.\n\n"
                                f"Напиши /start чтобы начать!"
                            )},
                            timeout=10
                        )
                    except Exception as e:
                        logger.error(f"Failed to send welcome: {e}")

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

# ============================================
# API ЭНДПОИНТЫ ДЛЯ КОНФАЙНТМЕНТ-МОДЕЛИ
# ============================================

from confinement_model import ConfinementModel9, VECTORS, LEVEL_PROFILES
import asyncio
import threading

@api_app.get("/api/confinement-model")
async def get_confinement_model(user_id: int):
    """
    Получить 9-элементную конфайнтмент-модель пользователя
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Проверяем, есть ли уже построенная модель
        existing_model = user_info.get('confinement_model')
        
        if existing_model:
            # Восстанавливаем модель из словаря
            if isinstance(existing_model, dict):
                model = ConfinementModel9.from_dict(existing_model)
            else:
                model = existing_model
        else:
            # Строим новую модель
            scores = {}
            for k in VECTORS:
                levels = user_info.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            
            # Получаем историю диалогов
            history = user_info.get('history', [])
            
            # Строим модель
            model = ConfinementModel9(user_id)
            model.build_from_profile(scores, history)
            
            # Сохраняем в user_data
            user_info['confinement_model'] = model.to_dict()
            sync_db.save_user_to_db(user_id)
        
        # Формируем ответ для фронтенда
        response = {
            "success": True,
            "user_id": user_id,
            "elements": {},
            "links": model.links,
            "loops": model.loops,
            "key_confinement": model.key_confinement,
            "is_closed": model.is_closed,
            "closure_score": model.closure_score,
            "vectors": {
                k: {
                    "name": VECTORS.get(k, {}).get('name', k),
                    "emoji": VECTORS.get(k, {}).get('emoji', '🔍'),
                    "level": model.elements.get(pos).level if model.elements.get(pos) else 3
                }
                for pos, k in [(2, 'СБ'), (3, 'ТФ'), (4, 'УБ')]
                if model.elements.get(pos)
            }
        }
        
        # Добавляем каждый элемент
        for i in range(1, 10):
            elem = model.elements.get(i)
            if elem:
                response["elements"][i] = {
                    "id": elem.id,
                    "name": elem.name,
                    "description": elem.description,
                    "type": elem.element_type,
                    "vector": elem.vector,
                    "level": elem.level,
                    "archetype": elem.archetype,
                    "strength": elem.strength,
                    "vak": elem.vak,
                    "causes": elem.causes,
                    "caused_by": elem.caused_by,
                    "amplifies": elem.amplifies
                }
        
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"❌ Error in get_confinement_model: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/confinement-model/rebuild")
async def rebuild_confinement_model(request: Request):
    """
    Принудительно перестроить конфайнтмент-модель
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Строим новую модель
        scores = {}
        for k in VECTORS:
            levels = user_info.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        history = user_info.get('history', [])
        
        model = ConfinementModel9(user_id)
        model.build_from_profile(scores, history)
        
        # Сохраняем
        user_info['confinement_model'] = model.to_dict()
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": "Модель перестроена",
            "closure_score": model.closure_score,
            "is_closed": model.is_closed
        })
        
    except Exception as e:
        logger.error(f"❌ Error in rebuild_confinement_model: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/goals/with-confinement")
async def get_goals_with_confinement(user_id: int, mode: str = "coach"):
    """
    Получить цели с учётом конфайнтмент-модели
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Получаем конфайнтмент-модель
        existing_model = user_info.get('confinement_model')
        if existing_model:
            if isinstance(existing_model, dict):
                model = ConfinementModel9.from_dict(existing_model)
            else:
                model = existing_model
        else:
            # Строим модель
            scores = {}
            for k in VECTORS:
                levels = user_info.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            
            model = ConfinementModel9(user_id)
            model.build_from_profile(scores, [])
        
        # Получаем профиль
        profile_data = user_info.get("profile_data", {})
        profile_code = profile_data.get("display_name", "СБ-4_ТФ-4_УБ-4_ЧВ-4")
        
        scores = {
            "СБ": profile_data.get("sb_level", 4),
            "ТФ": profile_data.get("tf_level", 4),
            "УБ": profile_data.get("ub_level", 4),
            "ЧВ": profile_data.get("chv_level", 4)
        }
        
        weakest = min(scores.items(), key=lambda x: x[1])[0] if scores else "СБ"
        
        # База целей
        goals_db = {
            "coach": {
                "weak": {
                    "СБ": [
                        {"id": "fear_work", "name": "Проработать страхи", "time": "3-4 недели", "difficulty": "medium", "emoji": "🛡️"},
                        {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "emoji": "🔒"}
                    ],
                    "ТФ": [
                        {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "emoji": "💰"},
                        {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "emoji": "📈"}
                    ],
                    "УБ": [
                        {"id": "meaning", "name": "Найти смысл", "time": "4-6 недель", "difficulty": "hard", "emoji": "🎯"},
                        {"id": "system_thinking", "name": "Развить системное мышление", "time": "3-5 недель", "difficulty": "medium", "emoji": "🧩"}
                    ],
                    "ЧВ": [
                        {"id": "relations", "name": "Улучшить отношения", "time": "4-6 недель", "difficulty": "hard", "emoji": "💕"},
                        {"id": "attachment", "name": "Проработать привязанность", "time": "5-7 недель", "difficulty": "hard", "emoji": "🪢"}
                    ]
                },
                "general": [
                    {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "emoji": "🌟"},
                    {"id": "balance", "name": "Обрести баланс", "time": "4-6 недель", "difficulty": "medium", "emoji": "⚖️"}
                ]
            },
            "psychologist": {
                "weak": {
                    "СБ": [
                        {"id": "fear_origin", "name": "Найти источник страхов", "time": "4-6 недель", "difficulty": "hard", "emoji": "🔍"},
                        {"id": "trauma", "name": "Проработать травму", "time": "6-8 недель", "difficulty": "hard", "emoji": "🩹"}
                    ],
                    "ТФ": [
                        {"id": "money_psychology", "name": "Понять психологию денег", "time": "4-5 недель", "difficulty": "medium", "emoji": "🧠💰"},
                        {"id": "worth", "name": "Проработать чувство ценности", "time": "5-7 недель", "difficulty": "hard", "emoji": "💎"}
                    ],
                    "УБ": [
                        {"id": "core_beliefs", "name": "Найти глубинные убеждения", "time": "5-7 недель", "difficulty": "hard", "emoji": "🏛️"},
                        {"id": "schemas", "name": "Проработать жизненные сценарии", "time": "6-8 недель", "difficulty": "hard", "emoji": "📜"}
                    ],
                    "ЧВ": [
                        {"id": "attachment_style", "name": "Проработать тип привязанности", "time": "6-8 недель", "difficulty": "hard", "emoji": "🪢"},
                        {"id": "inner_child", "name": "Исцелить внутреннего ребёнка", "time": "5-7 недель", "difficulty": "hard", "emoji": "🧸"}
                    ]
                },
                "general": [
                    {"id": "self_discovery", "name": "Глубинное самопознание", "time": "7-9 недель", "difficulty": "hard", "emoji": "🔮"},
                    {"id": "healing", "name": "Исцеление внутренних ран", "time": "8-10 недель", "difficulty": "hard", "emoji": "💖"}
                ]
            },
            "trainer": {
                "weak": {
                    "СБ": [
                        {"id": "assertiveness", "name": "Развить ассертивность", "time": "3-4 недели", "difficulty": "medium", "emoji": "💪"},
                        {"id": "conflict_skills", "name": "Освоить навыки конфликта", "time": "4-5 недель", "difficulty": "medium", "emoji": "⚔️"}
                    ],
                    "ТФ": [
                        {"id": "money_skills", "name": "Освоить навыки управления деньгами", "time": "3-4 недели", "difficulty": "easy", "emoji": "💰"},
                        {"id": "income_skills", "name": "Навыки увеличения дохода", "time": "4-6 недель", "difficulty": "medium", "emoji": "📊"}
                    ],
                    "УБ": [
                        {"id": "thinking_tools", "name": "Освоить инструменты мышления", "time": "4-5 недель", "difficulty": "medium", "emoji": "🧠"},
                        {"id": "decision_making", "name": "Навыки принятия решений", "time": "3-4 недели", "difficulty": "easy", "emoji": "✅"}
                    ],
                    "ЧВ": [
                        {"id": "communication_skills", "name": "Развить навыки общения", "time": "3-4 недели", "difficulty": "easy", "emoji": "💬"},
                        {"id": "negotiation", "name": "Навыки переговоров", "time": "4-6 недель", "difficulty": "medium", "emoji": "🤝"}
                    ]
                },
                "general": [
                    {"id": "productivity", "name": "Повысить продуктивность", "time": "4-6 недель", "difficulty": "medium", "emoji": "⚡"},
                    {"id": "habit_building", "name": "Сформировать полезные привычки", "time": "3-5 недель", "difficulty": "easy", "emoji": "🔄"}
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
        
        # ✅ ИСПРАВЛЕНО: проверяем, что key_confinement существует и является словарём
        if model.key_confinement and isinstance(model.key_confinement, dict):
            key_elem = model.key_confinement.get('element')
            # Проверяем, что key_elem — это объект с атрибутом name
            if key_elem and hasattr(key_elem, 'name'):
                goals.insert(0, {
                    "id": "key_confinement_work",
                    "name": f"Работа с ключевым ограничением: {key_elem.name[:30]}",
                    "time": "3-5 недель",
                    "difficulty": "hard",
                    "emoji": "🔐",
                    "description": model.key_confinement.get('description', 'Работа с главным ограничением системы'),
                    "is_priority": True
                })
            elif isinstance(key_elem, dict) and key_elem.get('name'):
                # Если key_elem — словарь
                goals.insert(0, {
                    "id": "key_confinement_work",
                    "name": f"Работа с ключевым ограничением: {key_elem.get('name', '')[:30]}",
                    "time": "3-5 недель",
                    "difficulty": "hard",
                    "emoji": "🔐",
                    "description": model.key_confinement.get('description', 'Работа с главным ограничением системы'),
                    "is_priority": True
                })
        
        return JSONResponse({
            "success": True,
            "goals": goals[:7],
            "profile_code": profile_code,
            "key_confinement": model.key_confinement,
            "closure_score": model.closure_score
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_goals_with_confinement: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/route/build-with-confinement")
async def build_route_with_confinement(request: Request):
    """
    Построить маршрут с учётом конфайнтмент-модели
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        goal = data.get('goal', {})
        
        if not user_id or not goal:
            raise HTTPException(status_code=400, detail="user_id and goal required")
        
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Получаем конфайнтмент-модель
        existing_model = user_info.get('confinement_model')
        if existing_model:
            if isinstance(existing_model, dict):
                model = ConfinementModel9.from_dict(existing_model)
            else:
                model = existing_model
        else:
            # Строим модель
            scores = {}
            for k in VECTORS:
                levels = user_info.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            
            model = ConfinementModel9(user_id)
            model.build_from_profile(scores, [])
        
        # Получаем режим
        context = user_contexts.get(user_id)
        mode = context.communication_mode if context else "coach"
        
        # Формируем промпт с учётом конфайнтмент-модели
        profile_code = user_info.get('profile_data', {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
        
        # Строим текст модели для промпта
        model_text = ""
        if model.key_confinement:
            key_elem = model.key_confinement.get('element')
            if key_elem:
                model_text += f"\n🔐 **КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ:** {key_elem.name} - {model.key_confinement.get('description', '')[:100]}\n"
        
        if model.loops:
            main_loop = model.loops[0] if model.loops else None
            if main_loop:
                model_text += f"\n🔄 **ОСНОВНАЯ ПЕТЛЯ:** {main_loop.get('description', '')}\n"
        
        from services import call_deepseek
        
        system_prompt = f"""Ты — Фреди, виртуальный психолог. Помоги пользователю построить маршрут к его цели с учётом его психологического профиля и выявленных ограничений.

ПРОФИЛЬ: {profile_code}

{model_text}

Твоя задача — создать пошаговый маршрут из 3-4 этапов, который:
1. Учитывает ключевое ограничение пользователя
2. Помогает разорвать петлю самоподдержания
3. Даёт конкретные, выполнимые шаги

Используй стиль, соответствующий режиму {mode}."""
        
        prompt = f"""
Цель пользователя: {goal.get('name', 'цель')}
Время: {goal.get('time', '3-6 месяцев')}
Сложность: {goal.get('difficulty', 'medium')}

Создай пошаговый маршрут:

📍 ЭТАП 1: [НАЗВАНИЕ]
   • Что делаем: [конкретные действия]
   • 📝 Домашнее задание: [задание между сессиями]
   • ✅ Критерий выполнения: [как понять, что этап пройден]

📍 ЭТАП 2: [НАЗВАНИЕ]
   • Что делаем: [конкретные действия]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]

📍 ЭТАП 3: [НАЗВАНИЕ]
   • Что делаем: [конкретные действия]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]

📍 ЭТАП 4: [НАЗВАНИЕ] (если нужно для закрепления)
   • Что делаем: [конкретные действия]
   • 📝 Домашнее задание: [задание]
   • ✅ Критерий: [критерий]
"""
        
        response = await call_deepseek(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.7
        )
        
        if response:
            # Сохраняем маршрут
            route = {
                "full_text": response,
                "steps": response.split("\n\n"),
                "goal": goal,
                "mode": mode,
                "created_at": datetime.now().isoformat()
            }
            
            if 'routes' not in user_info:
                user_info['routes'] = []
            user_info['routes'].append(route)
            sync_db.save_user_to_db(user_id)
            
            return JSONResponse({
                "success": True,
                "route": route,
                "key_confinement": model.key_confinement
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Не удалось сгенерировать маршрут"
            })
        
    except Exception as e:
        logger.error(f"❌ Error in build_route_with_confinement: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/reality-check/with-confinement")
async def reality_check_with_confinement(request: Request):
    """
    Проверка реальности с учётом конфайнтмент-модели
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        goal = data.get('goal', {})
        life_context = data.get('life_context', {})
        goal_context = data.get('goal_context', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Получаем конфайнтмент-модель
        existing_model = user_info.get('confinement_model')
        if existing_model:
            if isinstance(existing_model, dict):
                model = ConfinementModel9.from_dict(existing_model)
            else:
                model = existing_model
        else:
            scores = {}
            for k in VECTORS:
                levels = user_info.get("behavioral_levels", {}).get(k, [])
                scores[k] = sum(levels) / len(levels) if levels else 3.0
            model = ConfinementModel9(user_id)
            model.build_from_profile(scores, [])
        
        # Теоретические требования для цели
        theoretical_time = 10  # часов в неделю по умолчанию
        theoretical_energy = 7  # уровень энергии 1-10
        
        if goal.get('difficulty') == 'easy':
            theoretical_time = 5
            theoretical_energy = 5
        elif goal.get('difficulty') == 'hard':
            theoretical_time = 15
            theoretical_energy = 8
        
        # Доступные ресурсы
        available_time = goal_context.get('time_per_week', 5)
        available_energy = life_context.get('energy_level', 5)
        
        # Расчёт дефицита
        time_deficit = max(0, (theoretical_time - available_time) / theoretical_time * 100) if theoretical_time > 0 else 0
        energy_deficit = max(0, (theoretical_energy - available_energy) / theoretical_energy * 100) if theoretical_energy > 0 else 0
        
        total_deficit = (time_deficit + energy_deficit) / 2
        
        # Учитываем конфайнтмент-модель
        if model.is_closed:
            total_deficit += 15  # закрытая система требует больше ресурсов
        if model.key_confinement:
            total_deficit += 10  # ключевое ограничение увеличивает сложность
        
        total_deficit = min(total_deficit, 100)
        
        # Статус
        if total_deficit < 30:
            status = "✅ ДОСТИЖИМО"
            status_emoji = "✅"
            recommendation = "Цель реалистична. Начните с первого шага."
        elif total_deficit < 60:
            status = "⚠️ СЛОЖНО, НО ВОЗМОЖНО"
            status_emoji = "⚠️"
            recommendation = "Цель достижима, но потребует усилий. Рекомендуется увеличить срок или снизить планку."
        else:
            status = "❌ НЕРЕАЛИСТИЧНО"
            status_emoji = "❌"
            recommendation = "Цель требует пересмотра. Увеличьте срок или выберите более простую цель."
        
        # Добавляем рекомендацию на основе конфайнтмент-модели
        if model.key_confinement:
            key_elem = model.key_confinement.get('element')
            if key_elem:
                recommendation += f"\n\n🔐 **КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ:** {key_elem.name}. Работа с ним критически важна для достижения цели."
        
        return JSONResponse({
            "success": True,
            "deficit": round(total_deficit, 1),
            "status": status,
            "status_emoji": status_emoji,
            "recommendation": recommendation,
            "requirements": {
                "time_per_week": theoretical_time,
                "energy_level": theoretical_energy
            },
            "available": {
                "time_per_week": available_time,
                "energy_level": available_energy
            },
            "key_confinement": model.key_confinement
        })
        
    except Exception as e:
        logger.error(f"❌ Error in reality_check_with_confinement: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# ============================================
# API ЭНДПОИНТЫ ДЛЯ КОНФАЙНТМЕНТ-МОДЕЛИ И ГИПНОЗА
# ============================================

@api_app.get("/api/confinement/model/{user_id}/loops")
async def get_confinement_loops(user_id: int):
    """
    Получить петли конфайнтмент-модели
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        existing_model = user_info.get('confinement_model')
        if not existing_model:
            return JSONResponse({
                "success": False,
                "message": "Модель не построена"
            })
        
        if isinstance(existing_model, dict):
            model = ConfinementModel9.from_dict(existing_model)
        else:
            model = existing_model
        
        analyzer = LoopAnalyzer(model)
        loops = analyzer.analyze()
        
        return JSONResponse({
            "success": True,
            "loops": loops,
            "statistics": analyzer.get_statistics(),
            "strongest_loop": analyzer.get_strongest_loop(),
            "all_loops_summary": analyzer.get_all_loops_summary()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_confinement_loops: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/confinement/model/{user_id}/key-confinement")
async def get_key_confinement(user_id: int):
    """
    Получить ключевой конфайнтмент (главное ограничение)
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        existing_model = user_info.get('confinement_model')
        if not existing_model:
            return JSONResponse({
                "success": False,
                "message": "Модель не построена"
            })
        
        if isinstance(existing_model, dict):
            model = ConfinementModel9.from_dict(existing_model)
        else:
            model = existing_model
        
        analyzer = LoopAnalyzer(model)
        loops = analyzer.analyze()
        
        detector = KeyConfinementDetector(model, loops)
        key_confinement = detector.detect()
        all_confinements = detector.detect_all()
        
        # Получаем интервенцию для ключевого конфайнтмента
        intervention = None
        if key_confinement:
            lib = InterventionLibrary()
            intervention = lib.get_intervention_for_element(
                key_confinement['element_id'],
                vector=key_confinement['element'].vector if key_confinement['element'] else None,
                level=key_confinement['element'].level if key_confinement['element'] else None
            )
        
        return JSONResponse({
            "success": True,
            "key_confinement": key_confinement,
            "all_confinements": all_confinements,
            "intervention": intervention,
            "summary": detector.get_key_confinement_summary() if key_confinement else None,
            "break_points_summary": detector.get_break_points_summary()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_key_confinement: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/confinement/model/{user_id}/element/{element_id}")
async def get_confinement_element(user_id: int, element_id: int):
    """
    Получить конкретный элемент модели
    """
    try:
        user_id = int(user_id)
        element_id = int(element_id)
        user_info = user_data.get(user_id, {})
        
        existing_model = user_info.get('confinement_model')
        if not existing_model:
            return JSONResponse({
                "success": False,
                "message": "Модель не построена"
            })
        
        if isinstance(existing_model, dict):
            model = ConfinementModel9.from_dict(existing_model)
        else:
            model = existing_model
        
        element = model.elements.get(element_id)
        if not element:
            return JSONResponse({
                "success": False,
                "message": f"Элемент {element_id} не найден"
            })
        
        # Находим петли, в которые входит элемент
        analyzer = LoopAnalyzer(model)
        loops = analyzer.analyze()
        element_loops = analyzer.get_loops_by_element(element_id)
        
        return JSONResponse({
            "success": True,
            "element": {
                "id": element.id,
                "name": element.name,
                "description": element.description,
                "type": element.element_type,
                "vector": element.vector,
                "level": element.level,
                "archetype": element.archetype,
                "strength": element.strength,
                "vak": element.vak,
                "causes": element.causes,
                "caused_by": element.caused_by,
                "amplifies": element.amplifies
            },
            "loops": element_loops,
            "participation_count": len(element_loops)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_confinement_element: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/confinement/model/{user_id}/rebuild")
async def rebuild_confinement_model(user_id: int):
    """
    Принудительно перестроить конфайнтмент-модель
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Строим новую модель
        scores = {}
        for k in VECTORS:
            levels = user_info.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        history = user_info.get('history', [])
        
        model = ConfinementModel9(user_id)
        model.build_from_profile(scores, history)
        
        # Сохраняем
        user_info['confinement_model'] = model.to_dict()
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": "Модель перестроена",
            "closure_score": model.closure_score,
            "is_closed": model.is_closed,
            "key_confinement": model.key_confinement
        })
        
    except Exception as e:
        logger.error(f"❌ Error in rebuild_confinement_model: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/intervention/{element_id}")
async def get_intervention(element_id: int, user_id: int):
    """
    Получить интервенцию для элемента
    """
    try:
        user_id = int(user_id)
        element_id = int(element_id)
        user_info = user_data.get(user_id, {})
        
        existing_model = user_info.get('confinement_model')
        if not existing_model:
            return JSONResponse({
                "success": False,
                "message": "Модель не построена"
            })
        
        if isinstance(existing_model, dict):
            model = ConfinementModel9.from_dict(existing_model)
        else:
            model = existing_model
        
        element = model.elements.get(element_id)
        if not element:
            return JSONResponse({
                "success": False,
                "message": f"Элемент {element_id} не найден"
            })
        
        lib = InterventionLibrary()
        
        intervention = lib.get_intervention_for_element(
            element_id,
            vector=element.vector,
            level=element.level
        )
        
        daily_practice = lib.get_daily_practice(element_id)
        week_program = lib.get_program_for_week(element_id)
        
        # Получаем случайное упражнение и цитату
        random_exercise = lib.get_random_exercise()
        random_quote = lib.get_random_quote()
        
        return JSONResponse({
            "success": True,
            "element": {
                "id": element.id,
                "name": element.name,
                "description": element.description,
                "type": element.element_type,
                "vector": element.vector,
                "level": element.level
            },
            "intervention": intervention,
            "daily_practice": daily_practice,
            "week_program": week_program,
            "random_exercise": random_exercise,
            "random_quote": random_quote
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_intervention: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/hypno/process")
async def process_hypno(request: Request):
    """
    Получить гипнотический ответ на сообщение
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        text = data.get('text')
        mode = data.get('mode', 'psychologist')
        
        if not user_id or not text:
            raise HTTPException(status_code=400, detail="user_id and text required")
        
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        # Получаем контекст
        context_obj = user_contexts.get(user_id)
        
        # Получаем конфайнтмент-модель
        existing_model = user_info.get('confinement_model')
        if existing_model:
            if isinstance(existing_model, dict):
                model = ConfinementModel9.from_dict(existing_model)
            else:
                model = existing_model
        else:
            model = None
        
        # Собираем контекст
        context = {
            'mode': mode,
            'vector': user_info.get('profile_data', {}).get('dominant_vector'),
            'confinement_model': model.to_dict() if model else None,
            'key_confinement': model.key_confinement if model else None
        }
        
        hypno = HypnoOrchestrator()
        response = hypno.process(user_id, text, context)
        
        # Сохраняем в историю
        if 'hypno_history' not in user_info:
            user_info['hypno_history'] = []
        user_info['hypno_history'].append({
            'text': text,
            'response': response,
            'mode': mode,
            'timestamp': datetime.now().isoformat()
        })
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "response": response,
            "mode": mode
        })
        
    except Exception as e:
        logger.error(f"❌ Error in process_hypno: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/hypno/support")
async def get_hypno_support(request: Request):
    """
    Получить поддерживающий гипнотический ответ
    """
    try:
        data = await request.json()
        text = data.get('text', '')
        
        hypno = HypnoOrchestrator()
        response = hypno.get_support_response(text)
        
        return JSONResponse({
            "success": True,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_hypno_support: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/tale")
async def get_tale(issue: str = None):
    """
    Получить терапевтическую сказку
    """
    try:
        tales = TherapeuticTales()
        
        if issue:
            tale = tales.get_tale_for_issue(issue)
        else:
            # Случайная сказка
            tale_id = random.choice(tales.get_all_tales())
            tale = tales.get_tale_by_id(tale_id)
        
        return JSONResponse({
            "success": True,
            "tale": tale,
            "available_tales": tales.get_all_tales()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_tale: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/tale/{tale_id}")
async def get_tale_by_id(tale_id: str):
    """
    Получить конкретную сказку по ID
    """
    try:
        tales = TherapeuticTales()
        tale = tales.get_tale_by_id(tale_id)
        
        if not tale:
            return JSONResponse({
                "success": False,
                "message": f"Сказка {tale_id} не найдена"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "tale": tale
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_tale_by_id: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/anchor/{state}")
async def get_anchor(state: str, user_id: int = None):
    """
    Получить якорь для состояния
    """
    try:
        anchoring = Anchoring()
        
        if user_id:
            phrase = anchoring.get_anchor(state, user_id)
        else:
            phrase = anchoring.get_anchor(state)
        
        emoji = anchoring.get_emoji(state)
        
        return JSONResponse({
            "success": True,
            "state": state,
            "phrase": phrase,
            "emoji": emoji,
            "available_states": anchoring.get_all_states()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_anchor: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/anchor/set")
async def set_anchor(request: Request):
    """
    Установить персональный якорь
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        anchor_name = data.get('anchor_name')
        state = data.get('state')
        phrase = data.get('phrase')
        
        if not all([user_id, anchor_name, state, phrase]):
            raise HTTPException(status_code=400, detail="user_id, anchor_name, state, phrase required")
        
        user_id = int(user_id)
        
        anchoring = Anchoring()
        anchoring.set_anchor(user_id, anchor_name, state, phrase)
        
        # Сохраняем в БД
        user_info = user_data.get(user_id, {})
        if 'anchors' not in user_info:
            user_info['anchors'] = []
        user_info['anchors'].append({
            'name': anchor_name,
            'state': state,
            'phrase': phrase,
            'timestamp': datetime.now().isoformat()
        })
        sync_db.save_user_to_db(user_id)
        
        return JSONResponse({
            "success": True,
            "message": f"Якорь '{anchor_name}' установлен"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in set_anchor: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.post("/api/anchor/fire")
async def fire_anchor(request: Request):
    """
    Активировать якорь
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        anchor_name = data.get('anchor_name')
        
        if not user_id or not anchor_name:
            raise HTTPException(status_code=400, detail="user_id and anchor_name required")
        
        user_id = int(user_id)
        
        anchoring = Anchoring()
        phrase = anchoring.fire_anchor(user_id, anchor_name)
        
        if not phrase:
            return JSONResponse({
                "success": False,
                "message": f"Якорь '{anchor_name}' не найден"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "phrase": phrase,
            "anchor_name": anchor_name
        })
        
    except Exception as e:
        logger.error(f"❌ Error in fire_anchor: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/anchor/user/{user_id}")
async def get_user_anchors(user_id: int):
    """
    Получить все якоря пользователя
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        anchors = user_info.get('anchors', [])
        
        return JSONResponse({
            "success": True,
            "anchors": anchors
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_user_anchors: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/practice/morning")
async def get_morning_practice():
    """
    Получить утреннюю практику
    """
    try:
        lib = InterventionLibrary()
        practice = lib.get_morning_practice()
        
        return JSONResponse({
            "success": True,
            "practice": practice
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_morning_practice: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/practice/evening")
async def get_evening_practice():
    """
    Получить вечернюю практику
    """
    try:
        lib = InterventionLibrary()
        practice = lib.get_evening_practice()
        
        return JSONResponse({
            "success": True,
            "practice": practice
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_evening_practice: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/practice/random-exercise")
async def get_random_exercise(category: str = None):
    """
    Получить случайное упражнение
    """
    try:
        lib = InterventionLibrary()
        exercise = lib.get_random_exercise(category)
        
        # Получаем все доступные категории
        all_categories = list(lib.exercises.keys())
        
        return JSONResponse({
            "success": True,
            "exercise": exercise,
            "category": category,
            "available_categories": all_categories
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_random_exercise: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/practice/random-quote")
async def get_random_quote(category: str = None):
    """
    Получить случайную цитату
    """
    try:
        lib = InterventionLibrary()
        quote = lib.get_random_quote(category)
        
        return JSONResponse({
            "success": True,
            "quote": quote,
            "category": category
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_random_quote: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/practice/week-program/{element_id}")
async def get_week_program(element_id: int, user_id: int):
    """
    Получить недельную программу для элемента
    """
    try:
        user_id = int(user_id)
        element_id = int(element_id)
        user_info = user_data.get(user_id, {})
        
        lib = InterventionLibrary()
        week_program = lib.get_program_for_week(element_id)
        
        return JSONResponse({
            "success": True,
            "element_id": element_id,
            "program": week_program
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_week_program: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@api_app.get("/api/confinement/statistics/{user_id}")
async def get_confinement_statistics(user_id: int):
    """
    Получить статистику по конфайнтмент-модели
    """
    try:
        user_id = int(user_id)
        user_info = user_data.get(user_id, {})
        
        existing_model = user_info.get('confinement_model')
        if not existing_model:
            return JSONResponse({
                "success": False,
                "message": "Модель не построена"
            })
        
        if isinstance(existing_model, dict):
            model = ConfinementModel9.from_dict(existing_model)
        else:
            model = existing_model
        
        analyzer = LoopAnalyzer(model)
        loops = analyzer.analyze()
        
        detector = KeyConfinementDetector(model, loops)
        key = detector.detect()
        
        lib = InterventionLibrary()
        
        return JSONResponse({
            "success": True,
            "statistics": {
                "total_elements": len([e for e in model.elements.values() if e]),
                "active_elements": sum(1 for e in model.elements.values() if e and e.strength > 0.3),
                "total_loops": len(loops),
                "strongest_loop_strength": analyzer.get_strongest_loop().get('impact', 0) if analyzer.get_strongest_loop() else 0,
                "is_system_closed": model.is_closed,
                "closure_score": model.closure_score,
                "has_key_confinement": key is not None,
                "key_confinement_strength": key.get('score', 0) if key else 0
            },
            "library_statistics": lib.get_statistics()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in get_confinement_statistics: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

if __name__ == "__main__":
    main()
