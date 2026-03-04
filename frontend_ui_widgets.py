# frontend_ui_widgets.py
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import traceback
from datetime import datetime
import json
import webbrowser
import os

# ========== СТИЛИ И ЦВЕТА ==========
class AppTheme:
    """Темы приложения"""
    
    @staticmethod
    def get_theme(theme_name):
        themes = {
            "light": AppTheme.light_theme(),
            "dark": AppTheme.dark_theme(),
            "mixed": AppTheme.mixed_theme()
        }
        return themes.get(theme_name, AppTheme.light_theme())
    
    @staticmethod
    def light_theme():
        return {
            "bg_primary": "#FFFFFF",
            "bg_secondary": "#F8F9FA",
            "bg_card": "#FFFFFF",
            "text_primary": "#212529",
            "text_secondary": "#6C757D",
            "text_on_primary": "#FFFFFF",
            "border": "#DEE2E6",
            "primary": "#0D6EFD",
            "primary_hover": "#0B5ED7",
            "success": "#198754",
            "warning": "#FFC107",
            "danger": "#DC3545",
            "info": "#0DCAF0",
            "health_healthy": "#198754",
            "health_recovering": "#FD7E14",
            "health_sick": "#DC3545",
            "fixed_day": "#E9ECEF"
        }
    
    @staticmethod
    def dark_theme():
        return {
            "bg_primary": "#121212",
            "bg_secondary": "#1E1E1E",
            "bg_card": "#2D2D2D",
            "text_primary": "#E9ECEF",
            "text_secondary": "#ADB5BD",
            "text_on_primary": "#FFFFFF",
            "border": "#495057",
            "primary": "#0D6EFD",
            "primary_hover": "#3D8BFD",
            "success": "#12B886",
            "warning": "#FFD43B",
            "danger": "#FA5252",
            "info": "#22B8CF",
            "health_healthy": "#12B886",
            "health_recovering": "#FD7E14",
            "health_sick": "#FA5252",
            "fixed_day": "#495057"
        }
    
    @staticmethod
    def mixed_theme():
        return {
            "bg_primary": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2B32B2, stop:1 #1488CC)",
            "bg_secondary": "rgba(255, 255, 255, 0.95)",
            "bg_card": "rgba(255, 255, 255, 0.98)",
            "text_primary": "#212529",
            "text_secondary": "#6C757D",
            "text_on_primary": "#FFFFFF",
            "border": "rgba(13, 110, 253, 0.3)",
            "primary": "#0D6EFD",
            "primary_hover": "#0B5ED7",
            "success": "#198754",
            "warning": "#FFC107",
            "danger": "#DC3545",
            "info": "#0DCAF0",
            "health_healthy": "#198754",
            "health_recovering": "#FD7E14",
            "health_sick": "#DC3545",
            "fixed_day": "rgba(233, 236, 239, 0.7)"
        }

# ========== ВСПОМОГАТЕЛЬНЫЕ ВИДЖЕТЫ ==========
class ModernButton(QPushButton):
    """Современная кнопка"""
    def __init__(self, text="", icon="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        if icon:
            self.setText(f"{icon} {text}")

class ModernCard(QFrame):
    """Карточка с современным дизайном"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)

class SettingsDialog(QDialog):
    """Диалог настройки дней с индикатором фиксации"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 Настройка дней")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Информация о фиксированных днях
        if self.parent().fixed_days:
            fixed_info = QLabel(f"📌 Фиксированные дни: {', '.join(sorted(self.parent().fixed_days))}")
            fixed_info.setStyleSheet("color: #0D6EFD; font-weight: bold; padding: 5px; background-color: #E9ECEF; border-radius: 5px;")
            layout.addWidget(fixed_info)
        
        # Количество дней
        days_group = QGroupBox("📅 Дни недели")
        days_layout = QVBoxLayout(days_group)
        
        days_widget = QWidget()
        days_hbox = QHBoxLayout(days_widget)
        days_hbox.addWidget(QLabel("Количество дней:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 7)
        self.days_spin.setValue(self.parent().days_count)
        days_hbox.addWidget(self.days_spin)
        days_hbox.addStretch()
        days_layout.addWidget(days_widget)
        
        # Индикатор фиксации дней
        fix_info = QLabel("⚠️ Фиксированные дни нельзя редактировать")
        fix_info.setStyleSheet("color: #FD7E14; font-size: 12px; padding: 5px;")
        fix_info.setVisible(bool(self.parent().fixed_days))
        days_layout.addWidget(fix_info)
        
        layout.addWidget(days_group)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

class StudentDialog(QDialog):
    """Диалог добавления/редактирования ученика"""
    def __init__(self, student_data=None, parent=None):
        super().__init__(parent)
        self.student_data = student_data or {}
        title = "✏️ Редактировать ученика" if student_data else "➕ Добавить ученика"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Имя
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("ФИО:"))
        self.name_edit = QLineEdit(self.student_data.get('name', ''))
        self.name_edit.setPlaceholderText("Иванов Иван Иванович")
        name_layout.addWidget(self.name_edit, 1)
        layout.addLayout(name_layout)
        
        # Статус здоровья
        health_layout = QHBoxLayout()
        health_layout.addWidget(QLabel("Статус здоровья:"))
        self.health_combo = QComboBox()
        self.health_combo.addItems(["✅ Здоров", "🔄 Недавно болел", "🛌 Болеет"])
        
        # Устанавливаем текущее значение
        health_status = self.student_data.get('health_status', 'здоров')
        if health_status == "здоров":
            self.health_combo.setCurrentIndex(0)
        elif health_status in ["недавно болел", "недавно болела"]:
            self.health_combo.setCurrentIndex(1)
        else:
            self.health_combo.setCurrentIndex(2)
            
        health_layout.addWidget(self.health_combo, 1)
        layout.addLayout(health_layout)
        
        # Дни недели
        days_group = QGroupBox("📅 Доступность по дням")
        days_grid = QGridLayout(days_group)
        
        self.day_checkboxes = {}
        days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        for i, day in enumerate(days):
            checkbox = QCheckBox(day)
            # Устанавливаем состояние из данных или по умолчанию True
            default_status = self.student_data.get('days', {}).get(day, "доступен")
            checkbox.setChecked(default_status == "доступен")
            
            # Делаем недоступным если день фиксированный
            if day in self.parent().fixed_days:
                checkbox.setEnabled(False)
                checkbox.setToolTip(f"День {day} фиксирован - редактирование недоступно")
                checkbox.setText(f"{day} 📌")
            
            self.day_checkboxes[day] = checkbox
            days_grid.addWidget(checkbox, i // 4, i % 4)
        
        layout.addWidget(days_group)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО ученика")
            return
        self.accept()
        
    def get_data(self):
        # Конвертируем статус здоровья
        health_mapping = {
            "✅ Здоров": "здоров",
            "🔄 Недавно болел": "недавно болел",
            "🛌 Болеет": "болеет"
        }
        
        # Собираем дни
        days = {}
        for day, checkbox in self.day_checkboxes.items():
            if checkbox.isEnabled():  # Только для нефиксированных дней
                days[day] = "доступен" if checkbox.isChecked() else "недоступен"
            else:
                # Для фиксированных дней сохраняем старое значение
                days[day] = self.student_data.get('days', {}).get(day, "доступен")
            
        return {
            'name': self.name_edit.text().strip(),
            'health_status': health_mapping.get(self.health_combo.currentText(), 'здоров'),
            'days': days
        }

class PlacesDialog(QDialog):
    """Диалог управления местами дежурств"""
    def __init__(self, places_config=None, parent=None):
        super().__init__(parent)
        self.places_config = places_config or {}
        self.setWindowTitle("📍 Места дежурств")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Список мест
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container = QWidget()
        self.places_layout = QVBoxLayout(container)
        
        self.place_widgets = []
        for place, count in self.places_config.items():
            self.add_place_widget(place, count)
            
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        add_btn = ModernButton("Добавить место", "➕")
        add_btn.clicked.connect(lambda: self.add_place_widget("Новое место", 1))
        buttons_layout.addWidget(add_btn)
        
        self.remove_btn = ModernButton("Удалить выбранное", "🗑️")
        self.remove_btn.clicked.connect(self.remove_selected_place)
        self.remove_btn.setEnabled(False)
        buttons_layout.addWidget(self.remove_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Основные кнопки
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        
    def add_place_widget(self, place_name, count):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Радиокнопка для выбора
        radio = QRadioButton()
        radio.toggled.connect(self.update_remove_button)
        
        # Название места
        name_edit = QLineEdit(place_name)
        name_edit.setPlaceholderText("Название места")
        
        # Количество
        count_spin = QSpinBox()
        count_spin.setRange(1, 10)
        count_spin.setValue(count)
        
        layout.addWidget(radio)
        layout.addWidget(name_edit, 1)
        layout.addWidget(QLabel("мест:"))
        layout.addWidget(count_spin)
        
        self.place_widgets.append({
            'widget': widget,
            'radio': radio,
            'name_edit': name_edit,
            'count_spin': count_spin
        })
        self.places_layout.addWidget(widget)
        
    def update_remove_button(self):
        selected = any(w['radio'].isChecked() for w in self.place_widgets)
        self.remove_btn.setEnabled(selected)
        
    def remove_selected_place(self):
        for i, widget_data in enumerate(self.place_widgets):
            if widget_data['radio'].isChecked():
                widget_data['widget'].deleteLater()
                self.place_widgets.pop(i)
                self.update_remove_button()
                break
                
    def get_config(self):
        config = {}
        for widget_data in self.place_widgets:
            name = widget_data['name_edit'].text().strip()
            count = widget_data['count_spin'].value()
            if name:  # Не добавляем пустые названия
                config[name] = count
        return config

class AboutDialog(QDialog):
    """Диалог о программе"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ℹ️ О программе")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("DutyMaster Pro")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0D6EFD;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Версия
        version = QLabel("Версия 2.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Разработчики
        devs_label = QLabel("""
        <h3>Разработчик:</h3>
        <p>• Скачков Андрей Юрьевич (практикант)</p>
        
        <h3>Организация:</h3>
        <p>Могилевский Государственный Технологический Колледж</p>
        
        <h3>Пару слов:</h3>
        <p>Моя цель при разработке проекта была проста - не разработать иновацию, не сделать то, чего нету, а именно решить текущую проблему в нашем колледже, которая существовало. а получилось ли или нет - знать лишь вам, увидете ли вы эту запись или нет. Да, скажу сразу, при разработке этого приложения я активно пользовался нейросетью deepseek, так как моя цель была создать приложение быстро, которая решить проблему, пусь не так качественно, не так красиво, с косяками, но это лучше чем неиметь вообще нечего. Да по сути весь этот код написать полностью deepseek, я лишь был в роли переводчика и состоявлял правильное ТЗ для него. Я знаю, что в приложении есть ещё много косяков, по типу не сохраняется цвет политры при выходе из приложения и есть определенные ошибки, которые приводят к краху приложения, но я старался все их залатать, все те, что я смог отследить и все те, что что смог исправить я исправил. На разработку этого проекта у меня ушло около 3 ней примерно по 6 часов разработки каждый день и надеюсь это чего-то стоило. Если ты это читаешь, то спасибо что пользуешься этим приложением, значит я не зря старался!</p>
        """)
        devs_label.setWordWrap(True)
        layout.addWidget(devs_label)
        
        # Сайт
        site_btn = ModernButton("🌐 Перейти на сайт МГТК")
        site_btn.clicked.connect(lambda: webbrowser.open("https://www.mgtk.mogilev.by/"))
        layout.addWidget(site_btn)
        
        # Кнопка закрытия
        close_btn = ModernButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
