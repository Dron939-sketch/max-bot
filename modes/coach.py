#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Режим КОУЧ - партнёрский стиль общения для MAX.
"""
from typing import Dict, Any, List, Optional
import random
import logging

from .base_mode import BaseMode
from profiles import VECTORS, LEVEL_PROFILES

logger = logging.getLogger(__name__)


class CoachMode(BaseMode):
    """
    Режим КОУЧ - партнёрский стиль общения.
    
    ОТВЕТСТВЕННОСТЬ:
    - Помогать пользователю находить ответы внутри себя
    - Работать с конфайнмент-моделью через вопросы
    - Разрывать циклы (loops) через осознавание
    - Использовать метафоры и аналогии
    - Не давать прямых советов
    
    ПРИНЦИПЫ РАБОТЫ С КОНФАЙНМЕНТ-МОДЕЛЬЮ:
    1. Выявлять ограничения через открытые вопросы
    2. Помогать увидеть циклы самоподдержания
    3. Находить ресурсы внутри системы
    4. Не ломать защиты, а исследовать их
    """
    
    def __init__(self, user_id: int, user_data: Dict[str, Any], context=None):
        super().__init__(user_id, user_data, context)
        
        # Название режима для отображения
        self.display_name = "🔮 КОУЧ"
        self.emoji = "🔮"
        
        # Инструменты коуча
        self.tools = {
            "open_questions": self._generate_open_questions,
            "loop_awareness": self._bring_awareness_to_loop,
            "reframing": self._reframe_limitation,
            "scaling": self._scale_question,
            "values_clarification": self._clarify_values,
            "exception_finding": self._find_exceptions,
            "future_pacing": self._future_pace
        }
        
        # Векторные особенности
        self.vector_questions = {
            "СБ": [
                "Что самое страшное может случиться?",
                "Как вы обычно защищаетесь?",
                "Что было бы, если бы вы не боялись?",
                "Как тело реагирует на страх?",
                "Когда страх бывает полезен?"
            ],
            "ТФ": [
                "Что для вас деньги?",
                "Как вы принимаете финансовые решения?",
                "Что бы вы делали, если бы у вас было достаточно?",
                "Какие убеждения о деньгах вы унаследовали от родителей?",
                "Что для вас значит финансовая свобода?"
            ],
            "УБ": [
                "Как вы объясняете себе происходящее?",
                "Какие у вас есть теории о мире?",
                "Что для вас значит 'понимать'?",
                "Откуда берутся ваши убеждения?",
                "Что происходит, когда вы сталкиваетесь с необъяснимым?"
            ],
            "ЧВ": [
                "Что важно в отношениях для вас?",
                "Как вы выбираете людей?",
                "Что происходит, когда вы доверяете?",
                "Какие отношения вы хотите построить?",
                "Что для вас близость?"
            ]
        }
        
        logger.info(f"🔮 Создан режим CoachMode для пользователя {user_id}")
    
    def get_system_prompt(self) -> str:
        """Системный промпт для режима КОУЧ с интеграцией конфайнмент-модели"""
        
        analysis = self.analyze_profile_for_response()
        pain_points = ", ".join(analysis["pain_points"]) if analysis["pain_points"] else "не выражены"
        
        # Информация о конфайнмент-модели
        confinement_info = ""
        if analysis["key_confinement"]:
            kc = analysis["key_confinement"]
            confinement_info = f"""
КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ:
- Название: {kc['name']}
- Описание: {kc['description']}
- Сила: {kc['strength']:.1%}
- Тип: {kc['type']}
"""
        
        # Информация о циклах
        loops_info = ""
        if analysis["loops"]:
            loops_info = "\nЦИКЛЫ САМОПОДДЕРЖАНИЯ:\n"
            for i, loop in enumerate(analysis["loops"], 1):
                loops_info += f"{i}. {loop['description']} (сила: {loop['strength']:.1%})\n"
        
        prompt = f"""Ты — профессиональный коуч (ICF-стиль). Твоя задача — помогать пользователю находить ответы внутри себя через открытые вопросы.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Тип восприятия: {self.perception_type} (фокус: {analysis['attention_focus']})
- Уровень мышления: {self.thinking_level}/9 (глубина: {analysis['thinking_depth']})
- Слабый вектор: {self.weakest_vector} ({VECTORS[self.weakest_vector]['name']}), уровень {self.weakest_level}
- Болевые точки: {pain_points}
- Зона роста: {analysis['growth_area']}

{confinement_info}
{loops_info}

ПРИНЦИПЫ ТВОЕЙ РАБОТЫ:
1. НИКОГДА не давай прямых советов
2. Задавай открытые вопросы (Как? Что? Почему? Зачем?)
3. Помогай увидеть циклы (loops) через вопросы, а не интерпретации
4. Ищи исключения — когда ограничение НЕ работает
5. Используй шкалирование (от 1 до 10)
6. Применяй метафоры, связанные с контекстом пользователя

ТВОЙ СТИЛЬ:
- Мягкий, исследовательский
- Вовлекающий в диалог
- С акцентом на осознанность
- Используй фразы: "Что вы чувствуете?", "Как вы видите?", "Что для вас важно?"

ЗАПРЕЩЕНО:
- Интерпретировать (только вопросы)
- Говорить "я думаю", "я считаю"
- Давать готовые решения
- Оценивать

КОНТЕКСТ:
{self.get_context_string()}
"""
        return prompt
    
    def get_greeting(self) -> str:
        """Приветствие в режиме коуча"""
        name = self.context.name if self.context and self.context.name else ""
        
        if self.weakest_vector:
            greetings = [
                f"Привет, {name}. Я здесь, чтобы помочь тебе исследовать себя. С чего начнём?",
                f"{name}, давай посмотрим на твои паттерны. Что сейчас для тебя актуально?",
                f"Твой слабый вектор — {VECTORS[self.weakest_vector]['name']}. Как это проявляется в жизни?",
                f"Я заметил, что твоё ключевое ограничение связано с {self.weakest_profile.get('quote', '')}. Хочешь исследовать это?"
            ]
            return random.choice(greetings)
        
        return f"Привет, {name}. Я здесь, чтобы помочь тебе найти ответы внутри себя."
    
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Обрабатывает вопрос в режиме коуча
        Возвращает вопрос на вопрос (сократический диалог)
        """
        question_lower = question.lower()
        self.last_tools_used = []
        
        logger.info(f"🔮 CoachMode обрабатывает вопрос: {question[:50]}...")
        
        # 1. Если вопрос про слабый вектор
        if any(word in question_lower for word in ["боюсь", "страх", "тревога", "пугает"]) and self.weakest_vector == "СБ":
            response = self._handle_fear_question()
            self.last_tools_used.append("fear_work")
        
        # 2. Если вопрос про цикл
        elif any(word in question_lower for word in ["замкнутый круг", "повторяется", "снова", "опять"]):
            response = self._handle_loop_question()
            self.last_tools_used.append("loop_awareness")
        
        # 3. Если вопрос про деньги
        elif any(word in question_lower for word in ["деньги", "заработать", "финансы", "доход"]):
            response = self._handle_money_question()
            self.last_tools_used.append("money_coaching")
        
        # 4. Если вопрос про отношения
        elif any(word in question_lower for word in ["отношения", "люди", "один", "пара", "любовь"]):
            response = self._handle_relations_question()
            self.last_tools_used.append("relations_coaching")
        
        # 5. Если вопрос про смысл/понимание
        elif any(word in question_lower for word in ["смысл", "понять", "разобраться", "почему"]):
            response = self._handle_meaning_question()
            self.last_tools_used.append("meaning_coaching")
        
        # 6. По умолчанию - открытый вопрос
        else:
            response = self._generate_open_question(question)
            self.last_tools_used.append("open_question")
        
        # Сохраняем в историю
        self.save_to_history(question, response, self.last_tools_used)
        
        # Генерируем предложения для продолжения
        suggestions = self._generate_suggestions()
        
        # Проверяем, нужно ли предложить сказку
        tale_suggested = False
        if self.should_suggest_tale(question) or random.random() < 0.15:  # 15% chance
            tale = self.suggest_tale()
            if tale:
                suggestions.append(f"📖 Кстати, есть сказка про {tale.get('title', 'это')} — хочешь расскажу?")
                tale_suggested = True
                self.last_tools_used.append("tale_suggested")
        
        # Проверяем, нужна ли гипнотическая техника
        hypnotic_suggestion = False
        if self.should_use_hypnosis(question):
            hypnotic_suggestion = True
            self.last_tools_used.append("hypnosis_considered")
        
        return self.format_response(
            text=response,
            suggestions=suggestions
        )
    
    def _handle_fear_question(self) -> str:
        """Обрабатывает вопросы про страх (вектор СБ)"""
        questions = [
            f"Что именно пугает в этой ситуации?",
            f"Как тело реагирует на страх?",
            f"Что было бы, если бы страха не было?",
            f"Когда в последний раз страх был полезен?",
            f"Что ты делаешь, когда пугаешься?",
            f"Откуда этот страх мог взяться?"
        ]
        return random.choice(questions)
    
    def _handle_loop_question(self) -> str:
        """Обрабатывает вопросы про циклы"""
        if self.confinement_model and self.confinement_model.loops:
            strongest = max(self.confinement_model.loops, key=lambda x: x['strength'])
            return f"Я вижу цикл: {strongest['description']}. Что обычно происходит первым в этом круге?"
        return "Расскажи подробнее про этот круг. С чего он начинается?"
    
    def _handle_money_question(self) -> str:
        """Обрабатывает вопросы про деньги (вектор ТФ)"""
        questions = [
            "Что для тебя деньги?",
            "Как ты принимаешь финансовые решения?",
            "Что бы ты делал, если бы денег было достаточно?",
            "Какие у тебя убеждения о деньгах?",
            "Что для тебя значит финансовая безопасность?",
            "Как в твоей семье относились к деньгам?"
        ]
        return random.choice(questions)
    
    def _handle_relations_question(self) -> str:
        """Обрабатывает вопросы про отношения (вектор ЧВ)"""
        questions = [
            "Что для тебя важно в отношениях?",
            "Как ты выбираешь людей?",
            "Что происходит, когда ты доверяешь?",
            "Какие отношения ты хочешь?",
            "Что для тебя близость?",
            "Как ты проявляешь любовь?"
        ]
        return random.choice(questions)
    
    def _handle_meaning_question(self) -> str:
        """Обрабатывает вопросы про смысл и понимание (вектор УБ)"""
        questions = [
            "Что для тебя значит 'понять'?",
            "Как ты ищешь смысл?",
            "Какие объяснения работают для тебя?",
            "Что происходит, когда ты не понимаешь?",
            "Откуда берутся твои убеждения?"
        ]
        return random.choice(questions)
    
    def _generate_open_question(self, question: str) -> str:
        """Генерирует открытый вопрос на основе входящего"""
        templates = [
            f"Что для вас важно в этом вопросе?",
            f"Как вы видите эту ситуацию?",
            f"Что вы чувствуете, когда думаете об этом?",
            f"Что бы вы хотели изменить?",
            f"Как это проявляется в жизни?",
            f"Что самое сложное в этом для вас?"
        ]
        return random.choice(templates)
    
    def _generate_open_questions(self, topic: str = None) -> List[str]:
        """Генерирует список открытых вопросов по теме"""
        questions = []
        
        # Вопросы из слабого вектора
        if self.weakest_vector in self.vector_questions:
            questions.extend(self.vector_questions[self.weakest_vector])
        
        # Общие вопросы
        general = [
            "Что для вас самое сложное в этом?",
            "Когда это работает хорошо?",
            "Что бы вы хотели вместо этого?",
            "Кто мог бы поддержать вас?",
            "Какой следующий маленький шаг?"
        ]
        questions.extend(general)
        
        return questions[:4]
    
    def _bring_awareness_to_loop(self, loop_index: int = 0) -> str:
        """Помогает осознать цикл"""
        if not self.confinement_model or not self.confinement_model.loops:
            return "Расскажите, что повторяется в вашей жизни?"
        
        loop = self.confinement_model.loops[loop_index if loop_index < len(self.confinement_model.loops) else 0]
        return f"Я замечаю цикл: {loop['description']}. Что обычно происходит в самом начале?"
    
    def _reframe_limitation(self, limitation: str) -> str:
        """Переформулирует ограничение в ресурс"""
        reframes = {
            "страх": "осторожность, которая когда-то помогла",
            "лень": "способ экономить энергию",
            "тревога": "внимание к деталям",
            "агрессия": "энергия для защиты",
            "недоверие": "опыт, который учит разбираться в людях",
            "контроль": "желание безопасности"
        }
        
        for key, reframe in reframes.items():
            if key in limitation.lower():
                return f"А что, если посмотреть на это как на {reframe}?"
        
        return "Как ещё можно это назвать?"
    
    def _scale_question(self, topic: str, current: int = None) -> str:
        """Задаёт шкалирующий вопрос"""
        if current is None:
            return f"Оцените от 1 до 10, насколько {topic} вас беспокоит?"
        else:
            return f"Что нужно, чтобы с {current} подняться на 1 балл выше?"
    
    def _clarify_values(self) -> str:
        """Помогает прояснить ценности"""
        return "Что для вас действительно важно в этой ситуации?"
    
    def _find_exceptions(self, problem: str) -> str:
        """Ищет исключения из проблемы"""
        return f"Бывает ли так, что {problem} НЕ происходит? Что тогда по-другому?"
    
    def _future_pace(self, goal: str) -> str:
        """Помогает представить будущее"""
        return f"Представьте, что {goal} уже случилось. Что изменилось? Что вы чувствуете?"
    
    def _generate_suggestions(self) -> List[str]:
        """Генерирует предложения для продолжения"""
        suggestions = []
        
        if self.weakest_vector == "СБ":
            suggestions.append("❓ Хочешь исследовать свои страхи глубже?")
        elif self.weakest_vector == "ТФ":
            suggestions.append("💰 Поговорим о твоих финансовых убеждениях?")
        elif self.weakest_vector == "УБ":
            suggestions.append("🔍 Исследуем, как ты понимаешь мир?")
        elif self.weakest_vector == "ЧВ":
            suggestions.append("🤝 Хочешь разобраться в отношениях?")
        
        # Добавляем общие предложения
        suggestions.append("🧠 Что для тебя сейчас самое важное?")
        suggestions.append("🎯 Хочешь поставить конкретную цель?")
        
        return suggestions[:3]  # Возвращаем не больше 3 предложений
    
    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о режиме"""
        return {
            "name": self.display_name,
            "emoji": self.emoji,
            "description": "Помогаю найти ответы внутри себя через открытые вопросы",
            "weakest_vector": self.weakest_vector,
            "tools_available": list(self.tools.keys())
        }
