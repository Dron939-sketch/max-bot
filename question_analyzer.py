#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Глубинный анализатор вопросов для MAX
Версия с полной функциональностью
"""

import logging
import re
from typing import Dict, Any, Optional, List

from profiles import VECTORS, LEVEL_PROFILES

logger = logging.getLogger(__name__)


class QuestionAnalyzer:
    """Анализирует вопросы пользователя с учетом его профиля"""
    
    def __init__(self, user_data: Dict[str, Any], user_name: str):
        self.user_data = user_data
        self.user_name = user_name
        self.scores = self._extract_scores()
        self.profile_data = user_data.get("profile_data", {})
        self.deep_patterns = user_data.get("deep_patterns", {})
        
        # Определяем слабый вектор
        if self.scores:
            min_vector = min(self.scores.items(), key=lambda x: x[1])
            self.weakest_vector, self.weakest_score = min_vector
            self.weakest_level = self._level(self.weakest_score)
            self.weakest_profile = LEVEL_PROFILES.get(self.weakest_vector, {}).get(self.weakest_level, {})
        else:
            self.weakest_vector = "СБ"
            self.weakest_score = 3.0
            self.weakest_level = 3
            self.weakest_profile = {}
    
    def _level(self, score: float) -> int:
        """Дробный балл 1..4 → целый уровень 1..6"""
        if score <= 1.49:
            return 1
        elif score <= 2.00:
            return 2
        elif score <= 2.50:
            return 3
        elif score <= 3.00:
            return 4
        elif score <= 3.50:
            return 5
        else:
            return 6
    
    def _extract_scores(self) -> Dict[str, float]:
        """Извлекает scores из данных пользователя"""
        scores = {}
        for k in VECTORS:
            levels = self.user_data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        return scores
    
    def _get_feelings_from_text(self, text: str) -> List[str]:
        """Извлекает упоминания чувств из текста"""
        feelings = {
            "страх": ["боюсь", "страшно", "пугает", "тревожно", "боязнь"],
            "гнев": ["злюсь", "бесит", "раздражает", "ярость", "гнев"],
            "грусть": ["грустно", "печально", "тоска", "уныние", "плакать"],
            "стыд": ["стыдно", "позор", "неловко", "унижение"],
            "вина": ["виноват", "вина", "должен", "обязан"],
            "радость": ["радуюсь", "счастье", "восторг", "кайф"],
            "любовь": ["люблю", "нежность", "забота", "тепло"],
            "одиночество": ["одиноко", "никому не нужен", "брошен", "покинут"]
        }
        
        found = []
        text_lower = text.lower()
        
        for feeling, markers in feelings.items():
            if any(marker in text_lower for marker in markers):
                found.append(feeling)
        
        return found[:3]  # не больше 3 чувств
    
    def _get_topics_from_text(self, text: str) -> List[str]:
        """Определяет основные темы вопроса"""
        topics = {
            "деньги": ["деньг", "заработ", "финанс", "доход", "бюджет", "инвестиц"],
            "отношения": ["отношени", "любов", "партнер", "муж", "жен", "друг"],
            "работа": ["работ", "карьер", "увольн", "начальник", "коллег"],
            "семья": ["семь", "мам", "пап", "дет", "родител"],
            "здоровье": ["здоров", "бол", "лечен", "врач", "симптом"],
            "смысл": ["смысл", "предназначен", "путь", "цель", "зачем"],
            "страх": ["страх", "боюсь", "тревог", "пуга"],
            "развитие": ["развит", "рост", "обучен", "навык", "умение"]
        }
        
        found = []
        text_lower = text.lower()
        
        for topic, markers in topics.items():
            if any(marker in text_lower for marker in markers):
                found.append(topic)
        
        return found[:3]  # не больше 3 тем
    
    def _analyze_question_type(self, question: str) -> str:
        """Определяет тип вопроса"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["почему", "зачем", "отчего"]):
            return "причинно-следственный"
        elif any(word in question_lower for word in ["как", "каким образом"]):
            return "процессуальный"
        elif any(word in question_lower for word in ["что", "кто", "где", "когда"]):
            return "фактический"
        elif any(word in question_lower for word in ["стоит ли", "нужно ли", "лучше"]):
            return "оценочный"
        elif "?" not in question:
            return "утверждение"
        else:
            return "общий"
    
    def get_reflection_text(self, question: str) -> str:
        """Возвращает глубинный анализ вопроса"""
        
        # Определяем чувства и темы
        feelings = self._get_feelings_from_text(question)
        topics = self._get_topics_from_text(question)
        question_type = self._analyze_question_type(question)
        
        reflection = f"🔍 <b>Глубинный анализ вопроса от {self.user_name}:</b>\n\n"
        
        # Тип вопроса
        reflection += f"<b>Тип вопроса:</b> {question_type}\n\n"
        
        # Анализ чувств
        if feelings:
            reflection += f"<b>Чувства в вопросе:</b> {', '.join(feelings)}\n"
            
            # Связь с профилем
            if self.weakest_vector == "ЧВ" and any(f in feelings for f in ["страх", "одиночество", "вина"]):
                reflection += "• Вопрос затрагивает вашу зону роста в отношениях (вектор ЧВ)\n"
            elif self.weakest_vector == "СБ" and "страх" in feelings:
                reflection += "• Вопрос связан с вашей реакцией на угрозу (вектор СБ)\n"
        else:
            reflection += "• В вопросе не выражены явные чувства (возможно, защита)\n"
        
        # Анализ тем
        if topics:
            reflection += f"\n<b>Основные темы:</b> {', '.join(topics)}\n"
            
            # Связь с профилем
            if self.weakest_vector == "ТФ" and "деньги" in topics:
                reflection += "• Финансовая тема - ваша ключевая зона роста\n"
            elif self.weakest_vector == "УБ" and "смысл" in topics:
                reflection += "• Поиск смысла - ваша ключевая зона роста\n"
        else:
            reflection += "\n• Тема вопроса не определена (общий вопрос)\n"
        
        # Анализ длины вопроса
        word_count = len(question.split())
        if word_count < 5:
            reflection += "\n• Короткий вопрос - возможно, требуется уточнение\n"
        elif word_count > 30:
            reflection += "\n• Развернутый вопрос - много деталей\n"
        
        # Анализ на основе профиля
        reflection += f"\n<b>На основе вашего профиля:</b>\n"
        reflection += f"• Тип восприятия: {self.user_data.get('perception_type', 'не определен')}\n"
        reflection += f"• Уровень мышления: {self.user_data.get('thinking_level', 5)}/9\n"
        
        if self.weakest_profile:
            reflection += f"• Ключевая характеристика: {self.weakest_profile.get('quote', '')}\n"
        
        # Глубинные паттерны (если есть)
        if self.deep_patterns:
            reflection += f"\n<b>Глубинные паттерны:</b>\n"
            
            if self.deep_patterns.get('attachment'):
                attachment_map = {
                    "secure": "надёжный",
                    "anxious": "тревожный",
                    "avoidant": "избегающий",
                    "disorganized": "дезорганизованный"
                }
                attachment = attachment_map.get(self.deep_patterns['attachment'], self.deep_patterns['attachment'])
                reflection += f"• Тип привязанности: {attachment}\n"
            
            if self.deep_patterns.get('defense_mechanisms'):
                defenses = self.deep_patterns['defense_mechanisms']
                if isinstance(defenses, list) and defenses:
                    reflection += f"• Защитные механизмы: {', '.join(defenses[:2])}\n"
            
            if self.deep_patterns.get('core_beliefs'):
                beliefs = self.deep_patterns['core_beliefs']
                if isinstance(beliefs, list) and beliefs:
                    reflection += f"• Глубинные убеждения: {', '.join(beliefs[:2])}\n"
        
        # Рекомендации на основе слабого вектора
        reflection += f"\n<b>Рекомендации:</b>\n"
        
        if self.weakest_vector == "СБ":
            reflection += "• Обратите внимание на телесные реакции\n"
            reflection += "• Исследуйте, как вы защищаетесь\n"
            reflection += "• Что происходит с дыханием, когда вы думаете об этом?\n"
        elif self.weakest_vector == "ТФ":
            reflection += "• Свяжите вопрос с вашими ресурсами\n"
            reflection += "• Подумайте о практических шагах\n"
            reflection += "• Какие ресурсы вам доступны?\n"
        elif self.weakest_vector == "УБ":
            reflection += "• Попробуйте посмотреть на ситуацию системно\n"
            reflection += "• Ищите закономерности\n"
            reflection += "• Как эта ситуация связана с другими областями жизни?\n"
        elif self.weakest_vector == "ЧВ":
            reflection += "• Обратите внимание на контекст отношений\n"
            reflection += "• Исследуйте, как вопрос влияет на связи с людьми\n"
            reflection += "• Кто мог бы поддержать вас в этом?\n"
        
        # Рекомендации на основе типа вопроса
        if question_type == "причинно-следственный":
            reflection += "\n• Вы ищете причины - это может указывать на потребность в контроле\n"
        elif question_type == "оценочный":
            reflection += "\n• Вы ищете оценку - возможно, не доверяете себе\n"
        elif question_type == "утверждение":
            reflection += "\n• Это скорее утверждение, чем вопрос - возможно, вам нужно подтверждение\n"
        
        return reflection
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Возвращает структурированный анализ вопроса
        """
        return {
            "feelings": self._get_feelings_from_text(question),
            "topics": self._get_topics_from_text(question),
            "question_type": self._analyze_question_type(question),
            "word_count": len(question.split()),
            "weakest_vector": self.weakest_vector,
            "weakest_level": self.weakest_level,
            "reflection": self.get_reflection_text(question)
        }
    
    def get_suggested_approach(self) -> str:
        """Возвращает рекомендуемый подход к ответу"""
        approaches = {
            "СБ": "Работать через телесные ощущения и безопасность",
            "ТФ": "Фокус на ресурсах и практических шагах",
            "УБ": "Системный анализ и поиск закономерностей",
            "ЧВ": "Акцент на отношениях и эмоциональных связях"
        }
        return approaches.get(self.weakest_vector, "Интегративный подход")


def create_analyzer_from_user_data(user_data: Dict[str, Any], user_name: str) -> QuestionAnalyzer:
    """Создает анализатор из данных пользователя"""
    return QuestionAnalyzer(user_data, user_name)


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'QuestionAnalyzer',
    'create_analyzer_from_user_data'
]
