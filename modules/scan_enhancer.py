"""
Модуль обработки и улучшения некачественных сканов документов.
Предназначен для предобработки изображений перед извлечением текста.

Функции:
- Шумоподавление (фильтры: медианный, Гаусса, двусторонний)
- Коррекция перекоса (автоматическое определение угла наклона)
- Улучшение контраста (адаптивная бинаризация, CLAHE)
- Повышение резкости для низкого DPI
- Автоматическое кадрирование документа
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
import cv2

logger = logging.getLogger(__name__)


class NoiseReductionMethod(Enum):
    """Методы шумоподавления."""
    MEDIAN = "median"
    GAUSSIAN = "gaussian"
    BILATERAL = "bilateral"
    NON_LOCAL_MEANS = "non_local_means"


class BinarizationMethod(Enum):
    """Методы бинаризации."""
    OTSU = "otsu"
    ADAPTIVE_MEAN = "adaptive_mean"
    ADAPTIVE_GAUSSIAN = "adaptive_gaussian"
    SAUVOLA = "sauvola"


@dataclass
class ScanEnhancementConfig:
    """Конфигурация параметров улучшения скана."""
    
    # Шумоподавление
    denoise_method: NoiseReductionMethod = NoiseReductionMethod.BILATERAL
    denoise_strength: int = 10  # Сила шумоподавления (1-30)
    
    # Коррекция перекоса
    deskew_enabled: bool = True
    deskew_max_angle: float = 15.0  # Максимальный угол коррекции в градусах
    
    # Улучшение контраста
    binarization_method: BinarizationMethod = BinarizationMethod.ADAPTIVE_GAUSSIAN
    contrast_enhancement: bool = True
    clahe_clip_limit: float = 2.0  # Ограничение клиппинга для CLAHE
    clahe_grid_size: Tuple[int, int] = (8, 8)  # Размер сетки для CLAHE
    
    # Повышение резкости
    sharpen_enabled: bool = True
    sharpen_strength: float = 1.5  # Сила повышения резкости (0.5-3.0)
    
    # Автоматическое кадрирование
    auto_crop: bool = True
    min_document_area: float = 0.5  # Минимальная доля площади документа (0.0-1.0)
    
    # Масштабирование
    target_dpi: Optional[int] = None  # Целевое DPI (None = без масштабирования)
    default_dpi: int = 150  # DPI по умолчанию для масштабирования
    
    def validate(self) -> list[str]:
        """Проверка корректности конфигурации."""
        errors = []
        
        if not 1 <= self.denoise_strength <= 30:
            errors.append(f"denoise_strength должен быть в диапазоне 1-30, получено {self.denoise_strength}")
        
        if not 0 < self.deskew_max_angle <= 45:
            errors.append(f"deskew_max_angle должен быть в диапазоне 0-45, получено {self.deskew_max_angle}")
        
        if not 0.5 <= self.clahe_clip_limit <= 4.0:
            errors.append(f"clahe_clip_limit должен быть в диапазоне 0.5-4.0, получено {self.clahe_clip_limit}")
        
        if not 0.5 <= self.sharpen_strength <= 3.0:
            errors.append(f"sharpen_strength должен быть в диапазоне 0.5-3.0, получено {self.sharpen_strength}")
        
        if not 0.1 <= self.min_document_area <= 1.0:
            errors.append(f"min_document_area должен быть в диапазоне 0.1-1.0, получено {self.min_document_area}")
        
        return errors


@dataclass
class EnhancementResult:
    """Результат улучшения скана."""
    image: np.ndarray  # Улучшенное изображение
    original_shape: Tuple[int, int]  # Исходные размеры (height, width)
    final_shape: Tuple[int, int]  # Финальные размеры (height, width)
    skew_angle: float  # Обнаруженный угол перекоса (градусы)
    applied_operations: list[str]  # Список примененных операций
    warnings: list[str]  # Предупреждения
    quality_score: float  # Оценка качества (0.0-1.0)
    
    @property
    def success(self) -> bool:
        """Успешно ли выполнено улучшение."""
        return len(self.applied_operations) > 0 and self.image is not None


class ScanEnhancer:
    """
    Класс для обработки и улучшения некачественных сканов документов.
    
    Пример использования:
        enhancer = ScanEnhancer()
        result = enhancer.enhance("scan.jpg")
        cv2.imwrite("enhanced.png", result.image)
    """
    
    def __init__(self, config: Optional[ScanEnhancementConfig] = None):
        """
        Инициализация улучшателя сканов.
        
        Args:
            config: Конфигурация параметров улучшения
        """
        self.config = config or ScanEnhancementConfig()
        self.warnings: list[str] = []
        
        # Проверка конфигурации
        errors = self.config.validate()
        for error in errors:
            logger.warning(f"Ошибка конфигурации: {error}")
            self.warnings.append(error)
    
    def enhance(
        self, 
        image_source: Union[str, Path, np.ndarray],
        config: Optional[ScanEnhancementConfig] = None
    ) -> EnhancementResult:
        """
        Полное улучшение скана документа.
        
        Args:
            image_source: Путь к файлу изображения или numpy массив
            config: Опциональная конфигурация (переопределяет конфигурацию по умолчанию)
            
        Returns:
            EnhancementResult с улучшенным изображением и метаданными
        """
        self.warnings = []
        applied_ops = []
        
        # Использование альтернативной конфигурации если предоставлена
        if config:
            self.config = config
        
        # Загрузка изображения
        image = self._load_image(image_source)
        if image is None:
            return EnhancementResult(
                image=np.array([]),
                original_shape=(0, 0),
                final_shape=(0, 0),
                skew_angle=0.0,
                applied_operations=[],
                warnings=["Не удалось загрузить изображение"],
                quality_score=0.0
            )
        
        original_shape = image.shape[:2]
        skew_angle = 0.0
        
        # 1. Предварительная обработка: шумоподавление
        if self.config.denoise_method != NoiseReductionMethod.MEDIAN or self.config.denoise_strength > 1:
            image = self._reduce_noise(image)
            applied_ops.append(f"Шумоподавление ({self.config.denoise_method.value})")
        
        # 2. Автоматическое кадрирование документа
        if self.config.auto_crop:
            cropped = self._auto_crop_document(image)
            if cropped is not None and cropped.size > 0:
                if cropped.shape[0] * cropped.shape[1] < image.shape[0] * image.shape[1] * 0.9:
                    image = cropped
                    applied_ops.append("Автоматическое кадрирование")
        
        # 3. Коррекция перекоса
        if self.config.deskew_enabled:
            image, skew_angle = self._deskew(image)
            if abs(skew_angle) > 0.1:
                applied_ops.append(f"Коррекция перекоса ({skew_angle:+.2f}°)")
        
        # 4. Улучшение контраста и бинаризация
        if self.config.contrast_enhancement:
            image = self._enhance_contrast(image)
            applied_ops.append("Улучшение контраста (CLAHE)")
        
        # 5. Бинаризация
        image = self._binarize(image)
        applied_ops.append(f"Бинаризация ({self.config.binarization_method.value})")
        
        # 6. Повышение резкости
        if self.config.sharpen_enabled:
            image = self._sharpen(image)
            applied_ops.append(f"Повышение резкости (сила={self.config.sharpen_strength})")
        
        # 7. Масштабирование до целевого DPI
        if self.config.target_dpi and self.config.target_dpi != self.config.default_dpi:
            scale_factor = self.config.target_dpi / self.config.default_dpi
            if scale_factor != 1.0:
                image = self._resize_image(image, scale_factor)
                applied_ops.append(f"Масштабирование (DPI: {self.config.default_dpi} → {self.config.target_dpi})")
        
        final_shape = image.shape[:2]
        
        # Оценка качества результата
        quality_score = self._estimate_quality(image)
        
        return EnhancementResult(
            image=image,
            original_shape=original_shape,
            final_shape=final_shape,
            skew_angle=skew_angle,
            applied_operations=applied_ops,
            warnings=self.warnings.copy(),
            quality_score=quality_score
        )
    
    def _load_image(self, source: Union[str, Path, np.ndarray]) -> Optional[np.ndarray]:
        """Загрузка изображения из файла или numpy массива."""
        if isinstance(source, np.ndarray):
            return source.copy()
        
        path = Path(source)
        if not path.exists():
            logger.error(f"Файл не найден: {path}")
            self.warnings.append(f"Файл не найден: {path}")
            return None
        
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            logger.error(f"Не удалось прочитать изображение: {path}")
            self.warnings.append(f"Не удалось прочитать изображение: {path}")
            return None
        
        return image
    
    def _reduce_noise(self, image: np.ndarray) -> np.ndarray:
        """Применение фильтра шумоподавления."""
        method = self.config.denoise_method
        strength = self.config.denoise_strength
        
        try:
            if method == NoiseReductionMethod.MEDIAN:
                # Медианный фильтр - хорош для удаления импульсного шума
                kernel_size = max(3, strength // 3 * 2 + 1)  # Нечетное число
                return cv2.medianBlur(image, kernel_size)
            
            elif method == NoiseReductionMethod.GAUSSIAN:
                # Фильтр Гаусса - для общего сглаживания
                kernel_size = max(3, strength // 5 * 2 + 1)
                sigma = strength / 10.0
                return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
            
            elif method == NoiseReductionMethod.BILATERAL:
                # Двусторонний фильтр - сохраняет края при шумоподавлении
                d = max(5, strength)
                sigma_color = strength * 2
                sigma_space = strength * 2
                return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
            
            elif method == NoiseReductionMethod.NON_LOCAL_MEANS:
                # NL-Means - лучший результат, но медленнее
                h = strength * 2
                return cv2.fastNlMeansDenoising(image, None, h, 7, 21)
            
            else:
                return image
                
        except Exception as e:
            logger.warning(f"Ошибка при шумоподавлении: {e}")
            self.warnings.append(f"Шумоподавление не выполнено: {e}")
            return image
    
    def _detect_skew_angle(self, image: np.ndarray) -> float:
        """
        Определение угла перекоса документа.
        Использует преобразование Хафа для обнаружения линий.
        """
        # Бинаризация для детекции краев
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Детекция краев
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)
        
        # Преобразование Хафа для обнаружения линий
        lines = cv2.HoughLinesP(
            edges, 
            rho=1, 
            theta=np.pi / 180, 
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            # Альтернативный метод: проекционный профиль
            return self._detect_skew_by_projection(binary)
        
        # Вычисление углов всех обнаруженных линий
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 != x1:  # Избегаем деления на ноль
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Учитываем только линии близкие к горизонтальным/вертикальным
                if abs(angle) < self.config.deskew_max_angle or \
                   abs(abs(angle) - 90) < self.config.deskew_max_angle:
                    angles.append(angle)
        
        if not angles:
            return 0.0
        
        # Возвращаем медианный угол (более устойчив к выбросам)
        median_angle = np.median(angles)
        
        # Нормализация угла к диапазону [-max_angle, max_angle]
        if abs(median_angle) > self.config.deskew_max_angle:
            if median_angle > 0:
                median_angle = median_angle - 90
            else:
                median_angle = median_angle + 90
        
        return np.clip(median_angle, -self.config.deskew_max_angle, self.config.deskew_max_angle)
    
    def _detect_skew_by_projection(self, binary: np.ndarray) -> float:
        """
        Альтернативный метод определения перекоса через проекционный профиль.
        """
        best_angle = 0.0
        best_variance = 0.0
        
        # Пробуем углы в диапазоне
        for angle in np.linspace(-self.config.deskew_max_angle, self.config.deskew_max_angle, 36):
            # Поворот изображения
            M = cv2.getRotationMatrix2D(
                (binary.shape[1] // 2, binary.shape[0] // 2), 
                angle, 
                1.0
            )
            rotated = cv2.warpAffine(
                binary, 
                M, 
                (binary.shape[1], binary.shape[0]),
                flags=cv2.INTER_NEAREST,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            # Горизонтальный проекционный профиль
            projection = np.sum(rotated, axis=1)
            
            # Дисперсия профиля (чем выше, тем лучше выровнены строки)
            variance = np.var(projection)
            
            if variance > best_variance:
                best_variance = variance
                best_angle = angle
        
        return best_angle
    
    def _deskew(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Коррекция перекоса изображения.
        
        Returns:
            Tuple с выпрямленным изображением и углом коррекции
        """
        skew_angle = self._detect_skew_angle(image)
        
        if abs(skew_angle) < 0.1:
            return image, skew_angle
        
        try:
            # Создание матрицы поворота
            center = (image.shape[1] // 2, image.shape[0] // 2)
            M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
            
            # Вычисление новых размеров для сохранения всего изображения
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])
            new_width = int(image.shape[0] * sin + image.shape[1] * cos)
            new_height = int(image.shape[0] * cos + image.shape[1] * sin)
            
            # Корректировка матрицы с учетом смещения
            M[0, 2] += (new_width / 2) - center[0]
            M[1, 2] += (new_height / 2) - center[1]
            
            # Поворот изображения
            deskewed = cv2.warpAffine(
                image, 
                M, 
                (new_width, new_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
                borderValue=255  # Белый фон
            )
            
            logger.info(f"Коррекция перекоса: {skew_angle:+.2f}°")
            return deskewed, skew_angle
            
        except Exception as e:
            logger.warning(f"Ошибка при коррекции перекоса: {e}")
            self.warnings.append(f"Коррекция перекоса не выполнена: {e}")
            return image, 0.0
    
    def _auto_crop_document(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Автоматическое кадрирование документа.
        Обнаруживает границы документа и обрезает лишние поля.
        """
        try:
            # Бинаризация
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Поиск контуров
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Находим наибольший контур (предполагаем, что это документ)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Проверка минимальной площади
            image_area = image.shape[0] * image.shape[1]
            contour_area = cv2.contourArea(largest_contour)
            
            if contour_area < image_area * self.config.min_document_area:
                logger.debug("Документ занимает слишком малую площадь, кадрирование отменено")
                return None
            
            # Получаем ограничивающий прямоугольник
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Добавляем небольшой отступ
            margin = 5
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(image.shape[1] - x, w + 2 * margin)
            h = min(image.shape[0] - y, h + 2 * margin)
            
            return image[y:y+h, x:x+w]
            
        except Exception as e:
            logger.warning(f"Ошибка при автоматическом кадрировании: {e}")
            self.warnings.append(f"Кадрирование не выполнено: {e}")
            return None
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Улучшение контраста с помощью CLAHE."""
        try:
            clahe = cv2.createCLAHE(
                clipLimit=self.config.clahe_clip_limit,
                tileGridSize=self.config.clahe_grid_size
            )
            return clahe.apply(image)
        except Exception as e:
            logger.warning(f"Ошибка при улучшении контраста: {e}")
            self.warnings.append(f"Улучшение контраста не выполнено: {e}")
            return image
    
    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Бинаризация изображения."""
        method = self.config.binarization_method
        
        try:
            if method == BinarizationMethod.OTSU:
                _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                return binary
            
            elif method == BinarizationMethod.ADAPTIVE_MEAN:
                return cv2.adaptiveThreshold(
                    image, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
            
            elif method == BinarizationMethod.ADAPTIVE_GAUSSIAN:
                return cv2.adaptiveThreshold(
                    image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
            
            elif method == BinarizationMethod.SAUVOLA:
                # Реализация метода Sauvola (упрощенная)
                mean = cv2.blur(image.astype(np.float32), (15, 15))
                std = cv2.blur(np.square(image.astype(np.float32)), (15, 15))
                variance = std - np.square(mean)
                k = 0.2
                R = 128  # Динамический диапазон для 8-битного изображения
                threshold = mean * (1 + k * (np.sqrt(variance) / R - 1))
                binary = np.where(image > threshold, 255, 0).astype(np.uint8)
                return binary
            
            else:
                _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                return binary
                
        except Exception as e:
            logger.warning(f"Ошибка при бинаризации: {e}")
            self.warnings.append(f"Бинаризация не выполнена: {e}")
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
    
    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Повышение резкости изображения."""
        try:
            # Ядро повышения резкости
            strength = self.config.sharpen_strength
            kernel = np.array([
                [0, -1, 0],
                [-1, strength + 4, -1],
                [0, -1, 0]
            ]) / strength
            
            sharpened = cv2.filter2D(image, -1, kernel)
            
            # Ограничиваем значения диапазоном [0, 255]
            return np.clip(sharpened, 0, 255).astype(np.uint8)
            
        except Exception as e:
            logger.warning(f"Ошибка при повышении резкости: {e}")
            self.warnings.append(f"Повышение резкости не выполнено: {e}")
            return image
    
    def _resize_image(self, image: np.ndarray, scale_factor: float) -> np.ndarray:
        """Масштабирование изображения."""
        try:
            new_width = int(image.shape[1] * scale_factor)
            new_height = int(image.shape[0] * scale_factor)
            
            # Используем интерполяцию Lanczos для лучшего качества
            return cv2.resize(
                image, 
                (new_width, new_height), 
                interpolation=cv2.INTER_LANCZOS4
            )
        except Exception as e:
            logger.warning(f"Ошибка при масштабировании: {e}")
            self.warnings.append(f"Масштабирование не выполнено: {e}")
            return image
    
    def _estimate_quality(self, image: np.ndarray) -> float:
        """
        Оценка качества обработанного изображения.
        Возвращает значение от 0.0 до 1.0.
        """
        try:
            # Метрика 1: Контраст (разница между светлыми и темными областями)
            hist = cv2.calcHist([image], [0], None, [256], [0, 256])
            hist_normalized = hist.flatten() / np.sum(hist)
            
            # Находим процентили 5% и 95%
            cumsum = np.cumsum(hist_normalized)
            low_idx = np.searchsorted(cumsum, 0.05)
            high_idx = np.searchsorted(cumsum, 0.95)
            contrast = (high_idx - low_idx) / 255.0
            
            # Метрика 2: Четкость краев
            edges = cv2.Canny(image, 50, 150)
            edge_density = np.sum(edges > 0) / image.size
            
            # Метрика 3: Уровень шума (оценка через дисперсию в однородных областях)
            blur = cv2.GaussianBlur(image, (5, 5), 0)
            noise_level = np.mean(np.abs(image.astype(float) - blur.astype(float)))
            noise_score = max(0, 1 - noise_level / 50)  # Нормализация
            
            # Комбинированная оценка
            quality = 0.4 * contrast + 0.3 * min(edge_density * 10, 1.0) + 0.3 * noise_score
            
            return min(max(quality, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"Ошибка при оценке качества: {e}")
            return 0.5  # Среднее значение по умолчанию


def enhance_scan(
    image_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    config: Optional[ScanEnhancementConfig] = None
) -> EnhancementResult:
    """
    Удобная функция для улучшения скана документа.
    
    Args:
        image_path: Путь к исходному изображению
        output_path: Путь для сохранения результата (опционально)
        config: Конфигурация параметров улучшения
        
    Returns:
        EnhancementResult с результатами обработки
    """
    enhancer = ScanEnhancer(config)
    result = enhancer.enhance(image_path)
    
    if output_path and result.success:
        cv2.imwrite(str(output_path), result.image)
        logger.info(f"Улучшенное изображение сохранено: {output_path}")
    
    return result


def preprocess_for_ocr(
    image_source: Union[str, Path, np.ndarray],
    target_dpi: int = 300
) -> EnhancementResult:
    """
    Предобработка изображения специально для OCR (распознавания текста).
    Использует оптимальные настройки для повышения точности распознавания.
    
    Args:
        image_source: Путь к изображению или numpy массив
        target_dpi: Целевое DPI для OCR (рекомендуется 300)
        
    Returns:
        EnhancementResult с подготовленным изображением
    """
    config = ScanEnhancementConfig(
        denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
        denoise_strength=15,
        deskew_enabled=True,
        deskew_max_angle=15.0,
        binarization_method=BinarizationMethod.ADAPTIVE_GAUSSIAN,
        contrast_enhancement=True,
        clahe_clip_limit=2.5,
        sharpen_enabled=True,
        sharpen_strength=1.8,
        auto_crop=True,
        target_dpi=target_dpi
    )
    
    return enhance_scan(image_source, config=config)
