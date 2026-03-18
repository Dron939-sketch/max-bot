#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 2: АНАЛИЗ ПЕТЕЛЬ (loop_analyzer.py)
Анализирует рекурсивные петли в конфайнмент-модели
ВЕРСИЯ 2.0 - ДОБАВЛЕНО СОХРАНЕНИЕ РЕЗУЛЬТАТОВ В БД
"""

from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import datetime
import logging
import json
import asyncio

from confinement_model import ConfinementModel9, ConfinementElement

# ✅ ДОБАВЛЕНО: импорт для БД
from db_instance import db

# Настройка логирования
logger = logging.getLogger(__name__)


class LoopAnalyzer:
    """
    Анализирует рекурсивные петли в конфайнмент-модели
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
    
    def __init__(self, model: ConfinementModel9):
        """
        Инициализация анализатора
        
        Args:
            model: построенная конфайнмент-модель
        """
        self.model = model
        self.significant_loops: List[Dict[str, Any]] = []
        self._visited: Set[int] = set()
        self._path: List[int] = []
        self._analysis_time: Optional[datetime] = None
        
        logger.info(f"LoopAnalyzer инициализирован для модели пользователя {model.user_id}")
    
    # ============================================
    # ✅ ДОБАВЛЕНО: ФУНКЦИИ ДЛЯ РАБОТЫ С БД
    # ============================================
    
    async def save_analysis_results(self, user_id: int):
        """Сохраняет результаты анализа в БД"""
        try:
            # Сохраняем как событие
            await db.log_event(
                user_id,
                'loop_analysis_completed',
                {
                    'total_loops': len(self.significant_loops),
                    'strongest_impact': self.get_strongest_loop().get('impact', 0) if self.significant_loops else 0,
                    'loop_types': self._get_loop_types_summary(),
                    'analysis_time': self._analysis_time.isoformat() if self._analysis_time else None
                }
            )
            
            # Сохраняем детальную информацию о каждой петле
            for i, loop in enumerate(self.significant_loops):
                await self._save_loop_details(user_id, loop, i)
            
            logger.info(f"💾 Результаты анализа сохранены в БД для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения результатов анализа для {user_id}: {e}")
    
    async def _save_loop_details(self, user_id: int, loop: Dict[str, Any], index: int):
        """Сохраняет детали конкретной петли"""
        try:
            # Получаем названия элементов в петле
            element_names = []
            for elem_id in loop.get('cycle', []):
                elem = self.model.elements.get(elem_id)
                if elem:
                    element_names.append(elem.name)
            
            # Получаем точки вмешательства
            intervention_points = self.get_intervention_points(loop)
            
            await db.log_event(
                user_id,
                'loop_detail',
                {
                    'loop_index': index,
                    'loop_type': loop.get('type'),
                    'loop_description': loop.get('description'),
                    'impact': loop.get('impact', 0),
                    'cycle': loop.get('cycle', []),
                    'element_names': element_names,
                    'length': loop.get('length', 0),
                    'best_intervention': intervention_points[0] if intervention_points else None,
                    'intervention_points_count': len(intervention_points)
                }
            )
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения деталей петли: {e}")
    
    def _get_loop_types_summary(self) -> Dict[str, int]:
        """Возвращает сводку по типам петель"""
        summary = {}
        for loop_type in self.LOOP_DESCRIPTIONS.keys():
            count = len(self.get_loops_by_type(loop_type))
            if count > 0:
                summary[loop_type] = count
        return summary
    
    async def get_saved_analysis(self, user_id: int, limit: int = 1) -> List[Dict]:
        """Получает сохраненные результаты анализа из БД"""
        try:
            async with db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT event_data, created_at
                    FROM fredi_events
                    WHERE user_id = $1 AND event_type = 'loop_analysis_completed'
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
                
                results = []
                for row in rows:
                    data = row['event_data']
                    if isinstance(data, str):
                        data = json.loads(data)
                    results.append({
                        'data': data,
                        'time': row['created_at']
                    })
                return results
        except Exception as e:
            logger.error(f"❌ Ошибка получения сохраненных анализов для {user_id}: {e}")
            return []
    
    # ============================================
    # ОСНОВНЫЕ МЕТОДЫ АНАЛИЗА
    # ============================================
    
    def analyze(self) -> List[Dict[str, Any]]:
        """
        Главный метод анализа - возвращает все значимые петли
        
        Returns:
            list: список найденных петель с характеристиками
        """
        logger.info("Начинаю анализ петель...")
        self.significant_loops = []
        self._analysis_time = datetime.now()
        
        self._find_all_cycles()
        self._rank_loops_by_impact()
        self._describe_loops()
        self._filter_insignificant_loops()
        
        # ✅ Асинхронно сохраняем результаты, если есть user_id
        if hasattr(self.model, 'user_id') and self.model.user_id:
            asyncio.create_task(self.save_analysis_results(self.model.user_id))
        
        logger.info(f"Анализ завершен. Найдено {len(self.significant_loops)} петель")
        return self.significant_loops.copy()
    
    def _find_all_cycles(self):
        """Находит все циклы в графе"""
        # Начинаем с каждого элемента
        for start_id in range(1, 10):
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
        
        if element.causes:
            for next_id in element.causes:
                if next_id in self.model.elements:  # проверяем, что элемент существует
                    self._dfs(next_id, depth + 1)
        
        self._path.pop()
    
    def _add_unique_cycle(self, cycle: List[int]):
        """
        Добавляет уникальный цикл в список
        
        Args:
            cycle: список ID элементов в цикле
        """
        # Проверяем, что цикл уникальный
        cycle_set = set(cycle)
        for existing in self.significant_loops:
            if set(existing['cycle']) == cycle_set:
                return  # цикл уже есть
        
        self.significant_loops.append({
            'cycle': cycle.copy(),
            'length': len(cycle),
            'raw_strength': self._calculate_raw_strength(cycle),
            'elements': [self.model.elements[eid] for eid in cycle if self.model.elements.get(eid)]
        })
    
    def _calculate_raw_strength(self, cycle: List[int]) -> float:
        """
        Вычисляет сырую силу цикла
        
        Args:
            cycle: список ID элементов в цикле
            
        Returns:
            float: сила цикла от 0 до 1
        """
        strength = 1.0
        
        for i in range(len(cycle)-1):
            from_id = cycle[i]
            to_id = cycle[i+1]
            
            # Ищем связь
            found = False
            for link in self.model.links:
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
        """
        Возвращает самую сильную петлю
        
        Returns:
            dict: информация о самой сильной петле или None
        """
        if not self.significant_loops:
            return None
        
        return max(self.significant_loops, key=lambda x: x.get('impact', 0))
    
    def get_weakest_loop(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает самую слабую петлю
        
        Returns:
            dict: информация о самой слабой петле или None
        """
        if not self.significant_loops:
            return None
        
        return min(self.significant_loops, key=lambda x: x.get('impact', 0))
    
    def get_loops_by_type(self, loop_type: str) -> List[Dict[str, Any]]:
        """
        Возвращает петли определенного типа
        
        Args:
            loop_type: тип петли (из констант LOOP_TYPE_*)
            
        Returns:
            list: список петель указанного типа
        """
        return [l for l in self.significant_loops if l.get('type') == loop_type]
    
    def get_loops_by_element(self, element_id: int) -> List[Dict[str, Any]]:
        """
        Возвращает все петли, содержащие указанный элемент
        
        Args:
            element_id: ID элемента (1-9)
            
        Returns:
            list: список петель с этим элементом
        """
        return [l for l in self.significant_loops if element_id in l.get('cycle', [])]
    
    def get_intervention_points(self, loop: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Определяет точки разрыва петли (элементы, где можно вмешаться)
        
        Args:
            loop: информация о петле
            
        Returns:
            list: точки вмешательства, отсортированные по эффективности
        """
        elements = loop.get('cycle', [])
        
        # Точки разрыва - элементы с наибольшим влиянием
        intervention_points = []
        
        for elem_id in elements:
            elem = self.model.elements.get(elem_id)
            if not elem:
                continue
            
            # Оцениваем, насколько легко изменить этот элемент
            changeability = self._calculate_changeability(elem)
            
            intervention_points.append({
                'element_id': elem_id,
                'element': elem,
                'element_name': elem.name,
                'element_type': elem.element_type,
                'impact': elem.strength * changeability,
                'difficulty': 1 - changeability,
                'changeability': changeability,
                'description': elem.description[:100]
            })
        
        return sorted(intervention_points, key=lambda x: x['impact'], reverse=True)
    
    def _calculate_changeability(self, element: ConfinementElement) -> float:
        """
        Вычисляет, насколько легко изменить элемент
        
        Args:
            element: элемент модели
            
        Returns:
            float: коэффициент изменяемости (0-1)
        """
        # Убеждения менять сложнее всего
        if element.element_type in [self.model.TYPE_COMMON_CAUSE, 
                                    self.model.TYPE_CLOSING,
                                    self.model.TYPE_UPPER_CAUSE]:
            return 0.3
        # Поведение менять проще
        elif element.element_type == self.model.TYPE_IMMEDIATE_CAUSE:
            return 0.7
        # Симптомы можно облегчить
        elif element.element_type == self.model.TYPE_RESULT:
            return 0.5
        # По умолчанию
        return 0.4
    
    def get_best_intervention_point(self, loop: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Возвращает лучшую точку для вмешательства
        
        Args:
            loop: информация о петле
            
        Returns:
            dict: лучшая точка вмешательства или None
        """
        points = self.get_intervention_points(loop)
        return points[0] if points else None
    
    def get_break_points_summary(self) -> str:
        """
        Возвращает краткое резюме по точкам разрыва для пользователя
        
        Returns:
            str: понятное пользователю резюме
        """
        strongest = self.get_strongest_loop()
        if not strongest:
            return "✨ В вашей системе не обнаружено рекурсивных петель. Это хороший признак!"
        
        points = self.get_intervention_points(strongest)
        if not points:
            return "⚡ Петля обнаружена, но точки вмешательства не определены."
        
        best = points[0]
        elem = best['element']
        
        # Определяем эмодзи для типа элемента
        type_emoji = {
            self.model.TYPE_RESULT: "🎯",
            self.model.TYPE_IMMEDIATE_CAUSE: "⚡",
            self.model.TYPE_COMMON_CAUSE: "💭",
            self.model.TYPE_UPPER_CAUSE: "🏛",
            self.model.TYPE_CLOSING: "🌍"
        }.get(elem.element_type, "🔹")
        
        # Определяем рекомендацию
        if best['difficulty'] < 0.3:
            difficulty_text = "🔵 Легко изменить"
        elif best['difficulty'] < 0.6:
            difficulty_text = "🟡 Средняя сложность"
        else:
            difficulty_text = "🔴 Сложно изменить"
        
        return (f"🎯 *Лучшая точка вмешательства*\n\n"
                f"{type_emoji} *{elem.name}*\n"
                f"📝 {elem.description[:100]}...\n\n"
                f"📊 Потенциал: {best['impact']:.0%}\n"
                f"{difficulty_text}\n\n"
                f"💡 *Совет:* {strongest.get('advice', 'Начните с этого элемента.')}")
    
    def get_loop_description_for_user(self, loop: Dict[str, Any]) -> str:
        """
        Возвращает понятное пользователю описание петли
        
        Args:
            loop: информация о петле
            
        Returns:
            str: понятное описание
        """
        elements = []
        for elem_id in loop['cycle']:
            elem = self.model.elements.get(elem_id)
            if elem:
                elements.append(elem.name)
        
        elements_str = " → ".join(elements)
        
        # Определяем силу словами
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
        """
        Возвращает сводку по всем петлям
        
        Returns:
            str: сводка для пользователя
        """
        if not self.significant_loops:
            return "✅ Рекурсивных петель не обнаружено."
        
        lines = ["🔄 *ОБНАРУЖЕННЫЕ ПЕТЛИ*\n"]
        
        for i, loop in enumerate(self.significant_loops[:5], 1):  # максимум 5 петель
            impact = loop.get('impact', 0)
            bar = "█" * int(impact * 10) + "░" * (10 - int(impact * 10))
            
            lines.append(f"{i}. {loop['description']}")
            lines.append(f"   {bar} {impact:.0%}")
        
        if len(self.significant_loops) > 5:
            lines.append(f"\n...и еще {len(self.significant_loops) - 5} петель")
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику по анализу
        
        Returns:
            dict: статистика
        """
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
    """
    Создает анализатор из сохраненных данных модели
    
    Args:
        model_data: словарь с данными модели
        user_id: ID пользователя
        
    Returns:
        LoopAnalyzer или None
    """
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
    """
    Форматирует петлю для отображения
    
    Args:
        loop: информация о петле
        detailed: детальный или краткий формат
        
    Returns:
        str: отформатированный текст
    """
    if detailed:
        elements = loop.get('elements', [])
        elements_text = ""
        for i, elem in enumerate(elements):
            arrow = " → " if i < len(elements) - 1 else ""
            elements_text += f"{elem.name}{arrow}"
        
        return (f"**{loop['description']}**\n\n"
                f"📊 Сила: {loop['impact']:.0%}\n"
                f"🔄 Цепочка: {elements_text}\n\n"
                f"💡 {loop.get('advice', '')}")
    else:
        return f"{loop['description']} (сила {loop['impact']:.0%})"


async def get_user_loop_analysis_history(user_id: int, limit: int = 5) -> List[Dict]:
    """
    Получает историю анализов петель пользователя из БД
    
    Args:
        user_id: ID пользователя
        limit: максимальное количество записей
        
    Returns:
        list: история анализов
    """
    try:
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT event_data, created_at
                FROM fredi_events
                WHERE user_id = $1 AND event_type = 'loop_analysis_completed'
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            history = []
            for row in rows:
                data = row['event_data']
                if isinstance(data, str):
                    data = json.loads(data)
                history.append({
                    'data': data,
                    'time': row['created_at']
                })
            return history
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории анализов для {user_id}: {e}")
        return []


# ============================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ (для тестирования)
# ============================================

if __name__ == "__main__":
    print("🧪 Тестирование LoopAnalyzer...")
    
    # Создаем тестовую модель
    from confinement_model import ConfinementModel9, ConfinementElement
    
    test_model = ConfinementModel9(user_id=12345)
    
    # Заполняем тестовыми данными
    for i in range(1, 10):
        test_model.elements[i] = ConfinementElement(i, f"Элемент {i}")
        test_model.elements[i].description = f"Описание элемента {i}"
        test_model.elements[i].strength = 0.5 + (i * 0.05)
    
    # Создаем тестовые связи для петли
    test_model.elements[1].causes = [2]
    test_model.elements[2].causes = [6]
    test_model.elements[6].causes = [9]
    test_model.elements[9].causes = [1]
    
    test_model.links = [
        {'from': 1, 'to': 2, 'strength': 0.8},
        {'from': 2, 'to': 6, 'strength': 0.7},
        {'from': 6, 'to': 9, 'strength': 0.6},
        {'from': 9, 'to': 1, 'strength': 0.9}
    ]
    
    # Анализируем
    analyzer = LoopAnalyzer(test_model)
    loops = analyzer.analyze()
    
    print(f"\n📊 Найдено петель: {len(loops)}")
    
    if loops:
        print("\n🔍 Самая сильная петля:")
        strongest = analyzer.get_strongest_loop()
        print(analyzer.get_loop_description_for_user(strongest))
        
        print("\n🎯 Лучшая точка вмешательства:")
        print(analyzer.get_break_points_summary())
    
    print("\n✅ Тест завершен")


# ============================================
# ЭКСПОРТ
# ============================================

__all__ = [
    'LoopAnalyzer',
    'create_analyzer_from_model_data',
    'format_loop_for_display',
    'get_user_loop_analysis_history'
]
