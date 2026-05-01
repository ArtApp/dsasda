"""
База знаний по оборудованию «Болид»
Связывает модели устройств из проектов с их внутренними идентификаторами и параметрами в PProg.
"""

EQUIPMENT_DATABASE = {
    # Приборы управления и индикации
    "С2000М исп.02": {
        "pprog_type": "S2000M console",
        "device_template": "S2000M",
        "description": "Прибор управления охранно-пожарный"
    },
    "С2000М": {
        "pprog_type": "S2000M console",
        "device_template": "S2000M",
        "description": "Прибор управления охранно-пожарный"
    },
    
    # Контроллеры двухпроводной линии связи
    "С2000-КДЛ-2И исп.01": {
        "pprog_type": "S2000-KDL-2I controller",
        "device_template": "S2000-KDL-2I",
        "zone_types": ["Smoke Analog Addressable", "Manual Call Points", "Heat Analog Addressable"],
        "description": "Контроллер двухпроводной линии связи"
    },
    "С2000-КДЛ-2И": {
        "pprog_type": "S2000-KDL-2I controller",
        "device_template": "S2000-KDL-2I",
        "zone_types": ["Smoke Analog Addressable", "Manual Call Points", "Heat Analog Addressable"],
        "description": "Контроллер двухпроводной линии связи"
    },
    
    # Адресные дымовые извещатели
    "ДИП-34А-03": {
        "pprog_type": "Addressable Smoke Detector",
        "parent_device_template": "S2000-KDL Template",
        "zone_type": "Smoke Analog Addressable",
        "algorithm": "B",
        "description": "Извещатель пожарный дымовой адресный"
    },
    "ДИП-34А": {
        "pprog_type": "Addressable Smoke Detector",
        "parent_device_template": "S2000-KDL Template",
        "zone_type": "Smoke Analog Addressable",
        "algorithm": "B",
        "description": "Извещатель пожарный дымовой адресный"
    },
    
    # Адресные ручные извещатели
    "ИПР 513-ЗАМ исп.01": {
        "pprog_type": "Addressable Manual Call Point",
        "parent_device_template": "S2000-KDL Template",
        "zone_type": "Manual Call Points",
        "algorithm": "A",
        "description": "Извещатель пожарный ручной адресный"
    },
    "ИПР 513-3А": {
        "pprog_type": "Addressable Manual Call Point",
        "parent_device_template": "S2000-KDL Template",
        "zone_type": "Manual Call Points",
        "algorithm": "A",
        "description": "Извещатель пожарный ручной адресный"
    },
    
    # Адресные комбинированные извещатели
    "С2000-ИПДЛ": {
        "pprog_type": "Addressable Multi-Sensor Detector",
        "parent_device_template": "S2000-KDL Template",
        "zone_type": "Multi-Sensor Analog Addressable",
        "algorithm": "B",
        "description": "Извещатель пожарный дымовой линейный адресный"
    },
    
    # Приборы интерфейсные
    "С2000-БКИ": {
        "pprog_type": "S2000-BKI interface module",
        "device_template": "S2000-BKI",
        "description": "Блок клавиатурный интерфейс"
    },
    "С2000-БКИ исп.02": {
        "pprog_type": "S2000-BKI interface module",
        "device_template": "S2000-BKI",
        "description": "Блок клавиатурный интерфейс"
    },
    
    # Приборы релейные
    "С2000-СП2 исп.01": {
        "pprog_type": "S2000-SP2 relay module",
        "device_template": "S2000-SP2",
        "relay_count": 2,
        "description": "Прибор приемно-контрольный и управления релейный"
    },
    "С2000-СП2": {
        "pprog_type": "S2000-SP2 relay module",
        "device_template": "S2000-SP2",
        "relay_count": 2,
        "description": "Прибор приемно-контрольный и управления релейный"
    },
    
    # Оповещатели
    "Маяк-12-3М": {
        "pprog_type": "Sound/Strobe Notification Appliance",
        "description": "Оповещатель светозвуковой"
    },
    "Табло Выход": {
        "pprog_type": "Exit Sign",
        "description": "Табло эвакуационного выхода"
    },
    
    # Сетевые преобразователи
    "RS-200T": {
        "pprog_type": "RS-200T network converter",
        "device_template": "RS-200T",
        "description": "Преобразователь интерфейсов"
    }
}

# Программы управления реле
RELAY_PROGRAMS = {
    0: {"name": "Off", "description": "Реле выключено"},
    1: {"name": "Lamp", "description": "Лампа (постоянно включено)"},
    2: {"name": "Siren", "description": "Сирена (мигание с паузой)"},
    3: {"name": "Blink", "description": "Мигание"},
    4: {"name": "ASPT", "description": "Управление АСПТ"},
    5: {"name": "Duct Damper", "description": "Управление клапаном дымоудаления"},
    6: {"name": "Fan", "description": "Управление вентилятором"},
    7: {"name": "Door Lock", "description": "Управление замком"},
}

# Алгоритмы принятия решения о пожаре
FIRE_ALGORITHMS = {
    "A": {
        "name": "Algorithm A",
        "description": "Для ИПР - срабатывание по одному извещателю",
        "applicable_zones": ["Manual Call Points"]
    },
    "B": {
        "name": "Algorithm B", 
        "description": "Для ДИП и ИПДЛ - срабатывание по двум извещателям",
        "applicable_zones": ["Smoke Analog Addressable", "Heat Analog Addressable", "Multi-Sensor Analog Addressable"]
    }
}


def get_device_info(device_name: str) -> dict | None:
    """Получить информацию об устройстве по названию."""
    # Точное совпадение
    if device_name in EQUIPMENT_DATABASE:
        return EQUIPMENT_DATABASE[device_name]
    
    # Частичное совпадение
    for key, value in EQUIPMENT_DATABASE.items():
        if key.lower() in device_name.lower() or device_name.lower() in key.lower():
            return value
    
    return None


def get_relay_program(program_id: int) -> dict | None:
    """Получить информацию о программе управления реле."""
    return RELAY_PROGRAMS.get(program_id)


def get_fire_algorithm(algorithm_id: str) -> dict | None:
    """Получить информацию об алгоритме пожара."""
    return FIRE_ALGORITHMS.get(algorithm_id.upper())
