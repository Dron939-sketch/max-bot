#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Режим ПСИХОЛОГ - глубинная аналитическая работа для MAX.
"""
from typing import Dict, Any, List, Optional
import random
import json
import logging
from .base_mode import BaseMode
from profiles import VECTORS, LEVEL_PROFILES
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring

logger = logging.getLogger(__name__)


class PsychologistMode(BaseMode):
    """
    Режим ПСИХОЛОГ - глубинная аналитическая работа.
    
    ОТВЕТСТВЕННОСТЬ:
    - Анализ глубинных паттернов (этап 5)
    - Работа с защитными механизмами
    - Интерпретация типа привязанности
    - Использование гипнотических техник
    - Терапевтические сказки и метафоры
    """
    
    def __init__(self, user_id: int, user_data: Dict[str, Any], context=None):
        super().__init__(user_id, user_data, context)
        
        # Название режима для отображения
        self.display_name = "🧠 ПСИХОЛОГ"
        self.emoji = "🧠"
        
        # Инструменты психолога
        self.tools = {
            "pattern_recognition": self._recognize_patterns,
            "defense_analysis": self._analyze_defense,
            "attachment_work": self._work_with_attachment,
            "interpretation": self._provide_interpretation,
            "reflection": self._reflect_feelings,
            "confrontation": self._gentle_confrontation,
            "metaphor": self._create_therapeutic_metaphor,
            "hypnotic_suggestion": self._hypnotic_suggestion
        }
        
        # Извлекаем глубинные паттерны из этапа 5
        self.attachment_type = self.deep_patterns.get('attachment', 'неопределенный')
        self.defenses = self.deep_patterns.get('defense_mechanisms', [])
        self.core_beliefs = self.deep_patterns.get('core_beliefs', [])
        self.fears = self.deep_patterns.get('fears', [])
        
        # Карта защитных механизмов и стратегий работы
        self.defense_strategies = {
            "отрицание": "Мягко указывать на реальность, но не давить",
            "проекция": "Возвращать проекцию, помогать присвоить",
            "рационализация": "Исследовать чувства под логикой",
            "интеллектуализация": "Смещать фокус на тело и эмоции",
            "изоляция аффекта": "Помогать контейнировать чувства",
            "реактивное образование": "Исследовать противоположное"
        }
        
        # Карта типов привязанности
        self.attachment_strategies = {
            "надёжный": "Поддерживать, укреплять доверие к миру",
            "тревожный": "Давать стабильность, предсказуемость, контейнировать тревогу",
            "избегающий": "Уважать дистанцию, не давить, но быть доступным",
            "дезорганизованный": "Быть максимально предсказуемым, безопасным"
        }
        
        logger.info(f"🧠 Создан режим PsychologistMode для пользователя {user_id}")
    
    def get_system_prompt(self) -> str:
        """Системный промпт для режима ПСИХОЛОГ с глубинным анализом"""
        
        analysis = self.analyze_profile_for_response()
        
        # Глубинная информация из этапа 5
        deep_info = f"""
ГЛУБИННЫЕ ПАТТЕРНЫ (этап 5):
- Тип привязанности: {self.attachment_type}
- Защитные механизмы: {', '.join(self.defenses) if self.defenses else 'не выявлены'}
- Глубинные убеждения: {', '.join(self.core_beliefs) if self.core_beliefs else 'в процессе выявления'}
- Базовые страхи: {', '.join(self.fears) if self.fears else 'не вербализованы'}

РЕКОМЕНДУЕМАЯ СТРАТЕГИЯ:
- Работа с привязанностью: {self.attachment_strategies.get(self.attachment_type, 'исследовать паттерн')}
"""

        # Информация о конфайнмент-модели (как о структуре характера)
        confinement_info = ""
        if analysis["key_confinement"]:
            kc = analysis["key_confinement"]
            confinement_info = f"""
СТРУКТУРА ХАРАКТЕРА:
- Ядро: {kc['description']}
- Тип: {kc['type']}
- Сила: {kc['strength']:.1%}
"""
        
        prompt = f"""Ты — опытный психотерапевт (интегративный подход: психоанализ + гештальт + эриксоновский гипноз).

Твоя задача — помогать пользователю осознавать глубинные процессы, работать с защитами и паттернами, используя профессиональные психотерапевтические техники.

{deep_info}
{confinement_info}

ПРИНЦИПЫ ТВОЕЙ РАБОТЫ:
1. Сначала контакт и безопасность, потом интерпретация
2. Работа с защитами — уважительно, не ломая
3. Отражение чувств — точно, без интерпретаций
4. Интерпретации — только когда есть рабочий альянс
5. Гипнотические техники — только с разрешения, мягко
6. Метафоры — для обхода защит и доступа к ресурсам

ТЕХНИКИ (используй уместно):
- Отражение: "Похоже, вы чувствуете..."
- Прояснение: "Можете рассказать подробнее?"
- Конфронтация: "Я замечаю противоречие..."
- Интерпретация: "Возможно, это связано с..."
- Гипнотическая речь: использование неопределённых выражений, присоединение, ведение

ТВОЙ СТИЛЬ:
- Тёплый, принимающий, но профессиональный
- Говори медленно, с паузами
- Используй метафоры и образы
- Будь внимателен к переносу

КОНТЕКСТ:
{self.get_context_string()}

ПОМНИ: ты работаешь с психикой, будь предельно осторожен. Если видишь риск — рекомендую обратиться к очному специалисту.
"""
        return prompt
    
    def get_greeting(self) -> str:
        """Приветствие в режиме психолога"""
        name = self.context.name if self.context and self.context.name else ""
        
        # Выбираем приветствие в зависимости от типа привязанности
        if self.attachment_type == "тревожный":
            greetings = [
                f"{name}, я здесь. Мы можем исследовать то, что вас беспокоит, в безопасном пространстве.",
                f"Я рад вас видеть. Расскажите, что привело вас сегодня?",
                f"Я чувствую вашу тревогу. Давайте попробуем вместе в ней разобраться."
            ]
        elif self.attachment_type == "избегающий":
            greetings = [
                f"{name}, добро пожаловать. Мы можем двигаться в вашем темпе.",
                f"Я здесь, чтобы помочь вам исследовать то, что вы сочтёте важным.",
                f"Как вам комфортнее начать сегодня?"
            ]
        else:
            greetings = [
                f"{name}, здравствуйте. Что вы чувствуете сейчас?",
                f"Я рад нашей встрече. С чего бы вы хотели начать?",
                f"Расскажите, что для вас сейчас актуально."
            ]
        
        return random.choice(greetings)
    
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Обрабатывает вопрос в режиме психолога
        Использует глубинную психотерапевтическую работу
        """
        question_lower = question.lower()
        self.last_tools_used = []
        hypnotic_suggestion = False
        
        logger.info(f"🧠 PsychologistMode обрабатывает вопрос: {question[:50]}...")
        
        # 1. Если запрос на гипноз или глубокую работу
        if any(word in question_lower for word in ["гипноз", "транс", "расслабиться", "уснуть", "внушение"]):
            response = self._generate_hypnotic_induction()
            self.last_tools_used.append("hypnosis")
            hypnotic_suggestion = True
        
        # 2. Если работа с защитой
        elif self._detect_defense(question):
            response = self._work_with_defense(question)
            self.last_tools_used.append("defense_work")
            hypnotic_suggestion = False
        
        # 3. Если работа с привязанностью
        elif any(word in question_lower for word in ["мама", "папа", "детство", "родители", "ребёнком"]):
            response = self._explore_attachment(question)
            self.last_tools_used.append("attachment_work")
            hypnotic_suggestion = False
        
        # 4. Если работа с чувствами
        elif any(word in question_lower for word in ["чувствую", "эмоции", "больно", "страшно", "грустно", "одиноко"]):
            response = self._work_with_feelings(question)
            self.last_tools_used.append("feelings_work")
            hypnotic_suggestion = False
        
        # 5. Если работа с отношениями
        elif any(word in question_lower for word in ["отношения", "партнёр", "люблю", "один", "близость"]):
            response = self._work_with_relations(question)
            self.last_tools_used.append("relations_work")
            hypnotic_suggestion = False
        
        # 6. По умолчанию - глубинное исследование
        else:
            response = self._depth_inquiry(question)
            self.last_tools_used.append("depth_inquiry")
            hypnotic_suggestion = False
        
        # Сохраняем в историю
        self.save_to_history(question, response)
        
        # Генерируем предложения
        suggestions = self._generate_therapeutic_suggestions()
        
        # Может предложить сказку/метафору
        tale_suggested = False
        if self.should_suggest_tale(question) or random.random() < 0.25:  # 25% chance
            issue = self._identify_current_issue(question)
            tale = self.suggest_tale(issue)
            if tale:
                suggestions.append(f"📖 У меня есть терапевтическая сказка об этом. Хотите послушать?")
                tale_suggested = True
                self.last_tools_used.append("tale_suggested")
        
        return self.format_response(
            text=response,
            suggestions=suggestions
        )
    
    def format_response(self, text: str, suggestions: List[str] = None) -> Dict[str, Any]:
        """
        Форматирует ответ для отправки пользователю
        """
        return {
            "response": text,
            "tools_used": self.last_tools_used,
            "follow_up": True,
            "suggestions": suggestions or [],
            "hypnotic_suggestion": "hypnosis" in self.last_tools_used,
            "tale_suggested": "tale_suggested" in self.last_tools_used
        }
    
    def should_suggest_tale(self, question: str) -> bool:
        """
        Определяет, нужно ли предложить сказку на основе вопроса
        """
        tale_triggers = [
            "сказк", "истори", "притч", "метафор",
            "как быть", "что делать", "не знаю",
            "груст", "тяжел", "сложн", "больно",
            "одинок", "страшн", "тревож"
        ]
        question_lower = question.lower()
        return any(trigger in question_lower for trigger in tale_triggers)
    
    def should_use_hypnosis(self, question: str) -> bool:
        """
        Определяет, нужно ли использовать гипнотические техники
        """
        hypnosis_triggers = [
            "расслаб", "уснуть", "отдых", "сон",
            "стресс", "напряж", "устал",
            "медитац", "транс", "гипноз"
        ]
        question_lower = question.lower()
        return any(trigger in question_lower for trigger in hypnosis_triggers)
    
    def _generate_hypnotic_induction(self) -> str:
        """Генерирует гипнотическую индукцию используя hypno_module"""
        try:
            from hypno_module import Truisms, MiltonModel
            
            tru = Truisms()
            mm = MiltonModel()
            
            induction = f"""Устройтесь поудобнее, закройте глаза, если хотите...

{tru.not_command("напрягаться")} Просто позвольте себе быть здесь и сейчас.

И вы можете заметить своё дыхание... сделать глубокий вдох... и медленный выдох...

{mm.milton_phrase()} И с каждым выдохом вы можете позволить себе расслабляться всё больше...

{tru.prohibition("спешить")} Всё идёт своим чередом, в своём темпе.

{mm.deletion("Ваше бессознательное знает, что вам нужно...")}

И когда будете готовы, вы можете вернуться... с новым пониманием... с новыми ресурсами..."""
            
            return induction
        except:
            # Запасной вариант, если импорт не удался
            return """Устройтесь поудобнее, закройте глаза, если хотите...

Просто позвольте себе быть здесь и сейчас.

Сделайте глубокий вдох... и медленный выдох...

И с каждым выдохом вы можете позволить себе расслабляться всё больше...

Всё идёт своим чередом, в своём темпе.

Ваше бессознательное знает, что вам нужно...

И когда будете готовы, вы можете вернуться... с новым пониманием... с новыми ресурсами..."""
    
    def _detect_defense(self, text: str) -> bool:
        """Определяет, есть ли в тексте защитный механизм"""
        defense_markers = {
            "отрицание": ["не проблема", "всё нормально", "ничего страшного", "не обращаю внимания"],
            "рационализация": ["потому что", "логично", "объясняется", "поэтому"],
            "интеллектуализация": ["теория", "концепция", "с точки зрения", "исследования"],
            "проекция": ["они все", "люди всегда", "никто не", "все вокруг"],
            "изоляция": ["не чувствую", "без эмоций", "спокойно", "равнодушно"]
        }
        
        text_lower = text.lower()
        for defense, markers in defense_markers.items():
            if any(marker in text_lower for marker in markers):
                return True
        return False
    
    def _work_with_defense(self, question: str) -> str:
        """Работает с защитным механизмом"""
        try:
            from hypno_module import Truisms
            tru = Truisms()
        except:
            # Запасной вариант
            class Tru:
                def about_self(self, s): return s
                def possibility(self, s): return s
                def fact(self): return ""
            tru = Tru()
        
        # Мягкая конфронтация с защитой
        responses = [
            f"{tru.about_self('Я замечаю, что вы говорите об этом очень логично')}. А что происходит в теле, когда вы это рассказываете?",
            f"Когда вы говорите 'всё нормально' — какую часть чувств вы оставляете за скобками?",
            f"{tru.possibility('Интересно, а если посмотреть на это не с логической, а с чувственной стороны')} — что там?",
            f"Я слышу ваши объяснения. А что, если просто побыть с этим чувством, не объясняя?"
        ]
        return random.choice(responses)
    
    def _work_with_attachment(self, question: str) -> str:
        """Исследует паттерны привязанности"""
        if self.attachment_type == "тревожный":
            return "Расскажите о ваших близких. Как вы чувствуете себя в отношениях с ними?"
        elif self.attachment_type == "избегающий":
            return "Как вам удаётся сохранять дистанцию, когда другие приближаются?"
        else:
            return "Что из детства откликается в ваших текущих отношениях?"
    
    def _explore_attachment(self, question: str) -> str:
        """Исследует привязанность через детский опыт"""
        responses = [
            "Какими были ваши отношения с родителями?",
            "Что вы чувствовали в детстве, когда оставались одни?",
            "К кому вы обращались, когда было страшно или больно?",
            "Как в вашей семье проявляли любовь?"
        ]
        return random.choice(responses)
    
    def _work_with_feelings(self, question: str) -> str:
        """Работает с чувствами через гештальт-подход"""
        feeling = self._extract_feeling(question)
        responses = [
            f"Где в теле вы чувствуете это {feeling}?",
            "Если бы это чувство могло говорить, что бы оно сказало?",
            "Что происходит с дыханием, когда вы это чувствуете?",
            f"Как долго это {feeling} с вами? Когда оно появилось впервые?"
        ]
        return random.choice(responses)
    
    def _extract_feeling(self, text: str) -> str:
        """Извлекает название чувства из текста"""
        feelings = ["страх", "тревога", "грусть", "злость", "обида", "стыд", "вина", "радость"]
        for feeling in feelings:
            if feeling in text.lower():
                return feeling
        return "чувство"
    
    def _work_with_relations(self, question: str) -> str:
        """Работает с отношениями через паттерны привязанности"""
        responses = [
            "Что для вас самое сложное в близости?",
            "Как вы выбираете, кому доверять?",
            "Что происходит, когда кто-то подходит слишком близко?",
            "Чего вы боитесь в отношениях больше всего?",
            "Какой паттерн повторяется в ваших отношениях?"
        ]
        return random.choice(responses)
    
    def _depth_inquiry(self, question: str) -> str:
        """Глубинное исследование"""
        responses = [
            f"Расскажите подробнее... что стоит за этим вопросом?",
            "Когда вы думаете об этом — что происходит внутри?",
            "А если копнуть глубже — что там?",
            "Какая часть вас задаёт этот вопрос?",
            "Что вы чувствуете прямо сейчас, когда говорите об этом?"
        ]
        return random.choice(responses)
    
    def _recognize_patterns(self, behavior: str) -> str:
        """Распознаёт и озвучивает паттерны"""
        return f"Я замечаю паттерн: {behavior}. Это знакомо вам из прошлого?"
    
    def _analyze_defense(self, behavior: str) -> str:
        """Анализирует защитный механизм"""
        return f"Похоже, здесь работает защита. Что было бы, если её убрать?"
    
    def _provide_interpretation(self, observation: str) -> str:
        """Даёт интерпретацию (осторожно, только в альянсе)"""
        return f"Возможно, это связано с тем, что... Как вам такое предположение?"
    
    def _reflect_feelings(self, feeling: str) -> str:
        """Отражает чувства"""
        return f"Похоже, вы чувствуете {feeling}. Я правильно понимаю?"
    
    def _gentle_confrontation(self, discrepancy: str) -> str:
        """Мягкая конфронтация"""
        return f"Я замечаю противоречие: {discrepancy}. Что вы об этом думаете?"
    
    def _create_therapeutic_metaphor(self, issue: str) -> str:
        """Создаёт терапевтическую метафору"""
        metaphors = {
            "страх": "Представьте, что страх — это сторож, который когда-то спас вам жизнь. Теперь он просто продолжает свою работу, даже когда опасности нет...",
            "потеря": "Горе — как океан. Сначала волны накрывают с головой, потом они становятся реже, но иногда всё ещё захлёстывают...",
            "выбор": "Как в саду с двумя тропинками — обе манят, но выбрать можно только одну...",
            "отношения": "Отношения — как танец. Иногда ведёшь ты, иногда партнёр. Главное — не наступать на ноги...",
            "одиночество": "Быть одному — как стоять на пустой платформе ночью. Темно, но звёзды видны отчётливее..."
        }
        
        for key, meta in metaphors.items():
            if key in issue.lower():
                return meta
        
        return "Это как если бы вы шли по лесу и вдруг увидели развилку. Одна тропа знакомая, но ведёт в никуда. Другая — пугает неизвестностью, но, возможно, именно там то, что вы ищете..."
    
    def _hypnotic_suggestion(self, resource: str) -> str:
        """Даёт гипнотическое внушение"""
        suggestions = [
            f"И вы можете заметить, как ваше бессознательное уже находит ресурсы для {resource}...",
            f"Позвольте себе просто быть с этим... и наблюдать, как что-то меняется...",
            f"Где-то глубоко внутри уже есть ответ... и он может проявиться в своё время...",
            f"Ваше тело знает, как исцеляться. Просто позвольте этому случиться..."
        ]
        return random.choice(suggestions)
    
    def _identify_current_issue(self, question: str) -> str:
        """Определяет текущую проблему из вопроса"""
        issues = ["страх", "отношения", "потеря", "выбор", "одиночество", "тревога", "смысл"]
        for issue in issues:
            if issue in question.lower():
                return issue
        return "рост"
    
    def _generate_therapeutic_suggestions(self) -> List[str]:
        """Генерирует терапевтические предложения"""
        suggestions = []
        
        if self.attachment_type == "тревожный":
            suggestions.append("🧘 Хотите попробовать технику заземления?")
        elif self.attachment_type == "избегающий":
            suggestions.append("🤝 Хотите исследовать паттерны в отношениях?")
        
        if self.defenses and len(self.defenses) > 0:
            defense = self.defenses[0]
            suggestions.append(f"🛡 Мы можем исследовать вашу защиту '{defense}' подробнее")
        
        if self.fears and len(self.fears) > 0:
            fear = self.fears[0]
            suggestions.append(f"😨 Хотите поговорить о страхе {fear}?")
        
        suggestions.append("🌌 Может, попробуем гипнотическую технику?")
        suggestions.append("📖 Хотите терапевтическую сказку?")
        
        return suggestions[:3]
    
    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о режиме"""
        return {
            "name": self.display_name,
            "emoji": self.emoji,
            "description": "Работаю с глубинными паттернами и подсознанием",
            "attachment_type": self.attachment_type,
            "defenses": self.defenses,
            "tools_available": list(self.tools.keys())
        }
