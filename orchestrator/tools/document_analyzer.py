"""
Document Analyzer - ИИ-инструмент для анализа входных файлов проектной документации.
Этап 1: Исследование, Анализ и Сбор Базовых Данных

Функции:
- Определение типов файлов (PDF, DWG, PNG и т.п.)
- Извлечение текста из PDF/DOCX
- OCR для сканированных документов
- Извлечение изображений из PDF/DWG
- Генерация отчета о входных данных
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


@dataclass
class DocumentInfo:
    """Информация о документе."""
    file_path: str
    file_type: str
    file_size_bytes: int
    page_count: int = 0
    text_length: int = 0
    image_count: int = 0
    image_resolutions: List[Tuple[int, int]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_scanned: bool = False
    ocr_required: bool = False


@dataclass
class AnalysisReport:
    """Отчет об анализе документов."""
    total_files: int
    documents: List[DocumentInfo] = field(default_factory=list)
    total_text_length: int = 0
    total_images: int = 0
    file_types: Dict[str, int] = field(default_factory=dict)
    keywords_found: List[str] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class DocumentAnalyzer(AITool):
    """
    ИИ-инструмент для анализа входной проектной документации.
    
    Принимает архив/каталог с проектной документацией и выполняет:
    - Классификацию типов файлов
    - Извлечение текста (с OCR для сканов)
    - Извлечение изображений
    - Поиск ключевых слов
    - Генерацию отчета
    """
    
    # Ключевые слова для поиска в документации АПС
    KEYWORDS_APS = [
        'С2000', 'Болид', 'ДИП', 'ИПР', 'ПК', 'ППКП',
        'дымовой', 'пожарный', 'извещатель', 'датчик',
        'раздел', 'зона', 'адрес', 'шлейф',
        'спецификация', 'ведомость', 'план', 'схема',
        'АПС', 'АУПТ', 'СОУЭ', 'КУД', 'ОПС',
    ]
    
    SUPPORTED_FORMATS = {
        '.pdf': 'PDF',
        '.dwg': 'DWG',
        '.dxf': 'DXF',
        '.png': 'PNG',
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.tiff': 'TIFF',
        '.docx': 'DOCX',
        '.doc': 'DOC',
        '.txt': 'TXT',
        '.xlsx': 'XLSX',
        '.xls': 'XLS',
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("DocumentAnalyzer", config)
        self.keywords = self.config.get('keywords', self.KEYWORDS_APS)
        self.use_ocr = self.config.get('use_ocr', True)
        self.ocr_languages = self.config.get('ocr_languages', 'rus+eng')
        
        # Lazy imports для опциональных зависимостей
        self._pymupdf = None
        self._easyocr = None
        self._cv2 = None
    
    def _initialize(self):
        """Инициализация зависимостей."""
        try:
            import fitz  # PyMuPDF
            self._pymupdf = fitz
            logger.info("PyMuPDF initialized")
        except ImportError:
            logger.warning("PyMuPDF not available, PDF parsing limited")
        
        if self.use_ocr:
            try:
                import easyocr
                self._easyocr = easyocr.Reader(['ru', 'en'], gpu=False)
                logger.info("EasyOCR initialized")
            except ImportError:
                logger.warning("EasyOCR not available, OCR disabled")
        
        try:
            import cv2
            self._cv2 = cv2
            logger.info("OpenCV initialized")
        except ImportError:
            logger.warning("OpenCV not available")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить анализ документов.
        
        Args:
            input_data: Путь к каталогу/архиву или список файлов
            
        Returns:
            ToolResult с отчетом об анализе
        """
        start_time = time.time()
        
        try:
            # Определение входных данных
            if isinstance(input_data, str):
                input_path = Path(input_data)
                if input_path.is_dir():
                    files = self._scan_directory(input_path)
                elif input_path.is_file():
                    files = [input_path]
                else:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        errors=[f"Path not found: {input_path}"],
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )
            elif isinstance(input_data, list):
                files = [Path(f) for f in input_data]
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data type. Expected str (path) or list of paths."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Анализ каждого файла
            documents = []
            for file_path in files:
                doc_info = self._analyze_file(file_path)
                if doc_info:
                    documents.append(doc_info)
            
            # Генерация отчета
            report = self._generate_report(documents)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    'report': report,
                    'documents': [
                        {
                            'file_path': d.file_path,
                            'file_type': d.file_type,
                            'file_size_bytes': d.file_size_bytes,
                            'page_count': d.page_count,
                            'text_length': d.text_length,
                            'image_count': d.image_count,
                            'is_scanned': d.is_scanned,
                            'keywords': d.keywords,
                        }
                        for d in documents
                    ],
                },
                metadata={
                    'total_files': report.total_files,
                    'file_types': report.file_types,
                    'total_text_length': report.total_text_length,
                    'total_images': report.total_images,
                },
                warnings=[f"OCR not available for {sum(1 for d in documents if d.ocr_required)} files"] if any(d.ocr_required for d in documents) else [],
                execution_time_ms=execution_time,
                confidence=0.95,
            )
            
        except Exception as e:
            logger.exception(f"Error in DocumentAnalyzer: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _scan_directory(self, directory: Path) -> List[Path]:
        """Сканировать директорию на наличие поддерживаемых файлов."""
        files = []
        for ext in self.SUPPORTED_FORMATS.keys():
            files.extend(directory.glob(f"**/*{ext}"))
            files.extend(directory.glob(f"**/*{ext.upper()}"))
        return sorted(files)
    
    def _analyze_file(self, file_path: Path) -> Optional[DocumentInfo]:
        """Анализировать отдельный файл."""
        if not file_path.exists():
            return None
        
        ext = file_path.suffix.lower()
        file_type = self.SUPPORTED_FORMATS.get(ext, 'UNKNOWN')
        
        doc_info = DocumentInfo(
            file_path=str(file_path),
            file_type=file_type,
            file_size_bytes=file_path.stat().st_size,
        )
        
        # Анализ в зависимости от типа файла
        if ext == '.pdf':
            self._analyze_pdf(file_path, doc_info)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff']:
            self._analyze_image(file_path, doc_info)
        elif ext in ['.docx', '.doc']:
            self._analyze_docx(file_path, doc_info)
        elif ext == '.txt':
            self._analyze_txt(file_path, doc_info)
        else:
            # Для неподдерживаемых форматов - только базовая информация
            pass
        
        return doc_info
    
    def _analyze_pdf(self, file_path: Path, doc_info: DocumentInfo):
        """Анализ PDF файла."""
        if not self._pymupdf:
            return
        
        try:
            doc = self._pymupdf.open(file_path)
            doc_info.page_count = len(doc)
            
            full_text = ""
            images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Извлечение текста
                text = page.get_text()
                full_text += text
                
                # Извлечение изображений
                image_list = page.get_images(full=True)
                images.extend(image_list)
            
            doc_info.text_length = len(full_text)
            doc_info.image_count = len(images)
            
            # Проверка на сканированный документ
            if doc_info.text_length < doc_info.page_count * 50:  # Мало текста на страницу
                doc_info.is_scanned = True
                doc_info.ocr_required = self.use_ocr
            
            # Поиск ключевых слов
            doc_info.keywords = self._find_keywords(full_text)
            
            doc.close()
            
        except Exception as e:
            logger.warning(f"Error analyzing PDF {file_path}: {e}")
    
    def _analyze_image(self, file_path: Path, doc_info: DocumentInfo):
        """Анализ изображения."""
        if self._cv2:
            try:
                img = self._cv2.imread(str(file_path))
                if img is not None:
                    height, width = img.shape[:2]
                    doc_info.image_resolutions.append((width, height))
                    doc_info.image_count = 1
            except Exception as e:
                logger.warning(f"Error reading image {file_path}: {e}")
        
        # OCR для изображений
        if self.use_ocr and self._easyocr:
            try:
                result = self._easyocr.readtext(str(file_path))
                text = " ".join([r[1] for r in result])
                doc_info.text_length = len(text)
                doc_info.keywords = self._find_keywords(text)
            except Exception as e:
                logger.warning(f"OCR error for {file_path}: {e}")
    
    def _analyze_docx(self, file_path: Path, doc_info: DocumentInfo):
        """Анализ DOCX файла."""
        try:
            from docx import Document
            doc = Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
            doc_info.text_length = len(full_text)
            doc_info.keywords = self._find_keywords(full_text)
        except ImportError:
            logger.warning("python-docx not available")
        except Exception as e:
            logger.warning(f"Error analyzing DOCX {file_path}: {e}")
    
    def _analyze_txt(self, file_path: Path, doc_info: DocumentInfo):
        """Анализ TXT файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                doc_info.text_length = len(text)
                doc_info.keywords = self._find_keywords(text)
        except Exception as e:
            logger.warning(f"Error reading TXT {file_path}: {e}")
    
    def _find_keywords(self, text: str) -> List[str]:
        """Поиск ключевых слов в тексте."""
        text_lower = text.lower()
        found = []
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                found.append(keyword)
        return list(set(found))  # Удаление дубликатов
    
    def _generate_report(self, documents: List[DocumentInfo]) -> AnalysisReport:
        """Генерация отчета об анализе."""
        report = AnalysisReport(total_files=len(documents))
        report.documents = documents
        
        # Статистика по типам файлов
        for doc in documents:
            report.file_types[doc.file_type] = report.file_types.get(doc.file_type, 0) + 1
            report.total_text_length += doc.text_length
            report.total_images += doc.image_count
            report.keywords_found.extend(doc.keywords)
        
        report.keywords_found = list(set(report.keywords_found))
        
        # Формирование резюме
        report.summary = (
            f"Проанализировано файлов: {report.total_files}\n"
            f"Типы файлов: {', '.join([f'{k}({v})' for k, v in report.file_types.items()])}\n"
            f"Общий объем текста: {report.total_text_length:,} символов\n"
            f"Изображений: {report.total_images}\n"
            f"Найдены ключевые слова: {', '.join(report.keywords_found[:10])}"
        )
        
        # Рекомендации
        scanned_count = sum(1 for d in documents if d.is_scanned)
        if scanned_count > 0:
            report.recommendations.append(
                f"Обнаружено {scanned_count} сканированных документов. Рекомендуется использовать OCR."
            )
        
        if report.total_text_length == 0:
            report.recommendations.append(
                "Текст не извлечен. Проверьте качество документов или используйте OCR."
            )
        
        if 'С2000' not in report.keywords_found and 'Болид' not in report.keywords_found:
            report.recommendations.append(
                "Не найдены ключевые слова оборудования Болид. Проверьте соответствие документации."
            )
        
        return report
