# confinement_model.py
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы из существующего кода (предполагаем, что они определены)
# В реальном коде нужно импортировать из основного модуля
VECTORS = {
    'СБ': {'name': 'Самосохранение', 'emoji': '🛡️', 'levels': {1: {'desc': 'Тревога, страх'}, 2: {'desc': 'Беспокойство'}, 3: {'desc': 'Осторожность'}, 4: {'desc': 'Уверенность'}, 5: {'desc': 'Безопасность'}, 6: {'desc': 'Гармония'}}},
    'ТФ': {'name': 'Территория и финансы', 'emoji': '💰', 'levels': {1: {'desc': 'Нехватка'}, 2: {'desc': 'Дефицит'}, 3: {'desc': 'Достаточно'}, 4: {'desc': 'Избыток'}, 5: {'desc': 'Свобода'}, 6: {'desc': 'Изобилие'}}},
    'УБ': {'name': 'Удовольствие и баланс', 'emoji': '🎯', 'levels': {1: {'desc': 'Апатия'}, 2: {'desc': 'Скука'}, 3: {'desc': 'Интерес'}, 4: {'desc': 'Радость'}, 5: {'desc': 'Счастье'}, 6: {'desc': 'Эйфория'}}},
    'ЧВ': {'name': 'Чувства и восприятие', 'emoji': '💭', 'levels': {1: {'desc': 'Оцепенение'}, 2: {'desc': 'Подавленность'}, 3: {'desc': 'Спокойствие'}, 4: {'desc': 'Интерес'}, 5: {'desc': 'Понимание'}, 6: {'desc': 'Просветление'}}}
}

LEVEL_PROFILES = {
    'СБ': {
        1: {'archetype': 'Жертва', 'quote': 'Мир опасен, я беззащитен', 'triggers': ['громкие звуки', 'неожиданности']},
        2: {'archetype': 'Беспокойный', 'quote': 'Надо быть начеку', 'triggers': ['новое', 'перемены']}
    },
    'ТФ': {
        1: {'archetype': 'Нищий', 'quote': 'Мне никогда не хватит', 'triggers': ['траты', 'цены']},
        2: {'archetype': 'Экономный', 'quote': 'Надо копить', 'triggers': ['покупки']}
    }
}

def level(score: float) -> int:
    """Преобразует балл в уровень (1-6)"""
    if score <= 1.5:
        return 1
    elif score <= 2.5:
        return 2
    elif score <= 3.5:
        return 3
    elif score <= 4.5:
        return 4
    elif score <= 5.5:
        return 5
    else:
        return 6


class ConfinementElement:
    """
    Элемент конфайнмент-модели (один из 9 кружочков)
    """
    
    def __init__(self, element_id: int, name: str = None):
        self.id = element_id  # 1..9
        self.name = name or f"Элемент {element_id}"
        self.description = ""
        self.element_type = None  # 'result', 'cause', 'common', 'closing'
        self.vector = None  # СБ, ТФ, УБ, ЧВ (если привязан)
        self.level = None  # 1..6 (если привязан)
        self.archetype = None  # из LEVEL_PROFILES
        self.strength = 0.5  # сила влияния 0-1
        self.vak = 'digital'  # ведущий ВАК-канал
        
        # Связи
        self.causes = []  # какие элементы вызывает
        self.caused_by = []  # какими элементами вызывается
        self.amplifies = []  # какие элементы усиливает
        
    def to_dict(self) -> dict:
        """Для сохранения в user_data"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.element_type,
            'vector': self.vector,
            'level': self.level,
            'archetype': self.archetype,
            'strength': self.strength,
            'vak': self.vak,
            'causes': self.causes.copy(),
            'caused_by': self.caused_by.copy(),
            'amplifies': self.amplifies.copy()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConfinementElement':
        """Восстановление из словаря"""
        element = cls(data['id'], data.get('name'))
        element.description = data.get('description', '')
        element.element_type = data.get('type')
        element.vector = data.get('vector')
        element.level = data.get('level')
        element.archetype = data.get('archetype')
        element.strength = data.get('strength', 0.5)
        element.vak = data.get('vak', 'digital')
        element.causes = data.get('causes', [])
        element.caused_by = data.get('caused_by', [])
        element.amplifies = data.get('amplifies', [])
        return element
    
    def __repr__(self) -> str:
        return f"<ConfinementElement {self.id}: {self.name}>"


class ConfinementModel9:
    """
    Полная 9-элементная конфайнмент-модель по Мейстеру
    """
    
    # Константы для типов элементов
    TYPE_RESULT = 'result'  # элемент 1
    TYPE_IMMEDIATE_CAUSE = 'immediate_cause'  # элементы 2,3,4
    TYPE_COMMON_CAUSE = 'common_cause'  # элемент 5
    TYPE_UPPER_CAUSE = 'upper_cause'  # элементы 6,7,8
    TYPE_CLOSING = 'closing'  # элемент 9
    
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.elements: Dict[int, Optional[ConfinementElement]] = {i: None for i in range(1, 10)}
        self.links = []  # все связи
        self.loops = []  # найденные петли
        self.key_confinement = None  # главное ограничение
        self.is_closed = False  # замкнута ли система
        self.closure_score = 0.0  # степень замыкания
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Метаданные для построения
        self.source_scores = {}  # исходные баллы
        self.source_history = []  # исходная история
    
    def build_from_profile(self, scores: dict, history: list = None) -> 'ConfinementModel9':
        """
        Строит модель из психологического профиля
        Это главный метод модуля
        """
        logger.info(f"Building confinement model for user {self.user_id}")
        self.source_scores = scores
        self.source_history = history or []
        
        try:
            # Шаг 1: Определяем результат (элемент 1) - главная жалоба
            self.elements[1] = self._extract_main_symptom()
            
            # Шаг 2: Три непосредственные причины (элементы 2,3,4) - из векторов
            self.elements[2] = self._element_from_vector('СБ')
            self.elements[3] = self._element_from_vector('ТФ')
            self.elements[4] = self._element_from_vector('УБ')
            
            # Шаг 3: Проверяем цепочку усиления 2→3→4
            self._ensure_causal_chain([2, 3, 4])
            
            # Шаг 4: Общая причина (элемент 5) - из комбинации
            self.elements[5] = self._find_common_cause([2, 3, 4])
            
            # Шаг 5: Причины верхнего уровня (элементы 6,7,8)
            self.elements[6] = self._find_cause_for([2, 5])
            self.elements[7] = self._find_cause_for([6, 2])
            self.elements[8] = self._find_linked_to(7, causing=[6, 5])
            
            # Шаг 6: Замыкающий элемент (элемент 9) - самый важный
            self.elements[9] = self._find_closing_element()
            
            # Шаг 7: Проверяем и валидируем связи
            self._validate_links()
            
            # Шаг 8: Ищем петли
            self._find_loops()
            
            # Шаг 9: Определяем ключевой конфайнмент
            self._identify_key_confinement()
            
            # Шаг 10: Оцениваем замыкание
            self._calculate_closure()
            
            self.updated_at = datetime.now()
            logger.info(f"Model built successfully for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error building model for user {self.user_id}: {e}")
            # Создаем минимальную модель, если что-то пошло не так
            self._build_fallback_model()
        
        return self
    
    def _build_fallback_model(self):
        """Создает запасную модель при ошибке"""
        for i in range(1, 10):
            if not self.elements[i]:
                self.elements[i] = ConfinementElement(i, f"Элемент {i}")
                self.elements[i].description = "Требуется дополнительный анализ"
                self.elements[i].strength = 0.5
        
        self._validate_links()
        self.is_closed = False
        self.closure_score = 0.3
    
    def _extract_main_symptom(self) -> ConfinementElement:
        """
        Извлекает главный симптом/жалобу из профиля и истории
        Элемент 1 - результат системы
        """
        if not self.source_scores:
            element = ConfinementElement(1, "Симптом")
            element.description = "Требуется анализ симптомов"
            element.element_type = self.TYPE_RESULT
            element.strength = 1.0
            return element
        
        # Определяем самый низкий уровень
        min_vector = min(self.source_scores.items(), 
                        key=lambda x: level(x[1]))
        vector, score = min_vector
        vector_name = VECTORS.get(vector, {}).get('name', vector)
        vector_emoji = VECTORS.get(vector, {}).get('emoji', '🔍')
        lvl = level(score)
        level_info = VECTORS.get(vector, {}).get('levels', {}).get(lvl, {})
        
        # Получаем живой профиль
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        
        # Извлекаем из истории последние жалобы
        recent_complaints = self._extract_complaints_from_history()
        
        # Формируем описание
        if profile and profile.get('quote'):
            description = f"{vector_emoji} {profile['quote']}"
        else:
            desc_text = level_info.get('desc', 'требует внимания')
            description = f"{vector_emoji} {desc_text}"
        
        element = ConfinementElement(1, f"Симптом: {vector_name}")
        element.description = description
        element.element_type = self.TYPE_RESULT
        element.vector = vector
        element.level = lvl
        element.archetype = profile.get('archetype') if profile else None
        element.strength = 1.0  # результат всегда сильный
        element.vak = 'kinesthetic'  # симптомы обычно телесные
        
        # Добавляем информацию из истории
        if recent_complaints:
            element.description += f"\n\n🔍 *Из диалогов:* {recent_complaints[0][:100]}..."
        
        return element
    
    def _element_from_vector(self, vector: str) -> ConfinementElement:
        """
        Создает элемент на основе вектора (СБ, ТФ, УБ, ЧВ)
        Для элементов 2,3,4 - непосредственные причины
        """
        score = self.source_scores.get(vector, 3.0)
        lvl = level(score)
        level_info = VECTORS.get(vector, {}).get('levels', {}).get(lvl, {})
        vector_name = VECTORS.get(vector, {}).get('name', vector)
        vector_emoji = VECTORS.get(vector, {}).get('emoji', '🔍')
        
        # Получаем живой профиль
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        
        # Определяем тип элемента по позиции
        element_map = {
            'СБ': 2,
            'ТФ': 3,
            'УБ': 4,
            'ЧВ': 4  # ЧВ может быть в разных позициях
        }
        element_id = element_map.get(vector, 4)
        
        element = ConfinementElement(element_id, f"{vector_emoji} {vector_name}")
        
        # Формируем описание
        level_name = level_info.get('name', f'Уровень {lvl}')
        level_desc = level_info.get('desc', '')
        element.description = f"**{level_name}** — {level_desc}"
        element.element_type = self.TYPE_IMMEDIATE_CAUSE
        element.vector = vector
        element.level = lvl
        element.archetype = profile.get('archetype') if profile else None
        element.strength = lvl / 6.0  # сила пропорциональна уровню
        element.vak = self._vector_to_vak(vector, lvl)
        
        # Добавляем триггеры из профиля
        if profile and profile.get('triggers'):
            triggers = profile['triggers'][:2]  # первые два
            element.description += "\n\n*Триггеры:*\n" + "\n".join(f"• {t}" for t in triggers)
        
        return element
    
    def _ensure_causal_chain(self, element_ids: list):
        """
        Проверяет и обеспечивает цепочку 2→3→4 (каждый усиливает следующий)
        """
        for i in range(len(element_ids)-1):
            cause_id = element_ids[i]
            effect_id = element_ids[i+1]
            
            cause = self.elements.get(cause_id)
            effect = self.elements.get(effect_id)
            
            if not cause or not effect:
                continue
            
            # Добавляем связь усиления
            if effect_id not in cause.amplifies:
                cause.amplifies.append(effect_id)
            if cause_id not in effect.caused_by:
                effect.caused_by.append(cause_id)
            
            # Описание связи
            self.links.append({
                'from': cause_id,
                'to': effect_id,
                'type': 'amplifies',
                'strength': cause.strength * effect.strength,
                'description': f"{cause.name} усиливает {effect.name}"
            })
    
    def _find_common_cause(self, effect_ids: list) -> ConfinementElement:
        """
        Находит общую причину для нескольких элементов (элемент 5)
        """
        # Собираем векторы эффектов
        vectors = []
        for eid in effect_ids:
            elem = self.elements.get(eid)
            if elem and elem.vector:
                vectors.append(elem.vector)
        
        # Определяем общую причину на основе комбинации
        if 'СБ' in vectors and 'ТФ' in vectors and 'УБ' in vectors:
            return self._create_identity_element()
        elif 'СБ' in vectors and 'ТФ' in vectors:
            return self._create_belief_element('СБ_ТФ')
        else:
            # По умолчанию - убеждения
            return self._create_belief_element('common')
    
    def _create_identity_element(self) -> ConfinementElement:
        """Создает элемент идентичности (обычно элемент 5 или 6)"""
        # Находим самый слабый вектор для определения архетипа
        if self.source_scores:
            weakest = min(self.source_scores.items(), 
                         key=lambda x: level(x[1]))
            vector, score = weakest
            lvl = level(score)
            profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        else:
            profile = {}
        
        element = ConfinementElement(5, "🎭 Идентичность")
        element.description = profile.get('archetype_desc', 
            "То, кем ты себя считаешь в этой ситуации")
        element.element_type = self.TYPE_COMMON_CAUSE
        element.archetype = profile.get('archetype')
        element.strength = 0.8
        element.vak = 'visual'
        
        if profile and profile.get('quote'):
            element.description += f"\n\n💬 {profile['quote']}"
        
        return element
    
    def _create_belief_element(self, belief_type: str) -> ConfinementElement:
        """Создает элемент убеждения"""
        # Типичные убеждения из профилей
        beliefs = {
            'СБ_ТФ': "Я не справлюсь сам, мир опасен",
            'СБ_УБ': "Лучше не знать правды",
            'ТФ_УБ': "Все сложно, легче плыть по течению",
            'common': "Есть вещи, которые я не могу изменить"
        }
        
        element = ConfinementElement(5, "💭 Убеждение")
        element.description = beliefs.get(belief_type, beliefs['common'])
        element.element_type = self.TYPE_COMMON_CAUSE
        element.strength = 0.7
        element.vak = 'auditory_digital'
        
        return element
    
    def _find_cause_for(self, effect_ids: list) -> ConfinementElement:
        """
        Находит причину для списка эффектов (элементы 6,7)
        """
        # Собираем все векторы эффектов
        vectors = []
        for eid in effect_ids:
            elem = self.elements.get(eid)
            if elem and elem.vector:
                vectors.append(elem.vector)
        
        # Определяем следующий уровень
        if len(effect_ids) == 2:
            # Причина для пары элементов - часто система/среда
            return self._create_systems_element(effect_ids)
        else:
            # По умолчанию - глубинные убеждения
            return self._create_deep_belief()
    
    def _create_systems_element(self, effect_ids: list) -> ConfinementElement:
        """Создает элемент систем/среды"""
        element_id = 6 if 6 not in effect_ids else 7
        element = ConfinementElement(element_id, "🏛 Система")
        element.description = "Семья, работа, культура — контекст, в котором это происходит"
        element.element_type = self.TYPE_UPPER_CAUSE
        element.strength = 0.6
        element.vak = 'auditory'
        
        return element
    
    def _create_deep_belief(self) -> ConfinementElement:
        """Создает элемент глубинного убеждения"""
        element = ConfinementElement(7, "⚓ Глубинное убеждение")
        element.description = "То, во что ты веришь на самом глубоком уровне"
        element.element_type = self.TYPE_UPPER_CAUSE
        element.strength = 0.9
        element.vak = 'digital'
        
        return element
    
    def _find_linked_to(self, source_id: int, causing: list) -> ConfinementElement:
        """
        Находит элемент, связанный с source_id и вызывающий указанные элементы
        Элемент 8 - связка
        """
        source = self.elements.get(source_id)
        
        # Элемент 8 часто связан с идентичностью и убеждениями
        element = ConfinementElement(8, "🔗 Связка")
        element.description = "То, что соединяет верхний и нижний уровни"
        element.element_type = self.TYPE_UPPER_CAUSE
        
        # Определяем ВАК на основе source
        if source and source.vak:
            element.vak = 'visual' if source.vak == 'kinesthetic' else 'auditory'
        else:
            element.vak = 'auditory_digital'
        
        return element
    
    def _find_closing_element(self) -> ConfinementElement:
        """
        Находит замыкающий элемент (9) - самый важный в модели
        """
        # Анализируем, что может замкнуть систему
        # Определяем по самому слабому месту
        if self.source_scores:
            weakest = min(self.source_scores.items(), 
                         key=lambda x: level(x[1]))
            vector, score = weakest
            lvl = level(score)
        else:
            vector, lvl = 'СБ', 3
        
        # Карта замыкающих элементов
        closing_map = {
            'СБ': "Мир опасен, нужно защищаться",
            'ТФ': "Ресурсов мало, их надо экономить",
            'УБ': "Все не случайно, во всем есть смысл",
            'ЧВ': "Людям нельзя доверять"
        }
        
        element = ConfinementElement(9, "🌍 Картина мира")
        element.description = closing_map.get(vector, 
            "Система самоподдерживается через это убеждение")
        element.element_type = self.TYPE_CLOSING
        element.vector = vector
        element.level = lvl
        element.strength = 1.0  # замыкание всегда сильно
        element.vak = 'visual'  # картина мира - визуальна
        
        return element
    
    def _validate_links(self):
        """Проверяет и добавляет все необходимые связи"""
        # Связи по Мейстеру: каждый элемент связан с другими
        
        # Добавляем стандартные связи, если элементы существуют
        standard_links = [
            (1, 2), (1, 3), (1, 4),  # результат ← причины
            (2, 3), (3, 4),           # цепочка усиления
            (5, 2), (5, 3), (5, 4),   # общая причина → все
            (6, 2), (6, 5),           # 6 → 2 и 5
            (7, 6), (7, 2),           # 7 → 6 и 2
            (8, 7), (8, 6), (8, 5),   # 8 → 7,6,5
            (9, 7), (9, 8),           # 9 → 7 и 8
            (4, 9), (1, 9)            # 4 и 1 → 9 (замыкание)
        ]
        
        for from_id, to_id in standard_links:
            if self.elements.get(from_id) and self.elements.get(to_id):
                from_elem = self.elements[from_id]
                to_elem = self.elements[to_id]
                
                if to_id not in from_elem.causes:
                    from_elem.causes.append(to_id)
                if from_id not in to_elem.caused_by:
                    to_elem.caused_by.append(from_id)
                
                # Проверяем, нет ли уже такой связи
                link_exists = any(
                    l['from'] == from_id and l['to'] == to_id 
                    for l in self.links
                )
                if not link_exists:
                    self.links.append({
                        'from': from_id,
                        'to': to_id,
                        'type': 'causes',
                        'strength': 0.7,
                        'description': f"{from_elem.name} влияет на {to_elem.name}"
                    })
    
    def _find_loops(self):
        """Находит рекурсивные петли в модели"""
        self.loops = []
        
        # Ищем циклы длины 3+
        # Основные возможные петли:
        
        # Петля 1: Симптом → Поведение → Убеждение → Симптом
        loop1 = self._find_cycle([1, 2, 6, 9, 1])
        if loop1:
            self.loops.append({
                'elements': loop1,
                'type': 'symptom_behavior_belief',
                'description': 'Симптом вызывает поведение, которое укрепляет убеждение, возвращаясь к симптому',
                'strength': self._calculate_loop_strength(loop1)
            })
        
        # Петля 2: Идентичность → Система → Среда → Идентичность
        loop2 = self._find_cycle([5, 6, 7, 8, 5])
        if loop2:
            self.loops.append({
                'elements': loop2,
                'type': 'identity_system_environment',
                'description': 'Идентичность определяет системы, системы создают среду, среда подтверждает идентичность',
                'strength': self._calculate_loop_strength(loop2)
            })
        
        # Петля 3: Полный цикл через замыкание
        loop3 = self._find_cycle([1, 2, 3, 4, 9, 1])
        if loop3:
            self.loops.append({
                'elements': loop3,
                'type': 'full_cycle',
                'description': 'Полный цикл самоподдержания системы',
                'strength': self._calculate_loop_strength(loop3)
            })
    
    def _find_cycle(self, potential_cycle: list) -> Optional[list]:
        """Проверяет, существует ли указанный цикл"""
        for i in range(len(potential_cycle)-1):
            from_id = potential_cycle[i]
            to_id = potential_cycle[i+1]
            
            # Проверяем, есть ли элемент
            if not self.elements.get(from_id) or not self.elements.get(to_id):
                return None
            
            # Проверяем, есть ли связь
            if to_id not in self.elements[from_id].causes:
                return None
        
        return potential_cycle
    
    def _calculate_loop_strength(self, cycle: list) -> float:
        """Вычисляет силу петли"""
        strength = 1.0
        for i in range(len(cycle)-1):
            from_id = cycle[i]
            to_id = cycle[i+1]
            
            # Ищем связь
            for link in self.links:
                if link['from'] == from_id and link['to'] == to_id:
                    strength *= link['strength']
                    break
        
        return min(strength, 1.0)  # не больше 1
    
    def _identify_key_confinement(self):
        """Определяет ключевой конфайнмент (главное ограничение)"""
        candidates = []
        
        for elem_id, element in self.elements.items():
            if not element:
                continue
            
            # Влияние = сколько элементов вызывает
            influence = len(element.causes)
            
            # Зависимость = сколько элементов на него влияют
            dependency = len(element.caused_by)
            
            # Важность = влияние * зависимость * сила
            importance = (influence + 1) * (dependency + 1) * element.strength
            
            candidates.append({
                'id': elem_id,
                'element': element,
                'influence': influence,
                'dependency': dependency,
                'importance': importance
            })
        
        # Сортируем по важности
        candidates.sort(key=lambda x: x['importance'], reverse=True)
        
        if candidates:
            top = candidates[0]
            self.key_confinement = {
                'id': top['id'],
                'element': top['element'],
                'description': self._describe_confinement(top),
                'importance': top['importance']
            }
    
    def _describe_confinement(self, candidate: dict) -> str:
        """Описывает ключевой конфайнмент человеческим языком"""
        elem = candidate['element']
        
        descriptions = {
            1: f"Главный симптом: {elem.description[:50]}... Держит всю систему в напряжении.",
            2: f"Ключевое поведение: {elem.name}. Оно запускает цепочку реакций.",
            3: f"Основная стратегия: {elem.name}. Через нее все замыкается.",
            4: f"Критический паттерн: {elem.name}. Без его изменения система не сдвинется.",
            5: f"Центральное убеждение: {elem.description[:50]}... Оно пронизывает все уровни.",
            6: f"Главная система: {elem.name}. Контекст, который держит проблему.",
            7: f"Глубинное убеждение: {elem.description[:50]}... Корень всего.",
            8: f"Ключевая связка: {elem.name}. То, что соединяет несовместимое.",
            9: f"Замыкающий элемент: {elem.description[:50]}... Именно он не дает системе измениться."
        }
        
        return descriptions.get(elem.id, "Ключевое ограничение требует анализа")
    
    def _calculate_closure(self):
        """Оценивает степень замыкания системы"""
        # Проверяем наличие петли через элемент 9
        has_closing_loop = False
        for loop in self.loops:
            if 9 in loop['elements']:
                has_closing_loop = True
                self.closure_score = loop['strength']
                break
        
        if has_closing_loop:
            self.is_closed = self.closure_score > 0.5
        else:
            self.is_closed = False
            self.closure_score = 0.0
    
    def _extract_complaints_from_history(self) -> list:
        """Извлекает жалобы из истории диалогов"""
        complaints = []
        
        if not self.source_history:
            return complaints
        
        # Ключевые слова жалоб
        complaint_keywords = [
            'беспокоит', 'проблема', 'не могу', 'тяжело', 'трудно',
            'раздражает', 'бесит', 'достало', 'устал', 'грустно',
            'страшно', 'боюсь', 'тревожно', 'одиноко'
        ]
        
        for entry in self.source_history[-10:]:  # последние 10
            if isinstance(entry, dict) and entry.get('role') == 'user':
                text = entry.get('text', '').lower()
                for keyword in complaint_keywords:
                    if keyword in text:
                        complaints.append(entry.get('text', ''))
                        break
        
        return complaints
    
    def _vector_to_vak(self, vector: str, level: int) -> str:
        """Определяет ведущий ВАК-канал для вектора и уровня"""
        mapping = {
            'СБ': 'kinesthetic',  # реакция на угрозу - телесная
            'ТФ': 'digital',      # ресурсы - концептуальные
            'УБ': 'visual',       # понимание мира - визуальное
            'ЧВ': 'auditory'      # отношения - слуховые
        }
        
        # Корректировка по уровню
        if level <= 2:
            return mapping.get(vector, 'kinesthetic')
        elif level <= 4:
            return 'auditory_digital'
        else:
            return 'visual'
    
    def to_dict(self) -> dict:
        """Сериализация для сохранения"""
        return {
            'user_id': self.user_id,
            'elements': {k: v.to_dict() if v else None for k, v in self.elements.items()},
            'links': self.links.copy(),
            'loops': self.loops.copy(),
            'key_confinement': self.key_confinement,
            'is_closed': self.is_closed,
            'closure_score': self.closure_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConfinementModel9':
        """Десериализация"""
        model = cls(data.get('user_id'))
        
        # Восстанавливаем элементы
        elements_data = data.get('elements', {})
        for k, v in elements_data.items():
            if v:
                model.elements[int(k)] = ConfinementElement.from_dict(v)
        
        model.links = data.get('links', [])
        model.loops = data.get('loops', [])
        model.key_confinement = data.get('key_confinement')
        model.is_closed = data.get('is_closed', False)
        model.closure_score = data.get('closure_score', 0.0)
        
        # Восстанавливаем даты
        try:
            model.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
            model.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        except:
            model.created_at = datetime.now()
            model.updated_at = datetime.now()
        
        return model
