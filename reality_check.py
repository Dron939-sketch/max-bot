"""
Модуль проверки реальности целей
Версия 2.0 - ПОЛНЫЙ НАБОР ЦЕЛЕЙ
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================
# ФУНКЦИИ ФОРМАТИРОВАНИЯ
# ============================================

def bold(text: str) -> str:
    """Жирный текст (HTML)"""
    return f"<b>{text}</b>"


# ============================================
# ПАРСИНГ ОТВЕТОВ ПОЛЬЗОВАТЕЛЯ
# ============================================

def parse_life_context_answers(text: str) -> Dict[str, Any]:
    """
    Парсит ответы на вопросы о жизненном контексте
    
    Args:
        text: текст ответа пользователя (обычно 10 строк)
    
    Returns:
        Dict с полями:
        - family_status: семейное положение
        - has_children: есть ли дети (bool)
        - children_info: информация о детях (строка)
        - work_schedule: график работы
        - job_title: должность
        - commute_time: время на дорогу
        - housing_type: тип жилья
        - has_private_space: есть ли отдельное пространство (bool)
        - has_car: есть ли машина (bool)
        - support_people: кто поддерживает
        - resistance_people: кто мешает
        - energy_level: уровень энергии (1-10)
    """
    lines = text.strip().split('\n')
    answers = []
    
    # Очищаем каждую строку от нумерации
    for line in lines:
        # Убираем цифры, эмодзи-цифры и лишние пробелы в начале
        clean = re.sub(r'^[\d️⃣🔟]*\s*', '', line.strip())
        if clean:  # добавляем только непустые строки
            answers.append(clean)
    
    result = {
        'family_status': 'не указано',
        'has_children': False,
        'children_info': '',
        'work_schedule': '',
        'job_title': '',
        'commute_time': '',
        'housing_type': '',
        'has_private_space': False,
        'has_car': False,
        'support_people': '',
        'resistance_people': '',
        'energy_level': 5  # значение по умолчанию
    }
    
    # Заполняем результат, если есть достаточно ответов
    if len(answers) >= 10:
        result['family_status'] = answers[0]
        result['children_info'] = answers[1]
        result['has_children'] = any(word in answers[1].lower() 
                                     for word in ['да', 'есть', 'двое', 'трое', 'ребенок', 'дочь', 'сын'])
        
        result['work_schedule'] = answers[2]
        result['job_title'] = answers[2]  # может быть уточнено позже
        
        result['commute_time'] = answers[3]
        
        result['housing_type'] = answers[4]
        
        result['has_private_space'] = any(word in answers[5].lower() 
                                          for word in ['да', 'есть', 'отдельная', 'своя'])
        
        result['has_car'] = any(word in answers[6].lower() 
                                for word in ['да', 'есть', 'машина'])
        
        result['support_people'] = answers[7] if len(answers) > 7 else ''
        result['resistance_people'] = answers[8] if len(answers) > 8 else ''
        
        # Парсим уровень энергии
        try:
            # Ищем число в строке
            energy_match = re.search(r'(\d+)', answers[9])
            if energy_match:
                result['energy_level'] = int(energy_match.group(1))
                # Ограничиваем диапазоном 1-10
                result['energy_level'] = max(1, min(10, result['energy_level']))
        except (ValueError, IndexError):
            result['energy_level'] = 5
    
    elif len(answers) >= 5:
        # Если ответов меньше, пытаемся извлечь хоть что-то
        for i, answer in enumerate(answers):
            if 'энерги' in answer.lower() or 'оцени' in answer.lower():
                try:
                    energy_match = re.search(r'(\d+)', answer)
                    if energy_match:
                        result['energy_level'] = int(energy_match.group(1))
                        result['energy_level'] = max(1, min(10, result['energy_level']))
                except Exception:
                    pass
            
            if 'комнат' in answer.lower() or 'пространств' in answer.lower():
                result['has_private_space'] = any(word in answer.lower() 
                                                  for word in ['да', 'есть', 'отдельная'])
            
            if 'машин' in answer.lower():
                result['has_car'] = any(word in answer.lower() 
                                        for word in ['да', 'есть'])
    
    return result


def parse_goal_context_answers(text: str) -> Dict[str, Any]:
    """
    Парсит ответы на вопросы о целевом контексте
    
    Args:
        text: текст ответа пользователя
    
    Returns:
        Dict с полями:
        - time_per_week: часов в неделю
        - budget: бюджет в рублях
        - raw_answers: сырые ответы
        - has_equipment: есть ли оборудование
        - equipment_needed: нужное оборудование
        - timeline_preference: предпочтения по срокам
    """
    result = {
        'time_per_week': 5,  # значение по умолчанию
        'budget': 0,
        'has_equipment': False,
        'equipment_needed': '',
        'timeline_preference': 'medium',  # fast/medium/slow
        'raw_answers': text
    }
    
    # Ищем время (часы в неделю)
    time_patterns = [
        r'(\d+)\s*часов',
        r'(\d+)\s*ч',
        r'(\d+)\s*час',
        r'(\d+)\s*в неделю'
    ]
    
    for pattern in time_patterns:
        time_match = re.search(pattern, text, re.IGNORECASE)
        if time_match:
            try:
                hours = int(time_match.group(1))
                # Реалистичные границы: 1-168 часов в неделю
                result['time_per_week'] = max(1, min(168, hours))
                break
            except Exception:
                pass
    
    # Если не нашли по паттернам, ищем любое число, похожее на часы
    if result['time_per_week'] == 5:  # если не нашли
        numbers = re.findall(r'(\d+)', text)
        for num in numbers:
            try:
                val = int(num)
                if 1 <= val <= 168:
                    result['time_per_week'] = val
                    break
            except Exception:
                pass
    
    # Ищем бюджет
    budget_patterns = [
        r'(\d+)\s*тыс',
        r'(\d+)\s*000',
        r'(\d+)\s*руб',
        r'(\d+)\s*₽'
    ]
    
    for pattern in budget_patterns:
        budget_match = re.search(pattern, text, re.IGNORECASE)
        if budget_match:
            try:
                amount = int(budget_match.group(1))
                if 'тыс' in pattern:
                    result['budget'] = amount * 1000
                else:
                    result['budget'] = amount
                break
            except Exception:
                pass
    
    # Ищем упоминания оборудования
    equipment_keywords = ['нужн', 'оборуд', 'инструм', 'компьютер', 'ноутбук', 'программ']
    for keyword in equipment_keywords:
        if keyword in text.lower():
            result['has_equipment'] = True
            # Пробуем извлечь что именно нужно
            sentences = text.split('.')
            for sent in sentences:
                if keyword in sent.lower():
                    result['equipment_needed'] = sent.strip()
                    break
            break
    
    # Определяем предпочтения по срокам
    if any(word in text.lower() for word in ['быстр', 'срочн', 'скоре']):
        result['timeline_preference'] = 'fast'
    elif any(word in text.lower() for word in ['нетороп', 'постепен', 'долгосрочн']):
        result['timeline_preference'] = 'slow'
    else:
        result['timeline_preference'] = 'medium'
    
    return result


# ============================================
# ТЕОРЕТИЧЕСКИЕ ПУТИ К ЦЕЛЯМ (ПОЛНЫЙ НАБОР)
# ============================================

def get_theoretical_path(goal_id: str, mode: str) -> Dict[str, Any]:
    """
    Возвращает теоретический путь к цели
    
    Args:
        goal_id: идентификатор цели
        mode: режим (coach/psychologist/trainer)
    
    Returns:
        Dict с полями:
        - time_total: общее время в часах
        - time_per_week: часов в неделю
        - duration_weeks: длительность в неделях
        - energy_required: требуемый уровень энергии (1-10)
        - space_required: требуется ли отдельное пространство
        - budget: бюджет в рублях (0 если бесплатно)
        - support_required: требуется ли поддержка
        - steps: список шагов с описанием
        - formatted_text: отформатированный текст для вывода
    """
    paths = {
        # ========== ДЕНЬГИ И ФИНАНСЫ ==========
        "income_growth": {
            "coach": {
                "time_total": 340,
                "time_per_week": 13,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей ситуации и ресурсов",
                    "Постановка конкретных финансовых целей",
                    "Поиск точек роста и возможностей",
                    "Создание плана действий",
                    "Еженедельные сессии для сверки и корректировки"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование денежных убеждений и сценариев",
                    "Проработка страхов и блоков",
                    "Анализ семейных денежных паттернов",
                    "Работа с чувством собственной ценности",
                    "Интеграция нового отношения к деньгам"
                ]
            },
            "trainer": {
                "time_total": 400,
                "time_per_week": 15,
                "duration_weeks": 26,
                "energy_required": 8,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Освоение конкретного навыка (обучение 120ч)",
                    "Практика и отработка (80ч)",
                    "Создание продукта/услуги (60ч)",
                    "Маркетинг и поиск клиентов (80ч)",
                    "Анализ и масштабирование (60ч)"
                ]
            }
        },
        
        "money_blocks": {
            "coach": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Выявление основных ограничений",
                    "Поиск альтернативных путей",
                    "Развитие новых финансовых привычек",
                    "Планирование бюджета",
                    "Регулярная ревизия прогресса"
                ]
            },
            "psychologist": {
                "time_total": 250,
                "time_per_week": 10,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней денежных блоков",
                    "Проработка семейных сценариев",
                    "Работа с чувством вины и стыда",
                    "Формирование новой денежной идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ведение финансового дневника",
                    "Освоение базовых финансовых инструментов",
                    "Создание финансовой подушки",
                    "Автоматизация накоплений",
                    "Анализ расходов"
                ]
            }
        },
        
        "financial_plan": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущих доходов и расходов",
                    "Определение финансовых целей",
                    "Создание бюджета",
                    "Планирование накоплений",
                    "Еженедельный контроль"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование отношения к деньгам",
                    "Проработка страха бедности",
                    "Анализ денежных сценариев",
                    "Формирование здоровых привычек",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ведение финансового дневника",
                    "Освоение инструментов учёта",
                    "Создание финансового плана",
                    "Автоматизация сбережений",
                    "Еженедельный анализ"
                ]
            }
        },
        
        "money_skills": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Оценка текущих финансовых навыков",
                    "Определение зон развития",
                    "Изучение базовых принципов",
                    "Практика управления бюджетом",
                    "Рефлексия и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страхов, связанных с деньгами",
                    "Проработка чувства нехватки",
                    "Работа с самооценкой",
                    "Формирование мышления изобилия",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Обучение основам финансовой грамотности",
                    "Практика составления бюджета",
                    "Освоение инструментов инвестирования",
                    "Создание финансовой подушки",
                    "Автоматизация процессов"
                ]
            }
        },
        
        "income_skills": {
            "coach": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущих источников дохода",
                    "Поиск новых возможностей",
                    "Развитие востребованных навыков",
                    "Создание стратегии роста",
                    "Еженедельный анализ"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование блоков, мешающих росту дохода",
                    "Проработка чувства недостойности",
                    "Работа со страхом успеха",
                    "Формирование новой идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": True,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Обучение навыкам повышения дохода",
                    "Практика переговоров о зарплате",
                    "Развитие дополнительных источников",
                    "Создание личного бренда",
                    "Масштабирование"
                ]
            }
        },
        
        "investment_skills": {
            "coach": {
                "time_total": 250,
                "time_per_week": 10,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение инвестиционных целей",
                    "Изучение базовых принципов",
                    "Анализ инструментов",
                    "Создание стратегии",
                    "Еженедельный анализ"
                ]
            },
            "psychologist": {
                "time_total": 280,
                "time_per_week": 11,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страхов, связанных с риском",
                    "Проработка отношения к деньгам",
                    "Анализ семейных паттернов",
                    "Формирование доверия к процессу",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": True,
                "budget": 10000,
                "support_required": True,
                "steps": [
                    "Обучение основам инвестирования",
                    "Практика с демо-счетом",
                    "Анализ рынка и инструментов",
                    "Создание инвестиционного портфеля",
                    "Мониторинг и корректировка"
                ]
            }
        },
        
        "wealth_building": {
            "coach": {
                "time_total": 300,
                "time_per_week": 12,
                "duration_weeks": 25,
                "energy_required": 8,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ текущего финансового положения",
                    "Определение целей по созданию капитала",
                    "Разработка стратегии",
                    "Поиск источников дохода",
                    "Еженедельный контроль"
                ]
            },
            "psychologist": {
                "time_total": 320,
                "time_per_week": 13,
                "duration_weeks": 25,
                "energy_required": 8,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование отношения к богатству",
                    "Проработка чувства вины",
                    "Анализ семейных сценариев",
                    "Формирование мышления изобилия",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 280,
                "time_per_week": 11,
                "duration_weeks": 25,
                "energy_required": 8,
                "space_required": True,
                "budget": 20000,
                "support_required": True,
                "steps": [
                    "Обучение стратегиям создания капитала",
                    "Практика инвестирования",
                    "Создание нескольких источников дохода",
                    "Оптимизация налогов",
                    "Защита капитала"
                ]
            }
        },
        
        "financial_strategy": {
            "coach": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей финансовой стратегии",
                    "Определение долгосрочных целей",
                    "Разработка новой стратегии",
                    "Планирование этапов",
                    "Еженедельный контроль"
                ]
            },
            "psychologist": {
                "time_total": 240,
                "time_per_week": 10,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страхов, связанных с деньгами",
                    "Проработка ограничивающих убеждений",
                    "Анализ финансовых сценариев",
                    "Формирование новой стратегии",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": True,
                "budget": 15000,
                "support_required": True,
                "steps": [
                    "Обучение стратегическому планированию",
                    "Анализ рынка и возможностей",
                    "Создание финансовой модели",
                    "Разработка дорожной карты",
                    "Мониторинг и корректировка"
                ]
            }
        },
        
        "money_psychology": {
            "coach": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование отношения к деньгам",
                    "Анализ денежных привычек",
                    "Выявление паттернов",
                    "Поиск новых подходов",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ денежных сценариев",
                    "Проработка детских посланий",
                    "Работа с чувством вины и стыда",
                    "Исцеление денежных травм",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика новых денежных привычек",
                    "Ведение дневника отношений с деньгами",
                    "Упражнения на принятие",
                    "Работа с аффирмациями",
                    "Закрепление"
                ]
            }
        },
        
        "worth": {
            "coach": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ самооценки",
                    "Выявление зон неуверенности",
                    "Поиск сильных сторон",
                    "Постановка целей",
                    "Еженедельная рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней низкой самооценки",
                    "Проработка детских травм",
                    "Работа с внутренним критиком",
                    "Формирование здоровой самооценки",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5,
                "duration_weeks": 28,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные практики самопринятия",
                    "Ведение дневника достижений",
                    "Упражнения на уверенность",
                    "Практика публичных выступлений",
                    "Закрепление"
                ]
            }
        },
        
        "scarcity": {
            "coach": {
                "time_total": 170,
                "time_per_week": 7,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ проявлений сценария дефицита",
                    "Выявление триггеров",
                    "Поиск альтернатив",
                    "Практика изобилия",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 210,
                "time_per_week": 8,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней сценария дефицита",
                    "Проработка детских посланий",
                    "Работа со страхом нехватки",
                    "Формирование мышления изобилия",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика благодарности",
                    "Ведение дневника изобилия",
                    "Упражнения на щедрость",
                    "Перепрограммирование привычек",
                    "Закрепление"
                ]
            }
        },
        
        "abundance": {
            "coach": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование текущего мышления",
                    "Выявление ограничений",
                    "Поиск возможностей",
                    "Практика изобилия",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Проработка страха изобилия",
                    "Анализ семейных паттернов",
                    "Работа с чувством вины",
                    "Формирование новой идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные практики изобилия",
                    "Ведение дневника благодарности",
                    "Упражнения на расширение",
                    "Создание новых привычек",
                    "Закрепление"
                ]
            }
        },
        
        "money_freedom": {
            "coach": {
                "time_total": 240,
                "time_per_week": 10,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Определение целей финансовой свободы",
                    "Анализ текущей ситуации",
                    "Разработка стратегии",
                    "Планирование этапов",
                    "Еженедельный контроль"
                ]
            },
            "psychologist": {
                "time_total": 260,
                "time_per_week": 10,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование отношения к свободе",
                    "Проработка страхов",
                    "Анализ ограничений",
                    "Формирование новой идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": True,
                "budget": 25000,
                "support_required": True,
                "steps": [
                    "Обучение стратегиям достижения свободы",
                    "Создание пассивного дохода",
                    "Оптимизация расходов",
                    "Инвестирование",
                    "Мониторинг"
                ]
            }
        },
        
        # ========== ОТНОШЕНИЯ ==========
        "relations": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей ситуации и желаний",
                    "Прояснение критериев и ценностей",
                    "Поиск мест знакомств",
                    "Развитие навыков общения",
                    "Анализ опыта и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование типа привязанности",
                    "Проработка прошлых травм",
                    "Анализ повторяющихся сценариев",
                    "Работа со страхом близости",
                    "Формирование здоровых моделей"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Навыки знакомства и самопрезентации",
                    "Развитие эмпатии и активного слушания",
                    "Навыки ведения свиданий",
                    "Коммуникация в отношениях",
                    "Разрешение конфликтов"
                ]
            }
        },
        
        "attachment": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование паттернов в отношениях",
                    "Анализ повторяющихся сценариев",
                    "Выявление типа привязанности",
                    "Поиск новых моделей",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ типа привязанности",
                    "Проработка детских травм",
                    "Работа со страхом близости",
                    "Формирование надежной привязанности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика новых паттернов",
                    "Упражнения на доверие",
                    "Развитие эмоциональной близости",
                    "Коммуникативные навыки",
                    "Закрепление"
                ]
            }
        },
        
        "attachment_style": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование паттернов в отношениях",
                    "Анализ повторяющихся сценариев",
                    "Выявление типа привязанности",
                    "Поиск новых моделей",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ типа привязанности",
                    "Проработка детских травм",
                    "Работа со страхом близости",
                    "Формирование надежной привязанности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика новых паттернов",
                    "Упражнения на доверие",
                    "Развитие эмоциональной близости",
                    "Коммуникативные навыки",
                    "Закрепление"
                ]
            }
        },
        
        "intimacy": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5,
                "duration_weeks": 28,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страха близости",
                    "Анализ прошлого опыта",
                    "Выявление барьеров",
                    "Постепенное сближение",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ страха близости",
                    "Проработка травм",
                    "Работа с уязвимостью",
                    "Формирование способности к близости",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика открытости",
                    "Упражнения на уязвимость",
                    "Развитие эмпатии",
                    "Навыки глубокого общения",
                    "Закрепление"
                ]
            }
        },
        
        "love": {
            "coach": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование способности любить",
                    "Анализ прошлого опыта",
                    "Выявление блоков",
                    "Развитие любви к себе",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ способности любить",
                    "Проработка детских травм",
                    "Работа с самооценкой",
                    "Формирование здоровой любви",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5,
                "duration_weeks": 28,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практика любви к себе",
                    "Упражнения на принятие",
                    "Развитие эмпатии",
                    "Навыки проявления любви",
                    "Закрепление"
                ]
            }
        },
        
        "communication_skills": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущих навыков общения",
                    "Определение зон роста",
                    "Практика активного слушания",
                    "Развитие уверенности",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страхов в общении",
                    "Проработка социальной тревоги",
                    "Анализ коммуникативных паттернов",
                    "Формирование новых моделей",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники эффективной коммуникации",
                    "Практика публичных выступлений",
                    "Навыки убеждения",
                    "Невербальное общение",
                    "Отработка в реальных ситуациях"
                ]
            }
        },
        
        "negotiation": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущих навыков",
                    "Изучение основ переговоров",
                    "Практика в безопасной среде",
                    "Анализ результатов",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страха конфликтов",
                    "Проработка неуверенности",
                    "Анализ паттернов в переговорах",
                    "Формирование уверенности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 3000,
                "support_required": False,
                "steps": [
                    "Изучение стратегий переговоров",
                    "Практика с кейсами",
                    "Ролевые игры",
                    "Анализ реальных ситуаций",
                    "Отработка навыков"
                ]
            }
        },
        
        "influence": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего влияния",
                    "Изучение принципов",
                    "Практика",
                    "Анализ результатов",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страха влияния",
                    "Проработка ответственности",
                    "Анализ этических аспектов",
                    "Формирование здорового влияния",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Техники убеждения",
                    "Практика харизмы",
                    "Развитие авторитета",
                    "Нетворкинг",
                    "Отработка навыков"
                ]
            }
        },
        
        "empathy": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего уровня эмпатии",
                    "Практика активного слушания",
                    "Развитие понимания",
                    "Рефлексия",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование блоков эмпатии",
                    "Проработка эмоциональных травм",
                    "Развитие эмоционального интеллекта",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Упражнения на эмпатию",
                    "Практика в общении",
                    "Развитие эмоционального слуха",
                    "Отработка навыков",
                    "Закрепление"
                ]
            }
        },
        
        "community": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Определение целей сообщества",
                    "Поиск единомышленников",
                    "Создание площадки",
                    "Развитие активности",
                    "Анализ и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 170,
                "time_per_week": 7,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование страха сообщества",
                    "Проработка опыта",
                    "Развитие доверия",
                    "Формирование принадлежности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 10000,
                "support_required": True,
                "steps": [
                    "Стратегии создания сообщества",
                    "Навыки фасилитации",
                    "Модерация и управление",
                    "Мероприятия и события",
                    "Масштабирование"
                ]
            }
        },
        
        "team_building": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ текущей команды",
                    "Определение целей",
                    "Планирование активностей",
                    "Проведение мероприятий",
                    "Анализ результатов"
                ]
            },
            "psychologist": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование динамики команды",
                    "Проработка конфликтов",
                    "Развитие доверия",
                    "Укрепление связей",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 15000,
                "support_required": True,
                "steps": [
                    "Методики тимбилдинга",
                    "Практика упражнений",
                    "Фасилитация командных сессий",
                    "Разрешение конфликтов",
                    "Оценка эффективности"
                ]
            }
        },
        
        # ========== СТРАХИ И ТРЕВОГА ==========
        "fear_work": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение основных страхов",
                    "Анализ их причин",
                    "Постановка маленьких целей",
                    "Практика преодоления",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней страхов",
                    "Проработка травм",
                    "Работа с защитами",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники работы со страхом",
                    "Ежедневные упражнения",
                    "Экспозиционная терапия",
                    "Закрепление результатов",
                    "Поддержка"
                ]
            }
        },
        
        "fear_origin": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страхов",
                    "Поиск их источников",
                    "Анализ связей",
                    "Понимание причин",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ происхождения страхов",
                    "Проработка детских травм",
                    "Работа с семейными сценариями",
                    "Интеграция",
                    "Исцеление"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники отслеживания страхов",
                    "Дневник страхов",
                    "Практики осознанности",
                    "Работа с триггерами",
                    "Закрепление"
                ]
            }
        },
        
        "anxiety_reduce": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение триггеров тревоги",
                    "Поиск ресурсных состояний",
                    "Постановка маленьких целей",
                    "Отслеживание прогресса",
                    "Закрепление новых состояний"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корневых причин тревоги",
                    "Проработка детских травм",
                    "Работа с защитными механизмами",
                    "Интеграция теневых частей",
                    "Формирование базового чувства безопасности"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные дыхательные практики (15 мин)",
                    "Техники заземления",
                    "Когнитивные упражнения",
                    "Телесные практики",
                    "Ведение дневника состояний"
                ]
            }
        },
        
        "calm": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение источников беспокойства",
                    "Поиск ресурсных состояний",
                    "Практика спокойствия",
                    "Отслеживание прогресса",
                    "Закрепление"
                ]
            },
            "psychologist": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск причин беспокойства",
                    "Проработка травм",
                    "Работа с гиперконтролем",
                    "Формирование спокойствия",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 70,
                "time_per_week": 3,
                "duration_weeks": 23,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Медитативные практики",
                    "Дыхательные техники",
                    "Релаксация",
                    "Mindfulness",
                    "Ежедневная практика"
                ]
            }
        },
        
        "safety": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ чувства безопасности",
                    "Выявление угроз",
                    "Создание безопасной среды",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней небезопасности",
                    "Проработка травм",
                    "Работа с базовым доверием",
                    "Формирование безопасности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники заземления",
                    "Практики безопасности",
                    "Создание ритуалов",
                    "Укрепление границ",
                    "Закрепление"
                ]
            }
        },
        
        # ========== ЭНЕРГИЯ ==========
        "energy_boost": {
            "coach": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего образа жизни",
                    "Определение точек утечки энергии",
                    "Поиск ресурсных активностей",
                    "Планирование изменений",
                    "Отслеживание динамики"
                ]
            },
            "psychologist": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование психосоматических связей",
                    "Проработка подавленных эмоций",
                    "Работа с внутренними конфликтами",
                    "Выявление вторичных выгод упадка сил",
                    "Интеграция новой энергии"
                ]
            },
            "trainer": {
                "time_total": 50,
                "time_per_week": 2,
                "duration_weeks": 24,
                "energy_required": 3,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Режим сна (настройка)",
                    "Коррекция питания",
                    "Физическая активность 3 раза в неделю",
                    "Энергетические практики 15 мин в день",
                    "Отслеживание показателей"
                ]
            }
        },
        
        # ========== САМОПОЗНАНИЕ И РАЗВИТИЕ ==========
        "purpose": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ценностей и интересов",
                    "Анализ прошлого опыта",
                    "Поиск точек вдохновения",
                    "Формулировка гипотез",
                    "Тестирование и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование детских мечтаний",
                    "Анализ запретов и долженствований",
                    "Работа с самооценкой",
                    "Поиск уникальности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Тестирование разных активностей",
                    "Ведение дневника",
                    "Обучение новым навыкам",
                    "Нетворкинг",
                    "Создание проекта"
                ]
            }
        },
        
        "meaning": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ценностей",
                    "Анализ значимых моментов",
                    "Поиск смыслов",
                    "Рефлексия",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Экзистенциальный анализ",
                    "Проработка страха смерти",
                    "Поиск уникальности",
                    "Формирование смыслов",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики осознанности",
                    "Ведение дневника смыслов",
                    "Создание проектов",
                    "Волонтерство",
                    "Рефлексия"
                ]
            }
        },
        
        "meaning_deep": {
            "coach": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинное исследование ценностей",
                    "Анализ жизненных этапов",
                    "Поиск экзистенциальных смыслов",
                    "Рефлексия",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 8.5,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Экзистенциальная терапия",
                    "Проработка кризисов",
                    "Работа со свободой и ответственностью",
                    "Поиск подлинности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Философские практики",
                    "Медитации",
                    "Творческие проекты",
                    "Рефлексивные практики",
                    "Закрепление"
                ]
            }
        },
        
        "self_discovery": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование себя",
                    "Анализ интересов",
                    "Поиск талантов",
                    "Рефлексия",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 170,
                "time_per_week": 6.5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ личности",
                    "Работа с тенью",
                    "Интеграция частей",
                    "Самопринятие",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики самопознания",
                    "Ведение дневника",
                    "Тестирование активностей",
                    "Рефлексия",
                    "Закрепление"
                ]
            }
        },
        
        "integration": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ разных аспектов себя",
                    "Выявление противоречий",
                    "Поиск целостности",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 190,
                "time_per_week": 7.5,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Работа с теневыми частями",
                    "Интеграция субличностей",
                    "Исцеление расколов",
                    "Формирование целостности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики целостности",
                    "Телесные практики",
                    "Творческое выражение",
                    "Рефлексия",
                    "Закрепление"
                ]
            }
        },
        
        "integration_deep": {
            "coach": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Глубинный анализ личности",
                    "Выявление конфликтов",
                    "Поиск целостности",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 8.5,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Юнгианский анализ",
                    "Работа с архетипами",
                    "Интеграция тени",
                    "Индивидуация",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Продвинутые практики",
                    "Ритуалы интеграции",
                    "Творческие проекты",
                    "Менторство",
                    "Закрепление"
                ]
            }
        },
        
        "wisdom": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ жизненного опыта",
                    "Извлечение уроков",
                    "Развитие понимания",
                    "Рефлексия",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 170,
                "time_per_week": 6.5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинная рефлексия",
                    "Работа с жизненными уроками",
                    "Развитие мудрости",
                    "Интеграция",
                    "Передача опыта"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики рефлексии",
                    "Ведение дневника мудрости",
                    "Медитации",
                    "Наставничество",
                    "Закрепление"
                ]
            }
        },
        
        "wisdom_deep": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Глубинный анализ опыта",
                    "Извлечение мудрости",
                    "Применение в жизни",
                    "Рефлексия",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Трансперсональный подход",
                    "Работа с мудростью веков",
                    "Интеграция духовного опыта",
                    "Мудрость тела",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики созерцания",
                    "Изучение философии",
                    "Менторство",
                    "Передача мудрости",
                    "Закрепление"
                ]
            }
        },
        
        "self_esteem": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ сильных сторон",
                    "Постановка достижимых целей",
                    "Фиксация успехов",
                    "Работа с внутренним критиком",
                    "Развитие самопринятия"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней низкой самооценки",
                    "Проработка детских посланий",
                    "Интеграция теневых частей",
                    "Формирование новой идентичности",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные аффирмации",
                    "Практики самопрезентации",
                    "Ведение дневника достижений",
                    "Телесные практики уверенности",
                    "Публичные выступления"
                ]
            }
        },
        
        "healing": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознание ран",
                    "Принятие",
                    "Поиск ресурсов",
                    "Исцеление",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Терапия травмы",
                    "Работа с внутренним ребенком",
                    "Исцеление привязанности",
                    "Интеграция",
                    "Посттравматический рост"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Телесные практики",
                    "Дыхательные техники",
                    "Творческое выражение",
                    "Поддерживающие ритуалы",
                    "Закрепление"
                ]
            }
        },
        
        "inner_child": {
            "coach": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Знакомство с внутренним ребенком",
                    "Выявление его потребностей",
                    "Диалог",
                    "Забота",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исцеление детских травм",
                    "Репарентинг",
                    "Работа с привязанностью",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Игровые практики",
                    "Творчество",
                    "Забота о себе",
                    "Радость и спонтанность",
                    "Закрепление"
                ]
            }
        },
        
        "family_system": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ семейной системы",
                    "Выявление паттернов",
                    "Понимание ролей",
                    "Поиск изменений",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 190,
                "time_per_week": 7.5,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Системная терапия",
                    "Работа с семейными сценариями",
                    "Освобождение от лояльностей",
                    "Интеграция",
                    "Новые паттерны"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики дифференциации",
                    "Установление границ",
                    "Коммуникативные навыки",
                    "Семейные ритуалы",
                    "Закрепление"
                ]
            }
        },
        
        "trauma": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Осознание травмы",
                    "Создание безопасности",
                    "Поиск ресурсов",
                    "Постепенная проработка",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 250,
                "time_per_week": 10,
                "duration_weeks": 25,
                "energy_required": 8,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Терапия травмы (EMDR, соматика)",
                    "Работа с телом",
                    "Регуляция нервной системы",
                    "Интеграция",
                    "Посттравматический рост"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Телесные практики",
                    "Дыхательные техники",
                    "Заземление",
                    "Регуляция",
                    "Поддержка"
                ]
            }
        },
        
        "core_beliefs": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Выявление убеждений",
                    "Анализ их влияния",
                    "Поиск альтернатив",
                    "Тестирование",
                    "Интеграция"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Когнитивная терапия",
                    "Поиск корней убеждений",
                    "Проработка",
                    "Формирование новых",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики осознанности",
                    "Аффирмации",
                    "Дневник мыслей",
                    "Поведенческие эксперименты",
                    "Закрепление"
                ]
            }
        },
        
        "schemas": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Выявление жизненных сценариев",
                    "Анализ повторений",
                    "Понимание паттернов",
                    "Поиск изменений",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Схема-терапия",
                    "Работа с ранними дезадаптивными схемами",
                    "Репарентинг",
                    "Изменение паттернов",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики новых реакций",
                    "Поведенческие эксперименты",
                    "Дневник сценариев",
                    "Ролевые игры",
                    "Закрепление"
                ]
            }
        },
        
        "resilience": {
            "coach": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ стрессоустойчивости",
                    "Поиск ресурсов",
                    "Развитие навыков",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Укрепление психологической устойчивости",
                    "Работа с травмами",
                    "Развитие адаптивности",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Стресс-менеджмент",
                    "Техники саморегуляции",
                    "Физическая выносливость",
                    "Практики восстановления",
                    "Закрепление"
                ]
            }
        },
        
        "protection": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ защитных механизмов",
                    "Осознание",
                    "Поиск альтернатив",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Психоанализ защит",
                    "Работа с сопротивлением",
                    "Трансформация",
                    "Интеграция",
                    "Зрелые защиты"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознанность",
                    "Практики новых реакций",
                    "Телесные практики",
                    "Дневник",
                    "Закрепление"
                ]
            }
        },
        
        # ========== ГРАНИЦЫ ==========
        "boundaries": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознание своих границ",
                    "Определение личных прав",
                    "Практика маленьких отказов",
                    "Анализ реакций окружающих",
                    "Закрепление новых паттернов"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск причин размытых границ",
                    "Проработка страха отвержения",
                    "Работа с чувством вины",
                    "Восстановление целостности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники твердого 'нет'",
                    "Я-высказывания",
                    "Управление дистанцией",
                    "Телесные практики границ",
                    "Ролевые игры"
                ]
            }
        },
        
        "boundaries_people": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознание своих границ",
                    "Определение личных прав",
                    "Практика маленьких отказов",
                    "Анализ реакций окружающих",
                    "Закрепление новых паттернов"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск причин размытых границ",
                    "Проработка страха отвержения",
                    "Работа с чувством вины",
                    "Восстановление целостности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники твердого 'нет'",
                    "Я-высказывания",
                    "Управление дистанцией",
                    "Телесные практики границ",
                    "Ролевые игры"
                ]
            }
        },
        
        "assertiveness": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознание своих прав",
                    "Практика уверенного поведения",
                    "Работа со страхом",
                    "Анализ результатов",
                    "Закрепление"
                ]
            },
            "psychologist": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней неуверенности",
                    "Проработка страха",
                    "Работа с самооценкой",
                    "Формирование уверенности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 70,
                "time_per_week": 3,
                "duration_weeks": 23,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники уверенного поведения",
                    "Ролевые игры",
                    "Практика в реальных ситуациях",
                    "Анализ",
                    "Закрепление"
                ]
            }
        },
        
        "conflict_skills": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ отношения к конфликтам",
                    "Понимание своих паттернов",
                    "Изучение стратегий",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней страха конфликтов",
                    "Проработка травм",
                    "Работа с агрессией",
                    "Формирование здорового подхода",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники разрешения конфликтов",
                    "Медиация",
                    "Ролевые игры",
                    "Практика",
                    "Закрепление"
                ]
            }
        },
        
        # ========== ЛИДЕРСТВО ==========
        "leadership": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ лидерских качеств",
                    "Определение стиля",
                    "Развитие навыков",
                    "Практика",
                    "Обратная связь"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование страха лидерства",
                    "Проработка синдрома самозванца",
                    "Работа с авторитетом",
                    "Формирование лидерской идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 15000,
                "support_required": True,
                "steps": [
                    "Навыки лидерства",
                    "Управление командой",
                    "Принятие решений",
                    "Коммуникация",
                    "Практика"
                ]
            }
        },
        
        "leader_courage": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ зон страха",
                    "Поиск ресурсов",
                    "Развитие смелости",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Поиск корней страха",
                    "Проработка травм",
                    "Работа с уязвимостью",
                    "Формирование мужества",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 5000,
                "support_required": True,
                "steps": [
                    "Упражнения на смелость",
                    "Публичные выступления",
                    "Принятие рисков",
                    "Анализ",
                    "Закрепление"
                ]
            }
        },
        
        "crisis_management": {
            "coach": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ реакций на кризис",
                    "Разработка стратегий",
                    "Практика",
                    "Оценка",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Работа со стрессом",
                    "Проработка травм",
                    "Укрепление устойчивости",
                    "Интеграция",
                    "Посткризисный рост"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 10000,
                "support_required": True,
                "steps": [
                    "Антикризисные стратегии",
                    "Быстрое принятие решений",
                    "Управление командой в кризисе",
                    "Коммуникация",
                    "Практика"
                ]
            }
        },
        
        # ========== МЫШЛЕНИЕ ==========
        "system_thinking": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Введение в системное мышление",
                    "Анализ текущих паттернов",
                    "Практика",
                    "Применение",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ограничений мышления",
                    "Работа с когнитивными искажениями",
                    "Развитие гибкости",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Инструменты системного анализа",
                    "Практика на кейсах",
                    "Моделирование",
                    "Применение в жизни",
                    "Закрепление"
                ]
            }
        },
        
        "system_analysis": {
            "coach": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Основы системного анализа",
                    "Изучение методов",
                    "Практика",
                    "Применение",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ мыслительных паттернов",
                    "Работа с ограничениями",
                    "Развитие аналитических способностей",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 7000,
                "support_required": False,
                "steps": [
                    "Продвинутые методы анализа",
                    "Практика на реальных задачах",
                    "Инструменты",
                    "Применение",
                    "Закрепление"
                ]
            }
        },
        
        "strategic_thinking": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Основы стратегического мышления",
                    "Анализ текущей стратегии",
                    "Разработка",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ограничений",
                    "Работа со страхом стратегий",
                    "Развитие видения",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 8000,
                "support_required": False,
                "steps": [
                    "Стратегические инструменты",
                    "Практика планирования",
                    "Анализ кейсов",
                    "Применение",
                    "Закрепление"
                ]
            }
        },
        
        "strategy": {
            "coach": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей стратегии",
                    "Определение целей",
                    "Разработка плана",
                    "Реализация",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование препятствий",
                    "Работа с ограничениями",
                    "Развитие стратегического мышления",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 6000,
                "support_required": False,
                "steps": [
                    "Стратегическое планирование",
                    "Инструменты",
                    "Практика",
                    "Анализ",
                    "Корректировка"
                ]
            }
        },
        
        "thinking_tools": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Изучение инструментов мышления",
                    "Практика",
                    "Применение",
                    "Анализ",
                    "Закрепление"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование текущих паттернов",
                    "Работа с ограничениями",
                    "Развитие гибкости",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 3000,
                "support_required": False,
                "steps": [
                    "Мастерство инструментов",
                    "Практика на задачах",
                    "Комбинирование методов",
                    "Применение",
                    "Закрепление"
                ]
            }
        },
        
        "triz": {
            "coach": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Введение в ТРИЗ",
                    "Изучение основных инструментов",
                    "Практика",
                    "Применение",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 160,
                "time_per_week": 6,
                "duration_weeks": 27,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование творческих блоков",
                    "Работа с ограничениями",
                    "Развитие изобретательности",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": True,
                "budget": 10000,
                "support_required": True,
                "steps": [
                    "Продвинутый ТРИЗ",
                    "Решение сложных задач",
                    "Практика на проектах",
                    "Инструменты",
                    "Мастерство"
                ]
            }
        },
        
        "decision_making": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ процесса принятия решений",
                    "Изучение методов",
                    "Практика",
                    "Анализ",
                    "Улучшение"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страха решений",
                    "Работа с неуверенностью",
                    "Развитие доверия к себе",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Методы принятия решений",
                    "Практика на кейсах",
                    "Анализ последствий",
                    "Быстрые решения",
                    "Закрепление"
                ]
            }
        },
        
        # ========== ПРОДУКТИВНОСТЬ ==========
        "productivity": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей продуктивности",
                    "Выявление точек роста",
                    "Внедрение методов",
                    "Отслеживание",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 110,
                "time_per_week": 4.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование прокрастинации",
                    "Работа со страхом неудачи",
                    "Мотивация",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 4,
                "space_required": True,
                "budget": 3000,
                "support_required": False,
                "steps": [
                    "Техники продуктивности",
                    "Тайм-менеджмент",
                    "Фокусировка",
                    "Привычки",
                    "Закрепление"
                ]
            }
        },
        
        "habit_building": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущих привычек",
                    "Выбор целевых привычек",
                    "Планирование внедрения",
                    "Отслеживание",
                    "Корректировка"
                ]
            },
            "psychologist": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование старых паттернов",
                    "Работа с сопротивлением",
                    "Мотивация",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 70,
                "time_per_week": 3,
                "duration_weeks": 23,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Методы формирования привычек",
                    "Ежедневная практика",
                    "Трекер привычек",
                    "Награды",
                    "Закрепление"
                ]
            }
        },
        
        "skill_mastery": {
            "coach": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Выбор навыка",
                    "Планирование обучения",
                    "Практика",
                    "Обратная связь",
                    "Углубление"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование блоков",
                    "Работа с синдромом самозванца",
                    "Развитие уверенности",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": True,
                "budget": 20000,
                "support_required": True,
                "steps": [
                    "Интенсивная практика",
                    "Наставничество",
                    "Проекты",
                    "Обратная связь",
                    "Мастерство"
                ]
            }
        },
        
        "growth": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего уровня",
                    "Определение зон роста",
                    "Планирование",
                    "Реализация",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ограничений",
                    "Работа с блоками",
                    "Развитие потенциала",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Стратегии роста",
                    "Практика",
                    "Обучение",
                    "Применение",
                    "Закрепление"
                ]
            }
        },
        
        "balance": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего баланса",
                    "Выявление дисбаланса",
                    "Планирование изменений",
                    "Внедрение",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование причин дисбаланса",
                    "Работа с чувством вины",
                    "Установление приоритетов",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Практики баланса",
                    "Тайм-менеджмент",
                    "Границы",
                    "Восстановление",
                    "Закрепление"
                ]
            }
        },
        
        "stress_resistance": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ стрессоров",
                    "Оценка реакций",
                    "Развитие навыков",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование уязвимостей",
                    "Проработка травм",
                    "Укрепление устойчивости",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Стресс-менеджмент",
                    "Техники релаксации",
                    "Физическая выносливость",
                    "Восстановление",
                    "Закрепление"
                ]
            }
        },
        
        # ========== ТРЕНИРОВКА СМЕЛОСТИ ==========
        "courage": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение зон, где не хватает смелости",
                    "Постановка маленьких целей на каждый день",
                    "Анализ страхов и их причин",
                    "Практика маленьких шагов",
                    "Рефлексия и закрепление результатов"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней страха и неуверенности",
                    "Проработка детских травм и запретов",
                    "Работа с внутренним критиком",
                    "Формирование новой самооценки",
                    "Интеграция смелости в повседневность"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные упражнения на выход из зоны комфорта",
                    "Техники управления страхом (дыхание, заземление)",
                    "Практика публичных выступлений",
                    "Ролевые игры с преодолением",
                    "Ведение дневника смелости"
                ]
            }
        },
        
        "trust": {
            "coach": {
                "time_total": 90,
                "time_per_week": 3.5,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ уровня доверия",
                    "Исследование причин недоверия",
                    "Постепенное развитие доверия",
                    "Практика",
                    "Рефлексия"
                ]
            },
            "psychologist": {
                "time_total": 130,
                "time_per_week": 5,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Поиск корней недоверия",
                    "Проработка предательств",
                    "Исцеление травм",
                    "Формирование доверия",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 27,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Упражнения на доверие",
                    "Практика уязвимости",
                    "Постепенное открытие",
                    "Анализ",
                    "Закрепление"
                ]
            }
        },
        
        "business": {
            "coach": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Анализ бизнес-идеи",
                    "Разработка стратегии",
                    "Планирование",
                    "Запуск",
                    "Анализ"
                ]
            },
            "psychologist": {
                "time_total": 220,
                "time_per_week": 9,
                "duration_weeks": 24,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Исследование страха успеха",
                    "Работа с синдромом самозванца",
                    "Развитие предпринимательского мышления",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": True,
                "budget": 30000,
                "support_required": True,
                "steps": [
                    "Бизнес-планирование",
                    "Маркетинг",
                    "Продажи",
                    "Управление",
                    "Масштабирование"
                ]
            }
        },
        
        "investments": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Изучение основ инвестирования",
                    "Анализ инструментов",
                    "Создание стратегии",
                    "Первые шаги",
                    "Анализ"
                ]
            },
            "psychologist": {
                "time_total": 170,
                "time_per_week": 7,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование страха риска",
                    "Работа с отношением к деньгам",
                    "Развитие инвестиционного мышления",
                    "Интеграция",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 140,
                "time_per_week": 5.5,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 20000,
                "support_required": True,
                "steps": [
                    "Инвестиционные стратегии",
                    "Анализ рынка",
                    "Управление портфелем",
                    "Риск-менеджмент",
                    "Практика"
                ]
            }
        }
    }
    
    # Защита от отсутствия цели
    if goal_id not in paths:
        logger.warning(f"Цель {goal_id} не найдена, возвращаю заглушку")
        return {
            "time_total": 200,
            "time_per_week": 8,
            "duration_weeks": 25,
            "energy_required": 6,
            "space_required": False,
            "budget": 0,
            "support_required": False,
            "steps": ["Информация уточняется"],
            "formatted_text": "Маршрут в разработке"
        }
    
    if mode not in paths[goal_id]:
        logger.warning(f"Режим {mode} не найден для цели {goal_id}, использую coach")
        mode = "coach"
    
    path = paths[goal_id][mode].copy()
    
    # Форматируем текст для вывода
    formatted_text = f"""
⏱ {bold('ВРЕМЯ:')} {path['time_total']} часов всего = {path['time_per_week']} ч/нед, {path['duration_weeks']} недель
⚡ {bold('ЭНЕРГИЯ:')} уровень {path['energy_required']}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ нужно отдельное' if path['space_required'] else 'не обязательно'}
💰 {bold('БЮДЖЕТ:')} {path['budget']}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ нужна' if path['support_required'] else 'опционально'}

{bold('ЭТАПЫ:')}
"""
    for i, step in enumerate(path['steps'], 1):
        formatted_text += f"{i}. {step}\n"
    
    path['formatted_text'] = formatted_text
    return path


# ============================================
# ГЕНЕРАЦИЯ ВОПРОСОВ ДЛЯ КОНТЕКСТА
# ============================================

def generate_life_context_questions() -> str:
    """Генерирует вопросы для сбора базового жизненного контекста"""
    return """
1️⃣ Семейное положение? (один/пара/семья/с родителями)
2️⃣ Есть дети? Если да, сколько и сколько лет?
3️⃣ Работаешь? Кем и какой график? (5/2, 2/2, свободный)
4️⃣ Сколько времени уходит на дорогу в день? (в минутах)
5️⃣ Есть своё жильё или съёмное? Ипотека?
6️⃣ Есть отдельная комната для дел?
7️⃣ Есть машина?
8️⃣ Кто из близких реально поддержит?
9️⃣ Кто будет мешать или обесценивать?
🔟 Оцени энергию от 1 до 10 в среднем
"""


def generate_goal_context_questions(goal_id: str, profile: Dict, mode: str, goal_name: str = "") -> str:
    """
    Генерирует вопросы под конкретную цель, профиль и режим
    
    Args:
        goal_id: идентификатор цели
        profile: данные профиля (векторы)
        mode: режим
        goal_name: название цели для контекста
    
    Returns:
        Строка с вопросами
    """
    
    # Получаем значения векторов с защитой от отсутствия данных
    try:
        behavioral = profile.get("behavioral_levels", {})
        sb = behavioral.get("СБ", [3])[0] if behavioral.get("СБ") else 3
        tf = behavioral.get("ТФ", [3])[0] if behavioral.get("ТФ") else 3
        ub = behavioral.get("УБ", [3])[0] if behavioral.get("УБ") else 3
        chv = behavioral.get("ЧВ", [3])[0] if behavioral.get("ЧВ") else 3
    except (IndexError, TypeError, KeyError):
        sb = tf = ub = chv = 3
    
    questions = []
    
    # Базовые вопросы для всех
    if "income" in goal_id or "money" in goal_id:
        questions.append("1️⃣ Какой навык будешь развивать? (коротко)")
        questions.append("2️⃣ Сколько часов в неделю реально можешь уделять?")
        questions.append("3️⃣ Нужны ли внешние инструменты/оборудование? (да/нет, какие)")
        
        # Вопросы от режима
        if mode == "coach":
            questions.append("4️⃣ Что для тебя идеальный результат?")
        elif mode == "psychologist":
            questions.append("4️⃣ Что самое страшное в увеличении дохода?")
            if sb >= 4:
                questions.append("5️⃣ Есть ли финансовая подушка? (да/нет)")
            if ub >= 4:
                questions.append("6️⃣ Доверяешь ли ты новым способам заработка?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов ли вставать на час раньше ради цели?")
            if tf >= 4:
                questions.append("5️⃣ Какой результат хочешь получить через месяц?")
    
    elif "relations" in goal_id:
        questions.append("1️⃣ Сколько времени готов уделять знакомствам/встречам?")
        questions.append("2️⃣ Нужны ли внешние изменения? (гардероб/имидж)")
        questions.append("3️⃣ Готов ли ходить к психологу, если потребуется?")
        
        if mode == "psychologist":
            if chv >= 4:
                questions.append("4️⃣ Боишься остаться один?")
            if sb >= 4:
                questions.append("5️⃣ Что страшнее — отвержение или сближение?")
    
    elif "anxiety" in goal_id or "energy" in goal_id or "calm" in goal_id:
        questions.append("1️⃣ Сколько часов спишь в среднем?")
        questions.append("2️⃣ Есть ли хронические заболевания?")
        questions.append("3️⃣ Принимаешь ли какие-то препараты?")
        
        if mode == "psychologist":
            questions.append("4️⃣ Когда началось? С чем связано?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов ли делать практики ежедневно?")
    
    elif "purpose" in goal_id or "meaning" in goal_id:
        questions.append("1️⃣ Сколько времени в неделю готов посвящать поиску?")
        questions.append("2️⃣ Есть ли идеи или гипотезы?")
        questions.append("3️⃣ Нужен ли наставник/психолог?")
        
        if mode == "psychologist":
            questions.append("4️⃣ Что запрещали в детстве?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов тестировать разные активности?")
    
    else:
        # Общие вопросы для других целей
        questions.append("1️⃣ Сколько часов в неделю можешь уделять?")
        questions.append("2️⃣ Нужны ли внешние ресурсы?")
        questions.append("3️⃣ Кто может поддержать?")
    
    # Добавляем вопросы по профилю для всех целей
    if sb >= 4:
        questions.append("❓ Что обычно вызывает у тебя тревогу? (коротко)")
    if tf >= 4:
        questions.append("❓ Важен ли быстрый результат?")
    if ub >= 4:
        questions.append("❓ Доверяешь ли ты себе в этом вопросе?")
    if chv >= 4:
        questions.append("❓ Чьё мнение для тебя важно в этом?")
    
    return "\n".join(questions)


# ============================================
# РАСЧЁТ ДОСТИЖИМОСТИ
# ============================================

def calculate_feasibility(
    goal_path: Dict,
    life_context: Dict,
    goal_context: Dict,
    profile: Dict
) -> Dict[str, Any]:
    """
    Рассчитывает достижимость цели на основе всех данных
    
    Args:
        goal_path: теоретический путь к цели
        life_context: жизненный контекст пользователя
        goal_context: контекст под цель
        profile: профиль пользователя
    
    Returns:
        Dict с полями:
        - deficit: общий дефицит ресурсов в %
        - time_deficit: дефицит времени в %
        - energy_deficit: дефицит энергии в %
        - space_deficit: есть ли пространство (100% если нет)
        - support_deficit: есть ли поддержка (100% если нет)
        - budget_deficit: дефицит бюджета в %
        - requirements_text: что требуется
        - available_text: что есть
        - recommendation: рекомендация
        - status: цветовой статус (🟢/🟡/🔴)
        - status_text: текстовый статус
    """
    
    # Защита от отсутствия данных
    if not goal_path:
        goal_path = {}
    if not life_context:
        life_context = {}
    if not goal_context:
        goal_context = {}
    
    # Извлекаем данные с защитой
    required_time = goal_path.get("time_per_week", 10)
    if required_time <= 0:
        required_time = 10  # избегаем деления на ноль
    
    required_energy = goal_path.get("energy_required", 6)
    if required_energy <= 0:
        required_energy = 6
    
    required_space = goal_path.get("space_required", False)
    required_budget = goal_path.get("budget", 0)
    if required_budget < 0:
        required_budget = 0
    
    required_support = goal_path.get("support_required", False)
    
    # Данные пользователя с защитой
    available_time = float(goal_context.get("time_per_week", 0) or 0)
    if available_time < 0:
        available_time = 0
    
    available_energy = life_context.get("energy_level", 5)
    if available_energy <= 0:
        available_energy = 5
    
    available_space = life_context.get("has_private_space", False)
    available_budget = float(goal_context.get("budget", 0) or 0)
    if available_budget < 0:
        available_budget = 0
    
    available_support = bool(life_context.get("support_people"))
    
    # Считаем дефициты
    time_deficit = max(0, (required_time - available_time) / required_time * 100) if required_time > 0 else 0
    energy_deficit = max(0, (required_energy - available_energy) / required_energy * 100) if required_energy > 0 else 0
    space_deficit = 100 if required_space and not available_space else 0
    support_deficit = 100 if required_support and not available_support else 0
    budget_deficit = max(0, (required_budget - available_budget) / required_budget * 100) if required_budget > 0 else 0
    
    # Общий дефицит (среднее, но пространство и поддержка имеют больший вес)
    deficits = [time_deficit, energy_deficit, space_deficit, support_deficit, budget_deficit]
    weights = [1, 1, 2, 1.5, 1]  # пространство и поддержка важнее
    
    weighted_sum = sum(d * w for d, w in zip(deficits, weights))
    total_weight = sum(weights)
    total_deficit = weighted_sum / total_weight if total_weight > 0 else 0
    
    # Ограничиваем дефицит диапазоном 0-100
    total_deficit = max(0, min(100, total_deficit))
    
    # Определяем статус
    if total_deficit <= 20:
        status = "🟢"
        status_text = "ЦЕЛЬ ДОСТИЖИМА"
    elif total_deficit <= 50:
        status = "🟡"
        status_text = "ТРЕБУЕТ КОРРЕКТИРОВКИ"
    else:
        status = "🔴"
        status_text = "ЦЕЛЬ НЕДОСТИЖИМА"
    
    # Формируем тексты
    requirements_text = f"""
⏱ {bold('ВРЕМЯ:')} {required_time} ч/нед
⚡ {bold('ЭНЕРГИЯ:')} уровень {required_energy}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ нужно' if required_space else 'не обязательно'}
💰 {bold('БЮДЖЕТ:')} {required_budget}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ нужна' if required_support else 'опционально'}
"""
    
    available_text = f"""
⏱ {bold('ВРЕМЯ:')} {available_time} ч/нед
⚡ {bold('ЭНЕРГИЯ:')} уровень {available_energy}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ есть' if available_space else '❌ нет'}
💰 {bold('БЮДЖЕТ:')} {available_budget}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ есть' if available_support else '❌ нет'}
"""
    
    # Формируем рекомендацию
    if total_deficit <= 20:
        recommendation = "Отличные условия! Можно начинать по плану."
    elif total_deficit <= 50:
        recommendation = "Есть дефициты, которые стоит учесть:\n"
        if time_deficit > 20:
            recommendation += "• Не хватает времени — увеличь срок или найди окна\n"
        if energy_deficit > 20:
            recommendation += "• Энергия ниже требуемой — начни с восстановления\n"
        if space_deficit > 0:
            recommendation += "• Нет отдельного пространства — найди место (кафе, коворкинг)\n"
        if support_deficit > 0:
            recommendation += "• Нет поддержки — найди единомышленников или наставника\n"
        if budget_deficit > 0:
            recommendation += f"• Не хватает {int(budget_deficit)}% бюджета — пересмотри расходы\n"
    else:
        recommendation = "Цель требует серьёзной подготовки:\n"
        recommendation += "• Увеличь срок в 2 раза\n"
        recommendation += "• Сначала создай условия (время, пространство, энергия)\n"
        recommendation += "• Или выбери более реалистичную цель"
    
    return {
        "deficit": round(total_deficit, 1),
        "time_deficit": round(time_deficit, 1),
        "energy_deficit": round(energy_deficit, 1),
        "space_deficit": round(space_deficit, 1),
        "support_deficit": round(support_deficit, 1),
        "budget_deficit": round(budget_deficit, 1),
        "requirements_text": requirements_text,
        "available_text": available_text,
        "recommendation": recommendation,
        "status": status,
        "status_text": status_text
    }


# ============================================
# ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ
# ============================================

def save_feasibility_result(user_id: int, goal_id: str, result: Dict) -> None:
    """
    Сохраняет результат проверки реальности
    
    Args:
        user_id: ID пользователя
        goal_id: ID цели
        result: результат проверки
    """
    # Здесь можно добавить сохранение в базу данных или файл
    # Например, в JSON-файл
    try:
        import json
        import os
        from datetime import datetime

        def _save_to_file():
            """Файловый I/O в отдельном потоке"""
            os.makedirs("feasibility_results", exist_ok=True)
            filename = f"feasibility_results/user_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
            data = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = []
            data.append({
                "user_id": user_id,
                "goal_id": goal_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        _save_to_file()

    except Exception as e:
        logger.error(f"Ошибка при сохранении результата: {e}")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_goal_difficulty(goal_id: str, mode: str) -> str:
    """
    Возвращает сложность цели
    
    Args:
        goal_id: ID цели
        mode: режим
    
    Returns:
        "easy", "medium" или "hard"
    """
    difficulties = {
        "income_growth": {"coach": "hard", "psychologist": "medium", "trainer": "hard"},
        "money_blocks": {"coach": "medium", "psychologist": "medium", "trainer": "easy"},
        "relations": {"coach": "medium", "psychologist": "hard", "trainer": "medium"},
        "anxiety_reduce": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "energy_boost": {"coach": "easy", "psychologist": "medium", "trainer": "easy"},
        "purpose": {"coach": "hard", "psychologist": "hard", "trainer": "medium"},
        "boundaries": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "self_esteem": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "courage": {"coach": "medium", "psychologist": "hard", "trainer": "medium"},
        "fear_work": {"coach": "medium", "psychologist": "hard", "trainer": "medium"},
        "calm": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "trust": {"coach": "medium", "psychologist": "hard", "trainer": "medium"},
        "leadership": {"coach": "hard", "psychologist": "hard", "trainer": "hard"},
        "stress_resistance": {"coach": "medium", "psychologist": "medium", "trainer": "medium"},
        "productivity": {"coach": "medium", "psychologist": "medium", "trainer": "easy"},
        "habit_building": {"coach": "easy", "psychologist": "medium", "trainer": "easy"}
    }
    
    if goal_id in difficulties and mode in difficulties[goal_id]:
        return difficulties[goal_id][mode]
    return "medium"


def get_goal_time_estimate(goal_id: str, mode: str) -> str:
    """
    Возвращает оценку времени для цели
    
    Args:
        goal_id: ID цели
        mode: режим
    
    Returns:
        Строка с оценкой времени
    """
    estimates = {
        "income_growth": {"coach": "6 месяцев", "psychologist": "6 месяцев", "trainer": "6 месяцев"},
        "money_blocks": {"coach": "4-6 недель", "psychologist": "6-8 недель", "trainer": "4-6 недель"},
        "relations": {"coach": "4-6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "anxiety_reduce": {"coach": "6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "energy_boost": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "purpose": {"coach": "6-8 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "boundaries": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "self_esteem": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "courage": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "fear_work": {"coach": "4-6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "calm": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "3-4 месяца"},
        "trust": {"coach": "4-6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "leadership": {"coach": "6-8 месяцев", "psychologist": "6-8 месяцев", "trainer": "6 месяцев"},
        "stress_resistance": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "productivity": {"coach": "4-6 месяцев", "psychologist": "4-6 месяцев", "trainer": "3-4 месяца"},
        "habit_building": {"coach": "3-4 месяца", "psychologist": "4-6 месяцев", "trainer": "3 месяца"}
    }
    
    if goal_id in estimates and mode in estimates[goal_id]:
        return estimates[goal_id][mode]
    return "3-6 месяцев"
