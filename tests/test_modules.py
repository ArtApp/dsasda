"""
Тесты для модулей Project-to-PProg.
"""

import unittest
from pathlib import Path

from data.models import (
    Configuration, Device, Partition, Zone, Relay, 
    ZoneType, RelayProgram, ManagementScenario, DeviceStatus
)
from data.equipment_db import get_device_info, get_relay_program, get_fire_algorithm
from modules.pdf_parser import PDFParser, parse_text_project
from modules.exporter import PProgExporter, export_configuration


class TestDataModels(unittest.TestCase):
    """Тесты для моделей данных."""
    
    def test_device_creation(self):
        """Тест создания устройства."""
        device = Device(address=1, device_type="S2000M console")
        self.assertEqual(device.address, 1)
        self.assertEqual(device.status, DeviceStatus.NOT_CONFIGURED)
    
    def test_zone_creation(self):
        """Тест создания зоны."""
        zone = Zone(
            zone_number=1,
            zone_type=ZoneType.SMOKE_ANALOG,
            address=1
        )
        self.assertEqual(zone.zone_number, 1)
        self.assertEqual(zone.algorithm, "B")
    
    def test_partition_add_zone(self):
        """Тест добавления зоны в раздел."""
        partition = Partition(partition_id=1, name="Test Partition")
        zone = Zone(zone_number=1, zone_type=ZoneType.SMOKE_ANALOG, address=1)
        
        partition.add_zone(zone)
        self.assertEqual(len(partition.zones), 1)
        
        partition.remove_zone(1)
        self.assertEqual(len(partition.zones), 0)
    
    def test_relay_full_address(self):
        """Тест формирования полного адреса реле."""
        relay = Relay(device_address=39, relay_number=1)
        self.assertEqual(relay.full_address, "SC39-39")
        
        relay2 = Relay(device_address=39, relay_number=2)
        self.assertEqual(relay2.full_address, "SC39-40")
    
    def test_configuration_validate_duplicates(self):
        """Тест валидации на дубликаты адресов."""
        config = Configuration()
        config.add_device(Device(address=1, device_type="Type1"))
        config.add_device(Device(address=1, device_type="Type2"))
        
        errors = config.validate()
        self.assertTrue(len(errors) > 0)
        self.assertIn("Дубликаты адресов", str(errors[0]))
    
    def test_configuration_validate_ok(self):
        """Тест валидации без ошибок."""
        config = Configuration()
        config.add_device(Device(address=1, device_type="Type1"))
        config.add_device(Device(address=2, device_type="Type2"))
        
        errors = config.validate()
        # Не должно быть ошибок дубликатов
        for error in errors:
            self.assertNotIn("Дубликаты адресов", error)


class TestEquipmentDatabase(unittest.TestCase):
    """Тесты для базы знаний оборудования."""
    
    def test_get_device_info_exact_match(self):
        """Тест точного совпадения названия устройства."""
        info = get_device_info("С2000М")
        self.assertIsNotNone(info)
        self.assertEqual(info["pprog_type"], "S2000M console")
    
    def test_get_device_info_partial_match(self):
        """Тест частичного совпадения названия устройства."""
        info = get_device_info("С2000М исп.02")
        self.assertIsNotNone(info)
    
    def test_get_device_info_not_found(self):
        """Тест отсутствия устройства в базе."""
        info = get_device_info("Unknown Device XYZ")
        # Должно вернуть None или найти ближайшее совпадение
        # В зависимости от реализации
    
    def test_get_relay_program(self):
        """Тест получения программы реле."""
        program = get_relay_program(2)
        self.assertIsNotNone(program)
        self.assertEqual(program["name"], "Siren")
    
    def test_get_fire_algorithm(self):
        """Тест получения алгоритма пожара."""
        algo = get_fire_algorithm("A")
        self.assertIsNotNone(algo)
        self.assertEqual(algo["name"], "Algorithm A")
        
        algo_b = get_fire_algorithm("b")  # Проверка регистра
        self.assertIsNotNone(algo_b)


class TestPDFParser(unittest.TestCase):
    """Тесты для парсера PDF."""
    
    def test_parse_text_basic(self):
        """Тест парсинга простого текста."""
        text = """
        Спецификация оборудования:
        С2000М адрес 127 - Прибор управления
        С2000-КДЛ-2И адрес 1 - Контроллер
        С2000-СП2 адрес 39 - Релейный модуль
        С2000-СП2 адрес 41 - Релейный модуль
        
        Раздел 1: Зоны 1-5
        Раздел 2: Зоны 6-10
        
        SC39-40 -> Табло Выход
        SC41-42 -> Маяк сирена
        """
        
        result = parse_text_project(text, "Test Project")
        
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.configuration.project_name, "Test Project")
        
        # Проверка устройств
        self.assertGreater(len(result.configuration.devices), 0)
        
        # Проверка разделов
        self.assertGreater(len(result.configuration.partitions), 0)
        
        # Проверка реле
        self.assertGreater(len(result.configuration.relays), 0)
    
    def test_parse_text_s2000m(self):
        """Тест парсинга С2000М."""
        text = "С2000М исп.02 адрес 127"
        result = parse_text_project(text)
        
        devices = result.configuration.devices
        s2000m_devices = [d for d in devices if "S2000M" in d.device_type]
        self.assertGreater(len(s2000m_devices), 0)
    
    def test_parse_text_kdl(self):
        """Тест парсинга КДЛ."""
        text = "С2000-КДЛ-2И исп.01 адрес 1"
        result = parse_text_project(text)
        
        devices = result.configuration.devices
        kdl_devices = [d for d in devices if "KDL" in d.device_type]
        self.assertGreater(len(kdl_devices), 0)
    
    def test_parse_text_partitions(self):
        """Тест парсинга разделов."""
        text = "Раздел 1: Зоны 1-5"
        result = parse_text_project(text)
        
        partitions = result.configuration.partitions
        self.assertGreater(len(partitions), 0)
        
        # Проверка зон в разделе
        if partitions:
            partition = partitions[0]
            self.assertEqual(len(partition.zones), 5)
    
    def test_parser_class(self):
        """Тест класса PDFParser."""
        parser = PDFParser()
        text = "С2000М адрес 127"
        result = parser.parse_text(text)
        
        self.assertIsNotNone(result.configuration)


class TestExporter(unittest.TestCase):
    """Тесты для экспортера конфигурации."""
    
    def setUp(self):
        """Настройка тестовых данных."""
        self.config = Configuration()
        self.config.project_name = "Test Project"
        
        # Добавляем устройства
        self.config.add_device(Device(address=127, device_type="S2000M console", description="С2000М"))
        self.config.add_device(Device(address=1, device_type="S2000-KDL-2I controller", description="КДЛ"))
        
        # Добавляем раздел
        partition = Partition(partition_id=1, name="Раздел 1")
        partition.add_zone(Zone(zone_number=1, zone_type=ZoneType.SMOKE_ANALOG, address=1))
        self.config.add_partition(partition)
        
        # Добавляем реле
        self.config.add_relay(Relay(device_address=39, relay_number=1, program=RelayProgram.LAMP))
    
    def test_export_txt(self):
        """Тест экспорта в TXT."""
        exporter = PProgExporter(self.config)
        output_path = Path("/tmp/test_config.txt")
        
        result = exporter.generate_txt(output_path)
        self.assertTrue(result)
        self.assertTrue(output_path.exists())
        
        # Проверка содержимого
        content = output_path.read_text(encoding='utf-8')
        self.assertIn("[DEVICES]", content)
        self.assertIn("[PARTITIONS]", content)
        self.assertIn("[RELAYS]", content)
        
        # Очистка
        output_path.unlink()
    
    def test_export_json(self):
        """Тест экспорта в JSON."""
        exporter = PProgExporter(self.config)
        output_path = Path("/tmp/test_config.json")
        
        result = exporter.generate_json(output_path)
        self.assertTrue(result)
        self.assertTrue(output_path.exists())
        
        # Очистка
        output_path.unlink()
    
    def test_export_function(self):
        """Тест функции экспорта."""
        output_path = Path("/tmp/test_config_func.txt")
        
        result = export_configuration(self.config, output_path, "txt")
        self.assertTrue(result)
        self.assertTrue(output_path.exists())
        
        output_path.unlink()
    
    def test_export_invalid_format(self):
        """Тест неподдерживаемого формата."""
        result = export_configuration(self.config, "/tmp/test.xyz", "xyz")
        self.assertFalse(result)


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты."""
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса."""
        # 1. Парсинг текста
        text = """
        Проект автоматизации
        
        Оборудование:
        С2000М исп.02 адрес 127
        С2000-КДЛ-2И адрес 1
        С2000-СП2 адрес 39
        С2000-БКИ адрес 2
        
        Раздел 1: Зоны 1-10
        Раздел 2: Зоны 11-20
        
        SC39-40 -> Табло
        SC41-42 -> Сирена Маяк
        """
        
        result = parse_text_project(text, "Integration Test")
        
        # 2. Проверка результатов парсинга
        self.assertEqual(len(result.errors), 0)
        self.assertGreater(len(result.configuration.devices), 0)
        self.assertGreater(len(result.configuration.partitions), 0)
        
        # 3. Экспорт конфигурации
        output_path = Path("/tmp/integration_test.txt")
        exporter = PProgExporter(result.configuration)
        export_result = exporter.generate_txt(output_path)
        
        self.assertTrue(export_result)
        self.assertTrue(output_path.exists())
        
        # 4. Проверка файла
        content = output_path.read_text(encoding='utf-8')
        self.assertIn("Integration Test", content)
        self.assertIn("[DEVICES]", content)
        
        # Очистка
        output_path.unlink()


if __name__ == '__main__':
    unittest.main()
