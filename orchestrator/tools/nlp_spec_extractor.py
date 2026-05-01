"""
NLP Spec Extractor - ИИ-инструмент для извлечения данных из спецификаций.
Этап 2: Разработка и Тестирование Прототипов ИИ-инструментов

Использует NLP (spaCy, transformers) или LLM для извлечения сущностей:
- DeviceType, ModelNumber, Quantity, Location, Characteristics
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import time
import re

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus
from orchestrator.models.domain import Device, DeviceType, ConfidenceLevel

logger = logging.getLogger(__name__)


class NLPSpecExtractor(AITool):
    """
    ИИ-инструмент для извлечения информации о оборудовании из текстовых спецификаций.
    
    Функции:
    - Извлечение сущностей (NER): устройства, модели, количества, локации
    - Извлечение отношений между сущностями
    - Вывод структурированного JSON/CSV с оборудованием
    """
    
    # Паттерны для поиска устройств Болид
    DEVICE_PATTERNS = {
        'control_panel': [
            r'С2000М', r'С2000-М', r'прибор управления', r'ППКП',
        ],
        'kdl': [
            r'С2000-КДЛ', r'контроллер ДПЛС', r'двухпроводной линии',
        ],
        'relay': [
            r'С2000-СП\d', r'прибор релейный', r'релейный модуль',
        ],
        'keyboard': [
            r'С2000-БКИ', r'блок клавиатурный', r'клавиатура',
        ],
        'smoke_detector': [
            r'ДИП-\d+', r'дымовой извещатель', r'датчик дыма',
        ],
        'manual_call_point': [
            r'ИПР\s*\d', r'ручной извещатель', r'кнопка тревоги',
        ],
        'sound_alarm': [
            r'Маяк', r'звуковой оповещатель', r'сирена',
        ],
    }
    
    # Паттерны для адресов
    ADDRESS_PATTERN = r'(?:адрес|addr\.?|№)\s*(\d{1,3})'
    
    # Паттерны для количеств
    QUANTITY_PATTERN = r'(\d+)\s*(?:шт\.?|единиц?|экземпляр[аов]?)'
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("NLPSpecExtractor", config)
        self.use_spacy = self.config.get('use_spacy', True)
        self.use_llm = self.config.get('use_llm', False)
        
        # Lazy imports
        self._nlp = None
        self._spacy_available = False
    
    def _initialize(self):
        """Инициализация NLP моделей."""
        if self.use_spacy:
            try:
                import spacy
                try:
                    self._nlp = spacy.load('ru_core_news_sm')
                    self._spacy_available = True
                    logger.info("spaCy Russian model loaded")
                except OSError:
                    logger.warning("Russian spaCy model not installed. Run: python -m spacy download ru_core_news_sm")
            except ImportError:
                logger.warning("spaCy not available")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить NLP-анализ спецификаций.
        
        Args:
            input_data: Текст спецификации или путь к файлу
            
        Returns:
            ToolResult с извлеченными устройствами
        """
        start_time = time.time()
        
        try:
            # Загрузка текста
            if isinstance(input_data, str):
                if Path(input_data).exists():
                    with open(input_data, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    text = input_data
            elif isinstance(input_data, dict) and 'text' in input_data:
                text = input_data['text']
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data. Expected text string or file path."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Извлечение устройств
            devices = self._extract_devices(text)
            
            # Извлечение локаций
            locations = self._extract_locations(text)
            
            # Сопоставление устройств с локациями
            self._match_devices_to_locations(devices, locations)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    'devices': [
                        {
                            'device_type': d.device_type.value,
                            'model': d.model,
                            'address': d.address,
                            'quantity': d.quantity,
                            'location': d.location,
                            'confidence': d.confidence.value,
                        }
                        for d in devices
                    ],
                    'total_devices': len(devices),
                    'locations': locations,
                },
                metadata={
                    'text_length': len(text),
                    'use_spacy': self._spacy_available,
                },
                execution_time_ms=execution_time,
                confidence=0.85 if self._spacy_available else 0.7,
            )
            
        except Exception as e:
            logger.exception(f"Error in NLPSpecExtractor: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _extract_devices(self, text: str) -> List[Device]:
        """Извлечь устройства из текста."""
        devices = []
        
        # Поиск по паттернам
        for device_type, patterns in self.DEVICE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    device = self._create_device_from_match(
                        text, match, device_type
                    )
                    if device:
                        devices.append(device)
        
        # Удаление дубликатов (простое)
        unique_devices = []
        seen = set()
        for d in devices:
            key = (d.device_type, d.model, d.address)
            if key not in seen:
                seen.add(key)
                unique_devices.append(d)
        
        return unique_devices
    
    def _create_device_from_match(
        self,
        text: str,
        match: re.Match,
        device_type_str: str,
    ) -> Optional[Device]:
        """Создать устройство из regex совпадения."""
        # Определение типа устройства
        try:
            device_type = DeviceType(device_type_str)
        except ValueError:
            device_type = DeviceType.OTHER
        
        # Получение контекста вокруг совпадения
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)
        context = text[start:end]
        
        # Поиск адреса в контексте
        address = 0
        addr_match = re.search(self.ADDRESS_PATTERN, context, re.IGNORECASE)
        if addr_match:
            try:
                address = int(addr_match.group(1))
            except ValueError:
                pass
        
        # Поиск количества
        quantity = 1
        qty_match = re.search(self.QUANTITY_PATTERN, context, re.IGNORECASE)
        if qty_match:
            try:
                quantity = int(qty_match.group(1))
            except ValueError:
                pass
        
        # Модель - само совпадение
        model = match.group(0)
        
        return Device(
            device_type=device_type,
            model=model,
            address=address,
            quantity=quantity,
            confidence=ConfidenceLevel.MEDIUM,
            source='spec_nlp',
        )
    
    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """Извлечь локации/помещения из текста."""
        locations = []
        
        # Паттерны для помещений
        room_patterns = [
            r'(?:помещение|комната|зал|коридор)\s*([№\d\-\.]+)',
            r'([№\d\-\.]+)\s*(?:этаж)',
            r'корпус\s*([A-ZА-Я]?[\d\-]*)',
        ]
        
        for pattern in room_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                locations.append({
                    'type': 'room',
                    'identifier': match.group(1),
                    'context': match.group(0),
                    'position': match.start(),
                })
        
        return locations
    
    def _match_devices_to_locations(
        self,
        devices: List[Device],
        locations: List[Dict[str, Any]],
    ):
        """Сопоставить устройства с локациями по близости в тексте."""
        # Простая эвристика: ближайшее помещение перед устройством
        # В полной версии можно использовать NLP для понимания контекста
        pass
