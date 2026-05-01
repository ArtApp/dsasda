"""
Модуль распознавания адресов с графических схем (планов этажей) из PDF.
Использует OpenCV для обработки изображений и Tesseract OCR для извлечения текста.
"""

import re
import io
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass, field

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    NdArrayType = NdArrayType
except ImportError:
    OPENCV_AVAILABLE = False
    np = None  # Заглушка для аннотаций типов
    NdArrayType = object  # Заглушка для аннотаций типов
    print("⚠ OpenCV не установлен. Установите: pip install opencv-python")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠ pytesseract не установлен. Установите: pip install pytesseract")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class DetectedAddress:
    """Обнаруженный адрес на схеме."""
    text: str  # Распознанный текст
    address_value: Optional[int] = None  # Числовое значение адреса
    device_type: Optional[str] = None  # Тип устройства (если определен)
    location: Optional[str] = None  # Местоположение на схеме
    confidence: float = 0.0  # Уверенность распознавания (0.0-1.0)
    bbox: tuple = field(default_factory=lambda: (0, 0, 0, 0))  # Bounding box (x, y, w, h)
    page_number: int = 0  # Номер страницы в PDF
    metadata: dict = field(default_factory=dict)  # Дополнительные данные


@dataclass
class SchemaAnalysisResult:
    """Результат анализа графической схемы."""
    addresses: list[DetectedAddress] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_pages_processed: int = 0
    images_extracted: int = 0
    
    def add_address(self, address: DetectedAddress):
        """Добавить адрес в результат."""
        self.addresses.append(address)


class SchemaAddressRecognizer:
    """
    Распознаватель адресов устройств с графических схем и планов этажей.
    
    Использует комбинацию OpenCV для предобработки изображений и Tesseract OCR
    для извлечения текстовой информации о адресах устройств.
    """
    
    # Паттерны для поиска адресов устройств
    ADDRESS_PATTERNS = [
        # Адреса в формате ARK1, ARK2, etc.
        (r'ARK\s*(\d+)', 'ARK', 1),
        # Адреса в формате SC39-40, SC41-42
        (r'SC\s*(\d+)[-\s](\d+)', 'SC', 2),
        # Адреса в формате BTH1, BTH2
        (r'BTH\s*(\d+)', 'BTH', 1),
        # Просто номер адреса
        (r'[Аа]дрес\s*[:\(]?\s*(\d+)', 'ADDR', 1),
        # Номер в кружке/квадрате (часто используется на схемах)
        (r'№\s*(\d+)', 'NUM', 1),
        # Формат С2000-КДЛ-2И адрес 1
        (r'КДЛ[-\s]*2И.*?[Аа]дрес\s*[:\(]?\s*(\d+)', 'KDL', 1),
        # ДИП-34 с адресом
        (r'ДИП[-\s]*34[А-Я]?.*?(\d{1,3})', 'DIP', 1),
        # ИПР с адресом
        (r'ИПР\s*513.*?(\d{1,3})', 'IPR', 1),
    ]
    
    # Паттерны типов устройств
    DEVICE_TYPE_PATTERNS = {
        'С2000М': r'С2000[−-]?М',
        'С2000-КДЛ-2И': r'С2000[−-]?КДЛ[−-]?2И',
        'С2000-СП2': r'С2000[−-]?СП2',
        'С2000-БКИ': r'С2000[−-]?БКИ',
        'ДИП-34': r'ДИП[−-]?34[А-Я]?',
        'ИПР 513': r'ИПР\s*513',
        'С2000-ИПДЛ': r'С2000[−-]?ИПДЛ',
        'RS-200T': r'RS?[−-]?200Т?',
    }
    
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = 'rus+eng'):
        """
        Инициализация распознавателя.
        
        Args:
            tesseract_cmd: Путь к исполняемому файлу Tesseract (если не в PATH)
            lang: Языки для Tesseract (по умолчанию русский + английский)
        """
        self.tesseract_cmd = tesseract_cmd
        self.lang = lang
        self.warnings: list[str] = []
        self.errors: list[str] = []
        
        # Настройка Tesseract
        if tesseract_cmd and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Проверка доступности Tesseract
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                self.warnings.append(f"Tesseract может быть недоступен: {str(e)}")
    
    def process_pdf(self, pdf_path: str | Path, 
                    min_image_size: int = 10000,
                    dpi: int = 150) -> SchemaAnalysisResult:
        """
        Обработка PDF файла для извлечения адресов с графических схем.
        
        Args:
            pdf_path: Путь к PDF файлу
            min_image_size: Минимальный размер изображения в пикселях (ширина*высота)
            dpi: Разрешение при рендеринге страниц PDF
            
        Returns:
            SchemaAnalysisResult с найденными адресами
        """
        result = SchemaAnalysisResult()
        
        # Проверка зависимостей
        if not PYMUPDF_AVAILABLE:
            result.errors.append("PyMuPDF не установлен. Установите: pip install PyMuPDF")
            return result
        
        if not OPENCV_AVAILABLE:
            result.errors.append("OpenCV не установлен. Установите: pip install opencv-python")
            return result
        
        if not TESSERACT_AVAILABLE:
            result.errors.append("pytesseract не установлен. Установите: pip install pytesseract")
            return result
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            result.errors.append(f"Файл не найден: {pdf_path}")
            return result
        
        try:
            doc = fitz.open(pdf_path)
            result.total_pages_processed = len(doc)
            
            for page_num, page in enumerate(doc, 1):
                # Рендеринг страницы в изображение
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                
                # Конвертация в numpy array для OpenCV
                img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img_data.reshape((pix.height, pix.width, pix.n))
                
                # Конвертация RGB -> BGR для OpenCV
                if pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                result.images_extracted += 1
                
                # Обработка изображения
                addresses = self._process_image(img, page_num)
                for addr in addresses:
                    result.add_address(addr)
            
            doc.close()
            
        except Exception as e:
            result.errors.append(f"Ошибка при обработке PDF: {str(e)}")
        
        return result
    
    def process_image(self, image_path: Union[str, Path], 
                      page_number: int = 1) -> SchemaAnalysisResult:
        """
        Обработка изображения (или пути к изображению) для распознавания адресов.
        
        Args:
            image_path: Путь к изображению или numpy array
            page_number: Номер страницы (для контекста)
            
        Returns:
            SchemaAnalysisResult с найденными адресами
        """
        result = SchemaAnalysisResult()
        
        # Проверка зависимостей
        if not OPENCV_AVAILABLE:
            result.errors.append("OpenCV не установлен")
            return result
        
        if not TESSERACT_AVAILABLE:
            result.errors.append("pytesseract не установлен")
            return result
        
        # Загрузка изображения
        if isinstance(image_path, (str, Path)):
            image_path = Path(image_path)
            if not image_path.exists():
                result.errors.append(f"Изображение не найдено: {image_path}")
                return result
            img = cv2.imread(str(image_path))
            if img is None:
                result.errors.append(f"Не удалось загрузить изображение: {image_path}")
                return result
        else:
            img = image_path.copy()
        
        result.images_extracted = 1
        result.total_pages_processed = 1
        
        # Обработка изображения
        addresses = self._process_image(img, page_number)
        for addr in addresses:
            result.add_address(addr)
        
        return result
    
    def _process_image(self, img: NdArrayType, page_number: int) -> list[DetectedAddress]:
        """
        Обработка изображения для извлечения адресов.
        
        Args:
            img: Изображение в формате OpenCV (BGR)
            page_number: Номер страницы
            
        Returns:
            Список DetectedAddress
        """
        addresses = []
        
        # Предобработка изображения для улучшения распознавания
        preprocessed = self._preprocess_image(img)
        
        # Распознавание текста с помощью Tesseract
        ocr_result = self._perform_ocr(preprocessed)
        
        # Анализ результатов OCR
        if ocr_result:
            detected = self._analyze_ocr_result(ocr_result, img.shape, page_number)
            addresses.extend(detected)
        
        # Дополнительный поиск по зонам интереса (ROI)
        roi_addresses = self._find_addresses_in_rois(img, page_number)
        addresses.extend(roi_addresses)
        
        # Удаление дубликатов
        addresses = self._remove_duplicates(addresses)
        
        return addresses
    
    def _preprocess_image(self, img: NdArrayType) -> NdArrayType:
        """
        Предобработка изображения для улучшения качества OCR.
        
        Args:
            img: Исходное изображение
            
        Returns:
            Предобработанное изображение
        """
        # Конвертация в оттенки серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Применение bilateral filter для уменьшения шума
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Адаптивная бинаризация
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Морфологические операции для улучшения текста
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        eroded = cv2.erode(dilated, kernel, iterations=1)
        
        return eroded
    
    def _perform_ocr(self, img: NdArrayType) -> Optional[dict]:
        """
        Выполнение OCR на изображении.
        
        Args:
            img: Предобработанное изображение
            
        Returns:
            Словарь с результатами OCR (или None при ошибке)
        """
        if not TESSERACT_AVAILABLE:
            return None
        
        try:
            # Конфигурация Tesseract для детального вывода
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzА-Яа-яёЁ №.-():"'
            
            # Получение данных с bounding boxes
            data = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)
            
            return data
        except Exception as e:
            self.warnings.append(f"OCR ошибка: {str(e)}")
            return None
    
    def _analyze_ocr_result(self, ocr_data: dict, 
                           image_shape: tuple, 
                           page_number: int) -> list[DetectedAddress]:
        """
        Анализ результатов OCR для поиска адресов.
        
        Args:
            ocr_data: Данные от Tesseract
            image_shape: Размеры изображения (height, width, channels)
            page_number: Номер страницы
            
        Returns:
            Список DetectedAddress
        """
        addresses = []
        n_boxes = len(ocr_data['text'])
        
        # Сборка текста из распознанных блоков
        text_blocks = []
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            if text and int(ocr_data['conf'][i]) > 30:  # Фильтр по уверенности
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                conf = int(ocr_data['conf'][i]) / 100.0
                
                text_blocks.append({
                    'text': text,
                    'bbox': (x, y, w, h),
                    'confidence': conf
                })
        
        # Поиск паттернов адресов в тексте
        full_text = ' '.join([b['text'] for b in text_blocks])
        
        for pattern, addr_type, group_idx in self.ADDRESS_PATTERNS:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                address_value = int(match.group(group_idx))
                
                # Поиск ближайшего блока с этим текстом
                matched_block = None
                for block in text_blocks:
                    if match.group(0) in block['text'] or \
                       any(part in block['text'] for part in match.group(0).split()):
                        matched_block = block
                        break
                
                # Определение типа устройства из контекста
                device_type = self._detect_device_type(full_text, match.start())
                
                # Вычисление местоположения на основе позиции
                location = self._estimate_location(
                    matched_block['bbox'] if matched_block else (0, 0, 0, 0),
                    image_shape
                )
                
                address = DetectedAddress(
                    text=match.group(0),
                    address_value=address_value,
                    device_type=device_type,
                    location=location,
                    confidence=matched_block['confidence'] if matched_block else 0.5,
                    bbox=matched_block['bbox'] if matched_block else (0, 0, 0, 0),
                    page_number=page_number,
                    metadata={
                        'address_type': addr_type,
                        'pattern': pattern
                    }
                )
                addresses.append(address)
        
        return addresses
    
    def _find_addresses_in_rois(self, img: NdArrayType, 
                                page_number: int) -> list[DetectedAddress]:
        """
        Поиск адресов в зонах интереса (например, где есть таблички с устройствами).
        
        Args:
            img: Исходное изображение
            page_number: Номер страницы
            
        Returns:
            Список DetectedAddress
        """
        addresses = []
        
        # Конвертация в оттенки серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Поиск прямоугольных областей (возможные таблички с адресами)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True)
            
            # Поиск четырехугольников подходящего размера
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # Фильтрация по размеру (не слишком маленькие и не слишком большие)
                if 5000 < area < img.shape[0] * img.shape[1] / 10:
                    # Извлечение ROI
                    roi = gray[y:y+h, x:x+w]
                    
                    # OCR для ROI
                    if TESSERACT_AVAILABLE and roi.size > 0:
                        try:
                            roi_text = pytesseract.image_to_string(
                                roi, 
                                config='--oem 3 --psm 7',
                                lang=self.lang
                            ).strip()
                            
                            # Поиск адресов в ROI
                            for pattern, addr_type, group_idx in self.ADDRESS_PATTERNS:
                                for match in re.finditer(pattern, roi_text, re.IGNORECASE):
                                    address_value = int(match.group(group_idx))
                                    device_type = self._detect_device_type(roi_text, 0)
                                    
                                    address = DetectedAddress(
                                        text=match.group(0),
                                        address_value=address_value,
                                        device_type=device_type,
                                        location=f"ROI ({x}, {y})",
                                        confidence=0.7,
                                        bbox=(x, y, w, h),
                                        page_number=page_number,
                                        metadata={
                                            'address_type': addr_type,
                                            'source': 'ROI'
                                        }
                                    )
                                    addresses.append(address)
                        except Exception:
                            pass
        
        return addresses
    
    def _detect_device_type(self, text: str, position: int) -> Optional[str]:
        """
        Определение типа устройства из контекста.
        
        Args:
            text: Текст контекста
            position: Позиция адреса в тексте
            
        Returns:
            Тип устройства или None
        """
        # Поиск ближайшего упоминания типа устройства
        context_start = max(0, position - 50)
        context_end = min(len(text), position + 50)
        context = text[context_start:context_end]
        
        for device_type, pattern in self.DEVICE_TYPE_PATTERNS.items():
            if re.search(pattern, context, re.IGNORECASE):
                return device_type
        
        return None
    
    def _estimate_location(self, bbox: tuple, image_shape: tuple) -> str:
        """
        Оценка местоположения на схеме на основе координат.
        
        Args:
            bbox: Bounding box (x, y, w, h)
            image_shape: Размеры изображения (height, width, channels)
            
        Returns:
            Строковое описание местоположения
        """
        height, width = image_shape[:2]
        x, y = bbox[0], bbox[1]
        
        # Определение квадранта
        if x < width / 2:
            horizontal = "левая"
        else:
            horizontal = "правая"
        
        if y < height / 2:
            vertical = "верхняя"
        else:
            vertical = "нижняя"
        
        return f"{vertical} {horizontal} часть"
    
    def _remove_duplicates(self, addresses: list[DetectedAddress]) -> list[DetectedAddress]:
        """
        Удаление дублирующихся адресов.
        
        Args:
            addresses: Список адресов
            
        Returns:
            Список без дубликатов
        """
        unique = []
        seen = set()
        
        for addr in addresses:
            # Ключ для уникальности: текст + адрес + страница
            key = (addr.text, addr.address_value, addr.page_number)
            
            if key not in seen:
                seen.add(key)
                unique.append(addr)
            else:
                # Если уже есть, оставляем адрес с большей уверенностью
                for i, existing in enumerate(unique):
                    if (existing.text, existing.address_value, existing.page_number) == key:
                        if addr.confidence > existing.confidence:
                            unique[i] = addr
                        break
        
        return unique
    
    def export_results(self, result: SchemaAnalysisResult, 
                       output_path: str | Path,
                       format: str = 'text') -> bool:
        """
        Экспорт результатов распознавания.
        
        Args:
            result: Результат анализа
            output_path: Путь для сохранения
            format: Формат экспорта ('text', 'json', 'csv')
            
        Returns:
            True если успешно
        """
        output_path = Path(output_path)
        
        try:
            if format == 'text':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("Результаты распознавания адресов с графических схем\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"Всего страниц обработано: {result.total_pages_processed}\n")
                    f.write(f"Всего изображений обработано: {result.images_extracted}\n")
                    f.write(f"Найдено адресов: {len(result.addresses)}\n\n")
                    
                    if result.addresses:
                        f.write("Найденные адреса:\n")
                        f.write("-" * 60 + "\n")
                        for i, addr in enumerate(result.addresses, 1):
                            f.write(f"{i}. Текст: {addr.text}\n")
                            f.write(f"   Значение: {addr.address_value}\n")
                            f.write(f"   Тип устройства: {addr.device_type or 'не определен'}\n")
                            f.write(f"   Местоположение: {addr.location or 'не определено'}\n")
                            f.write(f"   Страница: {addr.page_number}\n")
                            f.write(f"   Уверенность: {addr.confidence:.2f}\n")
                            f.write(f"   BBox: {addr.bbox}\n\n")
                    
                    if result.warnings:
                        f.write("\nПредупреждения:\n")
                        for warning in result.warnings:
                            f.write(f"- {warning}\n")
                    
                    if result.errors:
                        f.write("\nОшибки:\n")
                        for error in result.errors:
                            f.write(f"- {error}\n")
            
            elif format == 'json':
                import json
                data = {
                    'total_pages': result.total_pages_processed,
                    'images_processed': result.images_extracted,
                    'addresses_count': len(result.addresses),
                    'addresses': [
                        {
                            'text': addr.text,
                            'address_value': addr.address_value,
                            'device_type': addr.device_type,
                            'location': addr.location,
                            'confidence': addr.confidence,
                            'bbox': addr.bbox,
                            'page_number': addr.page_number,
                            'metadata': addr.metadata
                        }
                        for addr in result.addresses
                    ],
                    'warnings': result.warnings,
                    'errors': result.errors
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format == 'csv':
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Текст', 'Значение', 'Тип устройства', 'Местоположение',
                        'Уверенность', 'BBox', 'Страница'
                    ])
                    for addr in result.addresses:
                        writer.writerow([
                            addr.text,
                            addr.address_value,
                            addr.device_type or '',
                            addr.location or '',
                            f"{addr.confidence:.2f}",
                            str(addr.bbox),
                            addr.page_number
                        ])
            
            return True
            
        except Exception as e:
            self.errors.append(f"Ошибка экспорта: {str(e)}")
            return False


def recognize_addresses_from_pdf(pdf_path: str | Path,
                                 tesseract_cmd: Optional[str] = None,
                                 dpi: int = 150) -> SchemaAnalysisResult:
    """
    Удобная функция для распознавания адресов из PDF.
    
    Args:
        pdf_path: Путь к PDF файлу
        tesseract_cmd: Путь к Tesseract (если не в PATH)
        dpi: Разрешение при рендеринге
        
    Returns:
        SchemaAnalysisResult с результатами
    """
    recognizer = SchemaAddressRecognizer(tesseract_cmd=tesseract_cmd)
    return recognizer.process_pdf(pdf_path, dpi=dpi)


def recognize_addresses_from_image(image_path: str | Path,
                                   tesseract_cmd: Optional[str] = None) -> SchemaAnalysisResult:
    """
    Удобная функция для распознавания адресов из изображения.
    
    Args:
        image_path: Путь к изображению
        tesseract_cmd: Путь к Tesseract (если не в PATH)
        
    Returns:
        SchemaAnalysisResult с результатами
    """
    recognizer = SchemaAddressRecognizer(tesseract_cmd=tesseract_cmd)
    return recognizer.process_image(image_path)
