"""
Парсер проектной документации в формате PDF.
Извлекает структурированные данные для конфигурации PProg.
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


@dataclass
class ParseResult:
    """Результат парсинга PDF."""
    configuration: Configuration
    warnings: list[str]
    errors: list[str]


class PDFParser:
    """Парсер проектной документации в формате PDF."""
    
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
    
    def __init__(self):
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.configuration = Configuration()
    
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
                errors=self.errors
            )
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            self.errors.append(f"Файл не найден: {pdf_path}")
            return ParseResult(
                configuration=self.configuration,
                warnings=self.warnings,
                errors=self.errors
            )
        
        try:
            doc = fitz.open(pdf_path)
            self.configuration.project_name = pdf_path.stem
            
            # Извлечение текста из всех страниц
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            
            doc.close()
            
            # Парсинг различных секций
            self._parse_devices(full_text)
            self._parse_partitions(full_text)
            self._parse_relays(full_text)
            
        except Exception as e:
            self.errors.append(f"Ошибка при чтении PDF: {str(e)}")
        
        return ParseResult(
            configuration=self.configuration,
            warnings=self.warnings,
            errors=self.errors
        )
    
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
        
        self._parse_devices(text)
        self._parse_partitions(text)
        self._parse_relays(text)
        
        return ParseResult(
            configuration=self.configuration,
            warnings=self.warnings,
            errors=self.errors
        )
    
    def _parse_devices(self, text: str):
        """Извлечение устройств из текста."""
        # Поиск С2000М (консоль)
        s2000m_pattern = r'С2000М(?:\s*исп\.?(\d+))?.*?(?:адрес|№)\s*(\d+)'
        for match in re.finditer(s2000m_pattern, text, re.IGNORECASE):
            version = match.group(1) if match.group(1) else None
            address = int(match.group(2))
            
            device_info = get_device_info("С2000М")
            device = Device(
                address=address,
                device_type=device_info["pprog_type"] if device_info else "S2000M console",
                description="Прибор управления охранно-пожарный С2000М",
                version=version
            )
            self.configuration.add_device(device)
        
        # Поиск КДЛ
        kdl_pattern = r'С2000-КДЛ-2И(?:\s*исп\.?(\d+))?.*?(?:адрес|№)\s*(\d+)'
        for match in re.finditer(kdl_pattern, text, re.IGNORECASE):
            version = match.group(1) if match.group(1) else None
            address = int(match.group(2))
            
            device_info = get_device_info("С2000-КДЛ-2И")
            device = Device(
                address=address,
                device_type=device_info["pprog_type"] if device_info else "S2000-KDL-2I controller",
                description="Контроллер двухпроводной линии связи",
                version=version
            )
            self.configuration.add_device(device)
        
        # Поиск СП2 (релейные модули)
        sp2_pattern = r'С2000-СП2(?:\s*исп\.?(\d+))?.*?(?:адрес|№)\s*(\d+)'
        for match in re.finditer(sp2_pattern, text, re.IGNORECASE):
            version = match.group(1) if match.group(1) else None
            address = int(match.group(2))
            
            device_info = get_device_info("С2000-СП2")
            device = Device(
                address=address,
                device_type=device_info["pprog_type"] if device_info else "S2000-SP2 relay module",
                description="Прибор приемно-контрольный и управления релейный",
                version=version
            )
            self.configuration.add_device(device)
            
            # Добавляем два реле для каждого СП2
            for relay_num in range(1, 3):
                relay = Relay(
                    device_address=address,
                    relay_number=relay_num,
                    program=RelayProgram.OFF
                )
                self.configuration.add_relay(relay)
        
        # Поиск БКИ
        bki_pattern = r'С2000-БКИ(?:\s*исп\.?(\d+))?.*?(?:адрес|№)\s*(\d+)'
        for match in re.finditer(bki_pattern, text, re.IGNORECASE):
            version = match.group(1) if match.group(1) else None
            address = int(match.group(2))
            
            device_info = get_device_info("С2000-БКИ")
            device = Device(
                address=address,
                device_type=device_info["pprog_type"] if device_info else "S2000-BKI interface module",
                description="Блок клавиатурный интерфейс",
                version=version
            )
            self.configuration.add_device(device)
        
        # Поиск RS-200T
        rs_pattern = r'RS-200T.*?(?:адрес|№)\s*(\d+)'
        for match in re.finditer(rs_pattern, text, re.IGNORECASE):
            address = int(match.group(1))
            
            device_info = get_device_info("RS-200T")
            device = Device(
                address=address,
                device_type=device_info["pprog_type"] if device_info else "RS-200T network converter",
                description="Преобразователь интерфейсов",
                version=None
            )
            self.configuration.add_device(device)
    
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


def parse_pdf_project(pdf_path: str | Path) -> ParseResult:
    """
    Удобная функция для парсинга PDF проекта.
    
    Args:
        pdf_path: Путь к PDF файлу
        
    Returns:
        ParseResult с конфигурацией
    """
    parser = PDFParser()
    return parser.parse_file(pdf_path)


def parse_text_project(text: str, project_name: str = "Project") -> ParseResult:
    """
    Удобная функция для парсинга текста проекта.
    
    Args:
        text: Текст проектной документации
        project_name: Имя проекта
        
    Returns:
        ParseResult с конфигурацией
    """
    parser = PDFParser()
    return parser.parse_text(text, project_name)
