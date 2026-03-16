#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики вопросов и умных вопросов для MAX
Восстановлено из оригинального bot3.py и адаптировано
"""

import logging
import random
import time
from typing import Dict, Any, List, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_edit_message
from keyboards import get_back_keyboard, get_main_menu_after_mode_keyboard
from services import call_deepseek, text_to_speech
from profiles import VECTORS, level
from modes import get_mode

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    from main import user_data
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    from main import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    from main import user_state_data
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_context(user_id: int):
    """Получает контекст пользователя"""
    from main import user_contexts
    return user_contexts.get(user_id)

def get_user_names(user_id: int) -> str:
    """Получает имя пользователя"""
    from main import user_names
    return user_names.get(user_id, "друг")

def is_test_completed(user_data: dict) -> bool:
    """Проверяет, завершен ли тест"""
    if user_data.get("profile_data"):
        return True
    if user_data.get("ai_generated_profile"):
        return True
    required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
    if all(field in user_data for field in required_minimal):
        return True
    return False

# ============================================
# ГЕНЕРАЦИЯ УМНЫХ ВОПРОСОВ
# ============================================

def generate_smart_questions(scores: Dict[str, float]) -> List[str]:
    """
    Генерирует вопросы на основе профиля
    """
    questions = []
    
    tf = level(scores.get("ТФ", 3))
    sb = level(scores.get("СБ", 3))
    ub = level(scores.get("УБ", 3))
    cv = level(scores.get("ЧВ", 3))
    
    # Вопросы про деньги (ТФ)
    if tf <= 2:
        questions.append("Как начать зарабатывать, если нет денег?")
        questions.append("Почему мне не везет с деньгами?")
    elif tf <= 4:
        questions.append("Как увеличить доход без новых вложений?")
        questions.append("Как создать финансовую подушку?")
    elif tf <= 6:
        questions.append("Как диверсифицировать источники дохода?")
        questions.append("Как начать инвестировать с умом?")
    
    # Вопросы про страх и защиту (СБ)
    if sb <= 2:
        questions.append("Как перестать бояться конфликтов?")
        questions.append("Как научиться говорить 'нет'?")
    elif sb <= 4:
        questions.append("Почему я злюсь внутри, но молчу?")
        questions.append("Как защищать границы без агрессии?")
    elif sb <= 6:
        questions.append("Как использовать свою силу во благо?")
        questions.append("Как защищать других, не выгорая?")
    
    # Вопросы про понимание мира (УБ)
    if ub <= 2:
        questions.append("Как понять, что происходит в жизни?")
        questions.append("Почему всё так сложно?")
    elif ub <= 4:
        questions.append("Как перестать искать заговоры?")
        questions.append("Как отличить правду от лжи?")
    elif ub <= 6:
        questions.append("Как видеть закономерности в хаосе?")
        questions.append("Как предсказывать развитие событий?")
    
    # Вопросы про отношения (ЧВ)
    if cv <= 2:
        questions.append("Как перестать зависеть от других?")
        questions.append("Почему меня бросают?")
    elif cv <= 4:
        questions.append("Как строить здоровые отношения?")
        questions.append("Почему отношения поверхностные?")
    elif cv <= 6:
        questions.append("Как создавать глубокие связи?")
        questions.append("Как быть лидером в отношениях?")
    
    # Общие вопросы
    general = [
        "С чего начать изменения?",
        "Что мне делать с этой ситуацией?",
        "Как не срываться на близких?",
        "Как найти своё призвание?",
        "Как обрести внутренний покой?"
    ]
    
    # Добавляем общие вопросы, если не хватает
    while len(questions) < 5:
        for q in general:
            if q not in questions and len(questions) < 5:
                questions.append(q)
    
    return questions[:5]

# ============================================
# ПОКАЗ УМНЫХ ВОПРОСОВ
# ============================================

def show_smart_questions(call: CallbackQuery):
    """
    Показывает умные вопросы на основе профиля
    """
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    context = get_user_context(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed(user_data):
        text = f"""
🧠 <b>ФРЕДИ: СНАЧАЛА ПРОЙДИ ТЕСТ</b>

Чтобы я мог задавать точные вопросы, нужно знать твой профиль.

👇 Пройди тест (15 минут), и я смогу помогать глубже.
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🚀 ПРОЙТИ ТЕСТ", callback_data="show_stage_1_intro"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu"))
        
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
        return
    
    # Получаем scores
    scores = {}
    for k in VECTORS:
        levels = user_data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    update_user_state_data(user_id, smart_questions=questions)
    
    mode = context.communication_mode if context else "coach"
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Разные заголовки для разных режимов
    if mode == "coach":
        header = f"{mode_config['emoji']} <b>ЗАДАЙТЕ ВОПРОС (КОУЧ)</b>\n\n"
        header += "Я буду задавать открытые вопросы, помогая вам найти ответы внутри себя.\n\n"
    elif mode == "psychologist":
        header = f"{mode_config['emoji']} <b>РАССКАЖИТЕ МНЕ (ПСИХОЛОГ)</b>\n\n"
        header += "Я здесь, чтобы помочь исследовать глубинные паттерны.\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} <b>ПОСТАВЬТЕ ЗАДАЧУ (ТРЕНЕР)</b>\n\n"
        header += "Чётко сформулируйте, что хотите решить. Я дам конкретные шаги.\n\n"
    else:
        header = f"❓ <b>ЗАДАЙТЕ ВОПРОС</b>\n\n"
    
    text = header + "👇 <b>Выберите вопрос или напишите свой:</b>"
    
    # Строим клавиатуру
    keyboard = InlineKeyboardMarkup()
    
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.add(InlineKeyboardButton(
            text=f"{q_short}",
            callback_data=f"ask_{i}"
        ))
    
    # Добавляем категории
    keyboard.row(
        InlineKeyboardButton("🗣 Отношения", callback_data="help_cat_relations"),
        InlineKeyboardButton("💰 Деньги", callback_data="help_cat_money")
    )
    keyboard.row(
        InlineKeyboardButton("🧠 Самоощущение", callback_data="help_cat_self"),
        InlineKeyboardButton("📚 Знания", callback_data="help_cat_knowledge")
    )
    keyboard.row(
        InlineKeyboardButton("💪 Поддержка", callback_data="help_cat_support"),
        InlineKeyboardButton("🎨 Муза", callback_data="help_cat_muse")
    )
    keyboard.row(InlineKeyboardButton("🍏 Забота о себе", callback_data="help_cat_care"))
    keyboard.row(InlineKeyboardButton("✏️ Написать самому", callback_data="ask_question"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="show_results"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)

# ============================================
# ОБРАБОТКА ВЫБРАННОГО ВОПРОСА
# ============================================

def handle_smart_question(call: CallbackQuery, question: str):
    """
    Обрабатывает выбранный умный вопрос
    """
    user_id = call.from_user.id
    user_data_dict = get_user_data(user_id)
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        "🤔 Думаю над ответом...\n\nЭто займёт около 10-15 секунд",
        delete_previous=True
    )
    
    context_obj = get_user_context(user_id)
    mode_name = context_obj.communication_mode if context_obj else "coach"
    
    # Создаём экземпляр режима
    mode = get_mode(mode_name, user_id, user_data_dict, context_obj)
    
    # Обрабатываем вопрос через режим
    result = mode.process_question(question)
    response = result["response"]
    
    # Обновляем данные с новой историей
    if "history" not in user_data_dict:
        user_data_dict["history"] = []
    user_data_dict["history"] = mode.history
    
    # Очищаем ответ от форматирования
    clean_response = clean_text_for_safe_display(response)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("❓ Ещё вопрос", callback_data="smart_questions"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help"))
    
    # Добавляем предложения, если есть
    suggestions_text = ""
    if result.get("suggestions"):
        suggestions_text = "\n\n" + "\n".join(result["suggestions"])
    
    # Удаляем статусное и отправляем ответ
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        call.message,
        f"❓ <b>{question}</b>\n\n{clean_response}{suggestions_text}",
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Отправляем голосовой ответ
    audio_data = text_to_speech(clean_response, mode_name)
    if audio_data:
        logger.info(f"🎙 Голосовой ответ сгенерирован для пользователя {user_id}")

def clean_text_for_safe_display(text: str) -> str:
    """Очищает текст для безопасного отображения"""
    if not text:
        return text
    
    # Удаляем Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    
    return text.strip()

# ============================================
# ПОКАЗ ЭКРАНА ВВОДА ВОПРОСА
# ============================================

def show_question_input(call: CallbackQuery):
    """
    Показывает экран ввода вопроса
    """
    user_id = call.from_user.id
    user_data_dict = get_user_data(user_id)
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Примеры вопросов для разных режимов
    examples = {
        "coach": [
            "Как найти своё предназначение?",
            "Что делать с неопределённостью?",
            "Как перестать сомневаться?"
        ],
        "psychologist": [
            "Почему реагирую на одни и те же триггеры?",
            "Откуда этот сценарий в отношениях?",
            "Как проработать детскую травму?"
        ],
        "trainer": [
            "Как научиться быстро принимать решения?",
            "Какие навыки нужны для роста дохода?",
            "Как действовать в конфликте?"
        ]
    }
    
    mode_examples = examples.get(mode, examples["coach"])
    examples_text = "\n".join([f"• {ex}" for ex in mode_examples])
    
    text = f"""
🧠 <b>ФРЕДИ: ЗАДАЙТЕ ВОПРОС</b>

{user_name}, <b>задавай вопрос.</b> Я отвечу с учётом твоего профиля и выбранного режима.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

📝 <b>Напиши вопрос текстом</b> или отправь голосовое сообщение.

👇 <b>Примеры:</b>
{examples_text}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    # Устанавливаем состояние ожидания вопроса
    from main import user_states
    user_states[user_id] = "awaiting_question"

# ============================================
# ОБРАБОТКА ТЕКСТОВОГО ВОПРОСА
# ============================================

def process_text_question(message: Message, user_id: int, text: str):
    """
    Обрабатывает текстовый вопрос пользователя
    """
    user_data_dict = get_user_data(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed(user_data_dict):
        safe_send_message(
            message,
            "❓ Сначала нужно пройти тест. Используйте /start",
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🎙 Думаю над ответом...",
        delete_previous=True
    )
    
    context_obj = get_user_context(user_id)
    mode_name = context_obj.communication_mode if context_obj else "coach"
    
    # Создаём экземпляр режима
    mode = get_mode(mode_name, user_id, user_data_dict, context_obj)
    
    # Обрабатываем вопрос через режим
    result = mode.process_question(text)
    response = result["response"]
    
    # Обновляем данные с новой историей
    if "history" not in user_data_dict:
        user_data_dict["history"] = []
    user_data_dict["history"] = mode.history
    
    # Очищаем ответ от форматирования
    clean_response = clean_text_for_safe_display(response)
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🎤 ЗАДАТЬ ЕЩЁ", callback_data="ask_question"),
        InlineKeyboardButton("🎯 К ЦЕЛИ", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="show_psychologist_thought"))
    keyboard.row(InlineKeyboardButton("◀️ К ПОРТРЕТУ", callback_data="show_results"))
    
    # Добавляем предложения, если есть
    suggestions_text = ""
    if result.get("suggestions"):
        suggestions_text = "\n\n" + "\n".join(result["suggestions"])
    
    # Удаляем статусное сообщение
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
    
    # Отправляем ответ
    safe_send_message(
        message,
        f"💭 <b>Ответ</b>\n\n{clean_response}{suggestions_text}",
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Отправляем голосовой ответ
    audio_data = text_to_speech(clean_response, mode_name)
    if audio_data:
        logger.info(f"🎙 Голосовой ответ сгенерирован для пользователя {user_id}")
    
    # Сбрасываем состояние
    from main import user_states
    user_states[user_id] = "results"

# ============================================
# ОБРАБОТКА ГОЛОСОВОГО СООБЩЕНИЯ
# ============================================

def process_voice_message(message, user_id: int, file_path: str):
    """
    Обрабатывает голосовое сообщение пользователя
    """
    user_data_dict = get_user_data(user_id)
    
    # Проверяем, завершен ли тест
    if not is_test_completed(user_data_dict):
        safe_send_message(
            message,
            "🎙 Голосовые сообщения доступны только после завершения теста",
            delete_previous=True
        )
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        message,
        "🎤 Распознаю речь...",
        delete_previous=True
    )
    
    try:
        # Распознаём речь
        from services import speech_to_text
        recognized_text = speech_to_text(file_path)
        
        if not recognized_text:
            if status_msg:
                try:
                    from message_utils import safe_delete_message
                    safe_delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
            
            safe_send_message(
                message,
                "❌ Не удалось распознать речь\n\nПопробуйте еще раз или напишите текстом.",
                delete_previous=True
            )
            return
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                from message_utils import safe_delete_message
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        # Обрабатываем распознанный текст как обычный вопрос
        process_text_question(message, user_id, recognized_text)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        
        if status_msg:
            try:
                from message_utils import safe_delete_message
                safe_delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        
        safe_send_message(
            message,
            "❌ Произошла ошибка при обработке голоса",
            delete_previous=True
        )


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_smart_questions',
    'handle_smart_question',
    'show_question_input',
    'process_text_question',
    'process_voice_message',
    'generate_smart_questions'
]
