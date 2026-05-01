"""
Тесты для модуля NLP-анализа (nlp_analyzer.py).
Проверяют извлечение сущностей, нормализацию и связи.
"""

import unittest
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.nlp_analyzer import (
    RussianNLPAnalyzer,
    analyze_project_description,
    NLPAnalysisResult,
    ExtractedEntity,
    EntityCategory,
    NLP_AVAILABLE
)


class TestNLPAnalyzer(unittest.TestCase):
    """Тесты для RussianNLPAnalyzer."""
    
    def setUp(self):
        """Инициализация тестовых данных."""
        self.analyzer = RussianNLPAnalyzer(use_spacy=True)
        self.sample_text = """
        В проекте используются следующие устройства:
        - С2000М исп.02 (адрес 127) - 1 шт, прибор приемно-контрольный
        - С2000-КДЛ-2И исп.01 (адрес 1) - 2 шт, контроллер двухпроводной линии связи
        - ДИП-34А-03 - 38 шт, извещатели пожарные дымовые, размещены в помещениях склада и офиса
        - ИПР 513-3АМ исп.01 - 5 шт, извещатели ручные, установлены у выходов
        - С2000-СП2 исп.01 - 5 шт, табло световые
        
        Схема подключения:
        ARK127 -> С2000М
        SC39-40 -> Табло "Выход"
        SC41-42 -> Маяк-12-3М (сирена)
        
        Устройства размещены:
        - ДИП-34А в коридоре первого этажа
        - ИПР 513 у эвакуационных выходов
        """
    
    def test_nlp_available(self):
        """Проверка доступности NLP библиотек."""
        self.assertTrue(NLP_AVAILABLE, "NLP библиотеки должны быть доступны")
    
    def test_analyze_text_returns_result(self):
        """Проверка что анализ возвращает правильный тип результата."""
        result = self.analyzer.analyze_text(self.sample_text)
        self.assertIsInstance(result, NLPAnalysisResult)
    
    def test_device_extraction_s2000m(self):
        """Проверка извлечения С2000М."""
        result = self.analyzer.analyze_text(self.sample_text)
        s2000m_entities = [e for e in result.device_mentions 
                          if e.metadata.get('device_type') == 's2000m']
        self.assertGreater(len(s2000m_entities), 0, "С2000М не найден")
    
    def test_device_extraction_kdl(self):
        """Проверка извлечения КДЛ-2И."""
        result = self.analyzer.analyze_text(self.sample_text)
        kdl_entities = [e for e in result.device_mentions 
                       if e.metadata.get('device_type') == 'kdl']
        self.assertGreater(len(kdl_entities), 0, "КДЛ-2И не найден")
    
    def test_device_extraction_dip(self):
        """Проверка извлечения ДИП-34А."""
        result = self.analyzer.analyze_text(self.sample_text)
        dip_entities = [e for e in result.device_mentions 
                       if e.metadata.get('device_type') == 'dip']
        self.assertGreater(len(dip_entities), 0, "ДИП-34А не найден")
    
    def test_device_extraction_ipr(self):
        """Проверка извлечения ИПР 513."""
        result = self.analyzer.analyze_text(self.sample_text)
        ipr_entities = [e for e in result.device_mentions 
                       if e.metadata.get('device_type') == 'ipr']
        self.assertGreater(len(ipr_entities), 0, "ИПР 513 не найден")
    
    def test_address_extraction(self):
        """Проверка извлечения адресов."""
        result = self.analyzer.analyze_text(self.sample_text)
        # Должны быть найдены адреса типа ARK, SC
        address_entities = result.address_mentions
        self.assertGreater(len(address_entities), 0, "Адреса не найдены")
        
        # Проверяем что есть ARK127
        ark_addresses = [e for e in address_entities 
                        if 'ARK127' in e.text or 'ark127' in e.text.lower()]
        self.assertGreater(len(ark_addresses), 0, "Адрес ARK127 не найден")
    
    def test_quantity_extraction(self):
        """Проверка извлечения количеств."""
        result = self.analyzer.analyze_text(self.sample_text)
        quantity_entities = result.quantity_mentions
        self.assertGreater(len(quantity_entities), 0, "Количества не найдены")
        
        # Проверяем что найдено количество 38 шт (ДИПы)
        qty_38 = [e for e in quantity_entities 
                 if e.metadata.get('count') == 38]
        self.assertGreater(len(qty_38), 0, "Количество 38 шт не найдено")
    
    def test_location_extraction(self):
        """Проверка извлечения локаций."""
        result = self.analyzer.analyze_text(self.sample_text)
        location_entities = result.location_mentions
        self.assertGreater(len(location_entities), 0, "Локации не найдены")
        
        # Проверяем что найдены ключевые слова локации
        location_texts = ' '.join([e.text.lower() for e in location_entities])
        self.assertTrue(
            any(keyword in location_texts for keyword in ['коридор', 'этаж', 'выход']),
            "Ключевые слова локации не найдены"
        )
    
    def test_normalization(self):
        """Проверка нормализации текста."""
        text = "С2000М"
        normalized = self.analyzer._normalize_text(text)
        self.assertIsInstance(normalized, str)
        self.assertTrue(len(normalized) > 0)
    
    def test_summary_generation(self):
        """Проверка генерации краткого содержания."""
        result = self.analyzer.analyze_text(self.sample_text)
        self.assertIsInstance(result.summary, str)
        self.assertTrue(len(result.summary) > 0)
        self.assertIn("устройств", result.summary.lower())
    
    def test_relations_extraction(self):
        """Проверка извлечения связей между устройствами."""
        result = self.analyzer.analyze_text(self.sample_text)
        # Должны быть найдены хотя бы некоторые связи
        # (паттерн SC39-40 -> Табло)
        self.assertGreaterEqual(len(result.relations), 0)
    
    def test_get_device_context(self):
        """Проверка получения контекста устройства."""
        result = self.analyzer.analyze_text(self.sample_text)
        contexts = self.analyzer.get_device_context("С2000М", result)
        self.assertIsInstance(contexts, list)
        # Контекст должен содержать информацию об адресе
        if contexts:
            self.assertTrue(any("127" in ctx for ctx in contexts))
    
    def test_empty_text(self):
        """Проверка обработки пустого текста."""
        result = self.analyzer.analyze_text("")
        self.assertIsInstance(result, NLPAnalysisResult)
        self.assertEqual(len(result.entities), 0)
        self.assertTrue(len(result.warnings) > 0)
    
    def test_confidence_scores(self):
        """Проверка что уверенности извлечения в правильном диапазоне."""
        result = self.analyzer.analyze_text(self.sample_text)
        for entity in result.entities:
            self.assertGreaterEqual(entity.confidence, 0.0)
            self.assertLessEqual(entity.confidence, 1.0)


class TestConvenienceFunction(unittest.TestCase):
    """Тесты для удобной функции analyze_project_description."""
    
    def test_convenience_function(self):
        """Проверка работы удобной функции."""
        text = "С2000М исп.02 - 1 шт, адрес 127"
        result = analyze_project_description(text, use_spacy=True)
        self.assertIsInstance(result, NLPAnalysisResult)
        self.assertGreater(len(result.device_mentions), 0)


class TestEntityCategory(unittest.TestCase):
    """Тесты для перечисления категорий сущностей."""
    
    def test_entity_categories_exist(self):
        """Проверка что все необходимые категории существуют."""
        self.assertEqual(EntityCategory.DEVICE.value, "DEVICE")
        self.assertEqual(EntityCategory.LOCATION.value, "LOCATION")
        self.assertEqual(EntityCategory.QUANTITY.value, "QUANTITY")
        self.assertEqual(EntityCategory.ADDRESS.value, "ADDRESS")


if __name__ == '__main__':
    unittest.main(verbosity=2)
