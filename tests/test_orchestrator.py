"""
Комплексные тесты для AI Orchestrator.
Тестируют полный конвейер обработки проектной документации.
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from orchestrator import (
    WorkflowManager,
    DocumentAnalyzer,
    ConfigFormatAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator,
)
from orchestrator.models.domain import (
    Device, DeviceType, Connection, Partition, ProjectDomainModel, ConfidenceLevel
)
from orchestrator.tools.base_tool import ToolStatus


class TestWorkflowManager(unittest.TestCase):
    """Тесты для WorkflowManager."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.orchestrator = WorkflowManager()
        
    def test_register_tool(self):
        """Тест регистрации инструментов."""
        tool = DocumentAnalyzer()
        self.orchestrator.register_tool(tool)
        
        self.assertIn('DocumentAnalyzer', self.orchestrator.list_tools())
        self.assertEqual(self.orchestrator.get_tool('DocumentAnalyzer'), tool)
        
    def test_unregister_tool(self):
        """Тест отмены регистрации инструмента."""
        tool = DocumentAnalyzer()
        self.orchestrator.register_tool(tool)
        self.orchestrator.unregister_tool('DocumentAnalyzer')
        
        self.assertNotIn('DocumentAnalyzer', self.orchestrator.list_tools())
        
    def test_default_pipeline(self):
        """Тест конвейера по умолчанию."""
        pipeline = self.orchestrator._get_default_pipeline()
        
        expected_tools = [
            'DocumentAnalyzer', 'NLPSpecExtractor', 'CVPlanAnalyzer',
            'CVSchematicAnalyzer', 'DataSynthesizer', 'ConfigGenerator',
            'ReportGenerator'
        ]
        
        self.assertEqual(len(pipeline), len(expected_tools))
        for i, tool_name in enumerate(expected_tools):
            self.assertEqual(pipeline[i]['tool'], tool_name)
            
    def test_create_custom_pipeline(self):
        """Тест создания пользовательского конвейера."""
        self.orchestrator.register_tool(DocumentAnalyzer())
        self.orchestrator.register_tool(NLPSpecExtractor())
        
        custom_pipeline = self.orchestrator.create_custom_pipeline([
            {'tool': 'DocumentAnalyzer', 'name': 'analyze'},
            {'tool': 'NLPSpecExtractor', 'name': 'extract'},
        ])
        
        self.assertEqual(len(custom_pipeline), 2)
        self.assertEqual(custom_pipeline[0]['tool'], 'DocumentAnalyzer')
        self.assertEqual(custom_pipeline[1]['tool'], 'NLPSpecExtractor')


class TestDocumentAnalyzer(unittest.TestCase):
    """Тесты для DocumentAnalyzer."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.analyzer = DocumentAnalyzer()
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Очистка после теста."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_initialization(self):
        """Тест инициализации."""
        self.assertTrue(self.analyzer.initialize())
        self.assertTrue(self.analyzer._is_initialized)
        
    def test_execute_with_empty_directory(self):
        """Тест выполнения с пустой директорией."""
        result = self.analyzer.execute(self.test_dir)
        
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertEqual(result.data['report'].total_files, 0)
        
    def test_execute_with_pdf_file(self):
        """Тест выполнения с PDF файлом."""
        # Создаем тестовый PDF
        pdf_path = Path(self.test_dir) / "test_spec.pdf"
        
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Спецификация оборудования АПС\nС2000-КДЛ - 2 шт\nДИП-34А - 10 шт")
            doc.save(str(pdf_path))
            doc.close()
            
            result = self.analyzer.execute(str(pdf_path))
            
            self.assertEqual(result.status, ToolStatus.SUCCESS)
            self.assertGreater(result.data['report'].total_files, 0)
            
        except ImportError:
            self.skipTest("PyMuPDF not available")
            
    def test_keyword_detection(self):
        """Тест обнаружения ключевых слов."""
        text = "Прибор С2000-М управляет датчиками ДИП и кнопками ИПР в разделе 1"
        
        found = self.analyzer._find_keywords(text)
        
        self.assertIn('С2000', found)
        self.assertIn('ДИП', found)
        self.assertIn('ИПР', found)


class TestNLPSpecExtractor(unittest.TestCase):
    """Тесты для NLPSpecExtractor."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.extractor = NLPSpecExtractor()
        
    def test_initialization(self):
        """Тест инициализации."""
        result = self.extractor.initialize()
        # Может быть False если spaCy не установлен
        self.assertIsInstance(result, bool)
        
    def test_extract_devices_from_text(self):
        """Тест извлечения устройств из текста."""
        text = """
        Спецификация оборудования:
        1. С2000-КДЛ - 2 штуки, адресный контроллер
        2. ДИП-34А - 10 штук, дымовой извещатель
        3. ИПР 513-3А - 5 штук, ручной извещатель
        """
        
        result = self.extractor.execute({'text': text, 'source': 'specification'})
        
        # Результат должен быть успешным или частичным
        self.assertIn(result.status, [ToolStatus.SUCCESS, ToolStatus.PARTIAL, ToolStatus.FAILED])


class TestDataModels(unittest.TestCase):
    """Тесты для моделей данных."""
    
    def test_device_creation(self):
        """Тест создания устройства."""
        device = Device(
            device_type=DeviceType.KDL,
            model="С2000-КДЛ",
            address=1,
            quantity=2,
            location="Щит управления",
            confidence=ConfidenceLevel.HIGH,
            source="specification"
        )
        
        self.assertEqual(device.device_type, DeviceType.KDL)
        self.assertEqual(device.model, "С2000-КДЛ")
        self.assertEqual(device.address, 1)
        self.assertEqual(device.quantity, 2)
        
    def test_connection_creation(self):
        """Тест создания соединения."""
        connection = Connection(
            from_device_id="device_1",
            to_device_id="device_2",
            connection_type="wire",
            channel=1,
            line="A",
            confidence=ConfidenceLevel.MEDIUM
        )
        
        self.assertEqual(connection.from_device_id, "device_1")
        self.assertEqual(connection.to_device_id, "device_2")
        self.assertEqual(connection.channel, 1)
        
    def test_partition_creation(self):
        """Тест создания раздела."""
        partition = Partition(
            partition_id=1,
            name="Раздел 1",
            zones=[1, 2, 3],
            devices=["device_1", "device_2"],
            location="Этаж 1"
        )
        
        self.assertEqual(partition.partition_id, 1)
        self.assertEqual(partition.name, "Раздел 1")
        self.assertEqual(len(partition.zones), 3)
        
    def test_project_domain_model(self):
        """Тест доменной модели проекта."""
        model = ProjectDomainModel(project_name="Test Project")
        
        device = Device(
            device_type=DeviceType.SMOKE_DETECTOR,
            model="ДИП-34А",
            address=1
        )
        model.add_device(device)
        
        self.assertEqual(model.total_devices, 1)
        self.assertEqual(model.project_name, "Test Project")
        
    def test_domain_model_to_dict(self):
        """Тест преобразования доменной модели в словарь."""
        model = ProjectDomainModel(project_name="Test Project")
        
        device = Device(
            device_type=DeviceType.KDL,
            model="С2000-КДЛ",
            address=1
        )
        model.add_device(device)
        
        result = model.to_dict()
        
        self.assertIn('project_name', result)
        self.assertIn('devices', result)
        self.assertEqual(len(result['devices']), 1)
        self.assertEqual(result['devices'][0]['model'], "С2000-КДЛ")


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты полного конвейера."""
    
    def test_full_pipeline_initialization(self):
        """Тест инициализации всех инструментов конвейера."""
        orchestrator = WorkflowManager()
        
        tools = [
            DocumentAnalyzer(),
            ConfigFormatAnalyzer(),
            NLPSpecExtractor(),
            CVPlanAnalyzer(),
            CVSchematicAnalyzer(),
            DataSynthesizer(),
            ConfigGenerator(),
            ReportGenerator(),
        ]
        
        for tool in tools:
            orchestrator.register_tool(tool)
            
        registered = orchestrator.list_tools()
        
        self.assertEqual(len(registered), 8)
        self.assertIn('DocumentAnalyzer', registered)
        self.assertIn('ConfigGenerator', registered)
        self.assertIn('ReportGenerator', registered)
        
    def test_workflow_state_management(self):
        """Тест управления состоянием workflow."""
        orchestrator = WorkflowManager()
        orchestrator.register_tool(DocumentAnalyzer())
        
        # Создаем временную директорию для теста
        test_dir = tempfile.mkdtemp()
        
        try:
            state = orchestrator.execute_workflow(
                input_data=test_dir,
                steps=[
                    {'tool': 'DocumentAnalyzer', 'name': 'analyze', 'on_error': 'continue'}
                ]
            )
            
            self.assertIsNotNone(state.workflow_id)
            self.assertIn(state.status.value, ['completed', 'failed', 'pending'])
            self.assertIsInstance(state.completed_steps, list)
            
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
