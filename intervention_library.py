# intervention_library.py
from typing import Dict, List, Optional, Any
from datetime import datetime


class InterventionLibrary:
    """
    Библиотека интервенций для разрыва петель
    """
    
    def __init__(self):
        self.interventions = self._build_library()
        self.exercises = self._build_exercises()
        self.quotes = self._build_quotes()
    
    def _build_library(self) -> Dict[str, Any]:
        """
        Строит библиотеку интервенций
        """
        return {
            # Для петель типа symptom_behavior_belief
            'symptom_behavior_belief': {
                'name': 'Петля симптом-поведение-убеждение',
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
                'break_points': [1, 2, 3, 4, 5, 6, 7, 8, 9],
                'interventions': {
                    1: {
                        'name': 'Дневник симптомов',
                        'description': 'Отслеживание симптомов',
                        'exercise': 'Записывай когда, где и при каких обстоятельствах появляется симптом.',
                        'duration': '14 дней',
                        'difficulty': 'Легкая',
                        'expected': 'Понимание триггеров',
                        'vak': 'digital'
                    },
                    5: {
                        'name': 'Работа с убеждениями',
                        'description': 'Когнитивная реструктуризация',
                        'exercise': 'Выпиши убеждение и найди 3 аргумента ЗА и 3 аргумента ПРОТИВ.',
                        'duration': '7 дней',
                        'difficulty': 'Средняя',
                        'expected': 'Гибкость мышления',
                        'vak': 'auditory_digital'
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
                'Съешь что-то очень медленно, смакуя каждый кусочек.'
            ],
            'journaling': [
                'Выпиши все мысли, которые крутятся в голове.',
                'Напиши письмо себе будущему через год.',
                'Опиши ситуацию глазами наблюдателя со стороны.'
            ],
            'behavioral': [
                'Сделай сегодня что-то, что обычно откладываешь.',
                'Скажи кому-то комплимент.',
                'Выйди на 15 минут раньше и просто погуляй.'
            ],
            'cognitive': [
                'Найди альтернативное объяснение ситуации.',
                'Представь, что бы посоветовал друг в этой ситуации.',
                'Подумай, чему тебя учит эта ситуация.'
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
                'Ты не можешь изменить то, чему не даешь названия.'
            ],
            'awareness': [
                'Осознанность — первый шаг к изменению.',
                'Проблему нельзя решить на том же уровне, на котором она возникла.',
                'Когда ты меняешь способ видеть вещи, вещи, которые ты видишь, меняются.'
            ],
            'action': [
                'Маленькие шаги каждый день приводят к большим результатам.',
                'Лучшее время начать было вчера. Следующее лучшее — сегодня.',
                'Дорога в тысячу миль начинается с первого шага.'
            ]
        }
    
    def get_for_loop(self, loop_type: str, element_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Возвращает интервенцию для петли и конкретного элемента
        """
        loop_data = self.interventions.get(loop_type)
        if not loop_data:
            # Пробуем универсальную
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
    
    def get_personalized(self, loop_type: str, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Возвращает персонализированную интервенцию с учетом профиля
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
            'СБ': 'тебе важно чувствовать безопасность',
            'ТФ': 'для тебя важны ресурсы и стабильность',
            'УБ': 'ты ищешь удовольствие и баланс',
            'ЧВ': 'ты ориентируешься на чувства и отношения'
        }
        
        vector_text = vector_descriptions.get(vector, 'у тебя есть свои особенности')
        
        # Добавляем персонализированное вступление
        intervention['personalized'] = f"Учитывая, что {vector_text} и текущий уровень {level}, рекомендую обратить внимание на..."
        
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
        import random
        intervention['bonus_exercise'] = random.choice(exercises)
        
        # Добавляем мотивирующую цитату
        quote_category = random.choice(['change', 'awareness', 'action'])
        intervention['quote'] = random.choice(self.quotes[quote_category])
        
        return intervention
    
    def get_daily_practice(self, element_id: int) -> Dict[str, str]:
        """
        Возвращает ежедневную практику для элемента
        """
        practices = {
            1: {
                'title': 'Наблюдение за симптомом',
                'practice': 'Сегодня просто замечай свой симптом без оценки. Как будто ты ученый, изучающий интересное явление.',
                'duration': '5 минут'
            },
            2: {
                'title': 'Осознанное действие',
                'practice': 'Выбери одно автоматическое действие и сделай его максимально осознанно.',
                'duration': '1 минута'
            },
            3: {
                'title': 'Новая стратегия',
                'practice': 'В привычной ситуации попробуй новый способ реагирования.',
                'duration': '5 минут'
            },
            4: {
                'title': 'Отслеживание паттерна',
                'practice': 'Заметь, когда срабатывает твой паттерн. Просто отметь это.',
                'duration': '10 секунд'
            },
            5: {
                'title': 'Исключение из правил',
                'practice': 'Найди сегодня одно исключение из твоего убеждения.',
                'duration': '5 минут'
            },
            6: {
                'title': 'Изменение среды',
                'practice': 'Измени что-то маленькое в своем окружении: переставь кружку, смени фон на телефоне.',
                'duration': '2 минуты'
            },
            7: {
                'title': 'Исследование корня',
                'practice': 'Спроси себя: "Когда я впервые так подумал?"',
                'duration': '3 минуты'
            },
            8: {
                'title': 'Осознание связки',
                'practice': 'Заметь, что соединяет две противоположности в твоей жизни.',
                'duration': '5 минут'
            },
            9: {
                'title': 'Новый взгляд',
                'practice': 'Посмотри на ситуацию глазами другого человека.',
                'duration': '5 минут'
            }
        }
        
        return practices.get(element_id, {
            'title': 'Осознанность',
            'practice': 'Побудь в тишине 2 минуты, просто наблюдая за дыханием.',
            'duration': '2 минуты'
        })
    
    def get_program_for_week(self, key_element_id: int) -> List[Dict[str, str]]:
        """
        Возвращает программу на неделю для работы с ключевым элементом
        """
        days = []
        
        for day in range(1, 8):
            if day == 1:
                practice = self.get_daily_practice(key_element_id)
                days.append({
                    'day': 'ПН',
                    'title': f'День 1: {practice["title"]}',
                    'task': practice['practice'],
                    'duration': practice['duration']
                })
            elif day == 2:
                days.append({
                    'day': 'ВТ',
                    'title': 'День 2: Наблюдение',
                    'task': 'Просто наблюдай, как проявляется твое ограничение в течение дня.',
                    'duration': 'В течение дня'
                })
            elif day == 3:
                days.append({
                    'day': 'СР',
                    'title': 'День 3: Запись',
                    'task': 'Запиши все мысли и чувства, связанные с этим ограничением.',
                    'duration': '10 минут'
                })
            elif day == 4:
                days.append({
                    'day': 'ЧТ',
                    'title': 'День 4: Эксперимент',
                    'task': 'Попробуй сделать маленький шаг в противоположном направлении.',
                    'duration': '5 минут'
                })
            elif day == 5:
                days.append({
                    'day': 'ПТ',
                    'title': 'День 5: Рефлексия',
                    'task': 'Подумай, чему тебя учит эта ситуация?',
                    'duration': '10 минут'
                })
            elif day == 6:
                days.append({
                    'day': 'СБ',
                    'title': 'День 6: Поддержка',
                    'task': 'Поговори с кем-то, кому доверяешь, о том, что происходит.',
                    'duration': '15 минут'
                })
            elif day == 7:
                days.append({
                    'day': 'ВС',
                    'title': 'День 7: Интеграция',
                    'task': 'Подведи итоги недели. Что изменилось? Что нового узнал?',
                    'duration': '15 минут'
                })
        
        return days
