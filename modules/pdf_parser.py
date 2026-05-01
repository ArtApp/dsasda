"""
Парсер проектной документации в формате PDF.
Извлекает структурированные данные для конфигурации PProg.
Интегрирован с NLP-анализатором для улучшения понимания контекста.
Поддерживает обработку сканированных документов с улучшением качества изображений.
"""

import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from data.models import (
    Configuration, Device, Partition, Zone, Relay, 
    ZoneType, RelayProgram, ManagementScenario
)
from data.equipment_db import get_device_info
from modules.nlp_analyzer import RussianNLPAnalyzer, NLPAnalysisResult, EntityCategory
from modules.scan_enhancer import (
    enhance_scan, preprocess_for_ocr, ScanEnhancementConfig,
    EnhancementResult, NoiseReductionMethod, BinarizationMethod
)


@dataclass
class ParseResult:
    """Результат парсинга PDF."""
    configuration: Configuration
    warnings: list[str]
    errors: list[str]
    nlp_result: Optional[NLPAnalysisResult] = None  # Добавлено поле для NLP-результатов
    enhancement_results: list[EnhancementResult] = None  # Результаты улучшения сканов


@dataclass
class ScannedPDFParserConfig:
    """Конфигурация для обработки сканированных PDF."""
    
    # Настройки улучшения сканов
    enhance_scans: bool = True
    scan_enhancement_config: Optional[ScanEnhancementConfig] = None
    
    # Настройки OCR
    ocr_enabled: bool = True
    ocr_languages: str = "rus+eng"
    
    # Пороговые значения
    min_image_dpi: int = 200  # Минимальное DPI для обработки
    min_text_confidence: float = 0.5  # Минимальная уверенность OCR
    
    def __post_init__(self):
        if self.scan_enhancement_config is None:
            self.scan_enhancement_config = ScanEnhancementConfig()


class PDFParser:
    """Парсер проектной документации в формате PDF с NLP-анализом и обработкой сканов."""
    
    # Паттерны для поиска устройств и адресов
    DEVICE_PATTERNS = {
        's2000m': r'С2000М(?:\s*исп\.?\d+)?',
        'kdl': r'С2000-КДЛ-2И(?:\s*исп\.?\d+)?',
        'sp2': r'С2000-СП2(?:\s*исп\.?\d+)?',
        'bki': r'С2000-БКИ(?:\s*исп\.?\d+)?',
        'dip': r'ДИП-34[А-Я]?(?:-\d+)?',
        'ipr': r'ИПР\s*513[-\s]*[3ЗАМ]+(?:\s*исп\.?\d+)?',
        'ipdl': r'С2000-ИПДЛ',
        'rs200t': r'RS-200T',
    }
    
    # Паттерны для поиска адресов
    ADDRESS_PATTERNS = [
        r'ARK(\d+)',      # ARK1, ARK2, etc.
        r'SC(\d+)-(\d+)', # SC39-40, SC41-42
        r'BTH(\d+)',      # BTH1, BTH2, etc.
        r'адрес\s*(\d+)', # адрес 1, адрес 2
        r'№\s*(\d+)',     # №1, №2
    ]
    
    def __init__(self, use_nlp: bool = True, scan_config: Optional[ScannedPDFParserConfig] = None):
        """
        Инициализация парсера.
        
        Args:
            use_nlp: Использовать ли NLP-анализ для обогащения данных
            scan_config: Конфигурация для обработки сканированных документов
        """
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.configuration = Configuration()
        self.use_nlp = use_nlp
        self.nlp_analyzer = RussianNLPAnalyzer(use_spacy=use_nlp) if use_nlp else None
        self.scan_config = scan_config or ScannedPDFParserConfig()
    
    def parse_file(self, pdf_path: str | Path) -> ParseResult:
        """
        Парсинг PDF файла проектной документации.
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            ParseResult с конфигурацией и списком предупреждений/ошибок
        """
        if not PYMUPDF_AVAILABLE:
            self.errors.append("PyMuPDF не установлен. Установите: pip install PyMuPDF")
            return ParseResult(
                configuration=self.configuration,
                warnings=self.warnings,
                errors=self.errors,
                nlp_result=None,
                enhancement_results=[]
            )
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            self.errors.append(f"Файл не найден: {pdf_path}")
            return ParseResult(
                configuration=self.configuration,
                warnings=self.warnings,
                errors=self.errors,
                nlp_result=None,
                enhancement_results=[]
            )
        
        try:
            doc = fitz.open(pdf_path)
            self.configuration.project_name = pdf_path.stem
            
            # Проверка типа PDF (текстовое или сканированное)
            is_scanned = self._is_scanned_pdf(doc)
            
            # Извлечение текста из всех страниц
            full_text = ""
            enhancement_results = []
            
            if is_scanned and self.scan_config.enhance_scans:
                # Обработка сканированного PDF с улучшением изображений
                full_text, enhancement_results = self._extract_text_from_scanned_pdf(doc)
            else:
                # Стандартное извлечение текста
                for page in doc:
                    full_text += page.get_text()
            
            doc.close()
            
            # NLP-анализ текста (если включен)
            nlp_result = None
            if self.use_nlp and self.nlp_analyzer and full_text.strip():
                try:
                    nlp_result = self.nlp_analyzer.analyze_text(full_text)
                    # Обогащение данных на основе NLP-анализа
                    self._enrich_with_nlp(nlp_result)
                except Exception as e:
                    self.warnings.append(f"NLP-анализ не выполнен: {str(e)}")
            
            # Парсинг различных секций
            if full_text.strip():
                self._parse_devices(full_text)
                self._parse_partitions(full_text)
                self._parse_relays(full_text)
            else:
                self.warnings.append("Не удалось извлечь текст из PDF. Возможно, требуется ручная обработка.")
            
        except Exception as e:
            self.errors.append(f"Ошибка при чтении PDF: {str(e)}")
        
        return ParseResult(
            configuration=self.configuration,
            warnings=self.warnings,
            errors=self.errors,
            nlp_result=nlp_result,
            enhancement_results=enhancement_results or []
        )
    
    def _is_scanned_pdf(self, doc) -> bool:
        """
        Определение типа PDF: текстовое или сканированное.
        
        Args:
            doc: PyMuPDF документ
            
        Returns:
            True если PDF содержит изображения (сканированный), False если текстовый
        """
        if len(doc) == 0:
            return False
        
        # Проверяем первые несколько страниц
        pages_to_check = min(3, len(doc))
        text_ratio = 0
        image_count = 0
        
        for i in range(pages_to_check):
            page = doc[i]
            text_len = len(page.get_text().strip())
            images = page.get_images()
            image_count += len(images)
            text_ratio += text_len
        
        # Если есть изображения и мало текста - это сканированный документ
        avg_text_per_page = text_ratio / pages_to_check if pages_to_check > 0 else 0
        has_images = image_count > 0
        
        # Считаем сканированным, если есть изображения и мало текста (<100 символов на страницу в среднем)
        return has_images and avg_text_per_page < 100
    
    def _extract_text_from_scanned_pdf(self, doc) -> tuple[str, list[EnhancementResult]]:
        """
        Извлечение текста из сканированного PDF с предварительным улучшением изображений.
        
        Args:
            doc: PyMuPDF документ
            
        Returns:
            Кортеж (извлеченный текст, список результатов улучшения)
        """
        import tempfile
        import os
        
        extracted_text = ""
        enhancement_results = []
        
        # Проверяем доступность pytesseract для OCR
        try:
            import pytesseract
            ocr_available = True
        except ImportError:
            ocr_available = False
            self.warnings.append("pytesseract не установлен. OCR будет недоступен. Установите: pip install pytesseract")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Получаем изображения со страницы
            image_list = page.get_images(full=True)
            
            if not image_list and ocr_available:
                # Если нет встроенных изображений, рендерим страницу как изображение
                mat = fitz.Matrix(2.0, 2.0)  # Увеличиваем разрешение для лучшего OCR
                pix = page.get_pixmap(matrix=mat)
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    pix.save(tmp.name)
                    tmp_path = tmp.name
                
                try:
                    # Улучшаем изображение
                    enhanced_result = enhance_scan(
                        tmp_path,
                        config=self.scan_config.scan_enhancement_config
                    )
                    enhancement_results.append(enhanced_result)
                    
                    # Выполняем OCR на улучшенном изображении
                    if ocr_available:
                        page_text = pytesseract.image_to_string(
                            enhanced_result.image,
                            lang=self.scan_config.ocr_languages
                        )
                        extracted_text += page_text + "\n"
                finally:
                    os.unlink(tmp_path)
            else:
                # Обрабатываем каждое изображение на странице
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            tmp.write(image_bytes)
                            tmp_path = tmp.name
                        
                        try:
                            # Улучшаем изображение
                            enhanced_result = enhance_scan(
                                tmp_path,
                                config=self.scan_config.scan_enhancement_config
                            )
                            enhancement_results.append(enhanced_result)
                            
                            # Выполняем OCR на улучшенном изображении
                            if ocr_available:
                                img_text = pytesseract.image_to_string(
                                    enhanced_result.image,
                                    lang=self.scan_config.ocr_languages
                                )
                                extracted_text += img_text + "\n"
                        finally:
                            os.unlink(tmp_path)
                    except Exception as e:
                        self.warnings.append(f"Ошибка обработки изображения на странице {page_num + 1}: {str(e)}")
        
        return extracted_text, enhancement_results
    
    def parse_text(self, text: str, project_name: str = "Project") -> ParseResult:
        """
        Парсинг текста (альтернатива для тестирования).
        
        Args:
            text: Текст проектной документации
            project_name: Имя проекта
            
        Returns:
            ParseResult с конфигурацией
        """
        self.configuration = Configuration()
        self.configuration.project_name = project_name
        self.warnings = []
        self.errors = []
        
        # NLP-анализ текста (если включен)
        nlp_result = None
        if self.use_nlp and self.nlp_analyzer:
            try:
                nlp_result = self.nlp_analyzer.analyze_text(text)
                # Обогащение данных на основе NLP-анализа
                self._enrich_with_nlp(nlp_result)
            except Exception as e:
                self.warnings.append(f"NLP-анализ не выполнен: {str(e)}")
        
        self._parse_devices(text)
        self._parse_partitions(text)
        self._parse_relays(text)
        
        return ParseResult(
            configuration=self.configuration,
            warnings=self.warnings,
            errors=self.errors,
            nlp_result=nlp_result
        )
    
    def _enrich_with_nlp(self, nlp_result: NLPAnalysisResult):
        """
        Обогащение извлеченных данных контекстной информацией из NLP-анализа.
        
        Args:
            nlp_result: Результат NLP-анализа текста
        """
        if not nlp_result:
            return
        
        # 1. Обогащение устройств информацией о местоположении
        for device in self.configuration.devices:
            # Поиск связей устройства с локациями
            for relation in nlp_result.relations:
                if relation.get('type') == 'LOCATED_IN':
                    source = relation.get('source', '').lower()
                    target = relation.get('target', '')
                    
                    # Проверяем, относится ли связь к этому устройству
                    device_desc_lower = device.description.lower()
                    if any(word in source for word in device_desc_lower.split()):
                        # Добавляем информацию о местоположении в описание
                        if target not in device.description:
                            device.description += f" ({target})"
        
        # 2. Использование извлеченных адресов для уточнения адресации устройств
        for addr_entity in nlp_result.address_mentions:
            addr_value = addr_entity.metadata.get('address_value')
            if addr_value and addr_value > 0:
                # Проверяем, есть ли устройства без адреса, которым можно назначить этот адрес
                for device in self.configuration.devices:
                    if device.address == 0:
                        # Проверяем контекст на соответствие типу устройства
                        context = addr_entity.context.lower()
                        device_type_lower = device.device_type.lower()
                        
                        # Простая эвристика: если устройство без адреса и тип совпадает по контексту
                        if any(keyword in context for keyword in ['прибор', 'контроллер', 'блок']):
                            device.address = addr_value
                            break
        
        # 3. Обогащение разделов информацией о зонах из NLP
        if nlp_result.location_mentions:
            # Группировка упоминаний локаций
            locations_by_keyword = {}
            for loc_entity in nlp_result.location_mentions:
                keyword = loc_entity.metadata.get('keyword', '')
                if keyword not in locations_by_keyword:
                    locations_by_keyword[keyword] = []
                locations_by_keyword[keyword].append(loc_entity.text)
            
            # Добавление информации о локациях в названия разделов
            for partition in self.configuration.partitions:
                if not partition.name or partition.name.startswith("Раздел"):
                    # Если у раздела стандартное имя, пробуем улучшить его
                    if locations_by_keyword:
                        # Берем первую найденную локацию как кандидат
                        first_keyword = next(iter(locations_by_keyword))
                        first_location = locations_by_keyword[first_keyword][0]
                        partition.name = f"{first_location} (Раздел {partition.partition_id})"
        
        # 4. Обновление реле на основе выявленных связей CONTROLS
        for relation in nlp_result.relations:
            if relation.get('type') == 'CONTROLS':
                source = relation.get('source', '')
                target = relation.get('target', '')
                
                # Поиск реле по описанию
                for relay in self.configuration.relays:
                    if source.lower() in relay.description.lower():
                        # Обновляем описание реле информацией о управляемом устройстве
                        if target and target not in relay.description:
                            relay.description += f" → {target}"
        
        # 5. Логирование предупреждений из NLP
        if nlp_result.warnings:
            for warning in nlp_result.warnings:
                if warning not in self.warnings:
                    self.warnings.append(f"NLP: {warning}")
    
    def _parse_devices(self, text: str):
        """Извлечение устройств из текста."""
        # Поиск С2000М (консоль) - различные форматы записи
        s2000m_patterns = [
            r'[Пп]рибор\s*[Пп]риемно-?[Кк]онтрольный\s*С2000М.*?(?:адрес|№)\s*(\d+)',
            r'С2000М(?:\s*\([^\)]*\))?.*?(?:адрес|№)\s*(\d+)',
            r'С2000М\s*-\s*(\d+)\s*шт',
            r'С2000-М(?:\s*\([^\)]*\))?.*?(?:адрес|№)\s*(\d+)',
        ]
        
        for pattern in s2000m_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                address = int(match.group(1)) if match.lastindex >= 1 else None
                if address:
                    device_info = get_device_info("С2000М")
                    device = Device(
                        address=address,
                        device_type=device_info["pprog_type"] if device_info else "S2000M",
                        description="Прибор управления охранно-пожарный С2000М",
                        version=None
                    )
                    self.configuration.add_device(device)
                    break  # Нашли хотя бы один раз
        
        # Поиск КДЛ-2И
        kdl_patterns = [
            r'[Кк]онтроллер\s*[Дд]вухпроводной\s*[Лл]инии\s*[Сс]вязи\s*КДЛ-2И.*?(\d+)\s*шт',
            r'КДЛ-2И(?:\s*\([^\)]*\))?.*?(\d+)\s*шт',
            r'С2000-КДЛ-2И.*?(\d+)\s*шт',
        ]
        
        for pattern in kdl_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("С2000-КДЛ-2И")
                for i in range(count):
                    device = Device(
                        address=0,  # Адрес будет назначен позже
                        device_type=device_info["pprog_type"] if device_info else "S2000-KDL-2I",
                        description="Контроллер двухпроводной линии связи КДЛ-2И",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск ДИП-34А
        dip_patterns = [
            r'[Ии]звещатель\s*[Пп]ожарный\s*[Дд]ымовой\s*ДИП-34[А-Я]?.*?(\d+)\s*шт',
            r'ДИП-34[А-Я]?(?:\s*\([^\)]*\))?.*?(\d+)\s*шт',
        ]
        
        for pattern in dip_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("ДИП-34А")
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type=device_info["pprog_type"] if device_info else "DIP-34A",
                        description="Извещатель пожарный дымовой ДИП-34А",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск ИПР 513
        ipr_patterns = [
            r'[Ии]звещатель\s*[Пп]ожарный\s*[Рр]учной\s*ИПР\s*513.*?(\d+)\s*шт',
            r'ИПР\s*513[-3АМ]*.*?(\d+)\s*шт',
        ]
        
        for pattern in ipr_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("ИПР 513-3А")
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type=device_info["pprog_type"] if device_info else "IPR-513",
                        description="Извещатель пожарный ручной ИПР 513",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск БКИ
        bki_patterns = [
            r'[Бб]лок\s*[Кк]оммутации\s*БКИ.*?(\d+)\s*шт',
            r'БКИ-?\d*.*?(\d+)\s*шт',
            r'С2000-БКИ.*?(\d+)\s*шт',
        ]
        
        for pattern in bki_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("С2000-БКИ")
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type=device_info["pprog_type"] if device_info else "S2000-BKI",
                        description="Блок коммутации БКИ",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск СП2-1 (табло)
        sp2_patterns = [
            r'[Тт]абло\s*[Сс]ветовое\s*СП2.*?(\d+)\s*шт',
            r'СП2-?\d*.*?(\d+)\s*шт',
            r'С2000-СП2.*?(\d+)\s*шт',
        ]
        
        for pattern in sp2_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("С2000-СП2")
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type=device_info["pprog_type"] if device_info else "S2000-SP2",
                        description="Табло световое СП2",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск сирен
        siren_patterns = [
            r'[Сс]ирена\s*[Зз]вуковая.*?(\d+)\s*шт',
            r'С2000-С\d*.*?(\d+)\s*шт',
        ]
        
        for pattern in siren_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type="S2000-Siren",
                        description="Сирена звуковая",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
        
        # Поиск РС-200Т
        rs_patterns = [
            r'[Рр]елейный\s*[Бб]лок\s*РС-200Т.*?(\d+)\s*шт',
            r'РС-200Т.*?(\d+)\s*шт',
            r'RS-200T.*?(\d+)\s*шт',
        ]
        
        for pattern in rs_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                count = int(match.group(1))
                device_info = get_device_info("RS-200T")
                for i in range(count):
                    device = Device(
                        address=0,
                        device_type=device_info["pprog_type"] if device_info else "RS-200T",
                        description="Релейный блок РС-200Т",
                        version=None
                    )
                    self.configuration.add_device(device)
                break
    
    def _parse_partitions(self, text: str):
        """Извлечение разделов и зон из текста."""
        # Поиск таблиц принадлежности ИП к ЗКПС
        # Пример формата: "Раздел 1: Зоны 1-5, ДИП-34А"
        partition_pattern = r'[Рр]аздел\s*(\d+).*?[Зз]оны?\s*(\d+)(?:-(\d+))?'
        
        partition_matches = re.findall(partition_pattern, text)
        
        if not partition_matches:
            self.warnings.append("Не найдено явного указания разделов. Создаю разделы по умолчанию.")
            # Создаем один раздел по умолчанию
            partition = Partition(partition_id=1, name="Раздел 1")
            self.configuration.add_partition(partition)
        else:
            for match in partition_matches:
                partition_id = int(match[0])
                zone_start = int(match[1])
                zone_end = int(match[2]) if match[2] else zone_start
                
                partition = Partition(partition_id=partition_id, name=f"Раздел {partition_id}")
                
                # Добавляем зоны в раздел
                for zone_num in range(zone_start, zone_end + 1):
                    zone = Zone(
                        zone_number=zone_num,
                        zone_type=ZoneType.SMOKE_ANALOG,  # По умолчанию дымовой
                        address=zone_num,
                        algorithm="B"
                    )
                    partition.add_zone(zone)
                
                self.configuration.add_partition(partition)
    
    def _parse_relays(self, text: str):
        """Извлечение информации о реле и исполнительных устройствах."""
        # Поиск информации о табло и сиренах
        # Пример: "SC39-40 -> Табло Выход", "SC41-42 -> Маяк-12-3М"
        
        tablo_pattern = r'SC(\d+)-(\d+).*?[Тт]абло'
        siren_pattern = r'SC(\d+)-(\d+).*?([Мм]аяк|[Сс]ирена)'
        
        for match in re.finditer(tablo_pattern, text):
            addr_start = int(match.group(1))
            addr_end = int(match.group(2))
            
            # Находим соответствующие реле
            for relay in self.configuration.relays:
                if relay.device_address == addr_start:
                    relay.program = RelayProgram.LAMP
                    relay.description = "Табло Выход"
        
        for match in re.finditer(siren_pattern, text):
            addr_start = int(match.group(1))
            
            # Находим соответствующие реле
            for relay in self.configuration.relays:
                if relay.device_address == addr_start:
                    relay.program = RelayProgram.SIREN
                    relay.activation_time = 300  # 5 минут
                    relay.description = "Сирена оповещения"


def parse_pdf_project(
    pdf_path: str | Path, 
    use_nlp: bool = True,
    scan_config: Optional[ScannedPDFParserConfig] = None
) -> ParseResult:
    """
    Удобная функция для парсинга PDF проекта.
    
    Args:
        pdf_path: Путь к PDF файлу
        use_nlp: Использовать ли NLP-анализ для обогащения данных
        scan_config: Конфигурация для обработки сканированных документов
        
    Returns:
        ParseResult с конфигурацией
    """
    parser = PDFParser(use_nlp=use_nlp, scan_config=scan_config)
    return parser.parse_file(pdf_path)


def parse_text_project(text: str, project_name: str = "Project", use_nlp: bool = True) -> ParseResult:
    """
    Удобная функция для парсинга текста проекта.
    
    Args:
        text: Текст проектной документации
        project_name: Имя проекта
        use_nlp: Использовать ли NLP-анализ для обогащения данных
        
    Returns:
        ParseResult с конфигурацией
    """
    parser = PDFParser(use_nlp=use_nlp)
    return parser.parse_text(text, project_name)


def parse_scanned_pdf(
    pdf_path: str | Path,
    enhance_config: Optional[ScanEnhancementConfig] = None,
    ocr_languages: str = "rus+eng",
    use_nlp: bool = True
) -> ParseResult:
    """
    Удобная функция для парсинга сканированных PDF с улучшением качества изображений.
    
    Args:
        pdf_path: Путь к PDF файлу
        enhance_config: Конфигурация улучшения сканов (None = настройки по умолчанию)
        ocr_languages: Языки для OCR (например, "rus+eng")
        use_nlp: Использовать ли NLP-анализ
        
    Returns:
        ParseResult с конфигурацией и результатами улучшения
    """
    scan_config = ScannedPDFParserConfig(
        enhance_scans=True,
        scan_enhancement_config=enhance_config,
        ocr_enabled=True,
        ocr_languages=ocr_languages
    )
    parser = PDFParser(use_nlp=use_nlp, scan_config=scan_config)
    return parser.parse_file(pdf_path)

