# Интеграция обработки сканов с PDF парсером

## Обзор

Модуль `pdf_parser.py` теперь интегрирован с модулем `scan_enhancer.py` для автоматической обработки сканированных документов. При парсинге PDF система автоматически определяет тип документа (текстовый или сканированный) и применяет соответствующие методы обработки.

## Основные возможности

### 1. Автоматическое определение типа PDF

```python
from modules.pdf_parser import PDFParser

parser = PDFParser()
# Метод _is_scanned_pdf() анализирует документ:
# - Проверяет наличие изображений
# - Оценивает количество текста на страницу
# - Принимает решение о необходимости OCR
```

### 2. Улучшение качества сканов перед OCR

Для сканированных документов применяются:
- **Шумоподавление** (медианный, Гаусса, двусторонний фильтр, NL-Means)
- **Коррекция перекоса** (автоматическое определение угла до ±15°)
- **Улучшение контраста** (CLAHE, адаптивная бинаризация)
- **Повышение резкости** для низкого DPI
- **Автоматическое кадрирование** документов
- **Масштабирование** к целевому DPI

### 3. OCR с улучшенными изображениями

После улучшения качества изображений выполняется распознавание текста через pytesseract.

## Использование

### Базовое использование

```python
from modules.pdf_parser import parse_pdf_project

# Автоматическое определение и обработка сканов
result = parse_pdf_project("document.pdf")
print(result.configuration)
print(result.enhancement_results)  # Результаты улучшения изображений
```

### Парсинг сканированного PDF с настройками

```python
from modules.pdf_parser import parse_scanned_pdf
from modules.scan_enhancer import ScanEnhancementConfig, NoiseReductionMethod

# Конфигурация улучшения сканов
enhance_config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.BILATERAL,
    denoise_strength=15,
    deskew_enabled=True,
    target_dpi=300
)

# Парсинг с улучшением
result = parse_scanned_pdf(
    "scanned_document.pdf",
    enhance_config=enhance_config,
    ocr_languages="rus+eng",
    use_nlp=True
)

# Доступ к результатам
print(f"Извлечено устройств: {len(result.configuration.devices)}")
print(f"Улучшено изображений: {len(result.enhancement_results)}")
for i, enh_result in enumerate(result.enhancement_results):
    print(f"  Изображение {i+1}: угол перекоса = {enh_result.skew_angle:.2f}°")
```

### Продвинутая конфигурация

```python
from modules.pdf_parser import PDFParser, ScannedPDFParserConfig
from modules.scan_enhancer import ScanEnhancementConfig, BinarizationMethod

# Конфигурация улучшения
enhance_config = ScanEnhancementConfig(
    denoise_strength=20,
    binarization_method=BinarizationMethod.SAUVOLA,
    sharpen_enabled=True,
    sharpen_strength=2.0,
    target_dpi=300
)

# Конфигурация парсера
scan_config = ScannedPDFParserConfig(
    enhance_scans=True,
    scan_enhancement_config=enhance_config,
    ocr_languages="rus+eng+deu",
    min_image_dpi=200
)

# Создание парсера
parser = PDFParser(use_nlp=True, scan_config=scan_config)

# Парсинг
result = parser.parse_file("project.pdf")

# Анализ результатов
if result.enhancement_results:
    print(f"Обработано {len(result.enhancement_results)} изображений")
    
if result.warnings:
    print("Предупреждения:")
    for w in result.warnings:
        print(f"  - {w}")
```

## API

### Классы

#### `ScannedPDFParserConfig`
Конфигурация обработки сканированных PDF.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `enhance_scans` | bool | True | Включить улучшение сканов |
| `scan_enhancement_config` | ScanEnhancementConfig | None | Конфигурация улучшения |
| `ocr_enabled` | bool | True | Включить OCR |
| `ocr_languages` | str | "rus+eng" | Языки для OCR |
| `min_image_dpi` | int | 200 | Минимальное DPI |
| `min_text_confidence` | float | 0.5 | Минимальная уверенность OCR |

#### `ParseResult`
Результат парсинга (расширен).

| Параметр | Тип | Описание |
|----------|-----|----------|
| `configuration` | Configuration | Извлеченная конфигурация |
| `warnings` | list[str] | Предупреждения |
| `errors` | list[str] | Ошибки |
| `nlp_result` | NLPAnalysisResult | Результаты NLP-анализа |
| `enhancement_results` | list[EnhancementResult] | **Новое:** Результаты улучшения сканов |

### Функции

#### `parse_scanned_pdf(pdf_path, enhance_config, ocr_languages, use_nlp)`
Удобная функция для парсинга сканированных PDF.

```python
result = parse_scanned_pdf(
    "scan.pdf",
    enhance_config=ScanEnhancementConfig(target_dpi=300),
    ocr_languages="rus",
    use_nlp=False
)
```

#### `parse_pdf_project(pdf_path, use_nlp, scan_config)`
Базовая функция парсинга с поддержкой конфигурации сканов.

```python
from modules.pdf_parser import parse_pdf_project, ScannedPDFParserConfig

config = ScannedPDFParserConfig(ocr_languages="rus+eng")
result = parse_pdf_project("doc.pdf", use_nlp=True, scan_config=config)
```

## Рабочий процесс

```
┌─────────────────┐
│   PDF файл      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Определение     │──── Текстовый ────▶ Извлечение текста
│ типа PDF        │                        (стандартное)
└────────┬────────┘
         │
         │ Сканированный
         ▼
┌─────────────────┐
│ Извлечение      │
│ изображений     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Улучшение       │◀─── ScanEnhancer
│ качества        │     (шум, перекос, контраст)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OCR             │◀─── pytesseract
│ (распознавание) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ NLP-анализ      │◀─── RussianNLPAnalyzer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Парсинг         │
│ устройств/зон   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ParseResult     │
│ + enhancement_  │
│   results       │
└─────────────────┘
```

## Зависимости

Для работы с сканированными PDF требуются:

```bash
# Обязательные
pip install PyMuPDF opencv-python numpy

# Для OCR
pip install pytesseract
# Также требуется установка Tesseract OCR в систему:
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
# macOS: brew install tesseract tessdata_best

# Опционально (для NLP)
pip install pymorphy3 spacy
```

## Обработка ошибок

```python
result = parse_scanned_pdf("document.pdf")

if result.errors:
    print("Ошибки:")
    for error in result.errors:
        print(f"  ❌ {error}")

if result.warnings:
    print("Предупреждения:")
    for warning in result.warnings:
        print(f"  ⚠ {warning}")

# Проверка успешности OCR
if not result.configuration.devices and not result.warnings:
    print("Возможно, OCR не смог распознать текст")
```

## Примеры использования

### Пример 1: Быстрый старт

```python
from modules.pdf_parser import parse_scanned_pdf

result = parse_scanned_pdf("project_scan.pdf")
print(f"Найдено устройств: {len(result.configuration.devices)}")
```

### Пример 2: Обработка некачественного скана

```python
from modules.pdf_parser import parse_scanned_pdf
from modules.scan_enhancer import ScanEnhancementConfig, NoiseReductionMethod

config = ScanEnhancementConfig(
    denoise_method=NoiseReductionMethod.NON_LOCAL_MEANS,
    denoise_strength=25,  # Сильное шумоподавление
    deskew_max_angle=20.0,  # Коррекция большого перекоса
    binarization_method=BinarizationMethod.SAUVOLA,  # Для неравномерного освещения
    target_dpi=300  # Масштабирование к 300 DPI
)

result = parse_scanned_pdf("poor_quality_scan.pdf", enhance_config=config)
```

### Пример 3: Пакетная обработка

```python
from pathlib import Path
from modules.pdf_parser import parse_scanned_pdf

pdf_files = list(Path("./scans").glob("*.pdf"))

for pdf_file in pdf_files:
    print(f"Обработка {pdf_file.name}...")
    result = parse_scanned_pdf(pdf_file)
    
    if result.configuration.devices:
        print(f"  ✓ Найдено {len(result.configuration.devices)} устройств")
    else:
        print(f"  ✗ Устройства не найдены")
    
    if result.enhancement_results:
        print(f"  Улучшено изображений: {len(result.enhancement_results)}")
```

## Тестирование

```bash
# Запуск тестов интеграции
pytest tests/test_pdf_scan_integration.py -v

# Все тесты должны пройти (13 passed)
```

## Миграция

Старый код продолжает работать без изменений:

```python
# Старый код (работает как прежде)
from modules.pdf_parser import parse_pdf_project
result = parse_pdf_project("document.pdf")

# Новый код с расширенными возможностями
from modules.pdf_parser import parse_scanned_pdf
result = parse_scanned_pdf("scanned_document.pdf")
```
