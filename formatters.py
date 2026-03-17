#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для форматирования текста для МАКС
Использует Markdown-форматирование (**жирный**, *курсив*)

ВЕРСИЯ 2.0 - ИСПРАВЛЕНА ПРОБЛЕМА С "УЗКИМИ" СООБЩЕНИЯМИ
"""

import re
from typing import List


def bold(text: str) -> str:
    """Жирный текст для МАКС (Markdown)"""
    if not text:
        return ""
    return f"**{text}**"


def italic(text: str) -> str:
    """Курсив для МАКС (Markdown)"""
    if not text:
        return ""
    return f"*{text}*"


def emoji_text(emoji: str, text: str, bold_text: bool = True) -> str:
    """Текст с эмодзи"""
    if not text:
        return emoji
    if bold_text:
        return f"{emoji} {bold(text)}"
    return f"{emoji} {text}"


def calculate_progress(current: int, total: int) -> str:
    """
    Возвращает прогресс-бар для отображения в вопросах теста
    
    Args:
        current: текущий номер вопроса (начиная с 1)
        total: общее количество вопросов
    
    Returns:
        строка с прогресс-баром, например: "▸ Вопрос 3/8 • ███░░░░░░░"
    """
    if total <= 0:
        return ""
    
    # Убеждаемся, что current не превышает total
    current = min(current, total)
    
    percent = int((current / total) * 10)
    bar = "█" * percent + "░" * (10 - percent)
    return f"▸ Вопрос {current}/{total} • {bar}"


def clean_text_for_safe_display(text: str) -> str:
    """Очищает текст от лишних символов, сохраняя Markdown-форматирование"""
    if not text:
        return text
    
    # Удаляем HTML-теги (они не работают в МАКС)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем множественные переводы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    
    return text.strip()


def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Разбивает длинное сообщение на части по max_length символов,
    стараясь не разрывать слова и абзацы.
    
    ВАЖНО: Функция автоматически удаляет лишние пробелы в начале каждой части,
    чтобы MAX не интерпретировал их как цитату или код (что приводит к "узкому" отображению)
    
    Args:
        text: исходный текст
        max_length: максимальная длина одной части (по умолчанию 4000)
    
    Returns:
        список строк, каждая не длиннее max_length
    """
    if not text:
        return []
    
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
    
    # ✅ КРИТИЧЕСКИ ВАЖНО: Очищаем каждую часть от пробелов и табуляций в начале
    # Это предотвращает интерпретацию сообщения как цитаты или кода в MAX
    cleaned_parts = []
    for i, part in enumerate(parts):
        # Убираем все пробелы и табуляции в начале строки
        cleaned = re.sub(r'^\s+', '', part, flags=re.MULTILINE)
        
        # Также убираем пробелы в начале каждой строки внутри части
        # (но оставляем отступы для списков)
        lines = cleaned.split('\n')
        cleaned_lines = []
        for line in lines:
            # Если строка начинается с маркера списка, сохраняем отступ
            if re.match(r'^[•\-*\d]', line.lstrip()):
                # Сохраняем один пробел для маркера списка
                cleaned_lines.append(line.lstrip())
            else:
                # Для обычного текста убираем все ведущие пробелы
                cleaned_lines.append(line.lstrip())
        
        cleaned = '\n'.join(cleaned_lines)
        
        # Если после очистки строка пустая - пропускаем
        if not cleaned:
            continue
        
        # Для всех частей, кроме первой, добавляем маркер начала обычного текста
        # Это гарантированно сбросит любое форматирование от предыдущей части
        if i > 0:
            # Используем символ-невидимку (U+2800) для сброса форматирования
            # Этот символ не виден, но заставляет MAX начать с обычного текста
            cleaned = "⠀" + cleaned
        
        cleaned_parts.append(cleaned)
    
    return cleaned_parts


def format_profile_text(text: str) -> str:
    """Форматирует текст профиля с жирными заголовками и эмодзи, убирает дубли"""
    if not text:
        return text
    
    # Очищаем от HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Карта замены заголовков с эмодзи
    header_map = [
        (r'БЛОК\s*1:?\s*', '🔑 **КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА**'),
        (r'БЛОК\s*2:?\s*', '💪 **СИЛЬНЫЕ СТОРОНЫ**'),
        (r'БЛОК\s*3:?\s*', '🎯 **ЗОНЫ РОСТА**'),
        (r'БЛОК\s*4:?\s*', '🌱 **КАК ЭТО СФОРМИРОВАЛОСЬ**'),
        (r'БЛОК\s*5:?\s*', '⚠️ **ГЛАВНАЯ ЛОВУШКА**'),
    ]
    
    # Заменяем "БЛОК X:" на правильные заголовки
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Убираем дублирование заголовков
    for _, header in header_map:
        # Убираем дубли: заголовок + такой же заголовок (без **)
        clean_header = header.replace('**', '')
        pattern = rf'({re.escape(header)})\s*\n\s*{re.escape(clean_header)}'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
    
    # ✅ Добавляем пустые строки между разделами
    sections = [
        'КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА',
        'СИЛЬНЫЕ СТОРОНЫ',
        'ЗОНЫ РОСТА',
        'КАК ЭТО СФОРМИРОВАЛОСЬ',
        'ГЛАВНАЯ ЛОВУШКА'
    ]
    
    for section in sections:
        # Ищем заголовок с эмодзи и жирным
        pattern = rf'(🔑|💪|🎯|🌱|⚠️)\s+\*\*{re.escape(section)}\*\*'
        
        # Добавляем пустую строку перед заголовком, если её нет
        def add_newline_before(match):
            return f"\n\n{match.group(0)}"
        
        text = re.sub(pattern, add_newline_before, text)
    
    # Убираем лишние пустые строки в начале
    text = re.sub(r'^\n+', '', text)
    
    # Нормализуем пустые строки (не больше двух подряд)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def format_psychologist_text(text: str, user_name: str = "") -> str:
    """Форматирует мысли психолога с жирными заголовками и эмодзи"""
    if not text:
        return text
    
    # Очищаем от HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Убираем нумерацию
    text = re.sub(r'###\s*\d+\.?\s*', '', text)
    text = re.sub(r'\d+\.\s*', '', text)
    
    # Добавляем обращение по имени
    if user_name and not text.lower().startswith(user_name.lower()):
        first_word = text.split()[0] if text else ""
        if first_word and first_word.lower() not in ['здравствуйте', 'привет', 'добрый']:
            text = f"{user_name}, " + text[0].lower() + text[1:] if text else text
    
    # ✅ Убираем дублирование эмодзи
    text = re.sub(r'🔐\s*🔐', '🔐', text)
    text = re.sub(r'🔄\s*🔄', '🔄', text)
    text = re.sub(r'🚪\s*🚪', '🚪', text)
    text = re.sub(r'📊\s*📊', '📊', text)
    
    # Карта замены заголовков
    header_map = [
        (r'🔐\s*КЛЮЧЕВОЙ\s*ЭЛЕМЕНТ', '🔐 **КЛЮЧЕВОЙ ЭЛЕМЕНТ**'),
        (r'🔄\s*ПЕТЛЯ', '🔄 **ПЕТЛЯ**'),
        (r'🚪\s*ТОЧКА\s*ВХОДА', '🚪 **ТОЧКА ВХОДА**'),
        (r'📊\s*ПРОГНОЗ', '📊 **ПРОГНОЗ**'),
    ]
    
    # Применяем форматирование к заголовкам
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # ✅ Добавляем пустые строки между разделами
    sections = [
        'КЛЮЧЕВОЙ ЭЛЕМЕНТ',
        'ПЕТЛЯ',
        'ТОЧКА ВХОДА',
        'ПРОГНОЗ'
    ]
    
    for section in sections:
        pattern = rf'(🔐|🔄|🚪|📊)\s+\*\*{re.escape(section)}\*\*'
        
        def add_newline_before(match):
            return f"\n\n{match.group(0)}"
        
        text = re.sub(pattern, add_newline_before, text)
    
    # Убираем лишние символы в конце
    text = re.sub(r'И вот:\s*$', '', text)
    
    # Нормализуем пустые строки
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\n+', '', text)
    
    return text.strip()


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


def html_to_markdown(text: str) -> str:
    """
    Преобразует HTML-форматирование в Markdown для МАКС
    <b>текст</b> -> **текст**
    <i>текст</i> -> *текст*
    """
    if not text:
        return text
    
    # Жирный
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    
    # Курсив
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    
    # Остальные теги удаляем
    text = re.sub(r'<[^>]+>', '', text)
    
    return text


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'bold',
    'italic',
    'emoji_text',
    'calculate_progress',
    'clean_text_for_safe_display',
    'split_long_message',
    'format_profile_text',
    'format_psychologist_text',
    'strip_html',
    'html_to_markdown'
]
