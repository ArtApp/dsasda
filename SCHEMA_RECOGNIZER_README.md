# Модуль распознавания адресов с графических схем

## Обзор

Модуль `schema_recognizer.py` предоставляет функциональность для распознавания адресов устройств с графических схем и планов этажей из PDF-документации. Использует OpenCV для обработки изображений и Tesseract OCR для извлечения текста.

## Возможности

- **Извлечение страниц PDF в изображения** - Конвертация страниц PDF в изображения с настраиваемым DPI
- **Предобработка изображений** - Улучшение качества для лучшего распознавания:
  - Конвертация в оттенки серого
  - Bilateral фильтрация для шумоподавления
  - Адаптивная бинаризация
  - Морфологические операции
- **OCR распознавание** - Использование Tesseract для извлечения текста с bounding boxes
- **Поиск адресов по паттернам**:
  - ARK1, ARK2, etc.
  - SC39-40, SC41-42
  - BTH1, BTH2
  - "адрес X"
  - "№X"
  - И другие форматы
- **Определение типа устройства** - Автоматическое определение типа устройства из контекста
- **Оценка местоположения** - Определение положения на схеме (верхняя/нижняя, левая/правая часть)
- **Удаление дубликатов** - Интеллектуальное объединение повторяющихся результатов
- **Экспорт результатов** - Поддержка форматов text, JSON, CSV

## Установка зависимостей

```bash
pip install opencv-python pytesseract numpy PyMuPDF
```

Также требуется установка Tesseract OCR:

### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

### macOS
```bash
brew install tesseract
brew install tesseract-lang
```

### Windows
Скачайте установщик с https://github.com/UB-Mannheim/tesseract/wiki

## Примеры использования

### Распознавание адресов из PDF

```python
from modules.schema_recognizer import SchemaAddressRecognizer, recognize_addresses_from_pdf

# Простой способ
result = recognize_addresses_from_pdf('path/to/floor_plan.pdf', dpi=150)

# Расширенный способ с настройками
recognizer = SchemaAddressRecognizer(
    tesseract_cmd='/usr/bin/tesseract',  # Опционально, если не в PATH
    lang='rus+eng'  # Языки распознавания
)

result = recognizer.process_pdf(
    'path/to/floor_plan.pdf',
    min_image_size=10000,
    dpi=150
)

# Обработка результатов
print(f"Обработано страниц: {result.total_pages_processed}")
print(f"Найдено адресов: {len(result.addresses)}")

for addr in result.addresses:
    print(f"  - {addr.text} (адрес {addr.address_value})")
    print(f"    Тип устройства: {addr.device_type}")
    print(f"    Местоположение: {addr.location}")
    print(f"    Уверенность: {addr.confidence:.2f}")
    print(f"    Страница: {addr.page_number}")

# Экспорт результатов
recognizer.export_results(result, 'output.txt', format='text')
recognizer.export_results(result, 'output.json', format='json')
recognizer.export_results(result, 'output.csv', format='csv')
```

### Распознавание адресов из изображения

```python
from modules.schema_recognizer import recognize_addresses_from_image

result = recognize_addresses_from_image('path/to/schema.png')

for addr in result.addresses:
    print(f"{addr.text}: адрес {addr.address_value}")
```

### Обработка numpy массива

```python
import cv2
from modules.schema_recognizer import SchemaAddressRecognizer

recognizer = SchemaAddressRecognizer()

# Загрузка изображения через OpenCV
img = cv2.imread('schema.png')

# Обработка
result = recognizer.process_image(img, page_number=1)

for addr in result.addresses:
    print(f"Найден адрес: {addr.text}")
```

## Структура данных

### DetectedAddress
```python
@dataclass
class DetectedAddress:
    text: str                    # Распознанный текст
    address_value: Optional[int] # Числовое значение адреса
    device_type: Optional[str]   # Тип устройства
    location: Optional[str]      # Местоположение на схеме
    confidence: float            # Уверенность (0.0-1.0)
    bbox: tuple                  # Bounding box (x, y, w, h)
    page_number: int             # Номер страницы
    metadata: dict               # Дополнительные данные
```

### SchemaAnalysisResult
```python
@dataclass
class SchemaAnalysisResult:
    addresses: list[DetectedAddress]  # Найденные адреса
    warnings: list[str]               # Предупреждения
    errors: list[str]                 # Ошибки
    total_pages_processed: int        # Всего обработано страниц
    images_extracted: int             # Всего обработано изображений
```

## Паттерны адресов

Модуль поддерживает следующие паттерны для поиска адресов:

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `ARK\s*(\d+)` | Адреса ARK | ARK1, ARK2 |
| `SC\s*(\d+)[-\s](\d+)` | Адреса SC | SC39-40 |
| `BTH\s*(\d+)` | Адреса BTH | BTH1, BTH2 |
| `[Аа]дрес\s*[:\(]?\s*(\d+)` | Слово "адрес" | адрес 1, Адрес(5) |
| `№\s*(\d+)` | Номер | №1, № 2 |
| `КДЛ[-\s]*2И.*?[Аа]дрес\s*[:\(]?\s*(\d+)` | КДЛ с адресом | КДЛ-2И адрес 3 |
| `ДИП[-\s]*34[А-Я]?.*?(\d{1,3})` | ДИП-34 с номером | ДИП-34А 015 |
| `ИПР\s*513.*?(\d{1,3})` | ИПР 513 с номером | ИПР 513-3А 042 |

## Интеграция с PDF парсером

Модуль может использоваться совместно с `pdf_parser.py` для комплексного анализа проектной документации:

```python
from modules.pdf_parser import PDFParser
from modules.schema_recognizer import SchemaAddressRecognizer

# Текстовый парсинг
pdf_parser = PDFParser(use_nlp=True)
pdf_result = pdf_parser.parse_file('project.pdf')

# Распознавание схем
schema_recognizer = SchemaAddressRecognizer()
schema_result = schema_recognizer.process_pdf('project.pdf')

# Комбинирование результатов
print("Текстовые данные:")
for device in pdf_result.configuration.devices:
    print(f"  {device.device_type} - адрес {device.address}")

print("\nДанные со схем:")
for addr in schema_result.addresses:
    print(f"  {addr.device_type} - адрес {addr.address_value}")
```

## Тестирование

```bash
python -m unittest tests.test_schema_recognizer -v
```

## Ограничения

- Качество распознавания зависит от качества исходных схем
- Для рукописных пометок точность может быть низкой
- Требуется установленный Tesseract OCR
- Для работы с PDF требуется PyMuPDF

## Лицензия

Интегрировано в проект Project-to-PProg.
