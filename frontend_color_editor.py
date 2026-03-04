# frontend_color_editor.py
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import traceback
from datetime import datetime
import json
import webbrowser
import os
from frontend_ui_widgets import ModernButton, ModernCard, AppTheme

# Импортируем AboutDialog
from frontend_ui_widgets import AboutDialog

class ElementSelectorWidget(QWidget):
    """Виджет для выбора элемента интерфейса"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("Выберите тип элемента:")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Категории элементов
        self.categories_combo = QComboBox()
        self.categories_combo.addItems([
            "Все элементы",
            "Кнопки",
            "Текст",
            "Фон",
            "Рамки",
            "Заголовки",
            "Таблицы",
            "Вкладки",
            "Поля ввода"
        ])
        layout.addWidget(self.categories_combo)
        
        # Список элементов
        self.elements_list = QListWidget()
        self.elements_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.elements_list, 1)
        
        # Кнопка "Выбрать все"
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all_elements)
        layout.addWidget(self.select_all_btn)
        
    def select_all_elements(self):
        """Выбрать все элементы в списке"""
        self.elements_list.selectAll()
        
    def set_elements(self, elements):
        """Установить список элементов"""
        self.elements_list.clear()
        for element in elements:
            # ИСПРАВЛЕНИЕ 4: Добавляем описание к элементу
            description = f"{element['name']} ({element.get('text', 'без текста')})"
            item = QListWidgetItem(description)
            item.setData(Qt.ItemDataRole.UserRole, element)
            item.setToolTip(f"Тип: {element['type']}\nТекст: {element.get('text', 'нет')}\nПуть: {element.get('path', 'корень')}")
            self.elements_list.addItem(item)
            
    def get_selected_elements(self):
        """Получить выбранные элементы"""
        selected = []
        for item in self.elements_list.selectedItems():
            selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

class ColorEditorDialog(QDialog):
    """Диалог для выбора цветов интерфейса (переработанный)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("🎨 Редактор цветов интерфейса")
        self.setModal(True)
        self.setMinimumSize(1000, 700)
        
        # Сохраняем оригинальные настройки для отмены изменений
        self.original_colors = parent.custom_colors.copy() if hasattr(parent, 'custom_colors') else {}
        self.original_bg_color = parent.custom_bg_color if hasattr(parent, 'custom_bg_color') else None
        
        # Флаг для отслеживания изменений
        self.changes_applied = False
        self.temporary_styles = {}  # Хранит временные стили для отмены
        
        # Собираем список всех элементов интерфейса
        self.collect_ui_elements()
        
        self.setup_ui()
        
    def collect_ui_elements(self):
        """ИСПРАВЛЕНИЕ 1: Собрать список ВСЕХ элементов интерфейса приложения"""
        self.ui_elements = []
        
        # Получаем все окна приложения
        app = QApplication.instance()
        if app:
            windows = app.topLevelWindows()
            for window in windows:
                if window.isWidgetType():
                    widget = QWidget.find(window.winId())
                    if widget:
                        self.collect_all_widgets(widget, "Приложение")
        
        # Также собираем из главного окна
        self.collect_all_widgets(self.parent_app, "Главное окно")
        
        # Дополнительно собираем все виджеты из всех дочерних окон
        self.collect_all_child_widgets(self.parent_app, "Главное окно")
        
        # Группируем элементы по категориям
        self.categorized_elements = {
            "Все элементы": self.ui_elements,
            "Кнопки": [e for e in self.ui_elements if e['type'] == 'QPushButton'],
            "Текст": [e for e in self.ui_elements if e['type'] in ['QLabel', 'QCheckBox', 'QRadioButton']],
            "Фон": [e for e in self.ui_elements if e['type'] in ['QFrame', 'QWidget', 'QMainWindow']],
            "Рамки": [e for e in self.ui_elements if e['type'] in ['QFrame', 'QLineEdit', 'QTextEdit', 'QTableWidget', 'QListWidget']],
            "Заголовки": [e for e in self.ui_elements if 'title' in e['name'].lower() or 'заголовок' in e.get('text', '').lower()],
            "Таблицы": [e for e in self.ui_elements if e['type'] == 'QTableWidget'],
            "Вкладки": [e for e in self.ui_elements if e['type'] == 'QTabWidget'],
            "Поля ввода": [e for e in self.ui_elements if e['type'] in ['QLineEdit', 'QTextEdit', 'QComboBox', 'QSpinBox']]
        }
    
    def collect_all_widgets(self, widget, path=""):
        """Собрать все виджеты рекурсивно"""
        try:
            if not widget:
                return
                
            # Игнорируем некоторые служебные виджеты
            ignore_types = ['QDialog', 'QMenuBar', 'QStatusBar', 'QScrollBar', 'QProgressBar']
            widget_type = widget.metaObject().className()
            if widget_type in ignore_types:
                return
            
            # Добавляем виджет в список
            widget_name = widget.objectName() if widget.objectName() else widget_type
            full_name = f"{path}/{widget_name}" if path else widget_type
            
            element_info = {
                'widget': widget,
                'name': full_name,
                'type': widget_type,
                'path': path
            }
            
            # Для кнопок добавляем текст
            if isinstance(widget, QPushButton):
                element_info['text'] = widget.text()
                element_info['name'] = f"{full_name} - {widget.text()}"
            elif isinstance(widget, QLabel):
                element_info['text'] = widget.text()
            elif isinstance(widget, QLineEdit):
                element_info['placeholder'] = widget.placeholderText()
            elif isinstance(widget, QTabWidget):
                for i in range(widget.count()):
                    tab_text = widget.tabText(i)
                    element_info['text'] = tab_text
                    break
            elif isinstance(widget, QCheckBox):
                element_info['text'] = widget.text()
            elif isinstance(widget, QRadioButton):
                element_info['text'] = widget.text()
                
            self.ui_elements.append(element_info)
            
        except Exception as e:
            print(f"Ошибка при сборе виджета: {e}")
    
    def collect_all_child_widgets(self, widget, path=""):
        """Рекурсивно собрать все дочерние виджеты"""
        try:
            if not widget:
                return
                
            # Получаем всех детей
            children = widget.findChildren(QWidget)
            for child in children:
                if child and child != widget:
                    # Добавляем текущий виджет
                    self.collect_all_widgets(child, f"{path}/дочерний")
                    # Рекурсивно для его детей
                    self.collect_all_child_widgets(child, f"{path}/дочерний")
                    
        except Exception as e:
            print(f"Ошибка при сборе дочерних виджетов: {e}")
            
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("🎨 Редактор цветов интерфейса")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0D6EFD; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Основная область
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # Левая панель - выбор элементов
        left_panel = ModernCard()
        left_panel.setMinimumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # Селектор элементов
        self.element_selector = ElementSelectorWidget()
        self.element_selector.categories_combo.currentTextChanged.connect(self.update_elements_list)
        left_layout.addWidget(self.element_selector, 1)
        
        # Правая панель - настройки цвета
        right_panel = ModernCard()
        right_layout = QVBoxLayout(right_panel)
        
        # Выбор свойства для изменения
        property_label = QLabel("Выберите свойство для изменения:")
        property_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(property_label)
        
        self.property_combo = QComboBox()
        self.property_combo.addItems([
            "Фон (background-color)",
            "Текст (color)",
            "Рамка (border)",
            "Шрифт (font-family)",
            "Размер шрифта (font-size)"
        ])
        right_layout.addWidget(self.property_combo)
        
        # Палитра цветов
        colors_label = QLabel("🎨 Палитра цветов:")
        colors_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        right_layout.addWidget(colors_label)
        
        # Сетка с цветами
        colors_grid = QGridLayout()
        colors = [
            "#0D6EFD", "#198754", "#FFC107", "#DC3545", "#6C757D",
            "#0DCAF0", "#20C997", "#FD7E14", "#E83E8C", "#6610F2",
            "#FFFFFF", "#000000", "#E9ECEF", "#343A40", "#007BFF",
            "#17A2B8", "#28A745", "#FFC107", "#DC3545", "#6F42C1"
        ]
        
        for i, color in enumerate(colors):
            color_btn = QPushButton()
            color_btn.setFixedSize(40, 40)
            color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
            color_btn.clicked.connect(lambda checked, c=color: self.set_color(c))
            color_btn.setToolTip(color)
            colors_grid.addWidget(color_btn, i // 5, i % 5)
        
        right_layout.addLayout(colors_grid)
        
        # Произвольный цвет
        custom_label = QLabel("🎨 Произвольный цвет:")
        custom_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        right_layout.addWidget(custom_label)
        
        custom_layout = QHBoxLayout()
        
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(50, 50)
        self.color_preview.setStyleSheet("background-color: #0D6EFD; border: 2px solid #ccc; border-radius: 5px;")
        self.color_preview.setToolTip("Предпросмотр цвета")
        
        self.color_hex_edit = QLineEdit("#0D6EFD")
        self.color_hex_edit.setPlaceholderText("#RRGGBB")
        
        custom_color_btn = QPushButton("Выбрать цвет")
        custom_color_btn.clicked.connect(self.pick_custom_color)
        custom_color_btn.setToolTip("Открыть диалог выбора цвета")
        
        custom_layout.addWidget(self.color_preview)
        custom_layout.addWidget(self.color_hex_edit)
        custom_layout.addWidget(custom_color_btn)
        
        right_layout.addLayout(custom_layout)
        
        # Настройки шрифта (если выбрано свойство шрифта)
        self.font_widget = QWidget()
        font_layout = QVBoxLayout(self.font_widget)
        
        font_family_label = QLabel("Шрифт:")
        font_layout.addWidget(font_family_label)
        
        self.font_combo = QFontComboBox()
        font_layout.addWidget(self.font_combo)
        
        font_size_label = QLabel("Размер шрифта:")
        font_layout.addWidget(font_size_label)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(10)
        font_layout.addWidget(self.font_size_spin)
        
        right_layout.addWidget(self.font_widget)
        self.font_widget.setVisible(False)
        
        # Обновляем видимость виджета шрифта
        self.property_combo.currentTextChanged.connect(self.update_property_widget)
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        
        preview_btn = ModernButton("Показать изменения", "👁️")
        preview_btn.clicked.connect(self.preview_changes)
        preview_btn.setToolTip("Временный предпросмотр изменений")
        buttons_layout.addWidget(preview_btn)
        
        apply_btn = ModernButton("Сохранить", "💾")
        apply_btn.clicked.connect(self.apply_changes)
        apply_btn.setToolTip("Сохранить изменения навсегда")
        buttons_layout.addWidget(apply_btn)
        
        right_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        layout.addWidget(main_widget, 1)
        
        # Кнопка закрытия
        close_btn = ModernButton("Закрыть редактор", "❌")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("background-color: #DC3545; color: white; font-weight: bold;")
        close_btn.setToolTip("Закрыть редактор")
        layout.addWidget(close_btn)
        
        # Инициализация списка элементов
        self.update_elements_list("Все элементы")
        
    def update_elements_list(self, category):
        """Обновить список элементов по категории"""
        elements = self.categorized_elements.get(category, [])
        print(f"Найдено элементов в категории '{category}': {len(elements)}")
        self.element_selector.set_elements(elements)
        
    def update_property_widget(self, property_text):
        """Обновить виджеты в зависимости от выбранного свойства"""
        if "шрифт" in property_text.lower():
            self.font_widget.setVisible(True)
        else:
            self.font_widget.setVisible(False)
            
    def pick_custom_color(self):
        """Выбрать произвольный цвет"""
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            self.color_hex_edit.setText(color_hex)
            self.color_preview.setStyleSheet(f"background-color: {color_hex}; border: 2px solid #ccc; border-radius: 5px;")
            
    def set_color(self, color_hex):
        """Установить выбранный цвет"""
        self.color_hex_edit.setText(color_hex)
        self.color_preview.setStyleSheet(f"background-color: {color_hex}; border: 2px solid #ccc; border-radius: 5px;")
        
    def preview_changes(self):
        """ИСПРАВЛЕНИЕ 2: Показать предпросмотр изменений без блокировки"""
        selected_elements = self.element_selector.get_selected_elements()
        if not selected_elements:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один элемент для изменения")
            return
            
        property_type = self.property_combo.currentText()
        
        # Сохраняем оригинальные стили перед предпросмотром
        for element in selected_elements:
            widget = element['widget']
            if widget not in self.temporary_styles:
                self.temporary_styles[widget] = widget.styleSheet()
        
        # Применяем изменения временно для предпросмотра
        for element in selected_elements:
            widget = element['widget']
            self.apply_property_to_widget(widget, property_type, preview=True)
        
        self.changes_applied = True
        QMessageBox.information(self, "Предпросмотр", 
                              f"Применено к {len(selected_elements)} элементам\n"
                              f"Свойство: {property_type}")
                              
    def apply_changes(self):
        """ИСПРАВЛЕНИЕ 3: Применить изменения с сохранением в файл"""
        selected_elements = self.element_selector.get_selected_elements()
        if not selected_elements:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один элемент для изменения")
            return
            
        property_type = self.property_combo.currentText()
        
        # Создаем новый словарь для custom_colors с правильными ключами
        new_custom_colors = {}
        
        for element in selected_elements:
            widget = element['widget']
            
            # Определяем ключ для сохранения
            widget_name = widget.objectName() if widget.objectName() else f"widget_{id(widget)}"
            
            if "шрифт" in property_type.lower():
                # Сохраняем настройки шрифта
                font_settings = {
                    'family': self.font_combo.currentFont().family(),
                    'size': self.font_size_spin.value()
                }
                new_custom_colors[f"font_{widget_name}"] = font_settings
            else:
                # Сохраняем цвет
                color_hex = self.color_hex_edit.text()
                # Определяем тип свойства для ключа
                if "фон" in property_type.lower():
                    new_custom_colors[f"bg_{widget_name}"] = color_hex
                elif "текст" in property_type.lower():
                    new_custom_colors[f"text_{widget_name}"] = color_hex
                elif "рамка" in property_type.lower():
                    new_custom_colors[f"border_{widget_name}"] = color_hex
            
            # Применяем к виджету (без preview)
            self.apply_property_to_widget(widget, property_type, preview=False)
        
        # Обновляем custom_colors в родительском приложении
        self.parent_app.custom_colors.update(new_custom_colors)
            
        # ИСПРАВЛЕНИЕ 3: Сохраняем настройки в файл
        self.parent_app.save_settings()
        
        # Очищаем временные стили
        self.temporary_styles.clear()
        
        QMessageBox.information(self, "Сохранено", 
                              f"Изменения применены к {len(selected_elements)} элементам и сохранены")
                              
    def apply_property_to_widget(self, widget, property_type, preview=False):
        """ИСПРАВЛЕНИЕ 2: Применить свойство к виджету без блокировки"""
        try:
            current_style = widget.styleSheet()
            
            if "фон" in property_type.lower():
                color = self.color_hex_edit.text()
                # Удаляем старые стили фона
                import re
                current_style = re.sub(r'background-color:[^;]*;?', '', current_style)
                current_style = re.sub(r'background:[^;]*;?', '', current_style)
                current_style += f"background-color: {color};"
                widget.setStyleSheet(current_style)
                    
            elif "текст" in property_type.lower():
                color = self.color_hex_edit.text()
                # Удаляем старые стили цвета текста
                import re
                current_style = re.sub(r'color:[^;]*;?', '', current_style)
                current_style += f"color: {color};"
                widget.setStyleSheet(current_style)
                    
            elif "рамка" in property_type.lower():
                color = self.color_hex_edit.text()
                # Удаляем старые стили рамки
                import re
                current_style = re.sub(r'border:[^;]*;?', '', current_style)
                current_style = re.sub(r'border-color:[^;]*;?', '', current_style)
                current_style += f"border: 2px solid {color};"
                widget.setStyleSheet(current_style)
                    
            elif "шрифт" in property_type.lower():
                font = QFont(self.font_combo.currentFont().family(), self.font_size_spin.value())
                widget.setFont(font)
                
        except Exception as e:
            print(f"Ошибка применения стиля: {e}")
    
    def accept(self):
        """ИСПРАВЛЕНИЕ 2: При закрытии редактора"""
        # Если были временные изменения (предпросмотр), сбрасываем их
        if self.changes_applied:
            self.reset_temporary_changes()
        
        super().accept()
    
    def reject(self):
        """ИСПРАВЛЕНИЕ 2: При отмене (крестик или Escape)"""
        # Всегда сбрасываем временные изменения
        if self.changes_applied:
            self.reset_temporary_changes()
        
        super().reject()
    
    def reset_temporary_changes(self):
        """Сбросить временные изменения"""
        for widget, original_style in self.temporary_styles.items():
            try:
                widget.setStyleSheet(original_style)
            except:
                pass
        self.temporary_styles.clear()
        self.changes_applied = False

class AppSettingsDialog(QDialog):
    """Диалог настроек приложения"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("⚙️ Настройки приложения")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Кнопка для открытия редактора цветов
        color_editor_btn = ModernButton("🎨 Редактор цветов интерфейса")
        color_editor_btn.setMinimumHeight(50)
        color_editor_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        color_editor_btn.clicked.connect(self.open_color_editor)
        color_editor_btn.setToolTip("Открыть редактор для изменения цветов всех элементов интерфейса")
        layout.addWidget(color_editor_btn)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Цвет фона
        color_group = QGroupBox("🎨 Цвет фона")
        color_layout = QVBoxLayout(color_group)
        
        self.color_btn = QPushButton("Выбрать цвет фона")
        self.color_btn.clicked.connect(self.choose_color)
        self.color_btn.setToolTip("Выбрать основной цвет фона приложения")
        color_layout.addWidget(self.color_btn)
        
        self.color_preview = QLabel("Текущий цвет")
        self.color_preview.setMinimumHeight(40)
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview.setToolTip("Текущий выбранный цвет фона")
        color_layout.addWidget(self.color_preview)
        
        # Загрузить текущий цвет
        if self.parent_app.custom_bg_color:
            self.update_color_preview(self.parent_app.custom_bg_color)
        
        layout.addWidget(color_group)
        
        # Версия
        version_group = QGroupBox("📋 Информация")
        version_layout = QVBoxLayout(version_group)
        
        # суммарная разработка = 3 дня
        version_label = QLabel("Версия приложения: 0.1.0")
        version_layout.addWidget(version_label)
        
        layout.addWidget(version_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        about_btn = ModernButton("О разработчиках", "ℹ️")
        about_btn.clicked.connect(self.show_about)
        about_btn.setToolTip("Информация о разработчиках приложения")
        buttons_layout.addWidget(about_btn)
        
        reset_btn = ModernButton("Сбросить настройки", "🔄")
        reset_btn.clicked.connect(self.reset_settings)
        reset_btn.setToolTip("Сбросить все настройки к заводским")
        buttons_layout.addWidget(reset_btn)
        
        layout.addLayout(buttons_layout)
        
        # Основные кнопки
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(self.save_settings)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        
    def open_color_editor(self):
        """Открыть редактор цветов"""
        try:
            color_dialog = ColorEditorDialog(self.parent_app)
            color_dialog.exec()
        except Exception as e:
            print(f"Ошибка открытия редактор цветов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактор цветов:\n{str(e)}")
        
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_preview(self.selected_color)
            
    def update_color_preview(self, color_hex):
        self.color_preview.setText(color_hex)
        self.color_preview.setStyleSheet(f"""
            background-color: {color_hex};
            color: {'white' if QColor(color_hex).lightness() < 128 else 'black'};
            border-radius: 5px;
        """)
        
    def show_about(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec()
        
    def reset_settings(self):
        reply = QMessageBox.question(
            self, "Сброс настроек",
            "Вы уверены, что хотите сбросить ВСЕ настройки к заводским?\n"
            "Это удалит: учеников, места дежурств, темы, цвета и фиксированные дни.\n"
            "Действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.parent_app.reset_to_default()
            self.accept()
            
    def save_settings(self):
        if hasattr(self, 'selected_color'):
            self.parent_app.custom_bg_color = self.selected_color
            self.parent_app.save_settings()
            self.parent_app.apply_theme()
        self.accept()
