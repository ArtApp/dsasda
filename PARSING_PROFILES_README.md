# Шаблоны проектов: Профили парсинга

## Обзор

Модуль `parsing_profiles.py` предоставляет систему управления профилями парсинга для различных проектных бюро. Каждый профиль содержит настройки для обработки спецификаций конкретного формата.

## Возможности

- **Профили парсинга** - Настройка правил извлечения данных под конкретное проектное бюро
- **Поддержка разных форматов**:
  - Стандартный формат Болид
  - Табличный формат (Excel/CSV)
  - Текстовый список
  - Пользовательский формат
- **Маппинг устройств** - Сопоставление названий из спецификации с типами PProg
- **Правила извлечения** - Regex-паттерны для парсинга различных форматов
- **Сериализация/Десериализация** - Сохранение профилей в JSON
- **Менеджер профилей** - Управление созданием, загрузкой и удалением профилей

## Установка

Модуль не требует дополнительных зависимостей beyond стандартной библиотеки Python.

## Быстрый старт

### Создание стандартных профилей

```python
from modules.parsing_profiles import create_default_profiles

# Создание набора стандартных профилей
manager = create_default_profiles()

# Список доступных профилей
for profile in manager.list_profiles():
    print(f"{profile['name']} ({profile['profile_id']})")
```

### Загрузка профиля

```python
from modules.parsing_profiles import ProfileManager

manager = ProfileManager()

# Загрузка профиля
profile = manager.load_profile("bolid_standard")

if profile:
    print(f"Активный профиль: {profile.metadata.name}")
    print(f"Формат: {profile.metadata.specification_format}")
```

### Создание пользовательского профиля

```python
from modules.parsing_profiles import (
    ProfileManager, 
    ParsingProfile, 
    DeviceMapping, 
    ParsingRule,
    SpecificationFormat
)

manager = ProfileManager()

# Создание нового профиля
profile = manager.create_profile(
    profile_id="my_bureau",
    name="Моё Проектное Бюро",
    bureau_name="ООО Пример",
    description="Спецификации в формате Word",
    specification_format=SpecificationFormat.CUSTOM
)

# Добавление маппингов устройств
profile.add_device_mapping(DeviceMapping(
    source_pattern=r"С2000.*Прибор",
    target_type="S2000M console",
    pprog_type="S2000M console",
    description="Прибор управления"
))

# Добавление правил парсинга
profile.add_parsing_rule(ParsingRule(
    name="word_table",
    pattern=r"([А-Я][а-я]+)\s+(\d+)\s+шт",
    field_mapping={"device": 1, "count": 2},
    description="Извлечение из таблицы Word",
    priority=10
))

# Сохранение профиля
manager.save_profile("my_bureau")
```

### Использование профиля при парсинге

```python
from modules.pdf_parser import PDFParser
from modules.parsing_profiles import ProfileManager

# Загрузка профиля
manager = ProfileManager()
profile = manager.load_profile("excel_table_format")

# Применение настроек профиля к парсеру
parser = PDFParser(use_nlp=True)

# Получение правил из профиля
rules = profile.get_parsing_rules()
for rule in rules:
    # Применение правил парсинга
    print(f"Правило: {rule.name}, Паттерн: {rule.pattern}")

# Парсинг документа
result = parser.parse_file("project_specification.pdf")
```

## Стандартные профили

### 1. bolid_standard

**Описание**: Стандартный формат спецификаций от НВП «Болид»

**Формат**: Standard

**Маппинги устройств**:
- С2000М → S2000M console
- С2000-КДЛ-2И → S2000-KDL-2I controller
- ДИП-34 → Addressable Smoke Detector (Algorithm B)
- ИПР 513 → Addressable Manual Call Point (Algorithm A)
- С2000-СП2 → S2000-SP2 relay module
- С2000-БКИ → S2000-BKI interface module

**Правила парсинга**:
- `device_count`: Извлечение количества устройств
- `device_address`: Извлечение адресов устройств

### 2. excel_table_format

**Описание**: Формат для спецификаций в виде таблиц Excel/CSV

**Формат**: Excel Table

**Настройки**:
- Разделитель: TAB
- Заголовок: есть
- Колонки: name, type, count, location

**Правила парсинга**:
- `table_row`: Парсинг строки таблицы (TAB-separated)

### 3. text_list_format

**Описание**: Формат для спецификаций в виде простого текстового списка

**Формат**: Text List

**Правила парсинга**:
- `list_item`: Элемент маркированного списка (•, -, –)
- `numbered_item`: Элемент нумерованного списка (1., 2., ...)

### 4. custom_format

**Описание**: Шаблон для создания пользовательских профилей

**Формат**: Custom

**Настройки**:
- use_regex: True
- case_sensitive: False
- multiline: True

**Пользовательские паттерны**:
- device_pattern: (настраивается)
- address_pattern: (настраивается)
- location_pattern: (настраивается)

## Структура профиля

```json
{
  "metadata": {
    "profile_id": "unique_id",
    "name": "Название профиля",
    "description": "Описание",
    "bureau_name": "Проектное бюро",
    "version": "1.0.0",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "author": "Автор",
    "specification_format": "standard"
  },
  "device_mappings": [
    {
      "source_pattern": "regex pattern",
      "target_type": "PProg type",
      "pprog_type": "internal type",
      "zone_type": "zone type",
      "algorithm": "A or B",
      "description": "Description"
    }
  ],
  "parsing_rules": [
    {
      "name": "rule_name",
      "pattern": "regex pattern",
      "field_mapping": {"field": "group"},
      "description": "Description",
      "enabled": true,
      "priority": 10
    }
  ],
  "custom_patterns": {},
  "settings": {}
}
```

## API Reference

### Классы

#### SpecificationFormat

Перечисление форматов спецификаций:
- `STANDARD` - Стандартный формат
- `EXCEL_TABLE` - Табличный формат
- `TEXT_LIST` - Текстовый список
- `CUSTOM` - Пользовательский формат

#### ParsingRule

Правило извлечения данных:
- `name`: Имя правила
- `pattern`: Regex паттерн
- `field_mapping`: Маппинг групп на поля
- `description`: Описание
- `enabled`: Статус активности
- `priority`: Приоритет применения

#### DeviceMapping

Маппинг устройства:
- `source_pattern`: Паттерн поиска
- `target_type`: Тип в PProg
- `pprog_type`: Внутренний тип
- `zone_type`: Тип зоны
- `algorithm`: Алгоритм (A/B)
- `description`: Описание

#### ParsingProfile

Профиль парсинга:
- `metadata`: Метаданные
- `device_mappings`: Список маппингов
- `parsing_rules`: Список правил
- `custom_patterns`: Пользовательские паттерны
- `settings`: Настройки

Методы:
- `add_device_mapping(mapping)` - Добавить маппинг
- `add_parsing_rule(rule)` - Добавить правило
- `get_device_mapping(name)` - Найти маппинг
- `get_parsing_rules(type)` - Получить правила
- `to_dict()` - Сериализация
- `from_dict(data)` - Десериализация

#### ProfileManager

Менеджер профилей:
- `create_profile(...)` - Создать профиль
- `save_profile(id)` - Сохранить профиль
- `load_profile(id)` - Загрузить профиль
- `delete_profile(id)` - Удалить профиль
- `list_profiles()` - Список профилей
- `get_active_profile()` - Активный профиль

## Хранение профилей

Профили хранятся в директории `profiles/` в формате JSON:

```
profiles/
├── bolid_standard.json
├── excel_table_format.json
├── text_list_format.json
└── custom_format.json
```

## Интеграция с PDF Parser

Для интеграции профилей с парсером PDF:

```python
from modules.pdf_parser import PDFParser
from modules.parsing_profiles import ProfileManager

class EnhancedPDFParser(PDFParser):
    def __init__(self, profile_id: str = None, use_nlp: bool = True):
        super().__init__(use_nlp=use_nlp)
        
        self.profile_manager = ProfileManager()
        if profile_id:
            self.active_profile = self.profile_manager.load_profile(profile_id)
        else:
            self.active_profile = self.profile_manager.load_profile("bolid_standard")
    
    def parse_with_profile(self, pdf_path: str):
        """Парсинг с применением активного профиля."""
        if not self.active_profile:
            return self.parse_file(pdf_path)
        
        # Применение правил из профиля
        rules = self.active_profile.get_parsing_rules()
        # ... логика парсинга с правилами
        
        return self.parse_file(pdf_path)
```

## Примеры использования

### Пример 1: Обработка спецификации из Excel

```python
from modules.parsing_profiles import ProfileManager

manager = ProfileManager()
profile = manager.load_profile("excel_table_format")

# Чтение Excel файла
import pandas as pd
df = pd.read_excel("specification.xlsx")

# Применение правил профиля
for _, row in df.iterrows():
    device_name = row.iloc[0]
    mapping = profile.get_device_mapping(device_name)
    
    if mapping:
        print(f"{device_name} → {mapping.target_type}")
```

### Пример 2: Кастомизация профиля

```python
from modules.parsing_profiles import ProfileManager, DeviceMapping, ParsingRule

manager = ProfileManager()
profile = manager.load_profile("custom_format")

# Добавление специфичных маппингов
profile.add_device_mapping(DeviceMapping(
    source_pattern=r"Арт\.\s*12345",
    target_type="Custom Device",
    pprog_type="Custom Type",
    description="Специфичное устройство"
))

# Добавление кастомных правил
profile.add_parsing_rule(ParsingRule(
    name="custom_format",
    pattern=r"ART-(\d+)-(\w+)",
    field_mapping={"series": 1, "type": 2},
    priority=100
))

# Сохранение изменений
manager.save_profile("custom_format")
```

## Расширение функциональности

### Добавление нового формата

```python
from modules.parsing_profiles import SpecificationFormat

# Добавление нового формата в Enum
class SpecificationFormat(Enum):
    STANDARD = "standard"
    EXCEL_TABLE = "excel_table"
    TEXT_LIST = "text_list"
    CUSTOM = "custom"
    XML_FORMAT = "xml"  # Новый формат
```

### Создание шаблона для нового бюро

```python
def create_bureau_profile(manager, bureau_name, format_type):
    profile = manager.create_profile(
        profile_id=f"{bureau_name.lower().replace(' ', '_')}",
        name=bureau_name,
        bureau_name=bureau_name,
        specification_format=format_type
    )
    
    # Добавление специфичных маппингов
    # ...
    
    manager.save_profile(profile.metadata.profile_id)
    return profile
```

## Тестирование

```python
def test_profile_loading():
    manager = ProfileManager()
    
    # Проверка загрузки всех стандартных профилей
    profiles = manager.list_profiles()
    assert len(profiles) == 4
    
    # Проверка загрузки конкретного профиля
    profile = manager.load_profile("bolid_standard")
    assert profile is not None
    assert profile.metadata.specification_format.value == "standard"
    
    print("Все тесты пройдены!")

test_profile_loading()
```

## Лицензия

[Укажите лицензию вашего проекта]
