"""
Тесты для модуля распознавания схем (schema_recognizer).
"""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

# Импортируем модуль для тестирования
try:
    from modules.schema_recognizer import (
        SchemaAddressRecognizer,
        DetectedAddress,
        SchemaAnalysisResult,
        recognize_addresses_from_pdf,
        recognize_addresses_from_image,
        OPENCV_AVAILABLE,
        TESSERACT_AVAILABLE
    )
    MODULE_AVAILABLE = True
except ImportError as e:
    MODULE_AVAILABLE = False
    print(f"Модуль schema_recognizer недоступен: {e}")


class TestDetectedAddress(unittest.TestCase):
    """Тесты для класса DetectedAddress."""
    
    def test_create_detected_address(self):
        """Создание объекта DetectedAddress."""
        addr = DetectedAddress(
            text="ARK1",
            address_value=1,
            device_type="С2000-КДЛ-2И",
            location="верхняя левая часть",
            confidence=0.95,
            bbox=(100, 200, 50, 30),
            page_number=1
        )
        
        self.assertEqual(addr.text, "ARK1")
        self.assertEqual(addr.address_value, 1)
        self.assertEqual(addr.device_type, "С2000-КДЛ-2И")
        self.assertEqual(addr.location, "верхняя левая часть")
        self.assertAlmostEqual(addr.confidence, 0.95)
        self.assertEqual(addr.bbox, (100, 200, 50, 30))
        self.assertEqual(addr.page_number, 1)
    
    def test_default_values(self):
        """Проверка значений по умолчанию."""
        addr = DetectedAddress(text="Test")
        
        self.assertIsNone(addr.address_value)
        self.assertIsNone(addr.device_type)
        self.assertIsNone(addr.location)
        self.assertEqual(addr.confidence, 0.0)
        self.assertEqual(addr.bbox, (0, 0, 0, 0))
        self.assertEqual(addr.page_number, 0)
        self.assertEqual(addr.metadata, {})


class TestSchemaAnalysisResult(unittest.TestCase):
    """Тесты для класса SchemaAnalysisResult."""
    
    def test_create_result(self):
        """Создание результата анализа."""
        result = SchemaAnalysisResult()
        
        self.assertEqual(result.addresses, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.total_pages_processed, 0)
        self.assertEqual(result.images_extracted, 0)
    
    def test_add_address(self):
        """Добавление адреса в результат."""
        result = SchemaAnalysisResult()
        addr = DetectedAddress(text="ARK1", address_value=1)
        
        result.add_address(addr)
        
        self.assertEqual(len(result.addresses), 1)
        self.assertEqual(result.addresses[0].text, "ARK1")


@unittest.skipIf(not MODULE_AVAILABLE, "Модуль schema_recognizer недоступен")
class TestSchemaAddressRecognizer(unittest.TestCase):
    """Тесты для класса SchemaAddressRecognizer."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.recognizer = SchemaAddressRecognizer()
    
    def test_init_default(self):
        """Инициализация по умолчанию."""
        recognizer = SchemaAddressRecognizer()
        
        self.assertEqual(recognizer.lang, 'rus+eng')
        self.assertIsNone(recognizer.tesseract_cmd)
    
    def test_init_with_params(self):
        """Инициализация с параметрами."""
        recognizer = SchemaAddressRecognizer(
            tesseract_cmd='/usr/bin/tesseract',
            lang='eng'
        )
        
        self.assertEqual(recognizer.lang, 'eng')
        self.assertEqual(recognizer.tesseract_cmd, '/usr/bin/tesseract')
    
    @unittest.skipIf(not OPENCV_AVAILABLE or not TESSERACT_AVAILABLE, 
                     "OpenCV или Tesseract недоступны")
    def test_process_nonexistent_image(self):
        """Обработка несуществующего изображения."""
        result = self.recognizer.process_image('/nonexistent/path.png')
        
        self.assertEqual(len(result.errors), 1)
        self.assertIn('не найдено', result.errors[0].lower())
    
    def test_address_patterns(self):
        """Проверка паттернов адресов."""
        patterns = self.recognizer.ADDRESS_PATTERNS
        
        # Проверка наличия основных паттернов
        pattern_texts = [p[0] for p in patterns]
        
        self.assertTrue(any('ARK' in p for p in pattern_texts))
        self.assertTrue(any('SC' in p for p in pattern_texts))
        self.assertTrue(any('BTH' in p for p in pattern_texts))
        self.assertTrue(any('[Аа]дрес' in p for p in pattern_texts))
        self.assertTrue(any('№' in p for p in pattern_texts))
    
    def test_device_type_patterns(self):
        """Проверка паттернов типов устройств."""
        patterns = self.recognizer.DEVICE_TYPE_PATTERNS
        
        # Проверка наличия основных типов устройств
        self.assertIn('С2000М', patterns)
        self.assertIn('С2000-КДЛ-2И', patterns)
        self.assertIn('ДИП-34', patterns)
        self.assertIn('ИПР 513', patterns)


@unittest.skipIf(not MODULE_AVAILABLE, "Модуль schema_recognizer недоступен")
class TestHelperFunctions(unittest.TestCase):
    """Тесты для вспомогательных функций."""
    
    @unittest.skipIf(not OPENCV_AVAILABLE or not TESSERACT_AVAILABLE,
                     "OpenCV или Tesseract недоступны")
    def test_recognize_addresses_from_pdf_nonexistent(self):
        """Распознавание из несуществующего PDF."""
        result = recognize_addresses_from_pdf('/nonexistent/file.pdf')
        
        self.assertIsInstance(result, SchemaAnalysisResult)
        self.assertEqual(len(result.errors), 1)
    
    @unittest.skipIf(not OPENCV_AVAILABLE or not TESSERACT_AVAILABLE,
                     "OpenCV или Tesseract недоступны")
    def test_recognize_addresses_from_image_nonexistent(self):
        """Распознавание из несуществующего изображения."""
        result = recognize_addresses_from_image('/nonexistent/image.png')
        
        self.assertIsInstance(result, SchemaAnalysisResult)
        self.assertEqual(len(result.errors), 1)


@unittest.skipIf(not MODULE_AVAILABLE, "Модуль schema_recognizer недоступен")
class TestIntegration(unittest.TestCase):
    """Интеграционные тесты."""
    
    def setUp(self):
        """Создание тестового изображения."""
        # Создаем простое тестовое изображение
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        self.test_image[:] = 255  # Белый фон
    
    @unittest.skipIf(not OPENCV_AVAILABLE, "OpenCV недоступен")
    def test_process_numpy_image(self):
        """Обработка numpy массива как изображения."""
        recognizer = SchemaAddressRecognizer()
        
        # Тест должен завершиться без ошибок (даже если адресов не будет найдено)
        result = recognizer.process_image(self.test_image)
        
        self.assertIsInstance(result, SchemaAnalysisResult)
        self.assertEqual(result.images_extracted, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
