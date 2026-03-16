#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматического добавления логирования в bot3.py
Запуск: python add_logging.py
"""

import re
import os
import shutil
from datetime import datetime

def backup_file(filename):
    """Создает резервную копию файла"""
    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filename, backup_name)
    print(f"✅ Создана резервная копия: {backup_name}")
    return backup_name

def add_logging_to_safe_send_message(content):
    """Добавляет логирование в функцию safe_send_message"""
    
    # Паттерн для поиска начала функции safe_send_message
    pattern = r'(async def safe_send_message\(.*?\).*?)(?=\n\s*#|\n\s*def|\n\s*async def|\n\s*$)'
    
    # Код для вставки после докстринга
    log_code = """
    
    # 🔍 ЛОГИРОВАНИЕ КНОПОК
    if reply_markup:
        button_texts = []
        for row in reply_markup.inline_keyboard:
            for btn in row:
                button_texts.append(f"{btn.text}[{btn.callback_data}]")
        logger.info(f"✅ [safe_send_message] Отправляю с кнопками: {' | '.join(button_texts)}")
    else:
        logger.warning(f"❌ [safe_send_message] Отправляю БЕЗ кнопок")"""
    
    # Вставляем после докстринга
    modified = re.sub(
        r'(async def safe_send_message.*?\):\n\s*""".*?""")',
        r'\1' + log_code,
        content,
        flags=re.DOTALL
    )
    
    return modified

def add_logging_to_show_ai_generated_profile(content):
    """Добавляет логирование в функцию show_ai_generated_profile"""
    
    log_start = """
    # 🔍 ЛОГИРОВАНИЕ
    logger.info(f"🟢 [show_ai_generated_profile] Начинаю показ профиля для пользователя {callback.from_user.id}")
"""
    
    # Добавляем в начало функции
    pattern = r'(async def show_ai_generated_profile.*?:\n)'
    modified = re.sub(pattern, r'\1' + log_start, content)
    
    # Добавляем логирование удаления статусного сообщения
    modified = re.sub(
        r'(if status_msg:\n\s*try:\n\s*await status_msg.delete\(\))',
        r'\1\n            logger.info(f"✅ [show_ai_generated_profile] Статусное сообщение {status_msg.message_id} удалено")',
        modified
    )
    
    # Добавляем логирование создания кнопок
    modified = re.sub(
        r'(keyboard = InlineKeyboardMarkup\(inline_keyboard=\[.*?\]\))',
        r'\1\n    \n    logger.info(f"🔘 [show_ai_generated_profile] Созданы кнопки: МЫСЛИ ПСИХОЛОГА, ВЫБРАТЬ ЦЕЛЬ, ВЫБРАТЬ РЕЖИМ")',
        modified,
        flags=re.DOTALL
    )
    
    return modified

def add_logging_to_show_saved_psychologist_thought(content):
    """Добавляет логирование в функцию show_saved_psychologist_thought"""
    
    log_start = """
    # 🔍 ЛОГИРОВАНИЕ
    logger.info(f"🟢 [show_saved_psychologist_thought] Начинаю показ мыслей психолога")
"""
    
    # Добавляем в начало функции
    pattern = r'(async def show_saved_psychologist_thought.*?:\n)'
    modified = re.sub(pattern, r'\1' + log_start, content)
    
    # Добавляем логирование создания кнопок
    modified = re.sub(
        r'(keyboard = InlineKeyboardMarkup\(inline_keyboard=\[.*?\]\))',
        r'\1\n    \n    logger.info(f"🔘 [show_saved_psychologist_thought] Созданы кнопки: ВЫБРАТЬ ЦЕЛЬ, ВЫБРАТЬ РЕЖИМ")',
        modified,
        flags=re.DOTALL
    )
    
    return modified

def add_logging_to_show_final_profile(content):
    """Добавляет логирование в функцию show_final_profile"""
    
    log_start = """
    # 🔍 ЛОГИРОВАНИЕ
    logger.info(f"🟢 [show_final_profile] Начинаю показ финального профиля для пользователя {user_id}")
"""
    
    # Добавляем в начало функции
    pattern = r'(async def show_final_profile.*?:\n)'
    modified = re.sub(pattern, r'\1' + log_start, content)
    
    # Добавляем логирование отправки статусного сообщения
    modified = re.sub(
        r'(status_msg = await callback\.message\.answer\(.*?\))',
        r'\1\n    logger.info(f"📊 [show_final_profile] Статусное сообщение отправлено, ID: {status_msg.message_id}")',
        modified
    )
    
    # Добавляем логирование генерации профиля
    modified = re.sub(
        r'(ai_profile = await generate_ai_profile\(user_id, data\))',
        r'\1\n    logger.info(f"✅ [show_final_profile] AI-профиль сгенерирован: {len(ai_profile) if ai_profile else 0} символов")',
        modified
    )
    
    return modified

def add_logging_to_callback_handler(content):
    """Добавляет логирование в callback_handler"""
    
    # Добавляем логирование в начало
    pattern = r'(async def callback_handler.*?:\n\s*await callback\.answer\(\))'
    log_line = '\n    logger.info(f"🔔 [callback_handler] Получен callback: {data} от пользователя {callback.from_user.id}")\n'
    modified = re.sub(pattern, r'\1' + log_line, content)
    
    # Добавляем логирование ошибок
    modified = re.sub(
        r'(except TelegramBadRequest as e:\n\s*if "message is not modified" in str\(e\).lower\(\):\n\s*# Игнорируем - сообщение уже такое же\n\s*logger\.debug\("Message not modified, ignoring"\))',
        r'\1\n        else:\n            logger.error(f"❌ [callback_handler] TelegramBadRequest: {e}")',
        modified
    )
    
    modified = re.sub(
        r'(except Exception as e:\n\s*logger\.error\(f"Unexpected error in callback_handler: {e}"\))',
        r'\1\n        logger.error(f"❌ [callback_handler] Неожиданная ошибка: {e}")',
        modified
    )
    
    return modified

def main():
    """Главная функция"""
    
    filename = 'bot3.py'
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        alt = input("Введите имя файла: ").strip()
        if alt and os.path.exists(alt):
            filename = alt
        else:
            return
    
    # Создаем резервную копию
    backup_file(filename)
    
    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_length = len(content)
    
    # Применяем все изменения
    content = add_logging_to_safe_send_message(content)
    content = add_logging_to_show_ai_generated_profile(content)
    content = add_logging_to_show_saved_psychologist_thought(content)
    content = add_logging_to_show_final_profile(content)
    content = add_logging_to_callback_handler(content)
    
    new_length = len(content)
    
    # Сохраняем изменения
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 Логирование успешно добавлено в {filename}!")
    print(f"📊 Размер файла: {original_length} → {new_length} символов (+{new_length - original_length})")
    print(f"📦 Резервная копия сохранена")
    print("\n✅ Что добавлено:")
    print("   - Логирование в safe_send_message (отслеживание кнопок)")
    print("   - Логирование в show_ai_generated_profile")
    print("   - Логирование в show_saved_psychologist_thought")
    print("   - Логирование в show_final_profile")
    print("   - Логирование в callback_handler")
    print("\n🚀 Запустите бота и смотрите логи:")
    print("   python bot3.py 2>&1 | tee bot.log")
    print("   tail -f bot.log | grep -E 'safe_send_message|show_ai|show_saved|кнопки|🔘|✅'")

if __name__ == "__main__":
    main()
