#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Административные обработчики для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import logging
import time
import datetime
from typing import Dict, Any, List, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import ADMIN_IDS
from message_utils import safe_send_message, safe_edit_message, safe_delete_message
from keyboards import get_back_keyboard

# ✅ ИСПРАВЛЕНО: Импортируем из state, а не из main
from state import (
    user_data, user_contexts, user_names, user_state_data, user_states,
    get_state, set_state, get_state_data, update_state_data, clear_state
)

# ✅ ИСПРАВЛЕНО: Импортируем Statistics из models, а не из main
from models import Statistics

logger = logging.getLogger(__name__)

# ============================================
# СОЗДАЕМ ЭКЗЕМПЛЯР STATISTICS
# ============================================

# Создаем экземпляр статистики
stats = Statistics()

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (теперь используют state)
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
            # Это callback
            safe_send_message(
                message_or_call.message,
                "⛔ <b>Доступ запрещён</b>\n\nЭта команда только для администраторов.",
                parse_mode='HTML',
                delete_previous=True
            )
        elif hasattr(message_or_call, 'chat'):
            # Это message
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
    
    # ✅ ИСПРАВЛЕНО: используем импортированный user_states из state
    user_states[message.from_user.id] = "awaiting_broadcast"

@bot.message_handler(commands=['users'])
def cmd_users(message: Message):
    """Команда /users — список пользователей"""
    if not check_admin_access(message):
        return
    
    show_users_list(message)

# ============================================
# АДМИНСКАЯ ПАНЕЛЬ
# ============================================

def show_admin_panel(message_or_call):
    """
    Показывает панель администратора
    """
    if not check_admin_access(message_or_call):
        return
    
    # Собираем статистику
    total_users = len(user_data)
    active_today = 0
    # Подсчёт активных за сегодня
    today = datetime.datetime.now().date()
    for uid, data in user_data.items():
        last_active = data.get('last_active')
        if last_active and hasattr(last_active, 'date') and last_active.date() == today:
            active_today += 1
    
    text = f"""
🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>

📊 <b>СТАТИСТИКА:</b>
• Всего пользователей: <b>{total_users}</b>
• Активных сегодня: <b>{active_today}</b>
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
        InlineKeyboardButton("🔧 НАСТРОЙКИ", callback_data="admin_settings")
    )
    keyboard.row(
        InlineKeyboardButton("📝 ЛОГИ", callback_data="admin_logs"),
        InlineKeyboardButton("🔄 ОЧИСТКА", callback_data="admin_cleanup")
    )
    keyboard.row(InlineKeyboardButton("◀️ В МЕНЮ", callback_data="main_menu"))
    
    if hasattr(message_or_call, 'message'):
        # Это callback
        safe_send_message(
            message_or_call.message,
            text,
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
    else:
        # Это message
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
    
    stats_text = stats.get_stats_text()
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        stats_text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

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
    
    # ✅ ИСПРАВЛЕНО: используем импортированный user_states из state
    user_states[call.from_user.id] = "awaiting_broadcast"

def process_broadcast(message: Message, text: str):
    """
    Обрабатывает текст рассылки и отправляет её
    """
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    # Получаем список всех пользователей
    all_users = list(user_data.keys())
    
    if not all_users:
        safe_send_message(
            message,
            "❌ Нет пользователей для рассылки",
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        f"📢 Отправка рассылки <b>{len(all_users)}</b> пользователям...\n\nЭто может занять несколько минут.",
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Счётчики
    sent = 0
    failed = 0
    
    # Отправляем каждому пользователю
    for uid in all_users:
        try:
            bot.send_message(
                uid,
                f"📢 <b>РАССЫЛКА</b>\n\n{text}",
                parse_mode='HTML'
            )
            sent += 1
            time.sleep(0.05)  # Небольшая задержка, чтобы не заблокировали
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {uid}: {e}")
            failed += 1
    
    # Удаляем статусное сообщение
    try:
        safe_delete_message(message.chat.id, status_msg.message_id)
    except:
        pass
    
    # Отправляем отчёт
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
        
        # Показываем первых 20
        for i, uid in enumerate(all_users[:20], 1):
            name = user_names.get(uid, "Без имени")
            context = user_contexts.get(uid)
            
            # Определяем, прошел ли тест
            test_passed = "✅" if user_data[uid].get("profile_data") or user_data[uid].get("ai_generated_profile") else "❌"
            
            # Режим
            mode = context.communication_mode if context else "coach"
            mode_emoji = "🔮" if mode == "coach" else "🧠" if mode == "psychologist" else "⚡"
            
            text += f"{i}. {test_passed} {mode_emoji} <b>{name}</b> (ID: {uid})\n"
        
        if len(all_users) > 20:
            text += f"\n... и ещё {len(all_users) - 20} пользователей"
    
    keyboard = InlineKeyboardMarkup()
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
{chr(10).join([f'• {aid}' for aid in ADMIN_IDS])}
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
    
    # Здесь можно реализовать чтение логов из файла
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
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="admin_panel"))
    
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
    
    # Очищаем state_data для всех пользователей
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
    
    # Здесь можно реализовать очистку лог-файлов
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
    
    # Оставляем только пользователей с профилями
    active_users = {}
    active_contexts = {}
    active_names = {}
    
    for uid, data in user_data.items():
        if data.get("profile_data") or data.get("ai_generated_profile"):
            active_users[uid] = data
            if uid in user_contexts:
                active_contexts[uid] = user_contexts[uid]
            if uid in user_names:
                active_names[uid] = user_names[uid]
    
    removed = len(user_data) - len(active_users)
    
    # Обновляем глобальные хранилища
    user_data.clear()
    user_data.update(active_users)
    
    user_contexts.clear()
    user_contexts.update(active_contexts)
    
    user_names.clear()
    user_names.update(active_names)
    
    # Очищаем state_data для всех
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
    
    # Удаляем данные незавершённых тестов
    cleaned = 0
    for uid, data in user_data.items():
        if not data.get("profile_data") and not data.get("ai_generated_profile"):
            if any(key in data for key in ["stage1_current", "stage2_current", "stage3_current", "stage4_current", "stage5_current"]):
                # Очищаем только данные теста, оставляем остальное
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

# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'is_admin',
    'check_admin_access',
    'cmd_stats',
    'cmd_apistatus',
    'cmd_admin',
    'cmd_broadcast',
    'cmd_users',
    'show_admin_panel',
    'handle_admin_callback',
    'show_admin_stats',
    'start_broadcast',
    'process_broadcast',
    'show_users_list',
    'show_admin_settings',
    'show_admin_logs',
    'show_admin_cleanup',
    'cleanup_cache',
    'cleanup_logs',
    'cleanup_users',
    'cleanup_tests'
]
