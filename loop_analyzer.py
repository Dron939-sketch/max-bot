#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 2: АНАЛИЗ ПЕТЕЛЬ (loop_analyzer.py)
Анализирует рекурсивные петли в конфайнтмент-модели
ВЕРСИЯ 1.1 - ИСПРАВЛЕНЫ ОШИБКИ, ДОБАВЛЕНЫ НОВЫЕ МЕТОДЫ
"""

from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import datetime
import logging

from confinement_model import ConfinementModel9, ConfinementElement

# Настройка логирования
logger = logging.getLogger(__name__)


class LoopAnalyzer:
    """
    Анализирует рекурсивные петли в конфайнтмент-модели
    """
    
    # Константы для типов петель
    LOOP_TYPE_MASTER = 'master_loop'
    LOOP_TYPE_IDENTITY = 'identity_loop'
    LOOP_TYPE_BEHAVIORAL = 'behavioral_loop'
    LOOP_TYPE_CLOSING = 'closing_loop'
    LOOP_TYPE_MINOR = 'minor_loop'
    
    # Описания типов петель
    LOOP_DESCRIPTIONS = {
        LOOP_TYPE_MASTER: {
            'name': 'Главная петля',
            'description': '🔴 Главная петля, замыкающая всю систему',
            'emoji': '🔴',
            'color': 'red',
            'advice': 'Это центральный механизм. Работайте с ним в первую очередь.'
        },
        LOOP_TYPE_IDENTITY: {
            'name': 'Идентичностная петля',
            'description': '🟠 Идентичность и симптомы усиливают друг друга',
            'emoji': '🟠',
            'color': 'orange',
            'advice': 'Ваше самовосприятие и симптомы взаимосвязаны. Начните с вопроса "кто я?"'
        },
        LOOP_TYPE_BEHAVIORAL: {
            'name': 'Поведенческая петля',
            'description': '🟡 Поведенческие реакции зациклены',
            'emoji': '🟡',
            'color': 'yellow',
            'advice': 'Ваши автоматические реакции создают повторяющиеся ситуации.'
        },
        LOOP_TYPE_CLOSING: {
            'name': 'Замыкающая петля',
            'description': '🔵 Петля через замыкающий элемент',
            'emoji': '🔵',
            'color': 'blue',
            'advice': 'Система замыкается через ключевое убеждение.'
        },
        LOOP_TYPE_MINOR: {
            'name': 'Второстепенная петля',
            'description': '⚪ Второстепенная петля',
            'emoji': '⚪',
            'color': 'gray',
            'advice': 'Менее значимая петля, но тоже влияет на систему.'
        }
    }
    
    def __init__(self, model_or_context):
        """
        Инициализация анализатора
        
        Args:
            model_or_context: ConfinementModel9 или UserContext объект
        """
        self.model = None
        self._visited: Set[int] = set()
        self._path: List[int] = []
        self._analysis_time: Optional[datetime] = None
        self.significant_loops: List[Dict[str, Any]] = []
        
        # Проверяем тип переданного объекта
        if isinstance(model_or_context, ConfinementModel9):
            self.model = model_or_context
            logger.info(f"LoopAnalyzer инициализирован с ConfinementModel для пользователя {self.model.user_id}")
        else:
            # Это UserContext или другой объект
            self._init_from_context(model_or_context)
    
    @classmethod
    def from_context(cls, context) -> Optional['LoopAnalyzer']:
        """
        Создает анализатор из UserContext
        
        Args:
            context: объект UserContext
        
        Returns:
            LoopAnalyzer или None при ошибке
        """
        try:
            return cls(context)
        except Exception as e:
            logger.error(f"Ошибка создания LoopAnalyzer из контекста: {e}")
            return None
    
    def _init_from_context(self, context):
        """
        Инициализирует модель из UserContext
        """
        logger.info("Инициализация LoopAnalyzer из UserContext")
        
        # Пытаемся извлечь модель из context
        if hasattr(context, 'confinement_model'):
            self.model = context.confinement_model
            logger.info("✅ Модель извлечена из context.confinement_model")
        elif hasattr(context, 'get_confinement_model'):
            self.model = context.get_confinement_model()
            logger.info("✅ Модель извлечена через get_confinement_model")
        elif hasattr(context, 'model'):
            self.model = context.model
            logger.info("✅ Модель извлечена из context.model")
        else:
            # Создаем пустую модель для тестирования
            logger.warning("⚠️ Не удалось найти confinement_model, создаю тестовую модель")
            self._create_test_model(context)
        
        if self.model and hasattr(self.model, 'user_id'):
            logger.info(f"LoopAnalyzer готов для пользователя {self.model.user_id}")
    
    def _create_test_model(self, context):
        """
        Создает тестовую модель на основе deep_patterns из UserContext
        """
        from confinement_model import ConfinementModel9, ConfinementElement
        
        user_id = getattr(context, 'user_id', None) or getattr(context, 'id', 99999)
        self.model = ConfinementModel9(user_id=user_id)
        
        # Пытаемся извлечь deep_patterns
        deep_patterns = {}
        if hasattr(context, 'deep_patterns'):
            deep_patterns = context.deep_patterns
        elif hasattr(context, 'get_deep_patterns'):
            deep_patterns = context.get_deep_patterns()
        
        # Заполняем модель на основе deep_patterns
        if deep_patterns:
            self._fill_model_from_patterns(deep_patterns)
        else:
            # Создаем стандартные элементы
            for i in range(1, 10):
                self.model.elements[i] = ConfinementElement(i, f"Элемент {i}")
                self.model.elements[i].description = f"Описание элемента {i}"
                self.model.elements[i].strength = 0.5
            
            # Создаем тестовую петлю
            self.model.elements[1].causes = [2]
            self.model.elements[2].causes = [3]
            self.model.elements[3].causes = [4]
            self.model.elements[4].causes = [1]
            
            self.model.links = [
                {'from': 1, 'to': 2, 'strength': 0.7},
                {'from': 2, 'to': 3, 'strength': 0.7},
                {'from': 3, 'to': 4, 'strength': 0.7},
                {'from': 4, 'to': 1, 'strength': 0.7}
            ]
    
    def _fill_model_from_patterns(self, patterns: Dict):
        """
        Заполняет модель из deep_patterns
        """
        from confinement_model import ConfinementElement
        
        # Определяем элементы на основе паттернов
        elements_info = {
            1: {'name': 'Симптом/Результат', 'type': 'result', 'desc': 'Проявление проблемы'},
            2: {'name': 'Непосредственная причина', 'type': 'immediate', 'desc': 'Триггер ситуации'},
            3: {'name': 'Поведенческая реакция', 'type': 'behavior', 'desc': 'Автоматическое действие'},
            4: {'name': 'Эмоциональная реакция', 'type': 'emotion', 'desc': 'Чувства и ощущения'},
            5: {'name': 'Мысль/Убеждение', 'type': 'thought', 'desc': 'Внутренний диалог'},
            6: {'name': 'Идентичность', 'type': 'identity', 'desc': 'Кто я в этой ситуации'},
            7: {'name': 'Ценности', 'type': 'values', 'desc': 'Что для меня важно'},
            8: {'name': 'Способности', 'type': 'capabilities', 'desc': 'Что я могу'},
            9: {'name': 'Замыкающий элемент', 'type': 'closing', 'desc': 'Глобальное убеждение'}
        }
        
        # Создаем элементы
        for elem_id, info in elements_info.items():
            self.model.elements[elem_id] = ConfinementElement(elem_id, info['name'])
            self.model.elements[elem_id].description = info['desc']
            self.model.elements[elem_id].element_type = info['type']
            self.model.elements[elem_id].strength = 0.6
        
        # Создаем связи на основе паттернов
        attachment = patterns.get('привязанность', 'тревожный')
        defense = patterns.get('защитные механизмы', ['избегание'])
        
        # Настраиваем связи в зависимости от типа привязанности
        if attachment == 'тревожный':
            # Петля тревожной привязанности
            self.model.elements[1].causes = [2]
            self.model.elements[2].causes = [3]
            self.model.elements[3].causes = [4]
            self.model.elements[4].causes = [5]
            self.model.elements[5].causes = [1]
            
            self.model.links = [
                {'from': 1, 'to': 2, 'strength': 0.8},
                {'from': 2, 'to': 3, 'strength': 0.7},
                {'from': 3, 'to': 4, 'strength': 0.9},
                {'from': 4, 'to': 5, 'strength': 0.6},
                {'from': 5, 'to': 1, 'strength': 0.8}
            ]
        elif attachment == 'избегающий':
            # Петля избегающей привязанности
            self.model.elements[1].causes = [5]
            self.model.elements[5].causes = [2]
            self.model.elements[2].causes = [3]
            self.model.elements[3].causes = [4]
            self.model.elements[4].causes = [1]
            
            self.model.links = [
                {'from': 1, 'to': 5, 'strength': 0.7},
                {'from': 5, 'to': 2, 'strength': 0.8},
                {'from': 2, 'to': 3, 'strength': 0.6},
                {'from': 3, 'to': 4, 'strength': 0.5},
                {'from': 4, 'to': 1, 'strength': 0.9}
            ]
        else:
            # Стандартная петля
            self.model.elements[1].causes = [2]
            self.model.elements[2].causes = [3]
            self.model.elements[3].causes = [4]
            self.model.elements[4].causes = [1]
            
            self.model.links = [
                {'from': 1, 'to': 2, 'strength': 0.7},
                {'from': 2, 'to': 3, 'strength': 0.7},
                {'from': 3, 'to': 4, 'strength': 0.7},
                {'from': 4, 'to': 1, 'strength': 0.7}
            ]
        
        logger.info(f"✅ Модель создана на основе паттернов: привязанность={attachment}")
    
    def analyze(self) -> List[Dict[str, Any]]:
        """
        Главный метод анализа - возвращает все значимые петли
        
        Returns:
            list: список найденных петель с характеристиками
        """
        if not self.model or not hasattr(self.model, 'elements'):
            logger.error("❌ Модель не инициализирована или не содержит elements")
            return []
        
        logger.info("Начинаю анализ петель...")
        self.significant_loops = []
        self._analysis_time = datetime.now()
        
        self._find_all_cycles()
        self._rank_loops_by_impact()
        self._describe_loops()
        self._filter_insignificant_loops()
        
        logger.info(f"Анализ завершен. Найдено {len(self.significant_loops)} петель")
        return self.significant_loops.copy()
    
    def _find_all_cycles(self):
        """Находит все циклы в графе"""
        # Начинаем с каждого элемента
        for start_id in list(self.model.elements.keys()):
            self._visited.clear()
            self._path.clear()
            self._dfs(start_id, 0)
    
    def _dfs(self, node_id: int, depth: int):
        """
        Поиск в глубину для нахождения циклов
        
        Args:
            node_id: текущий узел
            depth: глубина поиска
        """
        if node_id in self._path:
            # Нашли цикл
            cycle_start = self._path.index(node_id)
            cycle = self._path[cycle_start:] + [node_id]
            if len(cycle) >= 3:  # минимум 3 элемента
                self._add_unique_cycle(cycle)
            return
        
        if node_id in self._visited or node_id not in self.model.elements:
            return
        
        element = self.model.elements.get(node_id)
        if not element:
            return
        
        self._visited.add(node_id)
        self._path.append(node_id)
        
        if hasattr(element, 'causes') and element.causes:
            for next_id in element.causes:
                if next_id in self.model.elements:
                    self._dfs(next_id, depth + 1)
        
        self._path.pop()
    
    def _add_unique_cycle(self, cycle: List[int]):
        """
        Добавляет уникальный цикл в список
        
        Args:
            cycle: список ID элементов в цикле
        """
        cycle_set = set(cycle)
        for existing in self.significant_loops:
            if set(existing['cycle']) == cycle_set:
                # Проверяем, что это тот же цикл (а не подцикл)
                if len(existing['cycle']) == len(cycle):
                    return
        self.significant_loops.append({
            'cycle': cycle.copy(),
            'length': len(cycle),
            'raw_strength': self._calculate_raw_strength(cycle),
            'elements': [self.model.elements[eid] for eid in cycle if eid in self.model.elements]
        })
    
    def _calculate_raw_strength(self, cycle: List[int]) -> float:
        """
        Вычисляет сырую силу цикла
        
        Args:
            cycle: список ID элементов в цикле
            
        Returns:
            float: сила цикла от 0 до 1
        """
        if not cycle:
            return 0.0
        
        strength = 1.0
        n = len(cycle)
        
        for i in range(n):
            from_id = cycle[i]
            to_id = cycle[(i + 1) % n]  # замыкаем петлю
            
            # Ищем связь
            found = False
            for link in getattr(self.model, 'links', []):
                if link.get('from') == from_id and link.get('to') == to_id:
                    strength *= link.get('strength', 0.5)
                    found = True
                    break
            
            if not found:
                # Если связи нет, используем слабую связь по умолчанию
                strength *= 0.3
        
        return min(strength, 1.0)
    
    def _rank_loops_by_impact(self):
        """Ранжирует петли по силе и длине"""
        for loop in self.significant_loops:
            # Чем длиннее петля, тем она значимее (охватывает больше системы)
            # Но при этом слабее (много слабых связей)
            length_factor = loop['length'] / 9.0  # нормализуем
            strength = loop['raw_strength']
            
            # Итоговая значимость
            loop['impact'] = length_factor * strength
    
    def _describe_loops(self):
        """Добавляет человеко-читаемые описания петель"""
        for loop in self.significant_loops:
            elements = loop['cycle']
            
            # Определяем тип петли по составу элементов
            has_result = 1 in elements
            has_closing = 9 in elements
            has_identity = 5 in elements or 6 in elements
            has_behavior = any(e in elements for e in [2, 3, 4])
            
            if has_result and has_closing and has_behavior:
                loop['type'] = self.LOOP_TYPE_MASTER
            elif has_identity and has_result:
                loop['type'] = self.LOOP_TYPE_IDENTITY
            elif all(e in elements for e in [2, 3, 4]) or all(e in elements for e in [2, 4]):
                loop['type'] = self.LOOP_TYPE_BEHAVIORAL
            elif has_closing:
                loop['type'] = self.LOOP_TYPE_CLOSING
            else:
                loop['type'] = self.LOOP_TYPE_MINOR
            
            # Добавляем описание из констант
            type_info = self.LOOP_DESCRIPTIONS.get(loop['type'], self.LOOP_DESCRIPTIONS[self.LOOP_TYPE_MINOR])
            loop['description'] = type_info['description']
            loop['color'] = type_info['color']
            loop['type_name'] = type_info['name']
            loop['advice'] = type_info['advice']
    
    def _filter_insignificant_loops(self, threshold: float = 0.1):
        """
        Удаляет незначительные петли (с очень низким impact)
        
        Args:
            threshold: порог значимости
        """
        self.significant_loops = [l for l in self.significant_loops if l.get('impact', 0) >= threshold]
    
    def get_strongest_loop(self) -> Optional[Dict[str, Any]]:
        """Возвращает самую сильную петлю"""
        if not self.significant_loops:
            return None
        return max(self.significant_loops, key=lambda x: x.get('impact', 0))
    
    def get_weakest_loop(self) -> Optional[Dict[str, Any]]:
        """Возвращает самую слабую петлю"""
        if not self.significant_loops:
            return None
        return min(self.significant_loops, key=lambda x: x.get('impact', 0))
    
    def get_loops_by_type(self, loop_type: str) -> List[Dict[str, Any]]:
        """Возвращает петли определенного типа"""
        if not self.significant_loops:
            return []
        return [l for l in self.significant_loops if l.get('type') == loop_type]
    
    def get_loops_by_element(self, element_id: int) -> List[Dict[str, Any]]:
        """Возвращает все петли, содержащие указанный элемент"""
        if not self.significant_loops:
            return []
        return [l for l in self.significant_loops if element_id in l.get('cycle', [])]
    
    def get_key_element(self, loop: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Определяет ключевой (центральный) элемент петли
        
        Returns:
            элемент с наибольшим количеством входящих/исходящих связей
        """
        elements = loop.get('cycle', [])
        if not elements:
            return None
        
        # Считаем степень узла (входящие + исходящие связи внутри петли)
        degrees = {elem_id: 0 for elem_id in elements}
        n = len(elements)
        
        for i in range(n):
            from_id = elements[i]
            to_id = elements[(i + 1) % n]
            degrees[from_id] += 1
            degrees[to_id] += 1
        
        # Находим элемент с максимальной степенью
        max_degree = max(degrees.values()) if degrees else 0
        for elem_id, degree in degrees.items():
            if degree == max_degree:
                elem = self.model.elements.get(elem_id)
                if elem:
                    return {
                        'element_id': elem_id,
                        'element': elem,
                        'element_name': getattr(elem, 'name', f'Элемент {elem_id}'),
                        'degree': degree,
                        'is_center': degree >= 2
                    }
        
        return None
    
    def visualize_loop(self, loop: Dict[str, Any]) -> str:
        """
        Возвращает текстовое представление петли для отображения
        
        Returns:
            str: ASCII-схема петли
        """
        elements = loop.get('cycle', [])
        if not elements:
            return "Петля не содержит элементов"
        
        lines = []
        lines.append("┌" + "─" * 50 + "┐")
        lines.append("│ " + loop['description'] + " │")
        lines.append("└" + "─" * 50 + "┘")
        lines.append("")
        
        # Цепочка элементов
        chain = []
        for elem_id in elements:
            elem = self.model.elements.get(elem_id)
            name = getattr(elem, 'name', f'Элемент {elem_id}')[:20]
            chain.append(name)
        
        lines.append("🔄 " + " → ".join(chain) + " →")
        lines.append("")
        
        # Сила петли
        impact = loop.get('impact', 0)
        bar = "█" * int(impact * 10) + "░" * (10 - int(impact * 10))
        lines.append(f"📊 Сила: {bar} {impact:.0%}")
        
        # Точки разрыва
        points = self.get_intervention_points(loop)
        if points:
            lines.append("")
            lines.append("🎯 Точки разрыва:")
            for p in points[:3]:
                difficulty_star = "⭐" * int(3 - p['difficulty'] * 2) + "☆" * int(p['difficulty'] * 2)
                lines.append(f"   • {p['element_name']}: {difficulty_star} (потенциал {p['impact']:.0%})")
        
        return "\n".join(lines)
    
    def get_intervention_points(self, loop: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Определяет точки разрыва петли"""
        elements = loop.get('cycle', [])
        intervention_points = []
        
        for elem_id in elements:
            elem = self.model.elements.get(elem_id)
            if not elem:
                continue
            
            changeability = self._calculate_changeability(elem)
            
            intervention_points.append({
                'element_id': elem_id,
                'element': elem,
                'element_name': getattr(elem, 'name', f'Элемент {elem_id}'),
                'element_type': getattr(elem, 'element_type', 'unknown'),
                'impact': getattr(elem, 'strength', 0.5) * changeability,
                'difficulty': 1 - changeability,
                'changeability': changeability,
                'description': getattr(elem, 'description', '')[:100]
            })
        
        return sorted(intervention_points, key=lambda x: x['impact'], reverse=True)
    
    def _calculate_changeability(self, element) -> float:
        """Вычисляет, насколько легко изменить элемент"""
        elem_type = getattr(element, 'element_type', '')
        
        if elem_type in ['common_cause', 'closing', 'upper_cause']:
            return 0.3
        elif elem_type == 'immediate_cause':
            return 0.7
        elif elem_type == 'result':
            return 0.5
        return 0.4
    
    def get_best_intervention_point(self, loop: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Возвращает лучшую точку для вмешательства"""
        points = self.get_intervention_points(loop)
        return points[0] if points else None
    
    def get_break_points_summary(self) -> str:
        """Возвращает краткое резюме по точкам разрыва"""
        strongest = self.get_strongest_loop()
        if not strongest:
            return "✨ В вашей системе не обнаружено рекурсивных петель. Это хороший признак!"
        
        points = self.get_intervention_points(strongest)
        if not points:
            return "⚡ Петля обнаружена, но точки вмешательства не определены."
        
        best = points[0]
        
        if best['difficulty'] < 0.3:
            difficulty_text = "🔵 Легко изменить"
        elif best['difficulty'] < 0.6:
            difficulty_text = "🟡 Средняя сложность"
        else:
            difficulty_text = "🔴 Сложно изменить"
        
        return (f"🎯 *Лучшая точка вмешательства*\n\n"
                f"📝 *{best['element_name']}*\n"
                f"{best['description']}\n\n"
                f"📊 Потенциал: {best['impact']:.0%}\n"
                f"{difficulty_text}\n\n"
                f"💡 *Совет:* {strongest.get('advice', 'Начните с этого элемента.')}")
    
    def get_loop_description_for_user(self, loop: Dict[str, Any]) -> str:
        """Возвращает понятное пользователю описание петли"""
        elements = []
        for elem_id in loop['cycle']:
            elem = self.model.elements.get(elem_id)
            if elem:
                elements.append(getattr(elem, 'name', f'Элемент {elem_id}'))
        
        elements_str = " → ".join(elements)
        
        impact = loop.get('impact', 0)
        if impact > 0.7:
            strength_word = "⚡ Очень сильная"
        elif impact > 0.4:
            strength_word = "📈 Средняя"
        elif impact > 0.2:
            strength_word = "📉 Слабая"
        else:
            strength_word = "🍃 Едва заметная"
        
        return (f"{loop['description']}\n\n"
                f"{strength_word} (точность {impact:.0%})\n"
                f"🔄 *Цепочка:* {elements_str}")
    
    def get_all_loops_summary(self) -> str:
        """Возвращает сводку по всем петлям"""
        if not self.significant_loops:
            return "✅ Рекурсивных петель не обнаружено."
        
        lines = ["🔄 *ОБНАРУЖЕННЫЕ ПЕТЛИ*\n"]
        
        for i, loop in enumerate(self.significant_loops[:5], 1):
            impact = loop.get('impact', 0)
            bar = "█" * int(impact * 10) + "░" * (10 - int(impact * 10))
            
            lines.append(f"{i}. {loop['description']}")
            lines.append(f"   {bar} {impact:.0%}")
        
        if len(self.significant_loops) > 5:
            lines.append(f"\n...и еще {len(self.significant_loops) - 5} петель")
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по анализу"""
        return {
            'total_loops': len(self.significant_loops),
            'strongest_impact': self.get_strongest_loop().get('impact', 0) if self.significant_loops else 0,
            'loops_by_type': {
                loop_type: len(self.get_loops_by_type(loop_type))
                for loop_type in self.LOOP_DESCRIPTIONS.keys()
            },
            'analysis_time': self._analysis_time.isoformat() if self._analysis_time else None
        }
    
    def clear(self):
        """Очищает результаты анализа"""
        self.significant_loops = []
        self._visited.clear()
        self._path.clear()
        self._analysis_time = None
        logger.info("Результаты анализа очищены")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def create_analyzer_from_model_data(model_data: Dict, user_id: int = None) -> Optional[LoopAnalyzer]:
    """Создает анализатор из сохраненных данных модели"""
    try:
        from confinement_model import ConfinementModel9
        model = ConfinementModel9.from_dict(model_data)
        if user_id:
            model.user_id = user_id
        return LoopAnalyzer(model)
    except Exception as e:
        logger.error(f"Ошибка при создании анализатора: {e}")
        return None


def format_loop_for_display(loop: Dict[str, Any], detailed: bool = False) -> str:
    """Форматирует петлю для отображения"""
    if detailed:
        elements = loop.get('elements', [])
        elements_text = ""
        for i, elem in enumerate(elements):
            arrow = " → " if i < len(elements) - 1 else ""
            elements_text += f"{getattr(elem, 'name', '?')}{arrow}"
        
        return (f"**{loop['description']}**\n\n"
                f"📊 Сила: {loop['impact']:.0%}\n"
                f"🔄 Цепочка: {elements_text}\n\n"
                f"💡 {loop.get('advice', '')}")
    else:
        return f"{loop['description']} (сила {loop['impact']:.0%})"
