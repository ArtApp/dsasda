"""
Тесты для утилит Project-to-PProg.
"""

import unittest
from pathlib import Path
import tempfile

from data.models import Configuration, Device, Partition, Zone, Relay, ZoneType, RelayProgram
from utils.helpers import (
    generate_filename,
    validate_address,
    format_device_info,
    format_partition_info,
    calculate_statistics,
    get_summary_text
)


class TestHelpers(unittest.TestCase):
    """Тесты вспомогательных функций."""
    
    def test_generate_filename(self):
        """Тест генерации имени файла."""
        filename = generate_filename("test", "txt")
        self.assertTrue(filename.startswith("test_"))
        self.assertTrue(filename.endswith(".txt"))
        
        filename_json = generate_filename("config", "json")
        self.assertTrue(filename_json.endswith(".json"))
    
    def test_validate_address_valid(self):
        """Тест валидации корректного адреса."""
        self.assertTrue(validate_address(1))
        self.assertTrue(validate_address(127))
        self.assertTrue(validate_address(254))
        self.assertTrue(validate_address(100, 50, 150))
    
    def test_validate_address_invalid(self):
        """Тест валидации некорректного адреса."""
        self.assertFalse(validate_address(0))
        self.assertFalse(validate_address(255))
        self.assertFalse(validate_address(-1))
        self.assertFalse(validate_address(10, 20, 30))
    
    def test_format_device_info(self):
        """Тест форматирования информации об устройстве."""
        device = Device(address=127, device_type="S2000M console", description="Прибор управления", version="02")
        info = format_device_info(device)
        
        self.assertIn("[127]", info)
        self.assertIn("S2000M console", info)
        self.assertIn("Прибор управления", info)
        self.assertIn("исп.02", info)
    
    def test_format_device_info_no_version(self):
        """Тест форматирования без версии."""
        device = Device(address=1, device_type="S2000-KDL-2I controller", description="КДЛ")
        info = format_device_info(device)
        
        self.assertIn("[1]", info)
        self.assertNotIn("исп.", info)
    
    def test_format_partition_info_enabled(self):
        """Тест форматирования включенного раздела."""
        partition = Partition(partition_id=1, name="Раздел 1", enabled=True)
        partition.add_zone(Zone(zone_number=1, zone_type=ZoneType.SMOKE_ANALOG, address=1))
        partition.add_zone(Zone(zone_number=2, zone_type=ZoneType.SMOKE_ANALOG, address=2))
        
        info = format_partition_info(partition)
        
        self.assertIn("✓", info)
        self.assertIn("Раздел 1", info)
        self.assertIn("2 зон", info)
    
    def test_format_partition_info_disabled(self):
        """Тест форматирования отключенного раздела."""
        partition = Partition(partition_id=2, name="Раздел 2", enabled=False)
        info = format_partition_info(partition)
        
        self.assertIn("✗", info)
    
    def test_calculate_statistics_empty(self):
        """Тест статистики пустой конфигурации."""
        config = Configuration()
        stats = calculate_statistics(config)
        
        self.assertEqual(stats["devices_count"], 0)
        self.assertEqual(stats["partitions_count"], 0)
        self.assertEqual(stats["zones_count"], 0)
        self.assertEqual(stats["relays_count"], 0)
    
    def test_calculate_statistics_full(self):
        """Тест статистики полной конфигурации."""
        config = Configuration(project_name="Test Project")
        
        # Добавляем устройства
        config.add_device(Device(address=127, device_type="S2000M console"))
        config.add_device(Device(address=1, device_type="S2000-KDL-2I controller"))
        config.add_device(Device(address=1, device_type="S2000-KDL-2I controller"))  # Дубликат типа
        
        # Добавляем раздел с зонами
        partition = Partition(partition_id=1, name="Раздел 1")
        partition.add_zone(Zone(zone_number=1, zone_type=ZoneType.SMOKE_ANALOG, address=1))
        partition.add_zone(Zone(zone_number=2, zone_type=ZoneType.MANUAL_CALL_POINT, address=2))
        config.add_partition(partition)
        
        # Добавляем реле
        config.add_relay(Relay(device_address=39, relay_number=1, program=RelayProgram.LAMP))
        config.add_relay(Relay(device_address=39, relay_number=2, program=RelayProgram.SIREN))
        
        stats = calculate_statistics(config)
        
        self.assertEqual(stats["devices_count"], 3)
        self.assertEqual(stats["partitions_count"], 1)
        self.assertEqual(stats["zones_count"], 2)
        self.assertEqual(stats["relays_count"], 2)
        
        # Проверка типов устройств
        self.assertEqual(stats["device_types"]["S2000M console"], 1)
        self.assertEqual(stats["device_types"]["S2000-KDL-2I controller"], 2)
        
        # Проверка программ реле
        self.assertEqual(stats["relay_programs"]["LAMP"], 1)
        self.assertEqual(stats["relay_programs"]["SIREN"], 1)
    
    def test_get_summary_text(self):
        """Тест текстовой сводки."""
        config = Configuration(project_name="Summary Test")
        config.add_device(Device(address=127, device_type="S2000M console"))
        
        partition = Partition(partition_id=1, name="Раздел 1")
        partition.add_zone(Zone(zone_number=1, zone_type=ZoneType.SMOKE_ANALOG, address=1))
        config.add_partition(partition)
        
        summary = get_summary_text(config)
        
        self.assertIn("Summary Test", summary)
        self.assertIn("Устройств: 1", summary)
        self.assertIn("Разделов: 1", summary)
        self.assertIn("Зон: 1", summary)
        self.assertIn("Валидация пройдена", summary)
    
    def test_get_summary_text_with_errors(self):
        """Тест сводки с ошибками валидации."""
        config = Configuration()
        # Добавляем дубликаты адресов
        config.add_device(Device(address=1, device_type="Type1"))
        config.add_device(Device(address=1, device_type="Type2"))
        
        summary = get_summary_text(config)
        
        self.assertIn("ОШИБКИ ВАЛИДАЦИИ", summary)
        self.assertIn("⚠", summary)


if __name__ == '__main__':
    unittest.main()
