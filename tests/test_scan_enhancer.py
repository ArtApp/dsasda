"""
Тесты для модуля обработки и улучшения сканов (scan_enhancer).
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

# Импортируем классы напрямую из файла (обходя modules/__init__.py)
exec(open(Path(__file__).parent.parent / 'modules' / 'scan_enhancer.py').read())


class TestScanEnhancementConfig:
    """Тесты конфигурации улучшения сканов."""
    
    def test_default_config(self):
        """Проверка конфигурации по умолчанию."""
        config = ScanEnhancementConfig()
        
        assert config.denoise_method == NoiseReductionMethod.BILATERAL
        assert config.denoise_strength == 10
        assert config.deskew_enabled is True
        assert config.deskew_max_angle == 15.0
        assert config.binarization_method == BinarizationMethod.ADAPTIVE_GAUSSIAN
        assert config.contrast_enhancement is True
        assert config.sharpen_enabled is True
        assert config.auto_crop is True
    
    def test_custom_config(self):
        """Проверка пользовательской конфигурации."""
        config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
            denoise_strength=20,
            deskew_enabled=False,
            target_dpi=300
        )
        
        assert config.denoise_method == NoiseReductionMethod.NON_LOCAL_MEANS
        assert config.denoise_strength == 20
        assert config.deskew_enabled is False
        assert config.target_dpi == 300
    
    def test_validate_correct_config(self):
        """Проверка валидации корректной конфигурации."""
        config = ScanEnhancementConfig()
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_incorrect_denoise_strength(self):
        """Проверка валидации некорректной силы шумоподавления."""
        config = ScanEnhancementConfig(denoise_strength=50)
        errors = config.validate()
        assert any("denoise_strength" in e for e in errors)
    
    def test_validate_incorrect_sharpen_strength(self):
        """Проверка валидации некорректной силы повышения резкости."""
        config = ScanEnhancementConfig(sharpen_strength=5.0)
        errors = config.validate()
        assert any("sharpen_strength" in e for e in errors)


class TestEnhancementResult:
    """Тесты результата улучшения."""
    
    def test_success_property(self):
        """Проверка свойства success."""
        # Успешный результат
        result = EnhancementResult(
            image=np.array([[0, 255], [255, 0]]),
            original_shape=(2, 2),
            final_shape=(2, 2),
            skew_angle=0.0,
            applied_operations=["Шумоподавление"],
            warnings=[],
            quality_score=0.8
        )
        assert result.success is True
        
        # Неудачный результат (пустые операции)
        result_empty = EnhancementResult(
            image=np.array([]),
            original_shape=(0, 0),
            final_shape=(0, 0),
            skew_angle=0.0,
            applied_operations=[],
            warnings=["Ошибка"],
            quality_score=0.0
        )
        assert result_empty.success is False


class TestScanEnhancer:
    """Тесты класса ScanEnhancer."""
    
    @pytest.fixture
    def test_image(self, tmp_path):
        """Создание тестового изображения."""
        img_path = tmp_path / "test_scan.png"
        
        # Создаем изображение с текстом
        img = np.ones((200, 400), dtype=np.uint8) * 255
        cv2.putText(img, 'Test', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
        
        # Добавляем шум
        noise = np.random.randint(0, 30, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)
        
        cv2.imwrite(str(img_path), img)
        return img_path
    
    @pytest.fixture
    def noisy_image(self, tmp_path):
        """Создание зашумленного тестового изображения."""
        img_path = tmp_path / "noisy_scan.png"
        
        img = np.ones((200, 400), dtype=np.uint8) * 200
        noise = np.random.randint(0, 100, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)
        
        cv2.imwrite(str(img_path), img)
        return img_path
    
    @pytest.fixture
    def skewed_image(self, tmp_path):
        """Создание перекошенного тестового изображения."""
        img_path = tmp_path / "skewed_scan.png"
        
        # Создаем прямое изображение
        img = np.ones((200, 400), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (350, 150), 0, 2)
        
        # Поворачиваем на 5 градусов
        M = cv2.getRotationMatrix2D((200, 100), 5.0, 1.0)
        img = cv2.warpAffine(img, M, (400, 200), borderValue=240)
        
        cv2.imwrite(str(img_path), img)
        return img_path
    
    def test_init_default(self):
        """Проверка инициализации по умолчанию."""
        enhancer = ScanEnhancer()
        assert enhancer.config is not None
        assert len(enhancer.warnings) == 0
    
    def test_init_with_config(self):
        """Проверка инициализации с конфигурацией."""
        config = ScanEnhancementConfig(denoise_strength=15)
        enhancer = ScanEnhancer(config)
        assert enhancer.config.denoise_strength == 15
    
    def test_load_image_from_path(self, test_image):
        """Проверка загрузки изображения из файла."""
        enhancer = ScanEnhancer()
        image = enhancer._load_image(str(test_image))
        
        assert image is not None
        assert isinstance(image, np.ndarray)
        assert len(image.shape) == 2  # Grayscale
    
    def test_load_image_from_array(self):
        """Проверка загрузки изображения из numpy массива."""
        enhancer = ScanEnhancer()
        img = np.ones((100, 100), dtype=np.uint8) * 128
        result = enhancer._load_image(img)
        
        assert result is not None
        assert np.array_equal(result, img)
    
    def test_load_image_not_found(self):
        """Проверка обработки несуществующего файла."""
        enhancer = ScanEnhancer()
        result = enhancer._load_image("/nonexistent/path/image.png")
        
        assert result is None
        assert len(enhancer.warnings) > 0
    
    def test_reduce_noise_median(self, noisy_image):
        """Проверка медианного фильтра шумоподавления."""
        config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.MEDIAN,
            denoise_strength=5
        )
        enhancer = ScanEnhancer(config)
        
        img = cv2.imread(str(noisy_image), cv2.IMREAD_GRAYSCALE)
        denoised = enhancer._reduce_noise(img)
        
        assert denoised.shape == img.shape
        # Дисперсия должна уменьшиться после шумоподавления
        assert np.var(denoised) <= np.var(img)
    
    def test_reduce_noise_bilateral(self, noisy_image):
        """Проверка двустороннего фильтра шумоподавления."""
        config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.BILATERAL,
            denoise_strength=10
        )
        enhancer = ScanEnhancer(config)
        
        img = cv2.imread(str(noisy_image), cv2.IMREAD_GRAYSCALE)
        denoised = enhancer._reduce_noise(img)
        
        assert denoised.shape == img.shape
    
    def test_deskew_detection(self, skewed_image):
        """Проверка обнаружения перекоса."""
        enhancer = ScanEnhancer()
        
        img = cv2.imread(str(skewed_image), cv2.IMREAD_GRAYSCALE)
        angle = enhancer._detect_skew_angle(img)
        
        # Угол должен быть близок к 5 градусам (с некоторой погрешностью)
        assert abs(abs(angle) - 5.0) < 2.0
    
    def test_deskew_correction(self, skewed_image):
        """Проверка коррекции перекоса."""
        enhancer = ScanEnhancer()
        
        img = cv2.imread(str(skewed_image), cv2.IMREAD_GRAYSCALE)
        corrected, angle = enhancer._deskew(img)
        
        assert corrected is not None
        assert abs(angle) > 0.1  # Перекос был обнаружен
    
    def test_auto_crop_document(self, tmp_path):
        """Проверка автоматического кадрирования."""
        # Создаем изображение с документом на белом фоне
        img_path = tmp_path / "document.png"
        img = np.ones((300, 400), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (350, 250), 0, -1)  # Черный документ
        cv2.imwrite(str(img_path), img)
        
        enhancer = ScanEnhancer()
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        cropped = enhancer._auto_crop_document(img)
        
        assert cropped is not None
        # Кадрированное изображение должно быть меньше оригинала
        assert cropped.shape[0] * cropped.shape[1] < img.shape[0] * img.shape[1]
    
    def test_enhance_contrast_clahe(self, test_image):
        """Проверка улучшения контраста CLAHE."""
        enhancer = ScanEnhancer()
        
        img = cv2.imread(str(test_image), cv2.IMREAD_GRAYSCALE)
        enhanced = enhancer._enhance_contrast(img)
        
        assert enhanced.shape == img.shape
        assert enhanced is not None
    
    def test_binarize_otsu(self, test_image):
        """Проверка бинаризации методом Оцу."""
        config = ScanEnhancementConfig(
            binarization_method=BinarizationMethod.OTSU
        )
        enhancer = ScanEnhancer(config)
        
        img = cv2.imread(str(test_image), cv2.IMREAD_GRAYSCALE)
        binary = enhancer._binarize(img)
        
        assert binary.shape == img.shape
        # После бинаризации должны быть только 0 и 255
        unique_values = np.unique(binary)
        assert all(v in [0, 255] for v in unique_values)
    
    def test_binarize_adaptive(self, test_image):
        """Проверка адаптивной бинаризации."""
        config = ScanEnhancementConfig(
            binarization_method=BinarizationMethod.ADAPTIVE_GAUSSIAN
        )
        enhancer = ScanEnhancer(config)
        
        img = cv2.imread(str(test_image), cv2.IMREAD_GRAYSCALE)
        binary = enhancer._binarize(img)
        
        assert binary.shape == img.shape
    
    def test_sharpen(self, test_image):
        """Проверка повышения резкости."""
        config = ScanEnhancementConfig(sharpen_strength=1.5)
        enhancer = ScanEnhancer(config)
        
        img = cv2.imread(str(test_image), cv2.IMREAD_GRAYSCALE)
        sharpened = enhancer._sharpen(img)
        
        assert sharpened.shape == img.shape
    
    def test_full_enhance_pipeline(self, test_image):
        """Проверка полного цикла улучшения."""
        config = ScanEnhancementConfig(
            denoise_method=NoiseReductionMethod.BILATERAL,
            deskew_enabled=True,
            contrast_enhancement=True,
            sharpen_enabled=True,
            auto_crop=False
        )
        enhancer = ScanEnhancer(config)
        result = enhancer.enhance(str(test_image))
        
        assert result.success is True
        assert result.image is not None
        assert len(result.applied_operations) > 0
        assert 0.0 <= result.quality_score <= 1.0
    
    def test_enhance_with_invalid_config(self, test_image):
        """Проверка обработки некорректной конфигурации."""
        config = ScanEnhancementConfig(
            denoise_strength=100,  # Некорректное значение
            sharpen_strength=10.0  # Некорректное значение
        )
        enhancer = ScanEnhancer(config)
        
        # Должны быть предупреждения о конфигурации
        assert len(enhancer.warnings) > 0


class TestHelperFunctions:
    """Тесты вспомогательных функций."""
    
    def test_preprocess_for_ocr(self, tmp_path):
        """Проверка предобработки для OCR."""
        img_path = tmp_path / "ocr_test.png"
        img = np.ones((200, 400), dtype=np.uint8) * 255
        cv2.putText(img, 'OCR Test', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
        cv2.imwrite(str(img_path), img)
        
        result = preprocess_for_ocr(str(img_path), target_dpi=300)
        
        assert result.success is True
        assert result.image is not None
        # Для OCR должно применяться агрессивное шумоподавление
        assert any("non_local_means" in op.lower() or "шумоподавление" in op.lower() 
                   for op in result.applied_operations)


class TestQualityEstimation:
    """Тесты оценки качества."""
    
    def test_quality_high_contrast(self):
        """Проверка оценки качества для изображения с высоким контрастом."""
        enhancer = ScanEnhancer()
        
        # Изображение с высоким контрастом (только черный и белый)
        img = np.zeros((100, 100), dtype=np.uint8)
        img[:50, :] = 255
        
        quality = enhancer._estimate_quality(img)
        assert 0.0 <= quality <= 1.0
    
    def test_quality_low_contrast(self):
        """Проверка оценки качества для изображения с низким контрастом."""
        enhancer = ScanEnhancer()
        
        # Изображение с низким контрастом (все значения близки)
        img = np.ones((100, 100), dtype=np.uint8) * 128
        
        quality = enhancer._estimate_quality(img)
        assert 0.0 <= quality <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
