# Модуль обработки и улучшения сканов (Scan Enhancer)

## Обзор

Модуль `scan_enhancer.py` предназначен для предобработки и улучшения некачественных сканов документов перед извлечением текста. Модуль решает следующие проблемы:

- **Шум** на изображении (зернистость, артефакты сжатия)
- **Перекос** документа (неправильное позиционирование при сканировании)
- **Низкий контраст** (бледный текст, плохое освещение)
- **Низкое DPI** (размытый текст)
- **Лишние поля** (необрезанные границы скана)

## Установка зависимостей

Модуль использует библиотеку OpenCV:

```bash
pip install opencv-python-headless
# или для GUI версии
pip install opencv-python

# Дополнительные зависимости (уже есть в requirements.txt)
pip install numpy
```

## Быстрый старт

### Базовое использование

```python
from modules.scan_enhancer import enhance_scan

# Улучшить скан с настройками по умолчанию
result = enhance_scan("path/to/scan.jpg", output_path="enhanced.png")

print(f"Качество: {result.quality_score:.2f}")
print(f"Применено операций: {len(result.applied_operations)}")
for op in result.applied_operations:
    print(f"  - {op}")
```

### Предобработка для OCR

```python
from modules.scan_enhancer import preprocess_for_ocr

# Оптимальные настройки для распознавания текста
result = preprocess_for_ocr("scan.jpg", target_dpi=300)

# Результат готов для передачи в Tesseract или другой OCR-движок
cv2.imwrite("ready_for_ocr.png", result.image)
```

## Конфигурация

### Параметры ScanEnhancementConfig

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `denoise_method` | NoiseReductionMethod | BILATERAL | Метод шумоподавления |
| `denoise_strength` | int | 10 | Сила шумоподавления (1-30) |
| `deskew_enabled` | bool | True | Включить коррекцию перекоса |
| `deskew_max_angle` | float | 15.0 | Максимальный угол коррекции (градусы) |
| `binarization_method` | BinarizationMethod | ADAPTIVE_GAUSSIAN | Метод бинаризации |
| `contrast_enhancement` | bool | True | Включить улучшение контраста (CLAHE) |
| `clahe_clip_limit` | float | 2.0 | Ограничение CLAHE (0.5-4.0) |
| `sharpen_enabled` | bool | True | Включить повышение резкости |
| `sharpen_strength` | float | 1.5 | Сила повышения резкости (0.5-3.0) |
| `auto_crop` | bool | True | Автоматическое кадрирование |
| `target_dpi` | Optional[int] | None | Целевое DPI для масштабирования |

### Методы шумоподавления

```python
from modules.scan_enhancer import NoiseReductionMethod

NoiseReductionMethod.MEDIAN          # Медианный фильтр (быстро, удаляет импульсный шум)
NoiseReductionMethod.GAUSSIAN        # Фильтр Гаусса (общее сглаживание)
NoiseReductionMethod.BILATERAL       # Двусторонний фильтр (сохраняет края)
NoiseReductionMethod.NON_LOCAL_MEANS # NL-Means (лучшее качество, медленнее)
```

### Методы бинаризации

```python
from modules.scan_enhancer import BinarizationMethod

BinarizationMethod.OTSU              # Глобальный порог Оцу
BinarizationMethod.ADAPTIVE_MEAN     # Адаптивный средний порог
BinarizationMethod.ADAPTIVE_GAUSSIAN # Адаптивный гауссов порог
BinarizationMethod.SAUVOLA           # Метод Sauvola (для текста)
```

## Примеры использования

### Пример 1: Обработка зашумленного скана

```python
from modules.scan_enhancer import ScanEnhancer, ScanEnhancementConfig, NoiseReductionMethod

config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
    denoise_strength=15,
    deskew_enabled=True,
    contrast_enhancement=True,
    sharpen_enabled=True
)

enhancer = ScanEnhancer(config)
result = enhancer.enhance("noisy_scan.jpg")

if result.success:
    print(f"✓ Улучшение выполнено")
    print(f"  Перекос: {result.skew_angle:+.2f}°")
    print(f"  Качество: {result.quality_score:.2f}")
```

### Пример 2: Исправление сильного перекоса

```python
from modules.scan_enhancer import ScanEnhancementConfig

config = ScanEnhancementConfig(
    deskew_enabled=True,
    deskew_max_angle=25.0,  # Увеличиваем максимальный угол
    auto_crop=True  # Обрезать поля после выравнивания
)

result = enhance_scan("skewed_document.png", config=config)
```

### Пример 3: Подготовка к OCR с низким DPI

```python
from modules.scan_enhancer import preprocess_for_ocr

# Масштабируем до 300 DPI и применяем агрессивное шумоподавление
result = preprocess_for_ocr("low_dpi_scan.jpg", target_dpi=300)

# Сохраняем результат
import cv2
cv2.imwrite("ocr_ready.png", result.image)
```

### Пример 4: Интеграция с pytesseract

```python
from modules.scan_enhancer import preprocess_for_ocr
import pytesseract
import cv2

# Предобработка
result = preprocess_for_ocr("document.jpg")

# Распознавание текста
text = pytesseract.image_to_string(result.image, lang='rus+eng')
print(text)
```

### Пример 5: Пакетная обработка

```python
from pathlib import Path
from modules.scan_enhancer import enhance_scan, ScanEnhancementConfig

config = ScanEnhancementConfig(
    denoise_strength=12,
    deskew_max_angle=10.0,
    target_dpi=300
)

input_dir = Path("scans/input")
output_dir = Path("scans/output")
output_dir.mkdir(exist_ok=True)

for scan_file in input_dir.glob("*.jpg"):
    print(f"Обработка {scan_file.name}...")
    result = enhance_scan(scan_file, config=config)
    
    if result.success:
        output_path = output_dir / f"enhanced_{scan_file.stem}.png"
        cv2.imwrite(str(output_path), result.image)
        print(f"  ✓ Сохранено: {output_path}")
    else:
        print(f"  ✗ Ошибка: {result.warnings}")
```

## Результат обработки

Класс `EnhancementResult` содержит:

```python
@dataclass
class EnhancementResult:
    image: np.ndarray              # Улучшенное изображение
    original_shape: Tuple[int, int] # Исходные размеры (height, width)
    final_shape: Tuple[int, int]    # Финальные размеры
    skew_angle: float              # Обнаруженный угол перекоса
    applied_operations: list[str]   # Список примененных операций
    warnings: list[str]            # Предупреждения
    quality_score: float           # Оценка качества (0.0-1.0)
    
    @property
    def success(self) -> bool:
        """Успешно ли выполнено улучшение"""
```

## Алгоритмы

### 1. Шумоподавление

- **Медианный фильтр**: Удаляет импульсный шум ("соль-перец")
- **Фильтр Гаусса**: Сглаживает высокочастотный шум
- **Двусторонний фильтр**: Сохраняет края при сглаживании
- **NL-Means**: Лучшее качество за счет поиска похожих паттернов

### 2. Определение перекоса

Используется комбинация методов:
- **Преобразование Хафа**: Обнаружение линий текста
- **Проекционный профиль**: Анализ горизонтальных проекций при разных углах

### 3. Улучшение контраста

- **CLAHE** (Contrast Limited Adaptive Histogram Equalization): Локальное улучшение контраста с ограничением усиления шума

### 4. Бинаризация

- **Адаптивные методы**: Порог вычисляется локально для каждой области
- **Метод Sauvola**: Учитывает локальную дисперсию для текста

### 5. Повышение резкости

- **Unsharp masking**: Усиление высоких частот для улучшения четкости краев

## Тестирование

```bash
# Запуск тестов
python -m pytest tests/test_scan_enhancer.py -v

# Тесты покрывают:
# - Конфигурацию и валидацию
# - Загрузку изображений
# - Шумоподавление различными методами
# - Определение и коррекцию перекоса
# - Автоматическое кадрирование
# - Улучшение контраста и бинаризацию
# - Повышение резкости
# - Полный цикл обработки
# - Оценку качества
```

## Интеграция с PDF парсером

Модуль может быть интегрирован в `pdf_parser.py` для обработки сканированных PDF:

```python
# В modules/pdf_parser.py
from modules.scan_enhancer import preprocess_for_ocr
import fitz  # PyMuPDF
import cv2
import numpy as np

def extract_text_from_scanned_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = ""
    
    for page_num, page in enumerate(doc):
        # Рендер страницы в изображение
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x масштаб
        img_data = pix.tobytes("png")
        
        # Конвертация в numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        # Предобработка для OCR
        result = preprocess_for_ocr(img)
        
        # OCR (требуется pytesseract)
        try:
            import pytesseract
            text = pytesseract.image_to_string(result.image, lang='rus+eng')
            full_text += text + "\n"
        except ImportError:
            pass
    
    doc.close()
    return full_text
```

## Рекомендации

### Для текстовых документов

```python
config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
    denoise_strength=15,
    binarization_method=BinarizationMethod.ADAPTIVE_GAUSSIAN,
    sharpen_strength=1.8,
    target_dpi=300
)
```

### Для документов с низким качеством

```python
config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.BILATERAL,
    denoise_strength=20,
    deskew_max_angle=20.0,
    clahe_clip_limit=3.0,
    sharpen_strength=2.0,
    auto_crop=True
)
```

### Для быстрой обработки

```python
config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.MEDIAN,
    denoise_strength=5,
    deskew_enabled=True,
    contrast_enhancement=False,
    sharpen_enabled=False
)
```

## Лицензия

Модуль является частью проекта Project-to-PProg.
