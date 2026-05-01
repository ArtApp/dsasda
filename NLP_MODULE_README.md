# NLP-анализ для проекта Project-to-PProg

## Обзор

Модуль `nlp_analyzer.py` предоставляет возможности обработки естественного языка (NLP) для улучшения понимания контекста в описательной части проектов систем безопасности «Болид».

## Возможности

### Извлечение сущностей

Модуль автоматически извлекает следующие типы сущностей из текста проектной документации:

- **DEVICE** - Устройства (С2000М, КДЛ-2И, ДИП-34А, ИПР 513, СП2, БКИ и др.)
- **ADDRESS** - Адреса устройств (ARK127, SC39-40, BTH1 и т.д.)
- **QUANTITY** - Количество устройств (38 шт, 5 единиц и пр.)
- **LOCATION** - Местоположения (коридор, этаж, склад, офис, выход)
- **PARAMETER** - Параметры устройств
- **ACTION** - Действия и управление
- **CONNECTION** - Связи между устройствами

### Технологии

- **spaCy** - глубокое лингвистическое анализирование, NER, синтаксические зависимости
- **pymorphy3** - морфологический анализ и лемматизация русского языка
- **Регулярные выражения** - паттерны для специфичных устройств «Болид»

## Установка

```bash
# Установка зависимостей
pip install spacy pymorphy3

# Загрузка русской модели spaCy
python -m spacy download ru_core_news_sm

# Или через requirements.txt
pip install -r requirements.txt
```

## Быстрый старт

### Базовое использование

```python
from modules import analyze_project_description

text = """
В проекте используются:
- С2000М исп.02 (адрес 127) - 1 шт
- ДИП-34А-03 - 38 шт, размещены в коридорах
- ИПР 513-3АМ - 5 шт, у выходов
"""

result = analyze_project_description(text)

print(result.summary)
# Найдено устройств: 3 (типы: s2000m, dip, ipr); 
# Найдено адресов: 1; Общее количество устройств: ~44

for device in result.device_mentions:
    print(f"{device.text} → {device.normalized_form}")
```

### Продвинутое использование

```python
from modules.nlp_analyzer import RussianNLPAnalyzer, EntityCategory

# Инициализация анализатора
analyzer = RussianNLPAnalyzer(use_spacy=True)

# Анализ текста
result = analyzer.analyze_text(text)

# Доступ к результатам
print(f"Устройств: {len(result.device_mentions)}")
print(f"Адресов: {len(result.address_mentions)}")
print(f"Локаций: {len(result.location_mentions)}")
print(f"Связей: {len(result.relations)}")

# Фильтрация по типу устройства
dip_devices = [e for e in result.device_mentions 
               if e.metadata.get('device_type') == 'dip']

# Получение контекста для конкретного устройства
contexts = analyzer.get_device_context("С2000М", result)
for ctx in contexts:
    print(f"Контекст: {ctx}")

# Извлеченные связи
for relation in result.relations:
    print(f"{relation['source']} → {relation['target']} ({relation['type']})")
```

## Интеграция с PDF парсером

```python
from modules.pdf_parser import PDFParser
from modules.nlp_analyzer import analyze_project_description

# Парсинг PDF
parser = PDFParser()
pdf_result = parser.parse_file("project.pdf")

# Извлечение текста из результата
full_text = " ".join([d.description for d in pdf_result.configuration.devices])

# NLP-анализ описания
nlp_result = analyze_project_description(full_text)

# Обогащение конфигурации данными из NLP
for entity in nlp_result.location_mentions:
    # Добавление информации о местоположении к устройствам
    pass
```

## Структура результатов

### NLPAnalysisResult

```python
@dataclass
class NLPAnalysisResult:
    entities: list[ExtractedEntity]       # Все сущности
    device_mentions: list[ExtractedEntity]  # Устройства
    location_mentions: list[ExtractedEntity]  # Локации
    quantity_mentions: list[ExtractedEntity]  # Количества
    address_mentions: list[ExtractedEntity]  # Адреса
    relations: list[dict]                  # Связи между сущностями
    summary: str                           # Краткое содержание
    warnings: list[str]                    # Предупреждения
```

### ExtractedEntity

```python
@dataclass
class ExtractedEntity:
    text: str              # Исходный текст
    category: EntityCategory  # Категория
    normalized_form: str   # Лемматизированная форма
    confidence: float      # Уверенность (0.0-1.0)
    context: str           # Контекст вокруг сущности
    metadata: dict         # Дополнительные данные
```

## Примеры использования

### Поиск всех упоминаний устройства

```python
result = analyze_project_description(text)

# Найти все С2000М
s2000m_mentions = [
    e for e in result.device_mentions 
    if 's2000m' in e.metadata.get('device_type', '')
]

for mention in s2000m_mentions:
    print(f"Найдено: {mention.text}")
    print(f"Нормализовано: {mention.normalized_form}")
    print(f"Контекст: {mention.context}")
    print(f"Уверенность: {mention.confidence:.2f}")
```

### Анализ связей между устройствами

```python
result = analyze_project_description(text)

# Вывод всех связей управления
control_relations = [
    r for r in result.relations 
    if r['type'] == 'CONTROLS'
]

for rel in control_relations:
    print(f"{rel['source']} управляет {rel['target']}")
```

### Подсчет общего количества устройств

```python
result = analyze_project_description(text)

total_count = sum(
    e.metadata.get('count', 0) 
    for e in result.quantity_mentions
)

print(f"Общее количество устройств: {total_count}")
```

## Тестирование

```bash
# Запуск тестов NLP-модуля
cd /workspace
PYTHONPATH=/workspace python tests/test_nlp_analyzer.py

# Быстрый тест без spaCy
python -c "
from modules.nlp_analyzer import RussianNLPAnalyzer
analyzer = RussianNLPAnalyzer(use_spacy=False)
result = analyzer.analyze_text('С2000М - 1 шт')
print(f'Устройств: {len(result.device_mentions)}')
"
```

## Производительность

- **Без spaCy**: быстрый режим, только pymorphy3 + regex (~100мс на текст)
- **С spaCy**: полный анализ с NER и синтаксисом (~500мс-2с на текст)

Для отключения spaCy в ресурсоограниченных средах:

```python
analyzer = RussianNLPAnalyzer(use_spacy=False)
```

## Ограничения

1. **Точность распознавания**: зависит от качества исходного текста
2. **Специфичные аббревиатуры**: могут требовать добавления паттернов
3. **Контекстная зависимость**: некоторые связи могут быть пропущены
4. **Память**: spaCy модель требует ~100-200MB RAM

## Расширение функциональности

### Добавление новых паттернов устройств

```python
# В файле nlp_analyzer.py
DEVICE_PATTERNS = {
    # ... существующие паттерны
    'new_device': r'НовоеУстройство[−-]?\d+',
}
```

### Добавление категорий сущностей

```python
class EntityCategory(Enum):
    # ... существующие категории
    NEW_CATEGORY = "NEW_CATEGORY"
```

## Лицензия

Модуль является частью проекта Project-to-PProg.

## Контакты

По вопросам интеграции и расширения функциональности обращайтесь к документации проекта.
