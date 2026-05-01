"""
Утилиты для приложения Project-to-PProg.
Вспомогательные функции и классы.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logging(log_file: Optional[str | Path] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Настроить логирование приложения.
    
    Args:
        log_file: Путь к файлу логов (опционально)
        level: Уровень логирования
        
    Returns:
        Настроенный logger
    """
    logger = logging.getLogger("ProjectToPProg")
    logger.setLevel(level)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик (если указан)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def generate_filename(prefix: str = "config", extension: str = "txt") -> str:
    """
    Сгенерировать имя файла с timestamp.
    
    Args:
        prefix: Префикс имени файла
        extension: Расширение файла
        
    Returns:
        Имя файла в формате: prefix_YYYYMMDD_HHMMSS.extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def validate_address(address: int, min_addr: int = 1, max_addr: int = 254) -> bool:
    """
    Проверить корректность адреса устройства.
    
    Args:
        address: Адрес для проверки
        min_addr: Минимальный допустимый адрес
        max_addr: Максимальный допустимый адрес
        
    Returns:
        True если адрес корректен
    """
    return min_addr <= address <= max_addr


def format_device_info(device) -> str:
    """
    Отформатировать информацию об устройстве для отображения.
    
    Args:
        device: Объект Device
        
    Returns:
        Форматированная строка
    """
    version_str = f" (исп.{device.version})" if device.version else ""
    return f"[{device.address}]{version_str} {device.device_type} - {device.description}"


def format_partition_info(partition) -> str:
    """
    Отформатировать информацию о разделе для отображения.
    
    Args:
        partition: Объект Partition
        
    Returns:
        Форматированная строка
    """
    status = "✓" if partition.enabled else "✗"
    return f"{status} Раздел {partition.partition_id}: {partition.name} ({len(partition.zones)} зон)"


def calculate_statistics(configuration) -> dict:
    """
    Подсчитать статистику конфигурации.
    
    Args:
        configuration: Объект Configuration
        
    Returns:
        Словарь со статистикой
    """
    total_zones = sum(len(p.zones) for p in configuration.partitions)
    
    # Подсчет типов устройств
    device_types = {}
    for device in configuration.devices:
        dtype = device.device_type
        device_types[dtype] = device_types.get(dtype, 0) + 1
    
    # Подсчет типов зон
    zone_types = {}
    for partition in configuration.partitions:
        for zone in partition.zones:
            ztype = zone.zone_type.value if hasattr(zone.zone_type, 'value') else str(zone.zone_type)
            zone_types[ztype] = zone_types.get(ztype, 0) + 1
    
    # Подсчет программ реле
    relay_programs = {}
    for relay in configuration.relays:
        pname = relay.program.name if hasattr(relay.program, 'name') else str(relay.program)
        relay_programs[pname] = relay_programs.get(pname, 0) + 1
    
    return {
        "devices_count": len(configuration.devices),
        "partitions_count": len(configuration.partitions),
        "zones_count": total_zones,
        "relays_count": len(configuration.relays),
        "scenarios_count": len(configuration.scenarios),
        "device_types": device_types,
        "zone_types": zone_types,
        "relay_programs": relay_programs,
        "validation_errors": len(configuration.validate())
    }


def get_summary_text(configuration) -> str:
    """
    Получить текстовую сводку конфигурации.
    
    Args:
        configuration: Объект Configuration
        
    Returns:
        Текстовая сводка
    """
    stats = calculate_statistics(configuration)
    
    lines = [
        "=" * 50,
        f"Проект: {configuration.project_name or 'Без названия'}",
        "=" * 50,
        "",
        "ОБЩАЯ СТАТИСТИКА:",
        f"  Устройств: {stats['devices_count']}",
        f"  Разделов: {stats['partitions_count']}",
        f"  Зон: {stats['zones_count']}",
        f"  Реле: {stats['relays_count']}",
        f"  Сценариев: {stats['scenarios_count']}",
        ""
    ]
    
    if stats['device_types']:
        lines.append("ТИПЫ УСТРОЙСТВ:")
        for dtype, count in sorted(stats['device_types'].items()):
            lines.append(f"  {dtype}: {count}")
        lines.append("")
    
    if stats['zone_types']:
        lines.append("ТИПЫ ЗОН:")
        for ztype, count in sorted(stats['zone_types'].items()):
            lines.append(f"  {ztype}: {count}")
        lines.append("")
    
    if stats['relay_programs']:
        lines.append("ПРОГРАММЫ РЕЛЕ:")
        for pname, count in sorted(stats['relay_programs'].items()):
            lines.append(f"  {pname}: {count}")
        lines.append("")
    
    if stats['validation_errors'] > 0:
        lines.append("ОШИБКИ ВАЛИДАЦИИ:")
        for error in configuration.validate():
            lines.append(f"  ⚠ {error}")
        lines.append("")
    else:
        lines.append("✓ Валидация пройдена без ошибок")
        lines.append("")
    
    lines.append("=" * 50)
    
    return "\n".join(lines)


# Глобальный logger
logger = setup_logging()
