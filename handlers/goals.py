#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики целей и маршрутов для MAX
Версия 2.4 - ИСПРАВЛЕНО: замена db на синхронные функции
"""

import logging
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional

from maxibot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Наши модули
from config import COMMUNICATION_MODES
from message_utils import safe_send_message, safe_delete_message
from keyboards import get_back_keyboard, get_main_menu_after_mode_keyboard
from services import generate_route_ai
from reality_check import (
    get_theoretical_path,
    generate_life_context_questions,
    generate_goal_context_questions,
    calculate_feasibility,
    parse_life_context_answers,
    parse_goal_context_answers
)

# Импорты из state.py
from state import (
    user_data, user_contexts, user_state_data, user_states, user_routes,
    get_state, set_state, get_state_data, update_state_data, 
    TestStates, user_names, clear_state
)

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
    get_stats
)

# Импорты из formatters.py
from formatters import bold, italic, clean_text_for_safe_display

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
# ✅ ИСПРАВЛЕНО: СИНХРОННЫЕ ФУНКЦИИ ДЛЯ БД
# ============================================

def save_goal_to_db_sync(user_id: int, goal_data: Dict[str, Any], status: str = "selected"):
    """Синхронно сохраняет выбранную цель в БД"""
    try:
        log_event(
            user_id,
            'goal_selected',
            {
                'goal_id': goal_data.get('id'),
                'goal_name': goal_data.get('name'),
                'goal_time': goal_data.get('time'),
                'goal_difficulty': goal_data.get('difficulty'),
                'status': status,
                'timestamp': time.time()
            }
        )
        logger.debug(f"💾 Цель {goal_data.get('id')} для {user_id} сохранена в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения цели для {user_id}: {e}")

def save_route_to_db_sync(user_id: int, route_data: Dict[str, Any], goal_data: Dict[str, Any]):
    """Синхронно сохраняет маршрут в БД"""
    try:
        # Сохраняем в user_routes
        user_routes[user_id] = {
            'route_data': route_data,
            'goal': goal_data,
            'current_step': 1,
            'progress': [],
            'started_at': time.time()
        }
        
        # Логируем событие
        log_event(
            user_id,
            'route_started',
            {
                'goal_id': goal_data.get('id'),
                'goal_name': goal_data.get('name'),
                'timestamp': time.time()
            }
        )
        logger.debug(f"💾 Маршрут для {user_id} сохранен в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения маршрута для {user_id}: {e}")

def update_route_progress_in_db_sync(user_id: int, step: int, progress: List[int]):
    """Синхронно обновляет прогресс по маршруту в БД"""
    try:
        log_event(
            user_id,
            'route_step_completed',
            {
                'step': step,
                'progress': progress,
                'timestamp': time.time()
            }
        )
    except Exception as e:
        logger.error(f"❌ Ошибка обновления прогресса маршрута для {user_id}: {e}")

def save_feasibility_result_to_db_sync(user_id: int, goal_data: Dict[str, Any], result: Dict[str, Any]):
    """Синхронно сохраняет результат проверки реальности в БД"""
    try:
        log_event(
            user_id,
            'feasibility_checked',
            {
                'goal_id': goal_data.get('id'),
                'goal_name': goal_data.get('name'),
                'deficit': result.get('deficit'),
                'status': result.get('status_text'),
                'timestamp': time.time()
            }
        )
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результата проверки для {user_id}: {e}")


# ============================================
# КАТЕГОРИИ ЦЕЛЕЙ (для обратной совместимости)
# ============================================

def show_goals_categories(message, user_id: int):
    """Показывает категории целей"""
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
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


def show_goals_for_category(call, category: str):
    """Показывает цели для выбранной категории"""
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    mode = user_data_dict.get("communication_mode", "coach")
    
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
    
    keyboard = InlineKeyboardMarkup()
    for goal in goals:
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


def select_goal(call, goal_id: str):
    """Выбирает конкретную цель и показывает её детали"""
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    mode = user_data_dict.get("communication_mode", "coach")
    
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        safe_send_message(
            call.message,
            "❌ Цель не найдена",
            reply_markup=get_back_keyboard("show_goals"),
            delete_previous=True
        )
        return
    
    update_user_state_data(user_id, current_goal=goal_info)
    
    # ✅ ИСПРАВЛЕНО: синхронное сохранение в фоне
    run_sync_in_background(save_goal_to_db_sync, user_id, goal_info, "selected")
    
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
        InlineKeyboardButton("🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data=f"check_reality")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_goals")
    )
    
    safe_send_message(call.message, text, reply_markup=keyboard, delete_previous=True)


# ============================================
# ДИНАМИЧЕСКИЙ ПОДБОР ЦЕЛЕЙ
# ============================================

async def get_dynamic_destinations(profile_code: str, mode: str) -> List[Dict]:
    """Динамически подбирает цели под профиль и режим"""
    
    parts = profile_code.split('_')
    scores = {}
    for part in parts:
        if '-' in part:
            vec, val = part.split('-')
            scores[vec] = int(val)
    
    if not scores:
        scores = {"СБ": 4, "ТФ": 4, "УБ": 4, "ЧВ": 4}
    
    sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
    weakest = sorted_vectors[0] if sorted_vectors else ("СБ", 4)
    strongest = sorted_vectors[-1] if sorted_vectors else ("ЧВ", 4)
    
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
    
    destinations = []
    
    if "weak" in mode_db and weakest[0] in mode_db["weak"]:
        destinations.extend(mode_db["weak"][weakest[0]])
    
    if "strong" in mode_db and strongest[0] in mode_db["strong"]:
        destinations.extend(mode_db["strong"][strongest[0]])
    
    if "general" in mode_db:
        destinations.extend(mode_db["general"])
    
    seen = set()
    unique_destinations = []
    for dest in destinations:
        if dest["id"] not in seen:
            seen.add(dest["id"])
            unique_destinations.append(dest)
    
    return unique_destinations[:9]


async def show_dynamic_destinations(call: CallbackQuery, state_data: Dict):
    """Показывает динамически подобранные цели"""
    
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    mode = user_data_dict.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = user_data_dict.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    destinations = await get_dynamic_destinations(profile_code, mode)
    
    text = f"""
🧠 {bold('ФРЕДИ: ЦЕЛИ ПО ТВОЕМУ ПРОФИЛЮ')}

{user_name}, я проанализировал твой профиль и подобрал цели, которые сейчас наиболее актуальны.

{bold('Твой профиль:')} {profile_code}
{bold('Режим:')} {mode_config['emoji']} {mode_config['name']}

👇 {bold('Куда двинемся?')}
"""
    
    keyboard = InlineKeyboardMarkup()
    
    for dest in destinations:
        difficulty_emoji = {
            "easy": "🟢",
            "medium": "🟡",
            "hard": "🔴"
        }.get(dest.get("difficulty", "medium"), "⚪")
        
        button_text = f"{difficulty_emoji} {dest['name']}"
        keyboard.add(InlineKeyboardButton(text=button_text, callback_data=f"dynamic_dest_{dest['id']}"))
    
    keyboard.add(InlineKeyboardButton(text="✏️ Сформулирую сам", callback_data="custom_destination"))
    keyboard.add(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.destination_selection)


async def show_theoretical_path(call: CallbackQuery, state_data: Dict, goal_info: Dict):
    """Показывает теоретический путь к цели после её выбора"""
    
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    goal_id = goal_info.get("id", "income_growth")
    mode = state_data.get("communication_mode", "coach")
    
    path = get_theoretical_path(goal_id, mode)
    
    update_user_state_data(user_id, theoretical_path=path, current_destination=goal_info)
    
    run_sync_in_background(save_goal_to_db_sync, user_id, goal_info, "in_progress")
    
    path_text = path.get('formatted_text', 'Маршрут строится...')
    
    text = f"""
🧠 {bold('ФРЕДИ: ТВОЯ ЦЕЛЬ')}

{user_name}, ты выбрал: {bold(goal_info.get('name', 'цель'))}
Режим: {bold(COMMUNICATION_MODES.get(mode, {}).get('name', 'КОУЧ'))}

👇 {bold('ТЕОРЕТИЧЕСКИЙ МАРШРУТ:')}

Чтобы достичь этой цели, в идеальном мире нужно:
{path_text}

⚠️ Это в идеале. В реальности всё зависит от твоих условий.

👇 Хочешь проверить, насколько это реально для тебя?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="🔍 ПРОВЕРИТЬ РЕАЛЬНОСТЬ", callback_data="check_reality"))
    keyboard.add(InlineKeyboardButton(text="🔄 ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.add(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_mode_selected"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.theoretical_path_shown)


async def handle_dynamic_destination(call: CallbackQuery, state_data: Dict):
    """Обрабатывает выбор динамической цели"""
    
    dest_id = call.data.replace("dynamic_dest_", "")
    
    user_id = call.from_user.id
    user_data_dict = get_user_data_dict(user_id)
    mode = user_data_dict.get("communication_mode", "coach")
    profile_code = user_data_dict.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    all_destinations = await get_dynamic_destinations(profile_code, mode)
    
    dest_info = None
    for dest in all_destinations:
        if dest["id"] == dest_id:
            dest_info = dest
            break
    
    if not dest_info:
        await call.answer("❌ Цель не найдена")
        return
    
    await show_theoretical_path(call, state_data, dest_info)


async def custom_destination(call: CallbackQuery, state_data: Dict):
    """Пользователь хочет сформулировать цель самостоятельно"""
    user_id = call.from_user.id
    user_name = get_user_name(user_id)
    
    text = f"""
🧠 {bold('ФРЕДИ: СФОРМУЛИРУЙ ЦЕЛЬ')}

{user_name}, расскажи своими словами, чего ты хочешь достичь.

Напиши мне сообщение с описанием цели, и я помогу построить маршрут.

👇 {bold('Напиши свою цель:')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    
    set_state(user_id, "awaiting_custom_goal")


# ============================================
# ПРОВЕРКА РЕАЛЬНОСТИ
# ============================================

async def show_reality_check(call: CallbackQuery, state_data: Dict):
    """Запускает проверку реальности для выбранной цели"""
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    
    goal = state_data.get("current_destination")
    if not goal:
        text = f"""
🧠 {bold('ФРЕДИ: СНАЧАЛА ВЫБЕРИ ЦЕЛЬ')}

Чтобы проверить реальность, нужно знать, к чему мы стремимся.

👇 Сначала выбери цель:
"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
        keyboard.add(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_mode_selected"))
        
        safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
        return
    
    if not (context and getattr(context, 'life_context_complete', False)):
        await start_life_context_collection(call, state_data, goal)
    else:
        await ask_goal_specific_questions(call, state_data, goal)


async def start_life_context_collection(call: CallbackQuery, state_data: Dict, goal: Dict):
    """Сбор базового контекста жизни (1 раз)"""
    
    user_id = call.from_user.id
    user_name = get_user_name(user_id)
    
    questions = generate_life_context_questions()
    
    text = f"""
🧠 {bold('ФРЕДИ: ДАВАЙ ПОЗНАКОМИМСЯ С ТВОЕЙ РЕАЛЬНОСТЬЮ')}

{user_name}, чтобы понять, что потребуется для твоей цели "{bold(goal.get('name', 'цель'))}", мне нужно знать твои условия.

Это вопросы на 2 минуты. Ответь коротко (можно одним сообщением все сразу):

{questions}

👇 {bold('Напиши ответы одним сообщением или отправь голосовое сообщение 🎤')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="⏭ ПРОПУСТИТЬ (будет неточно)", callback_data="skip_life_context"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.collecting_life_context)
    update_user_state_data(user_id, pending_goal=goal)


async def ask_goal_specific_questions(call: CallbackQuery, state_data: Dict, goal: Dict):
    """Задаёт вопросы, специфичные для цели"""
    
    user_id = call.from_user.id
    context = get_user_context_obj(user_id)
    user_name = get_user_name(user_id)
    
    goal_id = goal.get("id", "income_growth")
    goal_name = goal.get("name", "цель")
    mode = state_data.get("communication_mode", "coach")
    profile = state_data.get("profile_data", {})
    
    questions = generate_goal_context_questions(goal_id, profile, mode, goal_name)
    
    text = f"""
🧠 {bold('ФРЕДИ: УТОЧНЯЮ ПОД ТВОЮ ЦЕЛЬ')}

{user_name}, твоя цель: {bold(goal_name)}

Чтобы точно рассчитать маршрут с учётом твоих условий, ответь на несколько вопросов:

{questions}

👇 {bold('Напиши ответы (можно по порядку) или отправь голосовое сообщение 🎤')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="⏭ ПРОПУСТИТЬ (общий план)", callback_data="skip_goal_questions"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(user_id, TestStates.collecting_goal_context)
    update_user_state_data(user_id, pending_goal=goal)


async def calculate_and_show_feasibility(call: CallbackQuery, state_data: Dict):
    """Рассчитывает достижимость и показывает результат"""
    
    context = get_user_context_obj(call.from_user.id)
    user_name = get_user_name(call.from_user.id)
    
    goal = state_data.get("current_destination") or state_data.get("pending_goal")
    if not goal:
        await call.answer("❌ Цель не найдена")
        return
    
    goal_id = goal.get("id", "income_growth")
    mode = state_data.get("communication_mode", "coach")
    
    path = get_theoretical_path(goal_id, mode)
    
    life_context = {}
    if context:
        life_context = {
            "time_per_week": 0,
            "energy_level": getattr(context, 'energy_level', 5),
            "has_private_space": getattr(context, 'has_private_space', False),
            "support_people": getattr(context, 'support_people', None)
        }
    
    goal_context = state_data.get("goal_context", {})
    profile = state_data.get("profile_data", {})
    
    result = calculate_feasibility(path, life_context, goal_context, profile)
    
    update_user_state_data(call.from_user.id, feasibility_result=result)
    
    run_sync_in_background(save_feasibility_result_to_db_sync, call.from_user.id, goal, result)
    
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
    keyboard.add(InlineKeyboardButton(text="✅ ПРИНЯТЬ ПЛАН", callback_data="accept_feasibility_plan"))
    keyboard.add(InlineKeyboardButton(text="🔄 ИЗМЕНИТЬ СРОК", callback_data="adjust_timeline"))
    keyboard.add(InlineKeyboardButton(text="📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    keyboard.add(InlineKeyboardButton(text="◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)
    set_state(call.from_user.id, TestStates.feasibility_result)


async def skip_life_context(call: CallbackQuery, state_data: Dict):
    """Пропускает сбор жизненного контекста"""
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    text = f"""
🧠 {bold('ФРЕДИ: БУДЕТ НЕТОЧНО')}

Ок, пропускаем. Маршрут построю без учёта твоих условий — он будет общим.

Хочешь продолжить?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="✅ ДА, ПОКАЖИ ПЛАН", callback_data="skip_to_route"))
    keyboard.add(InlineKeyboardButton(text="🔄 ВСЁ-ТАКИ ОТВЕТИТЬ", callback_data="check_reality"))
    keyboard.add(InlineKeyboardButton(text="◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


async def skip_goal_questions(call: CallbackQuery, state_data: Dict):
    """Пропускает целевые вопросы"""
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    update_user_state_data(call.from_user.id, goal_context={"time_per_week": 5, "budget": 0})
    
    await calculate_and_show_feasibility(call, state_data)


async def skip_to_route(call: CallbackQuery, state_data: Dict):
    """Пропускает проверку и сразу строит маршрут"""
    goal = state_data.get("pending_goal") or state_data.get("current_destination")
    
    if not goal:
        await call.answer("❌ Цель не найдена")
        return
    
    await build_route(call, state_data, goal.get('id'))


async def accept_feasibility_plan(call: CallbackQuery, state_data: Dict):
    """Принимает план и переходит к построению маршрута"""
    goal = state_data.get("current_destination")
    
    if not goal:
        await call.answer("❌ Цель не найдена")
        return
    
    run_sync_in_background(save_goal_to_db_sync, call.from_user.id, goal, "accepted")
    
    await build_route(call, state_data, goal.get('id'))


async def adjust_timeline(call: CallbackQuery, state_data: Dict):
    """Предлагает скорректировать сроки"""
    goal = state_data.get("current_destination")
    
    text = f"""
🧠 {bold('ФРЕДИ: КОРРЕКТИРОВКА СРОКОВ')}

Текущий срок: 6 месяцев

Если увеличить срок до 12 месяцев, нагрузка снизится:
• Время: с 13 ч/нед до 6-7 ч/нед
• Энергия: с 7/10 до 5-6/10

Это сделает цель более реалистичной в твоих условиях.

👇 Что выбираешь?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="✅ УВЕЛИЧИТЬ СРОК", callback_data="apply_extended_timeline"))
    keyboard.add(InlineKeyboardButton(text="🔄 ОСТАВИТЬ КАК ЕСТЬ", callback_data="accept_feasibility_plan"))
    keyboard.add(InlineKeyboardButton(text="📉 СНИЗИТЬ ПЛАНКУ", callback_data="reduce_goal"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


async def reduce_goal(call: CallbackQuery, state_data: Dict):
    """Предлагает снизить планку цели"""
    text = f"""
🧠 {bold('ФРЕДИ: СНИЖЕНИЕ ПЛАНКИ')}

Вместо "увеличить доход в 2 раза" можно выбрать:
• Увеличить на 50% (реалистично за 6 месяцев)
• Увеличить на 30% (легко за 3-4 месяца)
• Проработать денежные блоки (подготовка)

👇 Что выбираешь?
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="📈 +50% (6 мес)", callback_data="select_goal_50"))
    keyboard.add(InlineKeyboardButton(text="📈 +30% (4 мес)", callback_data="select_goal_30"))
    keyboard.add(InlineKeyboardButton(text="🧠 ПРОРАБОТКА БЛОКОВ", callback_data="select_goal_blocks"))
    keyboard.add(InlineKeyboardButton(text="◀️ ДРУГАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    
    safe_send_message(call.message, text, reply_markup=keyboard, parse_mode='HTML', delete_previous=True)


async def apply_extended_timeline(call: CallbackQuery, state_data: Dict):
    """Применяет увеличенный срок и пересчитывает"""
    await accept_feasibility_plan(call, state_data)


async def select_goal_50(call: CallbackQuery, state_data: Dict):
    """Выбирает цель +50%"""
    new_goal = {
        "id": "income_growth_50",
        "name": "Увеличить доход на 50%",
        "time": "6 месяцев",
        "difficulty": "medium",
        "description": "Реалистичный рост дохода за полгода"
    }
    
    update_user_state_data(call.from_user.id, current_destination=new_goal)
    
    run_sync_in_background(save_goal_to_db_sync, call.from_user.id, new_goal, "adjusted")
    
    await show_theoretical_path(call, state_data, new_goal)


async def select_goal_30(call: CallbackQuery, state_data: Dict):
    """Выбирает цель +30%"""
    new_goal = {
        "id": "income_growth_30",
        "name": "Увеличить доход на 30%",
        "time": "4 месяца",
        "difficulty": "easy",
        "description": "Комфортный рост дохода"
    }
    
    update_user_state_data(call.from_user.id, current_destination=new_goal)
    
    run_sync_in_background(save_goal_to_db_sync, call.from_user.id, new_goal, "adjusted")
    
    await show_theoretical_path(call, state_data, new_goal)


async def select_goal_blocks(call: CallbackQuery, state_data: Dict):
    """Выбирает работу с блоками"""
    new_goal = {
        "id": "money_blocks",
        "name": "Проработать денежные блоки",
        "time": "3-4 недели",
        "difficulty": "medium",
        "description": "Выяви и устрани препятствия на пути к финансовому благополучию"
    }
    
    update_user_state_data(call.from_user.id, current_destination=new_goal)
    
    run_sync_in_background(save_goal_to_db_sync, call.from_user.id, new_goal, "adjusted")
    
    await show_theoretical_path(call, state_data, new_goal)


# ============================================
# МАРШРУТЫ К ЦЕЛЯМ
# ============================================

async def build_route(call: CallbackQuery, state_data: Dict, goal_id: str):
    """Строит маршрут к цели (после проверки реальности или сразу)"""
    user_id = call.from_user.id
    
    mode = state_data.get("communication_mode", "coach")
    goal_info = find_goal_by_id(goal_id, mode)
    
    if not goal_info:
        goal_info = state_data.get("current_destination")
    
    if not goal_info:
        safe_send_message(call.message, "❌ Цель не найдена", delete_previous=True)
        return
    
    status_msg = safe_send_message(
        call.message,
        f"🧠 Строю маршрут к цели: {bold(goal_info.get('name'))}...\n\nЭто займёт несколько секунд.",
        delete_previous=True
    )
    
    try:
        route = await generate_route_ai(user_id, state_data, goal_info)
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации маршрута: {e}")
        route = None
    
    if route:
        update_user_state_data(user_id, current_route=route)
        
        run_sync_in_background(save_route_to_db_sync, user_id, route, goal_info)
        
        await show_route_step(call, state_data, 1, route, status_msg)
    else:
        await show_fallback_route(call, state_data, goal_info, status_msg)


async def show_route_step(
    call: CallbackQuery, 
    state_data: Dict, 
    step: int, 
    route: Dict, 
    status_msg=None
):
    """Показывает текущий шаг маршрута"""
    user_id = call.from_user.id
    
    if not isinstance(state_data, dict):
        logger.error(f"❌ state_data не является словарем: {type(state_data)}")
        state_data = get_user_state_data_dict(user_id)
    
    destination = state_data.get("current_destination", {})
    if not isinstance(destination, dict):
        destination = {}
    
    mode = state_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    route_text = route.get('full_text', 'Маршрут строится...')
    route_text = clean_text_for_safe_display(route_text)
    
    text = f"""
{mode_config['emoji']} {bold('МАРШРУТ К ЦЕЛИ')}

🎯 {bold('Точка назначения:')} {destination.get('name', 'цель')}
⏱ {bold('Ориентировочное время:')} {destination.get('time', 'не указано')}

{route_text}

👇 {bold('Отмечай выполнение, когда готов(а)')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="✅ ВЫПОЛНИЛ ЭТАП", callback_data="route_step_done"))
    keyboard.add(InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    keyboard.add(InlineKeyboardButton(text="◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    if status_msg:
        try:
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении статусного сообщения: {e}")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    set_state(user_id, TestStates.route_active)


async def show_fallback_route(call: CallbackQuery, state_data: Dict, destination: dict, status_msg=None):
    """Резервный маршрут, если ИИ не отвечает"""
    user_id = call.from_user.id
    
    if not isinstance(state_data, dict):
        logger.error(f"❌ state_data не является словарем: {type(state_data)}")
        state_data = get_user_state_data_dict(user_id)
    
    mode = state_data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} {bold('МАРШРУТ К ЦЕЛИ')}

🎯 {bold('Точка назначения:')} {destination.get('name', 'цель')}
⏱ {bold('Ориентировочное время:')} {destination.get('time', 'не указано')}

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
    keyboard.add(InlineKeyboardButton(text="✅ НАЧАТЬ", callback_data="route_step_done"))
    keyboard.add(InlineKeyboardButton(text="◀️ К ЦЕЛЯМ", callback_data="show_dynamic_destinations"))
    
    if status_msg:
        try:
            safe_delete_message(call.message.chat.id, status_msg.message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении статусного сообщения: {e}")
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    set_state(user_id, TestStates.route_active)


async def route_step_done(call: CallbackQuery, state_data: Dict):
    """Отмечает выполнение этапа маршрута"""
    user_id = call.from_user.id
    
    step = state_data.get("route_step", 1)
    route_progress = state_data.get("route_progress", [])
    
    route_progress.append(step)
    next_step = step + 1
    
    update_user_state_data(user_id, route_step=next_step, route_progress=route_progress)
    
    run_sync_in_background(update_route_progress_in_db_sync, user_id, step, route_progress)
    
    if next_step > 3:
        await complete_route(call, state_data)
    else:
        safe_send_message(
            call.message,
            f"✅ {bold(f'Этап {step} выполнен!')}\n\nПереходим к этапу {next_step}...",
            parse_mode='HTML',
            delete_previous=True
        )
        await asyncio.sleep(1)
        
        route = state_data.get("current_route", {})
        await show_route_step(call, state_data, next_step, route, None)


async def complete_route(call: CallbackQuery, state_data: Dict):
    """Показывает завершение маршрута"""
    user_id = call.from_user.id
    user_name = get_user_name(user_id)
    
    destination = state_data.get("current_destination", {})
    
    run_sync_in_background(log_event, user_id, 'route_completed', {
        'goal_id': destination.get('id'),
        'goal_name': destination.get('name'),
        'timestamp': time.time()
    })
    
    text = f"""
🎉 {bold('МАРШРУТ ЗАВЕРШЕН!')}

Поздравляю, {user_name}! Ты достиг цели: {bold(destination.get('name', 'цель'))}

💪 {bold('ГОРДИСЬ СОБОЙ!')}

Хочешь выбрать новую цель или закрепить результат?

👇 {bold('Выбери действие:')}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="🎯 НОВАЯ ЦЕЛЬ", callback_data="show_dynamic_destinations"))
    keyboard.add(InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results"))
    keyboard.add(InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions"))
    
    safe_send_message(
        call.message,
        text,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )
    
    update_user_state_data(user_id, route_step=None, current_destination=None, current_route=None)
    
    run_sync_in_background(save_user, user_id, get_user_name(user_id), None)
    run_sync_in_background(save_user_data, user_id, user_data.get(user_id, {}))


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА ЦЕЛЕЙ
# ============================================

def find_goal_by_id(goal_id: str, mode: str) -> Optional[Dict]:
    """Ищет цель по ID во всех категориях"""
    all_goals = {
        "improve_relations": {"id": "improve_relations", "name": "Улучшить отношения с близкими", "time": "4-6 недель", "difficulty": "medium", "description": "Построй гармоничные отношения с семьей и друзьями"},
        "find_partner": {"id": "find_partner", "name": "Найти партнёра", "time": "3-5 месяцев", "difficulty": "hard", "description": "Встретить человека для серьёзных отношений"},
        "boundaries": {"id": "boundaries", "name": "Научиться защищать границы", "time": "2-3 недели", "difficulty": "medium", "description": "Освой искусство говорить 'нет'"},
        "income_growth": {"id": "income_growth", "name": "Увеличить доход", "time": "4-6 недель", "difficulty": "hard", "description": "Создай стратегию для роста дохода"},
        "financial_plan": {"id": "financial_plan", "name": "Создать финансовый план", "time": "2-3 недели", "difficulty": "easy", "description": "Составь личный финансовый план"},
        "money_blocks": {"id": "money_blocks", "name": "Проработать денежные блоки", "time": "3-4 недели", "difficulty": "medium", "description": "Выяви и устрани препятствия"},
        "self_esteem": {"id": "self_esteem", "name": "Повысить самооценку", "time": "4-5 недель", "difficulty": "medium", "description": "Научись ценить себя"},
        "anxiety": {"id": "anxiety", "name": "Справиться с тревогой", "time": "3-4 недели", "difficulty": "medium", "description": "Обрети внутреннее спокойствие"},
        "purpose": {"id": "purpose", "name": "Найти предназначение", "time": "5-7 недель", "difficulty": "hard", "description": "Ответь на вопрос 'зачем я здесь?'"},
        "new_skill": {"id": "new_skill", "name": "Освоить новый навык", "time": "4-6 недель", "difficulty": "medium", "description": "Научись чему-то новому"},
        "reading": {"id": "reading", "name": "Читать по книге в неделю", "time": "8 недель", "difficulty": "easy", "description": "Сформируй привычку читать"},
        "course": {"id": "course", "name": "Пройти онлайн-курс", "time": "6-8 недель", "difficulty": "medium", "description": "Получи новые знания"},
        "sport": {"id": "sport", "name": "Начать заниматься спортом", "time": "4 недели", "difficulty": "medium", "description": "Внедри регулярные тренировки"},
        "sleep": {"id": "sleep", "name": "Наладить сон", "time": "3-4 недели", "difficulty": "easy", "description": "Улучши качество сна"},
        "energy": {"id": "energy", "name": "Повысить уровень энергии", "time": "4 недели", "difficulty": "medium", "description": "Чувствуй себя бодрее"},
        "start_creative": {"id": "start_creative", "name": "Начать творить", "time": "3-4 недели", "difficulty": "easy", "description": "Найди своё творческое выражение"},
        "overcome_block": {"id": "overcome_block", "name": "Преодолеть творческий блок", "time": "2-3 недели", "difficulty": "medium", "description": "Верни вдохновение"},
        "project": {"id": "project", "name": "Завершить творческий проект", "time": "6-8 недель", "difficulty": "hard", "description": "Доведи дело до конца"}
    }
    
    return all_goals.get(goal_id)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'get_dynamic_destinations',
    'show_dynamic_destinations',
    'show_theoretical_path',
    'handle_dynamic_destination',
    'custom_destination',
    'show_reality_check',
    'start_life_context_collection',
    'ask_goal_specific_questions',
    'calculate_and_show_feasibility',
    'skip_life_context',
    'skip_goal_questions',
    'skip_to_route',
    'accept_feasibility_plan',
    'adjust_timeline',
    'reduce_goal',
    'apply_extended_timeline',
    'select_goal_50',
    'select_goal_30',
    'select_goal_blocks',
    'build_route',
    'show_route_step',
    'show_fallback_route',
    'route_step_done',
    'complete_route',
    'find_goal_by_id',
    'show_goals_categories',
    'show_goals_for_category',
    'select_goal',
    'save_goal_to_db_sync',
    'save_route_to_db_sync',
    'update_route_progress_in_db_sync',
    'save_feasibility_result_to_db_sync'
]
