#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики выбора и подтверждения режима для MAX
Версия 2.0 - ДОБАВЛЕНО СОХРАНЕНИЕ В БД
ИСПРАВЛЕНО: все f-строки с кавычками
"""
import logging
import asyncio
import time
from maxibot import types
from bot_instance import bot
from config import COMMUNICATION_MODES
from models import UserContext
from keyboards import (
    get_mode_selection_keyboard, 
    get_mode_confirmation_keyboard,
    get_main_menu_keyboard,
    get_main_menu_after_mode_keyboard
)
from formatters import bold
from message_utils import safe_send_message, safe_edit_message

# Импорты из state.py
from state import (
    get_user_context, 
    get_user_context_dict, 
    get_state_data,
    update_state_data,
    user_data,
    user_contexts,
    clear_state,
    set_state,
    TestStates
)

# ✅ ДОБАВЛЕНО: импорт для БД
from db_instance import db, save_user_to_db

logger = logging.getLogger(__name__)

# ============================================
# ✅ ДОБАВЛЕНО: ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ============================================

async def save_mode_to_db(user_id: int, mode: str):
    """Сохраняет выбранный режим в БД"""
    try:
        # Логируем событие
        await db.log_event(
            user_id,
            'mode_selected',
            {
                'mode': mode,
                'mode_name': COMMUNICATION_MODES.get(mode, {}).get('display_name', mode),
                'timestamp': time.time()
            }
        )
        
        # Сохраняем пользователя целиком (контекст уже должен быть обновлен)
        await save_user_to_db(user_id, user_data, user_contexts, {})
        
        logger.debug(f"💾 Режим {mode} для пользователя {user_id} сохранен в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения режима для {user_id}: {e}")

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['mode'])
def cmd_mode(message: types.Message):
    """Команда для смены режима"""
    user_id = message.from_user.id
    
    # Получаем или создаем контекст через функцию
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        # Сохраняем через словарь контекстов
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Показываем выбор режима
    show_mode_selection(message)


@bot.message_handler(commands=['menu'])
def cmd_menu(message: types.Message):
    """Команда для возврата в главное меню"""
    user_id = message.from_user.id
    context = get_user_context(user_id)
    
    if context:
        show_main_menu_after_mode(message, context)
    else:
        # Если нет контекста, показываем главное меню без режима
        show_main_menu(message)


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: call.data == 'show_modes')
def callback_show_modes(call: types.CallbackQuery):
    """Показать выбор режимов"""
    show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'set_mode_coach')
def callback_set_mode_coach(call: types.CallbackQuery):
    """Установить режим КОУЧ"""
    set_mode_coach(call)


@bot.callback_query_handler(func=lambda call: call.data == 'set_mode_psychologist')
def callback_set_mode_psychologist(call: types.CallbackQuery):
    """Установить режим ПСИХОЛОГ"""
    set_mode_psychologist(call)


@bot.callback_query_handler(func=lambda call: call.data == 'set_mode_trainer')
def callback_set_mode_trainer(call: types.CallbackQuery):
    """Установить режим ТРЕНЕР"""
    set_mode_trainer(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def callback_mode_selected(call: types.CallbackQuery):
    """Обработка выбора режима (старый вариант, для совместимости)"""
    user_id = call.from_user.id
    mode = call.data.replace('mode_', '')
    
    # Маппинг для обратной совместимости
    mode_map = {
        "coach": "coach",
        "psychologist": "psychologist",
        "trainer": "trainer",
        "hard": "trainer",
        "medium": "coach",
        "soft": "psychologist"
    }
    new_mode = mode_map.get(mode, "coach")
    
    if new_mode == "coach":
        set_mode_coach(call)
    elif new_mode == "psychologist":
        set_mode_psychologist(call)
    elif new_mode == "trainer":
        set_mode_trainer(call)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_modes')
def callback_back_to_modes(call: types.CallbackQuery):
    """Вернуться к выбору режимов"""
    show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_mode_selected')
def callback_back_to_mode_selected(call: types.CallbackQuery):
    """Возврат к экрану выбранного режима"""
    back_to_mode_selected(call)


@bot.callback_query_handler(func=lambda call: call.data == 'start_test')
def callback_start_test(call: types.CallbackQuery):
    """Начать тест после выбора режима"""
    from .stages import show_stage_1_intro
    user_id = call.from_user.id
    state_data = get_state_data(user_id)
    show_stage_1_intro(call.message, user_id, state_data)


@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def callback_main_menu(call: types.CallbackQuery):
    """Вернуться в главное меню"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if context:
        show_main_menu_after_mode(call.message, context)
    else:
        show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def callback_back_to_main(call: types.CallbackQuery):
    """Вернуться в главное меню до теста"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if context:
        show_main_menu(call.message, context)
    else:
        # Если нет контекста, создаем новый
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
        show_main_menu(call.message, context)


# ============================================
# ФУНКЦИИ УСТАНОВКИ РЕЖИМОВ
# ============================================

def set_mode_coach(call: types.CallbackQuery):
    """Устанавливает режим КОУЧ"""
    user_id = call.from_user.id
    
    # Получаем контекст
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Устанавливаем режим
    context.communication_mode = "coach"
    contexts_dict = get_user_context_dict()
    contexts_dict[user_id] = context
    
    # ✅ СОХРАНЯЕМ В БД
    asyncio.create_task(save_mode_to_db(user_id, "coach"))
    
    # Показываем подтверждение
    show_mode_selected(call.message, "coach")
    
    # Отвечаем на callback
    try:
        bot.answer_callback_query(call.id, "✅ Режим КОУЧ активирован")
    except:
        pass


def set_mode_psychologist(call: types.CallbackQuery):
    """Устанавливает режим ПСИХОЛОГ"""
    user_id = call.from_user.id
    
    # Получаем контекст
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Устанавливаем режим
    context.communication_mode = "psychologist"
    contexts_dict = get_user_context_dict()
    contexts_dict[user_id] = context
    
    # ✅ СОХРАНЯЕМ В БД
    asyncio.create_task(save_mode_to_db(user_id, "psychologist"))
    
    # Показываем подтверждение
    show_mode_selected(call.message, "psychologist")
    
    # Отвечаем на callback
    try:
        bot.answer_callback_query(call.id, "✅ Режим ПСИХОЛОГ активирован")
    except:
        pass


def set_mode_trainer(call: types.CallbackQuery):
    """Устанавливает режим ТРЕНЕР"""
    user_id = call.from_user.id
    
    # Получаем контекст
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Устанавливаем режим
    context.communication_mode = "trainer"
    contexts_dict = get_user_context_dict()
    contexts_dict[user_id] = context
    
    # ✅ СОХРАНЯЕМ В БД
    asyncio.create_task(save_mode_to_db(user_id, "trainer"))
    
    # Показываем подтверждение
    show_mode_selected(call.message, "trainer")
    
    # Отвечаем на callback
    try:
        bot.answer_callback_query(call.id, "✅ Режим ТРЕНЕР активирован")
    except:
        pass


def choose_mode(call: types.CallbackQuery, mode: str):
    """
    Выбор режима через "жесткий/средний/мягкий"
    mode может быть: "hard", "medium", "soft"
    """
    user_id = call.from_user.id
    
    # Получаем контекст
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Маппинг
    mode_map = {
        "hard": "trainer",
        "medium": "coach",
        "soft": "psychologist"
    }
    new_mode = mode_map.get(mode, "coach")
    
    context.communication_mode = new_mode
    contexts_dict = get_user_context_dict()
    contexts_dict[user_id] = context
    
    # ✅ СОХРАНЯЕМ В БД
    asyncio.create_task(save_mode_to_db(user_id, new_mode))
    
    mode_info = COMMUNICATION_MODES.get(new_mode, COMMUNICATION_MODES["coach"])
    
    # 👇 ИСПРАВЛЕНО: вынесли значение в отдельную переменную
    mode_display_name = mode_info["display_name"]
    text = f"{mode_info['emoji']} {bold(f'Выбранный режим: {mode_display_name}')}\n\n"
    text += f"{mode_info.get('responsibility', '')}\n\n"
    text += "Теперь давайте познакомимся поближе."
    
    safe_send_message(call.message, text, delete_previous=True)
    
    # Небольшая пауза
    time.sleep(1)
    
    # Проверяем, заполнен ли контекст
    if not (context.city and context.gender and context.age):
        from .context import start_context
        start_context(call.message)
    else:
        intro_text = f"""
🧠 {bold('ВИРТУАЛЬНЫЙ ПСИХОЛОГ')}

🔍 {bold('5 ЭТАПОВ ТЕСТИРОВАНИЯ:')}

ЭТАП 1: Конфигурация восприятия
ЭТАП 2: Конфигурация мышления
ЭТАП 3: Конфигурация поведения
ЭТАП 4: Точка роста
ЭТАП 5: Глубинные паттерны

⏱ {bold('Всего 15 минут')}

👇 {bold('Начинаем?')}
"""
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro"))
        
        safe_send_message(call.message, intro_text, reply_markup=keyboard)


def back_to_mode_selected(call: types.CallbackQuery):
    """Возврат к экрану выбранного режима"""
    user_id = call.from_user.id
    context = get_user_context(user_id)
    
    if context and context.communication_mode:
        show_mode_selected(call.message, context.communication_mode)
    else:
        show_mode_selection(call.message)


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def show_mode_selection(message: types.Message):
    """Показывает выбор режима общения"""
    user_id = message.chat.id
    
    # Получаем контекст через функцию
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Получаем данные профиля
    profile_data = getattr(context, 'profile_data', {})
    if not profile_data and user_id in user_data:
        profile_data = user_data[user_id].get("profile_data", {})
    
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
    
    # Устанавливаем состояние
    set_state(user_id, TestStates.mode_selection)


def show_mode_selected(message: types.Message, mode: str):
    """Показывает экран подтверждения выбранного режима"""
    user_id = message.chat.id
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    # Получаем данные профиля
    profile_data = getattr(context, 'profile_data', {})
    if not profile_data and user_id in user_data:
        profile_data = user_data[user_id].get("profile_data", {})
    
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
    
    # Проверяем, есть ли профиль
    has_profile = False
    if profile_data or user_data.get(user_id, {}).get("ai_generated_profile"):
        has_profile = True
    else:
        user_data_dict = user_data.get(user_id, {})
        required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
        if all(field in user_data_dict for field in required_minimal):
            has_profile = True
    
    # Получаем клавиатуру с проверкой профиля
    keyboard = get_main_menu_after_mode_keyboard(has_profile)
    
    safe_send_message(message, full_text, reply_markup=keyboard, delete_previous=True)
    
    # Устанавливаем состояние
    set_state(user_id, TestStates.results)


def show_main_menu(message: types.Message, context: UserContext = None):
    """
    Показывает главное меню до теста
    """
    from keyboards import get_main_menu_keyboard
    
    user_id = message.chat.id
    
    if not context:
        context = get_user_context(user_id)
        if not context:
            context = UserContext(user_id)
            contexts_dict = get_user_context_dict()
            contexts_dict[user_id] = context
    
    # Обновляем погоду
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
    
    safe_send_message(message, welcome_text, reply_markup=keyboard, delete_previous=True)


def show_main_menu_after_mode(message: types.Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    from keyboards import get_main_menu_after_mode_keyboard
    
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    # Обновляем погоду
    context.update_weather()
    day_context = context.get_day_context()
    
    # 👇 ИСПРАВЛЕНО: вынесли значение в отдельную переменную
    mode_display_name = mode_config["display_name"]
    text = f"{mode_config['emoji']} {bold(f'РЕЖИМ {mode_display_name}')}\n\n"
    text += context.get_greeting(context.name) + "\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if hasattr(context, 'weather_cache') and context.weather_cache:
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
    
    # Проверяем, есть ли профиль
    user_id = message.chat.id
    user_data_dict = user_data.get(user_id, {})
    has_profile = False
    
    if user_data_dict.get("profile_data") or user_data_dict.get("ai_generated_profile"):
        has_profile = True
    else:
        required_minimal = ["perception_type", "thinking_level", "behavioral_levels"]
        if all(field in user_data_dict for field in required_minimal):
            has_profile = True
    
    if has_profile:
        text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    # Получаем клавиатуру с проверкой профиля
    keyboard = get_main_menu_after_mode_keyboard(has_profile)
    
    safe_send_message(message, text, reply_markup=keyboard)


def get_current_mode(user_id: int) -> str:
    """
    Возвращает текущий режим пользователя
    """
    context = get_user_context(user_id)
    if context and hasattr(context, 'communication_mode'):
        return context.communication_mode
    return "coach"  # по умолчанию


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'cmd_mode',
    'cmd_menu',
    'show_mode_selection',
    'show_mode_selected',
    'show_main_menu',
    'show_main_menu_after_mode',
    'get_current_mode',
    'set_mode_coach',
    'set_mode_psychologist',
    'set_mode_trainer',
    'choose_mode',
    'back_to_mode_selected',
    'callback_show_modes',
    'callback_set_mode_coach',
    'callback_set_mode_psychologist',
    'callback_set_mode_trainer',
    'callback_mode_selected',
    'callback_back_to_modes',
    'callback_back_to_mode_selected',
    'callback_start_test',
    'callback_main_menu',
    'callback_back_to_main',
    # ✅ ДОБАВЛЕНО: функция для БД
    'save_mode_to_db'
]
