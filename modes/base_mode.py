#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для всех режимов общения.
Интегрирован с конфайнмент-моделью и гипнотическими техниками.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime
import random

# Импорты остаются теми же
from models import ConfinementModel9, UserContext
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring
from profiles import VECTORS, LEVEL_PROFILES, DILTS_LEVELS

logger = logging.getLogger(__name__)


class BaseMode(ABC):
    """
    Базовый класс для всех режимов общения.
    Интегрирован с конфайнмент-моделью и гипнотическими техниками.
    """
    
    def __init__(self, user_id: int, user_data: Dict[str, Any], context: Optional[UserContext] = None):
        self.user_id = user_id
        self.user_data = user_data
        self.context = context
        self.name = self.__class__.__name__
        
        # Базовая информация о пользователе
        self.profile = user_data.get("profile_data", {})
        self.perception_type = user_data.get("perception_type", "не определен")
        self.thinking_level = user_data.get("thinking_level", 5)
        self.deep_patterns = user_data.get("deep_patterns", {})
        
        # История диалога
        self.history = user_data.get("history", [])
        
        # Для отслеживания использованных инструментов
        self.last_tools_used = []
        
        # === ИНИЦИАЛИЗАЦИЯ КЛЮЧЕВЫХ СИСТЕМ ===
        
        # 1. Конфайнмент-модель (ограничивающие убеждения)
        self.confinement_model = None
        if "confinement_model" in user_data:
            confinement_data = user_data["confinement_model"]
            if isinstance(confinement_data, dict):
                self.confinement_model = ConfinementModel9.from_dict(confinement_data)
        
        # 2. Гипнотический оркестратор (для трансовых техник)
        self.hypno = HypnoOrchestrator()
        
        # 3. Терапевтические сказки
        self.tales = TherapeuticTales()
        
        # 4. Якорение (для ресурсных состояний)
        self.anchoring = Anchoring()
        
        # 5. Векторные scores (СБ, ТФ, УБ, ЧВ)
        self.scores = {}
        for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
            levels = user_data.get("behavioral_levels", {}).get(k, [])
            self.scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        # 6. Определяем самое слабое место (главный тормоз)
        if self.scores:
            min_vector = min(self.scores.items(), key=lambda x: self._level(x[1]))
            self.weakest_vector, self.weakest_score = min_vector
            self.weakest_level = self._level(self.weakest_score)
            self.weakest_profile = LEVEL_PROFILES.get(self.weakest_vector, {}).get(self.weakest_level, {})
        else:
            self.weakest_vector = "СБ"
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
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Возвращает системный промпт для режима"""
        pass
    
    @abstractmethod
    def get_greeting(self) -> str:
        """Возвращает приветствие режима"""
        pass
    
    @abstractmethod
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Обрабатывает вопрос пользователя
        Возвращает: {
            "response": str,           # текст ответа
            "tools_used": List[str],   # использованные инструменты
            "follow_up": bool,         # нужно ли уточнение
            "suggestions": List[str],  # предложения для продолжения
            "hypnotic_suggestion": bool, # было ли гипнотическое внушение
            "tale_suggested": bool,    # была ли предложена сказка
            "should_save": bool        # нужно ли сохранять в историю
        }
        """
        pass
    
    def analyze_profile_for_response(self) -> Dict[str, Any]:
        """Анализирует профиль для настройки ответа"""
        analysis = {
            "attention_focus": self._get_attention_focus(),
            "thinking_depth": self._get_thinking_depth(),
            "pain_points": self._get_pain_points(),
            "growth_area": self._get_growth_area(),
            "weakest_vector": self.weakest_vector,
            "weakest_level": self.weakest_level,
            "weakest_description": self.weakest_profile.get('quote', ''),
            "key_confinement": self._get_key_confinement_info(),
            "loops": self._get_loops_info(),
            "vector_scores": self.scores
        }
        return analysis
    
    def _get_key_confinement_info(self) -> Optional[Dict]:
        """Возвращает информацию о ключевом ограничении"""
        if self.confinement_model and self.confinement_model.key_confinement:
            elem = self.confinement_model.key_confinement.get('element')
            if elem:
                return {
                    'id': elem.id,
                    'name': elem.name,
                    'description': elem.description,
                    'type': elem.element_type,
                    'vector': elem.vector,
                    'strength': elem.strength
                }
        return None
    
    def _get_loops_info(self) -> List[Dict]:
        """Возвращает информацию о циклах"""
        if self.confinement_model and self.confinement_model.loops:
            return [
                {
                    'type': loop['type'],
                    'description': loop['description'],
                    'strength': loop['strength']
                }
                for loop in self.confinement_model.loops
            ]
        return []
    
    def _get_attention_focus(self) -> str:
        """Определяет фокус внимания пользователя"""
        if self.perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
            return "external"
        return "internal"
    
    def _get_thinking_depth(self) -> str:
        """Определяет глубину мышления"""
        if self.thinking_level <= 3:
            return "concrete"
        elif self.thinking_level <= 6:
            return "systemic"
        else:
            return "deep"
    
    def _get_pain_points(self) -> List[str]:
        """Определяет болевые точки из профиля"""
        points = []
        
        # Из самого слабого вектора
        if self.weakest_profile:
            points.extend(self.weakest_profile.get('pain_costs', []))
        
        # Из глубинных паттернов
        if self.deep_patterns:
            fears = self.deep_patterns.get('fears', [])
            points.extend(fears[:2])
            
            defenses = self.deep_patterns.get('defenses', [])
            if defenses:
                points.append(f"защита: {defenses[0]}")
        
        return [p for p in points if p][:3]  # максимум 3 пункта
    
    def _get_growth_area(self) -> str:
        """Определяет зону роста из DILTS_LEVELS"""
        dilts_counts = self.user_data.get("dilts_counts", {})
        if dilts_counts:
            dominant = max(dilts_counts.items(), key=lambda x: x[1])[0]
            return DILTS_LEVELS.get(dominant, "Поведение")
        return "Поведение"
    
    def get_context_string(self) -> str:
        """Возвращает контекст для вставки в промпт"""
        lines = []
        
        if self.context:
            if self.context.gender:
                lines.append(f"Пол пользователя: {'мужской' if self.context.gender == 'male' else 'женский'}")
            if self.context.age:
                lines.append(f"Возраст: {self.context.age}")
            if self.context.city:
                lines.append(f"Город: {self.context.city}")
            
            day = self.context.get_day_context()
            lines.append(f"Время: {day['time_str']}, {day['weekday']}")
            
            if self.context.weather_cache:
                w = self.context.weather_cache
                lines.append(f"Погода: {w['icon']} {w['description']}, {w['temp']}°C")
        
        return "\n".join(lines)
    
    def get_context_dict(self) -> Dict[str, Any]:
        """Возвращает контекст в виде словаря для JSON"""
        if not self.context:
            return {}
        
        day = self.context.get_day_context()
        result = {
            "gender": self.context.gender,
            "age": self.context.age,
            "city": self.context.city,
            "time": day['time_str'],
            "weekday": day['weekday'],
            "is_weekend": day['is_weekend']
        }
        
        if self.context.weather_cache:
            w = self.context.weather_cache
            result["weather"] = {
                "icon": w['icon'],
                "description": w['description'],
                "temp": w['temp']
            }
        
        return result
    
    def save_to_history(self, question: str, response: str, tools_used: List[str] = None):
        """Сохраняет диалог в историю"""
        self.history.append({
            "role": "user",
            "text": question,
            "timestamp": datetime.now().isoformat()
        })
        
        self.history.append({
            "role": "assistant",
            "text": response,
            "timestamp": datetime.now().isoformat(),
            "mode": self.name,
            "tools_used": tools_used or self.last_tools_used
        })
        
        # Обновляем в user_data
        self.user_data["history"] = self.history
    
    def suggest_tale(self, issue: str = None) -> Optional[Dict]:
        """Предлагает терапевтическую сказку по проблеме"""
        if not issue:
            # Если проблема не указана, берём из слабого вектора
            vector_names = {
                "СБ": "страх", 
                "ТФ": "деньги", 
                "УБ": "понимание", 
                "ЧВ": "отношения"
            }
            issue = vector_names.get(self.weakest_vector, "рост")
        
        tale = self.tales.get_tale_for_issue(issue)
        return tale
    
    def create_anchor(self, trigger: str, resource_state: str) -> Dict:
        """Создаёт якорь для ресурсного состояния"""
        return self.anchoring.create_anchor(self.user_id, trigger, resource_state)
    
    def fire_anchor(self, trigger: str) -> bool:
        """Активирует якорь"""
        return self.anchoring.fire_anchor(self.user_id, trigger)
    
    def should_use_hypnosis(self, question: str) -> bool:
        """Определяет, нужно ли использовать гипнотические техники"""
        hypno_triggers = ["боюсь", "тревога", "страх", "паника", "не могу уснуть", 
                          "напряжение", "стресс", "расслабиться", "успокоиться"]
        
        question_lower = question.lower()
        for trigger in hypno_triggers:
            if trigger in question_lower:
                return True
        return False
    
    def should_suggest_tale(self, question: str) -> bool:
        """Определяет, нужно ли предложить сказку"""
        tale_triggers = ["сказка", "история", "притча", "метафора", 
                         "расскажи историю", "хочу сказку"]
        
        question_lower = question.lower()
        for trigger in tale_triggers:
            if trigger in question_lower:
                return True
        return False
    
    def format_response(self, text: str, suggestions: List[str] = None) -> Dict[str, Any]:
        """
        Форматирует ответ для отправки пользователю
        
        Args:
            text: Основной текст ответа
            suggestions: Предложения для продолжения диалога
            
        Returns:
            Словарь с полным ответом
        """
        if suggestions is None:
            suggestions = []
        
        return {
            "response": text,
            "suggestions": suggestions,
            "tools_used": self.last_tools_used,
            "follow_up": len(suggestions) > 0,
            "hypnotic_suggestion": False,
            "tale_suggested": False,
            "should_save": True
        }
