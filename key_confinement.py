# key_confinement.py
from typing import Dict, List, Optional, Any
from confinement_model import ConfinementModel9, ConfinementElement


class KeyConfinementDetector:
    """
    Детектор ключевого конфайнмента (главного ограничения)
    """
    
    def __init__(self, model: ConfinementModel9, loops: List[Dict[str, Any]]):
        self.model = model
        self.loops = loops
    
    def detect(self) -> Optional[Dict[str, Any]]:
        """
        Определяет ключевой конфайнмент
        """
        # Метод 1: По центральности в графе
        centrality_scores = self._calculate_centrality()
        
        # Метод 2: По участию в петлях
        loop_participation = self._calculate_loop_participation()
        
        # Метод 3: По силе элемента
        strength_scores = {eid: elem.strength 
                          for eid, elem in self.model.elements.items() 
                          if elem}
        
        # Метод 4: По типу элемента (замыкающие важнее)
        type_importance = self._calculate_type_importance()
        
        # Комбинируем с весами
        final_scores = {}
        for eid in range(1, 10):
            if not self.model.elements.get(eid):
                continue
            
            final_scores[eid] = (
                centrality_scores.get(eid, 0) * 0.3 +
                loop_participation.get(eid, 0) * 0.4 +
                strength_scores.get(eid, 0) * 0.2 +
                type_importance.get(eid, 0) * 0.1
            )
        
        # Находим максимум
        if not final_scores:
            return None
        
        best_eid = max(final_scores, key=final_scores.get)
        best_element = self.model.elements[best_eid]
        
        return {
            'element_id': best_eid,
            'element': best_element,
            'score': final_scores[best_eid],
            'description': self._generate_description(best_element),
            'intervention': self._suggest_intervention(best_element)
        }
    
    def _calculate_centrality(self) -> Dict[int, float]:
        """
        Вычисляет центральность элементов (насколько они важны в графе)
        """
        centrality = {}
        
        for eid in range(1, 10):
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            # Считаем количество входящих и исходящих связей
            in_degree = len(element.caused_by)
            out_degree = len(element.causes)
            
            # Центральность по степени (макс связей ~16)
            max_links = 16
            centrality[eid] = (in_degree + out_degree) / max_links
        
        return centrality
    
    def _calculate_loop_participation(self) -> Dict[int, float]:
        """
        Вычисляет, насколько часто элемент участвует в петлях
        """
        participation = {eid: 0 for eid in range(1, 10)}
        
        for loop in self.loops:
            for eid in loop.get('cycle', []):
                if eid in participation:
                    participation[eid] += 1
        
        # Нормализуем
        max_participation = max(participation.values()) if participation else 1
        if max_participation > 0:
            participation = {k: v / max_participation for k, v in participation.items()}
        
        return participation
    
    def _calculate_type_importance(self) -> Dict[int, float]:
        """
        Вычисляет важность на основе типа элемента
        """
        importance = {}
        
        type_weights = {
            self.model.TYPE_CLOSING: 1.0,
            self.model.TYPE_COMMON_CAUSE: 0.9,
            self.model.TYPE_UPPER_CAUSE: 0.8,
            self.model.TYPE_IMMEDIATE_CAUSE: 0.6,
            self.model.TYPE_RESULT: 0.5
        }
        
        for eid in range(1, 10):
            element = self.model.elements.get(eid)
            if not element:
                continue
            
            importance[eid] = type_weights.get(element.element_type, 0.5)
        
        return importance
    
    def _generate_description(self, element: ConfinementElement) -> str:
        """
        Генерирует описание ключевого конфайнмента
        """
        base = f"**{element.name}** — вот что держит всю систему."
        
        # Берем первую часть описания элемента
        short_desc = element.description[:50] if element.description else "..."
        
        details = {
            1: f"Симптом {short_desc} возвращается снова и снова, потому что вся система его воспроизводит.",
            2: f"Твое поведение ({short_desc}) запускает цепную реакцию, которая возвращается к нему же.",
            3: f"Стратегия {element.name} кажется единственно возможной, но она же и ловушка.",
            4: f"Паттерн {element.name} незаметен, но именно через него все замыкается.",
            5: f"Убеждение «{short_desc}» — это линза, через которую ты видишь всё.",
            6: f"Система {element.name} создает правила, по которым ты играешь, даже не замечая.",
            7: f"Глубинное убеждение «{short_desc}» — это корень, из которого всё растет.",
            8: f"Связка {element.name} соединяет то, что кажется несовместимым, удерживая противоречия.",
            9: f"Картина мира «{short_desc}» — именно она не дает системе измениться."
        }
        
        return base + " " + details.get(element.id, "Это ключевая точка системы.")
    
    def _suggest_intervention(self, element: ConfinementElement) -> Dict[str, str]:
        """
        Предлагает интервенцию для работы с конфайнментом
        """
        # Библиотека интервенций по типам элементов
        interventions = {
            self.model.TYPE_RESULT: {
                'approach': 'Работа с симптомом напрямую',
                'method': 'Отслеживание и дневник симптомов',
                'exercise': 'Каждый день записывай, когда симптом проявляется и что ему предшествует',
                'vak': 'kinesthetic',
                'duration': '21 день',
                'difficulty': 'Средняя'
            },
            self.model.TYPE_IMMEDIATE_CAUSE: {
                'approach': 'Изменение поведения',
                'method': 'Замена автоматической реакции на осознанную',
                'exercise': 'Вместо привычного действия сделай паузу и выбери другое',
                'vak': 'kinesthetic',
                'duration': '30 дней',
                'difficulty': 'Средняя'
            },
            self.model.TYPE_COMMON_CAUSE: {
                'approach': 'Работа с убеждениями',
                'method': 'Поиск исключений и альтернатив',
                'exercise': 'Найди одно исключение из правила и исследуй его',
                'vak': 'auditory_digital',
                'duration': '14 дней',
                'difficulty': 'Высокая'
            },
            self.model.TYPE_UPPER_CAUSE: {
                'approach': 'Изменение контекста',
                'method': 'Работа с системой и средой',
                'exercise': 'Измени одно условие в своей среде на этой неделе',
                'vak': 'auditory',
                'duration': '7 дней',
                'difficulty': 'Средняя'
            },
            self.model.TYPE_CLOSING: {
                'approach': 'Трансформация картины мира',
                'method': 'Переосмысление фундаментальных убеждений',
                'exercise': 'Представь, что мир устроен иначе. Что бы ты делал по-другому?',
                'vak': 'visual',
                'duration': '30 дней',
                'difficulty': 'Очень высокая'
            }
        }
        
        intervention = interventions.get(element.element_type, 
                                        interventions[self.model.TYPE_COMMON_CAUSE])
        
        # Персонализируем под элемент
        intervention = intervention.copy()
        intervention['target'] = element.name
        intervention['element_id'] = element.id
        intervention['vector'] = element.vector
        intervention['level'] = element.level
        
        # Адаптируем описание под вектор
        if element.vector:
            vector_names = {'СБ': 'безопасность', 'ТФ': 'ресурсы', 
                           'УБ': 'удовольствие', 'ЧВ': 'чувства'}
            vector_word = vector_names.get(element.vector, '')
            if vector_word:
                intervention['personalized'] = f"Учитывая твой фокус на {vector_word}, обрати особое внимание на..."
        
        return intervention
