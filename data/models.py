"""
Модуль данных для представления конфигурации PProg.
Использует dataclasses для строгой типизации всех сущностей системы.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ZoneType(Enum):
    """Типы зон в системе."""
    SMOKE_ANALOG = "Smoke Analog Addressable"
    HEAT_ANALOG = "Heat Analog Addressable"
    MANUAL_CALL_POINT = "Manual Call Points"
    MULTI_SENSOR = "Multi-Sensor Analog Addressable"
    AUXILIARY = "Auxiliary"
    FIRE_MONITOR = "Fire Monitor Module"


class RelayProgram(Enum):
    """Программы управления реле."""
    OFF = 0
    LAMP = 1
    SIREN = 2
    BLINK = 3
    ASPT = 4
    DUCT_DAMPER = 5
    FAN = 6
    DOOR_LOCK = 7


class DeviceStatus(Enum):
    """Статус устройства."""
    OK = "OK"
    MISSING = "Missing"
    WRONG_VERSION = "Wrong Version"
    NOT_CONFIGURED = "Not Configured"


@dataclass
class Device:
    """Представление устройства в системе PProg."""
    address: int
    device_type: str
    description: str = ""
    version: Optional[str] = None
    status: DeviceStatus = DeviceStatus.NOT_CONFIGURED
    comments: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"Device {self.address}"


@dataclass
class Zone:
    """Представление зоны (извещателя) в разделе."""
    zone_number: int
    zone_type: ZoneType
    address: int
    description: str = ""
    algorithm: str = "B"  # A или B
    enabled: bool = True
    
    def __post_init__(self):
        if not self.description:
            self.description = f"Zone {self.zone_number}"


@dataclass
class Partition:
    """Представление раздела (Partition) в системе."""
    partition_id: int
    name: str = ""
    zones: list[Zone] = field(default_factory=list)
    enabled: bool = True
    
    def add_zone(self, zone: Zone):
        """Добавить зону в раздел."""
        self.zones.append(zone)
    
    def remove_zone(self, zone_number: int):
        """Удалить зону из раздела по номеру."""
        self.zones = [z for z in self.zones if z.zone_number != zone_number]


@dataclass
class Relay:
    """Представление реле (выхода) в системе."""
    device_address: int
    relay_number: int  # 1 или 2 для С2000-СП2
    program: RelayProgram = RelayProgram.OFF
    partitions: list[int] = field(default_factory=list)  # ID разделов, управляющих этим реле
    delay: int = 0  # Задержка активации в секундах
    activation_time: int = 0  # Время активации (0 = бесконечно)
    description: str = ""
    
    @property
    def full_address(self) -> str:
        """Возвращает полный адрес реле в формате SC{address}-{relay}."""
        return f"SC{self.device_address}-{self.device_address + self.relay_number - 1}"


@dataclass
class ManagementScenario:
    """Сценарий управления для сложной логики."""
    scenario_id: int
    name: str
    conditions: list[dict] = field(default_factory=list)  # Условия запуска
    actions: list[dict] = field(default_factory=list)  # Действия при выполнении
    enabled: bool = True


@dataclass
class Configuration:
    """Основной класс конфигурации PProg."""
    project_name: str = ""
    devices: list[Device] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    relays: list[Relay] = field(default_factory=list)
    scenarios: list[ManagementScenario] = field(default_factory=list)
    
    def add_device(self, device: Device):
        """Добавить устройство в конфигурацию."""
        self.devices.append(device)
    
    def add_partition(self, partition: Partition):
        """Добавить раздел в конфигурацию."""
        self.partitions.append(partition)
    
    def add_relay(self, relay: Relay):
        """Добавить реле в конфигурацию."""
        self.relays.append(relay)
    
    def add_scenario(self, scenario: ManagementScenario):
        """Добавить сценарий в конфигурацию."""
        self.scenarios.append(scenario)
    
    def get_device_by_address(self, address: int) -> Optional[Device]:
        """Найти устройство по адресу."""
        for device in self.devices:
            if device.address == address:
                return device
        return None
    
    def get_partition_by_id(self, partition_id: int) -> Optional[Partition]:
        """Найти раздел по ID."""
        for partition in self.partitions:
            if partition.partition_id == partition_id:
                return partition
        return None
    
    def validate(self) -> list[str]:
        """
        Валидация конфигурации.
        Возвращает список ошибок.
        """
        errors = []
        
        # Проверка на дубликаты адресов устройств
        addresses = [d.address for d in self.devices]
        duplicates = [addr for addr in addresses if addresses.count(addr) > 1]
        if duplicates:
            errors.append(f"Дубликаты адресов устройств: {set(duplicates)}")
        
        # Проверка на пустые обязательные поля
        for device in self.devices:
            if not device.device_type:
                errors.append(f"Устройство адреса {device.address} не имеет типа")
        
        # Проверка реле
        for relay in self.relays:
            if relay.program == RelayProgram.OFF and relay.partitions:
                errors.append(f"Реле {relay.full_address} выключено, но имеет привязанные разделы")
        
        return errors
