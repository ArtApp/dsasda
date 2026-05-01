"""
GUI модуль приложения Project-to-PProg.
Интерфейс на базе PySide6/PyQt6 для интерактивного редактирования конфигурации.
"""

from .main_window import MainWindow, run_gui, DeviceDialog, PartitionDialog

__all__ = ['MainWindow', 'run_gui', 'DeviceDialog', 'PartitionDialog']