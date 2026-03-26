#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 4: БИБЛИОТЕКА ИНТЕРВЕНЦИЙ (intervention_library.py)
Библиотека упражнений и практик для разрыва петель
ВЕРСИЯ 1.1 - ДОБАВЛЕНЫ МЕТОДЫ ДЛЯ РАБОТЫ С КОНТЕКСТОМ
"""

import random
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InterventionLibrary:
    """
    Библиотека интервенций для разрыва петель
    """
    
    def __init__(self):
        self.interventions = self._build_library()
        self.exercises = self._build_exercises()
        self.quotes = self._build_quotes()
        self.daily_practices = self._build_daily_practices()
        self._init_counter = 0
    
    def _build_library(self) -> Dict[str, Any]:
        """
        Строит библиотеку интервенций
        """
        return {
            # Для петель типа symptom_behavior_belief
            'symptom_behavior_belief': {
                'name': 'Петля симптом-поведение-убеждение',
                'description': 'Симптом вызывает поведение, которое подтверждает убеждение, а убеждение усиливает симптом.',
                'break_points': [2, 6, 7],  # поведение или убеждения
                'interventions': {
                    2: {
                        'name': 'Изменение автоматизма',
                        'description': 'Поймай момент, когда срабатывает автоматическая реакция, и сделай паузу.',
                        'exercise': 'Каждый день отслеживай ситуацию и вместо привычного действия делай паузу на 10 секунд. Записывай, что чувствуешь в этот момент.',
                        'duration': '21 день',
                        'difficulty': 'Средняя',
                        'expected': 'Автоматизм ослабнет, появится выбор',
                        'vak': 'kinesthetic'
                    },
                    6: {
                        'name': 'Оспаривание системных правил',
                        'description': 'Исследуй правила системы, в которой находишься.',
                        'exercise': 'Напиши список неписаных правил твоей семьи/работы. Какие из них можно нарушить без последствий?',
                        'duration': '7 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Осознание, что правила можно менять',
                        'vak': 'auditory_digital'
                    },
                    7: {
                        'name': 'Оспаривание убеждения',
                        'description': 'Найди одно исключение из правила каждый день.',
                        'exercise': 'Каждый вечер вспоминай случай, когда твое убеждение не работало. Записывай в дневник.',
                        'duration': '14 дней',
                        'difficulty': 'Высокая',
                        'expected': 'Убеждение перестанет быть абсолютным',
                        'vak': 'visual'
                    }
                }
            },
            
            # Для петель identity_system_environment
            'identity_system_environment': {
                'name': 'Петля идентичность-система-среда',
                'description': 'Идентичность определяет, как ты взаимодействуешь с системой, которая формирует среду, а среда укрепляет идентичность.',
                'break_points': [5, 6, 8],  # идентичность, система, связка
                'interventions': {
                    5: {
                        'name': 'Эксперимент с идентичностью',
                        'description': 'Попробуй вести себя так, как будто ты уже тот, кем хочешь стать.',
                        'exercise': 'Выбери один день и проживи его в роли «нового себя». Замечай разницу в мыслях, чувствах, поведении.',
                        'duration': '1 день (эксперимент)',
                        'difficulty': 'Средняя',
                        'expected': 'Появится новый опыт, расширяющий идентичность',
                        'vak': 'visual'
                    },
                    6: {
                        'name': 'Изменение среды',
                        'description': 'Измени один элемент в своем окружении.',
                        'exercise': 'Переставь мебель, смени маршрут, познакомься с новым человеком. Любое изменение среды влияет на систему.',
                        'duration': '3 дня',
                        'difficulty': 'Легкая',
                        'expected': 'Система потеряет устойчивость',
                        'vak': 'kinesthetic'
                    },
                    8: {
                        'name': 'Разрыв связки',
                        'description': 'Найди, что соединяет несовместимое в твоей жизни.',
                        'exercise': 'Выпиши два противоречия, которые ты удерживаешь. Что будет, если выбрать одно?',
                        'duration': '7 дней',
                        'difficulty': 'Высокая',
                        'expected': 'Освобождение энергии от противоречия',
                        'vak': 'auditory'
                    }
                }
            },
            
            # Для полной петли
            'full_cycle': {
                'name': 'Полный цикл самоподдержания',
                'description': 'Система полностью замкнута на себя, создавая устойчивый паттерн.',
                'break_points': [9, 4, 1],  # замыкание, нижняя причина, симптом
                'interventions': {
                    9: {
                        'name': 'Смена картины мира',
                        'description': 'Твой взгляд на мир замыкает систему. Попробуй увидеть иначе.',
                        'exercise': 'Каждый день находи три подтверждения тому, что мир может быть другим, более дружелюбным/справедливым/безопасным.',
                        'duration': '30 дней',
                        'difficulty': 'Очень высокая',
                        'expected': 'Система потеряет устойчивость, появятся новые возможности',
                        'vak': 'visual'
                    },
                    4: {
                        'name': 'Разрыв на нижнем уровне',
                        'description': 'Измени самую базовую реакцию.',
                        'exercise': 'В момент срабатывания паттерна сделай что-то радикально другое: если обычно напрягаешься — расслабься, если убегаешь — останься.',
                        'duration': '7 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Цепочка прервется, появится новый опыт',
                        'vak': 'kinesthetic'
                    },
                    1: {
                        'name': 'Работа с симптомом',
                        'description': 'Симптом — это сигнал системы. Научись его слушать.',
                        'exercise': 'Когда симптом появляется, не борись с ним. Спроси: «О чем ты хочешь мне сказать? Что мне нужно?»',
                        'duration': '14 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Симптом станет союзником, а не врагом',
                        'vak': 'auditory'
                    }
                }
            },
            
            # Для поведенческой петли
            'behavioral_loop': {
                'name': 'Поведенческая петля',
                'description': 'Автоматические реакции зацикливаются, усиливая друг друга.',
                'break_points': [2, 3, 4],
                'interventions': {
                    2: {
                        'name': 'Пауза перед реакцией',
                        'description': 'Автоматические реакции зациклены. Пауза разрывает цикл.',
                        'exercise': 'Сделай паузу перед любой эмоциональной реакцией. Сосчитай до 5. Подыши.',
                        'duration': '10 дней',
                        'difficulty': 'Легкая',
                        'expected': 'Появится контроль над реакциями',
                        'vak': 'kinesthetic'
                    },
                    3: {
                        'name': 'Смена стратегии',
                        'description': 'Если стратегия не работает — смени её.',
                        'exercise': 'В ситуации выбора сделай не то, что обычно, а наоборот. Любое новое действие — шаг из петли.',
                        'duration': '7 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Расширение поведенческого репертуара',
                        'vak': 'auditory_digital'
                    }
                }
            },
            
            # Универсальные интервенции
            'universal': {
                'name': 'Универсальные интервенции',
                'description': 'Практики, подходящие для любой петли.',
                'break_points': [1, 2, 3, 4, 5, 6, 7, 8, 9],
                'interventions': {
                    1: {
                        'name': 'Дневник симптомов',
                        'description': 'Отслеживание симптомов помогает увидеть паттерны.',
                        'exercise': 'Записывай когда, где и при каких обстоятельствах появляется симптом.',
                        'duration': '14 дней',
                        'difficulty': 'Легкая',
                        'expected': 'Понимание триггеров',
                        'vak': 'digital'
                    },
                    5: {
                        'name': 'Работа с убеждениями',
                        'description': 'Когнитивная реструктуризация меняет внутренние установки.',
                        'exercise': 'Выпиши убеждение и найди 3 аргумента ЗА и 3 аргумента ПРОТИВ.',
                        'duration': '7 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Гибкость мышления',
                        'vak': 'auditory_digital'
                    },
                    9: {
                        'name': 'Смена перспективы',
                        'description': 'Посмотри на ситуацию с другой стороны.',
                        'exercise': 'Представь, что ты наблюдаешь за собой со стороны. Что бы ты посоветовал?',
                        'duration': '5 минут в день',
                        'difficulty': 'Средняя',
                        'expected': 'Расширение картины мира',
                        'vak': 'visual'
                    }
                }
            }
        }
    
    def _build_exercises(self) -> Dict[str, List[str]]:
        """
        Строит библиотеку упражнений
        """
        return {
            'mindfulness': [
                'Закрой глаза и просто наблюдай за дыханием 5 минут.',
                'Почувствуй свое тело: где напряжение, где легкость?',
                'Съешь что-то очень медленно, смакуя каждый кусочек.',
                'Побудь в тишине, слушая звуки вокруг.',
                'Почувствуй, как ступают твои ноги при ходьбе.'
            ],
            'journaling': [
                'Выпиши все мысли, которые крутятся в голове.',
                'Напиши письмо себе будущему через год.',
                'Опиши ситуацию глазами наблюдателя со стороны.',
                'Запиши три вещи, за которые ты благодарен сегодня.',
                'Напиши, что бы ты сказал себе десятилетней давности.'
            ],
            'behavioral': [
                'Сделай сегодня что-то, что обычно откладываешь.',
                'Скажи кому-то комплимент.',
                'Выйди на 15 минут раньше и просто погуляй.',
                'Улыбнись незнакомцу.',
                'Попробуй что-то новое: новое блюдо, новый маршрут.'
            ],
            'cognitive': [
                'Найди альтернативное объяснение ситуации.',
                'Представь, что бы посоветовал друг в этой ситуации.',
                'Подумай, чему тебя учит эта ситуация.',
                'Найди три положительных аспекта в сложной ситуации.',
                'Сформулируй проблему иначе: что если это возможность?'
            ],
            'social': [
                'Позвони старому другу.',
                'Сделай комплимент коллеге.',
                'Попроси о помощи, если она нужна.',
                'Выслушай кого-то, не перебивая.',
                'Напиши благодарственное письмо.'
            ]
        }
    
    def _build_quotes(self) -> Dict[str, List[str]]:
        """
        Строит библиотеку мотивирующих цитат
        """
        return {
            'change': [
                'Единственный способ изменить свою жизнь — это выйти из зоны комфорта.',
                'Изменения начинаются там, где заканчивается зона комфорта.',
                'Ты не можешь изменить то, чему не даешь названия.',
                'Маленькие шаги каждый день приводят к большим результатам.',
                'Лучшее время начать было вчера. Следующее лучшее — сегодня.'
            ],
            'awareness': [
                'Осознанность — первый шаг к изменению.',
                'Проблему нельзя решить на том же уровне, на котором она возникла.',
                'Когда ты меняешь способ видеть вещи, вещи, которые ты видишь, меняются.',
                'Сначала ты формируешь привычки, потом привычки формируют тебя.',
                'Внимание — это самое ценное, что ты можешь кому-то подарить.'
            ],
            'action': [
                'Дорога в тысячу миль начинается с первого шага.',
                'Не жди идеального момента. Сделай шаг и сделай его идеальным.',
                'Действие — лучшее лекарство от тревоги.',
                'Сделай сегодня то, за что будешь благодарен себе завтра.',
                'Начни с малого. Это всегда работает.'
            ],
            'healing': [
                'Исцеление начинается с принятия.',
                'Ты не обязан быть тем, кем был вчера.',
                'Рана — это место, куда проникает свет.',
                'Самое глубокое исцеление происходит в тишине.',
                'Твоя история — это не приговор, это материал для новой жизни.'
            ]
        }
    
    def _build_daily_practices(self) -> Dict[int, Dict[str, str]]:
        """
        Строит библиотеку ежедневных практик для каждого элемента
        """
        return {
            1: {
                'title': 'Наблюдение за симптомом',
                'practice': 'Сегодня просто замечай свой симптом без оценки. Как будто ты ученый, изучающий интересное явление.',
                'duration': '5 минут',
                'question': 'Что я чувствую прямо сейчас?'
            },
            2: {
                'title': 'Осознанное действие',
                'practice': 'Выбери одно автоматическое действие и сделай его максимально осознанно.',
                'duration': '1 минута',
                'question': 'Что я делаю? Зачем?'
            },
            3: {
                'title': 'Новая стратегия',
                'practice': 'В привычной ситуации попробуй новый способ реагирования.',
                'duration': '5 минут',
                'question': 'Как ещё я могу на это отреагировать?'
            },
            4: {
                'title': 'Отслеживание паттерна',
                'practice': 'Заметь, когда срабатывает твой паттерн. Просто отметь это.',
                'duration': '10 секунд',
                'question': 'Что запустило этот паттерн?'
            },
            5: {
                'title': 'Исключение из правил',
                'practice': 'Найди сегодня одно исключение из твоего убеждения.',
                'duration': '5 минут',
                'question': 'Когда это убеждение НЕ работало?'
            },
            6: {
                'title': 'Изменение среды',
                'practice': 'Измени что-то маленькое в своем окружении: переставь кружку, смени фон на телефоне.',
                'duration': '2 минуты',
                'question': 'Что изменилось в моем состоянии?'
            },
            7: {
                'title': 'Исследование корня',
                'practice': 'Спроси себя: "Когда я впервые так подумал?"',
                'duration': '3 минуты',
                'question': 'Откуда это пришло?'
            },
            8: {
                'title': 'Осознание связки',
                'practice': 'Заметь, что соединяет две противоположности в твоей жизни.',
                'duration': '5 минут',
                'question': 'Что удерживает эти противоположности вместе?'
            },
            9: {
                'title': 'Новый взгляд',
                'practice': 'Посмотри на ситуацию глазами другого человека.',
                'duration': '5 минут',
                'question': 'Что бы увидел другой человек?'
            }
        }
    
    def get_for_loop(self, loop_type: str, element_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Возвращает интервенцию для петли и конкретного элемента
        
        Args:
            loop_type: тип петли
            element_id: ID элемента (опционально)
        
        Returns:
            dict: интервенция или None
        """
        loop_data = self.interventions.get(loop_type)
        if not loop_data:
            loop_data = self.interventions.get('universal')
        
        if not loop_data:
            return None
        
        if element_id and element_id in loop_data.get('interventions', {}):
            return loop_data['interventions'][element_id]
        
        # Если элемент не указан, берем первый рекомендуемый
        if loop_data.get('break_points'):
            first_point = loop_data['break_points'][0]
            return loop_data['interventions'].get(first_point)
        
        return None
    
    def get_for_loop_type(self, loop_type: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает информацию о петле по её типу
        """
        return self.interventions.get(loop_type, self.interventions.get('universal'))
    
    def get_all_loop_types(self) -> List[str]:
        """
        Возвращает список всех типов петель
        """
        return list(self.interventions.keys())
    
    def get_personalized(self, loop_type: str, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Возвращает персонализированную интервенцию с учетом профиля
        
        Args:
            loop_type: тип петли
            profile: словарь с профилем пользователя (vector, level, etc)
        
        Returns:
            dict: персонализированная интервенция
        """
        base = self.get_for_loop(loop_type)
        if not base:
            return None
        
        # Копируем, чтобы не менять оригинал
        intervention = base.copy()
        
        # Добавляем персонализацию
        vector = profile.get('vector', 'общий')
        level = profile.get('level', 3)
        
        # Адаптируем описание под вектор
        vector_descriptions = {
            'СБ': 'тебе важно чувствовать безопасность и защиту',
            'ТФ': 'для тебя важны ресурсы и стабильность',
            'УБ': 'ты ищешь удовольствие и баланс',
            'ЧВ': 'ты ориентируешься на чувства и отношения'
        }
        
        vector_text = vector_descriptions.get(vector, 'у тебя есть свои особенности')
        
        # Добавляем персонализированное вступление
        intervention['personalized'] = f"Учитывая, что {vector_text} и текущий уровень {level}, рекомендую обратить внимание на работу с телом и ощущениями."
        
        # Добавляем случайное упражнение из соответствующей категории
        vak = intervention.get('vak', 'cognitive')
        exercise_category = {
            'visual': 'mindfulness',
            'auditory': 'journaling',
            'kinesthetic': 'behavioral',
            'auditory_digital': 'cognitive',
            'digital': 'cognitive'
        }.get(vak, 'cognitive')
        
        exercises = self.exercises.get(exercise_category, self.exercises['mindfulness'])
        intervention['bonus_exercise'] = random.choice(exercises)
        
        # Добавляем мотивирующую цитату
        quote_category = random.choice(['change', 'awareness', 'action', 'healing'])
        intervention['quote'] = random.choice(self.quotes[quote_category])
        
        return intervention
    
    def get_daily_practice(self, element_id: int) -> Dict[str, str]:
        """
        Возвращает ежедневную практику для элемента
        
        Args:
            element_id: ID элемента (1-9)
        
        Returns:
            dict: ежедневная практика
        """
        return self.daily_practices.get(element_id, {
            'title': 'Осознанность',
            'practice': 'Побудь в тишине 2 минуты, просто наблюдая за дыханием.',
            'duration': '2 минуты',
            'question': 'Что я чувствую сейчас?'
        })
    
    def get_program_for_week(self, key_element_id: int) -> List[Dict[str, str]]:
        """
        Возвращает программу на неделю для работы с ключевым элементом
        
        Args:
            key_element_id: ID ключевого элемента
        
        Returns:
            list: программа на 7 дней
        """
        days = []
        base_practice = self.get_daily_practice(key_element_id)
        
        week_days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
        themes = [
            ('Наблюдение', base_practice['practice']),
            ('Запись', 'Запиши все мысли и чувства, связанные с этим ограничением.'),
            ('Эксперимент', 'Попробуй сделать маленький шаг в противоположном направлении.'),
            ('Рефлексия', f'Подумай: {base_practice.get("question", "Чему меня учит эта ситуация?")}'),
            ('Поддержка', 'Поговори с кем-то, кому доверяешь, о том, что происходит.'),
            ('Новый опыт', 'Сделай что-то, чего никогда не делал в этой сфере.'),
            ('Интеграция', 'Подведи итоги недели. Что изменилось? Что нового узнал?')
        ]
        
        for i, (day_name, (title, task)) in enumerate(zip(week_days, themes)):
            days.append({
                'day': day_name,
                'title': f'День {i+1}: {title}',
                'task': task,
                'duration': base_practice.get('duration', '5 минут')
            })
        
        return days
    
    def get_morning_practice(self) -> Dict[str, str]:
        """
        Возвращает утреннюю практику
        """
        return {
            'title': 'Утреннее намерение',
            'practice': 'Проснувшись, сделай три глубоких вдоха. Спроси себя: "Каким я хочу быть сегодня?"',
            'duration': '2 минуты',
            'question': 'Что важно для меня сегодня?'
        }
    
    def get_evening_practice(self) -> Dict[str, str]:
        """
        Возвращает вечернюю практику
        """
        return {
            'title': 'Вечерняя рефлексия',
            'practice': 'Перед сном вспомни три хороших момента за день. За что ты благодарен?',
            'duration': '3 минуты',
            'question': 'Что я сделал хорошо сегодня?'
        }
    
    def get_random_exercise(self, category: str = None) -> str:
        """
        Возвращает случайное упражнение
        
        Args:
            category: категория упражнения (mindfulness, journaling, behavioral, cognitive, social)
        """
        if category and category in self.exercises:
            return random.choice(self.exercises[category])
        
        all_exercises = []
        for exercises in self.exercises.values():
            all_exercises.extend(exercises)
        
        return random.choice(all_exercises)
    
    def get_random_quote(self, category: str = None) -> str:
        """
        Возвращает случайную цитату
        
        Args:
            category: категория цитаты (change, awareness, action, healing)
        """
        if category and category in self.quotes:
            return random.choice(self.quotes[category])
        
        all_quotes = []
        for quotes in self.quotes.values():
            all_quotes.extend(quotes)
        
        return random.choice(all_quotes)
    
    def get_intervention_for_element(self, element_id: int, vector: str = None, 
                                       level: int = None) -> Dict[str, Any]:
        """
        Возвращает интервенцию для конкретного элемента с учетом вектора
        
        Args:
            element_id: ID элемента
            vector: вектор пользователя (СБ, ТФ, УБ, ЧВ)
            level: уровень (1-6)
        
        Returns:
            dict: персонализированная интервенция
        """
        # Ищем интервенцию в универсальной библиотеке
        universal = self.interventions.get('universal', {})
        intervention = universal.get('interventions', {}).get(element_id)
        
        if not intervention:
            intervention = {
                'name': 'Осознанность',
                'description': 'Практика осознанности помогает увидеть паттерны.',
                'exercise': 'Побудь в тишине, наблюдая за дыханием.',
                'duration': '5 минут',
                'difficulty': 'Легкая',
                'expected': 'Понимание своих реакций',
                'vak': 'kinesthetic'
            }
        
        result = intervention.copy()
        
        # Добавляем персонализацию
        if vector:
            vector_names = {
                'СБ': 'безопасность и защиту',
                'ТФ': 'ресурсы и деньги',
                'УБ': 'удовольствие и смыслы',
                'ЧВ': 'чувства и отношения'
            }
            vector_word = vector_names.get(vector, '')
            if vector_word:
                result['personalized'] = f"Учитывая, что для тебя важно {vector_word}, обрати внимание на..."
        
        if level:
            if level <= 2:
                result['difficulty'] = 'Легкая'
                result['first_step'] = 'Начни с простого наблюдения'
            elif level <= 4:
                result['difficulty'] = 'Средняя'
                result['first_step'] = 'Попробуй один эксперимент'
            else:
                result['difficulty'] = 'Сложная'
                result['first_step'] = 'Начни с дневника, потом переходи к действиям'
        
        return result
    
    def get_progress_tracking(self, element_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Возвращает трекер прогресса для элемента
        
        Args:
            element_id: ID элемента
            days: количество дней для отслеживания
        
        Returns:
            dict: структура для отслеживания прогресса
        """
        practice = self.get_daily_practice(element_id)
        
        return {
            'element_id': element_id,
            'element_name': practice.get('title', f'Элемент {element_id}'),
            'tracking_days': days,
            'questions': [
                practice.get('question', 'Что я заметил?'),
                'Что изменилось?',
                'Что было сложным?',
                'Что получилось хорошо?'
            ],
            'scale': {
                '1': 'Совсем нет',
                '2': 'Немного',
                '3': 'Умеренно',
                '4': 'Заметно',
                '5': 'Значительно'
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику библиотеки
        """
        return {
            'total_loop_types': len(self.interventions),
            'total_interventions': sum(len(v.get('interventions', {})) for v in self.interventions.values()),
            'total_exercises': sum(len(v) for v in self.exercises.values()),
            'total_quotes': sum(len(v) for v in self.quotes.values()),
            'total_daily_practices': len(self.daily_practices),
            'loop_types': list(self.interventions.keys())
        }


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def format_intervention_for_display(intervention: Dict[str, Any]) -> str:
    """
    Форматирует интервенцию для отображения пользователю
    """
    lines = [
        f"🎯 **{intervention.get('name', 'Интервенция')}**",
        "",
        intervention.get('description', ''),
        "",
        f"📝 **Упражнение:** {intervention.get('exercise', '')}",
        f"⏱ **Длительность:** {intervention.get('duration', '')}",
        f"🎨 **Канал:** {intervention.get('vak', '')}",
        f"📊 **Сложность:** {intervention.get('difficulty', '')}",
        f"✨ **Ожидаемый результат:** {intervention.get('expected', '')}"
    ]
    
    if intervention.get('personalized'):
        lines.insert(2, f"🎭 **Персонализация:** {intervention['personalized']}")
    
    if intervention.get('quote'):
        lines.append("")
        lines.append(f"💭 *\"{intervention['quote']}\"*")
    
    if intervention.get('bonus_exercise'):
        lines.append("")
        lines.append(f"🌟 **Бонусное упражнение:** {intervention['bonus_exercise']}")
    
    return "\n".join(lines)


def format_week_program_for_display(program: List[Dict[str, str]]) -> str:
    """
    Форматирует недельную программу для отображения
    """
    lines = ["📅 **НЕДЕЛЬНАЯ ПРОГРАММА**\n"]
    
    for day in program:
        lines.append(f"**{day['day']}** — {day['title']}")
        lines.append(f"   📝 {day['task']}")
        lines.append(f"   ⏱ {day['duration']}")
        lines.append("")
    
    return "\n".join(lines)
