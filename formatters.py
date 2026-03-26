#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для форматирования текста для МАКС
Использует Markdown-форматирование (**жирный**, *курсив*)

ВЕРСИЯ 3.1 - ВОЗВРАТ К MARKDOWN (MAX НЕ ПОДДЕРЖИВАЕТ HTML)
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
    """Возвращает прогресс-бар"""
    if total <= 0:
        return ""
    current = min(current, total)
    percent = int((current / total) * 10)
    bar = "█" * percent + "░" * (10 - percent)
    return f"▸ Вопрос {current}/{total} • {bar}"


def clean_text_for_safe_display(text: str) -> str:
    """Очищает текст от лишних символов, сохраняя Markdown-форматирование"""
    if not text:
        return text
    
    # Удаляем HTML-теги (они не работают в MAX)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем множественные переводы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if not line.strip():
            cleaned_lines.append('')
        else:
            cleaned_lines.append(line.strip())
    
    text = '\n'.join(cleaned_lines)
    return text.strip()


def ensure_full_width(text: str) -> str:
    """Убирает пробелы в начале каждой строки"""
    if not text:
        return text
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if not line.strip():
            cleaned_lines.append('')
        else:
            cleaned_lines.append(line.lstrip())
    
    return '\n'.join(cleaned_lines)


def split_long_message(text: str, max_length: int = 3500) -> List[str]:
    """Разбивает длинное сообщение на части"""
    if not text:
        return []
    
    text = ensure_full_width(text)
    
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if not para.strip():
            continue
        
        if len(current_part) + len(para) + 2 <= max_length:
            if current_part:
                current_part += "\n\n" + para
            else:
                current_part = para
        else:
            if current_part:
                parts.append(current_part)
            
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_part = ""
                for sent in sentences:
                    if len(temp_part) + len(sent) + 1 <= max_length:
                        if temp_part:
                            temp_part += " " + sent
                        else:
                            temp_part = sent
                    else:
                        if temp_part:
                            parts.append(temp_part)
                        if len(sent) > max_length:
                            words = sent.split()
                            word_part = ""
                            for word in words:
                                if len(word_part) + len(word) + 1 <= max_length:
                                    if word_part:
                                        word_part += " " + word
                                    else:
                                        word_part = word
                                else:
                                    parts.append(word_part)
                                    word_part = word
                            if word_part:
                                temp_part = word_part
                            else:
                                temp_part = ""
                        else:
                            temp_part = sent
                if temp_part:
                    current_part = temp_part
                else:
                    current_part = ""
            else:
                current_part = para
    
    if current_part:
        parts.append(current_part)
    
    cleaned_parts = []
    for i, part in enumerate(parts):
        cleaned = ensure_full_width(part)
        if i > 0:
            cleaned = "⠀" + cleaned
        cleaned_parts.append(cleaned)
    
    return cleaned_parts


def format_profile_text(text: str) -> str:
    """Форматирует текст профиля с жирными заголовками (Markdown)"""
    if not text:
        return text
    
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Карта замены заголовков (Markdown)
    header_map = [
        (r'БЛОК\s*1:?\s*', '🔑 **КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА**'),
        (r'БЛОК\s*2:?\s*', '💪 **СИЛЬНЫЕ СТОРОНЫ**'),
        (r'БЛОК\s*3:?\s*', '🎯 **ЗОНЫ РОСТА**'),
        (r'БЛОК\s*4:?\s*', '🌱 **КАК ЭТО СФОРМИРОВАЛОСЬ**'),
        (r'БЛОК\s*5:?\s*', '⚠️ **ГЛАВНАЯ ЛОВУШКА**'),
    ]
    
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Убираем дублирование заголовков
    for _, header in header_map:
        clean_header = header.replace('**', '')
        pattern = rf'({re.escape(header)})\s*\n\s*{re.escape(clean_header)}'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
    
    # Добавляем пустые строки между разделами
    sections = [
        'КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА',
        'СИЛЬНЫЕ СТОРОНЫ',
        'ЗОНЫ РОСТА',
        'КАК ЭТО СФОРМИРОВАЛОСЬ',
        'ГЛАВНАЯ ЛОВУШКА'
    ]
    
    for section in sections:
        pattern = rf'(🔑|💪|🎯|🌱|⚠️)\s+\*\*{re.escape(section)}\*\*'
        text = re.sub(pattern, lambda m: f"\n\n{m.group(0)}", text)
    
    text = re.sub(r'^\n+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = ensure_full_width(text)
    
    return text.strip()


def format_psychologist_text(text: str, user_name: str = "") -> str:
    """Форматирует мысли психолога (Markdown)"""
    if not text:
        return text
    
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Убираем нумерацию
    text = re.sub(r'###\s*\d+\.?\s*', '', text)
    text = re.sub(r'\d+\.\s*', '', text)
    
    # Добавляем обращение по имени
    if user_name and not text.lower().startswith(user_name.lower()):
        first_word = text.split()[0] if text else ""
        if first_word and first_word.lower() not in ['здравствуйте', 'привет', 'добрый']:
            text = f"{user_name}, " + text[0].lower() + text[1:] if text else text
    
    # Убираем дублирование эмодзи
    text = re.sub(r'🔐\s*🔐', '🔐', text)
    text = re.sub(r'🔄\s*🔄', '🔄', text)
    text = re.sub(r'🚪\s*🚪', '🚪', text)
    text = re.sub(r'📊\s*📊', '📊', text)
    
    # Карта замены заголовков (Markdown)
    header_map = [
        (r'🔐\s*КЛЮЧЕВОЙ\s*ЭЛЕМЕНТ', '🔐 **КЛЮЧЕВОЙ ЭЛЕМЕНТ**'),
        (r'🔄\s*ПЕТЛЯ', '🔄 **ПЕТЛЯ**'),
        (r'🚪\s*ТОЧКА\s*ВХОДА', '🚪 **ТОЧКА ВХОДА**'),
        (r'📊\s*ПРОГНОЗ', '📊 **ПРОГНОЗ**'),
    ]
    
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Добавляем пустые строки между разделами
    sections = ['КЛЮЧЕВОЙ ЭЛЕМЕНТ', 'ПЕТЛЯ', 'ТОЧКА ВХОДА', 'ПРОГНОЗ']
    for section in sections:
        pattern = rf'(🔐|🔄|🚪|📊)\s+\*\*{re.escape(section)}\*\*'
        text = re.sub(pattern, lambda m: f"\n\n{m.group(0)}", text)
    
    text = re.sub(r'И вот:\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\n+', '', text)
    text = ensure_full_width(text)
    
    return text.strip()


def strip_html(text: str) -> str:
    """Удаляет HTML-теги"""
    if not text:
        return text
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return text


def html_to_markdown(text: str) -> str:
    """Преобразует HTML в Markdown"""
    if not text:
        return text
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
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
    'ensure_full_width',
    'split_long_message',
    'format_profile_text',
    'format_psychologist_text',
    'strip_html',
    'html_to_markdown'
]
