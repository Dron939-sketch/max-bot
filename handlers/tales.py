#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик терапевтических сказок
"""

import logging
import time  # ✅ ДОБАВЛЕНО
import threading
from typing import Optional

from maxibot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from message_utils import safe_send_message
from hypno_module import TherapeuticTales
from db_sync import sync_db

logger = logging.getLogger(__name__)

tales = TherapeuticTales()

def log_tale_event(user_id: int, tale_title: str, issue: str):
    """Логирует просмотр сказки в БД"""
    try:
        sync_db.log_event(
            user_id,
            'tale_viewed',
            {
                'tale_title': tale_title,
                'issue': issue,
                'timestamp': time.time()  # ✅ теперь time импортирован
            }
        )
    except Exception as e:
        logger.error(f"❌ Ошибка логирования: {e}")

def show_tale(call: CallbackQuery):
    """
    Показывает случайную терапевтическую сказку
    """
    from state import user_data, user_contexts, user_names
    
    user_id = call.from_user.id
    context = user_contexts.get(user_id)
    user_data_dict = user_data.get(user_id, {})
    
    # Определяем текущую проблему на основе профиля
    scores = {}
    for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = user_data_dict.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    # Находим самый слабый вектор
    if scores:
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector = min_vector[0]
        
        issue_map = {
            "СБ": "страх",
            "ТФ": "деньги",
            "УБ": "понимание",
            "ЧВ": "отношения"
        }
        issue = issue_map.get(vector, "рост")
    else:
        issue = "рост"
    
    # Получаем сказку
    try:
        tale = tales.get_tale_for_issue(issue)
        tale_title = tale.get("title", "Сказка на ночь")
    except Exception:
        tale = None
        tale_title = "Сказка на ночь"
    
    if not tale:
        tale = {
            "title": "Сказка на ночь",
            "text": "Жил-был человек, который искал ответы. Он ходил по миру, спрашивал мудрецов, читал книги. И однажды понял, что все ответы уже были внутри него. Просто нужно было время, чтобы их услышать."
        }
    
    threading.Thread(target=log_tale_event, args=(user_id, tale_title, issue), daemon=True).start()
    
    # Формируем текст
    text = f"📖 **{tale['title']}**\n\n{tale['text']}"
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📖 ЕЩЁ СКАЗКУ", callback_data="show_tale"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='Markdown',
        delete_previous=True
    )
