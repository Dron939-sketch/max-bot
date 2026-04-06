#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Административные обработчики для MAX
Версия 2.2 - СТАТИСТИКА ИЗ ПАМЯТИ (без БД)
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

# Импорты для статистики
from models import Statistics

logger = logging.getLogger(__name__)

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
# СБОР СТАТИСТИКИ ИЗ ПАМЯТИ
# ============================================

def collect_memory_stats() -> Dict[str, Any]:
    """
    Собирает статистику из памяти (user_data, user_contexts и т.д.)
    """
    stats = {
        'total_users': len(user_data),
        'users_with_context': len(user_contexts),
        'users_with_name': len(user_names),
        'users_with_routes': len(user_routes),
        'users_with_states': len(user_states),
        'test_completed': 0,
        'test_in_progress': 0,
        'test_not_started': 0,
        'perception_types': {},
        'thinking_levels': {},
        'modes': {},
        'vectors': {
            'СБ': {'sum': 0, 'count': 0},
            'ТФ': {'sum': 0, 'count': 0},
            'УБ': {'sum': 0, 'count': 0},
            'ЧВ': {'sum': 0, 'count': 0}
        },
        'deep_patterns': {},
        'dilts_levels': {}
    }
    
    for uid, data in user_data.items():
        # Проверяем завершённость теста
        has_profile = data.get('profile_data') or data.get('ai_generated_profile')
        
        if has_profile:
            stats['test_completed'] += 1
        elif data.get('all_answers') and len(data.get('all_answers', [])) > 0:
            stats['test_in_progress'] += 1
        else:
            stats['test_not_started'] += 1
        
        # Типы восприятия
        pt = data.get('perception_type')
        if pt:
            stats['perception_types'][pt] = stats['perception_types'].get(pt, 0) + 1
        
        # Уровни мышления
        tl = data.get('thinking_level')
        if tl:
            stats['thinking_levels'][tl] = stats['thinking_levels'].get(tl, 0) + 1
        
        # Вектора из профиля
        profile = data.get('profile_data', {})
        if profile:
            for vec in ['СБ', 'ТФ', 'УБ', 'ЧВ']:
                level = profile.get(f'{vec.lower()}_level')
                if level:
                    stats['vectors'][vec]['sum'] += level
                    stats['vectors'][vec]['count'] += 1
        
        # Глубинные паттерны
        deep = data.get('deep_patterns', {})
        if deep:
            for key, value in deep.items():
                if key not in stats['deep_patterns']:
                    stats['deep_patterns'][key] = {}
                stats['deep_patterns'][key][value] = stats['deep_patterns'][key].get(value, 0) + 1
        
        # Уровни Дилтса
        dilts = data.get('dilts_counts', {})
        if dilts:
            for level, count in dilts.items():
                if level not in stats['dilts_levels']:
                    stats['dilts_levels'][level] = {'sum': 0, 'count': 0}
                stats['dilts_levels'][level]['sum'] += count
                stats['dilts_levels'][level]['count'] += 1
    
    # Собираем режимы общения
    for uid, context in user_contexts.items():
        mode = context.communication_mode if context and hasattr(context, 'communication_mode') else 'coach'
        stats['modes'][mode] = stats['modes'].get(mode, 0) + 1
    
    # Вычисляем средние значения векторов
    for vec in stats['vectors']:
        if stats['vectors'][vec]['count'] > 0:
            stats['vectors'][vec]['avg'] = stats['vectors'][vec]['sum'] / stats['vectors'][vec]['count']
        else:
            stats['vectors'][vec]['avg'] = 0
    
    # Вычисляем средние значения уровней Дилтса
    for level in stats['dilts_levels']:
        if stats['dilts_levels'][level]['count'] > 0:
            stats['dilts_levels'][level]['avg'] = stats['dilts_levels'][level]['sum'] / stats['dilts_levels'][level]['count']
    
    return stats

def format_stats_text(stats: Dict[str, Any]) -> str:
    """
    Форматирует статистику в читаемый текст
    """
    now = datetime.datetime.now()
    
    text = f"📊 <b>СТАТИСТИКА БОТА (В ПАМЯТИ)</b>\n"
    text += f"🕐 {now.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
    
    # Основная статистика
    text += f"👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
    text += f"• Всего в памяти: <b>{stats['total_users']}</b>\n"
    text += f"• С профилем: <b>{stats['test_completed']}</b>\n"
    text += f"• В процессе теста: <b>{stats['test_in_progress']}</b>\n"
    text += f"• Не начинали тест: <b>{stats['test_not_started']}</b>\n"
    text += f"• С контекстом: <b>{stats['users_with_context']}</b>\n"
    text += f"• С именем: <b>{stats['users_with_name']}</b>\n"
    text += f"• С маршрутами: <b>{stats['users_with_routes']}</b>\n"
    text += f"• В состояниях: <b>{stats['users_with_states']}</b>\n\n"
    
    # Режимы общения
    if stats['modes']:
        text += f"🎭 <b>РЕЖИМЫ ОБЩЕНИЯ</b>\n"
        mode_names = {
            'coach': '🔮 Коуч',
            'psychologist': '🧠 Психолог',
            'trainer': '⚡ Тренер'
        }
        for mode, count in sorted(stats['modes'].items(), key=lambda x: x[1], reverse=True):
            name = mode_names.get(mode, mode)
            percent = (count / stats['total_users'] * 100) if stats['total_users'] > 0 else 0
            text += f"• {name}: <b>{count}</b> ({percent:.1f}%)\n"
        text += "\n"
    
    # Типы восприятия
    if stats['perception_types']:
        text += f"👁️ <b>ТИПЫ ВОСПРИЯТИЯ</b>\n"
        pt_names = {
            'visual': '👁️ Визуал',
            'auditory': '👂 Аудиал',
            'kinesthetic': '🤲 Кинестетик',
            'digital': '💭 Дигитал'
        }
        for pt, count in sorted(stats['perception_types'].items(), key=lambda x: x[1], reverse=True):
            name = pt_names.get(pt, pt)
            percent = (count / stats['test_completed'] * 100) if stats['test_completed'] > 0 else 0
            text += f"• {name}: <b>{count}</b> ({percent:.1f}%)\n"
        text += "\n"
    
    # Уровни мышления
    if stats['thinking_levels']:
        text += f"🧠 <b>УРОВНИ МЫШЛЕНИЯ</b>\n"
        for level in sorted(stats['thinking_levels'].keys()):
            count = stats['thinking_levels'][level]
            percent = (count / stats['test_completed'] * 100) if stats['test_completed'] > 0 else 0
            text += f"• Уровень {level}: <b>{count}</b> ({percent:.1f}%)\n"
        text += "\n"
    
    # Средние значения векторов
    if any(v['count'] > 0 for v in stats['vectors'].values()):
        text += f"📈 <b>СРЕДНИЕ ЗНАЧЕНИЯ ВЕКТОРОВ</b>\n"
        vector_names = {
            'СБ': '🛡️ Стабильность',
            'ТФ': '💰 Трансформация',
            'УБ': '🧩 Убеждения',
            'ЧВ': '💕 Чувства'
        }
        for vec, data in stats['vectors'].items():
            if data['count'] > 0:
                name = vector_names.get(vec, vec)
                text += f"• {name}: <b>{data['avg']:.1f}</b> (n={data['count']})\n"
        text += "\n"
    
    # Глубинные паттерны
    if stats['deep_patterns']:
        text += f"🔍 <b>ГЛУБИННЫЕ ПАТТЕРНЫ</b>\n"
        for pattern, values in stats['deep_patterns'].items():
            pattern_names = {
                'attachment': '🪢 Тип привязанности',
                'coping': '🛡️ Копинг-стратегии',
                'defense': '🔒 Защитные механизмы'
            }
            name = pattern_names.get(pattern, pattern)
            text += f"<b>{name}:</b>\n"
            for value, count in sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]:
                percent = (count / stats['test_completed'] * 100) if stats['test_completed'] > 0 else 0
                text += f"   • {value}: {count} ({percent:.1f}%)\n"
        text += "\n"
    
    # Уровни Дилтса
    if stats['dilts_levels']:
        text += f"🏔️ <b>УРОВНИ ДИЛТСА</b>\n"
        level_names = {
            'environment': '🌍 Окружение',
            'behavior': '⚡ Поведение',
            'capabilities': '💪 Способности',
            'beliefs': '🧠 Убеждения',
            'identity': '🪞 Идентичность',
            'spiritual': '✨ Духовность'
        }
        for level, data in stats['dilts_levels'].items():
            if data['count'] > 0:
                name = level_names.get(level, level)
                text += f"• {name}: <b>{data['avg']:.1f}</b>\n"
        text += "\n"
    
    # Прогресс
    if stats['test_completed'] > 0:
        completion_rate = (stats['test_completed'] / stats['total_users'] * 100) if stats['total_users'] > 0 else 0
        text += f"📊 <b>ОБЩИЙ ПРОГРЕСС</b>\n"
        text += f"• Завершили тест: <b>{completion_rate:.1f}%</b>\n"
    
    return text

# ============================================
# КОМАНДЫ АДМИНИСТРАТОРОВ
# ============================================

@bot.message_handler(commands=['stats'])
def cmd_stats(message: Message):
    """Команда /stats — статистика бота из памяти"""
    if not check_admin_access(message):
        return
    
    # Собираем статистику
    stats_data = collect_memory_stats()
    
    # Форматируем текст
    stats_text = format_stats_text(stats_data)
    
    # Отправляем
    safe_send_message(
        message,
        stats_text,
        parse_mode='HTML',
        delete_previous=True
    )

@bot.message_handler(commands=['dbstats'])
def cmd_dbstats(message: Message):
    """Команда /dbstats — статистика из памяти (БД отключена)"""
    if not check_admin_access(message):
        return
    
    memory_stats = get_memory_stats()
    
    text = f"📊 <b>СТАТИСТИКА ПАМЯТИ</b>\n\n"
    text += f"<b>Хранилища:</b>\n"
    text += f"• user_data: {memory_stats.get('users_in_data', 0)}\n"
    text += f"• user_contexts: {memory_stats.get('users_in_contexts', 0)}\n"
    text += f"• user_routes: {memory_stats.get('users_in_routes', 0)}\n"
    text += f"• user_states: {memory_stats.get('users_in_states', 0)}\n"
    text += f"• user_names: {memory_stats.get('users_with_names', 0)}\n"
    text += f"• Всего уникальных: {memory_stats.get('total_unique', 0)}\n\n"
    
    text += f"<b>⚠️ Режим работы:</b>\n"
    text += f"• База данных ОТКЛЮЧЕНА\n"
    text += f"• Данные хранятся только в памяти\n"
    text += f"• При перезапуске данные будут потеряны"
    
    safe_send_message(message, text, parse_mode='HTML', delete_previous=True)

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
    """Команда /sync — синхронизация с БД (отключена)"""
    if not check_admin_access(message):
        return
    
    safe_send_message(
        message,
        "⚠️ <b>СИНХРОНИЗАЦИЯ ОТКЛЮЧЕНА</b>\n\nБаза данных временно отключена. Все данные хранятся только в памяти.\n\nПри перезапуске данные будут потеряны.",
        parse_mode='HTML',
        delete_previous=True
    )

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
    stats_data = collect_memory_stats()
    
    text = f"""
🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>

📊 <b>СТАТИСТИКА В ПАМЯТИ:</b>
• Всего пользователей: <b>{stats_data['total_users']}</b>
• С профилем: <b>{stats_data['test_completed']}</b>
• В процессе теста: <b>{stats_data['test_in_progress']}</b>
• В контексте: <b>{stats_data['users_with_context']}</b>

⚠️ <b>РЕЖИМ РАБОТЫ:</b>
• База данных ОТКЛЮЧЕНА
• Данные только в памяти

👇 <b>ДЕЙСТВИЯ:</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats"),
        InlineKeyboardButton("📢 РАССЫЛКА", callback_data="admin_broadcast")
    )
    keyboard.row(
        InlineKeyboardButton("👥 ПОЛЬЗОВАТЕЛИ", callback_data="admin_users"),
        InlineKeyboardButton("💾 ПАМЯТЬ", callback_data="admin_memory")
    )
    keyboard.row(
        InlineKeyboardButton("🧹 ОЧИСТКА", callback_data="admin_cleanup"),
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
    elif action == "memory":
        show_memory_info(call)
    elif action == "settings":
        show_admin_settings(call)
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
    
    # Собираем статистику
    stats_data = collect_memory_stats()
    
    # Форматируем текст
    stats_text = format_stats_text(stats_data)
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        stats_text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_memory_info(call: CallbackQuery):
    """Показывает информацию о памяти"""
    if not check_admin_access(call):
        return
    
    memory_stats = get_memory_stats()
    
    # Размеры объектов в памяти (приблизительно)
    import sys
    size_data = sys.getsizeof(user_data) // 1024
    size_contexts = sys.getsizeof(user_contexts) // 1024
    size_routes = sys.getsizeof(user_routes) // 1024
    size_states = sys.getsizeof(user_states) // 1024
    
    text = f"💾 <b>ИНФОРМАЦИЯ О ПАМЯТИ</b>\n\n"
    
    text += f"<b>Хранилища:</b>\n"
    text += f"• user_data: {memory_stats.get('users_in_data', 0)} записей (~{size_data} KB)\n"
    text += f"• user_contexts: {memory_stats.get('users_in_contexts', 0)} записей (~{size_contexts} KB)\n"
    text += f"• user_routes: {memory_stats.get('users_in_routes', 0)} записей (~{size_routes} KB)\n"
    text += f"• user_states: {memory_stats.get('users_in_states', 0)} записей (~{size_states} KB)\n"
    text += f"• user_names: {memory_stats.get('users_with_names', 0)} записей\n"
    text += f"• Всего уникальных: {memory_stats.get('total_unique', 0)}\n\n"
    
    text += f"<b>⚠️ ВАЖНО:</b>\n"
    text += f"• База данных ОТКЛЮЧЕНА\n"
    text += f"• Данные хранятся ТОЛЬКО в оперативной памяти\n"
    text += f"• При перезапуске бота все данные будут потеряны\n"
    text += f"• Рекомендуется включить БД для постоянного хранения"
    
    keyboard = get_back_keyboard("admin_panel")
    
    safe_send_message(
        call.message,
        text,
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
    except Exception:
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
            mode = context.communication_mode if context and hasattr(context, 'communication_mode') else "coach"
            mode_emoji = "🔮" if mode == "coach" else "🧠" if mode == "psychologist" else "⚡"
            
            # ID для копирования
            text += f"{i}. {test_passed} {mode_emoji} <b>{name}</b> (ID: <code>{uid}</code>)\n"
        
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
{chr(10).join([f'• <code>{aid}</code>' for aid in ADMIN_IDS])}

<b>РЕЖИМ РАБОТЫ:</b>
• База данных: ❌ ОТКЛЮЧЕНА
• Хранение: только в памяти
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
🔄 <b>ОЧИСТКА ПАМЯТИ</b>

Выберите, что очистить:
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🧹 ВСЕ ДАННЫЕ", callback_data="cleanup_all"),
        InlineKeyboardButton("👥 НЕАКТИВНЫХ", callback_data="cleanup_users")
    )
    keyboard.row(
        InlineKeyboardButton("🧠 НЕЗАВЕРШЁННЫЕ", callback_data="cleanup_tests"),
        InlineKeyboardButton("🗑 СОСТОЯНИЯ", callback_data="cleanup_cache")
    )
    keyboard.row(
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
    """Очищает кэш состояний"""
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

def cleanup_users(call: CallbackQuery):
    """Очищает неактивных пользователей"""
    if not check_admin_access(call):
        return
    
    # Оставляем только пользователей с профилями
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
    
    # Обновляем глобальные хранилища
    user_data.clear()
    user_data.update(active_users)
    
    user_contexts.clear()
    user_contexts.update(active_contexts)
    
    user_names.clear()
    user_names.update(active_names)
    
    user_routes.clear()
    user_routes.update(active_routes)
    
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

def cleanup_all(call: CallbackQuery):
    """Очищает все данные пользователей"""
    if not check_admin_access(call):
        return
    
    # Сохраняем количество
    total = len(user_data)
    
    # Очищаем все хранилища
    user_data.clear()
    user_contexts.clear()
    user_names.clear()
    user_routes.clear()
    user_state_data.clear()
    user_states.clear()
    
    text = f"✅ Очищены все данные: {total} пользователей удалено"
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
    'cmd_dbstats',
    'cmd_apistatus',
    'cmd_admin',
    'cmd_broadcast',
    'cmd_users',
    'cmd_sync',
    'show_admin_panel',
    'handle_admin_callback',
    'show_admin_stats',
    'start_broadcast',
    'process_broadcast',
    'show_users_list',
    'show_admin_settings',
    'show_admin_cleanup',
    'cleanup_cache',
    'cleanup_users',
    'cleanup_tests',
    'cleanup_all',
    'collect_memory_stats',
    'format_stats_text'
]
