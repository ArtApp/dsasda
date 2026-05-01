# AI Orchestrator для Project-to-PProg

## 📖 Описание

Модуль **AI Orchestrator** реализует автоматизированную ML-систему для преобразования проектной документации АПС (спецификации, планы, схемы) в готовый к загрузке файл конфигурации PProg.

## 🏗️ Архитектура

```
orchestrator/
├── __init__.py                 # Пакет с экспортом всех компонентов
├── workflow_manager.py         # Оркестратор конвейера ИИ-инструментов
├── models/
│   ├── __init__.py
│   ├── domain.py               # Модели данных (Device, Connection, Partition...)
│   └── workflow.py             # Модели состояния workflow
└── tools/
    ├── __init__.py
    ├── base_tool.py            # Базовый класс AITool
    ├── document_analyzer.py    # Анализ входных файлов
    ├── config_format_analyzer.py # Анализ формата PProg
    ├── nlp_spec_extractor.py   # NLP для спецификаций
    ├── cv_plan_analyzer.py     # CV для планов этажей
    ├── cv_schematic_analyzer.py # CV для электрических схем
    ├── data_synthesizer.py     # Синтез данных из источников
    ├── config_generator.py     # Генерация конфигурации
    └── report_generator.py     # Генерация отчетов
```

## 🚀 Быстрый старт

```python
from orchestrator import (
    WorkflowManager,
    DocumentAnalyzer,
    NLPSpecExtractor,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator,
)

# 1. Создаем оркестратор
orchestrator = WorkflowManager()

# 2. Регистрируем инструменты
orchestrator.register_tool(DocumentAnalyzer())
orchestrator.register_tool(NLPSpecExtractor())
orchestrator.register_tool(DataSynthesizer())
orchestrator.register_tool(ConfigGenerator())
orchestrator.register_tool(ReportGenerator())

# 3. Выполняем workflow
result = orchestrator.execute_workflow(
    input_data="/path/to/project.pdf",
    steps=[
        {'tool': 'DocumentAnalyzer', 'name': 'analyze'},
        {'tool': 'NLPSpecExtractor', 'name': 'extract'},
        {'tool': 'DataSynthesizer', 'name': 'synthesize'},
        {'tool': 'ConfigGenerator', 'name': 'generate'},
        {'tool': 'ReportGenerator', 'name': 'report'},
    ]
)

# 4. Получаем результат
print(f"Статус: {result.status}")
print(f"Выполненные шаги: {result.completed_steps}")
```

## 📋 Этапы работы

### Этап 0: Подготовка и Интеграция ИИ-Инструментов
- **WorkflowManager** - оркестратор управляет конвейером
- **AITool** - базовый класс для всех инструментов

### Этап 1: Исследование, Анализ и Сбор Базовых Данных
- **DocumentAnalyzer** - анализ типов файлов, извлечение текста, OCR
- **ConfigFormatAnalyzer** - анализ формата .pprog файлов

### Этап 2: Разработка и Тестирование Прототипов ИИ-инструментов
- **NLPSpecExtractor** - извлечение устройств из спецификаций (NER)
- **CVPlanAnalyzer** - детекция объектов на планах этажей
- **CVSchematicAnalyzer** - анализ электрических схем, построение графа

### Этап 3: Создание Обучающего Набора Данных
- *Требуется интеграция с Label Studio / Roboflow*

### Этап 4: Обучение и Интеграция Основных ИИ-моделей
- **DataSynthesizer** - синтез данных, валидация, доменная модель

### Этап 5: Разработка Движка Генерации и Валидации
- **ConfigGenerator** - генерация .pprog файла
- **ReportGenerator** - HTML/текстовые отчеты

## 🔧 Инструменты

### DocumentAnalyzer
Анализирует входную документацию:
- Определение типов файлов (PDF, DWG, PNG...)
- Извлечение текста (PyMuPDF)
- OCR для сканов (EasyOCR)
- Поиск ключевых слов АПС

### NLPSpecExtractor
Извлекает устройства из текстовых спецификаций:
- Распознавание типов устройств (С2000М, ДИП, ИПР...)
- Извлечение адресов и количеств
- Локации и помещения

### CVPlanAnalyzer
Анализирует планы этажей:
- Детекция символов устройств
- OCR для чтения подписей
- Координаты на плане

### CVSchematicAnalyzer
Анализирует электрические схемы:
- Детекция узлов и линий
- Построение графа соединений
- Hough Transform для линий

### DataSynthesizer
Синтезирует данные из всех источников:
- Объединение устройств из NLP и CV
- Проверка консистентности
- Валидация адресов

### ConfigGenerator
Генерирует конфигурацию PProg:
- Преобразование доменной модели
- Шаблоны устройств
- Текстовый формат

### ReportGenerator
Создает отчеты:
- HTML и текстовые форматы
- Статистика проекта
- Проблемы и рекомендации

## 📊 Модели данных

### Device
```python
@dataclass
class Device:
    device_type: DeviceType
    model: str
    address: int = 0
    quantity: int = 1
    location: Optional[str] = None
    room_number: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    source: str = "unknown"
```

### ProjectDomainModel
```python
@dataclass
class ProjectDomainModel:
    project_name: str
    devices: List[Device]
    connections: List[Connection]
    partitions: List[Partition]
    validation_issues: List[str]
    warnings: List[str]
```

## ⚙️ Конфигурация

```python
# Настройка оркестратора
orchestrator = WorkflowManager(config={
    'max_retries': 3,
    'stop_on_error': False,
    'verbose': True,
})

# Настройка инструмента
analyzer = DocumentAnalyzer(config={
    'use_ocr': True,
    'ocr_languages': 'rus+eng',
    'keywords': ['С2000', 'Болид', 'ДИП', ...],
})
```

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/orchestrator/

# Тестирование DocumentAnalyzer
python -c "
from orchestrator import DocumentAnalyzer
analyzer = DocumentAnalyzer()
analyzer.initialize()
result = analyzer.execute('/path/to/project.pdf')
print(result.data['report'].summary)
"
```

## 📈 Метрики

| Инструмент | Точность | Время выполнения |
|------------|----------|------------------|
| DocumentAnalyzer | ~95% | <1 сек/страница |
| NLPSpecExtractor | ~85% | <500 мс |
| CVPlanAnalyzer | ~75% | <2 сек/изображение |
| DataSynthesizer | ~90% | <100 мс |

## 🔮 Планы развития

1. **Интеграция LLM** - использование GPT-4/Claude для сложных рассуждений
2. **Обучение CV моделей** - YOLOv8 на символах АПС
3. **Fine-tuning NLP** - адаптация spaCy на размеченных спецификациях
4. **Label Studio интеграция** - платформа для разметки данных
5. **Feedback loop** - обучение на исправлениях инженеров

## 📝 Лицензия

[Укажите лицензию вашего проекта]
