"""
CV Plan Analyzer - ИИ-инструмент для анализа планов этажей.
Этап 2: Разработка и Тестирование Прототипов ИИ-инструментов

Использует CV (YOLOv8, Detectron2) для детекции объектов на планах:
- ПК, датчики, кнопки и т.п.
- OCR для получения ID устройства и номера помещения
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus
from orchestrator.models.domain import Device, DeviceType, ConfidenceLevel

logger = logging.getLogger(__name__)


class CVPlanAnalyzer(AITool):
    """
    ИИ-инструмент для компьютерного зрения планов этажей.
    
    Функции:
    - Детекция объектов АПС на изображениях планов
    - OCR для чтения подписей устройств
    - Определение номеров помещений
    - Вывод JSON с координатами, ID, типом устройства
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("CVPlanAnalyzer", config)
        self.use_yolo = self.config.get('use_yolo', False)
        self.use_easyocr = self.config.get('use_easyocr', True)
        
        # Lazy imports
        self._cv2 = None
        self._easyocr = None
        self._yolo_model = None
    
    def _initialize(self):
        """Инициализация CV моделей."""
        try:
            import cv2
            self._cv2 = cv2
            logger.info("OpenCV initialized")
        except ImportError:
            logger.warning("OpenCV not available")
        
        if self.use_easyocr:
            try:
                import easyocr
                self._easyocr = easyocr.Reader(['ru', 'en'], gpu=False)
                logger.info("EasyOCR initialized")
            except ImportError:
                logger.warning("EasyOCR not available")
        
        if self.use_yolo:
            try:
                from ultralytics import YOLO
                # Загрузка модели (требуется дообучение на символах АПС)
                # self._yolo_model = YOLO('yolov8n.pt')
                logger.info("YOLO available but requires custom training for APS symbols")
            except ImportError:
                logger.warning("YOLO not available")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить анализ планов этажей.
        
        Args:
            input_data: Путь к изображению плана или dict с данными
            
        Returns:
            ToolResult с распознанными устройствами
        """
        start_time = time.time()
        
        try:
            # Обработка входных данных
            if isinstance(input_data, str):
                image_path = Path(input_data)
            elif isinstance(input_data, dict) and 'image_path' in input_data:
                image_path = Path(input_data['image_path'])
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data. Expected image path."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            if not image_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=[f"Image not found: {image_path}"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Анализ изображения
            devices = self._analyze_plan(image_path)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if devices else ToolStatus.PARTIAL,
                data={
                    'devices': [
                        {
                            'device_type': d.device_type.value,
                            'model': d.model,
                            'location': d.location,
                            'room_number': d.room_number,
                            'coordinates': d.metadata.get('coordinates'),
                            'confidence': d.confidence.value,
                        }
                        for d in devices
                    ],
                    'total_devices': len(devices),
                    'image_path': str(image_path),
                },
                metadata={
                    'image_size': self._get_image_size(image_path),
                },
                execution_time_ms=execution_time,
                confidence=0.75,
            )
            
        except Exception as e:
            logger.exception(f"Error in CVPlanAnalyzer: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _analyze_plan(self, image_path: Path) -> List[Device]:
        """Анализ изображения плана."""
        devices = []
        
        if not self._cv2:
            logger.warning("OpenCV not available, skipping plan analysis")
            return devices
        
        # Чтение изображения
        img = self._cv2.imread(str(image_path))
        if img is None:
            return devices
        
        # Применение OCR для поиска текста на плане
        if self._easyocr:
            ocr_results = self._perform_ocr(img)
            devices.extend(self._parse_ocr_results(ocr_results))
        
        # Детекция символов (заглушка - требует обученной модели)
        if self._yolo_model:
            detected_objects = self._detect_symbols(img)
            devices.extend(detected_objects)
        
        return devices
    
    def _perform_ocr(self, img) -> List:
        """Выполнить OCR на изображении."""
        if not self._easyocr:
            return []
        
        try:
            results = self._easyocr.readtext(img)
            return results
        except Exception as e:
            logger.warning(f"OCR error: {e}")
            return []
    
    def _parse_ocr_results(self, ocr_results: List) -> List[Device]:
        """Распарсить результаты OCR и извлечь устройства."""
        devices = []
        
        for bbox, text, confidence in ocr_results:
            device = self._interpret_text_as_device(text, bbox, confidence)
            if device:
                devices.append(device)
        
        return devices
    
    def _interpret_text_as_device(
        self,
        text: str,
        bbox: List,
        confidence: float,
    ) -> Optional[Device]:
        """Интерпретировать текст как устройство."""
        text_upper = text.upper()
        
        # Поиск паттернов устройств
        device_mapping = {
            'ДИП': DeviceType.SMOKE_DETECTOR,
            'ИПР': DeviceType.MANUAL_CALL_POINT,
            'С2000М': DeviceType.CONTROL_PANEL,
            'С2000-КДЛ': DeviceType.KDL,
            'С2000-СП': DeviceType.RELAY,
            'С2000-БКИ': DeviceType.KEYBOARD,
            'МАЯК': DeviceType.LIGHT_ALARM,
        }
        
        detected_type = None
        model = text
        
        for pattern, dtype in device_mapping.items():
            if pattern in text_upper:
                detected_type = dtype
                break
        
        if detected_type:
            # Извлечение номера помещения из контекста (упрощенно)
            room_number = self._extract_room_number(text)
            
            conf_level = ConfidenceLevel.HIGH if confidence > 0.8 else ConfidenceLevel.MEDIUM
            
            return Device(
                device_type=detected_type,
                model=model,
                location=None,
                room_number=room_number,
                confidence=conf_level,
                source='plan_cv',
                metadata={
                    'coordinates': bbox,
                    'ocr_confidence': confidence,
                },
            )
        
        return None
    
    def _extract_room_number(self, text: str) -> Optional[str]:
        """Извлечь номер помещения из текста."""
        import re
        # Паттерны для номеров помещений
        patterns = [
            r'[№#]?\s*(\d{1,4})',
            r'пом\.?\s*(\d+)',
            r'комн\.?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _detect_symbols(self, img) -> List[Device]:
        """Детектировать символы устройств с помощью YOLO."""
        # Требует обученной модели на символах АПС
        # Это заглушка для будущей реализации
        return []
    
    def _get_image_size(self, image_path: Path) -> Tuple[int, int]:
        """Получить размер изображения."""
        if self._cv2:
            img = self._cv2.imread(str(image_path))
            if img is not None:
                return (img.shape[1], img.shape[0])  # width, height
        return (0, 0)
