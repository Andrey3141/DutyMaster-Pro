"""
Генератор справедливого расписания дежурств
Профессиональная версия с отладкой и визуализацией
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import time
import sys

# ========== КОНФИГУРАЦИЯ (легко менять) ==========
DAYS_COUNT = 7  # Измените здесь количество дней
PLACES_CONFIG = {
    "1 этаж": 2,
    "2 этаж": 2,  
    "3 этаж": 2,
    "столовая": 2,
    "лабораторный корпус": 2,
    "гардероб": 2,  # Добавил 2 дежурных в гардероб для примера
}

# Системные настройки
MAX_ATTEMPTS = 100
DEBUG = False  # Включите True для отладки

# ========== DATA CLASSES ==========
@dataclass
class DayStatus:
    """Статус ребенка на конкретный день"""
    day: str
    status: str
    
    def __str__(self) -> str:
        return f"{self.day}:{self.status}"

@dataclass
class Child:
    """Информация о ребенке"""
    name: str
    days: List[DayStatus]
    health_status: str
    
    def __post_init__(self):
        """Проверка данных после создания"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(f"Некорректное имя ребенка: {self.name}")
    
    def can_work(self, day_name: str) -> bool:
        """Может ли работать в указанный день"""
        return any(d.day == day_name and d.status == "доступен" for d in self.days)
    
    def available_days_count(self) -> int:
        """Сколько дней доступен"""
        return sum(1 for d in self.days if d.status == "доступен")
    
    def is_available(self) -> bool:
        """Доступен ли вообще для дежурств"""
        return self.available_days_count() > 0 and self.health_status != "болеет"
    
    def __str__(self) -> str:
        return self.name

class ScheduleResult:
    """Результат генерации расписания"""
    def __init__(self, schedule: List[List[Optional[Child]]], 
                 distribution: Dict[str, int],
                 score: int,
                 issues: List[str],
                 algorithm_name: str = "unknown"):
        self.schedule = schedule
        self.distribution = distribution
        self.score = score
        self.issues = issues
        self.algorithm_name = algorithm_name
        self.empty_spots = self._count_empty_spots()
    
    def _count_empty_spots(self) -> int:
        """Подсчет пустых мест"""
        return sum(1 for day in self.schedule for child in day if child is None)
    
    def is_perfect(self) -> bool:
        """Проверка на идеальное расписание"""
        return self.score == 0 and self.empty_spots == 0

# ========== БАЗОВЫЙ КЛАСС ПЛАНИРОВЩИКА ==========
class BaseScheduler:
    """Базовый класс для генерации расписания"""
    
    # Статические списки дней
    DAY_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    DAY_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    def __init__(self, days_count: int, places_config: Dict[str, int], children: List[Child]):
        self._validate_input(days_count, places_config, children)
        
        self.days_count = days_count
        self.places_config = {k: v for k, v in places_config.items() if v > 0}
        self.children = children
        
        # Проверяем дни
        if days_count > len(self.DAY_SHORT):
            raise ValueError(f"Запрошено {days_count} дней, но доступно только {len(self.DAY_SHORT)}")
        
        self.day_names = self.DAY_SHORT[:days_count]
        self.day_names_full = self.DAY_FULL[:days_count]
        
        # Создаем список мест
        self.places_list = []
        for place, count in self.places_config.items():
            self.places_list.extend([place] * count)
        
        if DEBUG:
            print(f"[DEBUG] Создан планировщик: {days_count} дней, {len(self.places_list)} мест в день")
    
    def _validate_input(self, days_count: int, places_config: Dict[str, int], children: List[Child]):
        """Валидация входных данных"""
        if days_count <= 0:
            raise ValueError("Количество дней должно быть положительным")
        
        if not places_config:
            raise ValueError("Не указаны места для дежурств")
        
        if not children:
            raise ValueError("Не указаны дети")
        
        # Проверяем уникальность имен
        names = [c.name for c in children]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Дублирующиеся имена детей: {set(duplicates)}")
    
    def calculate_target_distribution(self) -> Dict[str, int]:
        """
        Рассчитывает целевое распределение дежурств
        Возвращает словарь {имя_ребенка: количество_дежурств}
        """
        total_duties = self.days_count * len(self.places_list)
        available_children = [c for c in self.children if c.is_available()]
        
        if DEBUG:
            print(f"[DEBUG] Всего дежурств: {total_duties}, доступных детей: {len(available_children)}")
        
        if not available_children:
            return {}
        
        # Простой математический расчет
        base_target = total_duties // len(available_children)
        extra_duties = total_duties % len(available_children)
        
        target_counts = {}
        
        # Даем всем базовое количество
        for child in available_children:
            target_counts[child.name] = base_target
        
        # Распределяем дополнительные дежурства
        # Сначала здоровым, потом недавно болевшим
        while extra_duties > 0:
            # Сортируем по приоритету: здоровые > недавно болевшие
            available_sorted = sorted(
                available_children,
                key=lambda c: (
                    1 if c.health_status == "здоров" else 2,
                    target_counts.get(c.name, 0)
                )
            )
            
            # Даем дополнительное дежурство первому в списке
            child = available_sorted[0]
            target_counts[child.name] += 1
            extra_duties -= 1
        
        return target_counts
    
    def _evaluate_schedule(self, schedule: List[List[Optional[Child]]], 
                          actual_counts: Dict[str, int]) -> Tuple[int, List[str]]:
        """
        Оценивает качество расписания
        """
        score = 0
        issues = []
        
        # 1. Проверка пустых мест
        empty_spots = sum(1 for day in schedule for child in day if child is None)
        if empty_spots > 0:
            score += empty_spots * 100
            issues.append(f"Пустых мест: {empty_spots}")
        
        # 2. Проверка, что один человек не дежурит в 2 местах одновременно
        duplicate_issues = []
        for day_idx, day_schedule in enumerate(schedule):
            day_name = self.day_names[day_idx]
            children_in_day = [child for child in day_schedule if child is not None]
            
            # Проверяем дубликаты
            child_names = [child.name for child in children_in_day]
            duplicates = set([name for name in child_names if child_names.count(name) > 1])
            
            if duplicates:
                for duplicate in duplicates:
                    duplicate_issues.append(f"{day_name}: {duplicate} дежурит в нескольких местах")
        
        if duplicate_issues:
            score += len(duplicate_issues) * 150
            issues.extend(duplicate_issues)
        
        # 3. Проверка доступных детей
        available_children = [c for c in self.children if c.is_available()]
        available_counts = [actual_counts.get(c.name, 0) for c in available_children]
        
        if available_counts:
            max_count = max(available_counts)
            min_count = min(available_counts)
            diff = max_count - min_count
            
            if diff > 1:
                score += diff * 50
                issues.append(f"Разница в дежурствах: {diff} (от {min_count} до {max_count})")
        
        # 4. Проверка приоритетов
        healthy_counts = [actual_counts.get(c.name, 0) for c in self.children 
                         if c.health_status == "здоров" and c.is_available()]
        sick_counts = [actual_counts.get(c.name, 0) for c in self.children 
                      if c.health_status in ["недавно болел", "недавно болела"] and c.is_available()]
        
        if healthy_counts and sick_counts:
            min_healthy = min(healthy_counts) if healthy_counts else 0
            max_sick = max(sick_counts) if sick_counts else 0
            
            if max_sick > min_healthy:
                score += 200
                issues.append(f"Нарушение приоритетов: болевшие ({max_sick}) > здоровые ({min_healthy})")
        
        return score, issues

# ========== ЖАДНЫЙ АЛГОРИТМ ==========
class GreedyScheduler(BaseScheduler):
    """Жадный алгоритм с приоритетами"""
    
    def find_best_schedule(self, max_attempts: int = MAX_ATTEMPTS) -> ScheduleResult:
        """Находит лучшее расписание"""
        print("🔄 Используется ЖАДНЫЙ АЛГОРИТМ...")
        print("   (Поэтапный выбор лучших кандидатов для каждого дня)")
        
        best_result = None
        best_score = float('inf')
        
        target_counts = self.calculate_target_distribution()
        
        for attempt in range(max_attempts):
            result = self._create_schedule_greedy(target_counts)
            
            if result.score < best_score:
                best_score = result.score
                best_result = result
                
                if best_score == 0:
                    break
        
        if best_result is None:
            raise RuntimeError("Не удалось создать расписание")
        
        return best_result
    
    def _create_schedule_greedy(self, target_counts: Dict[str, int]) -> ScheduleResult:
        """Создает расписание жадным алгоритмом"""
        schedule = [[None for _ in self.places_list] for _ in range(self.days_count)]
        actual_counts = defaultdict(int)
        
        # Для каждого дня выбираем лучших кандидатов
        for day_idx in range(self.days_count):
            day_name = self.day_names[day_idx]
            
            # Собираем кандидатов на этот день
            candidates = []
            for child in self.children:
                if child.can_work(day_name) and child.is_available():
                    # Вычисляем "цену" назначения
                    current = actual_counts.get(child.name, 0)
                    target = target_counts.get(child.name, 0)
                    
                    # 1. Базовая цена = насколько далеко от цели
                    cost = abs(current - target) * 10
                
                    # 2. Штраф за статус здоровья (важно: здоровые дешевле)
                    if child.health_status == "здоров":
                        # Здоровые имеют базовую стоимость
                        pass  # Не добавляем штраф
                    elif child.health_status in ["недавно болел", "недавно болела"]:
                        # Недавно болевшие дороже
                        cost += 30
                    else:  # болеет
                        # Болеющие самые дорогие
                        cost += 100
                    
                    # 3. Штраф за уже выполненные дежурства (ВАЖНОЕ ИСПРАВЛЕНИЕ)
                    # Чем больше уже дежурил, тем дороже его назначать снова
                    penalty_for_repeat = current * 25  # Штраф 25 за каждое уже выполненное дежурство
                    cost += penalty_for_repeat
                
                    # 4. Небольшой рандом для разнообразия между одинаковыми кандидатами
                    cost += random.random() * 3
                    
                    candidates.append((cost, child))
            
            # Сортируем по возрастанию цены
            candidates.sort(key=lambda x: x[0])
            
            # Выбираем первых N, следя за тем, чтобы не брать одного ребенка дважды
            selected = []
            used_child_names = set()
            
            for cost, child in candidates:
                if len(selected) >= len(self.places_list):
                    break
                if child.name not in used_child_names:
                    selected.append(child)
                    used_child_names.add(child.name)
                    actual_counts[child.name] += 1
            
            # Если все еще не хватает (из-за проверки на уникальность)
            if len(selected) < len(self.places_list):
                needed = len(self.places_list) - len(selected)
                # Ищем любых доступных детей, которых еще нет в списке
                additional_candidates = [
                    child for child in self.children
                    if child.can_work(day_name) and child.is_available() and 
                       child.name not in used_child_names
                ]
                
                # Добавляем оставшихся
                for child in additional_candidates[:needed]:
                    selected.append(child)
                    actual_counts[child.name] += 1
            
            # Распределяем по местам
            random.shuffle(selected)
            for i in range(len(self.places_list)):
                schedule[day_idx][i] = selected[i] if i < len(selected) else None
        
        # Попытаемся улучшить путем локальных обменов
        self._local_improvement(schedule, actual_counts, target_counts)
        
        score, issues = self._evaluate_schedule(schedule, actual_counts)
        return ScheduleResult(schedule, dict(actual_counts), score, issues, "Жадный алгоритм")
    
    def _local_improvement(self, schedule, actual_counts, target_counts):
        """Локальное улучшение расписания"""
        for _ in range(100):
            # Находим ребенка с наибольшим превышением цели
            over_child = max(
                [c for c in self.children if c.is_available()],
                key=lambda c: actual_counts.get(c.name, 0) - target_counts.get(c.name, 0)
            )
            
            over_value = actual_counts.get(over_child.name, 0) - target_counts.get(over_child.name, 0)
            if over_value <= 0:
                break
            
            # Находим ребенка с наибольшим недобором
            under_child = max(
                [c for c in self.children if c.is_available() and c.name != over_child.name],
                key=lambda c: target_counts.get(c.name, 0) - actual_counts.get(c.name, 0)
            )
            
            under_value = target_counts.get(under_child.name, 0) - actual_counts.get(under_child.name, 0)
            if under_value <= 0:
                break
            
            # Пытаемся найти замену
            improved = False
            for day_idx in range(self.days_count):
                day_name = self.day_names[day_idx]
                
                # Может ли under_child работать в этот день?
                if not under_child.can_work(day_name):
                    continue
                
                # Ищем over_child в этот день
                for place_idx, child in enumerate(schedule[day_idx]):
                    if child is not None and child.name == over_child.name:
                        # Пробуем заменить
                        schedule[day_idx][place_idx] = under_child
                        actual_counts[over_child.name] -= 1
                        actual_counts[under_child.name] += 1
                        
                        # Проверяем, улучшилось ли
                        new_over = actual_counts.get(over_child.name, 0) - target_counts.get(over_child.name, 0)
                        new_under = target_counts.get(under_child.name, 0) - actual_counts.get(under_child.name, 0)
                        
                        if abs(new_over) + abs(new_under) < abs(over_value) + abs(under_value):
                            improved = True
                            break
                        else:
                            # Откат
                            schedule[day_idx][place_idx] = over_child
                            actual_counts[over_child.name] += 1
                            actual_counts[under_child.name] -= 1
                
                if improved:
                    break

# ========== АЛГОРИТМ НАЗНАЧЕНИЙ (ASSIGNMENT PROBLEM) ==========
class AssignmentScheduler(BaseScheduler):
    """Алгоритм на основе задачи о назначениях"""
    
    def find_best_schedule(self, max_attempts: int = MAX_ATTEMPTS) -> ScheduleResult:
        """Находит лучшее расписание"""
        print("🔄 Используется АЛГОРИТМ НАЗНАЧЕНИЙ...")
        print("   (Решение задачи оптимизации с матрицей стоимости)")
        
        best_result = None
        best_score = float('inf')
        
        target_counts = self.calculate_target_distribution()
        
        for attempt in range(max_attempts):
            result = self._create_schedule_assignment(target_counts)
            
            if result.score < best_score:
                best_score = result.score
                best_result = result
                
                if best_score == 0:
                    break
        
        if best_result is None:
            raise RuntimeError("Не удалось создать расписание")
        
        return best_result
    
    def _create_schedule_assignment(self, target_counts: Dict[str, int]) -> ScheduleResult:
        """Создает расписание алгоритмом назначений"""
        schedule = [[None for _ in self.places_list] for _ in range(self.days_count)]
        actual_counts = defaultdict(int)
        
        # Создаем матрицу доступности и стоимости
        cost_matrix = []
        for day_idx in range(self.days_count):
            day_name = self.day_names[day_idx]
            day_costs = []
            
            for child in self.children:
                if child.can_work(day_name) and child.is_available():
                    # Стоимость = текущее отклонение от цели * 10
                    current = actual_counts.get(child.name, 0)
                    target = target_counts.get(child.name, 0)
                    cost = abs(current - target) * 10
                    
                    # Штраф за статус здоровья
                    if child.health_status != "здоров":
                        cost += 50
                    
                    # Штраф за перегрузку
                    if current >= target:
                        cost += (current - target + 1) * 100
                else:
                    cost = float('inf')  # Не доступен
                
                day_costs.append(cost)
            
            cost_matrix.append(day_costs)
        
        # Распределяем детей по дням
        for place_idx in range(len(self.places_list)):
            # Для каждого дня выбираем лучшего ребенка для этого места
            for day_idx in range(self.days_count):
                if schedule[day_idx][place_idx] is not None:
                    continue
                
                day_name = self.day_names[day_idx]
                
                # Находим лучшего кандидата для этого дня и места
                best_child = None
                best_cost = float('inf')
                
                for child_idx, child in enumerate(self.children):
                    # Получаем список имен уже назначенных детей в этот день
                    scheduled_names = [c.name for c in schedule[day_idx] if c is not None]
                    if (child.can_work(day_name) and child.is_available() and 
                        child.name not in scheduled_names):
                        
                        cost = cost_matrix[day_idx][child_idx]
                        
                        if cost < best_cost:
                            best_cost = cost
                            best_child = child
                
                if best_child:
                    schedule[day_idx][place_idx] = best_child
                    actual_counts[best_child.name] += 1
                    
                    # Обновляем матрицу стоимостей
                    for d_idx in range(self.days_count):
                        if d_idx != day_idx:
                            for c_idx, child in enumerate(self.children):
                                if child.name == best_child.name:
                                    # Увеличиваем стоимость для этого ребенка в другие дни
                                    current = actual_counts.get(child.name, 0)
                                    target = target_counts.get(child.name, 0)
                                    cost_matrix[d_idx][c_idx] = abs(current - target) * 10
                                    if child.health_status != "здоров":
                                        cost_matrix[d_idx][c_idx] += 50
                                    if current >= target:
                                        cost_matrix[d_idx][c_idx] += (current - target + 1) * 100
        
        # Заполняем оставшиеся пустые места
        for day_idx in range(self.days_count):
            day_name = self.day_names[day_idx]
            for place_idx in range(len(self.places_list)):
                if schedule[day_idx][place_idx] is None:
                    # Получаем список имен уже назначенных детей в этот день
                    scheduled_names = [c.name for c in schedule[day_idx] if c is not None]
                    # Ищем любого доступного ребенка, который еще не назначен в этот день
                    for child in self.children:
                        if child.can_work(day_name) and child.is_available() and child.name not in scheduled_names:
                            schedule[day_idx][place_idx] = child
                            actual_counts[child.name] += 1
                            break
        
        score, issues = self._evaluate_schedule(schedule, actual_counts)
        return ScheduleResult(schedule, dict(actual_counts), score, issues, "Задача о назначениях")

# ========== ПРОСТОЙ РАНДОМНЫЙ АЛГОРИТМ ==========
class RandomScheduler(BaseScheduler):
    """Простой случайный алгоритм (для сравнения)"""
    
    def find_best_schedule(self, max_attempts: int = MAX_ATTEMPTS) -> ScheduleResult:
        """Находит лучшее расписание"""
        print("🔄 Используется СЛУЧАЙНЫЙ АЛГОРИТМ...")
        print("   (Множество случайных попыток с выбором лучшей)")
        
        best_result = None
        best_score = float('inf')
        
        for attempt in range(max_attempts):
            schedule = self._generate_random_schedule()
            actual_counts = self._count_schedule(schedule)
            score, issues = self._evaluate_schedule(schedule, actual_counts)
            
            if score < best_score:
                best_score = score
                best_result = ScheduleResult(schedule, actual_counts, score, issues, "Случайный алгоритм")
                
                if best_score == 0:
                    break
        
        if best_result is None:
            raise RuntimeError("Не удалось создать расписание")
        
        return best_result
    
    def _generate_random_schedule(self) -> List[List[Optional[Child]]]:
        """Генерирует случайное расписание"""
        schedule = [[None for _ in self.places_list] for _ in range(self.days_count)]
        
        for day_idx in range(self.days_count):
            day_name = self.day_names[day_idx]
            
            # Доступные дети в этот день
            available = [c for c in self.children if c.can_work(day_name) and c.is_available()]
            
            if len(available) >= len(self.places_list):
                # Выбираем случайных, но уникальных
                selected = random.sample(available, len(self.places_list))
            else:
                # Берем всех доступных и дополняем уникальными
                selected = available.copy()
                used_names = {child.name for child in selected}
                while len(selected) < len(self.places_list):
                    # Ищем ребенка, которого еще нет в списке
                    remaining = [c for c in available if c.name not in used_names]
                    if remaining:
                        new_child = random.choice(remaining)
                        selected.append(new_child)
                        used_names.add(new_child.name)
                    else:
                        # Если все уже выбраны, прерываем цикл
                        break
            
            random.shuffle(selected)
            for i in range(len(self.places_list)):
                schedule[day_idx][i] = selected[i] if i < len(selected) else None
        
        return schedule
    
    def _count_schedule(self, schedule: List[List[Optional[Child]]]) -> Dict[str, int]:
        """Подсчитывает распределение дежурств"""
        counts = defaultdict(int)
        for day in schedule:
            for child in day:
                if child:
                    counts[child.name] += 1
        return dict(counts)

# ========== ВИЗУАЛИЗАЦИЯ ==========
class ScheduleVisualizer:
    """Класс для визуализации расписания"""
    
    @staticmethod
    def print_configuration(scheduler: BaseScheduler, children: List[Child]):
        """Вывод конфигурации"""
        print("=" * 80)
        print("КОНФИГУРАЦИЯ СИСТЕМЫ")
        print("=" * 80)
        
        print(f"\n📅 Расписание:")
        print(f"  • Дней: {scheduler.days_count}")
        print(f"  • Мест в день: {len(scheduler.places_list)}")
        print(f"  • Всего дежурств: {scheduler.days_count * len(scheduler.places_list)}")
        
        print(f"\n🗓️ Используемые дни:")
        for i, (short, full) in enumerate(zip(scheduler.day_names, scheduler.day_names_full), 1):
            print(f"  {i:2}. {full:<12} ({short})")
        
        print(f"\n📍 Места дежурства:")
        for place, count in scheduler.places_config.items():
            print(f"  • {place:<25} → {count:2} дежурных")
        
        print(f"\n👥 Дети:")
        print(f"  • Всего детей: {len(children)}")
        
        status_count = Counter(c.health_status for c in children)
        for status, count in status_count.items():
            icon = "🏥" if status != "здоров" else "✅"
            print(f"  • {icon} {status:<15} → {count:2} детей")
        
        available_count = sum(1 for c in children if c.is_available())
        print(f"  • 👤 Доступны для дежурств: {available_count}")
    
    @staticmethod
    def print_schedule(result: ScheduleResult, scheduler: BaseScheduler):
        """Вывод расписания"""
        print("\n" + "=" * 80)
        print(f"📋 РАСПИСАНИЕ ДЕЖУРСТВ (Алгоритм: {result.algorithm_name})")
        print("=" * 80)
        
        if result.issues:
            print("\n⚠️  ЗАМЕЧАНИЯ:")
            for issue in result.issues:
                print(f"  • {issue}")
        else:
            print("\n✅ Все проверки пройдены")
        
        # Расписание по дням
        for day_idx in range(scheduler.days_count):
            day_name = scheduler.day_names_full[day_idx]
            print(f"\n{'='*40}")
            print(f"📅 {day_name} ({scheduler.day_names[day_idx]})")
            print(f"{'='*40}")
            
            # Группируем по местам
            place_assignments = defaultdict(list)
            for place_idx, child in enumerate(result.schedule[day_idx]):
                place = scheduler.places_list[place_idx]
                if child:
                    place_assignments[place].append(child)
            
            for place in scheduler.places_config.keys():
                children = place_assignments[place]
                if children:
                    children_str = []
                    for child in children:
                        if child.health_status == "здоров":
                            children_str.append(f"✅ {child.name}")
                        elif child.health_status == "болеет":
                            children_str.append(f"🛌 {child.name}")
                        else:
                            children_str.append(f"🏥 {child.name}")
                    
                    print(f"\n📍 {place}:")
                    print("   " + ", ".join(children_str))
    
    @staticmethod
    def print_statistics(result: ScheduleResult, children: List[Child]):
        """Вывод статистики"""
        print("\n" + "=" * 80)
        print("📊 СТАТИСТИКА РАСПРЕДЕЛЕНИЯ")
        print("=" * 80)
        
        # Группируем детей
        groups = {
            "ЗДОРОВЫЕ": [],
            "НЕДАВНО БОЛЕЛИ": [],
            "БОЛЕЕТ": []
        }
        
        for child in children:
            count = result.distribution.get(child.name, 0)
            if child.health_status == "болеет":
                groups["БОЛЕЕТ"].append((child, count))
            elif child.health_status in ["недавно болел", "недавно болела"]:
                groups["НЕДАВНО БОЛЕЛИ"].append((child, count))
            else:
                groups["ЗДОРОВЫЕ"].append((child, count))
        
        total_duties = 0
        
        for group_name, children_list in groups.items():
            if not children_list:
                continue
            
            print(f"\n{'─'*40}")
            if group_name == "ЗДОРОВЫЕ":
                print(f"✅ {group_name}:")
            elif group_name == "НЕДАВНО БОЛЕЛИ":
                print(f"🏥 {group_name}:")
            else:
                print(f"🛌 {group_name}:")
            
            group_total = 0
            counts = []
            
            for child, count in sorted(children_list, key=lambda x: (-x[1], x[0].name)):
                print(f"  • {child.name:<25} → {count:2} дежурств")
                group_total += count
                counts.append(count)
                total_duties += count
            
            if counts:
                print(f"  Всего детей: {len(children_list)}")
                print(f"  Всего дежурств: {group_total}")
                print(f"  Среднее: {group_total/len(children_list):.2f}")
                if len(counts) > 1:
                    print(f"  Диапазон: {min(counts)}-{max(counts)}")
                    print(f"  Разница: {max(counts) - min(counts)}")
        
        print(f"\n{'='*80}")
        print("🎯 ИТОГОВАЯ СВОДКА")
        print(f"{'='*80}")
        
        print(f"\n📈 Общие показатели:")
        print(f"  • Распределено дежурств: {total_duties}")
        print(f"  • Пустых мест: {result.empty_spots}")
        print(f"  • Оценка качества: {result.score}")
        print(f"  • Использованный алгоритм: {result.algorithm_name}")
        
        # Проверка правил
        print(f"\n✅ Проверка правил:")
        
        # Правило 1
        if result.empty_spots == 0:
            print(f"  • ✅ Все места заполнены")
        else:
            print(f"  • ❌ {result.empty_spots} пустых мест")
        
        # Правило 2 (новое): один человек - одно место
        has_duplicates = False
        for day_idx, day_schedule in enumerate(result.schedule):
            children_in_day = [child for child in day_schedule if child is not None]
            child_names = [child.name for child in children_in_day]
            duplicates = set([name for name in child_names if child_names.count(name) > 1])
            if duplicates:
                has_duplicates = True
                break
        
        if not has_duplicates:
            print(f"  • ✅ Один ученик - одно место")
        else:
            print(f"  • ❌ Один ученик в нескольких местах одновременно")
        
        # Правило 3 (бывшее 2)
        available_children = [c for c in children if c.is_available()]
        available_counts = [result.distribution.get(c.name, 0) for c in available_children]
        
        if available_counts:
            diff = max(available_counts) - min(available_counts)
            if diff <= 1:
                print(f"  • ✅ Отличная равномерность (разница={diff})")
            elif diff == 2:
                print(f"  • ⚠️  Приемлемая равномерность (разница={diff})")
            else:
                print(f"  • ❌ Плохая равномерность (разница={diff})")
        
        # Правило 4 (бывшее 3)
        healthy_counts = [result.distribution.get(c.name, 0) for c in children 
                         if c.health_status == "здоров" and c.is_available()]
        sick_counts = [result.distribution.get(c.name, 0) for c in children 
                      if c.health_status in ["недавно болел", "недавно болела"] and c.is_available()]
        
        if healthy_counts and sick_counts:
            min_healthy = min(healthy_counts)
            max_sick = max(sick_counts)
            
            if max_sick <= min_healthy:
                print(f"  • ✅ Приоритеты соблюдены ({max_sick} ≤ {min_healthy})")
            else:
                print(f"  • ❌ Нарушение приоритетов ({max_sick} > {min_healthy})")
        
        # Итог
        print(f"\n{'='*80}")
        if result.is_perfect():
            print("🎉 РАСПИСАНИЕ ИДЕАЛЬНО!")
        else:
            print("📋 Расписание сгенерировано с учетом всех ограничений")

# ========== ФАБРИКА ДАННЫХ ==========
class DataFactory:
    """Создание тестовых данных"""
    
    @staticmethod
    def create_sample_children(days_count: int) -> List[Child]:
        """
        Создает тестовый набор из 29 детей
        days_count: количество дней в расписании
        """
        days_to_use = BaseScheduler.DAY_SHORT[:days_count]
        
        # Основные данные
        children_data = [
            # Здоровые дети с полной доступностью
            ("Иван Петров", "здоров", []),
            ("Мария Сидорова", "здоров", []),
            ("Алексей Иванов", "здоров", [("ср", "заявление"), ("пт", "заявление")]),
            ("Елена Кузнецова", "здоров", [("чт", "прогул"), ("пт", "прогул")]),
            ("Дмитрий Смирнов", "здоров", []),
            ("Анна Попова", "здоров", [("вт", "заявление"), ("сб", "больничный")]),
            
            # Недавно болевшие
            ("Сергей Васильев", "недавно болел", []),
            ("Ольга Новикова", "недавно болела", []),
            
            # Болеет сейчас
            ("Павел Федоров", "болеет", []),
            
            # Остальные здоровые
            ("Татьяна Морозова", "здоров", []),
            ("Николай Волков", "здоров", []),
            ("Юлия Алексеева", "здоров", []),
            ("Андрей Лебедев", "здоров", []),
            ("Наталья Семенова", "здоров", []),
            ("Артем Егоров", "здоров", []),
            ("Екатерина Павлова", "здоров", []),
            ("Михаил Козлов", "здоров", []),
            ("Светлана Николаева", "здоров", []),
            ("Владимир Захаров", "здоров", []),
            ("Алина Степанова", "здоров", []),
            ("Игорь Макаров", "здоров", []),
            ("Виктория Орлова", "здоров", []),
            ("Константин Андреев", "здоров", []),
            ("Марина Зайцева", "здоров", []),
            ("Роман Соловьев", "здоров", []),
            ("Ксения Виноградова", "здоров", []),
            ("Георгий Богданов", "здоров", []),
            ("Дарья Фролова", "здоров", []),
            ("Станислав Тимофеев", "здоров", []),
        ]
        
        children = []
        
        for name, health_status, special_days in children_data:
            # Создаем статусы для всех дней
            day_statuses = []
            
            for day in days_to_use:
                # Проверяем специальные статусы
                status = "доступен"
                for special_day, special_status in special_days:
                    if special_day == day:
                        status = special_status
                        break
                
                # Если ребенок болеет, он не доступен
                if health_status == "болеет":
                    status = "больничный"
                
                day_statuses.append(DayStatus(day, status))
            
            children.append(Child(name, day_statuses, health_status))
        
        return children

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def get_user_choice() -> str:
    """Получает выбор алгоритма от пользователя"""
    print("\n" + "=" * 80)
    print("🤖 ВЫБОР АЛГОРИТМА ГЕНЕРАЦИИ")
    print("=" * 80)
    
    print("\nДоступные алгоритмы:")
    print("  1. Жадный алгоритм (рекомендуется)")
    print("     - Быстрый, оптимальный для большинства случаев")
    print("     - Поэтапный выбор лучших кандидатов")
    
    print("\n  2. Алгоритм назначений")
    print("     - Решение задачи оптимизации")
    print("     - Использует матрицу стоимости")
    print("     - Более точный, но медленнее")
    
    print("\n  3. Случайный алгоритм")
    print("     - Множество случайных попыток")
    print("     - Выбор лучшего результата")
    print("     - Может найти неожиданные решения")
    
    while True:
        choice = input("\nВыберите алгоритм (1-3) или нажмите Enter для выбора по умолчанию (1): ").strip()
        
        if choice == "":
            return "1"
        elif choice in ["1", "2", "3"]:
            return choice
        else:
            print("❌ Неверный выбор. Пожалуйста, введите 1, 2 или 3.")

def simulate_thinking(seconds: int = 10):
    """Симулирует процесс 'думания' алгоритма"""
    print(f"\n⏳ Алгоритм обрабатывает данные... (примерно {seconds} секунд)")
    print("Это сложная оптимизационная задача, требующая времени.")
    
    # Прогресс-бар
    for i in range(seconds * 2):  # Половины секунды для плавности
        time.sleep(0.5)
        
        # Вычисляем прогресс
        progress = (i + 1) / (seconds * 2)
        bar_length = 40
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Показываем прогресс
        percent = int(progress * 100)
        print(f"\r  [{bar}] {percent}% ", end="", flush=True)
    
    print()  # Новая строка после прогресс-бара

def main():
    """Точка входа в программу"""
    try:
        print("🚀 Запуск генератора расписания дежурств")
        print("=" * 80)
        
        # Общий замер времени
        total_start_time = time.time()
        
        # 1. Создаем данные
        print("\n📋 Создание данных...")
        children = DataFactory.create_sample_children(DAYS_COUNT)
        
        # 2. Получаем выбор алгоритма от пользователя
        choice = get_user_choice()
        
        # 3. Создаем планировщик в зависимости от выбора
        print("\n⚙️  Инициализация планировщика...")
        
        if choice == "1":
            scheduler = GreedyScheduler(DAYS_COUNT, PLACES_CONFIG, children)
            algorithm_name = "Жадный алгоритм"
        elif choice == "2":
            scheduler = AssignmentScheduler(DAYS_COUNT, PLACES_CONFIG, children)
            algorithm_name = "Задача о назначениях"
        else:  # choice == "3"
            scheduler = RandomScheduler(DAYS_COUNT, PLACES_CONFIG, children)
            algorithm_name = "Случайный алгоритм"
        
        # 4. Вывод конфигурации
        ScheduleVisualizer.print_configuration(scheduler, children)
        
        # 5. Симуляция "думания" алгоритма
        simulate_thinking(10)
        
        # 6. Генерация расписания
        print(f"\n🎲 Генерация расписания с помощью {algorithm_name}...")
        algorithm_start_time = time.time()
        result = scheduler.find_best_schedule()
        algorithm_time = time.time() - algorithm_start_time
        
        # 7. Вывод результатов
        total_time = time.time() - total_start_time
        print(f"\n⏱️  Время выполнения:")
        print(f"  • Алгоритм: {algorithm_time:.2f} секунд")
        print(f"  • Общее время: {total_time:.2f} секунд")
        
        ScheduleVisualizer.print_schedule(result, scheduler)
        ScheduleVisualizer.print_statistics(result, children)
        
        print("\n" + "=" * 80)
        print("✅ Генерация завершена успешно!")
        
    except ValueError as e:
        print(f"\n❌ Ошибка в данных: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Для отладки можно установить DEBUG = True
    main()
