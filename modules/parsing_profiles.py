"""
Модуль управления профилями парсинга для различных проектных бюро.
Поддерживает разные форматы спецификаций и шаблоны извлечения данных.
"""

import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class SpecificationFormat(Enum):
    """Форматы спецификаций оборудования."""
    STANDARD = "standard"  # Стандартный формат Болид
    EXCEL_TABLE = "excel_table"  # Табличный формат из Excel
    TEXT_LIST = "text_list"  # Текстовый список
    CUSTOM = "custom"  # Пользовательский формат


@dataclass
class ParsingRule:
    """Правило извлечения данных из спецификации."""
    name: str
    pattern: str  # Regex паттерн
    field_mapping: dict[str, str]  # Маппинг групп regex на поля
    description: str = ""
    enabled: bool = True
    priority: int = 0  # Приоритет применения правила


@dataclass
class DeviceMapping:
    """Маппинг названий устройств на внутренние типы PProg."""
    source_pattern: str  # Паттерн для поиска в спецификации
    target_type: str  # Тип устройства в PProg
    pprog_type: str  # Внутренний тип PProg
    zone_type: Optional[str] = None
    algorithm: Optional[str] = None
    description: str = ""
    zone_types: list[str] = field(default_factory=list)  # Опциональный список типов зон


@dataclass
class ProfileMetadata:
    """Метаданные профиля парсинга."""
    profile_id: str
    name: str
    description: str
    bureau_name: str  # Название проектного бюро
    version: str
    created_at: str
    updated_at: str
    author: str = ""
    specification_format: SpecificationFormat = SpecificationFormat.STANDARD


@dataclass
class ParsingProfile:
    """Профиль парсинга для конкретного проектного бюро."""
    metadata: ProfileMetadata
    device_mappings: list[DeviceMapping] = field(default_factory=list)
    parsing_rules: list[ParsingRule] = field(default_factory=list)
    custom_patterns: dict[str, str] = field(default_factory=dict)
    settings: dict[str, any] = field(default_factory=dict)
    
    def add_device_mapping(self, mapping: DeviceMapping):
        """Добавить маппинг устройства."""
        self.device_mappings.append(mapping)
    
    def add_parsing_rule(self, rule: ParsingRule):
        """Добавить правило парсинга."""
        self.parsing_rules.append(rule)
        # Сортировка по приоритету
        self.parsing_rules.sort(key=lambda x: x.priority, reverse=True)
    
    def get_device_mapping(self, device_name: str) -> Optional[DeviceMapping]:
        """Найти маппинг для устройства по названию."""
        for mapping in self.device_mappings:
            if re.search(mapping.source_pattern, device_name, re.IGNORECASE):
                return mapping
        return None
    
    def get_parsing_rules(self, rule_type: Optional[str] = None) -> list[ParsingRule]:
        """Получить правила парсинга, опционально фильтруя по типу."""
        if rule_type is None:
            return [r for r in self.parsing_rules if r.enabled]
        return [r for r in self.parsing_rules if r.enabled and rule_type in r.name.lower()]
    
    def to_dict(self) -> dict:
        """Сериализация профиля в словарь."""
        return {
            'metadata': {
                **asdict(self.metadata),
                'specification_format': self.metadata.specification_format.value
            },
            'device_mappings': [asdict(m) for m in self.device_mappings],
            'parsing_rules': [asdict(r) for r in self.parsing_rules],
            'custom_patterns': self.custom_patterns,
            'settings': self.settings
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ParsingProfile':
        """Десериализация профиля из словаря."""
        metadata = ProfileMetadata(
            profile_id=data['metadata']['profile_id'],
            name=data['metadata']['name'],
            description=data['metadata']['description'],
            bureau_name=data['metadata']['bureau_name'],
            version=data['metadata']['version'],
            created_at=data['metadata']['created_at'],
            updated_at=data['metadata']['updated_at'],
            author=data['metadata'].get('author', ''),
            specification_format=SpecificationFormat(data['metadata'].get('specification_format', 'standard'))
        )
        
        profile = cls(metadata=metadata)
        
        # Восстановление маппингов устройств
        for m in data.get('device_mappings', []):
            profile.device_mappings.append(DeviceMapping(**m))
        
        # Восстановление правил парсинга
        for r in data.get('parsing_rules', []):
            profile.parsing_rules.append(ParsingRule(**r))
        
        # Восстановление паттернов и настроек
        profile.custom_patterns = data.get('custom_patterns', {})
        profile.settings = data.get('settings', {})
        
        return profile


class ProfileManager:
    """Менеджер профилей парсинга."""
    
    DEFAULT_PROFILES_DIR = Path(__file__).parent.parent / 'profiles'
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Инициализация менеджера профилей.
        
        Args:
            profiles_dir: Директория для хранения профилей
        """
        self.profiles_dir = profiles_dir or self.DEFAULT_PROFILES_DIR
        self.profiles: dict[str, ParsingProfile] = {}
        self.active_profile: Optional[ParsingProfile] = None
        
        # Создание директории если не существует
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Загрузка существующих профилей
        self._load_all_profiles()
    
    def _load_all_profiles(self):
        """Загрузить все профили из директории."""
        for profile_file in self.profiles_dir.glob('*.json'):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = ParsingProfile.from_dict(data)
                    self.profiles[profile.metadata.profile_id] = profile
            except Exception as e:
                print(f"Ошибка загрузки профиля {profile_file}: {e}")
    
    def create_profile(self, 
                       profile_id: str,
                       name: str,
                       bureau_name: str,
                       description: str = "",
                       author: str = "",
                       specification_format: SpecificationFormat = SpecificationFormat.STANDARD
                       ) -> ParsingProfile:
        """
        Создать новый профиль парсинга.
        
        Args:
            profile_id: Уникальный идентификатор профиля
            name: Отображаемое имя профиля
            bureau_name: Название проектного бюро
            description: Описание профиля
            author: Автор профиля
            specification_format: Формат спецификаций
            
        Returns:
            Созданный профиль
        """
        from datetime import datetime
        
        now = datetime.now().isoformat()
        
        metadata = ProfileMetadata(
            profile_id=profile_id,
            name=name,
            description=description,
            bureau_name=bureau_name,
            version="1.0.0",
            created_at=now,
            updated_at=now,
            author=author,
            specification_format=specification_format
        )
        
        profile = ParsingProfile(metadata=metadata)
        self.profiles[profile_id] = profile
        
        return profile
    
    def save_profile(self, profile_id: str) -> bool:
        """
        Сохранить профиль в файл.
        
        Args:
            profile_id: Идентификатор профиля для сохранения
            
        Returns:
            True если успешно
        """
        if profile_id not in self.profiles:
            return False
        
        profile = self.profiles[profile_id]
        profile_file = self.profiles_dir / f"{profile_id}.json"
        
        try:
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения профиля: {e}")
            return False
    
    def load_profile(self, profile_id: str) -> Optional[ParsingProfile]:
        """
        Загрузить профиль и сделать его активным.
        
        Args:
            profile_id: Идентификатор профиля
            
        Returns:
            Загруженный профиль или None
        """
        if profile_id in self.profiles:
            self.active_profile = self.profiles[profile_id]
            return self.active_profile
        
        # Попытка загрузить из файла
        profile_file = self.profiles_dir / f"{profile_id}.json"
        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = ParsingProfile.from_dict(data)
                    self.profiles[profile_id] = profile
                    self.active_profile = profile
                    return profile
            except Exception as e:
                print(f"Ошибка загрузки профиля: {e}")
        
        return None
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Удалить профиль.
        
        Args:
            profile_id: Идентификатор профиля для удаления
            
        Returns:
            True если успешно
        """
        if profile_id not in self.profiles:
            return False
        
        profile_file = self.profiles_dir / f"{profile_id}.json"
        try:
            if profile_file.exists():
                profile_file.unlink()
            del self.profiles[profile_id]
            if self.active_profile and self.active_profile.metadata.profile_id == profile_id:
                self.active_profile = None
            return True
        except Exception as e:
            print(f"Ошибка удаления профиля: {e}")
            return False
    
    def list_profiles(self) -> list[dict]:
        """Получить список всех доступных профилей."""
        return [
            {
                'profile_id': p.metadata.profile_id,
                'name': p.metadata.name,
                'bureau_name': p.metadata.bureau_name,
                'description': p.metadata.description,
                'version': p.metadata.version,
                'specification_format': p.metadata.specification_format.value
            }
            for p in self.profiles.values()
        ]
    
    def get_active_profile(self) -> Optional[ParsingProfile]:
        """Получить активный профиль."""
        return self.active_profile


def create_default_profiles():
    """Создать набор стандартных профилей для типовых проектных бюро."""
    manager = ProfileManager()
    
    # Профиль 1: Стандартный формат Болид
    standard_profile = manager.create_profile(
        profile_id="bolid_standard",
        name="Стандартный формат Болид",
        bureau_name="НВП Болид",
        description="Стандартный формат спецификаций от производителя",
        specification_format=SpecificationFormat.STANDARD
    )
    
    # Добавляем маппинги для стандартного формата
    standard_mappings = [
        DeviceMapping(
            source_pattern=r"С2000М",
            target_type="S2000M console",
            pprog_type="S2000M console",
            description="Прибор управления охранно-пожарный"
        ),
        DeviceMapping(
            source_pattern=r"С2000-КДЛ-2И",
            target_type="S2000-KDL-2I controller",
            pprog_type="S2000-KDL-2I controller",
            zone_types=["Smoke Analog Addressable", "Manual Call Points"],
            description="Контроллер двухпроводной линии связи"
        ),
        DeviceMapping(
            source_pattern=r"ДИП-34",
            target_type="Addressable Smoke Detector",
            pprog_type="Addressable Smoke Detector",
            zone_type="Smoke Analog Addressable",
            algorithm="B",
            description="Дымовой адресный извещатель"
        ),
        DeviceMapping(
            source_pattern=r"ИПР 513",
            target_type="Addressable Manual Call Point",
            pprog_type="Addressable Manual Call Point",
            zone_type="Manual Call Points",
            algorithm="A",
            description="Ручной адресный извещатель"
        ),
        DeviceMapping(
            source_pattern=r"С2000-СП2",
            target_type="S2000-SP2 relay module",
            pprog_type="S2000-SP2 relay module",
            description="Прибор релейный"
        ),
        DeviceMapping(
            source_pattern=r"С2000-БКИ",
            target_type="S2000-BKI interface module",
            pprog_type="S2000-BKI interface module",
            description="Блок клавиатурный"
        ),
    ]
    
    for mapping in standard_mappings:
        standard_profile.add_device_mapping(mapping)
    
    # Добавляем правила парсинга
    standard_profile.add_parsing_rule(ParsingRule(
        name="device_count",
        pattern=r"(С2000[^\d\s]*|[А-Я]{2,3}-?\d*[А-Я]?)\s*(?:исп\.?\d+)?(?:.*?)(\d+)\s*шт",
        field_mapping={"device_type": 1, "count": 2},
        description="Извлечение количества устройств",
        priority=10
    ))
    
    standard_profile.add_parsing_rule(ParsingRule(
        name="device_address",
        pattern=r"(?:адрес|№|ARK|SC)\s*(\d+)",
        field_mapping={"address": 1},
        description="Извлечение адресов устройств",
        priority=9
    ))
    
    manager.save_profile("bolid_standard")
    
    # Профиль 2: Табличный формат (Excel)
    excel_profile = manager.create_profile(
        profile_id="excel_table_format",
        name="Табличный формат (Excel)",
        bureau_name="Проектные бюро с Excel-спецификациями",
        description="Формат для спецификаций в виде таблиц Excel/CSV",
        specification_format=SpecificationFormat.EXCEL_TABLE
    )
    
    # Маппинги для табличного формата
    excel_mappings = [
        DeviceMapping(
            source_pattern=r".*Прибор.*С2000М.*",
            target_type="S2000M console",
            pprog_type="S2000M console",
            description="Прибор управления"
        ),
        DeviceMapping(
            source_pattern=r".*КДЛ.*",
            target_type="S2000-KDL-2I controller",
            pprog_type="S2000-KDL-2I controller",
            description="Контроллер КДЛ"
        ),
        DeviceMapping(
            source_pattern=r".*ДИП.*",
            target_type="Addressable Smoke Detector",
            pprog_type="Addressable Smoke Detector",
            zone_type="Smoke Analog Addressable",
            algorithm="B",
            description="Дымовой извещатель"
        ),
        DeviceMapping(
            source_pattern=r".*ИПР.*",
            target_type="Addressable Manual Call Point",
            pprog_type="Addressable Manual Call Point",
            zone_type="Manual Call Points",
            algorithm="A",
            description="Ручной извещатель"
        ),
    ]
    
    for mapping in excel_mappings:
        excel_profile.add_device_mapping(mapping)
    
    # Правила для табличного формата
    excel_profile.add_parsing_rule(ParsingRule(
        name="table_row",
        pattern=r"^([^\t]+)\t([^\t]+)\t(\d+)\t(.*)$",
        field_mapping={"name": 1, "type": 2, "count": 3, "location": 4},
        description="Парсинг строки таблицы (TAB-separated)",
        priority=10
    ))
    
    excel_profile.settings = {
        "delimiter": "\t",
        "has_header": True,
        "columns": {
            "name": 0,
            "type": 1,
            "count": 2,
            "location": 3
        }
    }
    
    manager.save_profile("excel_table_format")
    
    # Профиль 3: Текстовый список
    text_profile = manager.create_profile(
        profile_id="text_list_format",
        name="Текстовый список",
        bureau_name="Бюро с текстовыми спецификациями",
        description="Формат для спецификаций в виде простого текстового списка",
        specification_format=SpecificationFormat.TEXT_LIST
    )
    
    # Маппинги для текстового формата
    text_mappings = standard_mappings.copy()
    for mapping in text_mappings:
        text_profile.add_device_mapping(mapping)
    
    # Правила для текстового списка
    text_profile.add_parsing_rule(ParsingRule(
        name="list_item",
        pattern=r"^[•\-–]\s*(.+?)\s*[-–]\s*(\d+)\s*(?:шт\.?|единиц)?",
        field_mapping={"device_name": 1, "count": 2},
        description="Элемент маркированного списка",
        priority=10
    ))
    
    text_profile.add_parsing_rule(ParsingRule(
        name="numbered_item",
        pattern=r"^\d+\.\s*(.+?)\s*[-–]\s*(\d+)\s*(?:шт\.?|единиц)?",
        field_mapping={"device_name": 1, "count": 2},
        description="Элемент нумерованного списка",
        priority=9
    ))
    
    manager.save_profile("text_list_format")
    
    # Профиль 4: Пользовательский формат
    custom_profile = manager.create_profile(
        profile_id="custom_format",
        name="Пользовательский формат",
        bureau_name="Настраиваемый профиль",
        description="Шаблон для создания пользовательских профилей парсинга",
        specification_format=SpecificationFormat.CUSTOM,
        author=""
    )
    
    custom_profile.custom_patterns = {
        "device_pattern": "",
        "address_pattern": "",
        "location_pattern": ""
    }
    
    custom_profile.settings = {
        "use_regex": True,
        "case_sensitive": False,
        "multiline": True
    }
    
    manager.save_profile("custom_format")
    
    return manager


if __name__ == "__main__":
    # Создание стандартных профилей
    manager = create_default_profiles()
    
    print("Доступные профили:")
    for profile in manager.list_profiles():
        print(f"  - {profile['name']} ({profile['profile_id']})")
        print(f"    Бюро: {profile['bureau_name']}")
        print(f"    Формат: {profile['specification_format']}")
        print(f"    Версия: {profile['version']}")
        print()
