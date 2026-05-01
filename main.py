"""
Главный модуль приложения Project-to-PProg.
Предоставляет основной API для работы с инструментом.
Интегрирует все модули: PDF парсер, NLP анализатор, улучшение сканов, 
распознавание схем, экспорт и базу знаний оборудования.
"""

from pathlib import Path
from typing import Optional
import logging

from data.models import Configuration
from data.equipment_db import get_device_info, EQUIPMENT_DATABASE
from modules.pdf_parser import (
    PDFParser, parse_pdf_project, parse_text_project, parse_scanned_pdf,
    ParseResult, ScannedPDFParserConfig
)
from modules.exporter import PProgExporter, export_configuration
from modules.nlp_analyzer import RussianNLPAnalyzer, NLPAnalysisResult
from modules.scan_enhancer import (
    enhance_scan, preprocess_for_ocr, ScanEnhancementConfig,
    EnhancementResult, NoiseReductionMethod, BinarizationMethod
)
from modules.schema_recognizer import SchemaAddressRecognizer as SchemaRecognizer, DetectedAddress, SchemaAnalysisResult

# Алиас для совместимости
SchemaRecognitionConfig = dict  # Конфигурация передается как dict с параметрами
from modules.parsing_profiles import ParsingProfile, ProfileManager


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectToPProg:
    """Основной класс приложения Project-to-PProg."""
    
    def __init__(self, use_nlp: bool = True, use_schema_recognition: bool = False):
        self.parser = PDFParser(use_nlp=use_nlp)
        self.configuration: Optional[Configuration] = None
        self.last_parse_result: Optional[ParseResult] = None
        self.use_nlp = use_nlp
        self.nlp_analyzer = RussianNLPAnalyzer(use_spacy=use_nlp) if use_nlp else None
        self.schema_recognizer = SchemaRecognizer() if use_schema_recognition else None
        self.profile_manager = ProfileManager()
        self._enhancement_results: list[EnhancementResult] = []
        self._detected_addresses: list[DetectedAddress] = []
    
    def load_pdf(
        self, 
        pdf_path: str | Path,
        is_scanned: bool = False,
        enhancement_config: Optional[ScanEnhancementConfig] = None,
        ocr_languages: str = "rus+eng",
        recognize_schemas: bool = False,
        schema_config: Optional[SchemaRecognitionConfig] = None
    ) -> ParseResult:
        """
        Загрузка и парсинг PDF файла проектной документации.
        
        Args:
            pdf_path: Путь к PDF файлу
            is_scanned: True если PDF сканированный (требуется OCR и улучшение)
            enhancement_config: Настройки улучшения сканов (для сканированных PDF)
            ocr_languages: Языки для OCR (например, "rus+eng")
            recognize_schemas: Распознавать ли адреса со схем/планов
            schema_config: Настройки распознавания схем
            
        Returns:
            ParseResult с конфигурацией и списком предупреждений/ошибок
        """
        if is_scanned:
            # Используем расширенный парсинг для сканированных документов
            scan_config = ScannedPDFParserConfig(
                enhance_scans=True,
                scan_enhancement_config=enhancement_config,
                ocr_enabled=True,
                ocr_languages=ocr_languages
            )
            result = parse_scanned_pdf(pdf_path, enhance_config=enhancement_config, 
                                       ocr_languages=ocr_languages, use_nlp=self.use_nlp)
            self._enhancement_results = result.enhancement_results or []
        else:
            result = self.parser.parse_file(pdf_path)
        
        self.configuration = result.configuration
        self.last_parse_result = result
        
        # Распознавание схем если включено
        if recognize_schemas and self.schema_recognizer:
            try:
                schema_result = self.schema_recognizer.process_pdf(
                    pdf_path, 
                    config=schema_config
                )
                self._detected_addresses = schema_result.addresses
                # Обогащаем конфигурацию данными со схем
                self._enrich_from_schemas(schema_result)
                logger.info(f"Распознано {len(schema_result.addresses)} адресов со схем")
            except Exception as e:
                logger.warning(f"Ошибка распознавания схем: {e}")
                result.warnings.append(f"Распознавание схем не выполнено: {e}")
        
        return result
    
    def _enrich_from_schemas(self, schema_result):
        """
        Обогащение конфигурации данными, распознанными со схем.
        
        Args:
            schema_result: Результат распознавания схем
        """
        if not self.configuration or not schema_result.addresses:
            return
        
        # Сопоставление адресов со схемами с устройствами в конфигурации
        for detected in schema_result.addresses:
            if detected.address_value and detected.device_type:
                # Ищем устройство с таким адресом и обновляем информацию
                for device in self.configuration.devices:
                    if device.address == 0 or device.address == detected.address_value:
                        # Обновляем адрес если он не был установлен
                        if device.address == 0:
                            device.address = detected.address_value
                        # Добавляем информацию о местоположении
                        if detected.location and detected.location not in device.description:
                            device.description += f" [{detected.location}]"
                        logger.debug(f"Обновлено устройство {device.device_type}: адрес={detected.address_value}, локация={detected.location}")
    
    def get_enhancement_results(self) -> list[EnhancementResult]:
        """Получить результаты улучшения сканов."""
        return self._enhancement_results
    
    def get_detected_addresses(self) -> list[DetectedAddress]:
        """Получить адреса, распознанные со схем."""
        return self._detected_addresses
    
    def load_profile(self, profile_path: str | Path) -> bool:
        """
        Загрузить профиль парсинга.
        
        Args:
            profile_path: Путь к файлу профиля (JSON)
            
        Returns:
            True если успешно
        """
        try:
            self.profile_manager.load_profile(profile_path)
            logger.info(f"Загружен профиль: {profile_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки профиля: {e}")
            return False
    
    def apply_profile(self, profile_name: str) -> bool:
        """
        Применить профиль парсинга.
        
        Args:
            profile_name: Имя профиля из доступных
            
        Returns:
            True если успешно
        """
        try:
            profile = self.profile_manager.get_profile(profile_name)
            if profile:
                # Применяем настройки профиля к парсеру
                if hasattr(profile, 'device_patterns') and profile.device_patterns:
                    self.parser.DEVICE_PATTERNS.update(profile.device_patterns)
                logger.info(f"Применён профиль: {profile_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка применения профиля: {e}")
            return False
    
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
    
    def get_nlp_analysis(self) -> Optional[NLPAnalysisResult]:
        """Получить результаты NLP-анализа последнего парсинга."""
        if self.last_parse_result:
            return self.last_parse_result.nlp_result
        return None
    
    def get_available_profiles(self) -> list[str]:
        """Получить список доступных профилей парсинга."""
        return self.profile_manager.list_profiles()


def create_app(use_nlp: bool = True, use_schema_recognition: bool = False) -> ProjectToPProg:
    """
    Создать экземпляр приложения.
    
    Args:
        use_nlp: Использовать ли NLP-анализ
        use_schema_recognition: Использовать ли распознавание схем
    
    Returns:
        Экземпляр ProjectToPProg
    """
    return ProjectToPProg(use_nlp=use_nlp, use_schema_recognition=use_schema_recognition)


# Удобные функции для быстрого доступа
def parse_project(
    pdf_path: str | Path, 
    is_scanned: bool = False,
    enhancement_config: Optional[ScanEnhancementConfig] = None,
    ocr_languages: str = "rus+eng",
    recognize_schemas: bool = False
) -> ParseResult:
    """Быстрый парсинг PDF проекта."""
    app = create_app()
    return app.load_pdf(
        pdf_path, 
        is_scanned=is_scanned,
        enhancement_config=enhancement_config,
        ocr_languages=ocr_languages,
        recognize_schemas=recognize_schemas
    )


def quick_export(pdf_path: str | Path, output_path: str | Path, format: str = "txt") -> bool:
    """Быстрый парсинг и экспорт проекта."""
    app = create_app()
    app.load_pdf(pdf_path)
    return app.export(output_path, format)


def parse_and_enhance_scan(
    image_path: str | Path,
    config: Optional[ScanEnhancementConfig] = None,
    output_path: Optional[str | Path] = None
) -> EnhancementResult:
    """Улучшить качество скана изображения."""
    return enhance_scan(image_path, config=config, output_path=output_path)


def preprocess_image_for_ocr(
    image_path: str | Path,
    target_dpi: int = 300,
    output_path: Optional[str | Path] = None
) -> EnhancementResult:
    """Подготовить изображение для OCR."""
    return preprocess_for_ocr(image_path, target_dpi=target_dpi, output_path=output_path)


if __name__ == "__main__":
    # Пример использования
    print("Project-to-PProg - Инструмент автоматизации конфигурирования Болид")
    print("=" * 60)
    print("\nДоступные модули:")
    print("  ✓ PDF парсер с поддержкой сканированных документов")
    print("  ✓ NLP анализатор для русского языка")
    print("  ✓ Улучшение качества сканов (шум, перекос, DPI)")
    print("  ✓ Распознавание схем и планов этажей")
    print("  ✓ Профили парсинга")
    print("  ✓ Экспорт в TXT/JSON/Excel")
    print("=" * 60)
    
    # Создаем приложение с полным набором функций
    app = create_app(use_nlp=True, use_schema_recognition=False)
    
    # Демонстрация доступных профилей
    print("\nДоступные профили парсинга:")
    profiles = app.get_available_profiles()
    for profile in profiles:
        print(f"  - {profile}")
    
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
    
    # Показываем результаты NLP если доступны
    nlp_result = app.get_nlp_analysis()
    if nlp_result:
        print(f"\nNLP-анализ выполнен:")
        print(f"  - Найдено устройств: {len(nlp_result.device_mentions)}")
        print(f"  - Найдено адресов: {len(nlp_result.address_mentions)}")
        print(f"  - Найдено локаций: {len(nlp_result.location_mentions)}")
    
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
    
    # Демонстрация работы с сканами
    print("\n" + "=" * 60)
    print("Пример обработки сканированного документа:")
    print("-" * 60)
    print("""
# Для обработки сканированного PDF используйте:
app = create_app(use_nlp=True)

# Обработка с улучшением качества и OCR
result = app.load_pdf(
    "scanned_project.pdf",
    is_scanned=True,
    enhancement_config=ScanEnhancementConfig(
        denoise_method=NoiseReductionMethod.NL_MEANS,
        deskew=True,
        enhance_contrast=True,
        target_dpi=300
    ),
    ocr_languages="rus+eng",
    recognize_schemas=True
)

# Получение результатов улучшения
enhancement_results = app.get_enhancement_results()
for res in enhancement_results:
    print(f"Страница {res.page_number}: качество улучшено на {res.quality_improvement:.1f}%")

# Получение адресов со схем
addresses = app.get_detected_addresses()
for addr in addresses:
    print(f"Адрес {addr.address_value}: {addr.device_type} в {addr.location}")
""")
    
    print("\n" + "=" * 60)
    print("Готово!")
