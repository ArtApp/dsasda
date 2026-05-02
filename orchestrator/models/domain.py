"""
Базовые модели данных для ИИ-оркестратора.
Определяет структуры для представления проектов, устройств и конфигураций.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class DeviceType(str, Enum):
    """Типы устройств АПС."""
    CONTROL_PANEL = "control_panel"  # Прибор управления (С2000М)
    KDL = "kdl"  # Контроллер ДПЛС (С2000-КДЛ)
    RELAY = "relay"  # Релейный прибор (С2000-СП2)
    KEYBOARD = "keyboard"  # Блок клавиатурный (С2000-БКИ)
    SMOKE_DETECTOR = "smoke_detector"  # Дымовой извещатель (ДИП-34А)
    HEAT_DETECTOR = "heat_detector"  # Тепловой извещатель
    MANUAL_CALL_POINT = "manual_call_point"  # Ручной извещатель (ИПР)
    SOUND_ALARM = "sound_alarm"  # Звуковой оповещатель
    LIGHT_ALARM = "light_alarm"  # Световой оповещатель (Маяк)
    SOUNDER = "sounder"  # Комбинированный оповещатель
    INPUT_MODULE = "input_module"  # Модуль ввода
    OUTPUT_MODULE = "output_module"  # Модуль вывода
    OTHER = "other"


class ConfidenceLevel(float, Enum):
    """Уровни уверенности ИИ."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class Device:
    """Модель устройства АПС."""
    device_type: DeviceType
    model: str
    address: int = 0
    quantity: int = 1
    location: Optional[str] = None
    room_number: Optional[str] = None
    characteristics: Dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    source: str = "unknown"  # Откуда извлечено: spec, plan, schematic
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Connection:
    """Модель соединения между устройствами."""
    from_device_id: str
    to_device_id: str
    connection_type: str = "wire"  # wire, wireless, bus
    channel: Optional[int] = None
    line: Optional[str] = None  # Номер линии (A, B, C...)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Partition:
    """Модель раздела (зоны охраны)."""
    partition_id: int
    name: str
    zones: List[int] = field(default_factory=list)
    devices: List[str] = field(default_factory=list)  # ID устройств
    location: Optional[str] = None


@dataclass
class ProjectDomainModel:
    """
    Единая доменная модель проекта.
    Содержит всю информацию о проекте в структурированном виде.
    """
    project_name: str = "Unknown Project"
    devices: List[Device] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    partitions: List[Partition] = field(default_factory=list)
    
    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Результаты валидации
    validation_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Статистика
    total_devices: int = 0
    total_zones: int = 0
    total_partitions: int = 0
    
    def __post_init__(self):
        """Обновление статистики после инициализации."""
        self.update_statistics()
    
    def update_statistics(self):
        """Пересчет статистики."""
        self.total_devices = len(self.devices)
        self.total_partitions = len(self.partitions)
        self.total_zones = sum(len(p.zones) for p in self.partitions)
        self.updated_at = datetime.now()
    
    def add_device(self, device: Device):
        """Добавить устройство."""
        self.devices.append(device)
        self.update_statistics()
    
    def add_connection(self, connection: Connection):
        """Добавить соединение."""
        self.connections.append(connection)
    
    def add_partition(self, partition: Partition):
        """Добавить раздел."""
        self.partitions.append(partition)
        self.update_statistics()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'project_name': self.project_name,
            'devices': [
                {
                    'device_type': d.device_type.value,
                    'model': d.model,
                    'address': d.address,
                    'quantity': d.quantity,
                    'location': d.location,
                    'room_number': d.room_number,
                    'characteristics': d.characteristics,
                    'confidence': d.confidence.value,
                    'source': d.source,
                }
                for d in self.devices
            ],
            'connections': [
                {
                    'from_device_id': c.from_device_id,
                    'to_device_id': c.to_device_id,
                    'connection_type': c.connection_type,
                    'channel': c.channel,
                    'line': c.line,
                    'confidence': c.confidence.value,
                }
                for c in self.connections
            ],
            'partitions': [
                {
                    'partition_id': p.partition_id,
                    'name': p.name,
                    'zones': p.zones,
                    'devices': p.devices,
                    'location': p.location,
                }
                for p in self.partitions
            ],
            'validation_issues': self.validation_issues,
            'warnings': self.warnings,
            'statistics': {
                'total_devices': self.total_devices,
                'total_zones': self.total_zones,
                'total_partitions': self.total_partitions,
            }
        }


@dataclass
class ValidationResult:
    """Результат валидации данных."""
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
