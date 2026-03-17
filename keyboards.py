#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль клавиатур для MAX-бота
Все клавиатуры возвращаются в формате, понятном для maxibot
ИСПРАВЛЕНО: заменены проблемные эмодзи на 🧐
"""
from maxibot import types
from typing import List, Optional, Dict, Any

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> types.InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру из списка кнопок
    
    Args:
        buttons: Список рядов кнопок, каждая кнопка = {"text": "...", "callback_data": "..."}
    
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = types.InlineKeyboardMarkup()
    for row in buttons:
        row_buttons = []
        for btn in row:
            row_buttons.append(
                types.InlineKeyboardButton(
                    text=btn["text"],
                    callback_data=btn["callback_data"]
                )
            )
        keyboard.row(*row_buttons)
    return keyboard


def create_reply_keyboard(buttons: List[List[str]], one_time: bool = True, resize: bool = True) -> types.ReplyKeyboardMarkup:
    """
    Создает reply-клавиатуру (для ввода текста)
    
    Args:
        buttons: Список рядов кнопок (текст на кнопках)
        one_time: Скрывать после нажатия
        resize: Подстраивать размер
    
    Returns:
        ReplyKeyboardMarkup
    """
    keyboard = types.ReplyKeyboardMarkup(
        one_time_keyboard=one_time,
        resize_keyboard=resize
    )
    for row in buttons:
        keyboard.row(*row)
    return keyboard


# ============================================
# КЛАВИАТУРЫ ДЛЯ ВЫБОРА РЕЖИМА
# ============================================

def get_mode_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора режима"""
    buttons = [
        [
            {"text": "🔮 КОУЧ", "callback_data": "mode_coach"},
            {"text": "🧠 ПСИХОЛОГ", "callback_data": "mode_psychologist"}
        ],
        [
            {"text": "⚡ ТРЕНЕР", "callback_data": "mode_trainer"},
            {"text": "❓ ЗАЧЕМ ЭТО", "callback_data": "why_details"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_mode_confirmation_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для подтверждения выбранного режима"""
    buttons = [
        [
            {"text": "🚀 НАЧАТЬ ТЕСТ", "callback_data": "start_test"},
            {"text": "🔄 ДРУГОЙ РЕЖИМ", "callback_data": "show_modes"}
        ],
        [
            {"text": "📋 МОЙ ПРОФИЛЬ", "callback_data": "show_profile"},
            {"text": "🎯 ВЫБРАТЬ ЦЕЛЬ", "callback_data": "show_goals"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ ТЕСТИРОВАНИЯ
# ============================================

def get_stage_1_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для этапа 1 (восприятие)"""
    buttons = [
        [
            {"text": "А", "callback_data": "stage1_a"},
            {"text": "Б", "callback_data": "stage1_b"}
        ],
        [
            {"text": "В", "callback_data": "stage1_c"},
            {"text": "Г", "callback_data": "stage1_d"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_stage_2_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для этапа 2 (мышление) - цифры 1-9"""
    buttons = [
        [
            {"text": "1️⃣", "callback_data": "stage2_1"},
            {"text": "2️⃣", "callback_data": "stage2_2"},
            {"text": "3️⃣", "callback_data": "stage2_3"}
        ],
        [
            {"text": "4️⃣", "callback_data": "stage2_4"},
            {"text": "5️⃣", "callback_data": "stage2_5"},
            {"text": "6️⃣", "callback_data": "stage2_6"}
        ],
        [
            {"text": "7️⃣", "callback_data": "stage2_7"},
            {"text": "8️⃣", "callback_data": "stage2_8"},
            {"text": "9️⃣", "callback_data": "stage2_9"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_stage_3_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для этапа 3 (поведение) - цифры 1-6"""
    buttons = [
        [
            {"text": "1️⃣", "callback_data": "stage3_1"},
            {"text": "2️⃣", "callback_data": "stage3_2"}
        ],
        [
            {"text": "3️⃣", "callback_data": "stage3_3"},
            {"text": "4️⃣", "callback_data": "stage3_4"}
        ],
        [
            {"text": "5️⃣", "callback_data": "stage3_5"},
            {"text": "6️⃣", "callback_data": "stage3_6"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_stage_4_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для этапа 4 (точка роста) - буквы А-Д"""
    buttons = [
        [
            {"text": "А", "callback_data": "stage4_a"},
            {"text": "Б", "callback_data": "stage4_b"}
        ],
        [
            {"text": "В", "callback_data": "stage4_c"},
            {"text": "Г", "callback_data": "stage4_d"}
        ],
        [
            {"text": "Д", "callback_data": "stage4_e"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_stage_5_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для этапа 5 (глубинные паттерны) - буквы А-Д"""
    buttons = [
        [
            {"text": "А", "callback_data": "stage5_a"},
            {"text": "Б", "callback_data": "stage5_b"}
        ],
        [
            {"text": "В", "callback_data": "stage5_c"},
            {"text": "Г", "callback_data": "stage5_d"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_clarifying_keyboard(options: Dict[str, str]) -> types.InlineKeyboardMarkup:
    """
    Клавиатура для уточняющих вопросов
    
    Args:
        options: Словарь {key: text} вариантов ответа
    """
    buttons = []
    row = []
    for i, (key, text) in enumerate(options.items()):
        if text:
            # Сокращаем текст для кнопки
            short_text = text[:15] + "..." if len(text) > 15 else text
            row.append({"text": short_text, "callback_data": f"clarify_{key}"})
        
        # По 2 кнопки в ряд
        if len(row) == 2 or i == len(options) - 1:
            if row:
                buttons.append(row)
                row = []
    
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ ГЛАВНОГО МЕНЮ
# ============================================

def get_main_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню (до теста)"""
    buttons = [
        [
            {"text": "🚀 ПРОЙТИ ТЕСТ", "callback_data": "start_context"},
            {"text": "❓ ЗАЧЕМ ЭТО", "callback_data": "why_details"}
        ],
        [
            {"text": "🔮 ВЫБРАТЬ РЕЖИМ", "callback_data": "show_modes"},
            {"text": "📋 МОЙ ПРОФИЛЬ", "callback_data": "show_profile"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_main_menu_after_mode_keyboard(has_profile: bool = False) -> types.InlineKeyboardMarkup:
    """
    Главное меню (после выбора режима) - 4 основные кнопки
    
    Args:
        has_profile: есть ли у пользователя профиль
    """
    buttons = []
    
    # Первый ряд - две кнопки: СКАЗКА и ВОПРОС
    row1 = [
        {"text": "📖 СКАЗКА", "callback_data": "ask_tale"},
        {"text": "❓ ВОПРОС", "callback_data": "ask_question"}
    ]
    buttons.append(row1)
    
    # Второй ряд - две кнопки: ПРОФИЛЬ и ПРОЙТИ ТЕСТ
    row2 = []
    
    # Кнопка ПРОФИЛЬ (ведет на профиль или сообщение о необходимости теста)
    if has_profile:
        row2.append({"text": "📊 ПРОФИЛЬ", "callback_data": "show_profile"})
    else:
        row2.append({"text": "📊 ПРОФИЛЬ", "callback_data": "profile_not_ready"})
    
    # Кнопка ПРОЙТИ ТЕСТ (всегда есть)
    row2.append({"text": "🚀 ПРОЙТИ ТЕСТ", "callback_data": "start_context"})
    
    buttons.append(row2)
    
    # Третий ряд - кнопка смены режима
    buttons.append([
        {"text": "🔄 СМЕНИТЬ РЕЖИМ", "callback_data": "show_modes"}
    ])
    
    return create_inline_keyboard(buttons)


def get_restart_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для перезапуска теста (для тех, у кого уже есть профиль)"""
    buttons = [
        [
            {"text": "🔄 ПРОЙТИ ЗАНОВО", "callback_data": "restart_test"},
            {"text": "📋 МОЙ ПРОФИЛЬ", "callback_data": "show_profile"}
        ],
        [
            {"text": "🎯 ВЫБРАТЬ ЦЕЛЬ", "callback_data": "show_goals"},
            {"text": "🔮 СМЕНИТЬ РЕЖИМ", "callback_data": "show_modes"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_start_context_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для начала сбора контекста (исправлено: 🤨 -> 🧐)"""
    buttons = [
        [
            {"text": "🚀 ДАВАЙ, ПОГНАЛИ!", "callback_data": "start_context"},
            {"text": "🧐 А ТЫ ВООБЩЕ КТО?", "callback_data": "why_details"}  # 🤨 заменен на 🧐
        ]
    ]
    return create_inline_keyboard(buttons)


def get_why_details_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура после показа деталей о боте"""
    buttons = [
        [
            {"text": "🚀 ПОГНАЛИ!", "callback_data": "start_context"},
            {"text": "🔮 ВЫБРАТЬ РЕЖИМ", "callback_data": "show_modes"}
        ],
        [
            {"text": "◀️ НАЗАД", "callback_data": "back_to_start"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ ПРОФИЛЯ
# ============================================

def get_profile_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для страницы профиля (исправлено: 💭 -> 🧐)"""
    buttons = [
        [
            {"text": "🧠 AI-ПРОФИЛЬ", "callback_data": "show_ai_profile"},
            {"text": "🧐 МЫСЛИ ПСИХОЛОГА", "callback_data": "show_psychologist_thought"}  # 💭 -> 🧐
        ],
        [
            {"text": "🎯 ВЫБРАТЬ ЦЕЛЬ", "callback_data": "show_goals"},
            {"text": "🔄 ПРОЙТИ ЗАНОВО", "callback_data": "restart_test"}
        ],
        [
            {"text": "◀️ В МЕНЮ", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_ai_profile_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура под AI-профилем (исправлено: 💭 -> 🧐)"""
    buttons = [
        [
            {"text": "🧐 МЫСЛИ ПСИХОЛОГА", "callback_data": "show_psychologist_thought"},  # 💭 -> 🧐
            {"text": "🎯 ВЫБРАТЬ ЦЕЛЬ", "callback_data": "show_goals"}
        ],
        [
            {"text": "🔮 СМЕНИТЬ РЕЖИМ", "callback_data": "show_modes"},
            {"text": "◀️ В ПРОФИЛЬ", "callback_data": "show_profile"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_psychologist_thought_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура под мыслями психолога (исправлено: 💭 -> 🧐)"""
    buttons = [
        [
            {"text": "🧐 МЫСЛИ ПСИХОЛОГА", "callback_data": "show_psychologist_thought"},  # 💭 -> 🧐
            {"text": "🎯 ВЫБРАТЬ ЦЕЛЬ", "callback_data": "show_goals"}
        ],
        [
            {"text": "📖 СКАЗКА", "callback_data": "ask_tale"},
            {"text": "◀️ В ПРОФИЛЬ", "callback_data": "show_profile"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ ЦЕЛЕЙ
# ============================================

def get_goals_categories_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура с категориями целей"""
    buttons = [
        [
            {"text": "🧩 САМОПОЗНАНИЕ", "callback_data": "goals_self_discovery"},
            {"text": "⚖️ РЕШЕНИЯ", "callback_data": "goals_decisions"}
        ],
        [
            {"text": "🎯 ПОСТАНОВКА ЦЕЛЕЙ", "callback_data": "goals_goals"},
            {"text": "🌀 ГЛУБИННЫЕ ПАТТЕРНЫ", "callback_data": "goals_deep_patterns"}
        ],
        [
            {"text": "🕊️ РАБОТА С ТРАВМОЙ", "callback_data": "goals_trauma"},
            {"text": "🌙 ГИПНОТЕРАПИЯ", "callback_data": "goals_hypnosis"}
        ],
        [
            {"text": "💼 КАРЬЕРА", "callback_data": "goals_career"},
            {"text": "💰 БИЗНЕС", "callback_data": "goals_business"}
        ],
        [
            {"text": "🏋️ ПРИВЫЧКИ", "callback_data": "goals_habits"},
            {"text": "🏆 ВЫЗОВЫ", "callback_data": "goals_challenges"}
        ],
        [
            {"text": "◀️ НАЗАД", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


def get_goal_details_keyboard(goal_id: str) -> types.InlineKeyboardMarkup:
    """Клавиатура для конкретной цели"""
    buttons = [
        [
            {"text": "🚀 ВЫБРАТЬ ЭТУ ЦЕЛЬ", "callback_data": f"select_goal_{goal_id}"},
            {"text": "🎯 ДРУГАЯ ЦЕЛЬ", "callback_data": "show_goals"}
        ],
        [
            {"text": "◀️ НАЗАД", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ КОНТЕКСТА (пол, возраст, город)
# ============================================

def get_gender_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для выбора пола"""
    return create_reply_keyboard([
        ["👨 Мужской", "👩 Женский"]
    ])


def get_age_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для выбора возраста"""
    return create_reply_keyboard([
        ["18-25", "26-35"],
        ["36-45", "46-60"],
        ["60+"]
    ])


def get_skip_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура с кнопкой пропуска"""
    return create_reply_keyboard([
        ["⏭️ Пропустить"]
    ])


def get_confirm_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    buttons = [
        [
            {"text": "✅ ДА", "callback_data": "confirm_yes"},
            {"text": "❌ НЕТ", "callback_data": "confirm_no"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ НАВИГАЦИИ
# ============================================

def get_back_keyboard(callback_data: str = "back_to_mode_selected") -> types.InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой 'Назад'"""
    buttons = [
        [{"text": "◀️ НАЗАД", "callback_data": callback_data}]
    ]
    return create_inline_keyboard(buttons)


def get_cancel_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для отмены действия"""
    return create_reply_keyboard([
        ["❌ ОТМЕНА"]
    ])


# ============================================
# КЛАВИАТУРЫ ДЛЯ СКАЗОК
# ============================================

def get_tale_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для сказок"""
    buttons = [
        [
            {"text": "📖 ЕЩЁ СКАЗКУ", "callback_data": "ask_tale"},
            {"text": "🧠 ВОПРОС", "callback_data": "ask_question"}
        ],
        [
            {"text": "◀️ В МЕНЮ", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# КЛАВИАТУРЫ ДЛЯ ИДЕЙ НА ВЫХОДНЫЕ
# ============================================

def get_weekend_ideas_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для идей на выходные"""
    buttons = [
        [
            {"text": "🎨 ДРУГИЕ ИДЕИ", "callback_data": "weekend_ideas"},
            {"text": "🧠 ВОПРОС", "callback_data": "ask_question"}
        ],
        [
            {"text": "◀️ В МЕНЮ", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# АДМИНСКИЕ КЛАВИАТУРЫ
# ============================================

def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Админская клавиатура"""
    buttons = [
        [
            {"text": "📊 СТАТИСТИКА", "callback_data": "admin_stats"},
            {"text": "📢 РАССЫЛКА", "callback_data": "admin_broadcast"}
        ],
        [
            {"text": "👥 ПОЛЬЗОВАТЕЛИ", "callback_data": "admin_users"},
            {"text": "🔧 НАСТРОЙКИ", "callback_data": "admin_settings"}
        ],
        [
            {"text": "◀️ В МЕНЮ", "callback_data": "back_to_mode_selected"}
        ]
    ]
    return create_inline_keyboard(buttons)


# ============================================
# УНИВЕРСАЛЬНАЯ КЛАВИАТУРА ДЛЯ ОТВЕТОВ
# ============================================

def get_options_keyboard(options: List[str], prefix: str = "option") -> types.InlineKeyboardMarkup:
    """
    Универсальная клавиатура из списка опций
    
    Args:
        options: Список текстов опций
        prefix: Префикс для callback_data
    """
    buttons = []
    for i, text in enumerate(options):
        if text:
            buttons.append([
                {"text": text, "callback_data": f"{prefix}_{i}"}
            ])
    return create_inline_keyboard(buttons)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    # Базовые функции
    'create_inline_keyboard',
    'create_reply_keyboard',
    
    # Режимы
    'get_mode_selection_keyboard',
    'get_mode_confirmation_keyboard',
    
    # Тестирование
    'get_stage_1_keyboard',
    'get_stage_2_keyboard',
    'get_stage_3_keyboard',
    'get_stage_4_keyboard',
    'get_stage_5_keyboard',
    'get_clarifying_keyboard',
    
    # Главное меню
    'get_main_menu_keyboard',
    'get_main_menu_after_mode_keyboard',
    'get_restart_keyboard',
    'get_start_context_keyboard',
    'get_why_details_keyboard',
    
    # Профиль
    'get_profile_keyboard',
    'get_ai_profile_keyboard',
    'get_psychologist_thought_keyboard',
    
    # Цели
    'get_goals_categories_keyboard',
    'get_goal_details_keyboard',
    
    # Контекст
    'get_gender_keyboard',
    'get_age_keyboard',
    'get_skip_keyboard',
    'get_confirm_keyboard',
    
    # Навигация
    'get_back_keyboard',
    'get_cancel_keyboard',
    
    # Сказки и идеи
    'get_tale_keyboard',
    'get_weekend_ideas_keyboard',
    
    # Админка
    'get_admin_keyboard',
    
    # Универсальная
    'get_options_keyboard'
]
