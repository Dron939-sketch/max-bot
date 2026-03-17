#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики целей и маршрутов для MAX
"""

import logging
import time
from typing import Dict, Any, List, Optional

from bot_instance import bot
from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Наши модули
from config import COMMUNICATION_MODES, DESTINATIONS
from message_utils import safe_send_message
from keyboards import get_back_keyboard
from services import generate_route_ai
from reality_check import get_theoretical_path

# Импорты из state.py
from state import (
    user_data, user_contexts, user_state_data, user_states,
    get_state, set_state, get_state_data, update_state_data, TestStates, user_names
)

logger = logging.getLogger(__name__)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_user_data_dict(user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]

def get_user_state_data_dict(user_id: int) -> Dict[str, Any]:
    """Получает данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    return user_state_data[user_id]

def update_user_state_data(user_id: int, **kwargs):
    """Обновляет данные состояния пользователя"""
    if user_id not in user_state_data:
        user_state_data[user_id] = {}
    user_state_data[user_id].update(kwargs)

def get_user_context_obj(user_id: int):
    """Получает контекст пользователя"""
    return user_contexts.get(user_id)

def get_user_name(user_id: int) -> str:
    """Получает имя пользователя"""
    return user_names.get(user_id, "друг")

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ ДЛЯ ЦЕЛЕЙ
# ============================================

def show_goals_categories(message, user_id: int):
    """Показывает категории целей"""
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    text = f"""
🧠 <b>ФРЕДИ: КАТЕГОРИИ ЦЕЛЕЙ</b>

{user_name}, выбери категорию, которая сейчас актуальна.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

👇 <b>Куда двинемся?</b>
"""
    
    # Строим клавиатуру с основными категориями
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🗣 Отношения", callback_data="goal_cat_relations"),
        InlineKeyboardButton("💰 Деньги", callback_data="goal_cat_money")
    )
    keyboard.row(
        InlineKeyboardButton("🧠 Самоощущение", callback_data="goal_cat_self"),
        InlineKeyboardButton("📚 Развитие", callback_data="goal_cat_knowledge")
    )
    keyboard.row(
        InlineKeyboardButton("💪 Здоровье", callback_data="goal_cat_health"),
        InlineKeyboardButton("🎨 Творчество", callback_data="goal_cat_creative")
    )
    keyboard.row(
        InlineKeyboardButton("🎯 ДИНАМИЧЕСКИЙ ПОДБОР", callback_data="show_dynamic_destinations")
    )
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(message, text, reply_markup=keyboard, delete_previous=True)

def show_goals_for_category(call: CallbackQuery, category: str):
    """Показывает цели для выбранной категории"""
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data_dict.get("communication_mode", "coach")
    
    # Определяем цели для категории
    category_goals = {
        "relations": [
            {"id": "improve_relations", "name": "Улучшить отношения с близкими", "time": "4-6 недель", "difficulty": "medium", "description": "Построй гармоничные отношения с семьей и друзьями"},
            {"id": "find_partner", "name": "Найти партнёра", "time": "3-5 месяцев", "difficulty": "hard", "description": "Встретить человека для серьёзных отношений"},
            {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "description": "Освой искусство говорить 'нет'"}
        ],
        "money": [
            {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "description": "Создай стратегию для роста дохода"},
            {"id": "financial_plan", "name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy", "description": "Составь личный финансовый план"},
            {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "description": "Выяви и устрани препятствия"}
        ],
        "self": [
            {"id": "self_esteem", "name": "Повысить самооценку", "time": "4-5 недель", "difficulty": "medium", "description": "Научись ценить себя"},
            {"id": "anxiety", "name": "Справиться с тревогой", "time": "3-4 недели", "difficulty": "medium", "description": "Обрети внутреннее спокойствие"},
            {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "description": "Ответь на вопрос 'зачем я здесь?'"}
        ],
        "knowledge": [
            {"id": "new_skill", "name": "Освоить новый навык", "time": "4-6 недель", "difficulty": "medium", "description": "Научись чему-то новому"},
            {"id": "reading", "name": "Читать по книге в неделю", "time": "8 недель", "difficulty": "easy", "description": "Сформируй привычку читать"},
            {"id": "course", "name": "Пройти онлайн-курс", "time": "6-8 недель", "difficulty": "medium", "description": "Получи новые знания"}
        ],
        "health": [
            {"id": "sport", "name": "Начать заниматься спортом", "time": "4 недели", "difficulty": "medium", "description": "Внедри регулярные тренировки"},
            {"id": "sleep", "name": "Наладить сон", "time": "3-4 недели", "difficulty": "easy", "description": "Улучши качество сна"},
            {"id": "energy", "name": "Повысить уровень энергии", "time": "4 недели", "difficulty": "medium", "description": "Чувствуй себя бодрее"}
        ],
        "creative": [
            {"id": "start_creative", "name": "Начать творить", "time": "3-4 недели", "difficulty": "easy", "description": "Найди своё творческое выражение"},
            {"id": "overcome_block", "name": "Преодолеть творческий блок", "time": "2-3 недели", "difficulty": "medium", "description": "Верни вдохновение"},
            {"id": "project", "name": "Завершить творческий проект", "time": "6-8 недель", "difficulty": "hard", "description": "Доведи дело до конца"}
        ]
    }
    
    goals = category_goals.get(category, [])
    
    if not goals:
        safe_send_message(
            call.message,
            "❌ В этой категории пока нет целей",
            reply_markup=get_back_keyboard("show_goals"),
            delete_previous=True
        )
        return
    
    # Названия категорий
    category_names = {
        "relations": "🗣 Отношения",
        "money": "💰 Деньги",
        "self": "🧠 Самоощущение",
        "knowledge": "📚 Развитие",
        "health": "💪 Здоровье",
        "creative": "🎨 Творчество"
    }
    
    category_name = category_names.get(category, category)
    
    text = f"""
🧠 <b>{category_name}</b>

👇 <b>Выбери конкретную цель:</b>
"""
    
    # Строим клавиатуру с целями
    keyboard = InlineKeyboardMarkup()
    for goal in goals:
        # Определяем эмодзи сложности
        difficulty_emoji = {
            "easy": "🟢",
            "medium": "🟡", 
            "hard": "🔴"
        }.get(goal.get("difficulty", "medium"), "⚪")
        
        button_text = f"{difficulty_emoji} {goal['name']} ({goal['time']})"
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_goal_{goal['id']}"
        ))
    
    keyboard.add(InlineKeyboardButton(
        text="◀️ НАЗАД", 
        callback_data="show_goals"
    ))
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)

def select_goal(call: CallbackQuery, goal_id: str):
    """Выбирает конкретную цель и показывает её детали"""
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data_dict.get("communication_mode", "coach")
    
    # Ищем цель по ID во всех категориях
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        safe_send_message(
            call.message,
            "❌ Цель не найдена",
            reply_markup=get_back_keyboard("show_goals"),
            delete_previous=True
        )
        return
    
    # Сохраняем выбранную цель
    update_user_state_data(user_id, current_goal=goal_info)
    
    text = f"""
🧠 <b>ВЫБРАННАЯ ЦЕЛЬ</b>

{user_name}, ты выбрал: <b>{goal_info['name']}</b>

📊 <b>Сложность:</b> {goal_info.get('difficulty', 'medium')}
⏱ <b>Ориентировочное время:</b> {goal_info.get('time', 'не указано')}

{goal_info.get('description', '')}

👇 <b>Что дальше?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🚀 ПОСТРОИТЬ МАРШРУТ", callback_data=f"build_route_{goal_id}"),
        InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data=f"check_reality_{goal_id}")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_goals")
    )
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)

def find_goal_by_id(goal_id: str, mode: str) -> Optional[Dict]:
    """Ищет цель по ID во всех категориях"""
    # Сначала проверяем в динамических целях
    try:
        from config import DESTINATIONS
        destinations = DESTINATIONS.get(mode, DESTINATIONS["coach"])
        
        for category_key, category in destinations.items():
            if isinstance(category, dict) and "destinations" in category:
                for goal in category.get("destinations", []):
                    if goal.get("id") == goal_id:
                        if "description" not in goal:
                            goal["description"] = category.get("description", "")
                        return goal
    except:
        pass
    
    # Затем проверяем в статических категориях
    all_goals = {
        "improve_relations": {"name": "Улучшить отношения с близкими", "time": "4-6 недель", "difficulty": "medium", "description": "Построй гармоничные отношения с семьей и друзьями"},
        "find_partner": {"name": "Найти партнёра", "time": "3-5 месяцев", "difficulty": "hard", "description": "Встретить человека для серьёзных отношений"},
        "boundaries": {"name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "description": "Освой искусство говорить 'нет'"},
        "income_growth": {"name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "description": "Создай стратегию для роста дохода"},
        "financial_plan": {"name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy", "description": "Составь личный финансовый план"},
        "money_blocks": {"name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "description": "Выяви и устрани препятствия"},
        "self_esteem": {"name": "Повысить самооценку", "time": "4-5 недель", "difficulty": "medium", "description": "Научись ценить себя"},
        "anxiety": {"name": "Справиться с тревогой", "time": "3-4 недели", "difficulty": "medium", "description": "Обрети внутреннее спокойствие"},
        "purpose": {"name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "description": "Ответь на вопрос 'зачем я здесь?'"},
        "new_skill": {"name": "Освоить новый навык", "time": "4-6 недель", "difficulty": "medium", "description": "Научись чему-то новому"},
        "reading": {"name": "Читать по книге в неделю", "time": "8 недель", "difficulty": "easy", "description": "Сформируй привычку читать"},
        "course": {"name": "Пройти онлайн-курс", "time": "6-8 недель", "difficulty": "medium", "description": "Получи новые знания"},
        "sport": {"name": "Начать заниматься спортом", "time": "4 недели", "difficulty": "medium", "description": "Внедри регулярные тренировки"},
        "sleep": {"name": "Наладить сон", "time": "3-4 недели", "difficulty": "easy", "description": "Улучши качество сна"},
        "energy": {"name": "Повысить уровень энергии", "time": "4 недели", "difficulty": "medium", "description": "Чувствуй себя бодрее"},
        "start_creative": {"name": "Начать творить", "time": "3-4 недели", "difficulty": "easy", "description": "Найди своё творческое выражение"},
        "overcome_block": {"name": "Преодолеть творческий блок", "time": "2-3 недели", "difficulty": "medium", "description": "Верни вдохновение"},
        "project": {"name": "Завершить творческий проект", "time": "6-8 недель", "difficulty": "hard", "description": "Доведи дело до конца"}
    }
    
    return all_goals.get(goal_id)

# ============================================
# ДИНАМИЧЕСКИЙ ПОДБОР ЦЕЛЕЙ
# ============================================

def get_dynamic_destinations(profile_code: str, mode: str) -> List[Dict]:
    """Динамически подбирает цели под профиль и режим"""
    
    # Парсим профиль (СБ-4_ТФ-4_УБ-4_ЧВ-4)
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
                    {"id": "fear_work", "name": "Проработать страхи", "time": "3-4 недели", "difficulty": "medium", "description": "Исследуй свои страхи и научись с ними работать"},
                    {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "description": "Освой искусство говорить 'нет' и отстаивать свои интересы"},
                    {"id": "calm", "name": "Найти внутреннее спокойствие", "time": "3-5 недель", "difficulty": "hard", "description": "Обрети устойчивость в любой ситуации"}
                ],
                "ТФ": [
                    {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "description": "Выяви и устрани препятствия на пути к финансовому благополучию"},
                    {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "description": "Создай стратегию для роста дохода"},
                    {"id": "financial_plan", "name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy", "description": "Составь личный финансовый план"}
                ],
                "УБ": [
                    {"id": "meaning", "name": "Найти смысл и предназначение", "time": "4-6 недель", "difficulty": "hard", "description": "Ответь на вопрос 'зачем я здесь?'"},
                    {"id": "system_thinking", "name": "Развить системное мышление", "time": "3-5 недель", "difficulty": "medium", "description": "Научись видеть взаимосвязи и закономерности"},
                    {"id": "trust", "name": "Научиться доверять миру", "time": "3-4 недели", "difficulty": "medium", "description": "Откройся новому опыту"}
                ],
                "ЧВ": [
                    {"id": "relations", "name": "Улучшить отношения", "time": "4-6 недель", "difficulty": "hard", "description": "Построй гармоничные отношения с близкими"},
                    {"id": "boundaries_people", "name": "Выстроить границы с людьми", "time": "3-4 недели", "difficulty": "medium", "description": "Научись сохранять себя в общении"},
                    {"id": "attachment", "name": "Проработать тип привязанности", "time": "5-7 недель", "difficulty": "hard", "description": "Пойми свои паттерны в отношениях"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "leadership", "name": "Развить лидерские качества", "time": "4-6 недель", "difficulty": "medium", "description": "Стань лидером для себя и других"},
                    {"id": "stress_resistance", "name": "Усилить стрессоустойчивость", "time": "3-4 недели", "difficulty": "easy", "description": "Научись сохранять спокойствие в любой ситуации"}
                ],
                "ТФ": [
                    {"id": "business", "name": "Развить бизнес-мышление", "time": "5-7 недель", "difficulty": "hard", "description": "Мысли как предприниматель"},
                    {"id": "investments", "name": "Начать инвестировать", "time": "4-6 недель", "difficulty": "medium", "description": "Сделай первые шаги в инвестициях"}
                ],
                "УБ": [
                    {"id": "strategy", "name": "Развить стратегическое мышление", "time": "4-6 недель", "difficulty": "medium", "description": "Научись планировать на годы вперёд"},
                    {"id": "wisdom", "name": "Углубить понимание себя", "time": "3-5 недель", "difficulty": "easy", "description": "Познай свои глубинные мотивы"}
                ],
                "ЧВ": [
                    {"id": "empathy", "name": "Развить эмпатию", "time": "3-4 недели", "difficulty": "easy", "description": "Научись лучше понимать других"},
                    {"id": "community", "name": "Создать сообщество", "time": "6-8 недель", "difficulty": "hard", "description": "Объедини единомышленников"}
                ]
            },
            "general": [
                {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "description": "Ответь на главный вопрос жизни"},
                {"id": "balance", "name": "Обрести баланс", "time": "4-6 недель", "difficulty": "medium", "description": "Найди гармонию между работой и жизнью"},
                {"id": "growth", "name": "Личностный рост", "time": "6-8 недель", "difficulty": "medium", "description": "Стань лучшей версией себя"}
            ]
        },
        "psychologist": {
            "weak": {
                "СБ": [
                    {"id": "fear_origin", "name": "Найти источник страхов", "time": "4-6 недель", "difficulty": "hard", "description": "Исследуй происхождение своих страхов"},
                    {"id": "trauma", "name": "Проработать травму", "time": "6-8 недель", "difficulty": "hard", "description": "Исцели старые раны"},
                    {"id": "safety", "name": "Сформировать базовое чувство безопасности", "time": "5-7 недель", "difficulty": "hard", "description": "Обрети внутреннюю опору"}
                ],
                "ТФ": [
                    {"id": "money_psychology", "name": "Понять психологию денег", "time": "4-5 недель", "difficulty": "medium", "description": "Разберись в своих денежных сценариях"},
                    {"id": "worth", "name": "Проработать чувство собственной ценности", "time": "5-7 недель", "difficulty": "hard", "description": "Пойми, что ты достоин"},
                    {"id": "scarcity", "name": "Проработать сценарий дефицита", "time": "4-6 недель", "difficulty": "medium", "description": "Выйди из мышления нехватки"}
                ],
                "УБ": [
                    {"id": "core_beliefs", "name": "Найти глубинные убеждения", "time": "5-7 недель", "difficulty": "hard", "description": "Познай свои базовые установки"},
                    {"id": "schemas", "name": "Проработать жизненные сценарии", "time": "6-8 недель", "difficulty": "hard", "description": "Измени повторяющиеся паттерны"},
                    {"id": "meaning_deep", "name": "Экзистенциальный поиск", "time": "7-9 недель", "difficulty": "hard", "description": "Найди глубинный смысл"}
                ],
                "ЧВ": [
                    {"id": "attachment_style", "name": "Проработать тип привязанности", "time": "6-8 недель", "difficulty": "hard", "description": "Пойми свои паттерны в близости"},
                    {"id": "inner_child", "name": "Исцелить внутреннего ребёнка", "time": "5-7 недель", "difficulty": "hard", "description": "Позаботься о своей детской части"},
                    {"id": "family_system", "name": "Проработать семейную систему", "time": "6-8 недель", "difficulty": "hard", "description": "Исследуй родовые сценарии"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "resilience", "name": "Укрепить психологическую устойчивость", "time": "4-6 недель", "difficulty": "medium", "description": "Стань устойчивее к стрессу"},
                    {"id": "protection", "name": "Трансформировать защитные механизмы", "time": "5-7 недель", "difficulty": "hard", "description": "Осознай и измени свои защиты"}
                ],
                "ТФ": [
                    {"id": "abundance", "name": "Сформировать мышление изобилия", "time": "5-7 недель", "difficulty": "hard", "description": "Перейди от дефицита к изобилию"},
                    {"id": "money_freedom", "name": "Обрести финансовую свободу", "time": "6-8 недель", "difficulty": "hard", "description": "Освободись от денежных страхов"}
                ],
                "УБ": [
                    {"id": "wisdom_deep", "name": "Углубить мудрость", "time": "5-7 недель", "difficulty": "medium", "description": "Развивай глубинное понимание"},
                    {"id": "integration", "name": "Интегрировать тени", "time": "6-8 недель", "difficulty": "hard", "description": "Прими свои теневые стороны"}
                ],
                "ЧВ": [
                    {"id": "intimacy", "name": "Научиться близости", "time": "5-7 недель", "difficulty": "hard", "description": "Построй глубокие связи"},
                    {"id": "love", "name": "Проработать способность любить", "time": "6-8 недель", "difficulty": "hard", "description": "Раскрой своё сердце"}
                ]
            },
            "general": [
                {"id": "self_discovery", "name": "Глубинное самопознание", "time": "7-9 недель", "difficulty": "hard", "description": "Познай себя настоящего"},
                {"id": "healing", "name": "Исцеление внутренних ран", "time": "8-10 недель", "difficulty": "hard", "description": "Исцели то, что болит внутри"},
                {"id": "integration_deep", "name": "Интеграция личности", "time": "9-12 недель", "difficulty": "hard", "description": "Объедини все части себя"}
            ]
        },
        "trainer": {
            "weak": {
                "СБ": [
                    {"id": "assertiveness", "name": "Развить ассертивность", "time": "3-4 недели", "difficulty": "medium", "description": "Научись уверенно отстаивать свои интересы"},
                    {"id": "conflict_skills", "name": "Освоить навыки конфликта", "time": "4-5 недель", "difficulty": "medium", "description": "Научись выходить из конфликтов с пользой"},
                    {"id": "courage", "name": "Тренировка смелости", "time": "3-5 недель", "difficulty": "hard", "description": "Развивай смелость каждый день"}
                ],
                "ТФ": [
                    {"id": "money_skills", "name": "Освоить навыки управления деньгами", "time": "3-4 недели", "difficulty": "easy", "description": "Научись управлять личными финансами"},
                    {"id": "income_skills", "name": "Навыки увеличения дохода", "time": "4-6 недель", "difficulty": "medium", "description": "Освой практические инструменты для роста дохода"},
                    {"id": "investment_skills", "name": "Навыки инвестирования", "time": "5-7 недель", "difficulty": "hard", "description": "Научись инвестировать с умом"}
                ],
                "УБ": [
                    {"id": "thinking_tools", "name": "Освоить инструменты мышления", "time": "4-5 недель", "difficulty": "medium", "description": "Изучи практические техники мышления"},
                    {"id": "triz", "name": "Научиться ТРИЗ", "time": "5-7 недель", "difficulty": "hard", "description": "Освой теорию решения изобретательских задач"},
                    {"id": "decision_making", "name": "Навыки принятия решений", "time": "3-4 недели", "difficulty": "easy", "description": "Научись быстро принимать решения"}
                ],
                "ЧВ": [
                    {"id": "communication_skills", "name": "Развить навыки общения", "time": "3-4 недели", "difficulty": "easy", "description": "Улучши свои коммуникативные навыки"},
                    {"id": "negotiation", "name": "Навыки переговоров", "time": "4-6 недель", "difficulty": "medium", "description": "Освой искусство переговоров"},
                    {"id": "influence", "name": "Навыки влияния", "time": "5-7 недель", "difficulty": "hard", "description": "Научись влиять на людей"}
                ]
            },
            "strong": {
                "СБ": [
                    {"id": "leader_courage", "name": "Лидерская смелость", "time": "4-6 недель", "difficulty": "medium", "description": "Развивай смелость лидера"},
                    {"id": "crisis_management", "name": "Управление в кризисах", "time": "5-7 недель", "difficulty": "hard", "description": "Научись действовать в кризисных ситуациях"}
                ],
                "ТФ": [
                    {"id": "wealth_building", "name": "Навыки создания капитала", "time": "6-8 недель", "difficulty": "hard", "description": "Научись создавать и сохранять капитал"},
                    {"id": "financial_strategy", "name": "Финансовая стратегия", "time": "5-7 недель", "difficulty": "hard", "description": "Разработай долгосрочную финансовую стратегию"}
                ],
                "УБ": [
                    {"id": "system_analysis", "name": "Системный анализ", "time": "5-7 недель", "difficulty": "hard", "description": "Научись анализировать сложные системы"},
                    {"id": "strategic_thinking", "name": "Стратегическое мышление", "time": "6-8 недель", "difficulty": "hard", "description": "Развивай стратегическое мышление"}
                ],
                "ЧВ": [
                    {"id": "team_building", "name": "Построение команды", "time": "5-7 недель", "difficulty": "hard", "description": "Научись строить эффективные команды"},
                    {"id": "leadership", "name": "Лидерские навыки", "time": "6-8 недель", "difficulty": "hard", "description": "Развивай лидерские качества"}
                ]
            },
            "general": [
                {"id": "productivity", "name": "Повысить продуктивность", "time": "4-6 недель", "difficulty": "medium", "description": "Делай больше за меньшее время"},
                {"id": "habit_building", "name": "Сформировать полезные привычки", "time": "3-5 недель", "difficulty": "easy", "description": "Внедри привычки, которые меняют жизнь"},
                {"id": "skill_mastery", "name": "Мастерство в ключевых навыках", "time": "8-10 недель", "difficulty": "hard", "description": "Стань мастером в своём деле"}
            ]
        }
    }
    
    mode_db = destinations_db.get(mode, destinations_db["coach"])
    
    # Собираем цели
    destinations = []
    
    # Цели для слабого вектора
    if "weak" in mode_db and weakest[0] in mode_db["weak"]:
        destinations.extend(mode_db["weak"][weakest[0]])
    
    # Цели для сильного вектора (развитие силы)
    if "strong" in mode_db and strongest[0] in mode_db["strong"]:
        destinations.extend(mode_db["strong"][strongest[0]])
    
    # Добавляем общие цели
    if "general" in mode_db:
        destinations.extend(mode_db["general"])
    
    # Убираем дубликаты по id
    seen = set()
    unique_destinations = []
    for dest in destinations:
        if dest["id"] not in seen:
            seen.add(dest["id"])
            unique_destinations.append(dest)
    
    return unique_destinations[:9]  # Не больше 9 целей

def show_dynamic_destinations(call: CallbackQuery):
    """Показывает динамически подобранные цели"""
    
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем динамические цели
    destinations = get_dynamic_destinations(profile_code, mode)
    
    text = f"""
🧠 <b>ФРЕДИ: ЦЕЛИ ПО ТВОЕМУ ПРОФИЛЮ</b>

{user_name}, я проанализировал твой профиль и подобрал цели, которые сейчас наиболее актуальны.

<b>Твой профиль:</b> {profile_code}
<b>Режим:</b> {mode_config['emoji']} {mode_config['name']}

👇 <b>Куда двинемся?</b>
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
        parse_mode='HTML',
        delete_previous=True
    )
    set_state(user_id, TestStates.destination_selection)

def handle_dynamic_destination(call: CallbackQuery):
    """Обрабатывает выбор динамической цели"""
    
    dest_id = call.data.replace("dynamic_dest_", "")
    
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    mode = user_data_dict.get("communication_mode", "coach")
    profile_code = user_data_dict.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    # Получаем все цели
    all_destinations = get_dynamic_destinations(profile_code, mode)
    
    # Находим выбранную
    dest_info = None
    for dest in all_destinations:
        if dest["id"] == dest_id:
            dest_info = dest
            break
    
    if not dest_info:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Сохраняем выбранную цель
    update_user_state_data(user_id,
        current_destination=dest_info,
        route_step=1,
        route_progress=[]
    )
    
    # Показываем теоретический путь
    show_theoretical_path(call, dest_info)

def custom_destination(call: CallbackQuery):
    """Пользователь хочет сформулировать цель самостоятельно"""
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    text = f"""
🧠 <b>ФРЕДИ: СФОРМУЛИРУЙ ЦЕЛЬ</b>

{user_name}, расскажи своими словами, чего ты хочешь достичь.

Напиши мне сообщение с описанием цели, и я помогу построить маршрут.

👇 <b>Напиши свою цель:</b>
"""
    
    keyboard = get_back_keyboard("show_dynamic_destinations")
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)
    
    # Устанавливаем состояние ожидания цели
    set_state(user_id, "awaiting_custom_goal")

# ============================================
# МАРШРУТЫ К ЦЕЛЯМ
# ============================================

def show_theoretical_path(call: CallbackQuery, goal_info: Dict):
    """
    Показывает теоретический путь к цели после её выбора
    """
    
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    goal_id = goal_info.get("id", "income_growth")
    mode = user_data_dict.get("communication_mode", "coach")
    
    # Получаем теоретический путь
    path = get_theoretical_path(goal_id, mode)
    
    # Сохраняем путь в состоянии
    update_user_state_data(user_id, theoretical_path=path)
    
    text = f"""
🧠 <b>ФРЕДИ: ТВОЯ ЦЕЛЬ</b>

{user_name}, ты выбрал: <b>{goal_info.get('name', 'цель')}</b>
Режим: <b>{COMMUNICATION_MODES.get(mode, {}).get('name', 'КОУЧ')}</b>

👇 <b>ТЕОРЕТИЧЕСКИЙ МАРШРУТ:</b>

Чтобы достичь этой цели, в идеальном мире нужно:
{path['formatted_text']}

⚠️ Это в идеале. В реальности всё зависит от твоих условий.

👇 Хочешь проверить, насколько это реально для тебя?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data="check_reality"))
    keyboard.row(InlineKeyboardButton("🔄 ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.row(InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.theoretical_path_shown)

def build_route(call: CallbackQuery, goal_id: str):
    """Строит маршрут к цели (после проверки реальности или сразу)"""
    user_id = call.from_user.id
    state_data = get_user_state_data_dict(user_id)
    user_data_dict = get_user_data_dict(user_id)
    
    # Получаем информацию о цели
    mode = user_data_dict.get("communication_mode", "coach")
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        goal_info = state_data.get("current_destination")
    
    if not goal_info:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    # Отправляем статусное сообщение
    status_msg = safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: <b>{goal_info.get('name')}</b>...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    # Генерируем маршрут через ИИ
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если цикл уже запущен, создаем задачу
            future = asyncio.run_coroutine_threadsafe(
                generate_route_ai(user_id, user_data_dict, goal_info), loop
            )
            route = future.result(timeout=30)
        else:
            route = loop.run_until_complete(generate_route_ai(user_id, user_data_dict, goal_info))
    except RuntimeError:
        route = asyncio.run(generate_route_ai(user_id, user_data_dict, goal_info))
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации маршрута: {e}")
        route = None
    
    if route:
        update_user_state_data(user_id, current_route=route)
        show_route_step(call, 1, route, status_msg)
    else:
        # Если ИИ не сработал, показываем резервный маршрут
        show_fallback_route(call, goal_info, status_msg)

def show_route_step(call: CallbackQuery, step: int, route: Dict, status_msg=None):
    """Показывает текущий шаг маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data_dict(user_id)
    user_data_dict = get_user_data_dict(user_id)
    
    destination = state_data.get("current_destination", {})
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    route_text = route.get('full_text', 'Маршрут строится...')
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

🎯 <b>Точка назначения:</b> {destination.get('name', 'цель')}
⏱ <b>Ориентировочное время:</b> {destination.get('time', 'не указано')}

{route_text}

👇 <b>Отмечай выполнение, когда готов(а)</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ ВЫПОЛНИЛ ЭТАП", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    set_state(user_id, TestStates.route_active)

def show_fallback_route(call: CallbackQuery, destination: dict, status_msg=None):
    """Резервный маршрут, если ИИ не отвечает"""
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

🎯 <b>Точка назначения:</b> {destination.get('name', 'цель')}
⏱ <b>Ориентировочное время:</b> {destination.get('time', 'не указано')}

📍 <b>ЭТАП 1: ДИАГНОСТИКА</b>
   • <b>Что делаем:</b> анализируем текущую ситуацию
   • <b>📝 Домашнее задание:</b> записываем всё, что связано с целью
   • <b>✅ Критерий:</b> есть список наблюдений

📍 <b>ЭТАП 2: ПЛАНИРОВАНИЕ</b>
   • <b>Что делаем:</b> составляем пошаговый план
   • <b>📝 Домашнее задание:</b> разбиваем цель на микро-шаги
   • <b>✅ Критерий:</b> есть конкретный план

📍 <b>ЭТАП 3: ДЕЙСТВИЕ</b>
   • <b>Что делаем:</b> начинаем с первого микро-шага
   • <b>📝 Домашнее задание:</b> каждый день делать хотя бы одно действие
   • <b>✅ Критерий:</b> первый шаг сделан

👇 <b>Начинаем?</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("✅ НАЧАТЬ", callback_data="route_step_done"))
    keyboard.row(InlineKeyboardButton("◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            from message_utils import safe_delete_message
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except:
            pass
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.route_active)

def route_step_done(call: CallbackQuery):
    """Отмечает выполнение этапа маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data_dict(user_id)
    
    step = state_data.get("route_step", 1)
    route_progress = state_data.get("route_progress", [])
    
    route_progress.append(step)
    next_step = step + 1
    
    update_user_state_data(user_id,
        route_step=next_step,
        route_progress=route_progress
    )
    
    if next_step > 3:
        complete_route(call)
    else:
        safe_send_message(
            call.message,
            f"✅ <b>Этап {step} выполнен!</b>\n\nПереходим к этапу {next_step}...",
            parse_mode='HTML',
            delete_previous=True
        )
        time.sleep(1)
        
        route = state_data.get("current_route", {})
        show_route_step(call, next_step, route, None)

def complete_route(call: CallbackQuery):
    """Показывает завершение маршрута"""
    user_id = call.from_user.id
    state_data = get_user_state_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = context.name if context and context.name else "друг"
    
    destination = state_data.get("current_destination", {})
    
    text = f"""
🎉 <b>МАРШРУТ ЗАВЕРШЕН!</b>

Поздравляю, {user_name}! Ты достиг цели: <b>{destination.get('name', 'цель')}</b>

💪 <b>ГОРДИСЬ СОБОЙ!</b>

Хочешь выбрать новую цель или закрепить результат?

👇 <b>Выбери действие:</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🎯 НОВАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"),
        InlineKeyboardButton("🧠 К ПОРТРЕТУ", callback_data="show_results")
    )
    keyboard.row(InlineKeyboardButton("❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    # Очищаем данные маршрута
    update_user_state_data(user_id, route_step=None, current_destination=None, current_route=None)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'show_goals_categories',
    'show_goals_for_category',
    'select_goal',
    'show_dynamic_destinations',
    'handle_dynamic_destination',
    'custom_destination',
    'build_route',
    'show_route_step',
    'show_fallback_route',
    'route_step_done',
    'complete_route'
]
