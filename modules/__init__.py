"""
Модули инструмента Project-to-PProg.
"""

from modules.pdf_parser import PDFParser, parse_pdf_project, parse_text_project
from modules.exporter import PProgExporter, export_configuration

try:
    from modules.nlp_analyzer import (
        RussianNLPAnalyzer,
        analyze_project_description,
        NLPAnalysisResult,
        ExtractedEntity,
        EntityCategory,
        NLP_AVAILABLE
    )
except ImportError:
    NLP_AVAILABLE = False

__all__ = [
    'PDFParser',
    'parse_pdf_project',
    'parse_text_project',
    'PProgExporter',
    'export_configuration',
    'RussianNLPAnalyzer',
    'analyze_project_description',
    'NLPAnalysisResult',
    'ExtractedEntity',
    'EntityCategory',
    'NLP_AVAILABLE',
]
