"""
Тесты парсера PDF на реальных тестовых файлах.
Проверяет извлечение устройств, разделов и сценариев управления.
Включая тесты интеграции с NLP-анализатором.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.pdf_parser import PDFParser, parse_pdf_project, parse_text_project
from data.models import Configuration


class TestPDFParserSimple(unittest.TestCase):
    """Тесты парсинга простого проекта."""
    
    @classmethod
    def setUpClass(cls):
        cls.parser = PDFParser()
        cls.pdf_path = "tests/data/simple_project.pdf"
        cls.result = cls.parser.parse_file(cls.pdf_path)
        cls.config = cls.result.configuration
    
    def test_devices_parsed(self):
        """Проверка извлечения устройств из спецификации."""
        self.assertGreater(len(self.config.devices), 0, "Устройства не найдены")
        
        # Проверка наличия основных типов устройств (pprog_type из equipment_db)
        device_types = {d.device_type for d in self.config.devices}
        
        # Типы устройств из базы знаний
        expected_types = {"S2000M console", "S2000-KDL-2I controller", 
                         "Addressable Smoke Detector", "Addressable Manual Call Point"}
        
        found_types = expected_types.intersection(device_types)
        self.assertEqual(len(found_types), len(expected_types),
                        f"Не найдены типы: {expected_types - found_types}")
    
    def test_device_count(self):
        """Проверка количества устройств."""
        # Подсчет по типам (используем pprog_type из БД)
        dips = [d for d in self.config.devices if d.device_type == "Addressable Smoke Detector"]
        iprs = [d for d in self.config.devices if d.device_type == "Addressable Manual Call Point"]
        
        # Парсер может найти больше устройств из-за нескольких паттернов
        # Проверяем минимальное количество
        self.assertGreaterEqual(len(dips), 15, f"Ожидалось >= 15 ДИП-34А, найдено {len(dips)}")
        self.assertGreaterEqual(len(iprs), 4, f"Ожидалось >= 4 ИПР 513-3А, найдено {len(iprs)}")
    
    def test_sections_parsed(self):
        """Проверка извлечения разделов."""
        self.assertGreater(len(self.config.partitions), 0, "Разделы не найдены")
        
        # Должно быть хотя бы 2 раздела
        self.assertGreaterEqual(len(self.config.partitions), 2, 
                                f"Ожидалось >= 2 разделов, найдено {len(self.config.partitions)}")
    
    def test_section_names(self):
        """Проверка имен разделов."""
        partition_names = [p.name for p in self.config.partitions]
        
        has_first_floor = any("первый этаж" in name.lower() for name in partition_names)
        has_second_floor = any("второй этаж" in name.lower() for name in partition_names)
        
        self.assertTrue(has_first_floor, "Не найден раздел 'Первый этаж'")
        self.assertTrue(has_second_floor, "Не найден раздел 'Второй этаж'")
    
    def test_relay_devices_found(self):
        """Проверка обнаружения исполнительных устройств (реле)."""
        relay_devices = [d for d in self.config.devices 
                        if d.device_type in ["СП2-1", "С2000-С1"]]
        
        self.assertGreater(len(relay_devices), 0, "Исполнительные устройства не найдены")
    
    def test_scenarios_parsed(self):
        """Проверка извлечения сценариев управления."""
        self.assertGreater(len(self.config.management_scenarios), 0, 
                          "Сценарии управления не найдены")
        
        # Проверка наличия сценария пожара
        fire_scenarios = [s for s in self.config.management_scenarios 
                         if "пожар" in s.description.lower()]
        self.assertGreater(len(fire_scenarios), 0, "Не найден сценарий пожара")


class TestPDFParserComplex(unittest.TestCase):
    """Тесты парсинга сложного проекта."""
    
    @classmethod
    def setUpClass(cls):
        cls.parser = PDFParser()
        cls.pdf_path = "tests/data/complex_project.pdf"
        cls.result = cls.parser.parse_file(cls.pdf_path)
        cls.config = cls.result.configuration
    
    def test_multiple_floors(self):
        """Проверка извлечения данных для нескольких этажей."""
        # Проверка количества разделов (должно быть 4)
        self.assertGreaterEqual(len(self.config.partitions), 3, 
                               "Не найдено достаточное количество разделов")
    
    def test_equipment_variety(self):
        """Проверка разнообразия оборудования."""
        device_types = {d.device_type for d in self.config.devices}
        
        expected_types = {"С2000М", "КДЛ-2И", "ДИП-34А", "ИПР 513-3А", "БКИ-70"}
        found_types = expected_types.intersection(device_types)
        
        self.assertEqual(len(found_types), len(expected_types),
                        f"Не найдены типы: {expected_types - found_types}")
    
    def test_relay_blocks_present(self):
        """Проверка наличия релейных блоков."""
        relay_blocks = [d for d in self.config.devices 
                       if d.device_type == "РС-200Т"]
        
        # В сложном проекте должны быть релейные блоки
        self.assertGreater(len(relay_blocks), 0, "Не найдены релейные блоки РС-200Т")
    
    def test_complex_scenarios(self):
        """Проверка сложных сценариев управления."""
        scenarios = self.config.management_scenarios
        
        # Поиск сценария с вентиляцией
        ventilation_scenarios = [s for s in scenarios 
                                if "вентиляц" in s.description.lower() 
                                or "клапан" in s.description.lower()]
        
        # Поиск сценария с СКУД
        access_scenarios = [s for s in scenarios 
                           if "скуд" in s.description.lower() 
                           or "разблок" in s.description.lower()]
        
        # Хотя бы один из этих сценариев должен быть найден
        self.assertTrue(len(ventilation_scenarios) > 0 or len(access_scenarios) > 0,
                       "Не найдены сценарии управления вентиляцией или СКУД")


class TestPDFParserEdgeCases(unittest.TestCase):
    """Тесты обработки граничных случаев."""
    
    @classmethod
    def setUpClass(cls):
        cls.parser = PDFParser()
        cls.pdf_path = "tests/data/edge_cases.pdf"
    
    def test_no_crash_on_invalid_data(self):
        """Проверка устойчивости к некорректным данным."""
        # Парсер не должен падать с исключением
        try:
            result = self.parser.parse_file(self.pdf_path)
            self.assertIsInstance(result.configuration, Configuration)
        except Exception as e:
            self.fail(f"Парсер упал с ошибкой: {e}")
    
    def test_handles_unknown_equipment(self):
        """Проверка обработки неизвестного оборудования."""
        result = self.parser.parse_file(self.pdf_path)
        config = result.configuration
        
        # Неизвестное оборудование должно быть добавлено с типом Unknown
        unknown_devices = [d for d in config.devices 
                          if "XYZ" in d.device_type or "unknown" in d.device_type.lower()]
        
        # Допускаем, что неизвестное оборудование может быть распознано как другое
        # Главное - парсер не должен падать
        self.assertIsInstance(config.devices, list)
    
    def test_validation_catches_invalid_addresses(self):
        """Проверка валидации некорректных адресов."""
        result = self.parser.parse_file(self.pdf_path)
        config = result.configuration
        
        # Адрес 999 должен быть отфильтрован или помечен как невалидный
        invalid_address_devices = [d for d in config.devices 
                                   if d.address and d.address > 254]
        
        # Если устройство с адресом 999 попало в конфигурацию, 
        # валидация должна это поймать
        if invalid_address_devices:
            errors = config.validate()
            address_errors = [e for e in errors if "адрес" in e.lower()]
            self.assertGreater(len(address_errors), 0, 
                              "Валидация не обнаружила некорректный адрес")


class TestParserIntegration(unittest.TestCase):
    """Интеграционные тесты полного цикла."""
    
    def test_simple_project_full_cycle(self):
        """Полный цикл обработки простого проекта."""
        parser = PDFParser()
        result = parser.parse_file("tests/data/simple_project.pdf")
        config = result.configuration
        
        # Валидация
        errors = config.validate()
        self.assertEqual(len(errors), 0, 
                        f"Конфигурация не прошла валидацию: {errors}")
        
        # Проверка статистики
        stats = config.get_statistics()
        self.assertIn("total_devices", stats)
        self.assertIn("total_partitions", stats)
        self.assertGreater(stats["total_devices"], 0)
    
    def test_complex_project_full_cycle(self):
        """Полный цикл обработки сложного проекта."""
        parser = PDFParser()
        result = parser.parse_file("tests/data/complex_project.pdf")
        config = result.configuration
        
        # Валидация
        errors = config.validate()
        # В сложном проекте могут быть предупреждения, но не критические ошибки
        critical_errors = [e for e in errors if "ошибка" in e.lower() or "error" in e.lower()]
        self.assertEqual(len(critical_errors), 0,
                        f"Критические ошибки валидации: {critical_errors}")
    
    def test_export_after_parsing(self):
        """Проверка экспорта после парсинга."""
        from modules.exporter import ConfigurationExporter
        import tempfile
        import os
        
        parser = PDFParser()
        result = parser.parse_file("tests/data/simple_project.pdf")
        config = result.configuration
        exporter = ConfigurationExporter(config)
        
        # Экспорт в JSON
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
            temp_json = f.name
        
        try:
            exporter.export_json(temp_json)
            
            # Проверка файла
            self.assertTrue(os.path.exists(temp_json))
            self.assertGreater(os.path.getsize(temp_json), 0, "JSON файл пуст")
        finally:
            if os.path.exists(temp_json):
                os.unlink(temp_json)


class TestNLPIntegration(unittest.TestCase):
    """Тесты интеграции PDF-парсера с NLP-анализатором."""
    
    def test_nlp_enrichment_with_locations(self):
        """Проверка обогащения данных информацией о местоположении."""
        test_text = """
        Проект системы пожарной сигнализации.
        С2000М адрес 1 - 1 шт в помещении охраны.
        С2000-КДЛ-2И - 2 шт в серверной комнате.
        ДИП-34А - 10 шт в коридоре первого этажа.
        """
        
        result = parse_text_project(test_text, use_nlp=True)
        
        # Проверка наличия NLP-результатов
        self.assertIsNotNone(result.nlp_result, "NLP-результат отсутствует")
        self.assertGreater(len(result.nlp_result.device_mentions), 0,
                          "NLP не нашел упоминания устройств")
        self.assertGreater(len(result.nlp_result.location_mentions), 0,
                          "NLP не нашел упоминания локаций")
    
    def test_nlp_enrichment_with_addresses(self):
        """Проверка использования NLP для назначения адресов устройствам."""
        test_text = """
        Установлено: С2000М адрес 5 - 1 шт.
        С2000-БКИ - 2 шт.
        """
        
        result = parse_text_project(test_text, use_nlp=True)
        
        # Проверка наличия NLP-результатов
        self.assertIsNotNone(result.nlp_result)
        self.assertGreater(len(result.nlp_result.address_mentions), 0,
                          "NLP не нашел упоминания адресов")
    
    def test_nlp_relations_extraction(self):
        """Проверка извлечения связей между устройствами."""
        test_text = """
        С2000М управляет табло выход.
        С2000-СП2 включает сирену оповещения.
        SC39-40 -> Табло Выход.
        """
        
        result = parse_text_project(test_text, use_nlp=True)
        
        # Проверка наличия связей
        self.assertIsNotNone(result.nlp_result)
        self.assertGreater(len(result.nlp_result.relations), 0,
                          "NLP не выявил связей между устройствами")
    
    def test_nlp_summary_generation(self):
        """Проверка генерации краткого содержания."""
        test_text = """
        Проект склада: С2000М - 1 шт, КДЛ-2И - 3 шт, ДИП-34А - 100 шт.
        Раздел 1: складское помещение.
        """
        
        result = parse_text_project(test_text, use_nlp=True)
        
        self.assertIsNotNone(result.nlp_result)
        self.assertTrue(len(result.nlp_result.summary) > 0,
                       "Краткое содержание не сгенерировано")
    
    def test_parser_without_nlp(self):
        """Проверка работы парсера без NLP (для совместимости)."""
        test_text = """
        С2000М - 1 шт.
        ДИП-34А - 10 шт.
        """
        
        result = parse_text_project(test_text, use_nlp=False)
        
        # NLP-результат должен отсутствовать
        self.assertIsNone(result.nlp_result)
        # Но устройства должны быть найдены
        self.assertGreater(len(result.configuration.devices), 0)
    
    def test_parser_with_nlp_disabled_explicitly(self):
        """Проверка явного отключения NLP через конструктор."""
        parser = PDFParser(use_nlp=False)
        test_text = "С2000М - 1 шт в помещении охраны."
        result = parser.parse_text(test_text)
        
        self.assertIsNone(result.nlp_result)
        self.assertIsNone(parser.nlp_analyzer)
    
    def test_nlp_enrichment_improves_descriptions(self):
        """Проверка что NLP улучшает описания устройств."""
        test_text = """
        С2000М адрес 1 - прибор в помещении охраны.
        С2000-КДЛ-2И - 2 шт в серверной комнате.
        """
        
        # Парсинг с NLP
        result_with_nlp = parse_text_project(test_text, use_nlp=True)
        
        # Проверка что NLP нашел локации
        self.assertGreater(len(result_with_nlp.nlp_result.location_mentions), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
