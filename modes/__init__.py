#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль с режимами общения для виртуального психолога.
Каждый режим реализует свой стиль общения, инструменты и промпты.
"""
from typing import Dict, Any, Optional, List
import logging

from .coach import CoachMode
from .psychologist import PsychologistMode
from .trainer import TrainerMode

logger = logging.getLogger(__name__)

# Словарь доступных режимов
_mode_classes = {
    "coach": CoachMode,
    "psychologist": PsychologistMode,  # бывший friend
    "trainer": TrainerMode
}

# Для обратной совместимости со старыми названиями
_mode_aliases = {
    "friend": "psychologist",  # автоматическая миграция
    "medium": "coach",
    "hard": "trainer",
    "soft": "psychologist"
}


def get_mode(mode_name: str, user_id: int, user_data: Dict[str, Any], context=None):
    """
    Фабрика для создания экземпляра режима.
    
    Args:
        mode_name: Название режима ("coach", "psychologist", "trainer")
        user_id: ID пользователя
        user_data: Данные пользователя (профиль, история и т.д.)
        context: Контекст пользователя (опционально)
    
    Returns:
        Экземпляр класса режима
        
    Example:
        >>> mode = get_mode("coach", user_id, state_data, user_context)
        >>> response = mode.process_question("Что мне делать?")
    """
    # Проверяем, не алиас ли это
    original_name = mode_name
    if mode_name in _mode_aliases:
        mode_name = _mode_aliases[mode_name]
        logger.info(f"🔀 Алиас '{original_name}' -> '{mode_name}'")
    
    # Получаем класс режима
    mode_class = _mode_classes.get(mode_name)
    
    # Если режим не найден, используем CoachMode по умолчанию
    if not mode_class:
        logger.warning(f"⚠️ Режим '{mode_name}' не найден, используется CoachMode")
        mode_class = CoachMode
    
    # Создаём экземпляр
    try:
        instance = mode_class(user_id, user_data, context)
        logger.info(f"✅ Создан экземпляр режима: {instance.name}")
        return instance
    except Exception as e:
        logger.error(f"❌ Ошибка создания режима {mode_name}: {e}")
        # В случае ошибки возвращаем базовый режим
        return CoachMode(user_id, user_data, context)


def get_available_modes() -> Dict[str, str]:
    """
    Возвращает список доступных режимов с кратким описанием.
    
    Returns:
        Словарь {название: описание}
        
    Example:
        >>> modes = get_available_modes()
        >>> print(modes["coach"])
        "🔮 КОУЧ - помогаю найти ответы внутри себя через вопросы"
    """
    return {
        "coach": "🔮 КОУЧ - помогаю найти ответы внутри себя через вопросы",
        "psychologist": "🧠 ПСИХОЛОГ - работаю с глубинными паттернами и подсознанием",
        "trainer": "⚡ ТРЕНЕР - даю чёткие инструкции и требую результат"
    }


def get_mode_description(mode_name: str, format_type: str = 'text') -> str:
    """
    Возвращает подробное описание режима.
    
    Args:
        mode_name: Название режима
        format_type: 'text' (обычный текст) или 'html' (с HTML-тегами)
        
    Returns:
        Многострочное описание с эмодзи и форматированием
    """
    # Проверяем алиасы
    if mode_name in _mode_aliases:
        mode_name = _mode_aliases[mode_name]
    
    # Описания в plain text (без Markdown)
    descriptions_text = {
        "coach": """
🔮 Режим КОУЧ

Как работает:
Задаёт открытые вопросы, помогает найти ответы внутри себя. Использует сократический диалог и коучинговые техники.

Когда выбирать:
Когда хотите разобраться в себе, найти новые перспективы, но не нуждаетесь в готовых советах.

Что получите:
• Осознание своих паттернов
• Новые вопросы для размышления
• Поддержку в исследовании себя

Пример диалога:
— Я боюсь выступать публично
— Что самое страшное может случиться, если ты выступишь?
""",
        "psychologist": """
🧠 Режим ПСИХОЛОГ

Как работает:
Анализирует глубинные паттерны, работает с защитными механизмами, использует гипнотические техники и терапевтические метафоры.

Когда выбирать:
Когда есть повторяющиеся проблемы, травматический опыт, сложные эмоции, или хотите заглянуть в подсознание.

Что получите:
• Понимание глубинных причин
• Доступ к бессознательному
• Терапевтические метафоры
• Гипнотические техники (по запросу)

Пример диалога:
— Я боюсь выступать публично
— Когда ты впервые почувствовал этот страх? Что тогда происходило?
""",
        "trainer": """
⚡ Режим ТРЕНЕР

Как работает:
Даёт конкретные задания, ставит дедлайны, мотивирует через вызов. Фокус на действии и результате.

Когда выбирать:
Когда нужен пинок, чёткий план действий и контроль выполнения. Для тех, кто хочет быстро перейти к делу.

Что получите:
• Конкретные шаги
• Дедлайны и ответственность
• Мотивацию через вызов
• Реальный прогресс

Пример диалога:
— Я боюсь выступать публично
— Задание: завтра встань и скажи тост на 1 минуту. Дедлайн: 20:00. Отчитаешься.
"""
    }
    
    # Описания в HTML (для сообщений)
    descriptions_html = {
        "coach": """
<b>🔮 Режим КОУЧ</b>

<b>Как работает:</b>
Задаёт открытые вопросы, помогает найти ответы внутри себя. Использует сократический диалог и коучинговые техники.

<b>Когда выбирать:</b>
Когда хотите разобраться в себе, найти новые перспективы, но не нуждаетесь в готовых советах.

<b>Что получите:</b>
• Осознание своих паттернов
• Новые вопросы для размышления
• Поддержку в исследовании себя

<b>Пример диалога:</b>
— Я боюсь выступать публично
— Что самое страшное может случиться, если ты выступишь?
""",
        "psychologist": """
<b>🧠 Режим ПСИХОЛОГ</b>

<b>Как работает:</b>
Анализирует глубинные паттерны, работает с защитными механизмами, использует гипнотические техники и терапевтические метафоры.

<b>Когда выбирать:</b>
Когда есть повторяющиеся проблемы, травматический опыт, сложные эмоции, или хотите заглянуть в подсознание.

<b>Что получите:</b>
• Понимание глубинных причин
• Доступ к бессознательному
• Терапевтические метафоры
• Гипнотические техники (по запросу)

<b>Пример диалога:</b>
— Я боюсь выступать публично
— Когда ты впервые почувствовал этот страх? Что тогда происходило?
""",
        "trainer": """
<b>⚡ Режим ТРЕНЕР</b>

<b>Как работает:</b>
Даёт конкретные задания, ставит дедлайны, мотивирует через вызов. Фокус на действии и результате.

<b>Когда выбирать:</b>
Когда нужен пинок, чёткий план действий и контроль выполнения. Для тех, кто хочет быстро перейти к делу.

<b>Что получите:</b>
• Конкретные шаги
• Дедлайны и ответственность
• Мотивацию через вызов
• Реальный прогресс

<b>Пример диалога:</b>
— Я боюсь выступать публично
— Задание: завтра встань и скажи тост на 1 минуту. Дедлайн: 20:00. Отчитаешься.
"""
    }
    
    # Выбираем нужный формат
    if format_type == 'html':
        return descriptions_html.get(mode_name, descriptions_html["coach"])
    else:
        return descriptions_text.get(mode_name, descriptions_text["coach"])


def get_mode_emoji(mode_name: str) -> str:
    """
    Возвращает эмодзи для режима.
    
    Args:
        mode_name: Название режима
        
    Returns:
        Эмодзи режима
    """
    emoji_map = {
        "coach": "🔮",
        "psychologist": "🧠",
        "trainer": "⚡"
    }
    
    if mode_name in _mode_aliases:
        mode_name = _mode_aliases[mode_name]
    
    return emoji_map.get(mode_name, "🔮")


def get_mode_display_name(mode_name: str) -> str:
    """
    Возвращает отображаемое название режима с эмодзи.
    
    Args:
        mode_name: Название режима
        
    Returns:
        Строка вида "🔮 КОУЧ"
    """
    name_map = {
        "coach": "🔮 КОУЧ",
        "psychologist": "🧠 ПСИХОЛОГ",
        "trainer": "⚡ ТРЕНЕР"
    }
    
    if mode_name in _mode_aliases:
        mode_name = _mode_aliases[mode_name]
    
    return name_map.get(mode_name, "🔮 КОУЧ")


def validate_mode(mode_name: str) -> bool:
    """
    Проверяет, существует ли режим с таким названием.
    
    Args:
        mode_name: Название режима для проверки
        
    Returns:
        True если режим существует, иначе False
    """
    if mode_name in _mode_classes:
        return True
    if mode_name in _mode_aliases:
        return True
    return False


def get_all_mode_names() -> List[str]:
    """
    Возвращает список всех доступных названий режимов.
    
    Returns:
        Список строк с названиями
    """
    return list(_mode_classes.keys())


def get_mode_config(mode_name: str) -> Dict[str, Any]:
    """
    Возвращает конфигурацию режима для использования в других модулях.
    
    Args:
        mode_name: Название режима
        
    Returns:
        Словарь с настройками режима
    """
    if mode_name in _mode_aliases:
        mode_name = _mode_aliases[mode_name]
    
    configs = {
        "coach": {
            "emoji": "🔮",
            "name": "КОУЧ",
            "voice": "filipp",
            "voice_emotion": "neutral",
            "response_style": "questions",
            "max_tokens": 1000,
            "temperature": 0.7
        },
        "psychologist": {
            "emoji": "🧠",
            "name": "ПСИХОЛОГ",
            "voice": "ermil",
            "voice_emotion": "good",
            "response_style": "deep",
            "max_tokens": 1500,
            "temperature": 0.8
        },
        "trainer": {
            "emoji": "⚡",
            "name": "ТРЕНЕР",
            "voice": "filipp",
            "voice_emotion": "strict",
            "response_style": "direct",
            "max_tokens": 800,
            "temperature": 0.6
        }
    }
    
    return configs.get(mode_name, configs["coach"])


# Для удобства импорта
__all__ = [
    'get_mode',
    'get_available_modes', 
    'get_mode_description',
    'get_mode_emoji',
    'get_mode_display_name',
    'get_mode_config',
    'validate_mode',
    'get_all_mode_names',
    'CoachMode',
    'PsychologistMode',
    'TrainerMode'
]
