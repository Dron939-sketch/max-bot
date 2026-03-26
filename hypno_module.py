#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hypno_module.py
Комплексный модуль гипнотического воздействия для виртуального психолога
Основан на книгах А.Ю. Мейстера "Теория манипуляции" и его методе терапевтических сказок
Версия: 1.1 - ДОБАВЛЕНА ИНТЕГРАЦИЯ С КОНФАЙНТМЕНТ-МОДЕЛЬЮ
"""

import random
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# МОДУЛЬ 1: ПРЕСУППОЗИЦИИ - скрытые внушения, подаваемые как уже принятые
# ============================================================================

class PreSuppositions:
    """Пресуппозиции - информация, подразумеваемая как уже согласованная"""
    
    def __init__(self):
        self.introductory_templates = [
            "Полагаю, вы понимаете, что {suggestion}",
            "Вы, конечно, знаете, что {suggestion}",
            "Как вы уже поняли, {suggestion}",
            "Здорово, что вы осознаёте, что {suggestion}",
            "Вы в курсе, что {suggestion}?",
            "Не могу не отметить, что {suggestion}",
            "Вам уже известно, что {suggestion}",
            "Согласитесь, что {suggestion}"
        ]
        
        self.implied_templates = [
            "Дай знать, когда {suggestion}",
            "Когда {suggestion}, сразу заметишь это",
            "Пока ты будешь {action}, ты поймёшь, что {suggestion}",
            "После того как {suggestion}, {action}",
            "Как только {suggestion}, ты почувствуешь"
        ]
        
        self.subordinate_templates = [
            "Благодаря тому, что {suggestion}, {main_message}",
            "Поскольку {suggestion}, я предлагаю {main_message}",
            "Так как {suggestion}, {main_message}",
            "Зная, что {suggestion}, {main_message}",
            "Учитывая, что {suggestion}, {main_message}"
        ]
        
        self.clarifying_templates = [
            "Когда ты {suggestion}?",
            "Как ты планируешь {suggestion}?",
            "Что в {suggestion} для тебя самое важное?",
            "Интересно, что произойдёт, когда ты {suggestion}?",
            "Как ты узнаешь, что {suggestion}?"
        ]
    
    def introductory(self, suggestion: str) -> str:
        """Внушение через вводные слова"""
        return random.choice(self.introductory_templates).format(suggestion=suggestion)
    
    def implied(self, suggestion: str, action: str = "думать об этом") -> str:
        """Подразумеваемое указание"""
        template = random.choice(self.implied_templates)
        return template.format(suggestion=suggestion, action=action)
    
    def subordinate(self, suggestion: str, main_message: str) -> str:
        """Внушение в придаточном предложении"""
        template = random.choice(self.subordinate_templates)
        return template.format(suggestion=suggestion, main_message=main_message)
    
    def clarifying(self, suggestion: str) -> str:
        """Уточняющий вопрос, предполагающий факт"""
        template = random.choice(self.clarifying_templates)
        return template.format(suggestion=suggestion)


# ============================================================================
# МОДУЛЬ 2: ТРЮИЗМЫ - утверждения, с которыми невозможно не согласиться
# ============================================================================

class Truisms:
    """Трюизмы - утверждения, вызывающие автоматическое согласие"""
    
    def __init__(self):
        self.facts = [
            "Ты сейчас читаешь этот текст",
            "У тебя есть тело, и ты его чувствуешь",
            "Ты дышишь прямо сейчас",
            "В твоей жизни есть люди, которые тебе дороги",
            "Ты хочешь жить лучше",
            "У тебя есть опыт, который ты приобрел в жизни",
            "Ты уже многое преодолел",
            "Каждый день ты учишься чему-то новому"
        ]
        
        self.possibility_templates = [
            "В твоей жизни наверняка есть {something}",
            "Не исключено, что {suggestion}",
            "Возможно, ты замечал, что {suggestion}",
            "Иногда бывает, что {suggestion}",
            "Бывает, что {suggestion}",
            "Случается, что {suggestion}"
        ]
        
        self.or_not_templates = [
            "Ты можешь {positive}, а можешь и {negative}. И то и другое нормально.",
            "Бывает, что {positive}, а бывает, что {negative}",
            "{positive} или {negative} — оба варианта имеют право на существование"
        ]
        
        self.condition_templates = [
            "{statement}, если {condition}",
            "Когда {condition}, тогда {statement}",
            "Как только {condition}, {statement}"
        ]
        
        self.about_self_templates = [
            "Мне кажется, что {feeling}",
            "Я чувствую, что {feeling}",
            "Мой опыт подсказывает, что {feeling}",
            "Я замечаю, что {feeling}",
            "Похоже, что {feeling}"
        ]
        
        self.proverbs = [
            "За одного битого двух небитых дают",
            "Без труда не вытянешь и рыбку из пруда",
            "Всё, что ни делается, всё к лучшему",
            "Дорогу осилит идущий",
            "Вода камень точит",
            "Терпение и труд всё перетрут",
            "Глаза боятся, а руки делают",
            "Утро вечера мудренее",
            "Как аукнется, так и откликнется"
        ]
        
        self.opposites = {
            "получится": "не получится",
            "согласишься": "не согласишься",
            "поймешь": "не поймешь",
            "захочешь": "не захочешь",
            "сделаешь": "не сделаешь",
            "знаешь": "не знаешь"
        }
    
    def fact(self) -> str:
        """Очевидный факт"""
        return random.choice(self.facts)
    
    def possibility(self, suggestion: str, something: str = "что-то важное") -> str:
        """Смягчение через возможность"""
        template = random.choice(self.possibility_templates)
        if "{something}" in template:
            return template.format(something=something)
        return template.format(suggestion=suggestion)
    
    def or_not(self, positive: str) -> str:
        """А или не А - тождественная истина"""
        words = positive.split()
        if words and words[0] in self.opposites:
            negative = positive.replace(words[0], self.opposites[words[0]], 1)
        else:
            negative = f"не {positive}"
        template = random.choice(self.or_not_templates)
        return template.format(positive=positive, negative=negative)
    
    def condition(self, statement: str, condition: str) -> str:
        """Условный трюизм"""
        template = random.choice(self.condition_templates)
        return template.format(statement=statement, condition=condition)
    
    def about_self(self, feeling: str) -> str:
        """Высказывание о себе (неоспоримо)"""
        template = random.choice(self.about_self_templates)
        return template.format(feeling=feeling)
    
    def proverb(self) -> str:
        """Пословица или поговорка"""
        return random.choice(self.proverbs)


# ============================================================================
# МОДУЛЬ 3: ПСЕВДОЛОГИКА - создание иллюзии логических связей
# ============================================================================

class PseudoLogic:
    """Псевдологика - искусственные логические связи"""
    
    def __init__(self):
        self.therefore_templates = [
            "{premise}, значит, {conclusion}",
            "{premise}, следовательно, {conclusion}",
            "{premise}, поэтому {conclusion}",
            "{premise}, а значит {conclusion}",
            "{premise}, из чего следует {conclusion}"
        ]
        
        self.temporal_templates = [
            "Пока {action1}, {action2}",
            "В то время как {action1}, {action2}",
            "После того как {action1}, {action2}",
            "Когда {action1}, тогда {action2}",
            "По мере того как {action1}, {action2}"
        ]
        
        self.causal_templates = [
            "{cause}, поэтому {effect}",
            "{effect}, потому что {cause}",
            "{cause} ведёт к {effect}",
            "Если {cause}, то {effect}",
            "{cause} неизбежно приводит к {effect}"
        ]
    
    def therefore(self, premise: str, conclusion: str) -> str:
        """Логический вывод (приравнивание)"""
        template = random.choice(self.therefore_templates)
        return template.format(premise=premise, conclusion=conclusion)
    
    def temporal(self, action1: str, action2: str) -> str:
        """Временная связка"""
        template = random.choice(self.temporal_templates)
        return template.format(action1=action1, action2=action2)
    
    def cause_effect(self, cause: str, effect: str) -> str:
        """Причинно-следственная связь"""
        template = random.choice(self.causal_templates)
        return template.format(cause=cause, effect=effect)
    
    def and_connection(self, statement1: str, statement2: str) -> str:
        """Связывание через 'и'"""
        return f"{statement1}, и {statement2}"
    
    def but_connection(self, statement1: str, statement2: str) -> str:
        """Противопоставление с сохранением связи"""
        return f"{statement1}, но {statement2}"


# ============================================================================
# МОДУЛЬ 4: НЕГАТИВНО-ПАРАДОКСАЛЬНЫЕ КОМАНДЫ - внушение через отрицание
# ============================================================================

class ParadoxCommands:
    """Парадоксальные команды - запрет провоцирует желание"""
    
    def __init__(self):
        self.not_templates = [
            "Я не буду просить тебя {command}",
            "Тебе необязательно {command}",
            "Ты можешь не {command}",
            "Я не говорю, что тебе нужно {command}",
            "Не стоит {command}",
            "Я бы не стал тебя просить {command}"
        ]
        
        self.prohibition_templates = [
            "Только не вздумай {forbidden}!",
            "Не смей {forbidden}!",
            "Я запрещаю тебе {forbidden}",
            "Тебе не стоит {forbidden}",
            "Ни в коем случае не {forbidden}",
            "Пожалуйста, не {forbidden}"
        ]
        
        self.limit_templates = [
            "{action}, но только {condition}",
            "Ты можешь {action}, пока {condition}",
            "{action} возможно лишь тогда, когда {condition}",
            "{action} только если {condition}"
        ]
    
    def not_command(self, command: str) -> str:
        """Внушение через отрицание (Не думай о белой обезьяне)"""
        template = random.choice(self.not_templates)
        return template.format(command=command)
    
    def prohibition(self, forbidden: str) -> str:
        """Запрет-провокация"""
        template = random.choice(self.prohibition_templates)
        return template.format(forbidden=forbidden)
    
    def false_limit(self, action: str, condition: str) -> str:
        """Мнимое ограничение"""
        template = random.choice(self.limit_templates)
        return template.format(action=action, condition=condition)
    
    def reverse_psychology(self, desired: str, opposite: str) -> str:
        """Обратная психология"""
        return f"Лучше {opposite}, чем {desired}. Правда?"


# ============================================================================
# МОДУЛЬ 5: ГИПНОТИЧЕСКИЕ ВОПРОСЫ - вопросы, которые внушают
# ============================================================================

class HypnoQuestions:
    """Вопросы, содержащие скрытые внушения"""
    
    def __init__(self):
        self.simple_templates = [
            "{suggestion}?",
            "Ты {suggestion}?",
            "Можешь {suggestion}?",
            "Готов {suggestion}?",
            "Согласен {suggestion}?"
        ]
        
        self.rhetorical_templates = [
            "Разве {suggestion}?",
            "Неужели {suggestion}?",
            "Кому не хочется {suggestion}?",
            "Как ты думаешь, {suggestion}?",
            "Скажи, разве не так, что {suggestion}?"
        ]
        
        self.return_templates = [
            "{statement}. Да?",
            "{statement}. Правда?",
            "{statement}. Согласен?",
            "{statement}. Чувствуешь?",
            "{statement}. Не так ли?"
        ]
        
        self.alternative_templates = [
            "Ты предпочитаешь {option1} или {option2}?",
            "Тебе больше подходит {option1} или {option2}?",
            "Выбирай: {option1} или {option2}",
            "Что для тебя важнее: {option1} или {option2}?"
        ]
        
        self.unequal_templates = [
            "Тебе {good_option} или лучше {bad_option}?",
            "Что для тебя важнее: {good_option} или {bad_option}?",
            "Ты выберешь {good_option} или всё-таки {bad_option}?"
        ]
    
    def simple(self, suggestion: str) -> str:
        """Простой внушающий вопрос"""
        template = random.choice(self.simple_templates)
        return template.format(suggestion=suggestion)
    
    def rhetorical(self, suggestion: str) -> str:
        """Риторический вопрос"""
        template = random.choice(self.rhetorical_templates)
        return template.format(suggestion=suggestion)
    
    def return_question(self, statement: str) -> str:
        """Возвратный вопрос (утверждение + вопрос)"""
        template = random.choice(self.return_templates)
        return template.format(statement=statement)
    
    def alternative(self, option1: str, option2: str) -> str:
        """Альтернативный вопрос (выбор без выбора)"""
        template = random.choice(self.alternative_templates)
        return template.format(option1=option1, option2=option2)
    
    def unequal_choice(self, good_option: str, bad_option: str) -> str:
        """Неравный выбор"""
        template = random.choice(self.unequal_templates)
        return template.format(good_option=good_option, bad_option=bad_option)
    
    def presupposition(self, presupposition: str) -> str:
        """Вопрос с пресуппозицией"""
        return f"Когда ты {presupposition}?"


# ============================================================================
# МОДУЛЬ 6: МИЛТОН-МОДЕЛЬ - язык неопределенности для бессознательного
# ============================================================================

class MiltonModel:
    """Милтон-модель - неопределенный язык для работы с бессознательным"""
    
    def __init__(self):
        self.nominalizations = [
            "понимание", "осознание", "отношение", "доверие", "свобода",
            "безопасность", "уверенность", "спокойствие", "развитие", "рост",
            "изменение", "исцеление", "любовь", "счастье", "радость",
            "сила", "мудрость", "опыт", "интуиция", "вдохновение"
        ]
        
        self.vague_verbs = [
            "сделать", "почувствовать", "понять", "осознать", "изменить",
            "двигаться", "развиваться", "открыть", "обнаружить", "найти",
            "довериться", "расслабиться", "отпустить", "принять", "позволить",
            "заметить", "увидеть", "услышать"
        ]
        
        self.vague_nouns = [
            "человек", "люди", "некто", "кто-то", "каждый",
            "некоторые", "многие", "окружающие", "другие", "другой"
        ]
        
        self.deletions = [
            "Можно...", "Хочется...", "Бывает...", "Случается...", 
            "Иногда...", "Порой...", "Возможно...", "Может быть..."
        ]
        
        self.unspecific_nouns = [
            "это", "то", "нечто", "что-то", "все это",
            "такое", "эта ситуация", "это состояние", "то самое"
        ]
    
    def nominalization(self) -> str:
        """Возвращает номинализацию"""
        return random.choice(self.nominalizations)
    
    def vague_verb(self) -> str:
        """Возвращает неопределенный глагол"""
        return random.choice(self.vague_verbs)
    
    def vague_noun(self) -> str:
        """Возвращает неопределенное имя"""
        return random.choice(self.vague_nouns)
    
    def deletion(self, thought: str = "") -> str:
        """Опущение - незаконченная мысль"""
        start = random.choice(self.deletions)
        if thought:
            return f"{start} {thought}"
        return start
    
    def unspecific(self) -> str:
        """Неспецифицированное существительное"""
        return random.choice(self.unspecific_nouns)
    
    def milton_phrase(self) -> str:
        """Генерирует фразу в стиле Милтон-модели"""
        templates = [
            f"И {self.vague_noun()} может {self.vague_verb()} это {self.unspecific()}",
            f"{self.nominalization()} приходит к {self.vague_noun()} {self.deletion()}",
            f"Когда {self.vague_noun()} {self.vague_verb()}, возникает {self.nominalization()}",
            f"Ты можешь {self.vague_verb()} {self.unspecific()} прямо сейчас",
            f"Представь, как {self.nominalization()} входит в {self.vague_noun()}"
        ]
        return random.choice(templates)


# ============================================================================
# МОДУЛЬ 7: ЯКОРЕНИЕ - триггеры для вызова состояний
# ============================================================================

class Anchoring:
    """Якоря - фразы и символы, вызывающие определенные состояния"""
    
    def __init__(self):
        self.phrase_anchors = {
            "calm": [
                "дыши глубже", "всё идёт своим чередом", "ты в безопасности",
                "можно расслабиться", "внутри становится тихо", "всё хорошо",
                "спокойствие приходит", "отпусти напряжение"
            ],
            "confidence": [
                "ты справишься", "у тебя получится", "ты уже делал это раньше",
                "в тебе есть сила", "я в тебя верю", "ты можешь больше, чем думаешь",
                "доверься себе", "ты сильный"
            ],
            "curiosity": [
                "интересно, что будет дальше", "давай посмотрим",
                "любопытно, что ты заметишь", "открой для себя",
                "что ты видишь?", "заметь новое"
            ],
            "action": [
                "сделай шаг", "начни прямо сейчас", "пришло время",
                "действуй", "двигайся вперед", "пора",
                "первый шаг уже сделан", "продолжай"
            ],
            "trust": [
                "ты можешь доверять", "я рядом", "ты не один",
                "доверься", "будь собой", "можно быть открытым",
                "всё будет хорошо"
            ],
            "insight": [
                "понимание приходит", "вдруг становится ясно",
                "озарение", "внутреннее знание", "интуиция подсказывает",
                "ответ уже есть внутри", "ты знаешь"
            ]
        }
        
        self.emoji_anchors = {
            "calm": "🌊", "confidence": "💪", "curiosity": "👀",
            "action": "⚡", "trust": "🤝", "insight": "💡",
            "love": "❤️", "success": "🏆", "peace": "🕊️"
        }
        
        self.user_anchors = defaultdict(dict)
    
    def get_anchor(self, state: str, user_id: Optional[int] = None) -> str:
        """Получить фразу-якорь для состояния"""
        if user_id and user_id in self.user_anchors:
            for anchor_name, (anchor_state, phrase) in self.user_anchors[user_id].items():
                if anchor_state == state:
                    return phrase
        
        anchors = self.phrase_anchors.get(state, self.phrase_anchors["calm"])
        return random.choice(anchors)
    
    def get_emoji(self, state: str) -> str:
        """Получить эмодзи-якорь для состояния"""
        return self.emoji_anchors.get(state, "✨")
    
    def set_anchor(self, user_id: int, anchor_name: str, state: str, phrase: str):
        """Установить персональный якорь"""
        self.user_anchors[user_id][anchor_name] = (state, phrase)
    
    def fire_anchor(self, user_id: int, anchor_name: str) -> Optional[str]:
        """Запустить якорь"""
        if user_id in self.user_anchors and anchor_name in self.user_anchors[user_id]:
            return self.user_anchors[user_id][anchor_name][1]
        return None
    
    def stack_anchors(self, states: List[str]) -> str:
        """Стек якорей - последовательность фраз"""
        phrases = []
        for state in states:
            phrase = self.get_anchor(state)
            emoji = self.get_emoji(state)
            phrases.append(f"{emoji} {phrase}")
        return "\n".join(phrases)
    
    def get_all_states(self) -> List[str]:
        """Возвращает все доступные состояния"""
        return list(self.phrase_anchors.keys())


# ============================================================================
# МОДУЛЬ 8: ТЕРАПЕВТИЧЕСКИЕ СКАЗКИ - метафоры для глубинной работы
# ============================================================================

class TherapeuticTales:
    """Терапевтические сказки и метафоры по методу Мейстера"""
    
    def __init__(self):
        self.tales = {
            "fear": {
                "title": "Тигренок",
                "keywords": ["страх", "боюсь", "трудно", "неуверен"],
                "text": """Давным-давно в далекой-далекой стране у самых Синих гор жил маленький полосатый тигренок. Он был весь полосатый: от носа до хвоста. Тигренок часто играл со своим полосатым хвостом, гонялся за бабочками, сбивал лапой цветы и листья. Это забавляло его. И все было бы хорошо, если бы тигренок не был таким трусливым. Он боялся уходить далеко от своей пещеры, боялся зверей, птиц, лесных духов. Тигренок мечтал, что когда он вырастет, он будет самым смелым тигром у Синих гор.

Однажды тигренок услышал историю о том, что в самом дальнем лесу, далеко от Синих гор есть волшебная поляна, на которой исполняется самое заветное желание того, кто дойдет туда. Тигренок очень хотел стать смелым, но он боялся уходить далеко. Уставший от раздумий он лег в своей пещере и уснул. И ему приснился сон, что он решил отправиться в путешествие в самый дальний лес на волшебную поляну.

Он долго шел по лесной тропинке все дальше и дальше от Синих гор, все глубже и глубже в лес. Иногда ему приходилось сворачивать с тропинки и идти по чаще вглубь леса. На пути он встречал разных животных. Он здоровался с ними, просил показать ему дорогу к самому дальнему лесу. И животные показывали ему дорогу. Тигренок шел дальше. Все глубже и глубже в лес. По пути он рассматривал новые места, играл со своим полосатым хвостом, гонялся за бабочками, срывал лапой цветы и листья. Когда на пути ему встречались разные птицы, он здоровался с ними и спрашивал дорогу в самый дальний лес. И птицы рассказывали ему, как идти туда. И он шел дальше, все глубже и глубже в лесную чащу.

Однажды он вышел на поляну и увидел там лесного духа. Он вежливо поздоровался и спросил, далеко ли еще самый дальний лес и волшебная поляна. Лесной дух улыбнулся и сказал: "Эта и есть та Волшебная поляна". Тигренок очень обрадовался, загадал свое самое заветное желание, и оно исполнилось.

Когда тигренок проснулся, он решил, что надо пойти в самый дальний лес, найти волшебную поляну и загадать свое самое заветное желание. И он отправился в путь.

Он долго шел по лесной тропинке все дальше и дальше от Синих гор, все глубже и глубже в лес по узкой лесной тропинке. Иногда ему приходилось сворачивать с тропинки и идти по чаще вглубь леса. На пути он встречал разных животных. Он здоровался с ними, просил показать ему дорогу к самому дальнему лесу. И животные показывали ему дорогу, иногда даже провожали его. Тигренок благодарил их и шел дальше. Все глубже и глубже в лес. По пути он рассматривал новые места, играл со своим полосатым хвостом, гонялся за бабочками, срывал лапой цветы и листья. Когда на пути ему встречались разные птицы, он здоровался с ними и спрашивал дорогу в самый дальний лес. И птицы рассказывали ему, как идти туда. И он шел дальше, все глубже и глубже в лесную чащу.

Однажды он вышел на поляну и увидел там лесного духа. Он вежливо поздоровался и спросил, далеко ли еще самый дальний лес и волшебная поляна. Лесной дух улыбнулся и сказал: "То, что ты ищешь, у тебя давно уже есть. Ты уже пришел". Тигренок очень обрадовался. Но в дороге он очень устал. Он лег на траву и уснул.

И когда тигренок проснулся, он понял, что его заветное желание исполнилось – он стал самым смелым тигром в округе.

Вот такая история случилась давным-давно, в далёкой-далёкой стране у самых Синих гор."""
            },
            
            "learning": {
                "title": "Поэт",
                "keywords": ["учиться", "научиться", "обучение", "понять"],
                "text": """Давным-давно в далекой-далекой стране у самых Синих гор в одном городе жил мальчик, который очень хотел стать Поэтом, сочинять стихи, песни, баллады; рассказывать людям истории, сказки и притчи. Мальчик очень хотел стать Поэтом, и решил, что когда в город придет странствующий Поэт, он обратиться к нему с такими словами: "Великий Поэт! Ты умеешь сочинять стихи, песни, баллады. Своими историями, сказками и притчами ты учишь людей смеяться, любить, радоваться жизни, быть счастливыми. Научи меня сочинять стихи и сказки."

Мальчик очень надеялся, что какой-нибудь Поэт останется на время в городе и научит его рифмовать строки.

Однажды в этот город пришел странствующий Поэт и, расположившись на центральной площади, стал читать людям свои стихи, петь песни, рассказывать истории и сказки. Люди смеялись и плакали, радовались и грустили, влюблялись и становились счастливыми вместе с героями стихов и сказок Поэта.

Когда мальчик узнал, что в город пришел Поэт, он бросился бежать к городской площади и, протиснувшись сквозь толпу, обратился к Поэту с такими словами: "Великий Поэт! Ты умеешь сочинять стихи, песни, баллады. Своими историями, сказками и притчами ты учишь людей смеяться, любить, радоваться жизни, быть счастливыми. Научи меня сочинять стихи и сказки, петь песни и рассказывать истории."

Поэт посмотрел на мальчика, улыбнулся и сказал: "Хорошо, я задержусь немного в твоем городе и расскажу тебе, как я сочиняю свои стихи и истории." Мальчик, едва дыша от счастья, сел рядом с Поэтом и стал внимательно слушать. Поэт долго рассказывал о том, как рифмовать слова, как сочинять сказки и истории. А когда пришло время уходить, Поэт попрощался с мальчиком и отправился в путь.

После ухода Поэта мальчик решил сочинить стихотворенье или историю, но он просто повторял истории Поэта, немного изменяя их.

Так продолжалось много лет. Мальчик вырос, стал юношей, потом взрослым человеком. Он встречал много поэтов, каждый раз просил научить его, внимательно слушал, но его собственные истории все еще были похожи на чужие.

Тогда он решил отправиться в путь и стать странником. Он шел по широким дорогам и узким горным тропам, переправлялся через реки и проходил мимо дремучих лесов. Он смеялся и плакал, радовался и тосковал, влюблялся и разочаровывался, страдал и был счастливым. Иногда он заходил в разные города и на городской площади рассказывал истории из своей жизни, иногда они были правдивые, иногда придуманные. Иногда пел песни, которые вдруг приходили к нему откуда-то из глубины души, рифмы складывались сами собой. И люди вокруг смеялись и плакали, радовались и грустили, влюблялись и становились счастливыми вместе с героями его стихов и рассказов.

Однажды, когда он зашел в какой-то город и стал рассказывать свои истории и сказки, к нему подбежал мальчик и, едва отдышавшись, сказал: "Великий Поэт! Ты умеешь сочинять стихи, песни, баллады. Своими историями, сказками и притчами ты учишь людей смеяться, любить, радоваться жизни, быть счастливыми. Научи меня сочинять так, как это делаешь ты."

Вот такая история случилась давным-давно в далекой-далекой стране у самых Синих гор."""
            },
            
            "truth": {
                "title": "В поисках Истины",
                "keywords": ["смысл", "истина", "понять", "зачем"],
                "text": """Давным-давно в далекой-далекой стране у самых Синих гор жил человек, который хотел узнать Истину. За свою жизнь он прочитал множество книг, разговаривал со всеми мудрецами близлежащих городов и селений, но так и не получил ответа на свой вопрос: в чем заключается Истина.

Однажды он решил отправиться в путь, чтобы найти ответ на свой вопрос. Он решил пройти по всем городам и селениям далекой-далекой страны и спросить всех Учителей, в чем заключается Истина.

Он долго шел по извилистой горной тропе, пока не пришел в селение, где, по слухам, жил Великий Учитель, познавший Истину. Он пришел к нему и спросил: "Великий Учитель! О тебе идет молва, как о самом мудром человеке в окрестностях. Говорят, ты познал Истину и теперь живешь легко и спокойно. Я прочитал множество книг, беседовал с множеством Учителей, но так и не понял, что же такое Истина. Ответь мне, в чем заключается этот секрет – секрет Истины."

Учитель улыбнулся и ответил: "Истина в том, что ее нет." Путник долго размышлял над словами Учителя, но не понял, о чем тот сказал и отправился в путь дальше.

Так он ходил от одного Учителя к другому, и каждый отвечал ему одно и то же: "Истина в том, что ее нет." Путник размышлял над словами Учителей, но не мог понять их и снова отправлялся в путь.

Однажды путник пришел в один город, где жил Великий Учитель и, как всегда, пришел к нему и сказал: "Великий Учитель! О тебе идет молва, как о самом мудром человеке в окрестностях. Говорят, ты познал Истину. Я прочитал множество книг, беседовал с множеством Учителей, но так и не понял, что же такое Истина. Ответь мне, в чем заключается этот секрет – секрет Истины."

Учитель улыбнулся в ответ и хотел ответить, как вдруг у путника возник ответ, он посмотрел на Учителя и сказал: "Истина в том, что ее нет."

"Вот теперь и ты стал Учителем," - ответил мудрец.

Вот такая история случилась давным-давно в далекой-далекой стране у самых Синих гор."""
            },
            
            "growth": {
                "title": "Сказка о дровосеке",
                "keywords": ["развитие", "расти", "вперед", "двигаться"],
                "text": """Давным-давно в далекой-далекой стране у самых Синих гор жил дровосек, который рубил дрова в соседнем лесу, отвозил их в ближайший город, продавал. И на вырученные деньги жил, пусть и бедно, но счастливо.

Однажды, когда дровосек как всегда рубил дрова в ближайшем лесу недалеко от дороги, мимо шел путник. Он увидел дровосека и попросил у него что-нибудь поесть. Дровосек с радостью поделился с путником своим обедом. Когда путник закончил обед, он поблагодарил дровосека и сказал: «Иди вперед!»

Дровосек удивился словам путника, но все же решил попробовать пойти дальше в лес. Он шел некоторое время, пока не увидел сандаловое дерево. А, надо сказать, в далекой-далекой стране сандаловое дерево очень высоко ценилось. Дровосек срубил дерево, взял с собой столько, сколько смог унести и отправился в город, чтоб продать его. Дровосек быстро продал сандаловое дерево, заработал денег намного больше, чем когда продавал дрова. И теперь ему стало легче содержать свою семью.

Следующий раз, когда дровосек решил пойти в лес, он прошел мимо вязанки дров, оставленной им возле дороги и пошел в глубь леса. Он дошел до срубленного сандалового дерева и, хотя там оставались еще ветки, которые можно было продать, вспомнил слова путника: «Иди вперед!» и решил пойти дальше. Он прошел еще какое-то время и нашел медную руду. Дровосек собрал столько руды, сколько смог, отнес в город, продал и выручил еще больше денег.

Так продолжалось много лет. Каждый раз, находя что-то ценное, он вспоминал слова путника и шел дальше. Он находил серебро, потом золото, потом алмазы. Он стал самым богатым и уважаемым человеком в городе.

Однажды он снова пришел в лес, сел у той самой вязанки дров, с которой когда-то начался его путь, и увидел того самого путника. Он пригласил его в свой дом, хотел поделиться богатством, но путник, поблагодарив, отказался и снова сказал: «Иди вперед!»

Вот такая история случилась давным-давно, в далёкой-далёкой стране у самых Синих гор."""
            }
        }
        
        self.standard_openings = [
            "Давным-давно в далекой-далекой стране у самых Синих гор",
            "В некотором царстве, в некотором государстве",
            "Давно это было, в стародавние времена",
            "Сказывают, в давние времена",
            "Жили-были"
        ]
        
        self.standard_closings = [
            "Вот такая история случилась давным-давно, в далёкой-далёкой стране у самых Синих гор",
            "Сказке конец, а кто слушал - молодец",
            "И стали они жить-поживать да добра наживать",
            "С тех пор прошло много лет, но сказка осталась с нами"
        ]
    
    def get_tale_for_issue(self, text: str) -> Dict:
        """Возвращает подходящую сказку по тексту проблемы"""
        text_lower = text.lower()
        
        for tale_id, tale in self.tales.items():
            for keyword in tale.get('keywords', []):
                if keyword in text_lower:
                    return {"title": tale["title"], "text": tale["text"]}
        
        default = self.tales["growth"]
        return {"title": default["title"], "text": default["text"]}
    
    def get_tale_by_id(self, tale_id: str) -> Optional[Dict]:
        """Возвращает сказку по ID"""
        return self.tales.get(tale_id)
    
    def get_all_tales(self) -> List[str]:
        """Возвращает список всех доступных сказок"""
        return list(self.tales.keys())
    
    def generate_tale(self, topic: str, suggestions: List[str] = None) -> str:
        """Генерирует простую сказку по теме"""
        suggestions = suggestions or ["довериться процессу"]
        
        tale = random.choice(self.standard_openings) + " "
        tale += f"жил-был человек, который {topic}. "
        tale += f"Он отправился в путь, чтобы найти ответ. "
        tale += f"Он шел долго, встречал разных людей, учился у них. "
        tale += f"И однажды он понял, что {suggestions[0]}. "
        tale += random.choice(self.standard_closings)
        
        return tale


# ============================================================================
# МОДУЛЬ 9: ГИПНОТИЧЕСКИЙ ОРКЕСТРАТОР - объединение всех техник
# ============================================================================

class HypnoOrchestrator:
    """Главный оркестратор, объединяющий все гипнотические модули"""
    
    def __init__(self):
        self.ps = PreSuppositions()
        self.truisms = Truisms()
        self.pl = PseudoLogic()
        self.pc = ParadoxCommands()
        self.hq = HypnoQuestions()
        self.mm = MiltonModel()
        self.anchoring = Anchoring()
        self.tales = TherapeuticTales()
        
        # Карта соответствия проблем и техник
        self.technique_map = {
            "сопротивление": ["not_command", "prohibition"],
            "недоверие": ["introductory", "fact", "proverb"],
            "страх": ["tale_fear", "calm_anchor", "possibility"],
            "неуверенность": ["tale_growth", "confidence_anchor", "rhetorical"],
            "тревога": ["calm_anchor", "about_self"],
            "поиск смысла": ["tale_truth", "insight_anchor", "rhetorical"],
            "обучение": ["tale_learning", "curiosity_anchor", "alternative"],
            "апатия": ["action_anchor", "unequal_choice", "temporal"],
            "обида": ["about_self", "return_question"]
        }
        
        # Состояния для якорей
        self.state_emojis = {
            "calm": "🌊", "confidence": "💪", "curiosity": "👀",
            "action": "⚡", "trust": "🤝", "insight": "💡"
        }
        
        # Конфигурация для разных режимов
        self.mode_config = {
            "coach": {
                "intro": "🔮",
                "style": "вопросы, размышления",
                "tech_filters": ["return_question", "alternative", "rhetorical"]
            },
            "psychologist": {
                "intro": "🧠",
                "style": "исследование, глубина",
                "tech_filters": ["tale_fear", "tale_truth", "insight_anchor"]
            },
            "trainer": {
                "intro": "⚡",
                "style": "инструкции, действия",
                "tech_filters": ["action_anchor", "unequal_choice", "temporal"]
            }
        }
    
    def process(self, user_id: int, text: str, context: Dict = None) -> str:
        """
        Главный метод обработки текста пользователя
        
        Args:
            user_id: ID пользователя
            text: текст сообщения
            context: контекст (профиль, конфайнтмент-модель, режим)
            
        Returns:
            ответ с гипнотическими техниками
        """
        # Определяем проблему
        issue = self._detect_issue(text)
        
        # Определяем состояние
        state = self._detect_state(context)
        
        # Определяем режим
        mode = context.get('mode', 'psychologist') if context else 'psychologist'
        
        # Выбираем техники
        techniques = self._select_techniques(issue, state, mode)
        
        # Генерируем ответ
        response = self._generate_response(techniques, text, mode)
        
        # Добавляем якорь
        response = self._add_anchor(response, state, user_id, mode)
        
        return response
    
    def _detect_issue(self, text: str) -> str:
        """Определяет ключевую проблему из текста"""
        keywords = {
            "страх": ["боюсь", "страшно", "боязнь", "пугает", "тревожно"],
            "тревога": ["тревожно", "беспокоюсь", "волнуюсь", "нервничаю"],
            "неуверенность": ["не уверен", "сомневаюсь", "не знаю", "не могу"],
            "обида": ["обидно", "обидели", "несправедливо", "должен"],
            "апатия": ["все равно", "нет сил", "устал", "не хочется"],
            "сопротивление": ["не хочу", "не буду", "не могу", "не получается"],
            "недоверие": ["не верю", "сомневаюсь", "вряд ли", "наверное"],
            "поиск смысла": ["зачем", "почему", "смысл", "зачем это"],
            "обучение": ["научиться", "понять", "разобраться", "узнать"]
        }
        
        text_lower = text.lower()
        for issue, words in keywords.items():
            for word in words:
                if word in text_lower:
                    return issue
        return "общее"
    
    def _detect_state(self, context: Dict = None) -> str:
        """Определяет состояние из контекста"""
        if not context:
            return "calm"
        
        # Используем конфайнтмент-модель если есть
        if context.get('confinement_model'):
            model = context['confinement_model']
            if model.get('key_confinement'):
                elem_id = model['key_confinement'].get('element_id')
                state_map = {
                    1: "fear", 2: "anxiety", 3: "apathy",
                    4: "resistance", 5: "search", 6: "learning",
                    7: "distrust", 8: "resentment", 9: "fear"
                }
                anchor_map = {
                    "fear": "calm", "anxiety": "calm", "apathy": "action",
                    "resistance": "curiosity", "search": "insight",
                    "learning": "curiosity", "distrust": "trust",
                    "resentment": "trust", "calm": "calm"
                }
                state = state_map.get(elem_id, "calm")
                return anchor_map.get(state, "calm")
        
        # Проверяем вектор
        vector = context.get('vector', '')
        if vector == 'СБ':
            return "calm"
        elif vector == 'ТФ':
            return "confidence"
        elif vector == 'УБ':
            return "curiosity"
        elif vector == 'ЧВ':
            return "trust"
        
        return "calm"
    
    def _select_techniques(self, issue: str, state: str, mode: str) -> List[str]:
        """Выбирает техники для проблемы и состояния"""
        # Базовые техники по проблеме
        techniques = self.technique_map.get(issue, [])
        
        # Добавляем техники по состоянию
        state_tech = {
            "calm": ["calm_anchor"],
            "action": ["action_anchor"],
            "curiosity": ["curiosity_anchor", "alternative"],
            "trust": ["trust_anchor", "introductory"],
            "insight": ["insight_anchor", "rhetorical"],
            "confidence": ["confidence_anchor", "fact"]
        }
        
        techniques.extend(state_tech.get(state, []))
        
        # Фильтруем по режиму
        mode_filters = self.mode_config.get(mode, {}).get("tech_filters", [])
        if mode_filters:
            # Оставляем только техники, подходящие для режима
            filtered = []
            for tech in techniques:
                # Сказки всегда оставляем
                if tech.startswith("tale_"):
                    filtered.append(tech)
                elif any(filter_tech in tech for filter_tech in mode_filters):
                    filtered.append(tech)
            techniques = filtered if filtered else techniques[:2]
        
        # Убираем дубликаты
        return list(set(techniques))[:3]
    
    def _generate_response(self, techniques: List[str], text: str, mode: str) -> str:
        """Генерирует ответ с использованием техник"""
        parts = []
        
        # Добавляем вступление в зависимости от режима
        mode_intro = self.mode_config.get(mode, {}).get("intro", "🧠")
        parts.append(f"{mode_intro} ")
        
        # Добавляем трюизм для согласия
        parts.append(self.truisms.fact())
        
        for technique in techniques:
            if technique == "tale_fear":
                tale = self.tales.get_tale_for_issue("страх")
                parts.append(tale['text'][:400])
                
            elif technique == "tale_growth":
                tale = self.tales.get_tale_for_issue("развитие")
                parts.append(tale['text'][:400])
                
            elif technique == "tale_truth":
                tale = self.tales.get_tale_for_issue("смысл")
                parts.append(tale['text'][:400])
                
            elif technique == "tale_learning":
                tale = self.tales.get_tale_for_issue("обучение")
                parts.append(tale['text'][:400])
                
            elif technique == "not_command":
                parts.append(self.pc.not_command("переживать об этом"))
                
            elif technique == "prohibition":
                parts.append(self.pc.prohibition("зацикливаться на этом"))
                
            elif technique == "introductory":
                parts.append(self.ps.introductory("ты можешь справиться"))
                
            elif technique == "fact":
                parts.append(self.truisms.fact())
                
            elif technique == "proverb":
                parts.append(self.truisms.proverb())
                
            elif technique == "rhetorical":
                parts.append(self.hq.rhetorical("ты хочешь найти решение"))
                
            elif technique == "alternative":
                parts.append(self.hq.alternative("довериться процессу", "контролировать всё"))
                
            elif technique == "unequal_choice":
                parts.append(self.hq.unequal_choice("сделать шаг сейчас", "откладывать дальше"))
                
            elif technique == "about_self":
                parts.append(self.truisms.about_self("я слышу, как тебе важно это"))
                
            elif technique == "possibility":
                parts.append(self.truisms.possibility("всё может измениться"))
                
            elif technique == "return_question":
                parts.append(self.hq.return_question("ты уже на пути к решению"))
                
            elif technique == "cause_effect":
                parts.append(self.pl.cause_effect("понимание приходит", "становится легче"))
                
            elif technique == "temporal":
                parts.append(self.pl.temporal("ты думаешь об этом", "ответ появляется"))
                
            elif technique == "calm_anchor":
                parts.append(self.anchoring.get_anchor("calm"))
                
            elif technique == "confidence_anchor":
                parts.append(self.anchoring.get_anchor("confidence"))
                
            elif technique == "curiosity_anchor":
                parts.append(self.anchoring.get_anchor("curiosity"))
                
            elif technique == "action_anchor":
                parts.append(self.anchoring.get_anchor("action"))
                
            elif technique == "trust_anchor":
                parts.append(self.anchoring.get_anchor("trust"))
                
            elif technique == "insight_anchor":
                parts.append(self.anchoring.get_anchor("insight"))
        
        # Добавляем вопрос для вовлечения
        parts.append(self.hq.simple("расскажешь подробнее"))
        
        return " ".join(parts)
    
    def _add_anchor(self, response: str, state: str, user_id: int, mode: str) -> str:
        """Добавляет якорь в ответ"""
        emoji = self.anchoring.get_emoji(state)
        anchor = self.anchoring.get_anchor(state, user_id)
        
        mode_emoji = self.mode_config.get(mode, {}).get("intro", "🧠")
        
        return f"{mode_emoji} {response}\n\n{emoji} {anchor}"
    
    def get_support_response(self, text: str) -> str:
        """Быстрый поддерживающий ответ"""
        parts = []
        parts.append(self.truisms.about_self("я слышу тебя"))
        parts.append(self.truisms.possibility("всё может наладиться"))
        parts.append(self.anchoring.get_anchor("trust"))
        return " ".join(parts)


# ============================================================================
# ФУНКЦИЯ ДЛЯ БЫСТРОГО ТЕСТИРОВАНИЯ
# ============================================================================

def test_hypno_module():
    """Тестирование всех модулей"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ГИПНОТИЧЕСКОГО МОДУЛЯ")
    print("=" * 60)
    
    # Создаем оркестратор
    hypno = HypnoOrchestrator()
    
    # Тестовые сообщения
    test_messages = [
        ("Я боюсь выступать на публике", "psychologist"),
        ("Я не уверен в своем решении", "coach"),
        ("Мне тревожно и непонятно", "psychologist"),
        ("Я хочу научиться новому", "trainer"),
        ("У меня нет сил ничего делать", "coach")
    ]
    
    for msg, mode in test_messages:
        print(f"\n📝 Сообщение: {msg}")
        print(f"🎭 Режим: {mode}")
        context = {'mode': mode, 'vector': 'СБ'}
        print(f"💬 Ответ: {hypno.process(123, msg, context)}")
        print("-" * 40)
    
    # Тестирование отдельных модулей
    print("\n🔧 ТЕСТИРОВАНИЕ МОДУЛЕЙ:")
    
    ps = PreSuppositions()
    print(f"Пресуппозиция: {ps.introductory('всё будет хорошо')}")
    
    tru = Truisms()
    print(f"Трюизм: {tru.about_self('это важно')}")
    
    pl = PseudoLogic()
    print(f"Псевдологика: {pl.therefore('ты здесь', 'значит, готов')}")
    
    pc = ParadoxCommands()
    print(f"Парадокс: {pc.not_command('думать об этом')}")
    
    hq = HypnoQuestions()
    print(f"Вопрос: {hq.alternative('сделать сейчас', 'подождать')}")
    
    anc = Anchoring()
    print(f"Якорь: {anc.get_anchor('confidence')} {anc.get_emoji('confidence')}")
    
    tale = TherapeuticTales()
    t = tale.get_tale_for_issue("страх")
    print(f"Сказка: {t['title']} ({len(t['text'])} символов)")
    
    mm = MiltonModel()
    print(f"Милтон-модель: {mm.milton_phrase()}")
    
    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    test_hypno_module()
