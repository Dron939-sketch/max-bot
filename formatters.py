#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для форматирования текста
Содержит функции для форматирования текста, прогресс-баров и очистки
"""

import re
from typing import List


def bold(text: str) -> str:
    """Жирный текст (HTML)"""
    if not text:
        return ""
    return f"<b>{text}</b>"


def italic(text: str) -> str:
    """Курсив (HTML)"""
    if not text:
        return ""
    return f"<i>{text}</i>"


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
    """Полностью очищает текст для безопасного отображения"""
    if not text:
        return text
    
    # Удаляем все возможные форматирования (Markdown)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Удаляем HTML-теги
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
    
    return parts


def format_profile_text(text: str) -> str:
    """Форматирует текст профиля с жирными заголовками и эмодзи, убирает дубли"""
    if not text:
        return text
    
    text = clean_text_for_safe_display(text)
    
    header_map = [
        (r'БЛОК\s*1:?\s*', '🔑 КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА'),
        (r'БЛОК\s*2:?\s*', '💪 СИЛЬНЫЕ СТОРОНЫ'),
        (r'БЛОК\s*3:?\s*', '🎯 ЗОНЫ РОСТА'),
        (r'БЛОК\s*4:?\s*', '🌱 КАК ЭТО СФОРМИРОВАЛОСЬ'),
        (r'БЛОК\s*5:?\s*', '⚠️ ГЛАВНАЯ ЛОВУШКА'),
    ]
    
    for pattern, replacement in header_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    for _, header in header_map:
        pattern = rf'({re.escape(header)})\s*\n\s*{re.escape(header)}'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
    
    for _, header in header_map:
        text = re.sub(rf'({re.escape(header)})', rf'{bold(header)}', text, flags=re.IGNORECASE)
    
    return text


def format_psychologist_text(text: str, user_name: str = "") -> str:
    """Форматирует мысли психолога с жирными заголовками и эмодзи"""
    if not text:
        return text
    
    text = clean_text_for_safe_display(text)
    text = re.sub(r'###\s*\d+\.?\s*', '', text)
    
    if user_name and not text.lower().startswith(user_name.lower()):
        first_word = text.split()[0] if text else ""
        if first_word and first_word.lower() not in ['здравствуйте', 'привет', 'добрый']:
            text = f"{user_name}, " + text[0].lower() + text[1:] if text else text
    
    header_map = [
        (r'КЛЮЧЕВОЙ\s*ЭЛЕМЕНТ', '🔐 КЛЮЧЕВОЙ ЭЛЕМЕНТ'),
        (r'ПЕТЛЯ', '🔄 ПЕТЛЯ'),
        (r'ТОЧКА\s*ВХОДА', '🚪 ТОЧКА ВХОДА'),
        (r'ПРОГНОЗ', '📊 ПРОГНОЗ'),
    ]
    
    for pattern, replacement in header_map:
        text = re.sub(rf'({pattern})', rf'{bold(replacement)}', text, flags=re.IGNORECASE)
    
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
    'strip_html'
]
