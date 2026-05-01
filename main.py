"""
Главный модуль приложения Project-to-PProg.
Предоставляет основной API для работы с инструментом.
"""

from pathlib import Path
from typing import Optional

from data.models import Configuration
from data.equipment_db import get_device_info, EQUIPMENT_DATABASE
from modules.pdf_parser import PDFParser, parse_pdf_project, parse_text_project, ParseResult
from modules.exporter import PProgExporter, export_configuration


class ProjectToPProg:
    """Основной класс приложения Project-to-PProg."""
    
    def __init__(self):
        self.parser = PDFParser()
        self.configuration: Optional[Configuration] = None
        self.last_parse_result: Optional[ParseResult] = None
    
    def load_pdf(self, pdf_path: str | Path) -> ParseResult:
        """
        Загрузка и парсинг PDF файла проектной документации.
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            ParseResult с конфигурацией и списком предупреждений/ошибок
        """
        result = self.parser.parse_file(pdf_path)
        self.configuration = result.configuration
        self.last_parse_result = result
        return result
    
    def load_text(self, text: str, project_name: str = "Project") -> ParseResult:
        """
        Загрузка и парсинг текста проектной документации.
        
        Args:
            text: Текст проектной документации
            project_name: Имя проекта
            
        Returns:
            ParseResult с конфигурацией
        """
        result = self.parser.parse_text(text, project_name)
        self.configuration = result.configuration
        self.last_parse_result = result
        return result
    
    def export(self, output_path: str | Path, format: str = "txt") -> bool:
        """
        Экспорт конфигурации в файл.
        
        Args:
            output_path: Путь к выходному файлу
            format: Формат экспорта ("txt", "json", "excel")
            
        Returns:
            True если успешно, False иначе
        """
        if self.configuration is None:
            print("Ошибка: Конфигурация не загружена. Сначала вызовите load_pdf() или load_text().")
            return False
        
        return export_configuration(self.configuration, output_path, format)
    
    def get_equipment_list(self) -> dict:
        """
        Получить список всего оборудования из базы знаний.
        
        Returns:
            Словарь с оборудованием
        """
        return EQUIPMENT_DATABASE
    
    def validate_configuration(self) -> list[str]:
        """
        Валидация текущей конфигурации.
        
        Returns:
            Список ошибок валидации
        """
        if self.configuration is None:
            return ["Конфигурация не загружена"]
        
        return self.configuration.validate()
    
    def get_summary(self) -> dict:
        """
        Получить сводку по текущей конфигурации.
        
        Returns:
            Словарь со статистикой конфигурации
        """
        if self.configuration is None:
            return {"error": "Конфигурация не загружена"}
        
        total_zones = sum(len(p.zones) for p in self.configuration.partitions)
        
        return {
            "project_name": self.configuration.project_name,
            "devices_count": len(self.configuration.devices),
            "partitions_count": len(self.configuration.partitions),
            "zones_count": total_zones,
            "relays_count": len(self.configuration.relays),
            "scenarios_count": len(self.configuration.scenarios),
            "validation_errors": len(self.configuration.validate())
        }


def create_app() -> ProjectToPProg:
    """
    Создать экземпляр приложения.
    
    Returns:
        Экземпляр ProjectToPProg
    """
    return ProjectToPProg()


# Удобные функции для быстрого доступа
def parse_project(pdf_path: str | Path) -> ParseResult:
    """Быстрый парсинг PDF проекта."""
    app = create_app()
    return app.load_pdf(pdf_path)


def quick_export(pdf_path: str | Path, output_path: str | Path, format: str = "txt") -> bool:
    """Быстрый парсинг и экспорт проекта."""
    app = create_app()
    app.load_pdf(pdf_path)
    return app.export(output_path, format)


if __name__ == "__main__":
    # Пример использования
    print("Project-to-PProg - Инструмент автоматизации конфигурирования Болид")
    print("=" * 60)
    
    # Создаем приложение
    app = create_app()
    
    # Пример парсинга текста (для демонстрации)
    sample_text = """
    Спецификация оборудования:
    С2000М исп.02 адрес 127 - Прибор управления охранно-пожарный
    С2000-КДЛ-2И исп.01 адрес 1 - Контроллер двухпроводной линии связи
    С2000-СП2 исп.01 адрес 39 - Прибор релейный
    С2000-СП2 исп.01 адрес 41 - Прибор релейный
    С2000-БКИ исп.02 адрес 2 - Блок клавиатурный
    
    Таблица принадлежности ИП к ЗКПС:
    Раздел 1: Зоны 1-5 (ДИП-34А)
    Раздел 2: Зоны 6-10 (ДИП-34А)
    Раздел 3: Зоны 11-15 (ИПР 513-3А)
    
    Исполнительные устройства:
    SC39-40 -> Табло Выход
    SC41-42 -> Маяк-12-3М сирена
    """
    
    print("\nЗагрузка примера проекта...")
    result = app.load_text(sample_text, "Demo Project")
    
    print(f"\nОшибки парсинга: {len(result.errors)}")
    print(f"Предупреждения: {len(result.warnings)}")
    
    print("\nСводка по конфигурации:")
    summary = app.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\nВалидация конфигурации:")
    errors = app.validate_configuration()
    if errors:
        for error in errors:
            print(f"  - {error}")
    else:
        print("  Ошибок не найдено")
    
    print("\nЭкспорт конфигурации в TXT...")
    output_file = Path("/tmp/demo_config.txt")
    if app.export(output_file, "txt"):
        print(f"  Файл успешно создан: {output_file}")
        print(f"\nСодержимое файла (первые 500 символов):")
        print("-" * 60)
        content = output_file.read_text(encoding='utf-8')[:500]
        print(content)
        print("...")
    else:
        print("  Ошибка при экспорте")
    
    print("\n" + "=" * 60)
    print("Готово!")
