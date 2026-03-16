#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Режим ТРЕНЕР - жёсткий, структурированный, ориентированный на действие для MAX.
"""
from typing import Dict, Any, List, Optional
import random
import logging
from datetime import datetime, timedelta

from .base_mode import BaseMode
from profiles import VECTORS, LEVEL_PROFILES

logger = logging.getLogger(__name__)


class TrainerMode(BaseMode):
    """
    Режим ТРЕНЕР - жёсткий, структурированный, ориентированный на действие.
    
    ОТВЕТСТВЕННОСТЬ:
    - Чёткие инструкции и планы действий
    - Постановка конкретных задач
    - Контроль выполнения (через напоминания)
    - Работа с конфайнмент-моделью через действие
    - Разрыв циклов через конкретные шаги
    
    ПРИНЦИПЫ РАБОТЫ:
    1. Минимум рефлексии, максимум действия
    2. Конкретные, измеримые задачи
    3. Дедлайны и ответственность
    4. Поддержка через вызов
    5. Якорение ресурсных состояний
    """
    
    def __init__(self, user_id: int, user_data: Dict[str, Any], context=None):
        super().__init__(user_id, user_data, context)
        
        # Название режима для отображения
        self.display_name = "⚡ ТРЕНЕР"
        self.emoji = "⚡"
        
        # Инструменты тренера
        self.tools = {
            "action_plan": self._create_action_plan,
            "task_setting": self._set_specific_task,
            "deadline_set": self._set_deadline,
            "progress_check": self._check_progress,
            "challenge": self._throw_challenge,
            "anchor_creation": self._create_resource_anchor,
            "habit_building": self._build_habit
        }
        
        # Маппинг векторов на конкретные действия
        self.vector_actions = {
            "СБ": {
                1: [
                    "Каждый день говорить 'нет' одному человеку", 
                    "Защитить свои границы в мелочи",
                    "Сказать 'я против', если что-то не нравится"
                ],
                2: [
                    "Выходить из зоны комфорта раз в день", 
                    "Делать то, что страшно, но маленькими шагами",
                    "Сделать сегодня что-то впервые"
                ],
                3: [
                    "Выражать недовольство сразу", 
                    "Не копить раздражение",
                    "Говорить о том, что бесит, в моменте"
                ],
                4: [
                    "Инициировать конфликт, если это необходимо", 
                    "Отстаивать позицию",
                    "Не сдаваться в споре"
                ],
                5: [
                    "Управлять конфликтом", 
                    "Быть лидером в напряжённой ситуации",
                    "Брать ответственность на себя"
                ],
                6: [
                    "Создавать безопасное пространство для других", 
                    "Брать ответственность в кризисе",
                    "Вести за собой в стрессовой ситуации"
                ]
            },
            "ТФ": {
                1: [
                    "Записывать все расходы 3 дня", 
                    "Найти 1 способ сэкономить",
                    "Посчитать траты за вчера"
                ],
                2: [
                    "Создать финансовый план на неделю", 
                    "Изучить 1 источник дохода",
                    "Открыть накопительный счёт"
                ],
                3: [
                    "Откладывать 5% от любого дохода", 
                    "Прочитать книгу по финансам",
                    "Начать вести бюджет"
                ],
                4: [
                    "Создать подушку безопасности", 
                    "Инвестировать первую сумму",
                    "Купить актив, а не пассив"
                ],
                5: [
                    "Диверсифицировать доходы", 
                    "Создать пассивный доход",
                    "Найти 3 источника дохода"
                ],
                6: [
                    "Обучать других финансам", 
                    "Создать финансовую систему",
                    "Написать план на 5 лет"
                ]
            },
            "УБ": {
                1: [
                    "Прочитать 10 страниц нон-фикшн", 
                    "Задать 5 вопросов эксперту",
                    "Посмотреть обучающее видео"
                ],
                2: [
                    "Изучить 1 новую тему", 
                    "Найти связи между событиями",
                    "Сделать mind-map"
                ],
                3: [
                    "Проверить факты", 
                    "Не делать выводов без доказательств",
                    "Найти 3 источника по теме"
                ],
                4: [
                    "Найти 3 объяснения событию", 
                    "Рассмотреть альтернативы",
                    "Посмотреть на ситуацию с другой стороны"
                ],
                5: [
                    "Создать свою теорию", 
                    "Написать статью/пост",
                    "Собрать знания в систему"
                ],
                6: [
                    "Обучать системе", 
                    "Создать методологию",
                    "Написать инструкцию для других"
                ]
            },
            "ЧВ": {
                1: [
                    "Познакомиться с 1 новым человеком", 
                    "Написать старому другу",
                    "Улыбнуться незнакомцу"
                ],
                2: [
                    "Сказать комплимент", 
                    "Попросить о помощи",
                    "Предложить помощь"
                ],
                3: [
                    "Выразить чувства словами", 
                    "Спросить, что чувствует другой",
                    "Сказать 'я тебя ценю'"
                ],
                4: [
                    "Установить границу в отношениях", 
                    "Сказать 'нет'",
                    "Обозначить свои правила"
                ],
                5: [
                    "Создать равные отношения", 
                    "Быть уязвимым",
                    "Рассказать о своих слабостях"
                ],
                6: [
                    "Вести за собой", 
                    "Создавать сообщество",
                    "Объединять людей"
                ]
            }
        }
        
        logger.info(f"⚡ Создан режим TrainerMode для пользователя {user_id}")
    
    def get_system_prompt(self) -> str:
        """Системный промпт для режима ТРЕНЕР"""
        
        analysis = self.analyze_profile_for_response()
        
        # Конкретные действия для слабого вектора
        actions = self.vector_actions.get(self.weakest_vector, {}).get(self.weakest_level, [])
        action_text = "\n".join([f"  - {a}" for a in actions[:3]]) if actions else "  - Начать с малого"
        
        prompt = f"""Ты — жёсткий, требовательный персональный тренер (как в спортзале, только для жизни).

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Слабый вектор: {self.weakest_vector} ({VECTORS[self.weakest_vector]['name']}), уровень {self.weakest_level}
- Зона роста: {analysis['growth_area']}
- Текущее ограничение: {self.weakest_profile.get('quote', 'не определено')}

РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ (если спросит):
{action_text}

ПРИНЦИПЫ ТВОЕЙ РАБОТЫ:
1. Коротко, чётко, по делу
2. Конкретные задачи с дедлайнами
3. Без сантиментов и долгих обсуждений
4. Ответственность и контроль
5. Мотивация через вызов

ТВОЙ СТИЛЬ:
- "Сделай это"
- "Сколько тебе нужно времени?"
- "Отчитайся о результате"
- "Не ищи оправданий"
- "Просто сделай"

ЗАПРЕЩЕНО:
- Рефлексировать
- Спрашивать "как ты себя чувствуешь"
- Давать выбор без дедлайна
- Жалеть

КОНТЕКСТ:
{self.get_context_string()}

ПОМНИ: ты не психолог, ты тренер. Твоя задача — действие и результат.
"""
        return prompt
    
    def get_greeting(self) -> str:
        """Приветствие в режиме тренера"""
        name = self.context.name if self.context and self.context.name else ""
        
        greetings = [
            f"{name}, привет. Какая задача сегодня?",
            f"Чё надо? Время — деньги.",
            f"Слушаю. Что будем решать?",
            f"{name}, по делу?",
            f"Твоё слабое место — {self.weakest_vector}. Работаем?",
            f"Есть запрос? Говори."
        ]
        return random.choice(greetings)
    
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Обрабатывает вопрос в режиме тренера
        Возвращает конкретные задачи и дедлайны
        """
        question_lower = question.lower()
        self.last_tools_used = []
        
        logger.info(f"⚡ TrainerMode обрабатывает вопрос: {question[:50]}...")
        
        # 1. Если вопрос про конкретную проблему
        if self.weakest_vector == "СБ" and any(word in question_lower for word in ["боюсь", "страх", "тревога", "пугает"]):
            response = self._task_for_fear()
            self.last_tools_used.append("fear_task")
        
        elif self.weakest_vector == "ТФ" and any(word in question_lower for word in ["деньги", "заработать", "финансы", "доход"]):
            response = self._task_for_money()
            self.last_tools_used.append("money_task")
        
        elif self.weakest_vector == "ЧВ" and any(word in question_lower for word in ["отношения", "люди", "один", "пара"]):
            response = self._task_for_relations()
            self.last_tools_used.append("relations_task")
        
        elif self.weakest_vector == "УБ" and any(word in question_lower for word in ["понять", "разобраться", "смысл", "почему"]):
            response = self._task_for_understanding()
            self.last_tools_used.append("understanding_task")
        
        # 2. Если вопрос про цикл/повторение
        elif any(word in question_lower for word in ["замкнутый круг", "повторяется", "снова", "опять"]):
            response = self._task_to_break_loop()
            self.last_tools_used.append("break_loop")
        
        # 3. Если вопрос про план
        elif any(word in question_lower for word in ["план", "что делать", "как", "помоги"]):
            response = self._create_action_plan(question)
            self.last_tools_used.append("action_plan")
        
        # 4. По умолчанию - задача
        else:
            response = self._set_specific_task(question)
            self.last_tools_used.append("task")
        
        # Сохраняем в историю
        self.save_to_history(question, response, self.last_tools_used)
        
        # Создаём якорь, если нужно
        if "якорь" in question_lower or "заякорить" in question_lower:
            self._create_resource_anchor()
        
        # Генерируем предложения
        suggestions = self._generate_action_suggestions()
        
        return self.format_response(
            text=response,
            suggestions=suggestions
        )
    
    def _task_for_fear(self) -> str:
        """Задача для работы со страхом"""
        tasks = [
            f"Задание на сегодня: сделай то, чего боишься, но в маленьком размере. Что выберешь? Дедлайн: сегодня 22:00.",
            f"Твоя задача: 3 раза за день сказать 'нет'. Отчитаешься вечером.",
            f"Страх лечится действием. До завтра сделай одно действие, которое откладывал из-за страха. Какое?",
            f"Прямо сейчас напиши 3 вещи, которые боишься сделать. Выбери одну. Сделай до вечера."
        ]
        return random.choice(tasks)
    
    def _task_for_money(self) -> str:
        """Задача для работы с деньгами"""
        tasks = [
            "Задание: найди 1 дополнительный источник дохода за неделю. В воскресенье отчёт.",
            "Сегодня до 18:00 составь финансовый план на месяц. Скинь мне.",
            "Твоя задача на завтра: прочитать 10 страниц книги по финансам и выписать 3 идеи.",
            "До пятницы: открой накопительный счёт и положи туда первую сумму."
        ]
        return random.choice(tasks)
    
    def _task_for_relations(self) -> str:
        """Задача для работы с отношениями"""
        tasks = [
            "Задание: сегодня скажи одному человеку, что ты чувствуешь. Без оценок, просто чувство. Дедлайн: сегодня.",
            "Твоя задача: установи одну границу. Скажи 'нет' там, где обычно соглашаешься.",
            "До пятницы: познакомься с одним новым человеком. Не в интернете.",
            "Напиши тому, с кем давно не общался. Сегодня."
        ]
        return random.choice(tasks)
    
    def _task_for_understanding(self) -> str:
        """Задача для работы с пониманием (вектор УБ)"""
        tasks = [
            "Задание: изучи одну новую тему за час. Выпиши 5 тезисов.",
            "Твоя задача: найди 3 объяснения тому, что тебя беспокоит.",
            "До завтра: прочитай 20 страниц по теме и сформулируй своё мнение."
        ]
        return random.choice(tasks)
    
    def _task_to_break_loop(self) -> str:
        """Задача для разрыва цикла"""
        return "Цикл разрывается действием. Сделай одно маленькое действие по-другому. Какое? Дедлайн: сегодня."
    
    def _create_action_plan(self, goal: str) -> str:
        """Создаёт конкретный план действий"""
        
        # Берём действия из слабого вектора
        actions = self.vector_actions.get(self.weakest_vector, {}).get(self.weakest_level, [])
        
        if len(actions) >= 3:
            plan = f"План действий для '{goal[:30]}...':\n"
            plan += f"1. {actions[0]} (до завтра)\n"
            plan += f"2. {actions[1]} (до конца недели)\n"
            plan += f"3. {actions[2]} (до следующей недели)\n"
            plan += f"Отчёт после каждого этапа."
        else:
            plan = f"Задача: {goal}. Разбей на 3 шага. Сделай первый сегодня. Отпишись."
        
        return plan
    
    def _set_specific_task(self, context: str) -> str:
        """Ставит конкретную задачу"""
        templates = [
            f"Твоя задача на сегодня: {self._get_random_action()} Дедлайн: 23:59.",
            f"Сделай это сегодня: {self._get_random_action()} Отчитаешься.",
            f"Задание: {self._get_random_action()} Срок - до завтра.",
            f"Прямо сейчас: {self._get_random_action()} Результат скинь."
        ]
        return random.choice(templates)
    
    def _get_random_action(self) -> str:
        """Возвращает случайное действие для слабого вектора"""
        actions = self.vector_actions.get(self.weakest_vector, {}).get(self.weakest_level, [])
        if actions:
            return random.choice(actions)
        return "сделай одно маленькое действие в сторону цели"
    
    def _set_deadline(self, task: str, hours: int = 24) -> str:
        """Устанавливает дедлайн"""
        deadline = (datetime.now() + timedelta(hours=hours)).strftime("%d.%m %H:%M")
        return f"Задача: {task}. Дедлайн: {deadline}. Опоздал — штраф (сам придумаешь)."
    
    def _check_progress(self) -> str:
        """Проверяет прогресс"""
        return "Отчёт по задачам. Что сделано за сегодня?"
    
    def _throw_challenge(self) -> str:
        """Бросает вызов"""
        challenges = [
            "Спорим, не сделаешь?",
            "Слабо?",
            "Докажи, что можешь.",
            "Это для слабаков или для чемпионов?",
            "Кто ты после этого?"
        ]
        return random.choice(challenges)
    
    def _create_resource_anchor(self) -> str:
        """Создаёт ресурсный якорь"""
        anchor = self.create_anchor("действие", "состояние силы")
        return f"Создаю якорь. Когда будешь готов действовать — нажми на кулак правой рукой. Заякорил."
    
    def _build_habit(self, habit: str, days: int = 21) -> str:
        """Помогает построить привычку"""
        return f"Привычка '{habit}'. Делаешь {days} дней подряд. Сегодня день 1. Поехали."
    
    def _generate_action_suggestions(self) -> List[str]:
        """Генерирует предложения действий"""
        suggestions = []
        
        # Предложения из слабого вектора
        actions = self.vector_actions.get(self.weakest_vector, {}).get(self.weakest_level, [])
        for action in actions[:2]:
            suggestions.append(f"⚡ {action}")
        
        # Общие предложения
        suggestions.append("📋 Составить план")
        suggestions.append("⏰ Поставить дедлайн")
        suggestions.append("🏆 Принять вызов")
        
        return suggestions[:3]
    
    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о режиме"""
        return {
            "name": self.display_name,
            "emoji": self.emoji,
            "description": "Даю чёткие инструкции и требую результат",
            "weakest_vector": self.weakest_vector,
            "weakest_level": self.weakest_level,
            "tools_available": list(self.tools.keys())
        }
