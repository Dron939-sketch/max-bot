#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ ДЛЯ MAX
ИСПРАВЛЕНО: обработка вопросов без await для синхронных функций
ДОБАВЛЕНО: FastAPI для мини-приложения с полной синхронизацией
ДОБАВЛЕНО: PostgreSQL для постоянного хранения данных
ИСПРАВЛЕНО: правильное обслуживание статических файлов из папки miniapp
ИСПРАВЛЕНО: окончательное решение проблемы sniffio для Python 3.14
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
import warnings
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime, timedelta

# ========== ИСПРАВЛЕНИЕ ПРОБЛЕМ ASYNCIO ==========
# Игнорируем предупреждения
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Импортируем nest_asyncio для решения проблем с циклами событий
import nest_asyncio
nest_asyncio.apply()  # Применяем глобально

# Глобальная фиксация sniffio
import sniffio

def _fixed_current_async_library():
    """Всегда возвращаем asyncio для sniffio"""
    return "asyncio"

# Применяем фикс глобально
sniffio.current_async_library = _fixed_current_async_library

# Принудительно устанавливаем политику цикла событий для разных платформ
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# =================================================

# ========== ИМПОРТЫ ДЛЯ FASTAPI ==========
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
    """
    Проверяет, не запущен ли уже экземпляр бота
    """
    # Проверяем, запущены ли мы на Render
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

# Дополнительные импорты для API эндпоинтов
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

# Устанавливаем morning_manager для profile.py (чтобы избежать циклического импорта)
set_morning_manager(morning_manager)

# Привязываем morning_manager к боту и контекстам
morning_manager.set_bot(bot)
morning_manager.set_contexts(user_contexts, user_data)

# ============================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================

async def init_database():
    """Инициализация базы данных"""
    try:
        # Подключаемся к базе
        await init_db()
        logger.info("✅ Подключение к PostgreSQL установлено")
        
        # Проверяем соединение с защитой от ошибок
        await ensure_db_connection()
        
        # Загружаем всех пользователей из БД в память
        await load_all_users_from_db()
        
        # ✅ ЗАПУСКАЕМ АВТОСОХРАНЕНИЕ
        setup_auto_save(interval_seconds=300)  # Каждые 5 минут
        
        # Запускаем фоновые задачи
        asyncio.create_task(periodic_save_to_db())
        asyncio.create_task(periodic_cleanup_db())
        
        logger.info("✅ База данных инициализирована")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

async def load_all_users_from_db():
    """Загружает всех пользователей из БД в словари памяти"""
    global user_data, user_names, user_contexts, user_routes
    
    logger.info("🔄 Загрузка данных из PostgreSQL...")
    
    try:
        # Загружаем пользователей из таблицы fredi_users
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, first_name, username FROM fredi_users")
            for row in rows:
                user_names[row['user_id']] = row['first_name'] or row['username'] or f"user_{row['user_id']}"
        
        # Загружаем контексты из полей таблицы
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT * FROM fredi_user_contexts")
            for row in rows:
                user_id = row['user_id']
                
                # Восстанавливаем объект UserContext
                context = UserContext(user_id)
                
                # Заполняем поля из строки БД
                context.name = row.get('name')
                context.age = row.get('age')
                context.gender = row.get('gender')
                context.city = row.get('city')
                context.birth_date = row.get('birth_date')
                context.timezone = row.get('timezone', 'Europe/Moscow')
                context.timezone_offset = row.get('timezone_offset', 3)
                context.communication_mode = row.get('communication_mode', 'coach')
                context.last_context_update = row.get('last_context_update')
                
                # Погода (JSON)
                if row.get('weather_cache'):
                    context.weather_cache = json.loads(row['weather_cache'])
                context.weather_cache_time = row.get('weather_cache_time')
                
                # Жизненный контекст
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
                
                # Состояние сбора
                context.awaiting_context = row.get('awaiting_context')
                
                user_contexts[user_id] = context
        
        # Загружаем user_data
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, data FROM fredi_user_data")
            for row in rows:
                data = row['data']
                if isinstance(data, str):
                    data = json.loads(data)
                user_data[row['user_id']] = data
        
        # Загружаем активные маршруты
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
        
        # Также пробуем загрузить из pickled контекстов (резерв)
        async with db.get_connection() as conn:
            rows = await conn.fetch("SELECT user_id, context_data FROM fredi_context_objects")
            for row in rows:
                user_id = row['user_id']
                # Если контекст еще не загружен из основной таблицы
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
        await asyncio.sleep(300)  # Каждые 5 минут
        
        logger.info("🔄 Периодическое сохранение данных в БД...")
        
        saved_count = 0
        for user_id in list(user_data.keys()):
            try:
                # Используем execute_with_retry для защиты от ошибок
                result = await execute_with_retry(
                    save_user_to_db, 
                    user_id, user_data, user_contexts, user_routes,
                    max_retries=3
                )
                if result:
                    saved_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения {user_id}: {e}")
        
        logger.info(f"✅ Сохранено {saved_count} пользователей")

async def periodic_cleanup_db():
    """Периодическая очистка старых данных"""
    while True:
        await asyncio.sleep(86400)  # 24 часа
        
        try:
            await db.cleanup_old_data(days=30)
            logger.info("🧹 Очистка старых данных выполнена")
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке данных: {e}")

# ============================================
# FASTAPI ДЛЯ МИНИ-ПРИЛОЖЕНИЯ - ИСПРАВЛЕНО
# ============================================

# Создаем FastAPI приложение
api_app = FastAPI(title="Фреди - Мини-приложение")

# Настройка CORS
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ПОДКЛЮЧЕНИЕ СТАТИЧЕСКИХ ФАЙЛОВ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

# Путь к папке с мини-приложением
MINIAPP_PATH = os.path.join(os.path.dirname(__file__), 'miniapp')

# Создаем папку, если её нет
os.makedirs(MINIAPP_PATH, exist_ok=True)

# Обслуживаем статические файлы из папки miniapp
if os.path.exists(MINIAPP_PATH):
    # Монтируем статические файлы по пути /miniapp
    api_app.mount("/miniapp", StaticFiles(directory=MINIAPP_PATH, html=True), name="miniapp")
    logger.info(f"✅ Статические файлы подключены из {MINIAPP_PATH}")

    # Перенаправление с корня на index.html из miniapp
    @api_app.get("/")
    async def serve_miniapp():
        index_path = os.path.join(MINIAPP_PATH, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "index.html не найден в папке miniapp"}
            )
else:
    logger.error(f"❌ Папка {MINIAPP_PATH} не найдена")
    
    @api_app.get("/")
    async def error_no_miniapp():
        return JSONResponse(
            status_code=404,
            content={"error": "Папка miniapp не найдена"}
        )

# ============================================
# API ЭНДПОИНТЫ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ
# ============================================

@api_app.post("/api/save-profile")
async def save_profile(request: Request):
    """Сохраняет профиль из мини-приложения"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        profile = data.get('profile')
        
        if not user_id or not profile:
            raise HTTPException(status_code=400, detail="user_id and profile required")
        
        # Сохраняем в user_data
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['ai_generated_profile'] = profile
        user_data[user_id]['profile_data'] = profile.get('profile_data', {})
        
        # Сохраняем в БД с защитой от ошибок
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
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
    """Сохраняет прогресс теста из мини-приложения"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        stage = data.get('stage')
        answers = data.get('answers', [])
        
        if not user_id or stage is None:
            raise HTTPException(status_code=400, detail="user_id and stage required")
        
        # Сохраняем в user_data
        if user_id not in user_data:
            user_data[user_id] = {}
        
        # Инициализируем хранилище ответов
        if 'all_answers' not in user_data[user_id]:
            user_data[user_id]['all_answers'] = []
        
        # Добавляем новые ответы
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
        
        # Сохраняем в БД с защитой от ошибок
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
        return JSONResponse({
            "success": True,
            "message": f"Stage {stage} progress saved"
        })
    except Exception as e:
        logger.error(f"❌ Error in save_test_progress: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.post("/api/save-mode")
async def save_mode(request: Request):
    """Сохраняет режим общения из мини-приложения"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        mode = data.get('mode')
        
        if not user_id or not mode:
            raise HTTPException(status_code=400, detail="user_id and mode required")
        
        # Сохраняем в контексте
        if user_id in user_contexts:
            user_contexts[user_id].communication_mode = mode
        
        # Сохраняем в user_data
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['communication_mode'] = mode
        
        # Сохраняем в БД с защитой от ошибок
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
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
    """Синхронизирует данные с мини-приложения"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        sync_data = data.get('data', {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        # Инициализируем данные пользователя
        if user_id not in user_data:
            user_data[user_id] = {}
        
        # Синхронизируем ответы
        if 'answers' in sync_data:
            if 'all_answers' not in user_data[user_id]:
                user_data[user_id]['all_answers'] = []
            user_data[user_id]['all_answers'].extend(sync_data['answers'])
        
        # Синхронизируем профиль
        if 'profile' in sync_data:
            user_data[user_id]['ai_generated_profile'] = sync_data['profile']
        
        # Синхронизируем режим
        if 'mode' in sync_data and user_id in user_contexts:
            user_contexts[user_id].communication_mode = sync_data['mode']
        
        # Сохраняем в БД с защитой от ошибок
        await execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        )
        
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
    """Возвращает профиль для мини-приложения"""
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
    """Возвращает прогресс теста для мини-приложения"""
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
# СТАРЫЕ ЭНДПОИНТЫ (ОСТАВЛЯЕМ ДЛЯ СОВМЕСТИМОСТИ)
# ============================================

# Вспомогательные функции для API
def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def get_human_readable_profile(scores: dict, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
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

@api_app.get("/api/user-data")
async def get_user_data_api(user_id: int):
    """Возвращает базовую информацию о пользователе"""
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
    """Возвращает психологический портрет"""
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        profile = data.get("ai_generated_profile")
        if not profile:
            # Если нет AI профиля, генерируем стандартный
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
    """Возвращает мысли психолога"""
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        
        thought = data.get("psychologist_thought")
        if not thought:
            # Генерируем мысль, если её нет
            thought = await generate_psychologist_thought(user_id, data)
            if thought:
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]["psychologist_thought"] = thought
                # Сразу сохраняем в БД с защитой
                asyncio.create_task(execute_with_retry(
                    save_user_to_db, user_id, user_data, user_contexts, user_routes,
                    max_retries=3
                ))
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
    """Возвращает идеи на выходные"""
    try:
        user_id = int(user_id)
        data = user_data.get(user_id, {})
        context = user_contexts.get(user_id)
        user_name = context.name if context else user_names.get(user_id, "друг")
        
        # Проверяем кэш в БД
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
        
        # Сохраняем в кэш БД
        if scores:
            main_vector = max(scores.items(), key=lambda x: x[1])[0]
            main_level = int(scores.get(main_vector, 3))
            asyncio.create_task(db.cache_weekend_ideas(user_id, ideas_text, main_vector, main_level))
        
        # Преобразуем текст в структурированные идеи
        ideas = []
        paragraphs = ideas_text.split('\n\n')
        for p in paragraphs:
            if p.strip() and not p.startswith('#'):
                ideas.append({
                    "title": p[:50] + "..." if len(p) > 50 else p,
                    "description": p
                })
        
        return {"ideas": ideas[:5]}  # Возвращаем первые 5 идей
    except Exception as e:
        logger.error(f"API error in get_ideas: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@api_app.get("/health")
async def health_check():
    """Health check для Render (FastAPI)"""
    return {"status": "ok"}

# ============================================
# НОВЫЕ ЭНДПОИНТЫ ДЛЯ МИНИ-ПРИЛОЖЕНИЯ (ЧАТ И ТЕСТЫ)
# ============================================

@api_app.get("/api/chat/history")
async def get_chat_history(user_id: int, limit: int = 50):
    """Возвращает историю чата пользователя"""
    try:
        user_id = int(user_id)
        
        # Здесь можно получать из БД, если сохраняете историю
        # Пока возвращаем пустую историю - приветствие покажет script.js
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

@api_app.post("/api/chat/message")
async def chat_message(request: Request):
    """Отправляет сообщение боту и получает ответ"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        message_text = data.get('message')
        mode = data.get('mode')
        
        if not user_id or not message_text:
            raise HTTPException(status_code=400, detail="user_id and message required")
        
        user_id = int(user_id)
        
        # Получаем контекст пользователя
        if user_id not in user_contexts:
            user_contexts[user_id] = UserContext(user_id)
        
        context = user_contexts[user_id]
        
        # Устанавливаем режим, если передан
        if mode and mode in COMMUNICATION_MODES:
            context.communication_mode = mode
        
        # Получаем данные пользователя
        user_info = user_data.get(user_id, {})
        
        # Анализируем вопрос (если это вопрос)
        from question_analyzer import QuestionAnalyzer
        analyzer = QuestionAnalyzer(user_id, user_info)
        analysis = await analyzer.analyze_question_async(message_text)
        
        # Генерируем ответ через DeepSeek
        from services import call_deepseek_with_context
        
        # Формируем промпт с учетом контекста и профиля
        system_prompt = f"Ты психолог Фреди. Режим: {context.communication_mode}. "
        
        if context.name:
            system_prompt += f"Имя пользователя: {context.name}. "
        
        if user_info.get('perception_type'):
            system_prompt += f"Тип восприятия: {user_info['perception_type']}. "
        
        if user_info.get('thinking_level'):
            system_prompt += f"Уровень мышления: {user_info['thinking_level']}/9. "
        
        if analysis:
            system_prompt += f"Анализ вопроса: {analysis.get('analysis', '')}. "
        
        # Вызываем DeepSeek
        response = await call_deepseek_with_context(
            user_id=user_id,
            user_message=message_text,
            context=context,
            mode=context.communication_mode,
            profile_data=user_info
        )
        
        if not response:
            response = "Я понял ваш запрос. Дайте подумать..."
        
        # Определяем, нужно ли показать кнопки
        buttons = None
        text_lower = response.lower()
        
        if any(word in text_lower for word in ['тест', 'пройди', 'этап']):
            buttons = [
                {"text": "🧠 Пройти тест", "action": "start_test"},
                {"text": "📊 Мой портрет", "action": "show_profile"}
            ]
        elif any(word in text_lower for word in ['профиль', 'портрет', 'результат']):
            buttons = [
                {"text": "📊 Посмотреть", "action": "show_profile"},
                {"text": "🧠 Мысли", "action": "show_thoughts"}
            ]
        elif any(word in text_lower for word in ['выходные', 'идеи', 'план']):
            buttons = [
                {"text": "🎯 Идеи", "action": "show_weekend"},
                {"text": "📊 В профиль", "action": "show_profile"}
            ]
        
        return JSONResponse({
            "success": True,
            "response": response,
            "mode": context.communication_mode,
            "analysis": analysis,
            "buttons": buttons
        })
        
    except Exception as e:
        logger.error(f"❌ Error in chat_message: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": str(e),
                "response": "Произошла ошибка. Попробуйте еще раз."
            }
        )

@api_app.post("/api/chat/action")
async def chat_action(request: Request):
    """Обрабатывает нажатия на кнопки"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        action = data.get('action')
        action_data = data.get('data', {})
        
        if not user_id or not action:
            raise HTTPException(status_code=400, detail="user_id and action required")
        
        user_id = int(user_id)
        
        # Обрабатываем различные действия
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

@api_app.get("/api/test/question")
async def get_test_question(user_id: int, stage: int, index: int):
    """Возвращает вопрос теста"""
    try:
        user_id = int(user_id)
        stage = int(stage)
        index = int(index)
        
        # Определяем общее количество вопросов для этапа
        stage_questions_count = {
            1: 4,  # Тип восприятия
            2: 6,  # Уровень мышления
            3: 24, # Поведенческие уровни (4 вектора × 6)
            4: 12, # Уровни Дилтса
            5: 8   # Глубинные паттерны
        }
        
        total = stage_questions_count.get(stage, 4)
        
        # Вопросы для этапа 1 (Тип восприятия)
        stage1_questions = [
            {
                "text": "Как вы обычно воспринимаете новую информацию?",
                "options": [
                    {"id": "A", "text": "Через визуальные образы и картинки", "value": "visual"},
                    {"id": "B", "text": "Через ощущения и телесный опыт", "value": "kinesthetic"},
                    {"id": "C", "text": "Через логические схемы и структуры", "value": "auditory"},
                    {"id": "D", "text": "Через интуицию и общее впечатление", "value": "digital"}
                ]
            },
            {
                "text": "Что для вас важнее при принятии решения?",
                "options": [
                    {"id": "A", "text": "Как это будет выглядеть", "value": "visual"},
                    {"id": "B", "text": "Что я чувствую по этому поводу", "value": "kinesthetic"},
                    {"id": "C", "text": "Логика и факты", "value": "auditory"},
                    {"id": "D", "text": "Общая картина и смысл", "value": "digital"}
                ]
            },
            {
                "text": "Как вы лучше запоминаете?",
                "options": [
                    {"id": "A", "text": "Когда вижу схему или изображение", "value": "visual"},
                    {"id": "B", "text": "Когда записываю или проживаю", "value": "kinesthetic"},
                    {"id": "C", "text": "Когда проговариваю вслух", "value": "auditory"},
                    {"id": "D", "text": "Когда понимаю суть", "value": "digital"}
                ]
            },
            {
                "text": "Что вас вдохновляет?",
                "options": [
                    {"id": "A", "text": "Красота и гармония", "value": "visual"},
                    {"id": "B", "text": "Глубокие переживания", "value": "kinesthetic"},
                    {"id": "C", "text": "Идеи и концепции", "value": "auditory"},
                    {"id": "D", "text": "Смысл и предназначение", "value": "digital"}
                ]
            }
        ]
        
        # Вопросы для этапа 2 (Уровень мышления)
        stage2_questions = [
            {
                "text": "Я часто анализирую свои мысли и чувства",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            },
            {
                "text": "Мне важно понимать причины своих поступков",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            },
            {
                "text": "Я вижу взаимосвязи между разными событиями",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            },
            {
                "text": "Я задумываюсь о смысле жизни",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            },
            {
                "text": "Мне интересно изучать новые концепции",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            },
            {
                "text": "Я замечаю, как меняются мои взгляды со временем",
                "options": [
                    {"id": "A", "text": "Совершенно не согласен", "value": 1},
                    {"id": "B", "text": "Скорее не согласен", "value": 2},
                    {"id": "C", "text": "Нейтрально", "value": 3},
                    {"id": "D", "text": "Скорее согласен", "value": 4},
                    {"id": "E", "text": "Полностью согласен", "value": 5}
                ]
            }
        ]
        
        # Выбираем нужный вопрос
        if stage == 1 and index < len(stage1_questions):
            question = stage1_questions[index]
        elif stage == 2 and index < len(stage2_questions):
            question = stage2_questions[index]
        else:
            # Заглушка для остальных этапов
            question = {
                "text": f"Вопрос {index + 1} этапа {stage}",
                "options": [
                    {"id": "A", "text": "Вариант А", "value": "A"},
                    {"id": "B", "text": "Вариант Б", "value": "B"},
                    {"id": "C", "text": "Вариант В", "value": "C"},
                    {"id": "D", "text": "Вариант Г", "value": "D"}
                ]
            }
        
        # Проверяем, отвечал ли пользователь уже на этот вопрос
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
    """Сохраняет ответ на вопрос теста"""
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
        
        # Сохраняем ответ в user_data
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'all_answers' not in user_data[user_id]:
            user_data[user_id]['all_answers'] = []
        
        # Добавляем ответ
        answer_record = {
            'stage': stage,
            'question_index': question_index,
            'answer': answer,
            'option': option,
            'timestamp': datetime.now().isoformat()
        }
        
        user_data[user_id]['all_answers'].append(answer_record)
        
        # Сохраняем в специфичное для этапа хранилище
        stage_key = f'stage{stage}_answers'
        if stage_key not in user_data[user_id]:
            user_data[user_id][stage_key] = []
        user_data[user_id][stage_key].append(answer_record)
        
        # Сохраняем в БД с защитой
        asyncio.create_task(execute_with_retry(
            save_user_to_db, user_id, user_data, user_contexts, user_routes,
            max_retries=3
        ))
        
        # Определяем, завершен ли этап
        stage_questions_count = {
            1: 4, 2: 6, 3: 24, 4: 12, 5: 8
        }
        total = stage_questions_count.get(stage, 4)
        
        # Считаем количество ответов на этом этапе
        stage_answers = [a for a in user_data[user_id].get('all_answers', []) 
                        if a.get('stage') == stage]
        stage_complete = len(stage_answers) >= total
        
        # Если этап завершен, обновляем прогресс
        if stage_complete:
            if stage == 1 and 'perception_type' not in user_data[user_id]:
                # Определяем тип восприятия (заглушка)
                user_data[user_id]['perception_type'] = 'visual'
            elif stage == 2 and 'thinking_level' not in user_data[user_id]:
                # Определяем уровень мышления (заглушка)
                user_data[user_id]['thinking_level'] = 5
            elif stage == 3 and 'behavioral_levels' not in user_data[user_id]:
                user_data[user_id]['behavioral_levels'] = {
                    'extraversion': [3,4,3,4,3,4],
                    'neuroticism': [3,3,3,3,3,3],
                    'agreeableness': [4,4,4,4,4,4],
                    'conscientiousness': [4,4,4,4,4,4]
                }
            
            # Обновляем current_stage
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
    """Возвращает результаты этапа теста"""
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
    # Начинаем с порта 10001, чтобы не конфликтовать с FastAPI
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
# Функция split_long_message теперь импортируется из formatters.py

# ============================================
# ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ УНИКАЛЬНЫХ CALLBACK'ОВ
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
# ФУНКЦИЯ ПРОВЕРКИ API ПРИ СТАРТЕ
# ============================================

async def check_api_on_startup():
    """Проверяет работу API при запуске"""
    logger.info("🔍 Проверка API при запуске...")
    
    results = {
        "deepseek": False,
        "deepgram": False,
        "yandex": False,
        "openweather": False
    }
    
    # Проверка DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            test_response = await call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
            results["deepseek"] = test_response is not None
            logger.info(f"✅ DeepSeek API: {'работает' if results['deepseek'] else 'ошибка'}")
        except Exception as e:
            logger.error(f"❌ DeepSeek API ошибка: {e}")
    
    # Проверка Deepgram (по наличию ключа)
    if DEEPGRAM_API_KEY:
        results["deepgram"] = True
        logger.info("✅ Deepgram API ключ найден")
    
    # Проверка Yandex (по наличию ключа)
    if YANDEX_API_KEY:
        results["yandex"] = True
        logger.info("✅ Yandex TTS ключ найден")
    
    # Проверка OpenWeather
    if OPENWEATHER_API_KEY:
        results["openweather"] = True
        logger.info("✅ OpenWeather API ключ найден")
    
    return results

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

# 👇 КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ
@bot.message_handler(commands=['test_yandex'])
def cmd_test_yandex(message: types.Message):
    """Тестирование Yandex TTS"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    def run_async():
        asyncio.run(test_yandex_async(message))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_weather'])
def cmd_test_weather(message: types.Message):
    """Тестирование OpenWeather API"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    def run_async():
        asyncio.run(test_weather_async(message))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_voices'])
def cmd_test_voices(message: types.Message):
    """Тестирование голосов"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    def run_async():
        asyncio.run(test_voices_async(message))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['test_voice_send'])
def cmd_test_voice_send(message: types.Message):
    """Тест отправки голосового сообщения"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    def run_async():
        asyncio.run(test_voice_send_async(message))
    
    threading.Thread(target=run_async, daemon=True).start()

@bot.message_handler(commands=['weekend'])
def cmd_weekend(message: types.Message):
    """Команда /weekend - идеи на выходные"""
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
    """Статистика базы данных (только для админов)"""
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
    """Асинхронное тестирование Yandex TTS"""
    status_msg = await safe_send_message(
        message,
        "🎧 Тестирую Yandex TTS...",
        delete_previous=True
    )
    
    test_text = "Привет! Это тестовое голосовое сообщение."
    results = []
    
    for mode in ["coach", "psychologist", "trainer"]:
        audio = await text_to_speech(test_text, mode)
        if audio:
            results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']}")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']}")
        await asyncio.sleep(0.5)
    
    await safe_delete_message(message.chat.id, status_msg.message_id)
    await safe_send_message(
        message,
        "📊 Результаты тестирования Yandex TTS:\n" + "\n".join(results),
        delete_previous=True
    )

async def test_weather_async(message: types.Message):
    """Асинхронное тестирование OpenWeather"""
    if not OPENWEATHER_API_KEY:
        await safe_send_message(message, "❌ OPENWEATHER_API_KEY не настроен", delete_previous=True)
        return
    
    test_city = "Москва"
    status_msg = await safe_send_message(
        message,
        f"🌍 Тестирую погоду для города {test_city}...",
        delete_previous=True
    )
    
    try:
        import aiohttp
        url = f"http://api.openweathermap.org/data/2.5/weather?q={test_city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    desc = data['weather'][0]['description']
                    humidity = data['main']['humidity']
                    wind = data['wind']['speed']
                    
                    text = f"✅ Погода работает!\n\n"
                    text += f"📍 Город: {test_city}\n"
                    text += f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    text += f"☁️ Описание: {desc}\n"
                    text += f"💧 Влажность: {humidity}%\n"
                    text += f"💨 Ветер: {wind} м/с"
                    
                    await safe_delete_message(message.chat.id, status_msg.message_id)
                    await safe_send_message(message, text, delete_previous=True)
                else:
                    error_text = await response.text()
                    await safe_delete_message(message.chat.id, status_msg.message_id)
                    await safe_send_message(message, f"❌ Ошибка {response.status}: {error_text[:200]}", delete_previous=True)
    except Exception as e:
        await safe_delete_message(message.chat.id, status_msg.message_id)
        await safe_send_message(message, f"❌ Ошибка: {e}", delete_previous=True)

async def test_voices_async(message: types.Message):
    """Тестирование всех голосов"""
    await safe_send_message(
        message,
        "🎙 Функция тестирования голосов в разработке",
        delete_previous=True
    )

async def test_voice_send_async(message: types.Message):
    """Асинхронное тестирование отправки голоса"""
    status_msg = await safe_send_message(
        message,
        "🎧 Тестирую отправку голоса...",
        delete_previous=True
    )
    
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
    
    await safe_delete_message(message.chat.id, status_msg.message_id)
    await safe_send_message(
        message,
        "📊 Результаты тестирования отправки голоса:\n" + "\n".join(results),
        delete_previous=True
    )

async def show_weekend_ideas(message: types.Message, user_id: int):
    """Показывает идеи на выходные"""
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = user_names.get(user_id, "друг")
    
    # Получаем scores из данных
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    profile_data = data.get("profile_data", {})
    
    # Отправляем статусное сообщение
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
# CALLBACK-ОБРАБОТЧИК
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: types.CallbackQuery):
    callback_handler(call)

# ============================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
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
        safe_send_message(
            message,
            "Пожалуйста, ответьте на вопрос или используйте кнопки",
            delete_previous=True,
            keep_last=1
        )

# ============================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ ПО СОСТОЯНИЯМ
# ============================================

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_question)
def handle_question_message(message: types.Message):
    """Обрабатывает текстовые сообщения в состоянии ожидания вопроса"""
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"❓ Получен вопрос от пользователя {user_id} в состоянии awaiting_question: {text[:50]}...")
    
    def run_sync():
        # Импортируем синхронную функцию из questions.py
        from handlers.questions import process_text_question_sync
        process_text_question_sync(message, user_id, text)
    
    # Запускаем в отдельном потоке (без asyncio.run)
    threading.Thread(target=run_sync, daemon=True).start()


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_custom_goal)
def handle_custom_goal_message(message: types.Message):
    """Обрабатывает пользовательскую цель"""
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"🎯 Получена пользовательская цель от пользователя {user_id}: {text[:50]}...")
    
    def run_async():
        asyncio.run(process_custom_goal_async(message, user_id, text))
    
    threading.Thread(target=run_async, daemon=True).start()


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.pretest_question)
def handle_pretest_question(message: types.Message):
    """Обрабатывает вопросы до теста"""
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"❓ Получен вопрос до теста от пользователя {user_id}")
    
    safe_send_message(
        message,
        "Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. "
        "Пройдите тест — это займёт 15 минут.",
        delete_previous=True
    )
    clear_state(user_id)


# ============================================
# ОБРАБОТЧИК ГОЛОСОВЫХ СООБЩЕНИЙ
# ============================================

@bot.message_handler(content_types=['voice'])
def handle_voice_wrapper(message: types.Message):
    """Обработчик голосовых сообщений"""
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


# ============================================
# АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ ОБРАБОТКИ СООБЩЕНИЙ
# ============================================

async def process_custom_goal_async(message: types.Message, user_id: int, text: str):
    """Асинхронная обработка пользовательской цели"""
    try:
        from handlers.goals import process_custom_goal_async as process_goal
        await process_goal(message, user_id, text)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке пользовательской цели: {e}")
        import traceback
        traceback.print_exc()
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке цели. Пожалуйста, попробуйте еще раз.",
            delete_previous=True
        )


# ============================================
# ФУНКЦИЯ ЗАПУСКА FASTAPI - ОКОНЧАТЕЛЬНОЕ ИСПРАВЛЕНИЕ
# ============================================

def run_fastapi():
    """Запускает FastAPI сервер в отдельном потоке"""
    # Render сам назначает порт через переменную окружения PORT
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Запуск FastAPI на порту {port}")
    
    # СОЗДАЁМ НОВЫЙ ЦИКЛ СОБЫТИЙ ДЛЯ ЭТОГО ПОТОКА
    try:
        # Создаём новый цикл
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("✅ Создан новый цикл событий для потока FastAPI")
        
        # Применяем nest_asyncio к этому циклу
        nest_asyncio.apply(loop)
        logger.info("✅ nest_asyncio применён к циклу FastAPI")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при настройке цикла событий: {e}")
        loop = None
    
    # ЗАПУСКАЕМ UVICORN
    try:
        # Важно: используем loop из этого потока
        uvicorn.run(
            api_app, 
            host="0.0.0.0", 
            port=port,
            loop=loop  # Передаём наш цикл напрямую
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске uvicorn: {e}")
        # Последняя попытка без передачи цикла
        uvicorn.run(api_app, host="0.0.0.0", port=port)


# ============================================
# ФУНКЦИЯ ЗАПУСКА АСИНХРОННЫХ ЗАДАЧ
# ============================================

def run_async_tasks():
    """Запускает асинхронные задачи в отдельном потоке"""
    # Создаём новый цикл для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Применяем nest_asyncio
    nest_asyncio.apply(loop)
    
    # Запускаем проверку API
    try:
        # Используем run_until_complete с обработкой ошибок
        loop.run_until_complete(check_api_on_startup())
    except RuntimeError as e:
        if 'already running' in str(e):
            logger.warning("⚠️ Цикл событий уже запущен, пропускаем")
        else:
            logger.error(f"❌ Ошибка при проверке API: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке API: {e}")
    
    # Не закрываем цикл, оставляем для других задач
    # loop.close() - закомментировано


# ============================================
# ЗАПУСК БОТА
# ============================================

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
    """Обработчик завершения работы - сохраняет все данные в БД"""
    logger.info("🛑 Завершение работы, сохраняем данные в БД...")
    
    try:
        from state import save_all_users_to_db
        # Используем execute_with_retry для защиты от ошибок
        saved_count = await execute_with_retry(save_all_users_to_db, db, max_retries=3)
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
    
    # Создаем новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Инициализируем базу данных
    try:
        loop.run_until_complete(init_database())
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при инициализации БД: {e}")
        sys.exit(1)
    
    # Запускаем планировщик
    scheduler.start()
    
    # Запускаем асинхронные задачи в отдельном потоке
    async_thread = threading.Thread(target=run_async_tasks, daemon=True)
    async_thread.start()
    
    # Запускаем FastAPI в отдельном потоке
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    logger.info("✅ FastAPI сервер запущен")
    
    # Добавляем обработчик сигналов для корректного завершения
    try:
        import signal
        
        def signal_handler():
            asyncio.create_task(shutdown_handler())
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    except (ImportError, NotImplementedError, AttributeError) as e:
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
                # Сохраняем данные перед выходом
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
                    # Сохраняем данные перед выходом
                    loop.run_until_complete(shutdown_handler())
    finally:
        cleanup_resources()

if __name__ == "__main__":
    main()
