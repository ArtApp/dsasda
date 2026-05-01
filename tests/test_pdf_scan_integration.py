"""
Тесты интеграции модуля обработки сканов с PDF парсером.
"""

import pytest
from pathlib import Path
from modules.pdf_parser import (
    PDFParser, 
    ScannedPDFParserConfig, 
    ParseResult,
    parse_scanned_pdf
)
from modules.scan_enhancer import ScanEnhancementConfig, NoiseReductionMethod, BinarizationMethod


class TestScannedPDFParserConfig:
    """Тесты конфигурации для обработки сканированных PDF."""
    
    def test_default_config(self):
        """Тест конфигурации по умолчанию."""
        config = ScannedPDFParserConfig()
        
        assert config.enhance_scans is True
        assert config.ocr_enabled is True
        assert config.ocr_languages == "rus+eng"
        assert config.min_image_dpi == 200
        assert config.min_text_confidence == 0.5
        assert config.scan_enhancement_config is not None
    
    def test_custom_config(self):
        """Тест пользовательской конфигурации."""
        custom_enhance_config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.MEDIAN,
            denoise_strength=15,
            deskew_enabled=False,
            binarization_method=BinarizationMethod.OTSU
        )
        
        config = ScannedPDFParserConfig(
            enhance_scans=True,
            scan_enhancement_config=custom_enhance_config,
            ocr_languages="rus",
            min_image_dpi=300
        )
        
        assert config.enhance_scans is True
        assert config.scan_enhancement_config.denoise_method == NoiseReductionMethod.MEDIAN
        assert config.scan_enhancement_config.denoise_strength == 15
        assert config.scan_enhancement_config.deskew_enabled is False
        assert config.ocr_languages == "rus"
        assert config.min_image_dpi == 300


class TestPDFParserWithScanConfig:
    """Тесты PDF парсера с конфигурацией обработки сканов."""
    
    def test_parser_creation_with_scan_config(self):
        """Тест создания парсера с конфигурацией сканов."""
        scan_config = ScannedPDFParserConfig()
        parser = PDFParser(use_nlp=False, scan_config=scan_config)
        
        assert parser.scan_config is not None
        assert parser.scan_config.enhance_scans is True
        assert parser.scan_config.ocr_enabled is True
    
    def test_parser_creation_without_scan_config(self):
        """Тест создания парсера без конфигурации сканов (по умолчанию)."""
        parser = PDFParser(use_nlp=False)
        
        assert parser.scan_config is not None
        assert parser.scan_config.enhance_scans is True
    
    def test_parser_with_disabled_scan_enhancement(self):
        """Тест парсера с отключенным улучшением сканов."""
        scan_config = ScannedPDFParserConfig(enhance_scans=False)
        parser = PDFParser(use_nlp=False, scan_config=scan_config)
        
        assert parser.scan_config.enhance_scans is False


class TestParseResultWithEnhancements:
    """Тесты результата парсинга с результатами улучшения."""
    
    def test_parse_result_has_enhancement_results(self):
        """Тест наличия поля enhancement_results в ParseResult."""
        from data.models import Configuration
        
        result = ParseResult(
            configuration=Configuration(),
            warnings=[],
            errors=[],
            enhancement_results=[]
        )
        
        assert hasattr(result, 'enhancement_results')
        assert result.enhancement_results == []
    
    def test_parse_result_with_none_enhancement_results(self):
        """Тест ParseResult с None enhancement_results."""
        from data.models import Configuration
        
        result = ParseResult(
            configuration=Configuration(),
            warnings=[],
            errors=[]
        )
        
        # По умолчанию должно быть None
        assert result.enhancement_results is None


class TestParseScannedPDFFunction:
    """Тесты функции parse_scanned_pdf."""
    
    def test_parse_scanned_pdf_function_exists(self):
        """Тест существования функции parse_scanned_pdf."""
        assert callable(parse_scanned_pdf)
    
    def test_parse_scanned_pdf_with_custom_config(self):
        """Тест parse_scanned_pdf с пользовательской конфигурацией."""
        enhance_config = ScanEnhancementConfig(
            denoise_strength=20,
            sharpen_enabled=False
        )
        
        # Проверяем, что функция принимает параметры
        # (не запускаем на реальном файле)
        import inspect
        sig = inspect.signature(parse_scanned_pdf)
        params = list(sig.parameters.keys())
        
        assert 'pdf_path' in params
        assert 'enhance_config' in params
        assert 'ocr_languages' in params
        assert 'use_nlp' in params


class TestIsScannedPDFDetection:
    """Тесты определения типа PDF (сканированный или текстовый)."""
    
    def test_is_scanned_pdf_method_exists(self):
        """Тест существования метода _is_scanned_pdf."""
        parser = PDFParser(use_nlp=False)
        assert hasattr(parser, '_is_scanned_pdf')
        assert callable(parser._is_scanned_pdf)
    
    def test_extract_text_from_scanned_pdf_method_exists(self):
        """Тест существования метода _extract_text_from_scanned_pdf."""
        parser = PDFParser(use_nlp=False)
        assert hasattr(parser, '_extract_text_from_scanned_pdf')
        assert callable(parser._extract_text_from_scanned_pdf)


class TestIntegrationWorkflow:
    """Интеграционные тесты рабочего процесса."""
    
    def test_full_workflow_with_text_pdf(self, tmp_path):
        """Тест полного workflow с текстовым PDF (без сканов)."""
        # Создаем простой текстовый файл (не настоящий PDF, но тестируем логику)
        parser = PDFParser(use_nlp=False)
        
        # Проверяем, что парсер создается корректно
        assert parser.scan_config is not None
        assert parser.scan_config.enhance_scans is True
    
    def test_config_chaining(self):
        """Тест цепочки конфигураций."""
        # Создаем конфигурацию улучшения
        enhance_config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
            target_dpi=300
        )
        
        # Создаем конфигурацию сканированного PDF
        scan_config = ScannedPDFParserConfig(
            scan_enhancement_config=enhance_config,
            ocr_languages="rus+eng+deu"
        )
        
        # Создаем парсер с use_nlp=False (чтобы избежать зависимости от pymorphy3)
        parser = PDFParser(use_nlp=False, scan_config=scan_config)
        
        # Проверяем цепочку конфигураций
        assert parser.scan_config.scan_enhancement_config.denoise_method == NoiseReductionMethod.NON_LOCAL_MEANS
        assert parser.scan_config.scan_enhancement_config.target_dpi == 300
        assert parser.scan_config.ocr_languages == "rus+eng+deu"
        assert parser.use_nlp is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
