"""
GUI модуль приложения Project-to-PProg.
Интерфейс на базе PySide6/PyQt6 для интерактивного редактирования конфигурации.
"""

from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QFileDialog, QTextEdit, QTableWidget,
        QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QFormLayout,
        QLineEdit, QComboBox, QSpinBox, QCheckBox, QMessageBox, QTabWidget,
        QMenuBar, QMenu, QAction, QStatusBar, QToolBar, QDialog, QDialogButtonBox
    )
    from PySide6.QtCore import Qt, QSettings, Signal, QObject
    from PySide6.QtGui import QAction, QIcon, QKeySequence
    PYSIDE_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QFileDialog, QTextEdit, QTableWidget,
            QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout,
            QLineEdit, QComboBox, QSpinBox, QCheckBox, QMessageBox, QTabWidget,
            QMenuBar, QMenu, QAction, QStatusBar, QToolBar, QDialog, QDialogButtonBox
        )
        from PyQt6.QtCore import Qt, QSettings, pyqtSignal as Signal, QObject
        from PyQt6.QtGui import QAction, QIcon, QKeySequence
        PYSIDE_AVAILABLE = True
    except ImportError:
        PYSIDE_AVAILABLE = False

from data.models import Configuration, Device, Partition, Zone, Relay, ZoneType, RelayProgram
from modules.pdf_parser import PDFParser, parse_text_project
from modules.exporter import export_configuration


class DeviceDialog(QDialog):
    """Диалог добавления/редактирования устройства."""
    
    def __init__(self, device: Optional[Device] = None, parent=None):
        super().__init__(parent)
        self.device = device
        self.setWindowTitle("Добавить устройство" if device is None else "Редактировать устройство")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Адрес
        self.address_edit = QSpinBox()
        self.address_edit.setRange(1, 254)
        self.address_edit.setValue(device.address if device else 1)
        layout.addRow("Адрес:", self.address_edit)
        
        # Тип устройства
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "S2000M console",
            "S2000-KDL-2I controller",
            "S2000-SP2 relay module",
            "S2000-BKI interface module",
            "RS-200T network converter"
        ])
        if device:
            index = self.type_combo.findText(device.device_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        layout.addRow("Тип:", self.type_combo)
        
        # Описание
        self.desc_edit = QLineEdit()
        if device:
            self.desc_edit.setText(device.description)
        layout.addRow("Описание:", self.desc_edit)
        
        # Версия
        self.version_edit = QLineEdit()
        if device and device.version:
            self.version_edit.setText(device.version)
        layout.addRow("Версия:", self.version_edit)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_device(self) -> Device:
        """Получить устройство из диалога."""
        return Device(
            address=self.address_edit.value(),
            device_type=self.type_combo.currentText(),
            description=self.desc_edit.text(),
            version=self.version_edit.text() or None
        )


class PartitionDialog(QDialog):
    """Диалог добавления/редактирования раздела."""
    
    def __init__(self, partition: Optional[Partition] = None, parent=None):
        super().__init__(parent)
        self.partition = partition
        self.setWindowTitle("Добавить раздел" if partition is None else "Редактировать раздел")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # ID раздела
        self.id_edit = QSpinBox()
        self.id_edit.setRange(1, 255)
        self.id_edit.setValue(partition.partition_id if partition else 1)
        layout.addRow("ID раздела:", self.id_edit)
        
        # Название
        self.name_edit = QLineEdit()
        if partition:
            self.name_edit.setText(partition.name)
        layout.addRow("Название:", self.name_edit)
        
        # Включен
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(partition.enabled if partition else True)
        layout.addRow("Включен:", self.enabled_check)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_partition(self) -> Partition:
        """Получить раздел из диалога."""
        return Partition(
            partition_id=self.id_edit.value(),
            name=self.name_edit.text(),
            enabled=self.enabled_check.isChecked()
        )


class MainWindow(QMainWindow):
    """Главное окно приложения Project-to-PProg."""
    
    def __init__(self):
        super().__init__()
        self.configuration = Configuration()
        self.parser = PDFParser()
        
        self.setWindowTitle("Project-to-PProg - Конфигуратор Болид")
        self.setMinimumSize(1200, 800)
        
        self._init_ui()
        self._init_menu()
        self._init_status_bar()
    
    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        
        # Разделитель
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Левая панель - дерево проекта
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Вкладки для устройств, разделов, реле
        self.tabs = QTabWidget()
        
        # Вкладка устройств
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(5)
        self.devices_table.setHorizontalHeaderLabels(["Адрес", "Тип", "Описание", "Версия", "Статус"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.devices_table.doubleClicked.connect(self._edit_device)
        left_layout.addWidget(self.devices_table)
        
        # Кнопки управления устройствами
        device_buttons = QHBoxLayout()
        self.btn_add_device = QPushButton("Добавить")
        self.btn_add_device.clicked.connect(self._add_device)
        self.btn_remove_device = QPushButton("Удалить")
        self.btn_remove_device.clicked.connect(self._remove_device)
        device_buttons.addWidget(self.btn_add_device)
        device_buttons.addWidget(self.btn_remove_device)
        device_buttons.addStretch()
        left_layout.addLayout(device_buttons)
        
        devices_widget = QWidget()
        devices_layout = QVBoxLayout(devices_widget)
        devices_layout.setContentsMargins(0, 0, 0, 0)
        devices_layout.addWidget(self.devices_table)
        devices_layout.addLayout(device_buttons)
        
        # Вкладка разделов
        self.partitions_table = QTableWidget()
        self.partitions_table.setColumnCount(3)
        self.partitions_table.setHorizontalHeaderLabels(["ID", "Название", "Зон"])
        self.partitions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.partitions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.partitions_table.doubleClicked.connect(self._edit_partition)
        
        partition_buttons = QHBoxLayout()
        self.btn_add_partition = QPushButton("Добавить")
        self.btn_add_partition.clicked.connect(self._add_partition)
        self.btn_remove_partition = QPushButton("Удалить")
        self.btn_remove_partition.clicked.connect(self._remove_partition)
        partition_buttons.addWidget(self.btn_add_partition)
        partition_buttons.addWidget(self.btn_remove_partition)
        partition_buttons.addStretch()
        
        partitions_widget = QWidget()
        partitions_layout = QVBoxLayout(partitions_widget)
        partitions_layout.setContentsMargins(0, 0, 0, 0)
        partitions_layout.addWidget(self.partitions_table)
        partitions_layout.addLayout(partition_buttons)
        
        # Вкладка реле
        self.relays_table = QTableWidget()
        self.relays_table.setColumnCount(6)
        self.relays_table.setHorizontalHeaderLabels(["Адрес", "Реле", "Программа", "Задержка", "Время", "Описание"])
        self.relays_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.relays_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        relay_buttons = QHBoxLayout()
        self.btn_refresh_relays = QPushButton("Обновить")
        self.btn_refresh_relays.clicked.connect(self._refresh_relays)
        relay_buttons.addWidget(self.btn_refresh_relays)
        relay_buttons.addStretch()
        
        relays_widget = QWidget()
        relays_layout = QVBoxLayout(relays_widget)
        relays_layout.setContentsMargins(0, 0, 0, 0)
        relays_layout.addWidget(self.relays_table)
        relays_layout.addLayout(relay_buttons)
        
        # Добавляем вкладки
        self.tabs.addTab(devices_widget, "Устройства")
        self.tabs.addTab(partitions_widget, "Разделы")
        self.tabs.addTab(relays_widget, "Реле")
        
        left_layout.addWidget(self.tabs)
        splitter.addWidget(left_panel)
        
        # Правая панель - предпросмотр и логи
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Предпросмотр конфигурации
        preview_group = QGroupBox("Предпросмотр конфигурации")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFontFamily("Courier New")
        preview_layout.addWidget(self.preview_text)
        
        right_layout.addWidget(preview_group)
        
        # Логи
        log_group = QGroupBox("Журнал событий")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        right_layout.addWidget(log_group)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
    
    def _init_menu(self):
        """Инициализация меню."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        open_action = QAction("Открыть PDF...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_pdf)
        file_menu.addAction(open_action)
        
        save_action = QAction("Сохранить конфигурацию...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_configuration)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Правка
        edit_menu = menubar.addMenu("Правка")
        
        add_device_action = QAction("Добавить устройство", self)
        add_device_action.triggered.connect(self._add_device)
        edit_menu.addAction(add_device_action)
        
        add_partition_action = QAction("Добавить раздел", self)
        add_partition_action.triggered.connect(self._add_partition)
        edit_menu.addAction(add_partition_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction("Очистить всё", self)
        clear_action.triggered.connect(self._clear_all)
        edit_menu.addAction(clear_action)
        
        # Инструменты
        tools_menu = menubar.addMenu("Инструменты")
        
        validate_action = QAction("Валидировать конфигурацию", self)
        validate_action.triggered.connect(self._validate_configuration)
        tools_menu.addAction(validate_action)
        
        preview_action = QAction("Обновить предпросмотр", self)
        preview_action.triggered.connect(self._update_preview)
        tools_menu.addAction(preview_action)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе...", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _init_status_bar(self):
        """Инициализация строки состояния."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Готов к работе")
    
    def _log(self, message: str):
        """Добавить сообщение в журнал."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def _open_pdf(self):
        """Открыть PDF файл."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть PDF проект",
            "",
            "PDF файлы (*.pdf);;Все файлы (*.*)"
        )
        
        if file_path:
            self._log(f"Открытие файла: {file_path}")
            try:
                result = self.parser.parse_file(file_path)
                self.configuration = result.configuration
                
                if result.errors:
                    for error in result.errors:
                        self._log(f"Ошибка: {error}")
                        QMessageBox.warning(self, "Ошибка парсинга", error)
                
                if result.warnings:
                    for warning in result.warnings:
                        self._log(f"Предупреждение: {warning}")
                
                self._refresh_all_tables()
                self._update_preview()
                self.statusbar.showMessage(f"Загружено: {file_path}")
                self._log(f"Загружено устройств: {len(self.configuration.devices)}")
                self._log(f"Загружено разделов: {len(self.configuration.partitions)}")
                
            except Exception as e:
                self._log(f"Ошибка при загрузке: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл:\n{e}")
    
    def _save_configuration(self):
        """Сохранить конфигурацию в файл."""
        if not self.configuration.devices:
            QMessageBox.warning(self, "Предупреждение", "Конфигурация пуста. Добавьте устройства.")
            return
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить конфигурацию",
            "configuration.txt",
            "TXT файлы (*.txt);;JSON файлы (*.json);;Excel файлы (*.xlsx);;Все файлы (*.*)"
        )
        
        if file_path:
            # Определяем формат по расширению
            if file_path.endswith(".json"):
                format = "json"
            elif file_path.endswith(".xlsx"):
                format = "excel"
            else:
                format = "txt"
            
            self._log(f"Сохранение в {format.upper()} формат: {file_path}")
            
            try:
                success = export_configuration(self.configuration, file_path, format)
                if success:
                    self._log("Конфигурация успешно сохранена")
                    self.statusbar.showMessage(f"Сохранено: {file_path}")
                    QMessageBox.information(self, "Успех", f"Конфигурация сохранена в:\n{file_path}")
                else:
                    self._log("Ошибка при сохранении")
                    QMessageBox.critical(self, "Ошибка", "Не удалось сохранить конфигурацию")
            except Exception as e:
                self._log(f"Ошибка при сохранении: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить конфигурацию:\n{e}")
    
    def _refresh_all_tables(self):
        """Обновить все таблицы."""
        self._refresh_devices_table()
        self._refresh_partitions_table()
        self._refresh_relays_table()
    
    def _refresh_devices_table(self):
        """Обновить таблицу устройств."""
        self.devices_table.setRowCount(0)
        for device in self.configuration.devices:
            row = self.devices_table.rowCount()
            self.devices_table.insertRow(row)
            self.devices_table.setItem(row, 0, QTableWidgetItem(str(device.address)))
            self.devices_table.setItem(row, 1, QTableWidgetItem(device.device_type))
            self.devices_table.setItem(row, 2, QTableWidgetItem(device.description))
            self.devices_table.setItem(row, 3, QTableWidgetItem(device.version or ""))
            self.devices_table.setItem(row, 4, QTableWidgetItem(device.status.value))
    
    def _refresh_partitions_table(self):
        """Обновить таблицу разделов."""
        self.partitions_table.setRowCount(0)
        for partition in self.configuration.partitions:
            row = self.partitions_table.rowCount()
            self.partitions_table.insertRow(row)
            self.partitions_table.setItem(row, 0, QTableWidgetItem(str(partition.partition_id)))
            self.partitions_table.setItem(row, 1, QTableWidgetItem(partition.name))
            self.partitions_table.setItem(row, 2, QTableWidgetItem(str(len(partition.zones))))
    
    def _refresh_relays_table(self):
        """Обновить таблицу реле."""
        self.relays_table.setRowCount(0)
        for relay in self.configuration.relays:
            row = self.relays_table.rowCount()
            self.relays_table.insertRow(row)
            self.relays_table.setItem(row, 0, QTableWidgetItem(str(relay.device_address)))
            self.relays_table.setItem(row, 1, QTableWidgetItem(str(relay.relay_number)))
            program_name = relay.program.name if hasattr(relay.program, 'name') else str(relay.program)
            self.relays_table.setItem(row, 2, QTableWidgetItem(program_name))
            self.relays_table.setItem(row, 3, QTableWidgetItem(str(relay.delay)))
            self.relays_table.setItem(row, 4, QTableWidgetItem(str(relay.activation_time)))
            self.relays_table.setItem(row, 5, QTableWidgetItem(relay.description))
    
    def _refresh_relays(self):
        """Обновить реле из парсера."""
        self._refresh_relays_table()
        self._log("Таблица реле обновлена")
    
    def _add_device(self):
        """Добавить устройство."""
        dialog = DeviceDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            device = dialog.get_device()
            
            # Проверка на дубликат адреса
            existing = self.configuration.get_device_by_address(device.address)
            if existing:
                QMessageBox.warning(
                    self,
                    "Дубликат адреса",
                    f"Устройство с адресом {device.address} уже существует."
                )
                return
            
            self.configuration.add_device(device)
            self._refresh_devices_table()
            self._update_preview()
            self._log(f"Добавлено устройство: адрес {device.address}, тип {device.device_type}")
    
    def _edit_device(self, index):
        """Редактировать устройство."""
        row = index.row()
        if row < 0 or row >= len(self.configuration.devices):
            return
        
        device = self.configuration.devices[row]
        dialog = DeviceDialog(device, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_device = dialog.get_device()
            
            # Проверка на дубликат адреса (если адрес изменился)
            if new_device.address != device.address:
                existing = self.configuration.get_device_by_address(new_device.address)
                if existing:
                    QMessageBox.warning(
                        self,
                        "Дубликат адреса",
                        f"Устройство с адресом {new_device.address} уже существует."
                    )
                    return
            
            # Удаляем старое и добавляем новое
            self.configuration.devices.remove(device)
            self.configuration.add_device(new_device)
            self._refresh_devices_table()
            self._update_preview()
            self._log(f"Обновлено устройство: адрес {new_device.address}")
    
    def _remove_device(self):
        """Удалить устройство."""
        current_row = self.devices_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите устройство для удаления")
            return
        
        device = self.configuration.devices[current_row]
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить устройство с адресом {device.address}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.configuration.devices.remove(device)
            self._refresh_devices_table()
            self._update_preview()
            self._log(f"Удалено устройство: адрес {device.address}")
    
    def _add_partition(self):
        """Добавить раздел."""
        dialog = PartitionDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            partition = dialog.get_partition()
            
            # Проверка на дубликат ID
            existing = self.configuration.get_partition_by_id(partition.partition_id)
            if existing:
                QMessageBox.warning(
                    self,
                    "Дубликат ID",
                    f"Раздел с ID {partition.partition_id} уже существует."
                )
                return
            
            self.configuration.add_partition(partition)
            self._refresh_partitions_table()
            self._update_preview()
            self._log(f"Добавлен раздел: {partition.name}")
    
    def _edit_partition(self, index):
        """Редактировать раздел."""
        row = index.row()
        if row < 0 or row >= len(self.configuration.partitions):
            return
        
        partition = self.configuration.partitions[row]
        dialog = PartitionDialog(partition, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_partition = dialog.get_partition()
            
            if new_partition.partition_id != partition.partition_id:
                existing = self.configuration.get_partition_by_id(new_partition.partition_id)
                if existing:
                    QMessageBox.warning(
                        self,
                        "Дубликат ID",
                        f"Раздел с ID {new_partition.partition_id} уже существует."
                    )
                    return
            
            self.configuration.partitions.remove(partition)
            self.configuration.add_partition(new_partition)
            self._refresh_partitions_table()
            self._update_preview()
            self._log(f"Обновлен раздел: {new_partition.name}")
    
    def _remove_partition(self):
        """Удалить раздел."""
        current_row = self.partitions_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите раздел для удаления")
            return
        
        partition = self.configuration.partitions[current_row]
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить раздел '{partition.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.configuration.partitions.remove(partition)
            self._refresh_partitions_table()
            self._update_preview()
            self._log(f"Удален раздел: {partition.name}")
    
    def _update_preview(self):
        """Обновить предпросмотр конфигурации."""
        from datetime import datetime
        
        lines = []
        lines.append(f"; Проект: {self.configuration.project_name or 'Без названия'}")
        lines.append(f"; Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Устройств: {len(self.configuration.devices)}")
        lines.append(f"Разделов: {len(self.configuration.partitions)}")
        lines.append(f"Реле: {len(self.configuration.relays)}")
        lines.append("")
        
        if self.configuration.devices:
            lines.append("[УСТРОЙСТВА]")
            for device in self.configuration.devices:
                lines.append(f"  {device.address}: {device.device_type} - {device.description}")
            lines.append("")
        
        if self.configuration.partitions:
            lines.append("[РАЗДЕЛЫ]")
            for partition in self.configuration.partitions:
                lines.append(f"  {partition.partition_id}: {partition.name} ({len(partition.zones)} зон)")
            lines.append("")
        
        if self.configuration.relays:
            lines.append("[РЕЛЕ]")
            for relay in self.configuration.relays:
                lines.append(f"  SC{relay.device_address}-{relay.device_address + relay.relay_number - 1}: {relay.program.name}")
        
        self.preview_text.setText('\n'.join(lines))
    
    def _validate_configuration(self):
        """Валидировать конфигурацию."""
        errors = self.configuration.validate()
        
        if errors:
            error_text = "Найдены ошибки валидации:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Ошибки валидации", error_text)
            self._log(f"Валидация: найдено {len(errors)} ошибок")
        else:
            QMessageBox.information(self, "Валидация", "Конфигурация корректна. Ошибок не найдено.")
            self._log("Валидация: ошибок не найдено")
    
    def _clear_all(self):
        """Очистить всю конфигурацию."""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить всю конфигурацию?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.configuration = Configuration()
            self._refresh_all_tables()
            self._update_preview()
            self._log("Конфигурация очищена")
    
    def _show_about(self):
        """Показать информацию о программе."""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>Project-to-PProg</h2>"
            "<p>Инструмент автоматизации конфигурирования систем пожарной сигнализации «Болид».</p>"
            "<p><b>Версия:</b> 0.1.0</p>"
            "<p><b>Python:</b> 3.10+</p>"
            "<p><b>GUI:</b> PySide6 / PyQt6</p>"
            "<p>Автоматический парсинг PDF проектной документации,<br>"
            "интерактивный редактор конфигурации,<br>"
            "экспорт в форматы PProg (TXT, JSON, Excel).</p>"
        )


def run_gui():
    """Запустить GUI приложение."""
    if not PYSIDE_AVAILABLE:
        print("Ошибка: PySide6 или PyQt6 не установлены.")
        print("Установите: pip install PySide6")
        return False
    
    import sys
    app = QApplication(sys.argv)
    app.setApplicationName("Project-to-PProg")
    app.setOrganizationName("Bolid Automation")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
