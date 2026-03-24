#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 7: АНАЛИЗ ВОПРОСОВ В КОНТЕКСТЕ КОНФАЙНМЕНТ-МОДЕЛИ
Анализирует вопросы пользователя с учетом его психологического профиля
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Импорты из наших модулей
from confinement_model import ConfinementModel9
from loop_analyzer import LoopAnalyzer

logger = logging.getLogger(__name__)


class ConfinementReporter:
    """
    Упрощенная версия репортера для анализатора
    """
    def __init__(self, model: ConfinementModel9, user_name: str = "друг"):
        self.model = model
        self.user_name = user_name
        self.key = self._find_key_confinement()
    
    def _find_key_confinement(self) -> Optional[Dict]:
        """Находит ключевое ограничение в модели"""
        if not self.model or not hasattr(self.model, 'elements'):
            return None
        
        # Ищем элемент с наибольшим количеством связей
        elements = getattr(self.model, 'elements', {})
        if not elements:
            return None
        
        max_connections = -1
        key_element = None
        
        for elem_id, element in elements.items():
            connections = 0
            if hasattr(element, 'causes') and element.causes:
                connections += len(element.causes)
            if hasattr(element, 'caused_by') and element.caused_by:
                connections += len(element.caused_by)
            
            if connections > max_connections:
                max_connections = connections
                key_element = element
        
        if key_element:
            return {
                'element': key_element,
                'description': getattr(key_element, 'description', 'Ключевое ограничение'),
                'id': getattr(key_element, 'id', 0),
                'strength': max_connections / 10 if max_connections > 0 else 0.5
            }
        
        return None
    
    def get_key_confinement(self) -> Optional[Dict]:
        """Возвращает ключевое ограничение"""
        return self.key


class QuestionContextAnalyzer:
    """
    Анализирует вопросы пользователя в контексте его конфайнмент-модели
    Не дает советов и инструкций - только глубинный анализ
    """
    
    # Ключевые слова для разных векторов
    VECTOR_KEYWORDS = {
        'СБ': [
            'страх', 'боюсь', 'тревог', 'опасн', 'безопасн', 'защит', 'давлен',
            'конфликт', 'ссор', 'руга', 'крик', 'агресс', 'напал', 'угроз',
            'спин', 'границ', 'терп', 'молч', 'стерп'
        ],
        'ТФ': [
            'деньг', 'финанс', 'заработ', 'доход', 'плат', 'стоим', 'цен',
            'коп', 'трат', 'покупк', 'долг', 'кредит', 'ипотек', 'зарплат',
            'бюджет', 'богат', 'бедн', 'нищет'
        ],
        'УБ': [
            'смысл', 'понима', 'дума', 'счита', 'вер', 'убежд', 'мнение',
            'анализ', 'систем', 'закономер', 'причин', 'следств', 'логик',
            'понят', 'осозна', 'рефлекс'
        ],
        'ЧВ': [
            'отношен', 'люд', 'общен', 'близк', 'чувств', 'одиноч', 'друз',
            'любов', 'семь', 'партнер', 'муж', 'жен', 'родствен', 'коллег',
            'привязан', 'довер', 'предатель'
        ]
    }
    
    # Маркеры глубины вопроса
    DEPTH_MARKERS = {
        'поверхностный': [
            'как', 'что делать', 'посоветуй', 'подскажи', 'научи',
            'метод', 'техник', 'упражнен', 'инструмент'
        ],
        'глубинный': [
            'почему', 'зачем', 'отчего', 'в чем причина', 'из-за чего',
            'откуда', 'как так', 'почему у меня', 'что со мной'
        ],
        'экзистенциальный': [
            'кто я', 'зачем я', 'в чем смысл', 'мое место', 'предназначен',
            'для чего я', 'что со мной не так', 'почему я такой'
        ]
    }
    
    # Маркеры эмоционального состояния
    EMOTION_MARKERS = {
        'тревога': [
            'боюсь', 'страшно', 'тревожно', 'беспокоюсь', 'волнуюсь',
            'паник', 'кошмар', 'ужас', 'не могу спать', 'ком в горле'
        ],
        'печаль': [
            'грустно', 'тоска', 'печаль', 'депресс', 'плохо', 'тяжело',
            'нет сил', 'опускаются руки', 'безнадеж', 'безысход'
        ],
        'злость': [
            'злюсь', 'бесит', 'раздражает', 'ненавиж', 'ярость', 'гнев',
            'обида', 'бешенство', 'взбешен'
        ],
        'стыд': [
            'стыдно', 'совестно', 'неловко', 'позор', 'унизительно',
            'какой же я', 'что обо мне подумают'
        ]
    }
    
    def __init__(self, model: ConfinementModel9, user_name: str = "друг"):
        """
        Инициализация анализатора
        
        Args:
            model: конфайнмент-модель пользователя
            user_name: имя пользователя
        """
        self.model = model
        self.user_name = user_name
        self.reporter = ConfinementReporter(model, user_name)
        self.loop_analyzer = LoopAnalyzer(model)
        self.loops = self.loop_analyzer.analyze()
        
        # Кэш для результатов анализа
        self._analysis_cache = {}
        self._cache_time = {}
        self.cache_ttl = 300  # 5 минут
        
        logger.info(f"QuestionContextAnalyzer инициализирован для {user_name}")
    
    def analyze(self, question: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Главный метод анализа вопроса
        
        Args:
            question: текст вопроса
            force_refresh: принудительно обновить кэш
            
        Returns:
            dict: полный контекстный анализ вопроса
        """
        # Проверяем кэш
        cache_key = hash(question) % 10000
        if not force_refresh and cache_key in self._analysis_cache:
            cache_age = (datetime.now() - self._cache_time.get(cache_key, datetime.now())).seconds
            if cache_age < self.cache_ttl:
                return self._analysis_cache[cache_key]
        
        # Проводим анализ
        analysis = {
            'question': question,
            'user_name': self.user_name,
            'timestamp': datetime.now().isoformat(),
            'vectors': self._analyze_vectors(question),
            'depth': self._analyze_depth(question),
            'emotion': self._analyze_emotion(question),
            'loops': self._find_activated_loops(question),
            'key_confinement': self._check_key_confinement(question),
            'paradox': self._find_paradox(question),
            'subtext': self._formulate_subtext(question),
            'reflection': self._generate_reflection(question)
        }
        
        # Кэшируем результат
        self._analysis_cache[cache_key] = analysis
        self._cache_time[cache_key] = datetime.now()
        
        return analysis
    
    def _analyze_vectors(self, question: str) -> List[Dict[str, Any]]:
        """
        Определяет, какие векторы затронуты в вопросе
        
        Args:
            question: текст вопроса
            
        Returns:
            list: список затронутых векторов с релевантностью
        """
        question_lower = question.lower()
        vectors = []
        
        for vector, keywords in self.VECTOR_KEYWORDS.items():
            matches = []
            for keyword in keywords:
                if keyword in question_lower:
                    matches.append(keyword)
            
            if matches:
                # Получаем уровень из модели
                level = self._get_vector_level(vector)
                
                # Рассчитываем релевантность
                relevance = min(len(matches) * 0.2, 0.9)
                
                vectors.append({
                    'vector': vector,
                    'level': level,
                    'relevance': relevance,
                    'matches': matches[:3],  # топ-3 совпадения
                    'description': self._get_vector_description(vector, level)
                })
        
        return sorted(vectors, key=lambda x: x['relevance'], reverse=True)
    
    def _get_vector_level(self, vector: str) -> int:
        """Получает уровень вектора из модели"""
        # Пытаемся получить из модели
        if hasattr(self.model, 'elements') and self.model.elements:
            for elem_id, element in self.model.elements.items():
                if hasattr(element, 'vector') and element.vector == vector:
                    if hasattr(element, 'strength'):
                        strength = getattr(element, 'strength', 0)
                        if strength <= 1:
                            return 1
                        elif strength <= 2:
                            return 2
                        elif strength <= 3:
                            return 3
                        elif strength <= 4:
                            return 4
                        elif strength <= 5:
                            return 5
                        else:
                            return 6
        
        # Значения по умолчанию
        levels = {'СБ': 3, 'ТФ': 3, 'УБ': 3, 'ЧВ': 3}
        return levels.get(vector, 3)
    
    def _get_vector_description(self, vector: str, level: int) -> str:
        """Возвращает описание вектора на его уровне"""
        descriptions = {
            'СБ': {
                1: "полное замирание перед угрозой",
                2: "избегание конфликтов любой ценой",
                3: "внешнее согласие при внутреннем протесте",
                4: "внешнее спокойствие при внутреннем напряжении",
                5: "попытки сгладить конфликт",
                6: "способность защищать себя"
            },
            'ТФ': {
                1: "деньги приходят и уходят случайно",
                2: "постоянный поиск возможностей с нуля",
                3: "способность зарабатывать трудом",
                4: "умение зарабатывать и копить",
                5: "создание систем дохода",
                6: "управление капиталом"
            },
            'УБ': {
                1: "избегание сложных мыслей",
                2: "вера в знаки и судьбу",
                3: "доверие авторитетам",
                4: "поиск скрытых смыслов",
                5: "анализ фактов",
                6: "построение теорий"
            },
            'ЧВ': {
                1: "сильная привязанность",
                2: "потеря себя в отношениях",
                3: "стремление нравиться",
                4: "умение влиять",
                5: "равные партнерские отношения",
                6: "создание сообществ"
            }
        }
        return descriptions.get(vector, {}).get(level, "особое отношение")
    
    def _analyze_depth(self, question: str) -> Dict[str, Any]:
        """
        Анализирует глубину вопроса
        
        Args:
            question: текст вопроса
            
        Returns:
            dict: информация о глубине вопроса
        """
        question_lower = question.lower()
        
        # Определяем тип глубины
        depth_type = 'поверхностный'
        for d_type, markers in self.DEPTH_MARKERS.items():
            for marker in markers:
                if marker in question_lower:
                    depth_type = d_type
                    break
        
        # Определяем, вопрос про себя или про других
        about_self = any(word in question_lower for word in ['я', 'меня', 'мне', 'мой', 'моя', 'мое'])
        about_others = any(word in question_lower for word in ['они', 'люди', 'другие', 'все', 'никто'])
        
        return {
            'type': depth_type,
            'about_self': about_self,
            'about_others': about_others,
            'is_why_question': 'почему' in question_lower or 'зачем' in question_lower,
            'is_how_question': 'как' in question_lower and 'почему' not in question_lower
        }
    
    def _analyze_emotion(self, question: str) -> Dict[str, Any]:
        """
        Анализирует эмоциональный фон вопроса
        
        Args:
            question: текст вопроса
            
        Returns:
            dict: информация об эмоциях в вопросе
        """
        question_lower = question.lower()
        
        emotions = {}
        primary_emotion = None
        max_intensity = 0
        
        for emotion, markers in self.EMOTION_MARKERS.items():
            matches = []
            for marker in markers:
                if marker in question_lower:
                    matches.append(marker)
            
            if matches:
                intensity = min(len(matches) * 0.25, 1.0)
                emotions[emotion] = {
                    'intensity': intensity,
                    'matches': matches[:3]
                }
                
                if intensity > max_intensity:
                    max_intensity = intensity
                    primary_emotion = emotion
        
        return {
            'present': bool(emotions),
            'primary': primary_emotion,
            'intensity': max_intensity,
            'all': emotions
        }
    
    def _find_activated_loops(self, question: str) -> List[Dict[str, Any]]:
        """
        Находит петли, которые активируются вопросом
        
        Args:
            question: текст вопроса
            
        Returns:
            list: активированные петли
        """
        if not self.loops:
            return []
        
        question_lower = question.lower()
        activated = []
        
        for loop in self.loops:
            # Проверяем, есть ли совпадения с элементами петли
            loop_elements = loop.get('elements', [])
            matches = []
            
            for elem in loop_elements:
                if hasattr(elem, 'description') and elem.description:
                    desc_words = elem.description.lower().split()
                    for word in desc_words:
                        if len(word) > 3 and word in question_lower:
                            matches.append(word)
            
            if matches:
                activation_strength = min(len(matches) * 0.2, 0.9)
                activated.append({
                    'loop': loop,
                    'description': loop.get('description', 'Неизвестная петля'),
                    'type': loop.get('type', 'minor_loop'),
                    'type_name': loop.get('type_name', 'Второстепенная петля'),
                    'activation_strength': activation_strength,
                    'matches': matches[:5]
                })
        
        return sorted(activated, key=lambda x: x['activation_strength'], reverse=True)
    
    def _check_key_confinement(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет, связан ли вопрос с ключевым ограничением
        
        Args:
            question: текст вопроса
            
        Returns:
            dict: информация о связи с ключевым ограничением или None
        """
        if not hasattr(self.reporter, 'key') or not self.reporter.key:
            return None
        
        key = self.reporter.key
        question_lower = question.lower()
        
        # Проверяем совпадения с описанием ключевого ограничения
        key_desc = key.get('description', '').lower()
        key_words = set(key_desc.split())
        
        matches = []
        for word in key_words:
            if len(word) > 3 and word in question_lower:
                matches.append(word)
        
        if matches:
            return {
                'is_related': True,
                'strength': min(len(matches) * 0.2, 0.9),
                'description': key.get('description', ''),
                'element': key.get('element'),
                'matches': matches[:5]
            }
        
        return {'is_related': False}
    
    def _find_paradox(self, question: str) -> Optional[str]:
        """
        Ищет парадокс в вопросе - противоречие, которое не замечает пользователь
        
        Args:
            question: текст вопроса
            
        Returns:
            str: описание парадокса или None
        """
        question_lower = question.lower()
        
        # Проверяем типичные парадоксы для разных профилей
        sb_level = self._get_vector_level('СБ')
        tf_level = self._get_vector_level('ТФ')
        ub_level = self._get_vector_level('УБ')
        
        if sb_level <= 2 and 'люди' in question_lower and 'используют' in question_lower:
            return "Вы боитесь конфликтов, но при этом постоянно живёте в состоянии внутреннего конфликта с собой"
        
        if sb_level <= 2 and 'сказать нет' in question_lower:
            return "Вы хотите научиться говорить 'нет', но ваше 'да' уже стало способом избегать конфликтов"
        
        if tf_level <= 3 and 'копить' in question_lower:
            return "Вы хотите копить, но для этого нужно уметь отказывать себе — то же самое, что отказывать другим, а вы не умеете ни того, ни другого"
        
        if ub_level >= 5 and 'призвание' in question_lower:
            return "Вы достаточно умны, чтобы видеть риски в любой деятельности, и достаточно тревожны, чтобы эти риски казались катастрофой"
        
        return None
    
    def _formulate_subtext(self, question: str) -> str:
        """
        Формулирует подтекст вопроса - что на самом деле спрашивает пользователь
        
        Args:
            question: текст вопроса
            
        Returns:
            str: формулировка подтекста
        """
        vectors = self._analyze_vectors(question)
        depth = self._analyze_depth(question)
        key = self._check_key_confinement(question)
        sb_level = self._get_vector_level('СБ')
        
        # Если вопрос глубокий и связан с ключевым ограничением
        if key and key.get('is_related') and depth['type'] != 'поверхностный':
            return f"Вы не просто спрашиваете, вы вышли на своё ключевое ограничение. За вопросом стоит {key['description'].lower()}"
        
        # Если вопрос про отношения
        if any(v['vector'] == 'ЧВ' for v in vectors):
            if sb_level <= 2:
                return "Вы спрашиваете про других, но на самом деле про себя — почему вы позволяете с собой так обращаться"
        
        # Если вопрос про деньги
        if any(v['vector'] == 'ТФ' for v in vectors):
            if sb_level <= 2:
                return "Вы спрашиваете про деньги, но на самом деле про границы — деньги утекают так же, как утекают ваши силы в отношениях"
        
        # Если вопрос про смысл
        if any(v['vector'] == 'УБ' for v in vectors):
            return "Вы ищете не ответ, а опору — точку, с которой можно начать что-то менять"
        
        # Универсальный подтекст
        if depth['about_self']:
            return "Вы спрашиваете о том, что болит. Не столько за ответом, сколько за тем, чтобы это увидели"
        else:
            return "Вы описываете ситуацию, в которой застряли. Не столько вопрос, сколько попытка выговориться"
    
    def _generate_reflection(self, question: str) -> str:
        """
        Генерирует основную рефлексию - то, что можно сказать пользователю
        
        Args:
            question: текст вопроса
            
        Returns:
            str: текст рефлексии (без советов и инструкций)
        """
        vectors = self._analyze_vectors(question)
        depth = self._analyze_depth(question)
        emotion = self._analyze_emotion(question)
        loops = self._find_activated_loops(question)
        paradox = self._find_paradox(question)
        key = self._check_key_confinement(question)
        
        # Начинаем с имени, если знаем
        reflection = []
        
        # Учитываем эмоциональный фон
        if emotion['present'] and emotion['intensity'] > 0.5:
            if emotion['primary'] == 'тревога':
                reflection.append(f"В этом вопросе чувствуется тревога. Не та, которую можно успокоить советом, а та, которая живёт в теле и заставляет замирать.")
            elif emotion['primary'] == 'печаль':
                reflection.append(f"Слышу усталость в этом вопросе. Не физическую, а ту, когда сил уже нет даже на то, чтобы злиться.")
            elif emotion['primary'] == 'злость':
                reflection.append(f"В вопросе есть злость. Спрятанная, приглушённая, но она здесь.")
            elif emotion['primary'] == 'стыд':
                reflection.append(f"Здесь есть стыд. Он часто маскируется под вопросы 'почему я такой'.")
        
        # Добавляем анализ векторов
        if vectors:
            main_vector = vectors[0]
            vector_name = {
                'СБ': 'страх конфликтов',
                'ТФ': 'деньги',
                'УБ': 'мышление',
                'ЧВ': 'отношения'
            }.get(main_vector['vector'], 'эта сфера')
            
            level_desc = main_vector['description']
            
            reflection.append(f"Судя по профилю, в {vector_name} у вас {level_desc}.")
        
        # Добавляем парадокс, если есть
        if paradox:
            reflection.append(paradox)
        
        # Добавляем информацию о петлях
        if loops:
            main_loop = loops[0]
            reflection.append(f"И это не просто ситуация, а петля: {main_loop['description']}")
        
        # Добавляем связь с ключевым ограничением
        if key and key.get('is_related'):
            reflection.append("И этот вопрос бьёт прямо в ключевое ограничение.")
        
        # Формулируем суть
        if depth['type'] == 'экзистенциальный':
            reflection.append("Вы спрашиваете не о том, что делать, а о том, кто вы.")
        elif depth['type'] == 'глубинный':
            reflection.append("Вы ищете не решение, а понимание.")
        else:
            if key and key.get('is_related'):
                reflection.append("За внешним вопросом стоит что-то большее.")
        
        # Если ничего не нашли, даем универсальную рефлексию
        if not reflection:
            reflection.append("Вы описали ситуацию, в которой застряли. Не столько спрашивая, сколько надеясь, что кто-то увидит, как вам тяжело.")
        
        return " ".join(reflection)
    
    def get_response_context(self, question: str) -> Dict[str, Any]:
        """
        Возвращает контекст для формирования ответа (для основного бота)
        
        Args:
            question: текст вопроса
            
        Returns:
            dict: контекст для ответа
        """
        analysis = self.analyze(question)
        
        return {
            'user_name': self.user_name,
            'vectors': analysis['vectors'],
            'depth': analysis['depth'],
            'emotion': analysis['emotion'],
            'loops': analysis['loops'],
            'key_confinement': analysis['key_confinement'],
            'paradox': analysis['paradox'],
            'subtext': analysis['subtext'],
            'reflection': analysis['reflection']
        }
    
    def get_reflection_text(self, question: str) -> str:
        """
        Возвращает только текст рефлексии (для использования в ответах)
        
        Args:
            question: текст вопроса
            
        Returns:
            str: текст рефлексии
        """
        analysis = self.analyze(question)
        return analysis['reflection']
    
    def clear_cache(self):
        """Очищает кэш анализов"""
        self._analysis_cache.clear()
        self._cache_time.clear()
        logger.info("Кэш анализов очищен")


# ============================================
# ДОБАВЛЯЕМ АЛИАС ДЛЯ СОВМЕСТИМОСТИ
# ============================================
QuestionAnalyzer = QuestionContextAnalyzer


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СОЗДАНИЯ АНАЛИЗАТОРА
# ============================================

def create_analyzer_from_user_data(user_data: Dict, user_name: str = "друг") -> Optional[QuestionContextAnalyzer]:
    """
    Создает анализатор из данных пользователя
    
    Args:
        user_data: словарь с данными пользователя
        user_name: имя пользователя
        
    Returns:
        QuestionContextAnalyzer или None
    """
    model_data = user_data.get('confinement_model')
    if not model_data:
        logger.warning(f"Нет конфайнмент-модели для пользователя {user_name}")
        return None
    
    try:
        from confinement_model import ConfinementModel9
        # Если model_data уже является объектом ConfinementModel9
        if isinstance(model_data, ConfinementModel9):
            model = model_data
        else:
            # Если это словарь, создаем модель из словаря
            model = ConfinementModel9.from_dict(model_data)
        return QuestionContextAnalyzer(model, user_name)
    except Exception as e:
        logger.error(f"Ошибка при создании анализатора: {e}")
        return None


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'QuestionContextAnalyzer',
    'QuestionAnalyzer',  # Добавлен алиас
    'ConfinementReporter',
    'create_analyzer_from_user_data'
]
