#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики выбора и подтверждения режима для MAX
"""
import logging
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

# ИСПРАВЛЕННЫЕ ИМПОРТЫ - используем только функции из context
from handlers.context import get_user_context, get_user_state_data, update_user_state_data, get_user_context_dict
import time

logger = logging.getLogger(__name__)

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
        show_mode_selection(message)


# ============================================
# CALLBACK-ОБРАБОТЧИКИ
# ============================================

@bot.callback_query_handler(func=lambda call: call.data == 'show_modes')
def callback_show_modes(call: types.CallbackQuery):
    """Показать выбор режимов"""
    show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def callback_mode_selected(call: types.CallbackQuery):
    """Обработка выбора режима"""
    user_id = call.from_user.id
    mode = call.data.replace('mode_', '')
    
    # Получаем контекст через функцию
    context = get_user_context(user_id)
    if not context:
        context = UserContext(user_id)
        contexts_dict = get_user_context_dict()
        contexts_dict[user_id] = context
    
    # Устанавливаем режим
    mode_map = {
        "coach": "coach",
        "psychologist": "psychologist",
        "trainer": "trainer",
        "hard": "trainer",
        "medium": "coach",
        "soft": "psychologist"
    }
    new_mode = mode_map.get(mode, "coach")
    
    context.communication_mode = new_mode
    # Сохраняем в словаре контекстов
    contexts_dict = get_user_context_dict()
    contexts_dict[user_id] = context
    
    # Показываем подтверждение
    show_mode_selected(call.message, new_mode)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_modes')
def callback_back_to_modes(call: types.CallbackQuery):
    """Вернуться к выбору режимов"""
    show_mode_selection(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'start_test')
def callback_start_test(call: types.CallbackQuery):
    """Начать тест после выбора режима"""
    from .stages import show_stage_1_intro
    user_id = call.from_user.id
    state_data = get_user_state_data(user_id)
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
    
    # Получаем данные профиля (из БД или контекста)
    profile_data = getattr(context, 'profile_data', {})
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


def show_mode_selected(message: types.Message, mode: str):
    """Показывает экран подтверждения выбранного режима"""
    user_id = message.chat.id
    context = get_user_context(user_id)
    user_name = context.name if context and context.name else "друг"
    
    # Получаем данные профиля
    profile_data = getattr(context, 'profile_data', {})
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


def show_main_menu_after_mode(message: types.Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    from keyboards import get_main_menu_after_mode_keyboard
    
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    # Обновляем погоду
    context.update_weather()
    day_context = context.get_day_context()
    
    text = f"{mode_config['emoji']} {bold(f'РЕЖИМ {mode_config["display_name"]}')}\n\n"
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
    text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    keyboard = get_main_menu_after_mode_keyboard()
    
    safe_send_message(message, text, reply_markup=keyboard)
