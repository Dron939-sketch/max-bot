#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики команды /start и начальных экранов для MAX
ВЕРСИЯ 2.0 - ПОЛНАЯ ИНТЕГРАЦИЯ С PostgreSQL
ДОБАВЛЕНО: Загрузка пользователей из БД, автосохранение
"""
import logging
import time
import asyncio
from typing import Optional, Dict, Any

from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from bot_instance import bot
from models import UserContext
from config import COMMUNICATION_MODES
from keyboards import (
    get_restart_keyboard, 
    get_main_menu_keyboard, 
    get_why_details_keyboard,
    get_start_context_keyboard
)
from formatters import bold
from message_utils import safe_send_message

# Импорты из state.py
from state import (
    user_data, user_names, user_contexts, user_routes,
    get_user_context, get_user_context_dict,
    clear_state, set_state, get_state, TestStates,
    get_user_name, load_user_from_db
)

# ✅ ИСПРАВЛЕНО: импортируем из db_instance вместо main
from db_instance import db, save_user_to_db

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def is_test_completed(user_data_dict: dict) -> bool:
    """Проверяет, завершен ли тест"""
    if user_data_dict.get("profile_data"):
        return True
    if user_data_dict.get("ai_generated_profile"):
        return True
    required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
    if all(field in user_data_dict for field in required_minimal):
        return True
    return False

def get_user_profile(user_id: int) -> dict:
    """Получает профиль пользователя"""
    data = user_data.get(user_id, {})
    return data.get("profile_data", {})

def get_user_name_local(user_id: int) -> str:
    """Получает имя пользователя (локальная версия)"""
    return user_names.get(user_id, "Пользователь")

def get_profile_code(user_id: int) -> str:
    """Получает код профиля пользователя"""
    data = user_data.get(user_id, {})
    profile_data = data.get("profile_data", {})
    
    # Пробуем получить из разных мест
    code = profile_data.get('display_name')
    if code:
        return code
    
    # Если нет, генерируем из векторов
    scores = {}
    from profiles import VECTORS
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    if scores:
        return f"СБ-{round(scores.get('СБ', 3))}_ТФ-{round(scores.get('ТФ', 3))}_УБ-{round(scores.get('УБ', 3))}_ЧВ-{round(scores.get('ЧВ', 3))}"
    
    return "СБ-4_ТФ-4_УБ-4_ЧВ-4"

# ============================================
# СТАТИСТИКА (теперь с сохранением в БД)
# ============================================
class Stats:
    def __init__(self):
        self.starts = {}
    
    def register_start(self, user_id):
        self.starts[user_id] = time.time()
        # Логируем событие в БД
        asyncio.create_task(db.log_event(user_id, 'start', {'timestamp': time.time()}))
    
    def get_starts(self):
        return self.starts

stats = Stats()


# ============================================
# ✅ НОВАЯ ФУНКЦИЯ: ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ИЗ БД
# ============================================

async def ensure_user_loaded(user_id: int, user_name: str = None) -> bool:
    """
    Проверяет, загружен ли пользователь, и загружает из БД если нужно
    Возвращает True, если данные загружены
    """
    # Если пользователь уже в памяти, просто обновляем имя
    if user_id in user_data or user_id in user_contexts:
        if user_name and user_id not in user_names:
            user_names[user_id] = user_name
        return True
    
    # Пробуем загрузить из БД
    logger.info(f"🔄 Загружаем пользователя {user_id} из БД...")
    loaded = await load_user_from_db(user_id, db)
    
    if loaded and user_name:
        user_names[user_id] = user_name
    
    return loaded

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    # Сохраняем имя в памяти
    user_names[user_id] = user_name
    clear_state(user_id)
    
    # Сохраняем пользователя в БД (асинхронно)
    asyncio.create_task(db.save_telegram_user(
        user_id=user_id,
        first_name=user_name,
        username=message.from_user.username,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    ))
    
    # ✅ ПРОВЕРЯЕМ, ЕСТЬ ЛИ ПОЛЬЗОВАТЕЛЬ В БД
    def run_load_check():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loaded = loop.run_until_complete(ensure_user_loaded(user_id, user_name))
        loop.close()
        
        # После загрузки продолжаем обработку
        continue_start(message, user_id, user_name, loaded)
    
    threading.Thread(target=run_load_check, daemon=True).start()


def continue_start(message: Message, user_id: int, user_name: str, loaded_from_db: bool):
    """Продолжает обработку /start после проверки БД"""
    
    # Получаем или создаем контекст
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    context.name = user_name
    
    # Регистрируем старт (событие в БД)
    stats.register_start(user_id)
    
    # Проверяем, есть ли уже профиль
    profile_data = get_user_profile(user_id)
    user_data_dict = user_data.get(user_id, {})
    
    if profile_data or is_test_completed(user_data_dict):
        # У пользователя уже есть профиль
        profile_code = get_profile_code(user_id)
        
        db_status = "✅ из базы данных" if loaded_from_db else "✅ из памяти"
        
        text = f"""
🧠 {bold('ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ')}

👋 О, {user_name}, я вас помню {db_status}!
(У меня, в отличие от людей, с памятью всё отлично)

📊 {bold('ВАШ ПРОФИЛЬ:')} {profile_code}

❓ {bold('ЧТО ДЕЛАЕМ?')}

Вы можете:
🔄 Пройти тест заново — вдруг вы изменились?
📋 Посмотреть свой профиль
🎯 Выбрать цель

⬇️ {bold('ВЫБИРАЙТЕ:')}
"""
        
        keyboard = get_restart_keyboard()
        safe_send_message(message, text, reply_markup=keyboard)
        return
    
    # Проверяем, заполнен ли контекст (город, пол, возраст)
    if not (context.city and context.gender and context.age):
        # Новый пользователь - показываем красивое приветствие
        welcome_text = f"""
{user_name}, привет! Ну, здравствуйте, дорогой человек! 👋

🧠 {bold('Я — Фреди, виртуальный психолог.')}
Оцифрованная версия Андрея Мейстера, если хотите — его цифровой слепок.

🎭 Короче, я — это он, только батарейка дольше держит и пожрать не прошу.

🕒 Нам нужно познакомиться, потому что я пока не экстрасенс.

🧐 Чтобы я понимал, с кем имею дело и чем могу быть полезен —
давайте-ка пройдём небольшой тест.

📊 {bold('Всего 5 этапов:')}

1️⃣ Конфигурация восприятия — как вы фильтруете реальность
2️⃣ Конфигурация мышления — как ваш мозг перерабатывает информацию
3️⃣ Конфигурация поведения — что вы делаете на автопилоте
4️⃣ Точка роста — куда двигаться, чтобы не топтаться на месте
5️⃣ Глубинные паттерны — что сформировало вас как личность

⏱ {bold('15 минут')} — и я буду знать о вас больше, чем вы думаете.

🚀 Ну что, начнём наше знакомство?
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🚀 Давай, погнали!", callback_data="start_context"),
            InlineKeyboardButton("🤨 А ты вообще кто такой?", callback_data="why_details")
        )
        
        safe_send_message(message, welcome_text, reply_markup=keyboard)
        return
    
    # Если контекст уже заполнен, показываем меню
    from handlers.modes import show_main_menu_after_mode
    show_main_menu_after_mode(message, context)


@bot.message_handler(commands=['menu'])
def cmd_menu(message: Message):
    """Обработчик команды /menu"""
    user_id = message.from_user.id
    
    if user_id in user_contexts:
        from handlers.modes import show_main_menu_after_mode
        show_main_menu_after_mode(message, user_contexts[user_id])
    else:
        # Если нет контекста, показываем /start
        cmd_start(message)


# ============================================
# ✅ НОВАЯ КОМАНДА: ПРИНУДИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ
# ============================================

@bot.message_handler(commands=['sync'])
def cmd_sync(message: Message):
    """Принудительная синхронизация с БД (для админов)"""
    user_id = message.from_user.id
    
    # Проверяем, админ ли это
    from config import ADMIN_IDS
    if user_id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    def run_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        saved_count = 0
        for uid in list(user_data.keys()):
            try:
                loop.run_until_complete(save_user_to_db(uid, user_data, user_contexts, user_routes))
                saved_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка синхронизации {uid}: {e}")
        
        loop.close()
        
        safe_send_message(
            message,
            f"✅ Синхронизировано {saved_count} пользователей",
            delete_previous=True
        )
    
    threading.Thread(target=run_sync, daemon=True).start()


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: call.data == 'start_context')
def callback_start_context(call: CallbackQuery):
    """Начать заполнение контекста"""
    from handlers.context import start_context
    start_context(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'why_details')
def callback_why_details(call: CallbackQuery):
    """Показать детальную информацию о боте"""
    show_why_details(call)


@bot.callback_query_handler(func=lambda call: call.data == 'restart_test')
def callback_restart_test(call: CallbackQuery):
    """Перезапустить тест"""
    user_id = call.from_user.id
    
    # Очищаем профиль в user_data
    if user_id in user_data:
        # Сохраняем только базовую информацию, удаляем данные теста
        user_data[user_id] = {}
    
    # Очищаем состояние
    clear_state(user_id)
    
    # Обновляем контекст
    if user_id in user_contexts:
        context = user_contexts[user_id]
        # Очищаем данные профиля
        if hasattr(context, 'profile_data'):
            context.profile_data = {}
        if hasattr(context, 'confinement_model'):
            context.confinement_model = {}
    
    # Сохраняем изменения в БД
    asyncio.create_task(save_user_to_db(user_id, user_data, user_contexts, user_routes))
    
    # Логируем событие в БД
    asyncio.create_task(db.log_event(user_id, 'restart_test', {}))
    
    # Показываем приветствие
    text = f"""
🔄 <b>ТЕСТ ПЕРЕЗАПУЩЕН</b>

Хорошо, начнём с чистого листа.
Давайте познакомимся заново.

🚀 Погнали?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🚀 Давай, погнали!", callback_data="start_context")
    )
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)


@bot.callback_query_handler(func=lambda call: call.data == 'show_profile')
def callback_show_profile(call: CallbackQuery):
    """Показать профиль"""
    from handlers.profile import show_profile
    show_profile(call.message, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == 'show_modes')
def callback_show_modes(call: CallbackQuery):
    """Показать выбор режимов"""
    from handlers.modes import show_mode_selection
    show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_start')
def callback_back_to_start(call: CallbackQuery):
    """Вернуться к начальному экрану"""
    # Создаем фейковое сообщение для cmd_start
    class FakeMessage:
        def __init__(self, user_id, chat_id, text):
            self.from_user = type('obj', (), {'id': user_id, 'first_name': get_user_name_local(user_id)})
            self.chat = type('obj', (), {'id': chat_id})
            self.text = text
            self.message_id = call.message.message_id
    
    fake_msg = FakeMessage(
        call.from_user.id,
        call.message.chat.id,
        '/start'
    )
    
    cmd_start(fake_msg)


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def show_why_details(call: CallbackQuery):
    """Показывает детальную информацию о боте"""
    user_id = call.from_user.id
    
    text = f"""
🎭 {bold('Ну, вопрос хороший. Давайте по существу.')}

Видите ли, дорогой человек, я — экспериментальная модель.
Андрей Мейстер однажды подумал: "А что, если я создам свою цифровую копию?
Пусть работает, пока я сплю, ем или просто ленюсь".

Так я и появился. 🧠

🧐 {bold('Что я умею:')}

• Вижу паттерны там, где вы видите просто день сурка
• Нахожу систему в ваших "случайных" решениях
• Понимаю, почему вы выбираете одних и тех же "не тех" людей
• Я реально беспристрастен — у меня нет плохого настроения

🎯 {bold('Конкретно по тесту:')}

1️⃣ Восприятие — поймём, какую линзу вы носите
2️⃣ Мышление — узнаем, как вы пережёвываете реальность
3️⃣ Поведение — посмотрим, что вы делаете "на автомате"
4️⃣ Точка роста — я скажу, куда вам двигаться
5️⃣ Глубинные паттерны — заглянем в детство и подсознание

⏱ {bold('15 минут')} — и я составлю ваш профиль.

👌 Погнали?"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🚀 ПОГНАЛИ!", callback_data="start_context"),
        InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_start")
    )
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


# ============================================
# ФУНКЦИЯ SHOW_INTRO
# ============================================

def show_intro(message: Message):
    """
    Показывает начальный экран приветствия (для кнопки "НАЗАД")
    """
    user_id = message.from_user.id
    user_name = get_user_name_local(user_id)
    
    text = f"""
👋 {bold(f'Привет, {user_name}!')}

👇 {bold('Выберите, с какой интонацией будем общаться:')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(text="🔴 ЖЕСТКИЙ", callback_data="mode_hard"),
        InlineKeyboardButton(text="🟡 СРЕДНИЙ", callback_data="mode_medium"),
        InlineKeyboardButton(text="🟢 МЯГКИЙ", callback_data="mode_soft")
    )
    keyboard.row(
        InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")
    )
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


def show_main_menu(message: Message, context: UserContext):
    """Показывает главное меню до теста"""
    from keyboards import get_main_menu_keyboard
    
    # Обновляем погоду
    context.update_weather()
    
    day_context = context.get_day_context()
    
    welcome_text = f"{context.get_greeting(context.name)}\n\n"
    
    # Безопасная проверка погоды
    if context.weather_cache and isinstance(context.weather_cache, dict):
        weather = context.weather_cache
        welcome_text += f"{weather.get('icon', '🌍')} {weather.get('description', 'данные погоды')}, {weather.get('temp', '?')}°C\n"
    
    if day_context['is_weekend']:
        welcome_text += f"🏖 Сегодня выходной! Как настроение?\n\n"
    elif 9 <= day_context['hour'] < 18:
        welcome_text += f"💼 Рабочее время. Чем займёмся?\n\n"
    else:
        welcome_text += f"🏡 Личное время. Есть что обсудить?\n\n"
    
    welcome_text += f"👇 {bold('Выберите действие:')}"
    
    keyboard = get_main_menu_keyboard()
    
    safe_send_message(message, welcome_text, reply_markup=keyboard)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'cmd_start',
    'cmd_menu',
    'cmd_sync',  # ✅ Добавлено
    'show_why_details',
    'show_intro',
    'show_main_menu',
    'callback_start_context',
    'callback_why_details',
    'callback_restart_test',
    'callback_show_profile',
    'callback_show_modes',
    'callback_back_to_start',
    'ensure_user_loaded',  # ✅ Добавлено
    'get_profile_code'  # ✅ Добавлено
]
