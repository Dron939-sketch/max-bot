#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ ДЛЯ MAX
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
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime

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
    format_profile_text, format_psychologist_text, strip_html
)

# Импорты из обработчиков
from handlers.context import handle_context_message, start_context, show_context_complete
from handlers.reality import process_life_context, process_goal_context
from handlers.callback import callback_handler
from handlers.modes import show_mode_selection, show_mode_selected, show_main_menu_after_mode
from handlers.start import cmd_start as start_cmd, show_why_details
from handlers.profile import show_profile, show_ai_profile, show_psychologist_thought, show_final_profile
from handlers.stages import *
from handlers.help import show_help, show_tale, show_benefits
from handlers.goals import *
from handlers.questions import *
from handlers.admin import *
from handlers.voice import handle_voice_message

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

# ============================================
# HEALTH CHECK ДЛЯ RENDER
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
    ports = [10000, 10001, 10002, 10003, 10004]
    for port in ports:
        try:
            server = HTTPServer(('0.0.0.0', port), HealthHandler)
            logger.info(f"✅ Health check server started on port {port}")
            server.serve_forever()
            return
        except OSError:
            continue
        except Exception as e:
            logger.error(f"❌ Error on port {port}: {e}")
            continue

health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДЛИННЫМИ СООБЩЕНИЯМИ
# ============================================

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if len(para) > max_length:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                if len(current_part) + len(sent) + 2 <= max_length:
                    if current_part:
                        current_part += "\n\n" + sent
                    else:
                        current_part = sent
                else:
                    if current_part:
                        parts.append(current_part)
                    if len(sent) > max_length:
                        words = sent.split()
                        temp = ""
                        for word in words:
                            if len(temp) + len(word) + 1 <= max_length:
                                if temp:
                                    temp += " " + word
                                else:
                                    temp = word
                            else:
                                parts.append(temp)
                                temp = word
                        if temp:
                            current_part = temp
                        else:
                            current_part = ""
                    else:
                        current_part = sent
        else:
            if len(current_part) + len(para) + 2 <= max_length:
                if current_part:
                    current_part += "\n\n" + para
                else:
                    current_part = para
            else:
                if current_part:
                    parts.append(current_part)
                current_part = para
    
    if current_part:
        parts.append(current_part)
    
    return parts

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

# 👇 НОВЫЕ КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ
@bot.message_handler(commands=['test_yandex'])
def cmd_test_yandex(message: types.Message):
    """Тестирование Yandex TTS"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    # Создаем отдельный поток для асинхронной задачи
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

# 👇 АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ
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
    
    text = f"{mode_config['emoji']} {bold(f'РЕЖИМ {mode_config["display_name"]}')}\n\n"
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
# 👇 НОВЫЕ ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ ПО СОСТОЯНИЯМ
# ============================================

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_question)
def handle_question_message(message: types.Message):
    """Обрабатывает текстовые сообщения в состоянии ожидания вопроса"""
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"❓ Получен вопрос от пользователя {user_id} в состоянии awaiting_question: {text[:50]}...")
    
    def run_async():
        asyncio.run(process_text_question_async(message, user_id, text))
    
    threading.Thread(target=run_async, daemon=True).start()


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
# 👇 ОБРАБОТЧИК ГОЛОСОВЫХ СООБЩЕНИЙ
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
# 👇 АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ ОБРАБОТКИ СООБЩЕНИЙ
# ============================================

async def process_text_question_async(message: types.Message, user_id: int, text: str):
    """Асинхронная обработка текстового вопроса"""
    try:
        from handlers.questions import process_text_question_async as process_question
        await process_question(message, user_id, text)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке вопроса: {e}")
        import traceback
        traceback.print_exc()
        await safe_send_message(
            message,
            "❌ Произошла ошибка при обработке вопроса. Пожалуйста, попробуйте еще раз.",
            delete_previous=True
        )


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

def run_async_tasks():
    """Запускает асинхронные задачи в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Запускаем проверку API
    try:
        loop.run_until_complete(check_api_on_startup())
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке API: {e}")
    
    # Здесь можно добавить другие асинхронные задачи
    # loop.run_until_complete(some_other_task())
    
    loop.close()

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
    print("="*80 + "\n")
    
    logger.info("🚀 Бот для MAX запущен!")
    
    # Запускаем планировщик (теперь он запускается в отдельном потоке)
    scheduler.start()
    
    # Запускаем асинхронные задачи в отдельном потоке
    async_thread = threading.Thread(target=run_async_tasks, daemon=True)
    async_thread.start()
    
    is_render = os.environ.get('RENDER') is not None
    retry_count = 0
    max_retries = 5 if not is_render else 1
    
    try:
        while retry_count < max_retries:
            try:
                bot.polling()
            except KeyboardInterrupt:
                logger.info("👋 Бот остановлен пользователем")
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
    finally:
        cleanup_resources()

if __name__ == "__main__":
    main()
