#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ ДЛЯ MAX
"""

import os
import json
import logging
import tempfile
import random
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List, Any, Tuple, Union
from statistics import mean
from datetime import datetime, timedelta
from collections import defaultdict

# Импорты из maxibot
from maxibot import MaxiBot, types
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# Импорты из наших модулей
from config import (
    MAX_TOKEN,
    ADMIN_IDS,
    COMMUNICATION_MODES,
    DEEPSEEK_API_KEY,
    DEEPGRAM_API_KEY,
    YANDEX_API_KEY,
    OPENWEATHER_API_KEY
)
from models import (
    UserContext, ReminderManager, DestinationManager, Statistics,
    ConfinementModel9, level, DelayedTaskManager
)
from services import (
    speech_to_text, text_to_speech, call_deepseek,
    generate_response_with_full_context, generate_ai_profile,
    generate_psychologist_thought
)
from reality_check import (
    get_theoretical_path,
    generate_life_context_questions,
    generate_goal_context_questions,
    calculate_feasibility,
    parse_life_context_answers,
    parse_goal_context_answers
)
from modes import get_mode, get_available_modes, get_mode_description
from morning_messages import MorningMessageManager
from profiles import (
    STAGE_1_FEEDBACK,
    STAGE_2_FEEDBACK,
    STAGE_3_FEEDBACK,
    DILTS_LEVELS,
    FALLBACK_ANALYSIS,
    VECTORS,
    LEVEL_PROFILES
)
from questions import (
    STAGE_1_QUESTIONS,
    STAGE_2_QUESTIONS,
    STAGE_3_QUESTIONS,
    STAGE_4_QUESTIONS,
    STAGE_5_QUESTIONS,
    STAGE_2_SCORING,
    CLARIFYING_QUESTIONS,
    DISCREPANCY_QUESTIONS,
    get_stage1_question,
    get_stage1_total,
    get_stage2_question,
    get_stage2_total,
    get_stage2_score,
    get_stage3_question,
    get_stage3_total,
    get_stage4_question,
    get_stage4_total,
    get_stage5_question,
    get_stage5_total,
    analyze_stage5_results,
    get_deep_patterns_description,
    get_clarifying_questions,
    get_question_text,
    get_question_options,
    get_option_text,
    get_option_value,
    map_to_stage3_feedback_level
)
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring
from weekend_planner import get_weekend_planner, get_weekend_ideas_keyboard
from keyboards import *
from message_utils import safe_send_message, safe_edit_message, safe_delete_message

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
# ГЛОБАЛЬНЫЕ ХРАНИЛИЩА
# ============================================

user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, UserContext] = {}
user_routes: Dict[int, Dict[str, Any]] = {}

# Инициализируем менеджеры
reminder_manager = ReminderManager()
destination_manager = DestinationManager()
stats = Statistics()
delayed_task_manager = DelayedTaskManager()
morning_manager = MorningMessageManager()

# Инициализируем гипнотический оркестратор
hypno = HypnoOrchestrator()
tales = TherapeuticTales()
anchoring = Anchoring()

# Инициализируем планировщик выходных
weekend_planner = get_weekend_planner()

# ============================================
# FSM СОСТОЯНИЯ (ЭМУЛЯЦИЯ)
# ============================================

class TestStates:
    """Состояния для FSM (эмуляция через словарь)"""
    stage_1 = "stage_1"
    stage_2 = "stage_2"
    stage_3 = "stage_3"
    stage_4 = "stage_4"
    stage_5 = "stage_5"
    results = "results"
    awaiting_question = "awaiting_question"
    pretest_question = "pretest_question"
    awaiting_context = "awaiting_context"
    mode_selection = "mode_selection"
    profile_confirmation = "profile_confirmation"
    clarifying_selection = "clarifying_selection"
    clarifying_test = "clarifying_test"
    alternative_test = "alternative_test"
    viewing_confinement = "viewing_confinement"
    viewing_intervention = "viewing_intervention"
    profile_generated = "profile_generated"
    destination_selection = "destination_selection"
    route_generation = "route_generation"
    route_active = "route_active"
    route_step_active = "route_step_active"
    collecting_life_context = "collecting_life_context"
    collecting_goal_context = "collecting_goal_context"
    theoretical_path_shown = "theoretical_path_shown"
    reality_check_active = "reality_check_active"
    feasibility_result = "feasibility_result"

# Хранилище состояний пользователей
user_states: Dict[int, str] = {}
user_state_data: Dict[int, Dict[str, Any]] = {}

def get_state(user_id: int) -> str:
    """Получает состояние пользователя"""
    return user_states.get(user_id, "")

def set_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state

def get_state_data(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def clear_state(user_id: int):
    """Очищает состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_state_data:
        del user_state_data[user_id]

# ============================================
# HEALTH CHECK ДЛЯ RENDER
# ============================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    try:
        server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
        logger.info("✅ Health check server started on port 10000")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health check server error: {e}")

# Запускаем health check в отдельном потоке
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# ============================================
# ФУНКЦИИ ДЛЯ КРАСИВОГО ОФОРМЛЕНИЯ ТЕКСТА
# ============================================

def bold(text: str) -> str:
    """Жирный текст (HTML)"""
    return f"<b>{text}</b>"

def italic(text: str) -> str:
    """Курсив (HTML)"""
    return f"<i>{text}</i>"

def emoji_text(emoji: str, text: str, bold_text: bool = True) -> str:
    """Текст с эмодзи"""
    if bold_text:
        return f"{emoji} {bold(text)}"
    return f"{emoji} {text}"

def format_profile_text(text: str) -> str:
    """Форматирует текст профиля с жирными заголовками и эмодзи, убирает дубли"""
    if not text:
        return text
    
    # Сначала очищаем от Markdown
    text = clean_text_for_safe_display(text)
    
    # Карта замены заголовков с эмодзи
    header_map = [
        (r'БЛОК\s*1:?\s*', '🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА'),
        (r'БЛОК\s*2:?\s*', '💪 СИЛЬНЫЕ СТОРОНЫ'),
        (r'БЛОК\s*3:?\s*', '🎯 ЗОНЫ РОСТА'),
        (r'БЛОК\s*4:?\s*', '🌱 КАК ЭТО СФОРМИРОВАЛОСЬ'),
        (r'БЛОК\s*5:?\s*', '⚠️ ГЛАВНАЯ ЛОВУШКА'),
    ]
    
    # Сначала заменяем "БЛОК X:" на правильные заголовки
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Убираем дублирование заголовков
    for _, header in header_map:
        # Ищем паттерн: заголовок, затем перенос строки, затем снова тот же заголовок
        pattern = rf'({re.escape(header)})\s*\n\s*{re.escape(header)}'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
        
        # Ищем паттерн с жирным форматированием
        pattern = rf'\*\*{re.escape(header)}\*\*\s*\n\s*{re.escape(header)}'
        text = re.sub(pattern, rf'{bold(header)}', text, flags=re.IGNORECASE)
        
        # Ищем паттерн: заголовок, потом такой же заголовок в жирном
        pattern = rf'{re.escape(header)}\s*\n\s*\*\*{re.escape(header)}\*\*'
        text = re.sub(pattern, rf'{bold(header)}', text, flags=re.IGNORECASE)
    
    # Теперь добавляем жирное форматирование к заголовкам
    for _, header in header_map:
        # Заменяем обычный заголовок на жирный
        text = re.sub(
            rf'({re.escape(header)})', 
            rf'{bold(header)}', 
            text, 
            flags=re.IGNORECASE
        )
    
    return text

def format_psychologist_text(text: str, user_name: str = "") -> str:
    """Форматирует мысли психолога с жирными заголовками и эмодзи, убирает дубли"""
    if not text:
        return text
    
    # Очищаем от Markdown
    text = clean_text_for_safe_display(text)
    
    # Убираем "### 1.", "### 2." и т.д.
    text = re.sub(r'###\s*\d+\.?\s*', '', text)
    text = re.sub(r'\d+\.\s*', '', text)
    
    # Добавляем обращение по имени, если есть и его нет
    if user_name and not text.lower().startswith(user_name.lower()):
        first_word = text.split()[0] if text else ""
        if first_word and first_word.lower() not in ['здравствуйте', 'привет', 'добрый']:
            text = f"{user_name}, " + text[0].lower() + text[1:] if text else text
    
    # Карта замены заголовков (эмодзи + текст)
    header_map = [
        (r'🔐\s*КЛЮЧЕВОЙ\s*ЭЛЕМЕНТ', '🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ'),
        (r'🔄\s*ПЕТЛЯ', '🔄 ПЕТЛЯ'),
        (r'🚪\s*ТОЧКА\s*ВХОДА', '🚪 ТОЧКА ВХОДА'),
        (r'📊\s*ПРОГНОЗ', '📊 ПРОГНОЗ'),
    ]
    
    # Сначала убираем возможные дубли эмодзи
    text = re.sub(r'🔐\s*🔐', '🔐', text)
    text = re.sub(r'🔄\s*🔄', '🔄', text)
    text = re.sub(r'🚪\s*🚪', '🚪', text)
    text = re.sub(r'📊\s*📊', '📊', text)
    
    # Затем форматируем заголовки жирным
    for pattern, replacement in header_map:
        # Разбиваем на эмодзи и текст
        parts = replacement.split(' ', 1)
        if len(parts) == 2:
            emoji, header_text = parts
            # Ищем паттерн с эмодзи или без
            text = re.sub(
                rf'({emoji}\s*)?{re.escape(header_text)}', 
                rf'{bold(replacement)}', 
                text, 
                flags=re.IGNORECASE
            )
    
    # Убираем лишние символы в конце
    text = re.sub(r'И вот:$', '', text)
    text = re.sub(r'И вот:\s*$', '', text)
    
    return text

def strip_html(text: str) -> str:
    """Полностью удаляет все HTML-теги из текста"""
    if not text:
        return text
    # Удаляем все теги
    text = re.sub(r'<[^>]+>', '', text)
    # Заменяем HTML-сущности
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return text

def clean_text_for_safe_display(text: str) -> str:
    """Полностью очищает текст для безопасного отображения"""
    if not text:
        return text
    
    # Удаляем все возможные форматирования (Markdown)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # жирный
    text = re.sub(r'__(.*?)__', r'\1', text)      # жирный через __
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # курсив
    text = re.sub(r'_(.*?)_', r'\1', text)        # курсив через _
    text = re.sub(r'`(.*?)`', r'\1', text)        # код
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # ссылки
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text) # картинки
    text = re.sub(r'#{1,6}\s+', '', text)          # заголовки
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # списки
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # нумерованные списки
    
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем множественные переводы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДЛИННЫМИ СООБЩЕНИЯМИ (СТРАХОВКА)
# ============================================

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Разбивает длинное сообщение на части по max_length символов,
    стараясь не разрывать слова и абзацы.
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по абзацам (двойной перенос строки)
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        # Если абзац сам по себе слишком длинный
        if len(para) > max_length:
            # Разбиваем по предложениям
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
                    # Если предложение слишком длинное, режем принудительно
                    if len(sent) > max_length:
                        # Режем по словам
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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def calculate_progress(current: int, total: int) -> str:
    """Возвращает прогресс-бар"""
    percent = int((current / total) * 10)
    bar = "█" * percent + "░" * (10 - percent)
    return f"▸ Вопрос {current}/{total} • {bar}"

def generate_unique_callback(prefix: str, user_id: int, question: int, option: str, extra: str = "") -> str:
    """Генерирует уникальный callback"""
    timestamp = int(time.time() * 1000) % 10000
    return f"{prefix}_{question}_{option}_{extra}_{user_id}_{timestamp}"

def determine_perception_type(scores: dict) -> str:
    """Определяет тип восприятия"""
    external = scores.get("EXTERNAL", 0)
    internal = scores.get("INTERNAL", 0)
    symbolic = scores.get("SYMBOLIC", 0)
    material = scores.get("MATERIAL", 0)
    
    attention = "EXTERNAL" if external > internal else "INTERNAL"
    anxiety = "SYMBOLIC" if symbolic > material else "MATERIAL"
    
    if attention == "EXTERNAL" and anxiety == "SYMBOLIC":
        return "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "EXTERNAL" and anxiety == "MATERIAL":
        return "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "INTERNAL" and anxiety == "SYMBOLIC":
        return "СМЫСЛО-ОРИЕНТИРОВАННЫЙ"
    else:
        return "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ"

def calculate_thinking_level_by_scores(level_scores_dict: dict) -> int:
    """Рассчитывает уровень мышления"""
    total_score = sum(level_scores_dict.values())
    
    if total_score <= 10:
        return 1
    elif total_score <= 20:
        return 2
    elif total_score <= 30:
        return 3
    elif total_score <= 40:
        return 4
    elif total_score <= 50:
        return 5
    elif total_score <= 60:
        return 6
    elif total_score <= 70:
        return 7
    elif total_score <= 80:
        return 8
    else:
        return 9

def get_level_group(level: int) -> str:
    """Группирует уровни"""
    if level <= 3:
        return "1-3"
    elif level <= 6:
        return "4-6"
    else:
        return "7-9"

def calculate_final_level(stage2_level: int, stage3_scores: list) -> int:
    """Рассчитывает финальный уровень"""
    if not stage3_scores:
        return stage2_level
    avg_behavior = sum(stage3_scores) / len(stage3_scores)
    return round((stage2_level + avg_behavior) / 2)

def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def calculate_profile_final(user_data: dict) -> dict:
    """Финальный расчет профиля"""
    perception_type = user_data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    thinking_level = user_data.get("thinking_level", 5)
    
    behavioral_levels = user_data.get("behavioral_levels", {})
    
    sb_levels = behavioral_levels.get("СБ", [])
    tf_levels = behavioral_levels.get("ТФ", [])
    ub_levels = behavioral_levels.get("УБ", [])
    chv_levels = behavioral_levels.get("ЧВ", [])
    
    sb_avg = sum(sb_levels) / len(sb_levels) if sb_levels else 3
    tf_avg = sum(tf_levels) / len(tf_levels) if tf_levels else 3
    ub_avg = sum(ub_levels) / len(ub_levels) if ub_levels else 3
    chv_avg = sum(chv_levels) / len(chv_levels) if chv_levels else 3
    
    dilts_counts = user_data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_code = f"СБ-{round(sb_avg)}_ТФ-{round(tf_avg)}_УБ-{round(ub_avg)}_ЧВ-{round(chv_avg)}"
    
    return {
        "display_name": profile_code,
        "perception_type": perception_type,
        "thinking_level": thinking_level,
        "sb_level": round(sb_avg),
        "tf_level": round(tf_avg),
        "ub_level": round(ub_avg),
        "chv_level": round(chv_avg),
        "dominant_dilts": dominant_dilts,
        "dilts_counts": dilts_counts
    }

def get_priority_order(scores: dict) -> list:
    """Определяет порядок приоритетов"""
    if not scores:
        return ["ТФ", "СБ", "УБ", "ЧВ"]
    tf = level(scores.get("ТФ", 3))
    if tf <= 2:
        rest = sorted([(k, v) for k, v in scores.items() if k != "ТФ"], key=lambda x: x[1])
        return ["ТФ"] + [r[0] for r in rest]
    else:
        return [k for k, _ in sorted(scores.items(), key=lambda x: x[1])]

def is_test_completed(user_data: dict) -> bool:
    """Проверяет, завершен ли тест (более гибкая версия)"""
    
    # Вариант 1: Есть profile_data (финальный рассчитанный профиль)
    if user_data.get("profile_data"):
        return True
    
    # Вариант 2: Есть ai_generated_profile (сгенерированный ИИ)
    if user_data.get("ai_generated_profile"):
        return True
    
    # Вариант 3: Есть ключевые поля (минимум для ответов на вопросы)
    # deep_patterns не обязателен - это 5-й этап
    required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
    if all(field in user_data for field in required_minimal):
        return True
    
    # Вариант 4: Старая проверка (для обратной совместимости)
    required_fields = ["perception_type", "thinking_level", "behavioral_levels", "dilts_counts"]
    if all(field in user_data for field in required_fields):
        return True
    
    return False

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
    avg = mean(scores_list)
    variance = sum((x - avg) ** 2 for x in scores_list) / len(scores_list)
    std_dev = variance ** 0.5
    return std_dev <= 1.3

def safe_get_profile_info(vector: str, level_num: int, key: str, default: str = "Информация уточняется") -> str:
    """Безопасно получает информацию из профиля"""
    try:
        profile = LEVEL_PROFILES.get(vector, {}).get(level_num, {})
        if isinstance(profile, dict):
            if key == 'quote':
                return profile.get('quote') or profile.get('description') or profile.get('block1') or default
            elif key == 'pain_origin':
                return profile.get('pain_origin') or profile.get('origin') or profile.get('block2') or default
            elif key == 'pain_costs':
                costs = profile.get('pain_costs') or profile.get('costs') or []
                if costs:
                    return costs
                return ["Энергией", "Временем", "Возможностями"]
        else:
            if key == 'quote':
                return str(profile)
            elif key == 'pain_origin':
                return "Из вашего опыта"
            elif key == 'pain_costs':
                return ["Энергией", "Временем", "Возможностями"]
    except Exception as e:
        logger.error(f"Ошибка при получении информации из профиля: {e}")
    
    return default

# ============================================
# ФУНКЦИИ ДЛЯ ПРОСТОГО ОПИСАНИЯ ПРОФИЛЯ
# ============================================

def convert_to_simple_language(scores: dict, perception_type: str, thinking_level: int, deep_patterns: dict = None) -> dict:
    """Конвертирует технические данные в простые описания"""
    
    result = {}
    
    # 1. Внимание (куда смотрит)
    if perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА ЛЮДЕЙ"
        result['attention_desc'] = "Для вас важно, что думают другие, вы чутко считываете настроение и ожидания окружающих."
    else:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА СЕБЯ"
        result['attention_desc'] = "Для вас важнее ваши внутренние ощущения и чувства, чем мнение других."
    
    # 2. Мышление
    if thinking_level <= 3:
        result['thinking'] = "ВЫ МЫСЛИТЕ КОНКРЕТНО"
        result['thinking_desc'] = "Вы хорошо видите отдельные ситуации, но не всегда замечаете общие закономерности."
    elif thinking_level <= 6:
        result['thinking'] = "ВЫ МЫСЛИТЕ СИСТЕМНО"
        result['thinking_desc'] = "Вы замечаете закономерности, но не всегда видите, к чему они приведут в будущем."
    else:
        result['thinking'] = "ВЫ МЫСЛИТЕ ГЛУБОКО"
        result['thinking_desc'] = "Вы видите общие законы и можете предсказывать развитие ситуаций."
    
    # 3. СБ (реакция на угрозу)
    sb_level = level(scores.get("СБ", 3))
    sb_profiles = {
        1: "Под давлением вы замираете и не можете слова сказать.",
        2: "Вы избегаете конфликтов — уходите, прячетесь, уворачиваетесь.",
        3: "Вы соглашаетесь внешне, но внутри всё кипит.",
        4: "Вы внешне спокойны, но внутри держите всё в себе.",
        5: "Вы пытаетесь сгладить конфликт, перевести в шутку.",
        6: "Вы умеете защищать себя, но можете и атаковать в ответ."
    }
    result['sb_desc'] = sb_profiles.get(sb_level, "Вы по-разному реагируете на давление.")
    
    # 4. ТФ (деньги)
    tf_level = level(scores.get("ТФ", 3))
    tf_profiles = {
        1: "Деньги приходят и уходят — как повезёт.",
        2: "Вы ищете возможности, но каждый раз как с нуля.",
        3: "Вы умеете зарабатывать своим трудом.",
        4: "Вы хорошо зарабатываете и можете копить.",
        5: "Вы создаёте системы дохода и управляете финансами.",
        6: "Вы управляете капиталом и создаёте финансовые структуры."
    }
    result['tf_desc'] = tf_profiles.get(tf_level, "У вас свои отношения с деньгами.")
    result['tf_strong'] = tf_level >= 5
    
    # 5. УБ (понимание мира)
    ub_level = level(scores.get("УБ", 3))
    ub_profiles = {
        1: "Вы стараетесь не думать о сложном — само как-то решится.",
        2: "Вы верите в знаки, судьбу, высшие силы.",
        3: "Вы доверяете экспертам и авторитетам.",
        4: "Вы ищете скрытые смыслы и заговоры.",
        5: "Вы анализируете факты и делаете выводы сами.",
        6: "Вы строите теории и ищете закономерности."
    }
    result['ub_desc'] = ub_profiles.get(ub_level, "Вы по-своему понимаете мир.")
    result['ub_weak'] = ub_level <= 2
    
    # 6. ЧВ (отношения)
    chv_level = level(scores.get("ЧВ", 3))
    chv_profiles = {
        1: "Вы сильно привязываетесь к людям, тяжело без них.",
        2: "Вы подстраиваетесь под других, теряя себя.",
        3: "Вы хотите нравиться, показываете себя с лучшей стороны.",
        4: "Вы умеете влиять на людей, добиваться своего.",
        5: "Вы строите равные партнёрские отношения.",
        6: "Вы создаёте сообщества и сети контактов."
    }
    result['chv_desc'] = chv_profiles.get(chv_level, "У вас свои паттерны в отношениях.")
    
    # 7. Точка роста
    growth_map = {
        "ENVIRONMENT": "Посмотрите вокруг — может, дело в обстоятельствах?",
        "BEHAVIOR": "Попробуйте делать хоть что-то по-другому — маленькие шаги многое меняют.",
        "CAPABILITIES": "Развивайте новые навыки — они откроют новые возможности.",
        "VALUES": "Поймите, что для вас действительно важно — это изменит всё.",
        "IDENTITY": "Ответьте себе на вопрос «кто я?» — в этом ключ к изменениям."
    }
    result['growth_point'] = growth_map.get(perception_type, "Начните с малого — и увидите, куда приведёт.")
    
    # 8. Глубинные паттерны (если есть)
    if deep_patterns:
        result['deep_patterns'] = get_deep_patterns_description(deep_patterns)
    
    return result

# ============================================
# ФУНКЦИИ РЕЗУЛЬТАТОВ
# ============================================

def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
    lines = []
    
    if scores:
        # Находим вектор с минимальным значением (самая проблемная зона)
        min_vector = min(scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        lvl = level(score)
        
        # Безопасно получаем информацию из профиля
        quote = safe_get_profile_info(vector, lvl, 'quote', 'Пока не определено')
        pain_origin = safe_get_profile_info(vector, lvl, 'pain_origin', 'Из вашего опыта')
        costs = safe_get_profile_info(vector, lvl, 'pain_costs', ["Энергией", "Временем", "Возможностями"])
    else:
        vector = "СБ"
        quote = "Пока не определено"
        pain_origin = "Из вашего опыта"
        costs = ["Энергией", "Временем", "Возможностями"]
    
    lines.append(f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}")
    lines.append("")
    lines.append(f"🔍 {bold('Тип восприятия:')} {perception_type}")
    lines.append(f"🧠 {bold('Уровень мышления:')} {thinking_level}/9")
    lines.append("")
    
    # Основные секции с правильными заголовками
    lines.append(f"🔑 {bold('КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА')}")
    lines.append(quote)
    lines.append("")
    
    lines.append(f"💪 {bold('СИЛЬНЫЕ СТОРОНЫ')}")
    lines.append("• Высокоразвитые социальные навыки и умение выстраивать надежные, доверительные отношения.")
    lines.append("• Системное мышление, позволяющее видеть связи, управлять сложными процессами и достигать целей.")
    lines.append("• Исключительная устойчивость к стрессу и угрозам, способность действовать хладнокровно в кризисах.")
    lines.append("• Прагматизм и высокая компетентность в вопросах финансов, карьеры и социального взаимодействия.")
    lines.append("")
    
    lines.append(f"🎯 {bold('ЗОНЫ РОСТА')}")
    lines.append(f"• {pain_origin}")
    for cost in costs[:3]:
        lines.append(f"• {cost}")
    lines.append("")
    
    lines.append(f"⚠️ {bold('ГЛАВНАЯ ЛОВУШКА')}")
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "⚡ Поведение")
    lines.append(f"• {dilts_desc}")
    
    return "\n".join(lines)

def calculate_profile_confidence(profile: dict) -> float:
    """Рассчитывает уверенность в профиле"""
    confidence = 0.5
    
    stages_done = 0
    if profile.get("perception_type"):
        stages_done += 1
    if profile.get("thinking_level"):
        stages_done += 1
    if profile.get("behavioral_levels"):
        stages_done += 1
    if profile.get("dilts_counts"):
        stages_done += 1
    if profile.get("deep_patterns"):
        stages_done += 1
    
    confidence += stages_done * 0.1
    
    clarification_count = profile.get("clarification_iteration", 0)
    confidence += clarification_count * 0.05
    
    return min(1.0, confidence)

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    user_names[user_id] = user_name
    clear_state(user_id)
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
        user_contexts[user_id].name = user_name
    
    stats.register_start(user_id)
    
    context = user_contexts[user_id]
    
    # Проверяем, есть ли уже профиль
    data = user_data.get(user_id, {})
    if is_test_completed(data):
        profile_code = data.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
        
        text = f"""
🧠 {bold('ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ')}

👋 О, {user_name}, я вас помню!
(У меня, в отличие от людей, с памятью всё отлично — спасибо базе данных)

📊 {bold('ВАШ ПРОФИЛЬ:')} {profile_code}
(Лежит у меня в архивах, пылится...)

❓ {bold('ЧТО ДЕЛАЕМ?')}

Вы можете:
🔄 Пройти тест заново — вдруг вы изменились?

⬇️ {bold('ВЫБИРАЙТЕ:')}
"""
        
        keyboard = get_restart_keyboard()
        safe_send_message(message, text, reply_markup=keyboard)
        return
    
    # Проверяем, заполнен ли контекст
    if not (context.city and context.gender and context.age):
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
        
        keyboard = get_start_context_keyboard()
        safe_send_message(message, welcome_text, reply_markup=keyboard)
        return
    
    # Если контекст уже заполнен, показываем меню
    show_main_menu(message, context)

@bot.message_handler(commands=['menu'])
def cmd_menu(message: types.Message):
    """Обработчик команды /menu"""
    user_id = message.from_user.id
    
    if user_id in user_contexts:
        show_main_menu_after_mode(message, user_contexts[user_id])
    else:
        cmd_start(message)

@bot.message_handler(commands=['mode'])
def cmd_mode(message: types.Message):
    """Команда для смены режима"""
    user_id = message.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    show_mode_selection(message)

@bot.message_handler(commands=['stats'])
def cmd_stats(message: types.Message):
    """Команда /stats (только для админов)"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    safe_send_message(message, stats.get_stats_text())

@bot.message_handler(commands=['apistatus'])
def cmd_apistatus(message: types.Message):
    """Команда /apistatus"""
    if message.from_user.id not in ADMIN_IDS:
        safe_send_message(message, "⛔ Доступ запрещен")
        return
    
    deepseek_status = "✅ работает" if DEEPSEEK_API_KEY else "❌ не настроен"
    deepgram_status = "✅ работает" if DEEPGRAM_API_KEY else "❌ не настроен"
    yandex_status = "✅ работает" if YANDEX_API_KEY else "❌ не настроен"
    weather_status = "✅ работает" if OPENWEATHER_API_KEY else "❌ не настроен"
    
    text = f"📊 Статус API:\n\n"
    text += f"• DeepSeek: {deepseek_status}\n"
    text += f"• Deepgram: {deepgram_status}\n"
    text += f"• Yandex TTS: {yandex_status}\n"
    text += f"• OpenWeather: {weather_status}\n\n"
    
    safe_send_message(message, text)

@bot.message_handler(commands=['context'])
def cmd_context(message: types.Message):
    """Команда /context - принудительный сбор контекста"""
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

# ============================================
# ФУНКЦИИ ДЛЯ ВЫБОРА РЕЖИМА
# ============================================

def show_mode_selection(message: types.Message):
    """Показывает выбор режима общения"""
    user_id = message.chat.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    current_mode = context.communication_mode if context else "coach"
    mode_names = {
        "coach": "КОУЧ",
        "psychologist": "ПСИХОЛОГ",
        "trainer": "ТРЕНЕР"
    }
    mode_display = mode_names.get(current_mode, "КОУЧ")
    
    text = f"""
🧠 {bold('ФРЕДИ: ВЫБЕРИТЕ РЕЖИМ')}

Слушай, я могу быть разным. Хочешь конкретики — давай определимся, в каком качестве я сегодня буду полезен.

{bold('Твой профиль:')} {profile_code}
{bold('Сейчас активен:')} {mode_display}

🔮 {bold('КОУЧ')}

Если хочешь, чтобы я помог тебе самому найти решения.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Задавать открытые вопросы, отражать твои мысли, направлять. Готовых ответов не дам — ты найдёшь их сам.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}
• Жить станет легче — перестанешь закапываться в сомнениях
• Появится больше радости от простых вещей
• Начнёшь замечать возможности вместо проблем
• Перестанешь чувствовать вину за каждый шаг

🧠 {bold('ПСИХОЛОГ')}

Если хочешь копнуть вглубь, разобраться с причинами, а не следствиями.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Исследовать твои глубинные паттерны, защитные механизмы, прошлый опыт. Пойдём к корню.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}
• Перестанешь реагировать на триггеры — будешь выбирать реакцию сам
• Исчезнут старые сценарии, которые портили жизнь
• Поймёшь, откуда растут ноги у твоих страхов
• Внутри станет легче и спокойнее
• Перестанешь саботировать собственное счастье
• Отношения с собой и другими выйдут на новый уровень

⚡ {bold('ТРЕНЕР')}

Если нужны чёткие инструменты, навыки и результат.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Формировать твои поведенческие и мыслительные навыки. Работаю по законам научения: правильные действия закрепляются, ненужные — угасают.

Научу мыслить системно — видеть структуру там, где раньше был хаос. Дам инструменты ТРИЗ, чтобы ты мог находить неочевидные решения.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}

{bold('Публичное поведение — то, что видят другие:')}
• Научишься чётко формулировать мысли — тебя будут понимать с полуслова
• Освоишь алгоритмы ведения переговоров и убеждения
• Сформируешь полезные привычки и избавишься от вредных
• Будешь уверенно действовать в стрессовых ситуациях

{bold('Приватное поведение — то, что происходит внутри:')}
• Освоишь алгоритмы мыследеятельности — будешь думать быстрее и чётче
• Научишься выявлять противоречия и находить элегантные решения
• Сможешь управлять своим эмоциональным состоянием
• Создашь внутренние опоры, которые будут работать всегда

👇 {bold('Выбирай, в каком качестве я сегодня работаю:')}
"""
    
    keyboard = get_mode_selection_keyboard()
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.mode_selection)

def show_mode_selected(message: types.Message, mode: str):
    """Показывает экран подтверждения выбранного режима"""
    user_id = message.chat.id
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    data = user_data.get(user_id, {})
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Тексты для разных режимов
    mode_texts = {
        "coach": {
            "title": f"ты выбрал режим: 🔮 КОУЧ",
            "description": "Отлично! Теперь я буду работать в партнёрском стиле — задавать вопросы, отражать твои мысли, помогать тебе самому находить решения.",
            "changes": [
                "Я не буду давать готовых ответов — ты будешь находить их сам",
                "Буду направлять вопросами, а не указаниями",
                "Сфокусируемся на твоих целях и твоём видении"
            ],
            "how_next": "Ты ставишь мне цель — и я просчитываю маршрут из точки А в точку Б. Всё последующее взаимодействие будет определяться тем, куда ты хочешь прийти."
        },
        "psychologist": {
            "title": f"ты выбрал режим: 🧠 ПСИХОЛОГ",
            "description": "Хорошо. Теперь я буду работать в глубинном стиле — исследовать твои паттерны, защитные механизмы, прошлый опыт. Пойдём к корню.",
            "changes": [
                "Будем копать вглубь, а не скользить по поверхности",
                "Сфокусируемся на причинах, а не следствиях",
                "Я буду использовать терапевтические техники"
            ],
            "how_next": "Ты ставишь мне цель — я просчитываю маршрут и определяю места, которые нужно проработать. Точки, где застревают старые сценарии. Узлы, которые держат систему."
        },
        "trainer": {
            "title": f"ты выбрал режим: ⚡ ТРЕНЕР",
            "description": "Отлично! Теперь я буду работать в тренировочном стиле — давать чёткие инструкции, упражнения, ставить дедлайны. Требовать выполнения.",
            "changes": [
                "Буду формировать твои поведенческие и мыслительные навыки",
                "Получишь конкретные инструменты и алгоритмы",
                "Сфокусируемся на действиях и результате"
            ],
            "how_next": "Ты ставишь мне цель — я просчитываю маршрут и составляю список навыков, которые тебе понадобятся. Чему придётся научиться. Какие алгоритмы освоить."
        }
    }
    
    t = mode_texts.get(mode, mode_texts["coach"])
    
    changes_text = "\n".join([f"• {change}" for change in t["changes"]])
    
    full_text = f"""
🧠 {bold('ФРЕДИ: РЕЖИМ ВЫБРАН')}

{user_name}, {bold(t["title"])}

{t["description"]}

{bold('Что меняется:')}
{changes_text}

{bold('Твой профиль:')} {profile_code}

{bold('Как дальше:')}
{t["how_next"]}

👇 {bold(f'С чего начнём, {user_name}?')}
"""
    
    keyboard = get_mode_confirmation_keyboard()
    safe_send_message(message, full_text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.results)

# ============================================
# ОБРАБОТЧИКИ ЭТАПА 1
# ============================================

def show_stage_1_intro(message: types.Message):
    """Экран перед ЭТАПОМ 1"""
    user_id = message.chat.id
    set_state(user_id, TestStates.stage_1)
    
    intro_text = f"""
🧠 {bold('ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ')}

Восприятие — это линза, через которую вы смотрите на мир.

🔍 {bold('Что мы исследуем:')}
• Куда направлено ваше внимание — вовне или внутрь
• Какая тревога доминирует — страх отвержения или страх потери контроля

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Отвечайте честно — это поможет мне лучше понять вас.
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_1"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True)

def start_stage_1(call: CallbackQuery):
    """Начало ЭТАПА 1"""
    user_id = call.from_user.id
    
    update_state_data(user_id,
        stage1_current=0,
        stage1_last_answered=-1,
        stage1_start_time=time.time(),
        perception_scores={"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0}
    )
    
    ask_stage_1_question(call.message, user_id)

def ask_stage_1_question(message: types.Message, user_id: int):
    """Задаёт вопрос ЭТАПА 1"""
    data = get_state_data(user_id)
    
    current = data.get("stage1_current", 0)
    total = get_stage1_total()
    
    if current >= total:
        finish_stage_1(message, user_id)
        return
    
    question = get_stage1_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage1_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_1_answer(call: CallbackQuery):
    """Обработка ответа ЭТАПА 1"""
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage1_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage1_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        perception_scores = data.get("perception_scores", {})
        for axis, score in selected_option.get("scores", {}).items():
            if axis in ["EXTERNAL", "INTERNAL", "SYMBOLIC", "MATERIAL"]:
                perception_scores[axis] = perception_scores.get(axis, 0) + score
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 1,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'scores': selected_option.get('scores', {})
        })
        
        update_state_data(user_id,
            perception_scores=perception_scores,
            stage1_last_answered=current,
            stage1_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_1_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_1_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)

def finish_stage_1(message: types.Message, user_id: int):
    """Завершение ЭТАПА 1"""
    data = get_state_data(user_id)
    
    perception_scores = data.get("perception_scores", {})
    perception_type = determine_perception_type(perception_scores)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["perception_type"] = perception_type
    
    logger.info(f"✅ User {user_id}: Stage 1 complete, type={perception_type}")
    
    result_text = STAGE_1_FEEDBACK.get(perception_type, STAGE_1_FEEDBACK["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"])
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 2')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 2", callback_data="show_stage_2_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.stage_2)

# ============================================
# ОБРАБОТЧИКИ ЭТАПА 2
# ============================================

def show_stage_2_intro(message: types.Message):
    """Экран перед ЭТАПОМ 2"""
    user_id = message.chat.id
    data = user_data.get(user_id, {})
    
    perception_type = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    total_questions = get_stage2_total(perception_type)
    
    intro_text = f"""
🧠 {bold('ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ')}

Восприятие определяет, что вы видите. Мышление — как вы это понимаете.

🎯 {bold('Самое важное:')}
Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте. Если ничего не менять — вы попадёте именно туда.

📊 {bold('Вопросов:')} {total_questions}
⏱ {bold('Время:')} ~3-4 минуты

Продолжим исследование?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_2"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True)

def start_stage_2(call: CallbackQuery):
    """Начало ЭТАПА 2"""
    user_id = call.from_user.id
    
    update_state_data(user_id,
        stage2_current=0,
        stage2_last_answered=-1,
        stage2_start_time=time.time(),
        stage2_level_scores_dict={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0},
        strategy_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    ask_stage_2_question(call.message, user_id)

def ask_stage_2_question(message: types.Message, user_id: int):
    """Задаёт вопрос ЭТАПА 2"""
    data = get_state_data(user_id)
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    current = data.get("stage2_current", 0)
    total_questions = get_stage2_total(perception_type)
    
    if current >= total_questions:
        finish_stage_2(message, user_id)
        return
    
    question = get_stage2_question(perception_type, current)
    if not question:
        finish_stage_2(message, user_id)
        return
    
    measures = question.get("measures", "thinking")
    progress = calculate_progress(current + 1, total_questions)
    
    question_text = f"""
🧠 {bold('ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for level_num, answer_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=answer_text,
            callback_data=f"stage2_{current}_{level_num}_{measures}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_2_answer(call: CallbackQuery):
    """Обработка ответа ЭТАПА 2"""
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        selected_level = parts[2]
        measures = parts[3]
        
        last_answered = data.get("stage2_last_answered", -1)
        if current <= last_answered:
            return
        
        perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception_type, current)
        if not question:
            return
        
        answer_text = question["options"].get(selected_level, "неизвестно")
        
        stage2_level_scores_dict = data.get("stage2_level_scores_dict", {})
        
        if measures == "thinking":
            points = get_stage2_score(perception_type, current, selected_level)
            stage2_level_scores_dict[selected_level] = stage2_level_scores_dict.get(selected_level, 0) + points
        
        strategy_levels = data.get("strategy_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if measures in ["СБ", "ТФ", "УБ", "ЧВ"]:
            try:
                value = int(selected_level)
                strategy_levels[measures].append(value)
            except ValueError:
                pass
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 2,
            'question_index': current,
            'question': question['text'],
            'answer': answer_text,
            'option': selected_level,
            'measures': measures,
            'perception_type': perception_type
        })
        
        update_state_data(user_id,
            stage2_level_scores_dict=stage2_level_scores_dict,
            strategy_levels=strategy_levels,
            stage2_last_answered=current,
            stage2_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_2_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_2_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)

def finish_stage_2(message: types.Message, user_id: int):
    """Завершение ЭТАПА 2"""
    data = get_state_data(user_id)
    
    level_scores_dict = data.get("stage2_level_scores_dict", {})
    thinking_level = calculate_thinking_level_by_scores(level_scores_dict)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["thinking_level"] = thinking_level
    
    # Сохраняем стратегии
    strategy_levels = data.get("strategy_levels", {})
    user_data[user_id]["behavioral_levels"] = strategy_levels
    
    perception_type = user_data.get(user_id, {}).get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    level_group = get_level_group(thinking_level)
    
    logger.info(f"✅ User {user_id}: Stage 2 complete, level={thinking_level}")
    
    result_text = STAGE_2_FEEDBACK.get((perception_type, level_group))
    if not result_text:
        result_text = STAGE_2_FEEDBACK[("СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "1-3")]
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 3')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 3", callback_data="show_stage_3_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.stage_3)

# ============================================
# ОБРАБОТЧИКИ ЭТАПА 3
# ============================================

def show_stage_3_intro(message: types.Message):
    """Экран перед ЭТАПОМ 3"""
    user_id = message.chat.id
    
    intro_text = f"""
🧠 {bold('ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ')}

Восприятие определяет, что вы видите.
Мышление — как вы это понимаете.

Конфигурация поведения — это то, как вы на это реагируете.

🔍 {bold('Здесь мы исследуем:')}
• Ваши автоматические реакции
• Как вы действуете в разных ситуациях
• Какие стратегии поведения закреплены

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Продолжим?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_3"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True)

def start_stage_3(call: CallbackQuery):
    """Начало ЭТАПА 3"""
    user_id = call.from_user.id
    
    update_state_data(user_id,
        stage3_current=0,
        stage3_last_answered=-1,
        stage3_start_time=time.time(),
        stage3_level_scores=[],
        behavioral_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    ask_stage_3_question(call.message, user_id)

def ask_stage_3_question(message: types.Message, user_id: int):
    """Задаёт вопрос ЭТАПА 3"""
    data = get_state_data(user_id)
    
    current = data.get("stage3_current", 0)
    total = get_stage3_total()
    
    if current >= total:
        finish_stage_3(message, user_id)
        return
    
    question = get_stage3_question(current)
    strategy = question.get("strategy", "УБ")
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option_text in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option_text,
            callback_data=f"stage3_{current}_{option_id}_{strategy}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_3_answer(call: CallbackQuery):
    """Обработка ответа ЭТАПА 3"""
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        strategy = parts[3]
        
        stage3_current = data.get("stage3_current", 0)
        
        if current < stage3_current:
            ask_stage_3_question(call.message, user_id)
            return
        
        question = get_stage3_question(current)
        option_text = question["options"].get(option_id)
        
        if not option_text:
            return
        
        try:
            level_val = int(option_id)
        except ValueError:
            level_val = 1
        
        stage3_level_scores = data.get("stage3_level_scores", [])
        stage3_level_scores.append(level_val)
        
        behavioral_levels = data.get("behavioral_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if strategy in ["СБ", "ТФ", "УБ", "ЧВ"]:
            behavioral_levels[strategy].append(level_val)
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 3,
            'question_index': current,
            'question': question['text'],
            'answer': option_text,
            'answer_value': level_val,
            'strategy': strategy
        })
        
        update_state_data(user_id,
            stage3_level_scores=stage3_level_scores,
            behavioral_levels=behavioral_levels,
            stage3_last_answered=current,
            stage3_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_3_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_3_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)

def finish_stage_3(message: types.Message, user_id: int):
    """Завершение ЭТАПА 3"""
    data = get_state_data(user_id)
    
    stage2_level = user_data.get(user_id, {}).get("thinking_level", 1)
    stage3_scores = data.get("stage3_level_scores", [])
    
    final_level = calculate_final_level(stage2_level, stage3_scores)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["final_level"] = final_level
    
    # Сохраняем поведенческие уровни
    behavioral_levels = data.get("behavioral_levels", {})
    if "behavioral_levels" not in user_data[user_id]:
        user_data[user_id]["behavioral_levels"] = {}
    
    for key, values in behavioral_levels.items():
        if key in user_data[user_id]["behavioral_levels"]:
            user_data[user_id]["behavioral_levels"][key].extend(values)
        else:
            user_data[user_id]["behavioral_levels"][key] = values
    
    behavior_level = map_to_stage3_feedback_level(final_level)
    
    logger.info(f"✅ User {user_id}: Stage 3 complete, final_level={final_level}")
    
    result_text = STAGE_3_FEEDBACK.get(behavior_level, STAGE_3_FEEDBACK[1])
    
    # Очищаем от форматирования
    result_text = clean_text_for_safe_display(result_text)
    
    text = f"{result_text}\n\n▶️ {bold('Перейти к этапу 4')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Перейти к этапу 4", callback_data="show_stage_4_intro"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.stage_4)

# ============================================
# ОБРАБОТЧИКИ ЭТАПА 4
# ============================================

def show_stage_4_intro(message: types.Message):
    """Экран перед ЭТАПОМ 4"""
    user_id = message.chat.id
    
    intro_text = f"""
🧠 {bold('ЭТАП 4: ТОЧКА РОСТА')}

Восприятие — что вы видите.
Мышление — как понимаете.
Поведение — как реагируете.

🌍 Но она живёт внутри внешней системы — общества, которое постоянно меняется.

⚡ Когда одна система меняется, а другая — нет, возникает напряжение.

🔍 {bold('Здесь мы найдём:')} где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.

📊 {bold('Вопросов:')} 8
⏱ {bold('Время:')} ~3 минуты

Готовы найти свою точку роста?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_4"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True)

def start_stage_4(call: CallbackQuery):
    """Начало ЭТАПА 4"""
    user_id = call.from_user.id
    
    update_state_data(user_id,
        stage4_current=0,
        stage4_last_answered=-1,
        stage4_start_time=time.time(),
        dilts_counts={"ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0}
    )
    
    ask_stage_4_question(call.message, user_id)

def ask_stage_4_question(message: types.Message, user_id: int):
    """Задаёт вопрос ЭТАПА 4"""
    data = get_state_data(user_id)
    
    current = data.get("stage4_current", 0)
    total = get_stage4_total()
    
    if current >= total:
        finish_stage_4(message, user_id)
        return
    
    question = get_stage4_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 4: ТОЧКА РОСТА')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage4_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_4_answer(call: CallbackQuery):
    """Обработка ответа ЭТАПА 4"""
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage4_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage4_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        dilts = selected_option.get("dilts", "BEHAVIOR")
        dilts_counts = data.get("dilts_counts", {})
        dilts_counts[dilts] = dilts_counts.get(dilts, 0) + 1
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 4,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'dilts': dilts
        })
        
        update_state_data(user_id,
            dilts_counts=dilts_counts,
            stage4_last_answered=current,
            stage4_current=current + 1,
            all_answers=all_answers
        )
        
        ask_stage_4_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_4_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)

def finish_stage_4(message: types.Message, user_id: int):
    """Завершение ЭТАПА 4"""
    data = get_state_data(user_id)
    
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["dilts_counts"] = dilts_counts
    user_data[user_id]["dominant_dilts"] = dominant_dilts
    
    # Рассчитываем финальный профиль
    profile_data = calculate_profile_final(user_data[user_id])
    user_data[user_id]["profile_data"] = profile_data
    
    # Строим конфайнмент-модель
    scores = {}
    for vector in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = user_data[user_id].get("behavioral_levels", {}).get(vector, [])
        scores[vector] = sum(levels) / len(levels) if levels else 3
    
    model = ConfinementModel9(user_id)
    model.build_from_profile(scores, user_data[user_id].get('history', []))
    user_data[user_id]["confinement_model"] = model.to_dict()
    
    logger.info(f"✅ User {user_id}: Stage 4 complete, profile={profile_data.get('display_name', 'unknown')}")
    
    # Показываем предварительный профиль
    show_preliminary_profile(message, user_id)

# ============================================
# НОВЫЕ ФУНКЦИИ: ПОКАЗ ПРЕДВАРИТЕЛЬНОГО ПРОФИЛЯ
# ============================================

def show_preliminary_profile(message: types.Message, user_id: int):
    """Показывает предварительный портрет простым языком"""
    
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "unknown")
    thinking_level = data.get("thinking_level", 5)
    
    simple_profile = convert_to_simple_language(
        scores, perception_type, thinking_level
    )
    
    confidence = calculate_profile_confidence(data)
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    text = f"""
🧠 {bold('ПРЕДВАРИТЕЛЬНЫЙ ПОРТРЕТ')}

{simple_profile['attention_desc']}

{simple_profile['thinking_desc']}

📊 {bold('ТВОИ ВЕКТОРЫ:')}
• {bold('Реакция на давление:')} {simple_profile['sb_desc']}
• {bold('Отношение к деньгам:')} {simple_profile['tf_desc']}
• {bold('Понимание мира:')} {simple_profile['ub_desc']}
• {bold('Отношения с людьми:')} {simple_profile['chv_desc']}

🎯 {bold('Точка роста:')} {simple_profile['growth_point']}

📊 {bold('Уверенность:')} {confidence_bar} {int(confidence*100)}%

👇 {bold('ЭТО ПОХОЖЕ НА ВАС?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ ДА", callback_data="profile_confirm"),
        InlineKeyboardButton("❓ ЕСТЬ СОМНЕНИЯ", callback_data="profile_doubt")
    )
    keyboard.row(InlineKeyboardButton("🔄 НЕТ", callback_data="profile_reject"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.profile_confirmation)

# ============================================
# НОВЫЕ ФУНКЦИИ: ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ПРОФИЛЯ
# ============================================

def profile_confirm(call: CallbackQuery):
    """Пользователь подтвердил профиль"""
    
    safe_send_message(call.message, "✅ Отлично! Тогда исследуем глубину...", delete_previous=True)
    
    # Показываем 5-й этап
    show_stage_5_intro(call.message)

def profile_doubt(call: CallbackQuery):
    """Пользователь сомневается"""
    
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    
    current_levels = {}
    for vector in VECTORS:
        levels = data.get("behavioral_levels", {}).get(vector, [])
        current_levels[vector] = sum(levels) / len(levels) if levels else 3
    
    ask_whats_wrong(call, current_levels)

def profile_reject(call: CallbackQuery):
    """Пользователь полностью не согласен - показываем анекдот"""
    
    # Текст с анекдотом
    anecdote = """
🧠 <b>ЧЕСТНОСТЬ - ЛУЧШАЯ ПОЛИТИКА</b>

Две подруги решили сходить на ипподром. Приходят, а там скачки, все ставки делают. Решили и они ставку сделать — вдруг повезёт? Одна другой и говорит: «Слушай, у тебя какой размер груди?». Вторая: «Второй… а у тебя?». Первая: «Третий… ну давай на пятую поставим — чтоб сумма была…».

Поставили на пятую, лошадь приходит первая, они счастливые прибегают домой с деньгами и мужьям рассказывают, как было дело.

На следующий день мужики тоже решили сходить на скачки — а вдруг им повезёт? Когда решали, на какую ставить, один говорит: «Ты сколько раз за ночь свою жену можешь удовлетворить?». Другой говорит: «Ну, три…». Первый: «А я четыре… ну давай на седьмую поставим».

Поставили на седьмую, первой пришла вторая.

Мужики переглянулись: «Не напиздили бы — выиграли…».

<b>Мораль:</b> Если врать в тесте — результат будет как у мужиков на скачках. Хотите попробовать еще раз?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔄 ПРОЙТИ ТЕСТ ЕЩЕ РАЗ", callback_data="restart_test"))
    keyboard.row(InlineKeyboardButton("👋 ДОСВИДУЛИ", callback_data="goodbye"))
    
    safe_send_message(
        call.message,
        anecdote,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def handle_goodbye(call: CallbackQuery):
    """Обработчик кнопки Досвидули"""
    
    safe_send_message(
        call.message,
        f"👋 {bold('До свидания!')}\n\nБуду рад помочь, если решите вернуться. Просто напишите /start",
        parse_mode='HTML',
        delete_previous=True
    )
    
    clear_state(call.from_user.id)

def ask_whats_wrong(call: CallbackQuery, current_levels: dict):
    """Спрашивает, что именно не так"""
    
    text = f"""
🔍 {bold('ДАВАЙ УТОЧНИМ')}

Что именно вам не подходит?
(можно выбрать несколько)

🎭 Про людей — я не так сильно завишу от чужого мнения
💰 Про деньги — у меня с ними по-другому
🔍 Про знаки — я вполне себе анализирую
🤝 Про отношения — я знаю, чего хочу
🛡 Про давление — я реагирую иначе

👇 {bold('Выберите и нажмите ДАЛЬШЕ')}
"""
    
    update_state_data(call.from_user.id, clarifying_levels=current_levels)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🎭 Про людей", callback_data="discrepancy_people"))
    keyboard.row(InlineKeyboardButton("💰 Про деньги", callback_data="discrepancy_money"))
    keyboard.row(InlineKeyboardButton("🔍 Про знаки", callback_data="discrepancy_signs"))
    keyboard.row(InlineKeyboardButton("🤝 Про отношения", callback_data="discrepancy_relations"))
    keyboard.row(InlineKeyboardButton("🛡 Про давление", callback_data="discrepancy_sb"))
    keyboard.row(InlineKeyboardButton("➡️ ДАЛЬШЕ", callback_data="clarify_next"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    set_state(call.from_user.id, TestStates.clarifying_selection)
    
    update_state_data(call.from_user.id, discrepancies=[])

def handle_discrepancy(call: CallbackQuery, discrepancy: str):
    """Обрабатывает выбор расхождения"""
    
    data = get_state_data(call.from_user.id)
    discrepancies = data.get("discrepancies", [])
    
    if discrepancy not in discrepancies:
        discrepancies.append(discrepancy)
        update_state_data(call.from_user.id, discrepancies=discrepancies)
        safe_send_message(call.message, f"✅ Добавлено", delete_previous=True)
    else:
        discrepancies.remove(discrepancy)
        update_state_data(call.from_user.id, discrepancies=discrepancies)
        safe_send_message(call.message, f"❌ Убрано", delete_previous=True)

def clarify_next(call: CallbackQuery):
    """Переходит к уточняющим вопросам"""
    
    data = get_state_data(call.from_user.id)
    discrepancies = data.get("discrepancies", [])
    current_levels = data.get("clarifying_levels", {})
    
    if not discrepancies:
        safe_send_message(call.message, "Выберите хотя бы одно расхождение!", delete_previous=True)
        return
    
    questions = get_clarifying_questions(discrepancies, current_levels)
    
    if not questions:
        safe_send_message(call.message, "Зададим общие уточняющие вопросы", delete_previous=True)
        return
    
    update_state_data(call.from_user.id,
        clarifying_questions=questions,
        clarifying_current=0,
        clarifying_answers=[]
    )
    
    ask_clarifying_question(call.message, call.from_user.id)

def ask_clarifying_question(message: types.Message, user_id: int):
    """Задаёт уточняющий вопрос"""
    
    data = get_state_data(user_id)
    questions = data.get("clarifying_questions", [])
    current = data.get("clarifying_current", 0)
    
    if current >= len(questions):
        update_profile_with_clarifications(message, user_id)
        return
    
    question = questions[current]
    
    question_text = f"""
🔍 {bold(f'УТОЧНЯЮЩИЙ ВОПРОС {current + 1}/{len(questions)}')}

{question['text']}
"""
    
    keyboard = InlineKeyboardMarkup()
    options = question.get('options', {})
    for opt_key, opt_text in options.items():
        keyboard.add(InlineKeyboardButton(
            text=opt_text,
            callback_data=f"clarify_answer_{current}_{opt_key}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_clarifying_answer(call: CallbackQuery):
    """Обрабатывает ответ на уточняющий вопрос"""
    
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    parts = call.data.split("_")
    if len(parts) < 4:
        return
    
    if not parts[2].isdigit():
        return
    current = int(parts[2])
    answer_key = parts[3]
    
    questions = data.get("clarifying_questions", [])
    if current >= len(questions):
        return
    
    question = questions[current]
    
    answers = data.get("clarifying_answers", [])
    answers.append({
        "question": question['text'],
        "answer_key": answer_key,
        "answer_text": question['options'].get(answer_key, ""),
        "type": question.get('type'),
        "target": question.get('target') or question.get('vector')
    })
    
    update_state_data(user_id,
        clarifying_answers=answers,
        clarifying_current=current + 1
    )
    
    ask_clarifying_question(call.message, user_id)

def update_profile_with_clarifications(message: types.Message, user_id: int):
    """Обновляет профиль с учётом уточнений"""
    
    data = get_state_data(user_id)
    
    iteration = data.get("clarification_iteration", 0) + 1
    update_state_data(user_id, clarification_iteration=iteration)
    
    show_preliminary_profile(message, user_id)

# ============================================
# НОВЫЕ ФУНКЦИИ: 5-Й ЭТАП
# ============================================

def show_stage_5_intro(message: types.Message):
    """Экран перед 5-м этапом"""
    
    intro_text = f"""
🧠 {bold('ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ')}

Мы узнали, как вы воспринимаете мир, мыслите и действуете.
Теперь пришло время заглянуть глубже — в то, что сформировало вас.

🔍 {bold('Здесь мы исследуем:')}
• Какой у вас тип привязанности (из детства)
• Какие защитные механизмы вы используете
• Какие глубинные убеждения управляют вами
• Чего вы боитесь на самом деле

📊 {bold('Вопросов:')} 10
⏱ {bold('Время:')} ~5 минут

👇 {bold('Готовы заглянуть вглубь себя?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Начать исследование", callback_data="start_stage_5"))
    
    safe_send_message(message, intro_text, reply_markup=keyboard, delete_previous=True)
    set_state(message.chat.id, TestStates.stage_5)

def start_stage_5(call: CallbackQuery):
    """Начало 5-го этапа"""
    user_id = call.from_user.id
    
    update_state_data(user_id,
        stage5_current=0,
        stage5_last_answered=-1,
        stage5_answers=[]
    )
    
    ask_stage_5_question(call.message, user_id)

def ask_stage_5_question(message: types.Message, user_id: int):
    """Задаёт вопрос 5-го этапа"""
    
    data = get_state_data(user_id)
    
    current = data.get("stage5_current", 0)
    total = get_stage5_total()
    
    if current >= total:
        finish_stage_5(message, user_id)
        return
    
    question = get_stage5_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 {bold('ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ')}

{question['text']}

{progress}
"""
    
    keyboard = InlineKeyboardMarkup()
    for option_id, option in question["options"].items():
        keyboard.add(InlineKeyboardButton(
            text=option["text"],
            callback_data=f"stage5_{current}_{option_id}"
        ))
    
    safe_send_message(message, question_text, reply_markup=keyboard, delete_previous=True)

def handle_stage_5_answer(call: CallbackQuery):
    """Обработка ответа 5-го этапа"""
    
    user_id = call.from_user.id
    data = get_state_data(user_id)
    
    if data.get("processing", False):
        return
    
    update_state_data(user_id, processing=True)
    
    try:
        parts = call.data.split("_")
        if len(parts) < 3:
            return
        
        if not parts[1].isdigit():
            return
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage5_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage5_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        stage5_answers = data.get("stage5_answers", [])
        stage5_answers.append({
            'question_id': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'pattern': selected_option.get('pattern'),
            'target': question.get('target')
        })
        
        update_state_data(user_id,
            stage5_answers=stage5_answers,
            stage5_last_answered=current,
            stage5_current=current + 1
        )
        
        ask_stage_5_question(call.message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        ask_stage_5_question(call.message, user_id)
    finally:
        update_state_data(user_id, processing=False)

def finish_stage_5(message: types.Message, user_id: int):
    """Завершение 5-го этапа"""
    
    data = get_state_data(user_id)
    stage5_answers = data.get("stage5_answers", [])
    
    deep_patterns = analyze_stage5_results(stage5_answers)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["deep_patterns"] = deep_patterns
    
    logger.info(f"✅ User {user_id}: Stage 5 complete")
    
    show_final_profile(message, user_id)

# ============================================
# ФИНАЛЬНЫЙ ПРОФИЛЬ
# ============================================

def show_final_profile(message: types.Message, user_id: int):
    """Показывает финальный профиль после всех этапов"""
    
    data = user_data.get(user_id, {})
    
    if data.get("ai_generated_profile"):
        show_ai_generated_profile(message, user_id, data["ai_generated_profile"])
        return
    
    # Отправляем статусное сообщение (БЕЗ КНОПОК)
    status_msg = safe_send_message(
        message,
        "🧠 Анализирую данные...\n\n"
        "Собираю воедино результаты 5 этапов тестирования.\n"
        "Это займёт около 20-30 секунд.\n\n"
        "Формирую ваш точный психологический портрет...",
        delete_previous=True
    )
    
    # Здесь должен быть вызов AI генерации
    # ai_profile = generate_ai_profile(user_id, data)
    ai_profile = None  # Заглушка
    
    if ai_profile:
        user_data[user_id]["ai_generated_profile"] = ai_profile
        show_ai_generated_profile(message, user_id, ai_profile, status_msg)
    else:
        show_old_final_profile(message, user_id, status_msg)

def show_ai_generated_profile(message: types.Message, user_id: int, ai_profile: str, status_msg: types.Message = None):
    """Показывает профиль, сгенерированный ИИ с красивым форматированием"""
    
    # Форматируем текст
    formatted_profile = format_profile_text(ai_profile)
    
    # Добавляем заголовок, если его нет
    if not formatted_profile.startswith("🧠"):
        formatted_profile = f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}\n\n{formatted_profile}"
    
    text = f"""
{formatted_profile}

👇 {bold('Что дальше?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(
        InlineKeyboardButton("🎤 ХОЧУ ВЫСКАЗАТЬСЯ", callback_data="ask_question"),
        InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    # Удаляем статусное сообщение
    if status_msg:
        try:
            safe_delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
    
    # Отправляем сообщение
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    set_state(user_id, TestStates.profile_generated)

def show_old_final_profile(message: types.Message, user_id: int, status_msg: types.Message = None):
    """Старая версия финального профиля (резерв)"""
    data = user_data.get(user_id, {})
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_text = get_human_readable_profile(
        scores, 
        model=None,
        perception_type=perception_type,
        thinking_level=thinking_level,
        dominant_dilts=dominant_dilts
    )
    
    text = f"{profile_text}\n\n👇 {bold('Что дальше?')}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection"))
    
    # Удаляем статусное сообщение
    if status_msg:
        try:
            safe_delete_message(message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    set_state(user_id, TestStates.profile_generated)

# ============================================
# ФУНКЦИИ ДЛЯ КОНТЕКСТА
# ============================================

def start_context(message: types.Message):
    """Начинает сбор контекста (обязательный)"""
    user_id = message.chat.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    
    # Принудительный сброс (чтобы точно спросило)
    context.city = None
    context.gender = None
    context.age = None
    
    question, keyboard = await context.ask_for_context()
    
    if question:
        safe_send_message(
            message,
            f"📝 {bold('Давайте познакомимся')}\n\n{question}",
            reply_markup=keyboard,
            parse_mode='HTML',
            delete_previous=True
        )
        set_state(user_id, TestStates.awaiting_context)
    else:
        show_context_complete(message, context)

def handle_context_message(message: types.Message):
    """Обрабатывает ответы на контекстные вопросы"""
    user_id = message.from_user.id
    context = user_contexts.get(user_id)
    
    if not context or not context.awaiting_context:
        return False
    
    text = message.text.strip()
    
    if context.awaiting_context == "city":
        context.city = text
        context.awaiting_context = None
        context.update_weather()
        question, keyboard = context.ask_for_context()
        
        if question:
            safe_send_message(
                message,
                f"📝 {bold('Давайте познакомимся')}\n\n{question}",
                reply_markup=keyboard,
                parse_mode='HTML',
                delete_previous=True
            )
        else:
            show_context_complete(message, context)
    
    elif context.awaiting_context == "age":
        try:
            age = int(text)
            if 1 <= age <= 120:
                context.age = age
                context.awaiting_context = None
                question, keyboard = context.ask_for_context()
                
                if question:
                    safe_send_message(
                        message,
                        f"📝 {bold('Давайте познакомимся')}\n\n{question}",
                        reply_markup=keyboard,
                        parse_mode='HTML',
                        delete_previous=True
                    )
                else:
                    show_context_complete(message, context)
            else:
                safe_send_message(
                    message,
                    bold("❌ Возраст должен быть от 1 до 120 лет.\n\n📅 Сколько вам лет? (напишите число)"),
                    parse_mode='HTML',
                    delete_previous=True
                )
        except ValueError:
            safe_send_message(
                message,
                bold("❌ Пожалуйста, введите число.\n\n📅 Сколько вам лет? (напишите число)"),
                parse_mode='HTML',
                delete_previous=True
            )
    
    return True

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
    
    safe_send_message(message, summary, reply_markup=keyboard, delete_previous=True)
    
    clear_state(message.from_user.id)

# ============================================
# ФУНКЦИИ ДЛЯ ГЛАВНОГО МЕНЮ
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
    
    safe_send_message(message, welcome_text, reply_markup=keyboard)

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
    
    safe_send_message(message, text, reply_markup=keyboard)

# ============================================
# ДИНАМИЧЕСКИЙ ПОДБОР ЦЕЛЕЙ
# ============================================

def get_dynamic_destinations(profile_code: str, mode: str) -> List[Dict]:
    """Динамически подбирает цели под профиль и режим"""
    
    # Парсим профиль
    parts = profile_code.split('_')
    scores = {}
    for part in parts:
        if '-' in part:
            vec, val = part.split('-')
            scores[vec] = int(val)
    
    if not scores:
        scores = {"СБ": 4, "ТФ": 4, "УБ": 4, "ЧВ": 4}
    
    # Находим слабые и сильные стороны
    sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
    weakest = sorted_vectors[0] if sorted_vectors else ("СБ", 4)
    strongest = sorted_vectors[-1] if sorted_vectors else ("ЧВ", 4)
    
    # База целей для разных режимов
    destinations_db = {
        "coach": {
            "weak": {
                "СБ": [
                    {"id": "fear_work", "name": "Проработать страхи", "time": "3-4 недели", "difficulty": "medium"},
                    {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium"},
                    {"id": "calm", "name": "Найти внутреннее спокойствие", "time": "3-5 недель", "difficulty": "hard"}
                ],
                "ТФ": [
                    {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium"},
                    {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard"},
                    {"id": "financial_plan", "name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy"}
                ],
                "УБ": [
                    {"id": "meaning", "name": "Найти смысл и предназначение", "time": "4-6 недель", "difficulty": "hard"},
                    {"id": "system_thinking", "name": "Развить системное мышление", "time": "3-5 недель", "difficulty": "medium"},
                    {"id": "trust", "name": "Научиться доверять миру", "time": "3-4 недели", "difficulty": "medium"}
                ],
                "ЧВ": [
                    {"id": "relations", "name": "Улучшить отношения", "time": "4-6 недель", "difficulty": "hard"},
                    {"id": "boundaries_people", "name": "Выстроить границы с людьми", "time": "3-4 недели", "difficulty": "medium"},
                    {"id": "attachment", "name": "Проработать тип привязанности", "time": "5-7 недель", "difficulty": "hard"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "leadership", "name": "Развить лидерские качества", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "stress_resistance", "name": "Усилить стрессоустойчивость", "time": "3-4 недели", "difficulty": "easy"}
                ],
                "ТФ": [
                    {"id": "business", "name": "Развить бизнес-мышление", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "investments", "name": "Начать инвестировать", "time": "4-6 недель", "difficulty": "medium"}
                ],
                "УБ": [
                    {"id": "strategy", "name": "Развить стратегическое мышление", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "wisdom", "name": "Углубить понимание себя", "time": "3-5 недель", "difficulty": "easy"}
                ],
                "ЧВ": [
                    {"id": "empathy", "name": "Развить эмпатию", "time": "3-4 недели", "difficulty": "easy"},
                    {"id": "community", "name": "Создать сообщество", "time": "6-8 недель", "difficulty": "hard"}
                ]
            },
            "general": [
                {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard"},
                {"id": "balance", "name": "Обрести баланс", "time": "4-6 недель", "difficulty": "medium"},
                {"id": "growth", "name": "Личностный рост", "time": "6-8 недель", "difficulty": "medium"}
            ]
        },
        "psychologist": {
            "weak": {
                "СБ": [
                    {"id": "fear_origin", "name": "Найти источник страхов", "time": "4-6 недель", "difficulty": "hard"},
                    {"id": "trauma", "name": "Проработать травму", "time": "6-8 недель", "difficulty": "hard"},
                    {"id": "safety", "name": "Сформировать базовое чувство безопасности", "time": "5-7 недель", "difficulty": "hard"}
                ],
                "ТФ": [
                    {"id": "money_psychology", "name": "Понять психологию денег", "time": "4-5 недель", "difficulty": "medium"},
                    {"id": "worth", "name": "Проработать чувство собственной ценности", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "scarcity", "name": "Проработать сценарий дефицита", "time": "4-6 недель", "difficulty": "medium"}
                ],
                "УБ": [
                    {"id": "core_beliefs", "name": "Найти глубинные убеждения", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "schemas", "name": "Проработать жизненные сценарии", "time": "6-8 недель", "difficulty": "hard"},
                    {"id": "meaning_deep", "name": "Экзистенциальный поиск", "time": "7-9 недель", "difficulty": "hard"}
                ],
                "ЧВ": [
                    {"id": "attachment_style", "name": "Проработать тип привязанности", "time": "6-8 недель", "difficulty": "hard"},
                    {"id": "inner_child", "name": "Исцелить внутреннего ребёнка", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "family_system", "name": "Проработать семейную систему", "time": "6-8 недель", "difficulty": "hard"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "resilience", "name": "Укрепить психологическую устойчивость", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "protection", "name": "Трансформировать защитные механизмы", "time": "5-7 недель", "difficulty": "medium"}
                ],
                "ТФ": [
                    {"id": "abundance", "name": "Сформировать мышление изобилия", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "money_freedom", "name": "Обрести финансовую свободу", "time": "6-8 недель", "difficulty": "hard"}
                ],
                "УБ": [
                    {"id": "wisdom_deep", "name": "Углубить мудрость", "time": "5-7 недель", "difficulty": "medium"},
                    {"id": "integration", "name": "Интегрировать тени", "time": "6-8 недель", "difficulty": "hard"}
                ],
                "ЧВ": [
                    {"id": "intimacy", "name": "Научиться близости", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "love", "name": "Проработать способность любить", "time": "6-8 недель", "difficulty": "hard"}
                ]
            },
            "general": [
                {"id": "self_discovery", "name": "Глубинное самопознание", "time": "7-9 недель", "difficulty": "hard"},
                {"id": "healing", "name": "Исцеление внутренних ран", "time": "8-10 недель", "difficulty": "hard"},
                {"id": "integration_deep", "name": "Интеграция личности", "time": "9-12 недель", "difficulty": "hard"}
            ]
        },
        "trainer": {
            "weak": {
                "СБ": [
                    {"id": "assertiveness", "name": "Развить ассертивность", "time": "3-4 недели", "difficulty": "medium"},
                    {"id": "conflict_skills", "name": "Освоить навыки конфликта", "time": "4-5 недель", "difficulty": "medium"},
                    {"id": "courage", "name": "Тренировка смелости", "time": "3-5 недель", "difficulty": "hard"}
                ],
                "ТФ": [
                    {"id": "money_skills", "name": "Освоить навыки управления деньгами", "time": "3-4 недели", "difficulty": "easy"},
                    {"id": "income_skills", "name": "Навыки увеличения дохода", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "investment_skills", "name": "Навыки инвестирования", "time": "5-7 недель", "difficulty": "hard"}
                ],
                "УБ": [
                    {"id": "thinking_tools", "name": "Освоить инструменты мышления", "time": "4-5 недель", "difficulty": "medium"},
                    {"id": "triz", "name": "Научиться ТРИЗ", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "decision_making", "name": "Навыки принятия решений", "time": "3-4 недели", "difficulty": "easy"}
                ],
                "ЧВ": [
                    {"id": "communication_skills", "name": "Развить навыки общения", "time": "3-4 недели", "difficulty": "easy"},
                    {"id": "negotiation", "name": "Навыки переговоров", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "influence", "name": "Навыки влияния", "time": "5-7 недель", "difficulty": "hard"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "leader_courage", "name": "Лидерская смелость", "time": "4-6 недель", "difficulty": "medium"},
                    {"id": "crisis_management", "name": "Управление в кризисах", "time": "5-7 недель", "difficulty": "hard"}
                ],
                "ТФ": [
                    {"id": "wealth_building", "name": "Навыки создания капитала", "time": "6-8 недель", "difficulty": "hard"},
                    {"id": "financial_strategy", "name": "Финансовая стратегия", "time": "5-7 недель", "difficulty": "hard"}
                ],
                "УБ": [
                    {"id": "system_analysis", "name": "Системный анализ", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "strategic_thinking", "name": "Стратегическое мышление", "time": "6-8 недель", "difficulty": "hard"}
                ],
                "ЧВ": [
                    {"id": "team_building", "name": "Построение команды", "time": "5-7 недель", "difficulty": "hard"},
                    {"id": "leadership", "name": "Лидерские навыки", "time": "6-8 недель", "difficulty": "hard"}
                ]
            },
            "general": [
                {"id": "productivity", "name": "Повысить продуктивность", "time": "4-6 недель", "difficulty": "medium"},
                {"id": "habit_building", "name": "Сформировать полезные привычки", "time": "3-5 недель", "difficulty": "easy"},
                {"id": "skill_mastery", "name": "Мастерство в ключевых навыках", "time": "8-10 недель", "difficulty": "hard"}
            ]
        }
    }
    
    mode_db = destinations_db.get(mode, destinations_db["coach"])
    
    # Собираем цели
    destinations = []
    
    # Цели для слабого вектора
    if weakest[0] in mode_db["weak"]:
        destinations.extend(mode_db["weak"][weakest[0]])
    
    # Цели для сильного вектора (развитие силы)
    if strongest[0] in mode_db["strong"]:
        destinations.extend(mode_db["strong"][strongest[0]])
    
    # Добавляем общие цели
    destinations.extend(mode_db["general"])
    
    # Убираем дубликаты по id
    seen = set()
    unique_destinations = []
    for dest in destinations:
        if dest["id"] not in seen:
            seen.add(dest["id"])
            unique_destinations.append(dest)
    
    return unique_destinations[:9]  # Не больше 9 целей

# ============================================
# ЭКРАН ДИНАМИЧЕСКОГО ВЫБОРА ЦЕЛЕЙ
# ============================================

def show_dynamic_destinations(call: CallbackQuery):
    """Показывает динамически подобранные цели"""
    
    user_id = call.from_user.id
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    data = user_data.get(user_id, {})
    mode = data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем динамические цели
    destinations = get_dynamic_destinations(profile_code, mode)
    
    text = f"""
🧠 {bold('ФРЕДИ: ВЫБЕРИТЕ ЦЕЛЬ')}

{user_name}, я проанализировал твой профиль и подобрал цели, которые сейчас наиболее актуальны.

{bold('Твой профиль:')} {profile_code}
{bold('Режим:')} {mode_config['emoji']} {mode_config['name']}

👇 {bold('Куда двинемся?')}
"""
    
    # Строим клавиатуру
    keyboard = InlineKeyboardMarkup()
    
    for dest in destinations:
        # Определяем эмодзи сложности
        difficulty_emoji = {
            "easy": "🟢",
            "medium": "🟡",
            "hard": "🔴"
        }.get(dest["difficulty"], "⚪")
        
        button_text = f"{difficulty_emoji} {dest['name']}"
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"dynamic_dest_{dest['id']}"
        ))
    
    keyboard.add(InlineKeyboardButton(
        text="✏️ Сформулирую сам", 
        callback_data="custom_destination"
    ))
    keyboard.add(InlineKeyboardButton(
        text="◀️ НАЗАД", 
        callback_data="back_to_mode_selected"
    ))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        delete_previous=True
    )
    set_state(user_id, TestStates.destination_selection)

def handle_dynamic_destination(call: CallbackQuery):
    """Обрабатывает выбор динамической цели"""
    
    dest_id = call.data.replace("dynamic_dest_", "")
    
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    mode = data.get("communication_mode", "coach")
    profile_code = data.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем все цели
    all_destinations = get_dynamic_destinations(profile_code, mode)
    
    # Находим выбранную
    dest_info = None
    for dest in all_destinations:
        if dest["id"] == dest_id:
            dest_info = dest
            break
    
    if not dest_info:
        safe_send_message(call.message, "Цель не найдена", delete_previous=True)
        return
    
    # Сохраняем выбранную цель
    update_state_data(user_id,
        current_destination=dest_info,
        route_step=1,
        route_progress=[]
    )
    
    # Показываем теоретический путь
    show_theoretical_path(call, dest_info)

# ============================================
# ПРОВЕРКА РЕАЛЬНОСТИ
# ============================================

def show_theoretical_path(call: CallbackQuery, goal_info: Dict):
    """
    Показывает теоретический путь к цели после её выбора
    """
    
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal_id = goal_info.get("id", "income_growth")
    mode = data.get("communication_mode", "coach")
    
    # Получаем теоретический путь
    path = get_theoretical_path(goal_id, mode)
    
    # Сохраняем путь в состоянии
    update_state_data(user_id, theoretical_path=path)
    
    text = f"""
🧠 {bold('ФРЕДИ: ТВОЯ ЦЕЛЬ')}

{user_name}, ты выбрал: {bold(goal_info.get('name', 'цель'))}
Режим: {bold(COMMUNICATION_MODES.get(mode, {}).get('name', 'КОУЧ'))}

👇 {bold('ТЕОРЕТИЧЕСКИЙ МАРШРУТ:')}

Чтобы достичь этой цели, в идеальном мире нужно:
{path['formatted_text']}

⚠️ Это в идеале. В реальности всё зависит от твоих условий.

👇 Хочешь проверить, насколько это реально для тебя?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data="check_reality"))
    keyboard.row(InlineKeyboardButton("🔄 ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.theoretical_path_shown)

def show_reality_check(call: CallbackQuery):
    """
    Запускает проверку реальности для выбранной цели
    """
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    
    # Проверяем, есть ли цель
    state_data = get_state_data(user_id)
    goal = state_data.get("current_destination")
    
    if not goal:
        text = f"""
🧠 {bold('ФРЕДИ: СНАЧАЛА ВЫБЕРИ ЦЕЛЬ')}

Чтобы проверить реальность, нужно знать, к чему мы стремимся.

👇 Сначала выбери цель:
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
        keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
        
        safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
        return
    
    # Проверяем, есть ли базовый контекст
    if not (context and context.life_context_complete):
        # Если нет — собираем
        start_life_context_collection(call, goal)
    else:
        # Если есть — задаём целевые вопросы
        ask_goal_specific_questions(call, goal)

def start_life_context_collection(call: CallbackQuery, goal: Dict):
    """
    Сбор базового контекста жизни (1 раз)
    """
    
    user_id = call.from_user.id
    user_name = user_names.get(user_id, "друг")
    
    questions = generate_life_context_questions()
    
    text = f"""
🧠 {bold('ФРЕДИ: ДАВАЙ ПОЗНАКОМИМСЯ С ТВОЕЙ РЕАЛЬНОСТЬЮ')}

{user_name}, чтобы понять, что потребуется для твоей цели "{bold(goal.get('name', 'цель'))}", мне нужно знать твои условия.

Это вопросы на 2 минуты. Ответь коротко (можно одним сообщением все сразу):

{questions}

👇 {bold('Напиши ответы одним сообщением или отправь голосовое сообщение 🎤')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (будет неточно)", callback_data="skip_life_context"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.collecting_life_context)
    update_state_data(user_id, pending_goal=goal)

def ask_goal_specific_questions(call: CallbackQuery, goal: Dict):
    """
    Задаёт вопросы, специфичные для цели
    """
    
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal_id = goal.get("id", "income_growth")
    goal_name = goal.get("name", "цель")
    mode = data.get("communication_mode", "coach")
    profile = data.get("profile_data", {})
    
    questions = generate_goal_context_questions(goal_id, profile, mode, goal_name)
    
    text = f"""
🧠 {bold('ФРЕДИ: УТОЧНЯЮ ПОД ТВОЮ ЦЕЛЬ')}

{user_name}, твоя цель: {bold(goal_name)}

Чтобы точно рассчитать маршрут с учётом твоих условий, ответь на несколько вопросов:

{questions}

👇 {bold('Напиши ответы (можно по порядку) или отправь голосовое сообщение 🎤')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("⏭ ПРОПУСТИТЬ (общий план)", callback_data="skip_goal_questions"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.collecting_goal_context)
    update_state_data(user_id, pending_goal=goal)

def process_life_context(message: types.Message):
    """Обрабатывает ответы на вопросы о жизненном контексте"""
    user_id = message.from_user.id
    text = message.text
    
    context = user_contexts.get(user_id)
    if not context:
        context = UserContext(user_id)
        user_contexts[user_id] = context
    
    try:
        parsed = parse_life_context_answers(text)
        
        # Заполняем контекст из распарсенных данных
        context.family_status = parsed.get('family_status', 'не указано')
        context.has_children = parsed.get('has_children', False)
        context.children_ages = parsed.get('children_info', '')
        context.work_schedule = parsed.get('work_schedule', '')
        context.job_title = parsed.get('job_title', '')
        context.commute_time = parsed.get('commute_time', '')
        context.housing_type = parsed.get('housing_type', '')
        context.has_private_space = parsed.get('has_private_space', False)
        context.has_car = parsed.get('has_car', False)
        context.support_people = parsed.get('support_people', '')
        context.resistance_people = parsed.get('resistance_people', '')
        context.energy_level = parsed.get('energy_level', 5)
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        lines = text.strip().split('\n')
        answers = []
        for line in lines:
            clean = re.sub(r'^[\d️⃣🔟]*\s*', '', line.strip())
            if clean:
                answers.append(clean)
    
    context.life_context_complete = True
    
    # Получаем сохранённую цель
    state_data = get_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    if goal:
        ask_goal_specific_questions(message, goal)
    else:
        show_main_menu_after_mode(message, context)

def process_goal_context(message: types.Message):
    """Обрабатывает ответы на вопросы о целевом контексте"""
    user_id = message.from_user.id
    text = message.text
    
    state_data = get_state_data(user_id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    try:
        goal_context = parse_goal_context_answers(text)
    except Exception as e:
        logger.error(f"Ошибка при парсинге целевого контекста: {e}")
        goal_context = {
            "raw_answers": text,
            "time_per_week": 5,
            "budget": 0
        }
        
        # Пробуем извлечь время
        time_match = re.search(r'(\d+)\s*часов', text, re.IGNORECASE)
        if time_match:
            goal_context["time_per_week"] = int(time_match.group(1))
        else:
            numbers = re.findall(r'\d+', text)
            if numbers and len(numbers) > 0:
                goal_context["time_per_week"] = int(numbers[0])
    
    update_state_data(user_id, goal_context=goal_context)
    
    calculate_and_show_feasibility(message, user_id)

def calculate_and_show_feasibility(message: types.Message, user_id: int):
    """
    Рассчитывает достижимость и показывает результат
    """
    
    state_data = get_state_data(user_id)
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal = state_data.get("current_destination") or state_data.get("pending_goal")
    goal_id = goal.get("id", "income_growth")
    mode = user_data.get(user_id, {}).get("communication_mode", "coach")
    
    # Получаем теоретический путь
    path = get_theoretical_path(goal_id, mode)
    
    # Собираем контекст
    life_context = {}
    if context:
        life_context = {
            "time_per_week": 0,
            "energy_level": context.energy_level or 5,
            "has_private_space": context.has_private_space or False,
            "support_people": context.support_people or None
        }
    
    goal_context = state_data.get("goal_context", {})
    profile = user_data.get(user_id, {}).get("profile_data", {})
    
    # Рассчитываем
    result = calculate_feasibility(path, life_context, goal_context, profile)
    
    # Сохраняем результат
    update_state_data(user_id, feasibility_result=result)
    
    text = f"""
🧠 {bold('ФРЕДИ: РЕАЛЬНОСТЬ ЦЕЛИ')}

{result['status']} {bold(result['status_text'])}

Твоя цель: {bold(goal.get('name', 'цель'))}

👇 {bold('ЧТО ПОТРЕБУЕТСЯ:')}
{result['requirements_text']}

👇 {bold('ЧТО У ТЕБЯ ЕСТЬ:')}
{result['available_text']}

📊 {bold('ДЕФИЦИТ РЕСУРСОВ:')} {result['deficit']}%

{result['recommendation']}

👇 {bold(f'Что делаем, {user_name}?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ПРИНЯТЬ ПЛАН", callback_data="accept_feasibility_plan"))
    keyboard.row(InlineKeyboardButton("🔄 ИЗМЕНИТЬ СРОК", callback_data="adjust_timeline"))
    keyboard.row(InlineKeyboardButton("📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)
    set_state(user_id, TestStates.feasibility_result)

def skip_life_context(call: CallbackQuery):
    """
    Пропускает сбор жизненного контекста
    """
    state_data = get_state_data(call.from_user.id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    text = f"""
🧠 {bold('ФРЕДИ: БУДЕТ НЕТОЧНО')}

Ок, пропускаем. Маршрут построю без учёта твоих условий — он будет общим.

Хочешь продолжить?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ДА, ПОКАЖИ ПЛАН", callback_data="skip_to_route"))
    keyboard.row(InlineKeyboardButton("🔄 ВСЁ-ТАКИ ОТВЕТИТЬ", callback_data="check_reality"))
    keyboard.row(InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)

def skip_goal_questions(call: CallbackQuery):
    """
    Пропускает целевые вопросы
    """
    state_data = get_state_data(call.from_user.id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    # Используем данные по умолчанию
    update_state_data(call.from_user.id, goal_context={"time_per_week": 5, "budget": 0})
    
    calculate_and_show_feasibility(call.message, call.from_user.id)

def skip_to_route(call: CallbackQuery):
    """
    Пропускает проверку и сразу строит маршрут
    """
    state_data = get_state_data(call.from_user.id)
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    if not goal:
        safe_send_message(call.message, "Цель не найдена", delete_previous=True)
        return
    
    safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: {bold(goal.get('name'))}...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Здесь должен быть вызов generate_route_ai
    # route = generate_route_ai(call.from_user.id, user_data.get(call.from_user.id, {}), goal)
    route = None  # Заглушка
    
    if route:
        update_state_data(call.from_user.id, current_route=route)
        show_route_step(call, 1, route)
    else:
        show_fallback_route(call, goal)

def accept_feasibility_plan(call: CallbackQuery):
    """
    Принимает план и переходит к построению маршрута
    """
    state_data = get_state_data(call.from_user.id)
    goal = state_data.get("current_destination")
    
    if not goal:
        safe_send_message(call.message, "Цель не найдена", delete_previous=True)
        return
    
    # Переходим к построению маршрута
    safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: {bold(goal.get('name'))}...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Здесь должен быть вызов generate_route_ai
    # route = generate_route_ai(call.from_user.id, user_data.get(call.from_user.id, {}), goal)
    route = None  # Заглушка
    
    if route:
        update_state_data(call.from_user.id, current_route=route)
        show_route_step(call, 1, route)
    else:
        show_fallback_route(call, goal)

def show_route_step(call: CallbackQuery, step: int, route: Dict):
    """Показывает текущий шаг маршрута"""
    
    state_data = get_state_data(call.from_user.id)
    data = user_data.get(call.from_user.id, {})
    destination = state_data.get("current_destination", {})
    mode = data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    route_text = route.get('full_text', 'Маршрут строится...')
    
    # Очищаем текст от Markdown
    route_text = re.sub(r'\*\*(.*?)\*\*', r'\1', route_text)
    route_text = re.sub(r'\*(.*?)\*', r'\1', route_text)
    route_text = re.sub(r'_(.*?)_', r'\1', route_text)
    route_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', route_text)
    
    text = f"""
{mode_config['emoji']} {bold('МАРШРУТ К ЦЕЛИ')}

🎯 {bold('Точка назначения:')} {destination['name']}
⏱ {bold('Ориентировочное время:')} {destination['time']}

{route_text}

👇 {bold('Отмечайте выполнение, когда готовы')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ВЫПОЛНИЛ ЭТАП", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    set_state(call.from_user.id, TestStates.route_active)

def show_fallback_route(call: CallbackQuery, destination: dict):
    """Резервный маршрут, если ИИ не отвечает"""
    
    data = user_data.get(call.from_user.id, {})
    mode = data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} {bold('МАРШРУТ К ЦЕЛИ')}

🎯 {bold('Точка назначения:')} {destination['name']}
⏱ {bold('Ориентировочное время:')} {destination['time']}

📍 {bold('ЭТАП 1: ДИАГНОСТИКА')}
   • {bold('Что делаем:')} анализируем текущую ситуацию
   • {bold('📝 Домашнее задание:')} записываем всё, что связано с целью
   • {bold('✅ Критерий:')} есть список наблюдений

📍 {bold('ЭТАП 2: ПЛАНИРОВАНИЕ')}
   • {bold('Что делаем:')} составляем пошаговый план
   • {bold('📝 Домашнее задание:')} разбиваем цель на микро-шаги
   • {bold('✅ Критерий:')} есть конкретный план

📍 {bold('ЭТАП 3: ДЕЙСТВИЕ')}
   • {bold('Что делаем:')} начинаем с первого микро-шага
   • {bold('📝 Домашнее задание:')} каждый день делать хотя бы одно действие
   • {bold('✅ Критерий:')} первый шаг сделан

👇 {bold('Начинаем?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ НАЧАТЬ", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    set_state(call.from_user.id, TestStates.route_active)

def route_step_done(call: CallbackQuery):
    """Отмечает выполнение этапа"""
    
    state_data = get_state_data(call.from_user.id)
    step = state_data.get("route_step", 1)
    route_progress = state_data.get("route_progress", [])
    
    route_progress.append(step)
    next_step = step + 1
    
    update_state_data(call.from_user.id,
        route_step=next_step,
        route_progress=route_progress
    )
    
    if next_step > 3:
        show_route_complete(call)
    else:
        safe_send_message(
            call.message,
            f"✅ {bold(f'Этап {step} выполнен!')}\n\nПереходим к этапу {next_step}...",
            delete_previous=True
        )
        time.sleep(1)
        
        route = state_data.get("current_route", {})
        show_route_step(call, next_step, route)

def show_route_complete(call: CallbackQuery):
    """Показывает завершение маршрута"""
    
    state_data = get_state_data(call.from_user.id)
    destination = state_data.get("current_destination", {})
    
    text = f"""
🎉 {bold('МАРШРУТ ЗАВЕРШЕН!')}

Поздравляю! Вы достигли цели: {bold(destination['name'])}

💪 {bold('ГОРДИТЕСЬ СОБОЙ')}

Хотите выбрать новую цель или закрепить результат?

👇 {bold('Выберите действие:')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🎯 НОВАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    update_state_data(call.from_user.id, route_step=None, current_destination=None)

# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    """Основной обработчик callback'ов"""
    
    data = call.data
    
    # Обработчики режимов
    if data == "show_modes":
        show_mode_selection(call.message)
    elif data.startswith("mode_"):
        mode = data.replace("mode_", "")
        context = user_contexts.get(call.from_user.id)
        if context:
            context.communication_mode = mode
        show_mode_selected(call.message, mode)
    
    # Обработчики навигации
    elif data == "back_to_mode_selected":
        state_data = get_state_data(call.from_user.id)
        mode = state_data.get("communication_mode", "coach")
        show_mode_selected(call.message, mode)
    elif data == "back_to_start":
        cmd_start(call.message)
    
    # Обработчики контекста
    elif data == "start_context":
        start_context(call.message)
    elif data == "set_gender_male":
        context = user_contexts.get(call.from_user.id)
        if context:
            context.gender = "male"
            question, keyboard = context.ask_for_context()
            if question:
                safe_send_message(
                    call.message,
                    f"📝 {bold('Давайте познакомимся')}\n\n{question}",
                    reply_markup=keyboard,
                    delete_previous=True
                )
    elif data == "set_gender_female":
        context = user_contexts.get(call.from_user.id)
        if context:
            context.gender = "female"
            question, keyboard = context.ask_for_context()
            if question:
                safe_send_message(
                    call.message,
                    f"📝 {bold('Давайте познакомимся')}\n\n{question}",
                    reply_markup=keyboard,
                    delete_previous=True
                )
    
    # Обработчики этапов
    elif data == "show_stage_1_intro":
        show_stage_1_intro(call.message)
    elif data == "start_stage_1":
        start_stage_1(call)
    elif data.startswith("stage1_"):
        handle_stage_1_answer(call)
    
    elif data == "show_stage_2_intro":
        show_stage_2_intro(call.message)
    elif data == "start_stage_2":
        start_stage_2(call)
    elif data.startswith("stage2_"):
        handle_stage_2_answer(call)
    
    elif data == "show_stage_3_intro":
        show_stage_3_intro(call.message)
    elif data == "start_stage_3":
        start_stage_3(call)
    elif data.startswith("stage3_"):
        handle_stage_3_answer(call)
    
    elif data == "show_stage_4_intro":
        show_stage_4_intro(call.message)
    elif data == "start_stage_4":
        start_stage_4(call)
    elif data.startswith("stage4_"):
        handle_stage_4_answer(call)
    
    elif data == "show_stage_5_intro":
        show_stage_5_intro(call.message)
    elif data == "start_stage_5":
        start_stage_5(call)
    elif data.startswith("stage5_"):
        handle_stage_5_answer(call)
    
    # Обработчики подтверждения профиля
    elif data == "profile_confirm":
        profile_confirm(call)
    elif data == "profile_doubt":
        profile_doubt(call)
    elif data == "profile_reject":
        profile_reject(call)
    elif data == "goodbye":
        handle_goodbye(call)
    
    # Обработчики расхождений
    elif data.startswith("discrepancy_"):
        disc = data.replace("discrepancy_", "")
        handle_discrepancy(call, disc)
    elif data == "clarify_next":
        clarify_next(call)
    elif data.startswith("clarify_answer_"):
        handle_clarifying_answer(call)
    
    # Обработчики результатов
    elif data == "show_results":
        show_final_profile(call.message, call.from_user.id)
    elif data == "psychologist_thought":
        show_ai_analysis(call)
    elif data == "smart_questions":
        show_smart_questions(call)
    
    # Обработчики целей
    elif data == "show_dynamic_destinations":
        show_dynamic_destinations(call)
    elif data.startswith("dynamic_dest_"):
        handle_dynamic_destination(call)
    
    # Обработчики проверки реальности
    elif data == "check_reality":
        show_reality_check(call)
    elif data == "skip_life_context":
        skip_life_context(call)
    elif data == "skip_goal_questions":
        skip_goal_questions(call)
    elif data == "skip_to_route":
        skip_to_route(call)
    elif data == "accept_feasibility_plan":
        accept_feasibility_plan(call)
    
    # Обработчики маршрутов
    elif data == "route_step_done":
        route_step_done(call)

def show_ai_analysis(call: CallbackQuery):
    """Показывает мысли психолога"""
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    if data.get("psychologist_thought"):
        show_saved_psychologist_thought(call.message, user_id, data["psychologist_thought"])
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        "🧠 Анализирую через конфайнмент-модель...\n\nЭто займёт около 15-20 секунд",
        delete_previous=True
    )
    
    # Здесь должен быть вызов generate_psychologist_thought
    # thought = generate_psychologist_thought(user_id, data)
    thought = None  # Заглушка
    
    if thought:
        user_data[user_id]["psychologist_thought"] = thought
        safe_delete_message(call.message.chat.id, status_msg.message_id)
        show_saved_psychologist_thought(call.message, user_id, thought)
    else:
        safe_delete_message(call.message.chat.id, status_msg.message_id)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("◀️ НАЗАД", callback_data="show_results"))
        safe_send_message(
            call.message,
            "❌ Не удалось сгенерировать анализ",
            reply_markup=keyboard,
            delete_previous=True
        )

def show_saved_psychologist_thought(message: types.Message, user_id: int, thought: str):
    """Показывает сохраненные мысли психолога с красивым форматированием"""
    
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else ""
    
    # Форматируем текст
    formatted_thought = format_psychologist_text(thought, user_name)
    
    # Добавляем заголовок, если его нет
    if not formatted_thought.startswith("🧠"):
        formatted_thought = f"🧠 {bold('МЫСЛИ ПСИХОЛОГА')}\n\n{formatted_thought}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("◀️ К ПОРТРЕТУ", callback_data="show_results"))
    
    safe_send_message(
        message,
        formatted_thought,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )

def show_smart_questions(call: CallbackQuery):
    """Показывает умные вопросы"""
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    context = user_contexts.get(user_id)
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    update_state_data(user_id, smart_questions=questions)
    
    mode = context.communication_mode if context else "coach"
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    if mode == "coach":
        header = f"{mode_config['emoji']} {bold('ЗАДАЙТЕ ВОПРОС (КОУЧ)')}\n\n{italic('Я буду задавать открытые вопросы, помогая вам найти ответы внутри себя.')}\n\n"
    elif mode == "psychologist":
        header = f"{mode_config['emoji']} {bold('РАССКАЖИТЕ МНЕ (ПСИХОЛОГ)')}\n\n{italic('Я здесь, чтобы помочь исследовать глубинные паттерны.')}\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} {bold('ПОСТАВЬТЕ ЗАДАЧУ (ТРЕНЕР)')}\n\n{italic('Чётко сформулируйте, что хотите решить. Я дам конкретные шаги.')}\n\n"
    else:
        header = f"❓ {bold('ЗАДАЙТЕ ВОПРОС')}\n\n"
    
    keyboard = InlineKeyboardMarkup()
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.add(InlineKeyboardButton(
            text=f"{q_short}",
            callback_data=f"ask_{i}"
        ))
    
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
    
    safe_send_message(
        call.message,
        header,
        reply_markup=keyboard,
        delete_previous=True
    )

def generate_smart_questions(scores):
    """Генерирует вопросы на основе профиля"""
    questions = []
    
    tf = level(scores.get("ТФ", 3))
    sb = level(scores.get("СБ", 3))
    ub = level(scores.get("УБ", 3))
    cv = level(scores.get("ЧВ", 3))
    
    if tf <= 2:
        questions.append("Как начать зарабатывать, если нет денег?")
        questions.append("Почему мне не везет с деньгами?")
    elif tf <= 4:
        questions.append("Как увеличить доход без новых вложений?")
        questions.append("Как создать финансовую подушку?")
    
    if sb <= 2:
        questions.append("Как перестать бояться конфликтов?")
        questions.append("Как научиться говорить 'нет'?")
    elif sb <= 4:
        questions.append("Почему я злюсь внутри, но молчу?")
        questions.append("Как защищать границы без агрессии?")
    
    if ub <= 2:
        questions.append("Как понять, что происходит в жизни?")
    elif ub == 4:
        questions.append("Как перестать искать заговоры?")
    
    if cv <= 2:
        questions.append("Как перестать зависеть от других?")
    elif cv <= 4:
        questions.append("Почему отношения поверхностные?")
    
    general = [
        "С чего начать изменения?",
        "Что мне делать с этой ситуацией?",
        "Как не срываться на близких?"
    ]
    
    while len(questions) < 5:
        for q in general:
            if q not in questions and len(questions) < 5:
                questions.append(q)
    
    return questions[:5]

# ============================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ============================================

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.awaiting_context)
def handle_context_message_wrapper(message: types.Message):
    """Обработчик сообщений в состоянии сбора контекста"""
    handle_context_message(message)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.collecting_life_context)
def handle_life_context_wrapper(message: types.Message):
    """Обработчик сообщений в состоянии сбора жизненного контекста"""
    process_life_context(message)

@bot.message_handler(func=lambda message: get_state(message.from_user.id) == TestStates.collecting_goal_context)
def handle_goal_context_wrapper(message: types.Message):
    """Обработчик сообщений в состоянии сбора целевого контекста"""
    process_goal_context(message)

@bot.message_handler(func=lambda message: True)
def handle_unknown_message(message: types.Message):
    """Обработчик неизвестных сообщений"""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results"))
    keyboard.row(InlineKeyboardButton("🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(
        message,
        "Используйте кнопки для навигации:",
        reply_markup=keyboard
    )

# ============================================
# ЗАПУСК БОТА
# ============================================

def main():
    """Главная функция"""
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v9.6 (MAX)")
    print("="*80)
    print(f"👤 Ваш ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("🎙 Распознавание: " + ("✅ Deepgram" if DEEPGRAM_API_KEY else "❌ нет"))
    print("🎙 Синтез речи: " + ("✅ Yandex" if YANDEX_API_KEY else "❌ нет"))
    print("🌍 Погода: " + ("✅ OpenWeather" if OPENWEATHER_API_KEY else "❌ нет"))
    print("🎭 Режимы: 🔮 КОУЧ | 🧠 ПСИХОЛОГ | ⚡ ТРЕНЕР")
    print("📊 5 этапов тестирования: ✅")
    print("🎯 Динамический подбор целей: ✅")
    print("🔍 Проверка реальности: ✅")
    print("="*80 + "\n")
    
    logger.info("🚀 Бот для MAX запущен!")
    bot.polling()

if __name__ == "__main__":
    os.makedirs("stats", exist_ok=True)
    main()
