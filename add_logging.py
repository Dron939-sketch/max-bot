#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления логирования в хэндлеры MAX-бота
Запуск: python add_logging_max.py
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

def add_logging_to_handler(filepath):
    """Добавляет логирование в файл-хэндлер"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Добавляем импорт logging, если его нет
    if 'import logging' not in content:
        content = 'import logging\n' + content
        logger_name = os.path.basename(filepath).replace('.py', '')
        content = content.replace('import logging', f'import logging\n\nlogger = logging.getLogger(__name__)')
    
    # Добавляем логирование в функции-обработчики
    pattern = r'(@(?:bot\.message_handler|bot\.callback_query_handler).*?\n)(\s*def .*?\(.*?\):)'
    
    def add_logging(match):
        decorator = match.group(1)
        func_def = match.group(2)
        
        # Извлекаем имя функции и параметры
        func_name = re.search(r'def (\w+)\(', func_def).group(1)
        
        # Добавляем логирование в начало функции
        log_line = f'\n    # 🔍 ЛОГИРОВАНИЕ\n    logger.info(f"🟢 [{func_name}] Вызван обработчик")\n'
        
        return decorator + func_def + log_line
    
    content = re.sub(pattern, add_logging, content, flags=re.MULTILINE)
    
    return content

def main():
    """Главная функция"""
    
    handlers_dir = 'handlers'
    
    if not os.path.exists(handlers_dir):
        print(f"❌ Папка {handlers_dir} не найдена!")
        return
    
    # Создаем резервную копию всей папки
    backup_name = f"{handlers_dir}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(handlers_dir, backup_name)
    print(f"✅ Создана резервная копия: {backup_name}")
    
    # Обрабатываем каждый .py файл в папке
    for filename in os.listdir(handlers_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(handlers_dir, filename)
            print(f"📝 Обрабатываю: {filename}")
            
            original_content = open(filepath, 'r', encoding='utf-8').read()
            modified_content = add_logging_to_handler(filepath)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            print(f"   ✅ Логирование добавлено")
    
    print(f"\n🎉 Логирование успешно добавлено во все хэндлеры!")

if __name__ == "__main__":
    main()
