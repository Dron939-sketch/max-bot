"""
Модуль для форматирования текста
"""
import re

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
