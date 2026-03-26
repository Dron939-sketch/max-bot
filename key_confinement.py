#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 3: ДЕТЕКТОР КЛЮЧЕВОГО КОНФАЙНТМЕНТА (key_confinement.py)
Определяет главное ограничение в системе
ВЕРСИЯ 1.1 - ИСПРАВЛЕНЫ ОШИБКИ, ДОБАВЛЕНЫ НОВЫЕ МЕТОДЫ
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import logging

from confinement_model import ConfinementModel9, ConfinementElement

logger = logging.getLogger(__name__)


class KeyConfinementDetector:
    """
    Детектор ключевого конфайнтмента (главного ограничения)
    """
    
    # Типы элементов (дублируем здесь на случай, если их нет в модели)
    TYPE_RESULT = 'result'
    TYPE_IMMEDIATE_CAUSE = 'immediate_cause'
    TYPE_COMMON_CAUSE = 'common_cause'
    TYPE_UPPER_CAUSE = 'upper_cause'
    TYPE_CLOSING = 'closing'
    
    # Веса для комбинирования метрик
    WEIGHTS = {
        'centrality': 0.3,
        'loop_participation': 0.4,
        'strength': 0.2,
        'type_importance': 0.1
    }
    
    def __init__(self, model: ConfinementModel9, loops: List[Dict[str, Any]]):
        """
        Инициализация детектора
        
        Args:
            model: объект ConfinementModel9
            loops: список петель от LoopAnalyzer
        """
        self.model = model
        self.loops = loops
        self._element_types = self._get_element_types()
        
        logger.info(f"KeyConfinementDetector инициализирован для пользователя {model.user_id}")
        logger.info(f"Найдено петель: {len(loops)}")
    
    def _get_element_types(self) -> Dict[int, str]:
        """
        Получает типы элементов из модели
        """
        types = {}
        for eid, elem in self.model.elements.items():
            if elem and hasattr(elem, 'element_type'):
                types[eid] = elem.element_type
            else:
                # Определяем тип по ID элемента
                if eid == 9:
                    types[eid] = self.TYPE_CLOSING
                elif eid in [5, 6, 7]:
                    types[eid] = self.TYPE_COMMON_CAUSE
                elif eid in [2, 3, 4]:
                    types[eid] = self.TYPE_IMMEDIATE_CAUSE
                elif eid == 1:
                    types[eid] = self.TYPE_RESULT
                else:
                    types[eid] = self.TYPE_UPPER_CAUSE
        return types
    
    def detect(self) -> Optional[Dict[str, Any]]:
        """
        Определяет ключевой конфайнтмент
        
        Returns:
            dict: информация о ключевом элементе
        """
        logger.info("Начинаю поиск ключевого конфайнтмента...")
        
        # Метод 1: По центральности в графе
        centrality_scores = self._calculate_centrality()
        
        # Метод 2: По участию в петлях
        loop_participation = self._calculate_loop_participation()
        
        # Метод 3: По силе элемента
        strength_scores = self._calculate_strength_scores()
        
        # Метод 4: По типу элемента
        type_importance = self._calculate_type_importance()
        
        # Комбинируем с весами
        final_scores = self._combine_scores(
            centrality_scores,
            loop_participation,
            strength_scores,
            type_importance
        )
        
        if not final_scores:
            logger.warning("Не удалось вычислить оценки для элементов")
            return None
        
        # Находим лучший элемент
        best_eid = max(final_scores, key=final_scores.get)
        best_element = self.model.elements.get(best_eid)
        
        if not best_element:
            logger.warning(f"Элемент {best_eid} не найден в модели")
            return None
        
        # Получаем все оценки для лучшего элемента
        result = {
            'element_id': best_eid,
            'element': best_element,
            'score': final_scores[best_eid],
            'centrality_score': centrality_scores.get(best_eid, 0),
            'loop_participation': loop_participation.get(best_eid, 0),
            'strength_score': strength_scores.get(best_eid, 0),
            'type_importance': type_importance.get(best_eid, 0),
            'element_type': self._element_types.get(best_eid, 'unknown'),
            'description': self._generate_description(best_element),
            'intervention': self._suggest_intervention(best_element)
        }
        
        logger.info(f"Ключевой конфайнтмент: элемент {best_eid} ({best_element.name}) "
                   f"с оценкой {result['score']:.2f}")
        
        return result
    
    def detect_all(self, min_score: float = 0.3) -> List[Dict[str, Any]]:
        """
        Возвращает все элементы с их оценками, отсортированные по важности
        
        Args:
            min_score: минимальный порог оценки
        
        Returns:
            list: список элементов с оценками
        """
        # Вычисляем все оценки
        centrality = self._calculate_centrality()
        participation = self._calculate_loop_participation()
        strength = self._calculate_strength_scores()
        type_imp = self._calculate_type_importance()
        
        scores = self._combine_scores(centrality, participation, strength, type_imp)
        
        # Формируем результаты
        results = []
        for eid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            if score < min_score:
                continue
            
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            results.append({
                'element_id': eid,
                'element': element,
                'score': score,
                'centrality_score': centrality.get(eid, 0),
                'loop_participation': participation.get(eid, 0),
                'strength_score': strength.get(eid, 0),
                'type_importance': type_imp.get(eid, 0),
                'element_type': self._element_types.get(eid, 'unknown')
            })
        
        return results
    
    def _calculate_centrality(self) -> Dict[int, float]:
        """
        Вычисляет центральность элементов (насколько они важны в графе)
        """
        centrality = {}
        max_links = 0
        
        # Считаем связи для каждого элемента
        for eid in range(1, 10):
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            in_degree = len(element.caused_by) if hasattr(element, 'caused_by') else 0
            out_degree = len(element.causes) if hasattr(element, 'causes') else 0
            total = in_degree + out_degree
            
            centrality[eid] = total
            max_links = max(max_links, total)
        
        # Нормализуем
        if max_links > 0:
            centrality = {k: v / max_links for k, v in centrality.items()}
        
        return centrality
    
    def _calculate_loop_participation(self) -> Dict[int, float]:
        """
        Вычисляет, насколько часто элемент участвует в петлях
        """
        participation = defaultdict(int)
        
        for loop in self.loops:
            for eid in loop.get('cycle', []):
                participation[eid] += 1
        
        # Нормализуем
        max_participation = max(participation.values()) if participation else 1
        if max_participation > 0:
            participation = {k: v / max_participation for k, v in participation.items()}
        
        return participation
    
    def _calculate_strength_scores(self) -> Dict[int, float]:
        """
        Вычисляет оценки по силе элемента
        """
        scores = {}
        
        for eid in range(1, 10):
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            strength = getattr(element, 'strength', 0.5)
            # Учитываем также влияние петли (если элемент в петле)
            loop_boost = 1.0
            if any(eid in loop.get('cycle', []) for loop in self.loops):
                loop_boost = 1.2
            
            scores[eid] = min(strength * loop_boost, 1.0)
        
        return scores
    
    def _calculate_type_importance(self) -> Dict[int, float]:
        """
        Вычисляет важность на основе типа элемента
        """
        type_weights = {
            self.TYPE_CLOSING: 1.0,
            self.TYPE_COMMON_CAUSE: 0.9,
            self.TYPE_UPPER_CAUSE: 0.8,
            self.TYPE_IMMEDIATE_CAUSE: 0.6,
            self.TYPE_RESULT: 0.5
        }
        
        importance = {}
        for eid in range(1, 10):
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            elem_type = self._element_types.get(eid, self.TYPE_IMMEDIATE_CAUSE)
            importance[eid] = type_weights.get(elem_type, 0.5)
        
        return importance
    
    def _combine_scores(self, *score_dicts) -> Dict[int, float]:
        """
        Комбинирует несколько словарей с оценками
        """
        combined = defaultdict(float)
        
        for i, scores in enumerate(score_dicts):
            weight = list(self.WEIGHTS.values())[i] if i < len(self.WEIGHTS) else 0.1
            for eid, score in scores.items():
                combined[eid] += score * weight
        
        return dict(combined)
    
    def _generate_description(self, element: ConfinementElement) -> str:
        """
        Генерирует описание ключевого конфайнтмента
        """
        name = getattr(element, 'name', f'Элемент {element.id}')
        desc = getattr(element, 'description', '')[:50]
        
        base = f"**{name}** — вот что держит всю систему."
        
        # Детали в зависимости от ID элемента
        details = {
            1: f"Симптом «{desc}» возвращается снова и снова, потому что вся система его воспроизводит.",
            2: f"Твое поведение («{desc}») запускает цепную реакцию, которая возвращается к нему же.",
            3: f"Стратегия «{name}» кажется единственно возможной, но она же и ловушка.",
            4: f"Паттерн «{name}» незаметен, но именно через него все замыкается.",
            5: f"Убеждение «{desc}» — это линза, через которую ты видишь всё.",
            6: f"Система «{name}» создает правила, по которым ты играешь, даже не замечая.",
            7: f"Глубинное убеждение «{desc}» — это корень, из которого всё растет.",
            8: f"Связка «{name}» соединяет то, что кажется несовместимым, удерживая противоречия.",
            9: f"Картина мира «{desc}» — именно она не дает системе измениться."
        }
        
        return base + " " + details.get(element.id, "Это ключевая точка системы.")
    
    def _suggest_intervention(self, element: ConfinementElement) -> Dict[str, str]:
        """
        Предлагает интервенцию для работы с конфайнтментом
        """
        # Определяем тип элемента
        elem_type = self._element_types.get(element.id, self.TYPE_COMMON_CAUSE)
        
        # Библиотека интервенций по типам элементов
        interventions = {
            self.TYPE_RESULT: {
                'name': 'Работа с симптомом',
                'approach': 'Отслеживание и дневник симптомов',
                'method': 'Каждый день записывай, когда симптом проявляется и что ему предшествует',
                'exercise': 'Веди дневник симптомов в течение 3 недель, отмечая триггеры',
                'vak': 'kinesthetic',
                'duration': '21 день',
                'difficulty': 'Средняя',
                'first_step': 'Заведи блокнот или заметки в телефоне для отслеживания'
            },
            self.TYPE_IMMEDIATE_CAUSE: {
                'name': 'Изменение поведения',
                'approach': 'Замена автоматической реакции на осознанную',
                'method': 'Вместо привычного действия сделай паузу и выбери другое',
                'exercise': 'Найди 3 альтернативных способа реагировать в привычной ситуации',
                'vak': 'kinesthetic',
                'duration': '30 дней',
                'difficulty': 'Средняя',
                'first_step': 'Начни с малого: в одной ситуации сделай паузу на 3 секунды'
            },
            self.TYPE_COMMON_CAUSE: {
                'name': 'Работа с убеждениями',
                'approach': 'Поиск исключений и альтернатив',
                'method': 'Найди одно исключение из правила и исследуй его',
                'exercise': 'Запиши убеждение, найди 3 факта, которые ему противоречат',
                'vak': 'auditory_digital',
                'duration': '14 дней',
                'difficulty': 'Высокая',
                'first_step': 'Сформулируй убеждение письменно и найди одно исключение'
            },
            self.TYPE_UPPER_CAUSE: {
                'name': 'Изменение контекста',
                'approach': 'Работа с системой и средой',
                'method': 'Измени одно условие в своей среде на этой неделе',
                'exercise': 'Переставь мебель, смени маршрут, познакомься с новым человеком',
                'vak': 'auditory',
                'duration': '7 дней',
                'difficulty': 'Средняя',
                'first_step': 'Выбери одно условие для изменения и сделай это завтра'
            },
            self.TYPE_CLOSING: {
                'name': 'Трансформация картины мира',
                'approach': 'Переосмысление фундаментальных убеждений',
                'method': 'Представь, что мир устроен иначе',
                'exercise': 'Каждый день представляй альтернативную реальность и спрашивай "что бы я делал?"',
                'vak': 'visual',
                'duration': '30 дней',
                'difficulty': 'Очень высокая',
                'first_step': 'Напиши свою текущую картину мира, затем представь противоположную'
            }
        }
        
        intervention = interventions.get(elem_type, interventions[self.TYPE_COMMON_CAUSE])
        
        # Персонализируем под элемент
        result = {
            'target': getattr(element, 'name', f'Элемент {element.id}'),
            'element_id': element.id,
            'element_type': elem_type,
            'vector': getattr(element, 'vector', None),
            'level': getattr(element, 'level', None),
            **intervention
        }
        
        # Адаптируем описание под вектор
        if result.get('vector'):
            vector_names = {
                'СБ': 'безопасность и защиту',
                'ТФ': 'ресурсы и деньги',
                'УБ': 'удовольствие и смыслы',
                'ЧВ': 'чувства и отношения'
            }
            vector_word = vector_names.get(result['vector'], '')
            if vector_word:
                result['personalized'] = f"Учитывая твой фокус на {vector_word}, обрати особое внимание на работу с телом и ощущениями."
        
        return result
    
    def get_alternate_interventions(self, element: ConfinementElement, 
                                     max_alternatives: int = 3) -> List[Dict[str, str]]:
        """
        Возвращает альтернативные интервенции для элемента
        
        Args:
            element: элемент конфайнтмента
            max_alternatives: максимальное количество альтернатив
        
        Returns:
            list: список альтернативных интервенций
        """
        alternatives = []
        
        # Базовые альтернативы для всех типов
        base_alternatives = [
            {
                'name': 'Дневник наблюдений',
                'approach': 'Записывай все случаи проявления элемента',
                'exercise': 'Веди дневник в течение 2 недель',
                'vak': 'visual',
                'duration': '14 дней',
                'difficulty': 'Низкая'
            },
            {
                'name': 'Телесная практика',
                'approach': 'Работа через тело',
                'exercise': 'Ежедневное сканирование тела и дыхательные упражнения',
                'vak': 'kinesthetic',
                'duration': '21 день',
                'difficulty': 'Низкая'
            },
            {
                'name': 'Рефрейминг',
                'approach': 'Смена перспективы',
                'method': 'Посмотри на ситуацию с другой стороны',
                'exercise': 'Найди 3 положительных аспекта в том, что кажется проблемой',
                'vak': 'auditory_digital',
                'duration': '7 дней',
                'difficulty': 'Средняя'
            }
        ]
        
        for alt in base_alternatives[:max_alternatives]:
            alt['target'] = getattr(element, 'name', f'Элемент {element.id}')
            alternatives.append(alt)
        
        return alternatives
    
    def get_key_confainment_summary(self) -> str:
        """
        Возвращает краткое описание ключевого конфайнтмента для пользователя
        """
        key = self.detect()
        if not key:
            return "✨ Не удалось определить ключевой конфайнтмент. Возможно, система уже сбалансирована."
        
        element = key['element']
        intervention = key['intervention']
        
        summary = f"""
🔑 **КЛЮЧЕВОЙ КОНФАЙНТМЕНТ**

{key['description']}

📊 **Почему это важно:**
• Участвует в {int(key['loop_participation'] * 100)}% всех петель
• Центральность: {int(key['centrality_score'] * 100)}%
• Сила воздействия: {int(key['strength_score'] * 100)}%

🎯 **Рекомендуемая интервенция:**
*{intervention['approach']}*

📝 **Метод:** {intervention['method']}

🏋️ **Упражнение:** {intervention['exercise']}

⏱ **Длительность:** {intervention['duration']}
🎨 **Канал восприятия:** {intervention.get('vak', '')}

{intervention.get('personalized', '')}

💡 **Первый шаг:** {intervention.get('first_step', 'Начни с малого')}
"""
        return summary.strip()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def create_detector_from_model_data(model_data: Dict, loops: List[Dict], 
                                     user_id: int = None) -> Optional[KeyConfinementDetector]:
    """
    Создает детектор из сохраненных данных модели
    
    Args:
        model_data: словарь с данными модели
        loops: список петель
        user_id: ID пользователя
    """
    try:
        from confinement_model import ConfinementModel9
        model = ConfinementModel9.from_dict(model_data)
        if user_id:
            model.user_id = user_id
        return KeyConfinementDetector(model, loops)
    except Exception as e:
        logger.error(f"Ошибка при создании детектора: {e}")
        return None


def format_key_confinement_for_display(key_confinement: Dict[str, Any]) -> str:
    """
    Форматирует ключевой конфайнтмент для отображения
    
    Args:
        key_confinement: результат detect()
    
    Returns:
        str: отформатированный текст
    """
    if not key_confinement:
        return "Ключевой конфайнтмент не определен."
    
    element = key_confinement['element']
    score = key_confinement['score']
    
    # Оценка важности
    if score > 0.7:
        importance = "🔴 КРИТИЧЕСКИ ВАЖНЫЙ"
    elif score > 0.4:
        importance = "🟠 ВАЖНЫЙ"
    else:
        importance = "🟡 ЗНАЧИМЫЙ"
    
    lines = [
        f"{importance}",
        "",
        f"**{element.name}**",
        f"{getattr(element, 'description', '')[:200]}",
        "",
        f"📊 Оценка: {score:.0%}",
        "",
        key_confinement['description'],
        "",
        "🎯 **Рекомендация:**",
        key_confinement['intervention']['approach']
    ]
    
    return "\n".join(lines)
