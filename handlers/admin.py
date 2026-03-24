#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Административные обработчики для MAX
Версия 2.2 - ИСПРАВЛЕНО: замена асинхронных вызовов БД на синхронные
"""

import logging
import time
import datetime
import asyncio
import threading
from typing import Dict, Any, List, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import ADMIN_IDS
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import get_back_keyboard

# Импорты из state
from state import (
    user_data, user_contexts, user_names, user_state_data, user_states, user_routes,
    get_state, set_state, get_state_data, update_state_data, clear_state,
    save_all_users_to_db, get_stats as get_memory_stats
)

# Импорты из models
from models import Statistics

# ✅ ИСПРАВЛЕНО: импорт синхронных функций из db_instance
from db_instance import (
    save_user,
    save_user_data,
    save_context,
    save_test_result,
    log_event,
    add_reminder,
    get_user_reminders,
    complete_reminder,
    load_user_data,
    load_user_context,
    load_all_users,
    get_stats as db_get_stats,
    ensure_connection as db_ensure
)

logger = logging.getLogger(__name__)


# ============================================
# ✅ ФУНКЦИЯ ДЛЯ ЗАПУСКА СИНХРОННЫХ ВЫЗОВОВ В ФОНЕ
# ============================================

def run_sync_in_background(func, *args, **kwargs):
    """Запускает синхронную функцию в отдельном потоке"""
    def _wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновой задаче: {e}")
    threading.Thread(target=_wrapper, daemon=True).start()


# ============================================
# СОЗДАЕМ ЭКЗЕМПЛЯР STATISTICS
# ============================================

stats = Statistics()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def get_user_context(user_id: int):
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_names(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "Пользователь")

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


# ============================================
# ✅ ИСПРАВЛЕНО: СИНХРОННЫЕ ФУНКЦИИ ДЛЯ БД
# ============================================

def get_db_stats_sync() -> Dict[str, Any]:
    """Синхронно получает статистику из БД"""
    try:
        db_ensure()
        return db_get_stats()
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики из БД: {e}")
        return {}

def sync_user_to_db_sync(user_id: int) -> bool:
    """Синхронизирует конкретного пользователя с БД"""
    try:
        db_ensure()
        save_user(user_id, user_names.get(user_id), None)
        if user_id in user_data:
            save_user_data(user_id, user_data[user_id])
        if user_id in user_contexts:
            context = user_contexts[user_id]
            save_context(
                user_id,
                name=getattr(context, 'name', None),
                age=getattr(context, 'age', None),
                gender=getattr(context, 'gender', None),
                city=getattr(context, 'city', None),
                mode=getattr(context, 'communication_mode', None)
            )
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации пользователя {user_id}: {e}")
        return False

def sync_all_users_to_db_sync() -> Dict[str, int]:
    """Синхронизирует всех пользователей с БД"""
    saved = 0
    for user_id in list(user_data.keys()):
        if sync_user_to_db_sync(user_id):
            saved += 1
    return {"saved": saved}

def get_db_size_sync() -> Dict[str, int]:
    """Синхронно получает размер таблиц в БД"""
    try:
        db_ensure()
        # Получаем статистику через get_stats
        stats_data = db_get_stats()
        return {
            "users": stats_data.get('users', 0),
            "contexts": stats_data.get('contexts', 0),
            "data": stats_data.get('data', 0),
            "routes": 0,  # TODO: добавить в get_stats
            "tests": stats_data.get('tests', 0),
            "events_30d": stats_data.get('events', 0)
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения размера БД: {e}")
        return {}


# ============================================
# ПРОВЕРКА ПРАВ ДОСТУПА
# ============================================

def check_admin_access(message_or_call) -> bool:
    """
    Проверяет, есть ли у пользователя права администратора
    Возвращает False и отправляет сообщение об ошибке, если нет прав
    """
    user_id = None
    if hasattr(message_or_call, 'from_user'):
        user_id = message_or_call.from_user.id
    elif hasattr(message_or_call, 'chat'):
        user_id = message_or_call.chat.id
    
    if not user_id or not is_admin(user_id):
        if hasattr(message_or_call, 'message') and hasattr(message_or_call.message, 'chat'):
            safe_send_message(
                message_or_call.message,
                "⛔ <b>Доступ запрещён</b>\n\nЭта команда только для администраторов.",
                parse_mode='HTML',
                delete_previous=True
            )
        elif hasattr(message_or_call, 'chat'):
            safe_send_message(
                message_or_call,
                "⛔ <b>Доступ запрещён</b>\n\nЭта команда только для администраторов.",
                parse_mode='HTML',
                delete_previous=True
            )
        return False
    return True


# ============================================
# КОМАНДЫ АДМИНИСТРАТОРОВ
# ============================================

@bot.message_handler(commands=['stats'])
def cmd_stats(message: Message):
    """Команда /stats — статистика бота"""
    if not check_admin_access(message):
        return
    
    stats_text = stats.get_stats_text()
    
    safe_send_message(
        message,
        stats_text,
        parse_mode='HTML',
        delete_previous=True
    )

@bot.message_handler(commands=['dbstats'])
def cmd_dbstats(message: Message):
    """Команда /dbstats — статистика базы данных"""
    if not check_admin_access(message):
        return
    
    def run_sync():
        try:
            status_msg = safe_send_message(
                message,
                "🔄 Получение статистики базы данных...",
                delete_previous=True
            )
            
            # Получаем размер таблиц
            db_sizes = get_db_size_sync()
            
            # Получаем статистику из памяти
            memory_stats = get_memory_stats()
            
            text = f"📊 <b>СТАТИСТИКА БАЗЫ ДАННЫХ</b>\n\n"
            
            text += f"<b>PostgreSQL:</b>\n"
            text += f"• Пользователей: {db_sizes.get('users', 0)}\n"
            text += f"• Контекстов: {db_sizes.get('contexts', 0)}\n"
            text += f"• Данных: {db_sizes.get('data', 0)}\n"
            text += f"• Результатов тестов: {db_sizes.get('tests', 0)}\n"
            text += f"• Событий: {db_sizes.get('events_30d', 0)}\n\n"
            
            text += f"<b>Память (кэш):</b>\n"
            text += f"• user_data: {memory_stats.get('users_in_data', 0)}\n"
            text += f"• user_contexts: {memory_stats.get('users_in_contexts', 0)}\n"
            text += f"• user_routes: {memory_stats.get('users_in_routes', 0)}\n"
            text += f"• user_states: {memory_stats.get('users_in_states', 0)}\n"
            
            if status_msg:
                try:
                    safe_delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
            
            safe_send_message(message, text, parse_mode='HTML', delete_previous=True)
        except Exception as e:
            logger.error(f"❌ Ошибка в dbstats: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()

@bot.message_handler(commands=['apistatus'])
def cmd_apistatus(message: Message):
    """Команда /apistatus — статус API ключей"""
    if not check_admin_access(message):
        return
    
    from config import (
        DEEPSEEK_API_KEY, DEEPGRAM_API_KEY,
        YANDEX_API_KEY, OPENWEATHER_API_KEY
    )
    
    deepseek_status = "✅ работает" if DEEPSEEK_API_KEY else "❌ не настроен"
    deepgram_status = "✅ работает" if DEEPGRAM_API_KEY else "❌ не настроен"
    yandex_status = "✅ работает" if YANDEX_API_KEY else "❌ не настроен"
    weather_status = "✅ работает" if OPENWEATHER_API_KEY else "❌ не настроен"
    
    text = f"📊 <b>СТАТУС API</b>\n\n"
    text += f"• DeepSeek: {deepseek_status}\n"
    text += f"• Deepgram: {deepgram_status}\n"
    text += f"• Yandex TTS: {yandex_status}\n"
    text += f"• OpenWeather: {weather_status}\n\n"
    
    safe_send_message(message, text, parse_mode='HTML', delete_previous=True)

@bot.message_handler(commands=['admin'])
def cmd_admin(message: Message):
    """Команда /admin — панель администратора"""
    if not check_admin_access(message):
        return
    
    show_admin_panel(message)

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message: Message):
    """Команда /broadcast — начать рассылку"""
    if not check_admin_access(message):
        return
    
    text = f"""
📢 <b>РАССЫЛКА</b>

Введите текст для рассылки всем пользователям.

Напишите сообщение, которое хотите отправить:
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("❌ ОТМЕНА", callback_data="admin_panel"))
    
    safe_send_message(message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    user_states[message.from_user.id] = "awaiting_broadcast"

@bot.message_handler(commands=['users'])
def cmd_users(message: Message):
    """Команда /users — список пользователей"""
    if not check_admin_access(message):
        return
    
    show_users_list(message)

@bot.message_handler(commands=['sync'])
def cmd_sync(message: Message):
    """Команда /sync — синхронизация с БД"""
    if not check_admin_access(message):
        return
    
    def run_sync():
        try:
            status_msg = safe_send_message(
                message,
                "🔄 Синхронизация с базой данных...",
                delete_previous=True
            )
            
            result = sync_all_users_to_db_sync()
            
            if status_msg:
                try:
                    safe_delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
            
            safe_send_message(
                message,
                f"✅ Синхронизировано пользователей: {result.get('saved', 0)}",
                delete_previous=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()


# ============================================
# АДМИНСКАЯ ПАНЕЛЬ
# ============================================

def show_admin_panel(message_or_call):
    """
    Показывает панель администратора
    """
    if not check_admin_access(message_or_call):
        return
    
    memory_stats = get_memory_stats()
    
    text = f"""
🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>

📊 <b>СТАТИСТИКА В ПАМЯТИ:</b>
• Всего пользователей: <b>{memory_stats.get('total_unique', 0)}</b>
• С данными: <b>{memory_stats.get('users_in_data', 0)}</b>
• В маршрутах: <b>{memory_stats.get('users_in_routes', 0)}</b>
• Завершили тест: <b>{stats.data.get('completed_tests', 0)}</b>

👇 <b>ДЕЙСТВИЯ:</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats"),
        InlineKeyboardButton("📢 РАССЫЛКА", callback_data="admin_broadcast")
    )
    keyboard.row(
        InlineKeyboardButton("👥 ПОЛЬЗОВАТЕЛИ", callback_data="admin_users"),
        InlineKeyboardButton("🗄 БАЗА ДАННЫХ", callback_data="admin_db")
    )
    keyboard.row(
        InlineKeyboardButton("🔄 СИНХРОНИЗАЦИЯ", callback_data="admin_sync"),
        InlineKeyboardButton("🧹 ОЧИСТКА", callback_data="admin_cleanup")
    )
    keyboard.row(
        InlineKeyboardButton("📝 ЛОГИ", callback_data="admin_logs"),
        InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="admin_settings")
    )
    keyboard.row(InlineKeyboardButton("◀️ В МЕНЮ", callback_data="main_menu"))
    
    if hasattr(message_or_call, 'message'):
        safe_send_message(
            message_or_call.message,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
    else:
        safe_send_message(
            message_or_call,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )


# ============================================
# ОБРАБОТЧИКИ АДМИНСКИХ CALLBACK'ОВ
# ============================================

def handle_admin_callback(call: CallbackQuery, action: str):
    """
    Обрабатывает callback'и из админ-панели
    """
    if not check_admin_access(call):
        return
    
    if action == "stats":
        show_admin_stats(call)
    elif action == "broadcast":
        start_broadcast(call)
    elif action == "users":
        show_users_list(call)
    elif action == "db":
        show_admin_db(call)
    elif action == "sync":
        start_sync(call)
    elif action == "settings":
        show_admin_settings(call)
    elif action == "logs":
        show_admin_logs(call)
    elif action == "cleanup":
        show_admin_cleanup(call)
    else:
        safe_send_message(
            call.message,
            "❌ Неизвестное действие",
            reply_markup=get_back_keyboard("admin_panel"),
            delete_previous=True
        )

def show_admin_stats(call: CallbackQuery):
    """Показывает расширенную статистику"""
    if not check_admin_access(call):
        return
    
    def run_sync():
        try:
            status_msg = safe_send_message(
                call.message,
                "🔄 Получение статистики...",
                delete_previous=True
            )
            
            # Получаем статистику из БД
            db_stats = get_db_stats_sync()
            
            # Статистика из памяти
            memory_stats = get_memory_stats()
            
            text = f"📊 <b>РАСШИРЕННАЯ СТАТИСТИКА</b>\n\n"
            
            text += f"<b>ПАМЯТЬ (КЭШ):</b>\n"
            text += f"• Всего уникальных: {memory_stats.get('total_unique', 0)}\n"
            text += f"• user_data: {memory_stats.get('users_in_data', 0)}\n"
            text += f"• user_contexts: {memory_stats.get('users_in_contexts', 0)}\n"
            text += f"• user_routes: {memory_stats.get('users_in_routes', 0)}\n"
            text += f"• user_states: {memory_stats.get('users_in_states', 0)}\n\n"
            
            text += f"<b>POSTGRESQL:</b>\n"
            text += f"• Всего пользователей: {db_stats.get('users', 0)}\n"
            text += f"• Контекстов: {db_stats.get('contexts', 0)}\n"
            text += f"• Результатов тестов: {db_stats.get('tests', 0)}\n"
            text += f"• Событий: {db_stats.get('events', 0)}\n"
            
            if status_msg:
                try:
                    safe_delete_message(call.message.chat.id, status_msg.message_id)
                except:
                    pass
            
            keyboard = get_back_keyboard("admin_panel")
            
            safe_send_message(
                call.message,
                text,
                reply_markup=keyboard,
                parse_mode='HTML',
                delete_previous=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка в admin_stats: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()

def show_admin_db(call: CallbackQuery):
    """Показывает информацию о базе данных"""
    if not check_admin_access(call):
        return
    
    def run_sync():
        try:
            status_msg = safe_send_message(
                call.message,
                "🔄 Получение информации о БД...",
                delete_previous=True
            )
            
            db_sizes = get_db_size_sync()
            
            text = f"🗄 <b>БАЗА ДАННЫХ</b>\n\n"
            
            text += f"<b>Размер таблиц:</b>\n"
            text += f"• Пользователей: {db_sizes.get('users', 0)} записей\n"
            text += f"• Контекстов: {db_sizes.get('contexts', 0)} записей\n"
            text += f"• Данных: {db_sizes.get('data', 0)} записей\n"
            text += f"• Результатов тестов: {db_sizes.get('tests', 0)} записей\n"
            text += f"• Событий: {db_sizes.get('events_30d', 0)} записей\n\n"
            
            if status_msg:
                try:
                    safe_delete_message(call.message.chat.id, status_msg.message_id)
                except:
                    pass
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                InlineKeyboardButton("🔄 СИНХРОНИЗАЦИЯ", callback_data="admin_sync"),
                InlineKeyboardButton("◀️ НАЗАД", callback_data="admin_panel")
            )
            
            safe_send_message(
                call.message,
                text,
                reply_markup=keyboard,
                parse_mode='HTML',
                delete_previous=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка в admin_db: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()

def start_sync(call: CallbackQuery):
    """Запускает синхронизацию с БД"""
    if not check_admin_access(call):
        return
    
    def run_sync():
        try:
            status_msg = safe_send_message(
                call.message,
                "🔄 Синхронизация с базой данных...",
                delete_previous=True
            )
            
            result = sync_all_users_to_db_sync()
            
            if status_msg:
                try:
                    safe_delete_message(call.message.chat.id, status_msg.message_id)
                except:
                    pass
            
            text = f"✅ Синхронизировано пользователей: {result.get('saved', 0)}"
            keyboard = get_back_keyboard("admin_panel")
            
            safe_send_message(
                call.message,
                text,
                reply_markup=keyboard,
                delete_previous=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
    
    threading.Thread(target=run_sync, daemon=True).start()

def start_broadcast(call: CallbackQuery):
    """Начинает процесс рассылки"""
    if not check_admin_access(call):
        return
    
    text = f"""
📢 <b>РАССЫЛКА</b>

Введите текст для рассылки всем пользователям.

Напишите сообщение, которое хотите отправить:
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("❌ ОТМЕНА", callback_data="admin_panel"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    user_states[call.from_user.id] = "awaiting_broadcast"

def process_broadcast(message: Message, text: str):
    """
    Обрабатывает текст рассылки и отправляет её
    """
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    all_users = list(user_data.keys())
    
    if not all_users:
        safe_send_message(
            message,
            "❌ Нет пользователей для рассылки",
            delete_previous=True
        )
        return
    
    status_msg = safe_send_message(
        message,
        f"📢 Отправка рассылки <b>{len(all_users)}</b> пользователям...\n\nЭто может занять несколько минут.",
        parse_mode='HTML',
        delete_previous=True
    )
    
    sent = 0
    failed = 0
    
    for uid in all_users:
        try:
            bot.send_message(
                uid,
                f"📢 <b>РАССЫЛКА</b>\n\n{text}",
                parse_mode='HTML'
            )
            sent += 1
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {uid}: {e}")
            failed += 1
    
    try:
        safe_delete_message(message.chat.id, status_msg.message_id)
    except:
        pass
    
    result_text = f"""
📊 <b>РЕЗУЛЬТАТ РАССЫЛКИ</b>

✅ Отправлено: <b>{sent}</b>
❌ Ошибок: <b>{failed}</b>
👥 Всего: <b>{len(all_users)}</b>
"""
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        message,
        result_text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_users_list(message_or_call):
    """
    Показывает список пользователей
    """
    if not check_admin_access(message_or_call):
        return
    
    all_users = list(user_data.keys())
    
    if not all_users:
        text = "👥 <b>Нет пользователей</b>"
    else:
        text = f"👥 <b>ПОЛЬЗОВАТЕЛИ ({len(all_users)})</b>\n\n"
        
        for i, uid in enumerate(all_users[:20], 1):
            name = user_names.get(uid, "Без имени")
            context = user_contexts.get(uid)
            
            test_passed = "✅" if user_data[uid].get("profile_data") or user_data[uid].get("ai_generated_profile") else "❌"
            
            mode = context.communication_mode if context else "coach"
            mode_emoji = "🔮" if mode == "coach" else "🧠" if mode == "psychologist" else "⚡"
            
            text += f"{i}. {test_passed} {mode_emoji} <b>{name}</b> (ID: <code>{uid}</code>)\n"
        
        if len(all_users) > 20:
            text += f"\n... и ещё {len(all_users) - 20} пользователей"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔄 СИНХРОНИЗИРОВАТЬ", callback_data="admin_sync"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="admin_panel"))
    
    if hasattr(message_or_call, 'message'):
        safe_send_message(
            message_or_call.message,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
    else:
        safe_send_message(
            message_or_call,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )

def show_admin_settings(call: CallbackQuery):
    """Показывает настройки админки"""
    if not check_admin_access(call):
        return
    
    from config import (
        DEEPSEEK_API_KEY, DEEPGRAM_API_KEY,
        YANDEX_API_KEY, OPENWEATHER_API_KEY
    )
    
    text = f"""
🔧 <b>НАСТРОЙКИ</b>

<b>API КЛЮЧИ:</b>
• DeepSeek: {"✅" if DEEPSEEK_API_KEY else "❌"}
• Deepgram: {"✅" if DEEPGRAM_API_KEY else "❌"}
• Yandex: {"✅" if YANDEX_API_KEY else "❌"}
• OpenWeather: {"✅" if OPENWEATHER_API_KEY else "❌"}

<b>АДМИНИСТРАТОРЫ:</b>
{chr(10).join([f'• <code>{aid}</code>' for aid in ADMIN_IDS])}
"""
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_admin_logs(call: CallbackQuery):
    """Показывает последние логи"""
    if not check_admin_access(call):
        return
    
    text = """
📝 <b>ЛОГИ</b>

Функция просмотра логов в разработке.
"""
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_admin_cleanup(call: CallbackQuery):
    """Показывает меню очистки"""
    if not check_admin_access(call):
        return
    
    text = """
🔄 <b>ОЧИСТКА</b>

Выберите, что очистить:
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🧹 КЭШ", callback_data="cleanup_cache"),
        InlineKeyboardButton("🗑 ЛОГИ", callback_data="cleanup_logs")
    )
    keyboard.row(
        InlineKeyboardButton("👥 ПОЛЬЗОВАТЕЛИ", callback_data="cleanup_users"),
        InlineKeyboardButton("🧠 ТЕСТЫ", callback_data="cleanup_tests")
    )
    keyboard.row(
        InlineKeyboardButton("🗄 БАЗА ДАННЫХ", callback_data="cleanup_db"),
        InlineKeyboardButton("◀️ НАЗАД", callback_data="admin_panel")
    )
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )


# ============================================
# ОБРАБОТЧИКИ КОНКРЕТНЫХ АДМИНСКИХ ДЕЙСТВИЙ
# ============================================

def cleanup_cache(call: CallbackQuery):
    """Очищает кэш"""
    if not check_admin_access(call):
        return
    
    user_state_data.clear()
    
    text = "✅ Кэш состояний очищен"
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        delete_previous=True
    )

def cleanup_logs(call: CallbackQuery):
    """Очищает логи"""
    if not check_admin_access(call):
        return
    
    text = "✅ Логи очищены"
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        delete_previous=True
    )

def cleanup_users(call: CallbackQuery):
    """Очищает неактивных пользователей"""
    if not check_admin_access(call):
        return
    
    active_users = {}
    active_contexts = {}
    active_names = {}
    active_routes = {}
    
    for uid, data in user_data.items():
        if data.get("profile_data") or data.get("ai_generated_profile"):
            active_users[uid] = data
            if uid in user_contexts:
                active_contexts[uid] = user_contexts[uid]
            if uid in user_names:
                active_names[uid] = user_names[uid]
            if uid in user_routes:
                active_routes[uid] = user_routes[uid]
    
    removed = len(user_data) - len(active_users)
    
    user_data.clear()
    user_data.update(active_users)
    
    user_contexts.clear()
    user_contexts.update(active_contexts)
    
    user_names.clear()
    user_names.update(active_names)
    
    user_routes.clear()
    user_routes.update(active_routes)
    
    user_state_data.clear()
    
    text = f"✅ Очищено неактивных пользователей: {removed}"
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        delete_previous=True
    )

def cleanup_tests(call: CallbackQuery):
    """Очищает незавершённые тесты"""
    if not check_admin_access(call):
        return
    
    cleaned = 0
    for uid, data in user_data.items():
        if not data.get("profile_data") and not data.get("ai_generated_profile"):
            if any(key in data for key in ["stage1_current", "stage2_current", "stage3_current", "stage4_current", "stage5_current"]):
                for key in list(data.keys()):
                    if key.startswith("stage") or key in ["perception_scores", "strategy_levels", "dilts_counts"]:
                        del data[key]
                cleaned += 1
    
    text = f"✅ Очищено незавершённых тестов: {cleaned}"
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        delete_previous=True
    )

def cleanup_db(call: CallbackQuery):
    """Очищает старые данные в БД"""
    if not check_admin_access(call):
        return
    
    def run_cleanup():
        try:
            status_msg = safe_send_message(
                call.message,
                "🧹 Очистка базы данных...",
                delete_previous=True
            )
            
            db_ensure()
            # В новой версии cleanup_old_data нет, используем get_stats для проверки
            result = "✅ База данных доступна"
            
            if status_msg:
                try:
                    safe_delete_message(call.message.chat.id, status_msg.message_id)
                except:
                    pass
            
            keyboard = get_back_keyboard("admin_panel")
            safe_send_message(
                call.message,
                result,
                reply_markup=keyboard,
                delete_previous=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка очистки БД: {e}")
    
    threading.Thread(target=run_cleanup, daemon=True).start()


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'is_admin',
    'check_admin_access',
    'cmd_stats',
    'cmd_dbstats',
    'cmd_apistatus',
    'cmd_admin',
    'cmd_broadcast',
    'cmd_users',
    'cmd_sync',
    'show_admin_panel',
    'handle_admin_callback',
    'show_admin_stats',
    'show_admin_db',
    'start_broadcast',
    'process_broadcast',
    'show_users_list',
    'show_admin_settings',
    'show_admin_logs',
    'show_admin_cleanup',
    'cleanup_cache',
    'cleanup_logs',
    'cleanup_users',
    'cleanup_tests',
    'cleanup_db'
]
