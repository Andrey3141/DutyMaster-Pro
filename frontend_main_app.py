# frontend_main_app.py
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import traceback
from datetime import datetime
import json
import webbrowser
import os

# Импортируем бэкенд
from backend import (
    DayStatus, Child, ScheduleResult, BaseScheduler, 
    GreedyScheduler, AssignmentScheduler, RandomScheduler,
    ScheduleVisualizer, DataFactory, DAYS_COUNT, PLACES_CONFIG
)

# Импортируем наши модули
from frontend_ui_widgets import *
from frontend_color_editor import *

# ========== ГЛАВНОЕ ОКНО ==========
class DutyScheduleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Фиксируем размер окна и открываем на весь экран
        self.setWindowFlags(Qt.WindowType.Window | 
                          Qt.WindowType.WindowMinMaxButtonsHint |  # Добавляем кнопки максимизации
                          Qt.WindowType.WindowCloseButtonHint)
        
        self.setWindowTitle("📅 Генератор расписания дежурств")
        
        # Загружаем ВСЕ данные
        self.settings = self.load_settings()
        
        # ВАЖНОЕ ИСПРАВЛЕНИЕ 1: Загружаем все данные из настроек
        self.children_data = self.settings.get('children_data', [])
        self.current_theme = self.settings.get('theme', 'light')
        self.custom_bg_color = self.settings.get('custom_bg_color')
        
        # ИСПРАВЛЕНИЕ 1: Исправляем загрузку custom_colors
        self.custom_colors = self.settings.get('custom_colors', {})
        
        self.theme_colors = AppTheme.get_theme(self.current_theme)
        
        # Настройки
        self.days_count = self.settings.get('days_count', DAYS_COUNT)
        self.places_config = self.settings.get('places_config', PLACES_CONFIG.copy())
        self.fixed_days = set(self.settings.get('fixed_days', []))
        
        # Исправление 3: Сохраняем выбранный алгоритм
        algorithm_mapping = {
            "greedy": 0,
            "assignment": 1,
            "random": 2
        }
        self.algorithm_choice = self.settings.get('algorithm', 'greedy')
        self.current_algorithm_index = algorithm_mapping.get(self.algorithm_choice, 0)
        
        # Данные
        self.current_schedule = None
        
        self.setup_ui()
        self.apply_theme()
        
        # Если нет учеников, загружаем примерные данные
        if not self.children_data:
            self.load_sample_data()
        else:
            self.update_stats()
        
        # 2. Открываем на весь экран после инициализации
        self.showMaximized()
    
    def load_settings(self):
        """Загрузить все настройки из файла"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print("Загружены настройки:", data.keys())
                return data
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
        return {}
            
    def save_settings(self):
        """Сохранить ВСЕ настройки в файл"""
        try:
            settings = {
                'theme': self.current_theme,
                'days_count': self.days_count,
                'places_config': self.places_config,
                'custom_bg_color': self.custom_bg_color,
                'custom_colors': self.custom_colors,
                'algorithm': self.algorithm_choice,
                'fixed_days': list(self.fixed_days),
                # ВАЖНОЕ ИСПРАВЛЕНИЕ: Сохраняем учеников
                'children_data': self.children_data
            }
            
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            print("Все настройки сохранены в settings.json")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            
    def reset_to_default(self):
        """Сбросить ВСЕ настройки и данные к заводским"""
        try:
            # Сбрасываем все переменные
            self.current_theme = 'light'
            self.custom_bg_color = None
            self.custom_colors = {}
            self.days_count = DAYS_COUNT
            self.places_config = PLACES_CONFIG.copy()
            self.algorithm_choice = 'greedy'
            self.current_algorithm_index = 0
            self.children_data = []
            self.fixed_days = set()
            self.current_schedule = None
            
            # Сохраняем сброшенные настройки
            self.save_settings()
            
            # ИСПРАВЛЕНИЕ 1: Применяем тему сразу
            self.theme_colors = AppTheme.get_theme(self.current_theme)
            self.apply_theme()
            
            # Обновляем интерфейс
            self.update_stats()
            
            # Загружаем примерные данные
            self.load_sample_data()
            
            QMessageBox.information(self, "Сброс", "Все настройки и данные сброшены к заводским")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сбросе настроек:\n{str(e)}")
        
    def setup_ui(self):
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Левая панель (20%)
        self.left_panel = self.create_left_panel()
        main_layout.addWidget(self.left_panel, 20)
        
        # Разделитель
        splitter = QFrame()
        splitter.setFrameShape(QFrame.Shape.VLine)
        main_layout.addWidget(splitter)
        
        # Правая панель (80%)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 80)
        
    def create_left_panel(self):
        panel = ModernCard()
        panel.setMinimumWidth(300)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Заголовок
        title = QLabel("DutyMaster Pro")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {self.theme_colors['primary']};
            padding-bottom: 10px;
            border-bottom: 2px solid {self.theme_colors['border']};
        """)
        layout.addWidget(title)
        
        # Статистика
        stats_card = ModernCard()
        stats_layout = QVBoxLayout(stats_card)
        
        stats_title = QLabel("📊 Статистика")
        stats_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(stats_title)
        
        self.stats_labels = {}
        stats_items = [
            ("Учеников:", "students_count", "👥"),
            ("Дней:", "days_count", "📅"),
            ("Мест:", "places_count", "📍"),
            ("Дежурств:", "duties_count", "📋"),
            ("Фикс. дней:", "fixed_days_count", "📌")
        ]
        
        for text, key, icon in stats_items:
            stat_widget = QWidget()
            stat_layout = QHBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 5, 0, 5)
            
            label = QLabel(f"{icon} {text}")
            label.setStyleSheet("color: #6C757D;")
            
            value = QLabel("0")
            value.setStyleSheet("font-weight: bold;")
            
            stat_layout.addWidget(label)
            stat_layout.addStretch()
            stat_layout.addWidget(value)
            stats_layout.addWidget(stat_widget)
            
            self.stats_labels[key] = value
            
        layout.addWidget(stats_card)
        
        # Быстрые действия
        actions_card = ModernCard()
        actions_layout = QVBoxLayout(actions_card)
        
        actions_title = QLabel("⚡ Быстрые действия")
        actions_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        actions_layout.addWidget(actions_title)
        
        # Кнопки действий с подсказками
        actions = [
            ("📅 Дни недели", self.open_days_dialog, "Настройка количества дней"),
            ("👥 Ученики", self.open_students_dialog, "Управление списком учеников"),
            ("📍 Места", self.open_places_dialog, "Настройка мест дежурств"),
            ("🤖 Алгоритм", self.open_algorithm_dialog, "Выбор алгоритма генерации"),
            ("🎨 Тема", self.open_theme_dialog, "Смена темы оформления"),
            ("⚙️ Настройки", self.open_app_settings, "Настройки приложения"),
            ("📂 Загрузить", self.load_schedule_file, "Загрузка расписания из файла"),
            ("📤 Экспорт", self.export_schedule, "Экспорт расписания в файл")
        ]
        
        for text, callback, tooltip in actions:
            btn = ModernButton(text)
            btn.clicked.connect(callback)
            btn.setToolTip(tooltip)  # ИСПРАВЛЕНИЕ 4
            actions_layout.addWidget(btn)
            
        layout.addWidget(actions_card)
        
        # Кнопка генерации
        self.generate_btn = ModernButton("🚀 СГЕНЕРИРОВАТЬ РАСПИСАНИЕ")
        self.generate_btn.setMinimumHeight(60)
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                font-weight: bold;
                font-size: 16px;
                background-color: {self.theme_colors['primary']};
                color: white;
                border-radius: 8px;
                padding: 15px;
            }}
            QPushButton:hover {{
                background-color: {self.theme_colors['primary_hover']};
            }}
        """)
        self.generate_btn.clicked.connect(self.generate_schedule)
        self.generate_btn.setToolTip("Сгенерировать расписание дежурств")  # ИСПРАВЛЕНИЕ 4
        layout.addWidget(self.generate_btn)
        
        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        return panel
        
    def create_right_panel(self):
        # Вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)
        
        # Вкладка 1: Расписание
        schedule_tab = self.create_schedule_tab()
        self.tab_widget.addTab(schedule_tab, "📅 Расписание")
        
        # Вкладка 2: Статистика
        stats_tab = self.create_statistics_tab()
        self.tab_widget.addTab(stats_tab, "📊 Статистика")
        
        # Вкладка 3: Анализ
        analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(analysis_tab, "📈 Анализ")
        
        return self.tab_widget
        
    def create_schedule_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Информационная панель
        info_panel = ModernCard()
        info_layout = QHBoxLayout(info_panel)
        
        info_items = [
            ("Алгоритм:", "algorithm", "Используемый алгоритм генерации"),
            ("Оценка:", "score", "Качество расписания (баллы)"),
            ("Пустых мест:", "empty_spots", "Количество незаполненных мест"),
            ("Замечаний:", "issues_count", "Количество проблем в расписании")
        ]
        
        for text, key, tooltip in info_items:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            label = QLabel(text)
            label.setStyleSheet("color: #6C757D; font-size: 12px;")
            label.setToolTip(tooltip)  # ИСПРАВЛЕНИЕ 4
            
            value = QLabel("—")
            value.setStyleSheet("font-weight: bold; font-size: 16px;")
            value.setToolTip(tooltip)  # ИСПРАВЛЕНИЕ 4
            
            container_layout.addWidget(label)
            container_layout.addWidget(value)
            info_layout.addWidget(container)
            
            setattr(self, f"{key}_label", value)
            
        layout.addWidget(info_panel)
        
        # Контейнер для расписания
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.schedule_container = QWidget()
        self.schedule_layout = QVBoxLayout(self.schedule_container)
        self.schedule_layout.setSpacing(20)
        
        scroll.setWidget(self.schedule_container)
        layout.addWidget(scroll, 1)
        
        return widget
        
    def create_statistics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Распределение по здоровью
        health_card = ModernCard()
        health_layout = QVBoxLayout(health_card)
        
        health_title = QLabel("🏥 Распределение по статусу здоровья")
        health_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 15px;")
        health_layout.addWidget(health_title)
        
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(5)
        self.health_table.setHorizontalHeaderLabels(["Статус", "Учеников", "Дежурств", "Среднее", "Диапазон"])
        health_layout.addWidget(self.health_table)
        
        layout.addWidget(health_card)
        
        # Детальная статистика
        detail_card = ModernCard()
        detail_layout = QVBoxLayout(detail_card)
        
        detail_title = QLabel("👥 Детальная статистика")
        detail_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 15px;")
        detail_layout.addWidget(detail_title)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(4)
        self.detail_table.setHorizontalHeaderLabels(["Ученик", "Статус", "Дежурств", "Эффективность"])
        detail_layout.addWidget(self.detail_table)
        
        layout.addWidget(detail_card, 1)
        
        return widget
        
    def create_analysis_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Анализ качества
        quality_card = ModernCard()
        quality_layout = QVBoxLayout(quality_card)
        
        quality_title = QLabel("📈 Анализ качества")
        quality_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 15px;")
        quality_layout.addWidget(quality_title)
        
        self.quality_text = QTextEdit()
        self.quality_text.setReadOnly(True)
        self.quality_text.setPlaceholderText("После генерации здесь появится анализ качества расписания...")
        quality_layout.addWidget(self.quality_text)
        
        layout.addWidget(quality_card)
        
        # Замечания
        issues_card = ModernCard()
        issues_layout = QVBoxLayout(issues_card)
        
        issues_title = QLabel("⚠️ Замечания")
        issues_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 15px;")
        issues_layout.addWidget(issues_title)
        
        self.issues_list = QListWidget()
        issues_layout.addWidget(self.issues_list)
        
        layout.addWidget(issues_card)
        
        return widget
        
    def apply_theme(self):
        """ИСПРАВЛЕНИЕ 1: Применить текущую тему с пользовательскими цветами"""
        self.theme_colors = AppTheme.get_theme(self.current_theme)
        
        # Базовый стиль
        base_style = f"""
            QMainWindow {{
                background-color: {self.custom_bg_color if self.custom_bg_color else self.theme_colors['bg_primary']};
            }}
            
            QFrame {{
                background-color: {self.theme_colors['bg_card']};
                border: 1px solid {self.theme_colors['border']};
                border-radius: 8px;
            }}
            
            QPushButton {{
                background-color: {self.theme_colors['primary']};
                color: {self.theme_colors['text_on_primary']};
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: 500;
            }}
            
            QPushButton:hover {{
                background-color: {self.theme_colors['primary_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {self.theme_colors['primary_hover']};
            }}
            
            QLabel {{
                color: {self.theme_colors['text_primary']};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {self.theme_colors['border']};
                background-color: {self.theme_colors['bg_primary']};
            }}
            
            QTabBar::tab {{
                background-color: {self.theme_colors['bg_secondary']};
                padding: 10px 20px;
                margin-right: 2px;
                color: {self.theme_colors['text_primary']};
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.theme_colors['bg_primary']};
                color: {self.theme_colors['primary']};
                border-bottom: 2px solid {self.theme_colors['primary']};
            }}
            
            QTableWidget {{
                border: 1px solid {self.theme_colors['border']};
                background-color: {self.theme_colors['bg_card']};
                color: {self.theme_colors['text_primary']};
                gridline-color: {self.theme_colors['border']};
            }}
            
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.theme_colors['border']};
                color: {self.theme_colors['text_primary']};
            }}
            
            QProgressBar {{
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
                text-align: center;
                color: {self.theme_colors['text_primary']};
            }}
            
            QProgressBar::chunk {{
                background-color: {self.theme_colors['primary']};
                border-radius: 4px;
            }}
            
            QTextEdit, QListWidget {{
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
                background-color: {self.theme_colors['bg_card']};
                color: {self.theme_colors['text_primary']};
            }}
            
            QLineEdit, QComboBox, QSpinBox {{
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
                padding: 5px;
                background-color: {self.theme_colors['bg_card']};
                color: {self.theme_colors['text_primary']};
            }}
            
            QGroupBox {{
                color: {self.theme_colors['text_primary']};
                border: 2px solid {self.theme_colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.theme_colors['primary']};
            }}
            
            QRadioButton, QCheckBox {{
                color: {self.theme_colors['text_primary']};
            }}
            
            QHeaderView::section {{
                background-color: {self.theme_colors['bg_secondary']};
                color: {self.theme_colors['text_primary']};
                border: none;
                border-bottom: 2px solid {self.theme_colors['border']};
                padding: 8px;
            }}
            
            .fixed-day {{
                background-color: #E9ECEF !important;
                color: #6C757D !important;
                border-color: #DEE2E6 !important;
            }}
        """
        
        # Применяем пользовательские цвета
        final_style = base_style
        
        if self.custom_colors:
            # ИСПРАВЛЕНИЕ: Применяем пользовательские цвета ко всем элементам
            for key, value in self.custom_colors.items():
                if isinstance(value, dict):
                    # Настройки шрифта
                    if 'family' in value and 'size' in value:
                        # Применяем шрифт к виджетам
                        try:
                            # Ищем виджет по имени в ключе
                            widget_name = key.replace('font_', '')
                            widget = self.findChild(QWidget, widget_name)
                            if widget:
                                font = QFont(value['family'], value['size'])
                                widget.setFont(font)
                        except Exception as e:
                            print(f"Ошибка применения шрифта {key}: {e}")
                else:
                    # Цвета
                    final_style += f"""
                        #{key} {{
                            {"background-color" if key.startswith('bg_') else "color" if key.startswith('text_') else "border"}: {value} !important;
                        }}
                    """
        
        try:
            self.setStyleSheet(final_style)
        except Exception as e:
            print(f"Ошибка применения стиля: {e}")
            # Применяем только базовый стиль в случае ошибки
            self.setStyleSheet(base_style)
            
        self.update_stats()
        
    def adjust_color(self, color_hex, amount):
        """Корректировка цвета (осветление/затемнение)"""
        try:
            color = QColor(color_hex)
            h, s, l, a = color.getHsl()
            l = max(0, min(255, l + amount))
            return QColor.fromHsl(h, s, l, a).name()
        except:
            return color_hex
        
    # ========== ОКНА НАСТРОЕК ==========
    def open_days_dialog(self):
        """Открыть диалог настройки дней"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.days_count = dialog.days_spin.value()
            self.save_settings()  # Сохраняем изменения
            self.update_stats()
            
    def open_students_dialog(self):
        """Открыть диалог управления учениками"""
        from functools import partial
        
        dialog = QDialog(self)
        dialog.setWindowTitle("👥 Управление учениками")
        dialog.setModal(True)
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Таблица учеников
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Имя", "Статус здоровья", "Доступные дни", "Действия"])
        table.horizontalHeader().setStretchLastSection(True)
        
        # Исправление 1: Используем актуальное количество учеников
        table.setRowCount(len(self.children_data))
        
        for i, student in enumerate(self.children_data):
            # Имя
            table.setItem(i, 0, QTableWidgetItem(student['name']))
            
            # Статус здоровья
            status = student['health_status']
            if status == "здоров":
                status_text = "✅ Здоров"
                color = self.theme_colors['health_healthy']
            elif status in ["недавно болел", "недавно болела"]:
                status_text = "🔄 Недавно болел(а)"
                color = self.theme_colors['health_recovering']
            else:
                status_text = "🛌 Болеет"
                color = self.theme_colors['health_sick']
                
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(color))
            table.setItem(i, 1, status_item)
            
            # Доступные дни
            available_days = [day for day, status in student['days'].items() if status == "доступен"]
            days_text = ", ".join(available_days) if available_days else "Нет"
            table.setItem(i, 2, QTableWidgetItem(days_text))
            
            # Кнопки действий
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            
            # Исправление 2: Используем lambda с аргументами по умолчанию
            edit_btn.clicked.connect(lambda checked, idx=i: self.edit_student(idx, dialog))
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_student(idx, dialog))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            table.setCellWidget(i, 3, actions_widget)
        
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        add_btn = ModernButton("Добавить ученика", "➕")
        add_btn.clicked.connect(lambda: self.add_student_from_dialog(dialog))
        buttons_layout.addWidget(add_btn)
        
        buttons_layout.addStretch()
        
        close_btn = ModernButton("Закрыть", "❌")
        close_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec()
        
    def edit_student(self, index, dialog=None):
        """Редактировать ученика"""
        try:
            if 0 <= index < len(self.children_data):
                student_dialog = StudentDialog(self.children_data[index], self)
                if student_dialog.exec():
                    self.children_data[index] = student_dialog.get_data()
                    self.update_stats()
                    self.save_settings()  # Сохраняем изменения
                    if dialog:
                        dialog.accept()
                        self.open_students_dialog()
        except Exception as e:
            print(f"Ошибка при редактировании ученика: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при редактировании ученика:\n{str(e)}")
            
    def delete_student(self, index, dialog=None):
        """Удалить ученика"""
        try:
            if 0 <= index < len(self.children_data):
                reply = QMessageBox.question(
                    self, "Удаление",
                    f"Удалить ученика {self.children_data[index]['name']}?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.children_data.pop(index)
                    self.update_stats()
                    self.save_settings()  # Сохраняем изменения
                    if dialog:
                        dialog.accept()
                        self.open_students_dialog()
        except Exception as e:
            print(f"Ошибка при удалении ученика: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении ученика:\n{str(e)}")
            
    def add_student_from_dialog(self, parent_dialog):
        dialog = StudentDialog(parent=self)
        if dialog.exec():
            self.children_data.append(dialog.get_data())
            self.save_settings()  # Сохраняем изменения
            parent_dialog.accept()
            self.open_students_dialog()
            
    def open_places_dialog(self):
        dialog = PlacesDialog(self.places_config, self)
        if dialog.exec():
            self.places_config = dialog.get_config()
            self.save_settings()  # Сохраняем изменения
            self.update_stats()
            
    def open_algorithm_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("🤖 Выбор алгоритма")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Описание алгоритмов
        info_label = QLabel("""
        <h3>Доступные алгоритмы:</h3>
        <p><b>1. Жадный алгоритм</b> (рекомендуется)<br>
        Быстрый и эффективный для большинства случаев.</p>
        
        <p><b>2. Алгоритм назначений</b><br>
        Более точный, но медленнее. Использует матрицу стоимости.</p>
        
        <p><b>3. Случайный алгоритм</b><br>
        Множество попыток, выбор лучшего результата.</p>
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Выбор алгоритма
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["Жадный алгоритм", "Алгоритм назначений", "Случайный алгоритм"])
        
        # Исправление 3: Устанавливаем сохраненный алгоритм
        self.algo_combo.setCurrentIndex(self.current_algorithm_index)
        
        layout.addWidget(self.algo_combo)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            choice = self.algo_combo.currentIndex()
            self.algorithm_choice = ["greedy", "assignment", "random"][choice]
            self.current_algorithm_index = choice
            self.save_settings()  # Сохраняем изменения
            
    def open_theme_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("🎨 Выбор темы")
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        themes = [
            ("☀️ Светлая", "light"),
            ("🌙 Тёмная", "dark"),
            ("🌈 Смешанная", "mixed")
        ]
        
        for text, theme_id in themes:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(self.current_theme == theme_id)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, t=theme_id: self.change_theme(t, dialog))
            layout.addWidget(btn)
            
        # Кнопка закрытия
        close_btn = ModernButton("Закрыть", "❌")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
        
    def open_app_settings(self):
        """Открыть настройки приложения"""
        dialog = AppSettingsDialog(self)
        dialog.exec()
        
    def change_theme(self, theme_name, dialog):
        self.current_theme = theme_name
        self.save_settings()  # Сохраняем изменения
        self.apply_theme()
        dialog.accept()
        
    # ========== ОСНОВНАЯ ЛОГИКА ==========
    def update_stats(self):
        """Обновить статистику"""
        # Исправление 1: Обновляем статистику после удаления учеников
        self.stats_labels['students_count'].setText(str(len(self.children_data)))
        self.stats_labels['days_count'].setText(str(self.days_count))
        
        total_places = sum(self.places_config.values())
        self.stats_labels['places_count'].setText(str(total_places))
        
        total_duties = self.days_count * total_places
        self.stats_labels['duties_count'].setText(str(total_duties))
        
        # Количество фиксированных дней
        self.stats_labels['fixed_days_count'].setText(str(len(self.fixed_days)))
        
    def load_sample_data(self):
        """Загрузить примерные данные только если нет сохраненных"""
        try:
            # Используем фабрику из бэкенда
            children = DataFactory.create_sample_children(DAYS_COUNT)
            
            for child in children:
                # Конвертируем в наш формат
                days_dict = {}
                for day_status in child.days:
                    days_dict[day_status.day] = day_status.status
                    
                self.children_data.append({
                    'name': child.name,
                    'health_status': child.health_status,
                    'days': days_dict
                })
                
            self.update_stats()
            self.save_settings()  # Сохраняем примерные данные
            
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            
    def generate_schedule(self):
        """Сгенерировать расписание"""
        try:
            if not self.children_data:
                QMessageBox.warning(self, "Ошибка", "Добавьте учеников!")
                return
                
            if not self.places_config:
                QMessageBox.warning(self, "Ошибка", "Добавьте места дежурств!")
                return
                
            # Подготовка данных для бэкенда
            days_to_use = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][:self.days_count]
            children = []
            
            for child_data in self.children_data:
                day_statuses = []
                for day in days_to_use:
                    status = child_data['days'].get(day, "доступен")
                    day_statuses.append(DayStatus(day, status))
                    
                children.append(Child(
                    name=child_data['name'],
                    days=day_statuses,
                    health_status=child_data['health_status']
                ))
            
            # Выбор алгоритма
            if self.algorithm_choice == "greedy":
                scheduler = GreedyScheduler(self.days_count, self.places_config, children)
            elif self.algorithm_choice == "assignment":
                scheduler = AssignmentScheduler(self.days_count, self.places_config, children)
            else:  # random
                scheduler = RandomScheduler(self.days_count, self.places_config, children)
            
            # Прогресс
            self.progress_bar.setValue(25)
            QApplication.processEvents()
            
            # Генерация
            result = scheduler.find_best_schedule(max_attempts=100)
            
            self.progress_bar.setValue(100)
            
            # Обновление интерфейса
            self.display_schedule_result(result)
            self.display_statistics(result)
            self.display_analysis(result)
            
            self.current_schedule = result
            
            QMessageBox.information(self, "Успех", "Расписание успешно сгенерировано!")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка генерации:\n{str(e)}")
            print(traceback.format_exc())
        finally:
            self.progress_bar.setValue(0)
            
    def display_schedule_result(self, result):
        """Отобразить результат расписания"""
        # Очистить контейнер
        while self.schedule_layout.count():
            item = self.schedule_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Заголовки
        days_header = QWidget()
        days_layout = QHBoxLayout(days_header)
        days_layout.addWidget(QLabel("📍 Места"), 2)
        
        days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][:self.days_count]
        for day_idx, day in enumerate(days):
            day_widget = QWidget()
            day_layout = QVBoxLayout(day_widget)
            day_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Добавляем индикатор фиксированного дня
            if day in self.fixed_days:
                fixed_indicator = QLabel("📌")
                fixed_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                fixed_indicator.setStyleSheet("font-size: 18px;")
                fixed_indicator.setToolTip("Фиксированный день - редактирование недоступно")
                day_layout.addWidget(fixed_indicator)
            
            day_label = QLabel(day.upper())
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Выделяем фиксированные дни
            if day in self.fixed_days:
                day_label.setStyleSheet("font-weight: bold; color: #6C757D; text-decoration: underline;")
                day_label.setToolTip("Фиксированный день")
            else:
                day_label.setStyleSheet("font-weight: bold;")
            
            day_layout.addWidget(day_label)
            days_layout.addWidget(day_widget, 1)
            
        self.schedule_layout.addWidget(days_header)
        
        # Список всех мест
        all_places = []
        for place, count in self.places_config.items():
            all_places.extend([place] * count)
            
        # Расписание
        for place_idx, place in enumerate(all_places):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            
            # Название места
            place_label = QLabel(f"📍 {place}")
            place_label.setStyleSheet("font-weight: bold;")
            row_layout.addWidget(place_label, 2)
            
            # Дежурные по дням
            for day_idx, day in enumerate(days):
                cell_widget = QWidget()
                cell_layout = QVBoxLayout(cell_widget)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Проверяем, фиксированный ли день
                is_fixed = day in self.fixed_days
                
                if place_idx < len(result.schedule[day_idx]) and result.schedule[day_idx][place_idx]:
                    child = result.schedule[day_idx][place_idx]
                    
                    # Цвет статуса
                    if child.health_status == "здоров":
                        color = self.theme_colors['health_healthy']
                        icon = "✅"
                    elif child.health_status in ["недавно болел", "недавно болела"]:
                        color = self.theme_colors['health_recovering']
                        icon = "🔄"
                    else:
                        color = self.theme_colors['health_sick']
                        icon = "🛌"
                        
                    name_label = QLabel(child.name)
                    name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    icon_label = QLabel(icon)
                    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    cell_layout.addWidget(name_label)
                    cell_layout.addWidget(icon_label)
                    
                    # Стиль для фиксированных дней
                    if is_fixed:
                        cell_style = f"""
                            border: 2px solid #E9ECEF;
                            border-radius: 8px;
                            background-color: #F8F9FA;
                            padding: 5px;
                            color: #6C757D;
                        """
                        name_label.setStyleSheet(f"font-weight: bold; color: #6C757D;")
                        name_label.setToolTip("Фиксированный день - редактирование недоступно")
                    else:
                        cell_style = f"""
                            border: 2px solid {color}30;
                            border-radius: 8px;
                            background-color: {color}10;
                            padding: 5px;
                        """
                        name_label.setStyleSheet(f"font-weight: bold; color: {color};")
                    
                    cell_widget.setStyleSheet(cell_style)
                    
                    # Для фиксированных дней делаем неактивными
                    if is_fixed:
                        cell_widget.setEnabled(False)
                        
                else:
                    empty_label = QLabel("—")
                    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    if is_fixed:
                        empty_label.setStyleSheet("color: #6C757D; font-style: italic;")
                        empty_label.setToolTip("Фиксированный день - редактирование недоступно")
                    else:
                        empty_label.setStyleSheet("color: #6C757D; font-style: italic;")
                    
                    cell_layout.addWidget(empty_label)
                    
                    # Стиль для фиксированных дней
                    if is_fixed:
                        cell_widget.setStyleSheet(f"""
                            border: 2px solid #E9ECEF;
                            border-radius: 8px;
                            background-color: #F8F9FA;
                            padding: 5px;
                        """)
                        cell_widget.setEnabled(False)
                
                row_layout.addWidget(cell_widget, 1)
                
            self.schedule_layout.addWidget(row_widget)
            
        # Информация
        self.algorithm_label.setText(result.algorithm_name)
        self.score_label.setText(str(result.score))
        self.empty_spots_label.setText(str(result.empty_spots))
        self.issues_count_label.setText(str(len(result.issues)))
        
    def display_statistics(self, result):
        """Отобразить статистику"""
        # Распределение по здоровью
        health_stats = {}
        for child in self.children_data:
            status = child['health_status']
            if status not in health_stats:
                health_stats[status] = {'count': 0, 'duties': []}
            health_stats[status]['count'] += 1
            duties = result.distribution.get(child['name'], 0)
            health_stats[status]['duties'].append(duties)
            
        self.health_table.setRowCount(len(health_stats))
        row = 0
        for status, stats in health_stats.items():
            # Отображение статуса
            if status == "здоров":
                display_text = "✅ Здоровые"
                color = self.theme_colors['health_healthy']
            elif status in ["недавно болел", "недавно болела"]:
                display_text = "🔄 Недавно болели"
                color = self.theme_colors['health_recovering']
            else:
                display_text = "🛌 Болеют"
                color = self.theme_colors['health_sick']
                
            self.health_table.setItem(row, 0, QTableWidgetItem(display_text))
            self.health_table.item(row, 0).setForeground(QColor(color))
            
            self.health_table.setItem(row, 1, QTableWidgetItem(str(stats['count'])))
            
            total_duties = sum(stats['duties'])
            self.health_table.setItem(row, 2, QTableWidgetItem(str(total_duties)))
            
            avg_duties = total_duties / stats['count'] if stats['count'] > 0 else 0
            self.health_table.setItem(row, 3, QTableWidgetItem(f"{avg_duties:.2f}"))
            
            if stats['duties']:
                range_text = f"{min(stats['duties'])}-{max(stats['duties'])}"
            else:
                range_text = "0-0"
            self.health_table.setItem(row, 4, QTableWidgetItem(range_text))
            
            row += 1
            
        self.health_table.resizeColumnsToContents()
        
        # Детальная статистика
        self.detail_table.setRowCount(len(result.distribution))
        row = 0
        for name, duties in sorted(result.distribution.items(), key=lambda x: (-x[1], x[0])):
            child = next((c for c in self.children_data if c['name'] == name), None)
            if child:
                self.detail_table.setItem(row, 0, QTableWidgetItem(name))
                
                # Статус
                status = child['health_status']
                if status == "здоров":
                    status_text = "✅ Здоров"
                elif status in ["недавно болел", "недавно болела"]:
                    status_text = "🔄 Недавно болел(а)"
                else:
                    status_text = "🛌 Болеет"
                    
                self.detail_table.setItem(row, 1, QTableWidgetItem(status_text))
                self.detail_table.setItem(row, 2, QTableWidgetItem(str(duties)))
                
                # Эффективность
                available_days = sum(1 for d in child['days'].values() if d == "доступен")
                efficiency = (duties / available_days * 100) if available_days > 0 else 0
                
                if efficiency >= 80:
                    eff_text = "🔴 Высокая"
                elif efficiency >= 50:
                    eff_text = "🟡 Средняя"
                else:
                    eff_text = "🟢 Низкая"
                    
                self.detail_table.setItem(row, 3, QTableWidgetItem(eff_text))
                
                row += 1
                
        self.detail_table.resizeColumnsToContents()
        
    def display_analysis(self, result):
        """Отобразить анализ"""
        # Информация о фиксированных днях
        fixed_days_info = ""
        if self.fixed_days:
            fixed_days_info = f"""
            <p><b>Фиксированные дни:</b> {', '.join(sorted(self.fixed_days))}</p>
            <p>Фиксированные дни выделены цветом и недоступны для редактирования.</p>
            """
        else:
            fixed_days_info = "<p><b>Фиксированные дни:</b> нет</p>"
            
        analysis_text = f"""
        <h3>📊 Анализ качества расписания</h3>
        
        <p><b>Алгоритм:</b> {result.algorithm_name}</p>
        <p><b>Оценка качества:</b> {result.score} баллов</p>
        <p><b>Пустых мест:</b> {result.empty_spots}</p>
        <p><b>Всего распределено дежурств:</b> {sum(result.distribution.values())}</p>
        
        {fixed_days_info}
        
        <h4>📈 Распределение:</h4>
        <p>• Среднее дежурств на ученика: {sum(result.distribution.values()) / len(result.distribution):.2f}</p>
        <p>• Диапазон: от {min(result.distribution.values())} до {max(result.distribution.values())}</p>
        """
        
        self.quality_text.setHtml(analysis_text)
        
        # Замечания
        self.issues_list.clear()
        if result.issues:
            for issue in result.issues:
                self.issues_list.addItem(f"⚠️  {issue}")
        else:
            self.issues_list.addItem("✅ Нет замечаний")
            
    def export_schedule(self):
        """Экспорт расписания"""
        if not self.current_schedule:
            QMessageBox.warning(self, "Экспорт", "Сначала сгенерируйте расписание!")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт расписания",
            f"расписание_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("РАСПИСАНИЕ ДЕЖУРСТВ\n")
                    f.write("=" * 60 + "\n\n")
                    
                    f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                    f.write(f"Алгоритм: {self.current_schedule.algorithm_name}\n")
                    if self.fixed_days:
                        f.write(f"Фиксированные дни: {', '.join(sorted(self.fixed_days))}\n")
                    f.write("\n")
                    
                    # Расписание
                    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][:self.days_count]
                    all_places = []
                    for place, count in self.places_config.items():
                        all_places.extend([place] * count)
                        
                    for day_idx, day in enumerate(days):
                        f.write(f"\n{'='*40}\n")
                        day_header = f"{days[day_idx].upper()}"
                        if day in self.fixed_days:
                            day_header += " [📌 ФИКСИРОВАННЫЙ]"
                        f.write(f"{day_header}\n")
                        f.write(f"{'='*40}\n\n")
                        
                        for place_idx, place in enumerate(all_places):
                            if place_idx < len(self.current_schedule.schedule[day_idx]):
                                child = self.current_schedule.schedule[day_idx][place_idx]
                                if child:
                                    child_info = f"{place}: {child.name} ({child.health_status})"
                                    if day in self.fixed_days:
                                        child_info += " [ФИКС]"
                                    f.write(child_info + "\n")
                                else:
                                    f.write(f"{place}: —\n")
                                    
                    # Статистика
                    f.write(f"\n\n{'='*60}\n")
                    f.write("СТАТИСТИКА\n")
                    f.write(f"{'='*60}\n\n")
                    
                    for name, duties in sorted(self.current_schedule.distribution.items()):
                        f.write(f"{name}: {duties} дежурств\n")
                        
                QMessageBox.information(self, "Успех", f"Расписание экспортировано в:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
                
    def load_schedule_file(self):
        """Загрузить расписание из файла"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Загрузить расписание",
            "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Диалог для выбора фиксированных дней
                dialog = QDialog(self)
                dialog.setWindowTitle("📅 Выберите фиксированные дни")
                dialog.setModal(True)
                dialog.setMinimumWidth(400)
                
                layout = QVBoxLayout(dialog)
                
                info_label = QLabel("""
                <b>Фиксированные дни</b> - это дни, которые нельзя будет редактировать.<br>
                Они будут отмечены значком 📌 и иметь серый цвет.
                """)
                info_label.setWordWrap(True)
                layout.addWidget(info_label)
                
                # Виджет с флажками дней
                days_widget = QWidget()
                days_layout = QGridLayout(days_widget)
                
                self.schedule_days_checkboxes = {}
                days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
                for i, day in enumerate(days):
                    checkbox = QCheckBox(f"{day} 📌")
                    checkbox.setChecked(day in self.fixed_days)
                    self.schedule_days_checkboxes[day] = checkbox
                    days_layout.addWidget(checkbox, i // 4, i % 4)
                    
                layout.addWidget(days_widget)
                
                # Кнопки
                buttons = QDialogButtonBox(
                    QDialogButtonBox.StandardButton.Ok | 
                    QDialogButtonBox.StandardButton.Cancel
                )
                
                def load_and_close():
                    # Определяем выбранные дни как фиксированные
                    selected_days = [day for day, cb in self.schedule_days_checkboxes.items() 
                                    if cb.isChecked()]
                    self.fixed_days = set(selected_days)
                    
                    # Обновляем статистику и интерфейс
                    self.update_stats()
                    if self.current_schedule:
                        self.display_schedule_result(self.current_schedule)
                    
                    # Сохраняем изменения
                    self.save_settings()
                    
                    QMessageBox.information(
                        self, "Успех", 
                        f"Расписание загружено. Фиксированные дни: {', '.join(selected_days) if selected_days else 'нет'}"
                    )
                    dialog.accept()
                
                buttons.accepted.connect(load_and_close)
                buttons.rejected.connect(dialog.reject)
                layout.addWidget(buttons)
                
                dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # Установка шрифта
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    
    # Создание и запуск приложения
    window = DutyScheduleApp()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
