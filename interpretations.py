#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔮 ТАЙНЫЙ ШЁПОТ: Объединённые интерпретации v1.0
336 стратегий (168 мужских + 168 женских)
Формат: детство / идентичность / окружение (от 2-го лица)
"""

import logging
from male_interpretations import MALE_STRATEGIES
from female_interpretations import FEMALE_STRATEGIES

# ==================== НАЗВАНИЯ НАРРАТИВОВ ====================

NARRATIVE_NAMES = {
    "СБ": "СИЛЫ",
    "ТФ": "ТРУДА", 
    "УБ": "ЗНАНИЙ",
    "ЧВ": "ВНИМАНИЯ"
}

# Настройка логирования
logger = logging.getLogger(__name__)

# ==================== ПРОВЕРКА ЗАГРУЗКИ ====================

try:
    male_count = len(MALE_STRATEGIES)
    female_count = len(FEMALE_STRATEGIES)
    total_count = male_count + female_count
    
    print("\n" + "="*50)
    print("🔍 ПРОВЕРКА ЗАГРУЗКИ ИНТЕРПРЕТАЦИЙ")
    print("="*50)
    print(f"✅ Загружено мужских стратегий: {male_count}")
    print(f"✅ Загружено женских стратегий: {female_count}")
    print(f"✅ ВСЕГО стратегий: {total_count}")
    
    # Показываем примеры женских ключей
    if female_count > 0:
        female_keys = list(FEMALE_STRATEGIES.keys())
        print(f"\n👩‍🦰 ПРИМЕРЫ ЖЕНСКИХ КЛЮЧЕЙ (первые 10):")
        for i, key in enumerate(female_keys[:10]):
            print(f"  {i+1}. {key}")
        
        # Проверяем наличие всех основных комбинаций
        print(f"\n📊 ПРОВЕРКА ОСНОВНЫХ КОМБИНАЦИЙ ДЛЯ ЖЕНЩИН:")
        narratives = ["СБ", "ТФ", "УБ", "ЧВ"]
        levels = [1, 2, 3, 4, 5, 6]
        programs = ["F1", "F2", "F3", "F4", "F5", "F6"]
        
        for n in narratives:
            for l in levels:
                key = f"{n}_{l}_F3"  # Проверяем для F3
                if key in FEMALE_STRATEGIES:
                    print(f"  ✅ {key} - найдена")
                else:
                    print(f"  ❌ {key} - НЕ найдена")
    else:
        print("❌ ЖЕНСКИЕ СТРАТЕГИИ НЕ ЗАГРУЖЕНЫ!")
    
    print("="*50 + "\n")
    
except Exception as e:
    print(f"❌ Ошибка при проверке стратегий: {e}")
    male_count = 0
    female_count = 0
    total_count = 0

logger.info(f"✅ Загружено мужских стратегий: {male_count}")
logger.info(f"✅ Загружено женских стратегий: {female_count}")
logger.info(f"✅ ВСЕГО стратегий: {total_count}")

# ==================== ФУНКЦИИ ПОЛУЧЕНИЯ ИНТЕРПРЕТАЦИЙ ====================

def get_interpretation(gender, narrative, level, age, program, second_narrative=None, third_narrative=None):
    """
    Универсальная функция для получения интерпретации
    
    Параметры:
    - gender: "М" или "Ж"
    - narrative: основной нарратив (СБ, ТФ, УБ, ЧВ)
    - level: уровень 1-6
    - age: возраст (не используется в текущей версии)
    - program: древняя программа (F1-F6)
    - second_narrative: второй нарратив (если есть)
    - third_narrative: третий нарратив (если есть)
    
    Возвращает:
    - словарь с ключами: детство, идентичность, окружение
    """
    
    # Формируем ключ в зависимости от наличия дополнительных нарративов
    if second_narrative and third_narrative and second_narrative != third_narrative:
        # Тройной нарратив (все три разные)
        key = f"{narrative}-{second_narrative}-{third_narrative}_{level}_{program}"
    elif second_narrative and second_narrative != narrative:
        # Двойной нарратив (два разных)
        key = f"{narrative}-{second_narrative}_{level}_{program}"
    else:
        # Чистый нарратив
        key = f"{narrative}_{level}_{program}"
    
    # Выбираем нужный словарь по полу
    if gender == "Ж":
        strategies = FEMALE_STRATEGIES
        gender_text = "женская"
        default_narrative = "ЧВ"  # Для женщин дефолтный нарратив
    else:
        strategies = MALE_STRATEGIES
        gender_text = "мужская"
        default_narrative = "СБ"  # Для мужчин дефолтный нарратив
    
    # === ОТЛАДКА ===
    debug_info = f"""
🔍 ПОИСК ИНТЕРПРЕТАЦИИ:
  gender: {gender}
  narrative: {narrative}
  level: {level}
  program: {program}
  second: {second_narrative}
  third: {third_narrative}
  сформированный ключ: '{key}'
"""
    print(debug_info)
    logger.debug(debug_info)
    
    # Ищем стратегию по сформированному ключу
    strategy = strategies.get(key)
    
    if strategy:
        print(f"  ✅ НАЙДЕНА {gender_text} стратегия: {key}")
        logger.info(f"✅ Найдена {gender_text} стратегия: {key}")
        return strategy
    
    # Если не нашли по точному ключу, пробуем найти похожую
    print(f"  ❌ Точный ключ '{key}' не найден, ищем альтернативы...")
    
    # Пробуем найти стратегию без учета program (если program не важен)
    base_key = f"{narrative}_{level}"
    alternative_keys = [k for k in strategies.keys() if k.startswith(base_key)]
    
    if alternative_keys:
        found_key = alternative_keys[0]
        strategy = strategies.get(found_key)
        print(f"  ✅ Найдена альтернатива: {found_key}")
        logger.info(f"✅ Найдена альтернативная {gender_text} стратегия: {found_key}")
        return strategy
    
    # Если всё еще не нашли, пробуем с другим уровнем
    alternative_level = 3  # Средний уровень как запасной
    base_key = f"{narrative}_{alternative_level}"
    alternative_keys = [k for k in strategies.keys() if k.startswith(base_key)]
    
    if alternative_keys:
        found_key = alternative_keys[0]
        strategy = strategies.get(found_key)
        print(f"  ✅ Найдена альтернатива с уровнем {alternative_level}: {found_key}")
        logger.info(f"✅ Найдена альтернативная {gender_text} стратегия: {found_key}")
        return strategy
    
    # Если совсем ничего не нашли, используем дефолт
    print(f"  ❌ НИЧЕГО НЕ НАЙДЕНО! Использую заглушку")
    logger.warning(f"⚠️ {gender_text} стратегия не найдена: {key}")
    
    # Заглушка на случай полного отсутствия
    if gender == "Ж":
        return {
            "детство": "Твоё детство было особенным. Ты росла в мире, где не было готовых ответов, и это сделало тебя сильнее.",
            "идентичность": "Ты — та, кто ищет свой путь, не оглядываясь на других. Твоя уникальность — в твоей способности создавать себя заново каждый день.",
            "окружение": "Твой мир — это пространство твоих возможностей. Где бы ты ни была, ты создаёшь вокруг себя место силы."
        }
    else:
        return {
            "детство": "Твоё детство было особенным. Ты рос в мире, где не было готовых ответов, и это сделало тебя сильнее.",
            "идентичность": "Ты — тот, кто ищет свой путь, не оглядываясь на других. Твоя уникальность — в твоей способности создавать себя заново каждый день.",
            "окружение": "Твой мир — это пространство твоих возможностей. Где бы ты ни был, ты создаёшь вокруг себя место силы."
        }

def get_male_interpretation(narrative, level, program, second_narrative=None, third_narrative=None):
    """Для обратной совместимости - мужские интерпретации"""
    return get_interpretation(
        gender="М",
        narrative=narrative,
        level=level,
        age=0,
        program=program,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )

def get_female_interpretation(narrative, level, program, second_narrative=None, third_narrative=None):
    """Для удобного вызова женских интерпретаций"""
    return get_interpretation(
        gender="Ж",
        narrative=narrative,
        level=level,
        age=0,
        program=program,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )

# ==================== ПРОВЕРОЧНАЯ ФУНКЦИЯ ====================

def test_female_strategies():
    """Тестирует наличие всех основных женских стратегий"""
    print("\n" + "="*50)
    print("🧪 ТЕСТИРОВАНИЕ ЖЕНСКИХ СТРАТЕГИЙ")
    print("="*50)
    
    narratives = ["СБ", "ТФ", "УБ", "ЧВ"]
    levels = [1, 2, 3, 4, 5, 6]
    programs = ["F1", "F2", "F3", "F4", "F5", "F6"]
    
    total_tests = 0
    passed_tests = 0
    
    for n in narratives:
        print(f"\n📌 Нарратив {NARRATIVE_NAMES[n]} ({n}):")
        for l in levels:
            for p in programs:
                key = f"{n}_{l}_{p}"
                total_tests += 1
                if key in FEMALE_STRATEGIES:
                    print(f"  ✅ {key} - найдена")
                    passed_tests += 1
                else:
                    print(f"  ❌ {key} - НЕ найдена")
    
    print(f"\n📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"  Всего тестов: {total_tests}")
    print(f"  Успешно: {passed_tests}")
    print(f"  Провалено: {total_tests - passed_tests}")
    print(f"  Процент покрытия: {(passed_tests/total_tests)*100:.1f}%")
    print("="*50 + "\n")

# Запускаем тест при импорте (можно закомментировать, если не нужно)
# test_female_strategies()

# ==================== ЭКСПОРТ ====================

__all__ = [
    'NARRATIVE_NAMES', 
    'get_interpretation', 
    'get_male_interpretation', 
    'get_female_interpretation',
    'MALE_STRATEGIES', 
    'FEMALE_STRATEGIES',
    'test_female_strategies'
]
