#!/usr/bin/env python3
"""
Демонстрация работы модуля улучшения сканов (scan_enhancer).

Создает тестовые изображения с различными проблемами и показывает их улучшение.
"""

import numpy as np
import cv2
from pathlib import Path
import sys

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем классы напрямую из файла
exec(open(Path(__file__).parent / 'modules' / 'scan_enhancer.py').read())


def create_test_images(output_dir: Path):
    """Создание тестовых изображений с различными проблемами."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("СОЗДАНИЕ ТЕСТОВЫХ ИЗОБРАЖЕНИЙ")
    print("=" * 60)
    
    # 1. Изображение с шумом
    noisy_img = np.ones((300, 500), dtype=np.uint8) * 255
    cv2.putText(noisy_img, 'NOISY SCAN', (80, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 0, 3)
    cv2.putText(noisy_img, 'Line 1: Text with noise', (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    cv2.putText(noisy_img, 'Line 2: More text here', (50, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    cv2.putText(noisy_img, 'Line 3: Even more text', (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    
    # Добавляем импульсный шум
    noise = np.random.randint(0, 80, noisy_img.shape, dtype=np.uint8)
    noisy_img = cv2.add(noisy_img, noise)
    
    cv2.imwrite(str(output_dir / '01_noisy.png'), noisy_img)
    print(f"✓ Создано: 01_noisy.png (шумное изображение)")
    
    # 2. Перекошенное изображение
    skewed_base = np.ones((300, 500), dtype=np.uint8) * 255
    cv2.putText(skewed_base, 'SKEWED DOCUMENT', (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 0, 3)
    cv2.rectangle(skewed_base, (40, 100), (460, 250), 128, 2)
    cv2.putText(skewed_base, 'Content inside border', (80, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    
    # Поворот на 7 градусов
    M = cv2.getRotationMatrix2D((250, 150), 7.0, 1.0)
    skewed_img = cv2.warpAffine(skewed_base, M, (500, 300), borderValue=240)
    
    cv2.imwrite(str(output_dir / '02_skewed.png'), skewed_img)
    print(f"✓ Создано: 02_skewed.png (перекос 7°)")
    
    # 3. Низкий контраст
    low_contrast = np.ones((300, 500), dtype=np.uint8) * 180
    cv2.putText(low_contrast, 'LOW CONTRAST', (70, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 100, 2)
    cv2.putText(low_contrast, 'Faint text, hard to read', (60, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 100, 1)
    cv2.putText(low_contrast, 'Very light gray on gray', (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 100, 1)
    
    cv2.imwrite(str(output_dir / '03_low_contrast.png'), low_contrast)
    print(f"✓ Создано: 03_low_contrast.png (низкий контраст)")
    
    # 4. Комбинированные проблемы (шум + перекос + низкий контраст)
    combined = np.ones((300, 500), dtype=np.uint8) * 190
    cv2.putText(combined, 'COMBINED PROBLEMS', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 80, 2)
    cv2.putText(combined, 'Noise + Skew + Low Contrast', (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 80, 1)
    cv2.putText(combined, 'This is challenging!', (80, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 80, 1)
    
    # Шум
    noise = np.random.randint(0, 50, combined.shape, dtype=np.uint8)
    combined = cv2.add(combined, noise)
    
    # Перекос 4 градуса
    M = cv2.getRotationMatrix2D((250, 150), 4.0, 1.0)
    combined = cv2.warpAffine(combined, M, (500, 300), borderValue=200)
    
    cv2.imwrite(str(output_dir / '04_combined.png'), combined)
    print(f"✓ Создано: 04_combined.png (комбинированные проблемы)")
    
    # 5. Документ с полями для кадрирования
    with_borders = np.ones((400, 600), dtype=np.uint8) * 255
    # Рамка документа
    cv2.rectangle(with_borders, (50, 50), (550, 350), 0, 2)
    cv2.putText(with_borders, 'DOCUMENT WITH BORDERS', (100, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(with_borders, 'Auto-crop will remove white margins', (80, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 1)
    
    cv2.imwrite(str(output_dir / '05_with_borders.png'), with_borders)
    print(f"✓ Создано: 05_with_borders.png (документ с полями)")
    
    print()
    return output_dir


def enhance_all_images(input_dir: Path, output_dir: Path):
    """Обработка всех тестовых изображений."""
    print("=" * 60)
    print("ОБРАБОТКА ИЗОБРАЖЕНИЙ")
    print("=" * 60)
    
    output_dir.mkdir(exist_ok=True)
    
    # Конфигурация для обработки
    config = ScanEnhancementConfig(
        denoise_method=NoiseReductionMethod.BILATERAL,
        denoise_strength=12,
        deskew_enabled=True,
        deskew_max_angle=15.0,
        binarization_method=BinarizationMethod.ADAPTIVE_GAUSSIAN,
        contrast_enhancement=True,
        clahe_clip_limit=2.5,
        sharpen_enabled=True,
        sharpen_strength=1.5,
        auto_crop=True
    )
    
    enhancer = ScanEnhancer(config)
    
    # Обработка каждого тестового изображения
    test_files = sorted(input_dir.glob('*.png'))
    
    for img_path in test_files:
        print(f"\n📄 Обработка: {img_path.name}")
        print("-" * 40)
        
        result = enhancer.enhance(str(img_path))
        
        if result.success:
            # Сохранение результата
            output_path = output_dir / f"enhanced_{img_path.name}"
            cv2.imwrite(str(output_path), result.image)
            
            print(f"  ✓ Успешно")
            print(f"    Размер: {result.original_shape} → {result.final_shape}")
            print(f"    Перекос: {result.skew_angle:+.2f}°")
            print(f"    Качество: {result.quality_score:.2f}")
            print(f"    Операции:")
            for op in result.applied_operations:
                print(f"      - {op}")
            
            if result.warnings:
                print(f"    Предупреждения:")
                for w in result.warnings:
                    print(f"      ⚠ {w}")
        else:
            print(f"  ✗ Ошибка обработки")
            if result.warnings:
                for w in result.warnings:
                    print(f"    {w}")
    
    print()


def demonstrate_ocr_preprocessing(input_dir: Path, output_dir: Path):
    """Демонстрация предобработки для OCR."""
    print("=" * 60)
    print("ПРЕДОБРАБОТКА ДЛЯ OCR")
    print("=" * 60)
    
    output_dir.mkdir(exist_ok=True)
    
    # Используем изображение с комбинированными проблемами
    img_path = input_dir / '04_combined.png'
    
    if img_path.exists():
        print(f"\n📄 Предобработка для OCR: {img_path.name}")
        
        result = preprocess_for_ocr(str(img_path), target_dpi=300)
        
        if result.success:
            output_path = output_dir / 'ocr_ready.png'
            cv2.imwrite(str(output_path), result.image)
            
            print(f"  ✓ Готово для OCR")
            print(f"    Размер: {result.original_shape} → {result.final_shape}")
            print(f"    Качество: {result.quality_score:.2f}")
            print(f"    Операции:")
            for op in result.applied_operations:
                print(f"      - {op}")
    
    print()


def compare_denoise_methods(input_dir: Path, output_dir: Path):
    """Сравнение различных методов шумоподавления."""
    print("=" * 60)
    print("СРАВНЕНИЕ МЕТОДОВ ШУМОПОДАВЛЕНИЯ")
    print("=" * 60)
    
    output_dir.mkdir(exist_ok=True)
    
    img_path = input_dir / '01_noisy.png'
    
    if img_path.exists():
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        
        methods = [
            (NoiseReductionMethod.MEDIAN, "median", 5),
            (NoiseReductionMethod.GAUSSIAN, "gaussian", 10),
            (NoiseReductionMethod.BILATERAL, "bilateral", 10),
            (NoiseReductionMethod.NON_LOCAL_MEANS, "nl_means", 15),
        ]
        
        for method, name, strength in methods:
            config = ScanEnhancementConfig(
                denoise_method=method,
                denoise_strength=strength,
                deskew_enabled=False,
                contrast_enhancement=False,
                sharpen_enabled=False,
                binarization_method=BinarizationMethod.OTSU,
                auto_crop=False
            )
            
            enhancer = ScanEnhancer(config)
            result = enhancer.enhance(str(img_path))
            
            if result.success:
                output_path = output_dir / f'denoise_{name}.png'
                cv2.imwrite(str(output_path), result.image)
                print(f"  ✓ {name}: сохранено как denoise_{name}.png")
    
    print()


def main():
    """Основная функция демонстрации."""
    demo_dir = Path(__file__).parent / 'demo_scans'
    input_subdir = demo_dir / 'input'
    output_subdir = demo_dir / 'output'
    
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ МОДУЛЯ SCAN_ENHANCER")
    print("Улучшение некачественных сканов документов")
    print("=" * 60)
    print()
    
    # Создание тестовых изображений
    create_test_images(input_subdir)
    
    # Обработка всех изображений
    enhance_all_images(input_subdir, output_subdir)
    
    # Предобработка для OCR
    demonstrate_ocr_preprocessing(input_subdir, output_subdir)
    
    # Сравнение методов шумоподавления
    compare_denoise_methods(input_subdir, output_subdir)
    
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    print()
    print(f"Входные файлы: {input_subdir.absolute()}")
    print(f"Выходные файлы: {output_subdir.absolute()}")
    print()
    print("Для просмотра результатов откройте папку output/")
    print()


if __name__ == "__main__":
    main()
