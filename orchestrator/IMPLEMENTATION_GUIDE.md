# 📘 Руководство по внедрению AI Orchestrator для Project-to-PProg

## 🎯 Обзор системы

Данная система автоматизирует процесс преобразования проектной документации АПС (автоматических систем пожарной сигнализации) в готовый к загрузке файл конфигурации PProg для приборов Болид (С2000М и др.).

---

## 📋 Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Пошаговое руководство по этапам](#пошаговое-руководство-по-этапам)
3. [Примеры использования](#примеры-использования)
4. [Настройка и конфигурация](#настройка-и-конфигурация)
5. [Интеграция с внешними сервисами](#интеграция-с-внешними-сервисами)
6. [Частые вопросы и решение проблем](#частые-вопросы-и-решение-проблем)

---

## 🏗️ Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                     Workflow Manager                             │
│                    (Оркестратор конвейера)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Этап 1       │   │   Этап 2        │   │   Этап 4-5      │
│  Анализ       │   │   Извлечение    │   │   Синтез &      │
│  данных       │   │   данных        │   │   Генерация     │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ • Document    │   │ • NLP Spec      │   │ • Data          │
│   Analyzer    │   │   Extractor     │   │   Synthesizer   │
│ • Config      │   │ • CV Plan       │   │ • Config        │
│   Format      │   │   Analyzer      │   │   Generator     │
│   Analyzer    │   │ • CV Schematic  │   │ • Report        │
│               │   │   Analyzer      │   │   Generator     │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 📖 Пошаговое руководство по этапам

### 🔹 Этап 0: Подготовка и Интеграция ИИ-Инструментов

#### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

**Основные зависимости:**
- `pymupdf` - извлечение текста из PDF
- `easyocr` - OCR для сканов
- `spacy` - NLP обработка текста
- `opencv-python` - компьютерное зрение
- `langchain` - интеграция с LLM (опционально)

#### 2. Инициализация оркестратора

```python
from orchestrator import WorkflowManager

# Создание оркестратора с настройками
orchestrator = WorkflowManager(config={
    'max_retries': 3,           # Максимум попыток при ошибке
    'stop_on_error': False,     # Продолжать при ошибке шага
    'verbose': True,            # Подробное логирование
    'timeout_per_step': 300,    # Таймаут на шаг (сек)
})
```

#### 3. Регистрация инструментов

```python
from orchestrator.tools import (
    DocumentAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator
)

# Регистрация всех инструментов
orchestrator.register_tool(DocumentAnalyzer())
orchestrator.register_tool(NLPSpecExtractor())
orchestrator.register_tool(CVPlanAnalyzer())
orchestrator.register_tool(CVSchematicAnalyzer())
orchestrator.register_tool(DataSynthesizer())
orchestrator.register_tool(ConfigGenerator())
orchestrator.register_tool(ReportGenerator())
```

---

### 🔹 Этап 1: Исследование, Анализ и Сбор Базовых Данных

#### Instrument: DocumentAnalyzer

**Назначение:** Анализ входной документации, определение типов файлов, извлечение текста.

```python
from orchestrator import DocumentAnalyzer

analyzer = DocumentAnalyzer(config={
    'use_ocr': True,              # Включить OCR для сканов
    'ocr_languages': 'rus+eng',   # Языки OCR
    'keywords': [                 # Ключевые слова для поиска
        'С2000', 'Болид', 'ДИП', 'ИПР', 'СПИ',
        'АПС', 'пожарная', 'извещатель',
        'спецификация', 'схема', 'план'
    ],
    'min_confidence': 0.7         # Минимальная уверенность
})

analyzer.initialize()

# Анализ файла
result = analyzer.execute('/path/to/project.pdf')

# Получение отчёта
report = result.data['report']
print(f"Типов файлов: {len(report.file_types)}")
print(f"Объём текста: {report.text_length} символов")
print(f"Ключевые слова: {report.detected_keywords}")
```

**Выходные данные:**
```json
{
  "file_types": ["PDF", "PNG"],
  "text_length": 54212,
  "images_count": 18,
  "detected_keywords": ["С2000", "ДИП-34А", "ИПР", "АПС"],
  "summary": "Проект АУПС, Щеткина 4, мазутонасосная"
}
```

#### Instrument: ConfigFormatAnalyzer

**Назначение:** Анализ формата .pprog файлов для понимания структуры.

```python
from orchestrator import ConfigFormatAnalyzer

format_analyzer = ConfigFormatAnalyzer(config={
    'sample_files': ['/path/to/sample1.pprog', '/path/to/sample2.pprog'],
    'detect_checksums': True,
    'use_llm_analysis': False  # Требуется интеграция с LLM
})

format_analyzer.initialize()
result = format_analyzer.execute('/path/to/samples/')

# Гипотетическая спецификация формата
format_spec = result.data['format_spec']
print(format_spec)
```

---

### 🔹 Этап 2: Разработка и Тестирование Прототипов ИИ-инструментов

#### Instrument: NLPSpecExtractor

**Назначение:** Извлечение устройств из текстовых спецификаций.

```python
from orchestrator import NLPSpecExtractor

nlp_extractor = NLPSpecExtractor(config={
    'use_spacy': True,           # Использовать spaCy NER
    'use_regex': True,           # Использовать regex паттерны
    'device_patterns': {         # Паттерны для устройств
        'control_panel': r'С2000[-\s]?\w+',
        'smoke_detector': r'ДИП[-\s]?\d+[А-Я]?',
        'manual_call_point': r'ИПР[-\s]?\d+'
    },
    'location_patterns': [
        r'пом\.?\s*\d+',
        r'этаж\s*\d+',
        r'[А-Я][а-я]+\s*ул\.'
    ]
})

nlp_extractor.initialize()

# Пример текста спецификации
spec_text = """
Спецификация оборудования:
1. Прибор приёмно-контрольный С2000М - 1 шт., щитовая
2. Извещатель дымовой ДИП-34А - 15 шт., помещения 1-5
3. Извещатель ручной ИПР-513-3А - 3 шт., коридоры
"""

result = nlp_extractor.execute({'text': spec_text})

# Извлечённые устройства
devices = result.data['devices']
for device in devices:
    print(f"{device.model}: {device.quantity} шт., {device.location}")
```

**Выходные данные:**
```json
[
  {
    "device_type": "CONTROL_PANEL",
    "model": "С2000М",
    "quantity": 1,
    "location": "щитовая",
    "confidence": "HIGH"
  },
  {
    "device_type": "SMOKE_DETECTOR",
    "model": "ДИП-34А",
    "quantity": 15,
    "location": "помещения 1-5",
    "confidence": "HIGH"
  },
  {
    "device_type": "MANUAL_CALL_POINT",
    "model": "ИПР-513-3А",
    "quantity": 3,
    "location": "коридоры",
    "confidence": "HIGH"
  }
]
```

#### Instrument: CVPlanAnalyzer

**Назначение:** Анализ планов этажей, детекция устройств.

```python
from orchestrator import CVPlanAnalyzer

cv_plan = CVPlanAnalyzer(config={
    'use_opencv': True,          # Использовать OpenCV
    'use_yolo': False,           # YOLO для детекции (требует обучения)
    'use_easyocr': True,         # OCR для подписей
    'min_symbol_size': 20,       # Мин. размер символа (пиксели)
    'device_symbols': {          # Шаблоны символов
        'smoke_detector': 'circle',
        'manual_call_point': 'square',
        'sounder': 'triangle'
    }
})

cv_plan.initialize()

# Анализ плана этажа
result = cv_plan.execute({'image_path': '/path/to/floor_plan.png'})

# Обнаруженные устройства
detected = result.data['detected_devices']
for device in detected:
    print(f"ID: {device.id}, Тип: {device.type}, "
          f"Координаты: ({device.x}, {device.y}), "
          f"Помещение: {device.room_number}")
```

**Выходные данные:**
```json
[
  {
    "id": "ДИП-001",
    "type": "SMOKE_DETECTOR",
    "x": 150,
    "y": 230,
    "room_number": "101",
    "confidence": 0.85
  },
  {
    "id": "ИПР-001",
    "type": "MANUAL_CALL_POINT",
    "x": 320,
    "y": 180,
    "room_number": "коридор",
    "confidence": 0.78
  }
]
```

#### Instrument: CVSchematicAnalyzer

**Назначение:** Анализ электрических схем, построение графа соединений.

```python
from orchestrator import CVSchematicAnalyzer

cv_schema = CVSchematicAnalyzer(config={
    'use_hough_transform': True,  # Детекция линий
    'min_line_length': 50,        # Мин. длина линии
    'detect_nodes': True,         # Детекция узлов соединения
    'build_graph': True           # Построение графа
})

cv_schema.initialize()

# Анализ схемы
result = cv_schema.execute({'image_path': '/path/to/schematic.png'})

# Граф соединений
graph = result.data['connection_graph']
print(f"Узлов: {graph.num_nodes}")
print(f"Соединений: {graph.num_edges}")

# Вывод соединений
for conn in graph.connections:
    print(f"{conn.from_device} --[{conn.wire_type}]--> {conn.to_device}")
```

**Выходные данные:**
```json
{
  "num_nodes": 25,
  "num_edges": 32,
  "connections": [
    {
      "from_device": "С2000М:К1",
      "to_device": "ДИП-001",
      "wire_type": "RS485",
      "channel": 1
    },
    {
      "from_device": "С2000М:К1",
      "to_device": "ДИП-002",
      "wire_type": "RS485",
      "channel": 1
    }
  ]
}
```

---

### 🔹 Этап 3: Создание Обучающего Набора Данных

> ⚠️ **Требуется интеграция с платформами разметки**

#### Рекомендуемые платформы:
- **Label Studio** - универсальная платформа для разметки
- **Roboflow** - специализированная для CV
- **Scale AI** - профессиональная разметка

#### Пример интеграции с Label Studio:

```python
# label_studio_integration.py
from label_studio_sdk.client import Client

client = Client(url='http://localhost:8080', api_key='YOUR_API_KEY')

# Создание проекта для разметки планов
project = client.start_project(
    title='APS Floor Plans',
    label_config='''
    <View>
        <Image name="image" value="$image"/>
        <RectangleLabels name="label" toName="image">
            <Label value="smoke_detector" background="green"/>
            <Label value="manual_call_point" background="red"/>
            <Label value="sounder" background="blue"/>
        </RectangleLabels>
    </View>
    '''
)

# Импорт данных для разметки
project.import_tasks([
    {'image': '/path/to/plan1.png'},
    {'image': '/path/to/plan2.png'}
])
```

---

### 🔹 Этап 4: Обучение и Интеграция Основных ИИ-моделей

#### Instrument: DataSynthesizer

**Назначение:** Синтез данных из всех источников, валидация, построение доменной модели.

```python
from orchestrator import DataSynthesizer

synthesizer = DataSynthesizer(config={
    'match_threshold': 0.8,       # Порог сопоставления устройств
    'validate_addresses': True,   # Проверка адресов
    'check_consistency': True,    # Проверка консистентности
    'resolve_conflicts': 'priority'  # Стратегия разрешения конфликтов
})

synthesizer.initialize()

# Входные данные от всех инструментов
input_data = {
    'nlp_devices': [...],         # Из NLPSpecExtractor
    'cv_plan_devices': [...],     # Из CVPlanAnalyzer
    'cv_schema_graph': {...},     # Из CVSchematicAnalyzer
    'document_report': {...}      # Из DocumentAnalyzer
}

result = synthesizer.execute(input_data)

# Доменная модель проекта
domain_model = result.data['domain_model']
print(f"Проект: {domain_model.project_name}")
print(f"Устройств: {len(domain_model.devices)}")
print(f"Соединений: {len(domain_model.connections)}")
print(f"Проблем: {len(domain_model.validation_issues)}")
```

**Выходные данные (ProjectDomainModel):**
```json
{
  "project_name": "АУПС Щеткина 4",
  "devices": [
    {
      "device_type": "CONTROL_PANEL",
      "model": "С2000М",
      "address": 1,
      "location": "щитовая",
      "source": "nlp+cv_plan",
      "confidence": "HIGH"
    }
  ],
  "connections": [...],
  "partitions": [
    {
      "name": "Раздел 1",
      "devices": ["ДИП-001", "ДИП-002", "ИПР-001"]
    }
  ],
  "validation_issues": [
    "Устройство ДИП-010 не найдено на плане",
    "Адрес 25 повторяется для двух устройств"
  ],
  "warnings": [
    "3 устройства имеют низкую уверенность распознавания"
  ]
}
```

---

### 🔹 Этап 5: Разработка Движка Генерации и Валидации

#### Instrument: ConfigGenerator

**Назначение:** Генерация конфигурации PProg из доменной модели.

```python
from orchestrator import ConfigGenerator

generator = ConfigGenerator(config={
    'format_version': '2.0',      # Версия формата PProg
    'include_checksums': True,    # Включить контрольные суммы
    'validate_output': True,      # Валидировать результат
    'template_path': '/path/to/templates/'  # Путь к шаблонам
})

generator.initialize()

# Генерация конфигурации
result = generator.execute({
    'domain_model': domain_model
})

# Сохранение файла
with open('/output/project.pprog', 'w') as f:
    f.write(result.data['config_text'])

print(f"Конфигурация сгенерирована: {result.data['output_path']}")
print(f"Размер: {result.data['file_size']} байт")
```

**Пример выходного файла (.pprog):**
```
; Конфигурация прибора С2000М
; Проект: АУПС Щеткина 4
; Дата генерации: 2025-01-15

[DEVICE]
Type=ControlPanel
Model=S2000M
Address=1

[PARTITION_1]
Name=Раздел 1
Devices=DIP-001,DIP-002,DIP-003,IPR-001

[CONNECTIONS]
DIP-001 -> S2000M:K1 (RS485)
DIP-002 -> S2000M:K1 (RS485)
IPR-001 -> S2000M:K2 (RS485)

[CHECKSUM]
Value=0xA7F3
```

#### Instrument: ReportGenerator

**Назначение:** Генерация подробных отчётов о проекте.

```python
from orchestrator import ReportGenerator

reporter = ReportGenerator(config={
    'format': 'html',             # Формат отчёта (html, txt, md)
    'include_stats': True,        # Включить статистику
    'include_warnings': True,     # Включить предупреждения
    'include_recommendations': True,  # Включить рекомендации
    'language': 'ru'              # Язык отчёта
})

reporter.initialize()

# Генерация отчёта
result = reporter.execute({
    'domain_model': domain_model,
    'config': config_text,
    'validation_result': validation_result
})

# Сохранение отчёта
with open('/output/report.html', 'w', encoding='utf-8') as f:
    f.write(result.data['report_html'])

print(f"Отчёт сгенерирован: {result.data['report_path']}")
```

**Структура отчёта:**
```html
<h1>Отчёт по проекту: АУПС Щеткина 4</h1>

<h2>📊 Статистика</h2>
<ul>
  <li>Всего устройств: 47</li>
  <li>Приборов С2000М: 2</li>
  <li>Дымовых извещателей: 35</li>
  <li>Ручных извещателей: 8</li>
  <li>Разделов: 4</li>
</ul>

<h2>⚠️ Проблемы и предупреждения</h2>
<ol>
  <li>Устройство ДИП-010 не найдено на плане</li>
  <li>Адрес 25 повторяется для двух устройств</li>
</ol>

<h2>💡 Рекомендации</h2>
<ul>
  <li>Проверить расположение ДИП-010 на плане</li>
  <li>Исправить конфликт адресов 25</li>
</ul>
```

---

## 🚀 Примеры использования

### Пример 1: Полный конвейер обработки проекта

```python
from orchestrator import WorkflowManager
from orchestrator.tools import (
    DocumentAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator
)

# 1. Создание оркестратора
orchestrator = WorkflowManager(config={
    'max_retries': 3,
    'stop_on_error': False,
    'verbose': True
})

# 2. Регистрация инструментов
tools = [
    DocumentAnalyzer(),
    NLPSpecExtractor(),
    CVPlanAnalyzer(),
    CVSchematicAnalyzer(),
    DataSynthesizer(),
    ConfigGenerator(),
    ReportGenerator()
]

for tool in tools:
    orchestrator.register_tool(tool)

# 3. Выполнение полного конвейера
result = orchestrator.execute_workflow(
    input_data='/path/to/project_folder/',
    steps=[
        {'tool': 'DocumentAnalyzer', 'name': 'analyze_docs'},
        {'tool': 'NLPSpecExtractor', 'name': 'extract_specs'},
        {'tool': 'CVPlanAnalyzer', 'name': 'analyze_plans'},
        {'tool': 'CVSchematicAnalyzer', 'name': 'analyze_schemas'},
        {'tool': 'DataSynthesizer', 'name': 'synthesize'},
        {'tool': 'ConfigGenerator', 'name': 'generate_config'},
        {'tool': 'ReportGenerator', 'name': 'generate_report'}
    ]
)

# 4. Проверка результата
if result.status.value == 'completed':
    print("✅ Конвейер выполнен успешно!")
    print(f"📄 Конфигурация: {result.data.get('config_path')}")
    print(f"📊 Отчёт: {result.data.get('report_path')}")
else:
    print(f"❌ Ошибка: {result.error_message}")
```

### Пример 2: Обработка только спецификаций

```python
from orchestrator import WorkflowManager, NLPSpecExtractor

orchestrator = WorkflowManager()
orchestrator.register_tool(NLPSpecExtractor())

result = orchestrator.execute_workflow(
    input_data={'text': open('specification.txt').read()},
    steps=[{'tool': 'NLPSpecExtractor', 'name': 'extract'}]
)

devices = result.data['devices']
print(f"Найдено устройств: {len(devices)}")
```

### Пример 3: Параллельная обработка нескольких источников

```python
from concurrent.futures import ThreadPoolExecutor
from orchestrator import DocumentAnalyzer, NLPSpecExtractor, CVPlanAnalyzer

# Создание инструментов
doc_analyzer = DocumentAnalyzer()
nlp_extractor = NLPSpecExtractor()
cv_plan = CVPlanAnalyzer()

# Параллельный запуск
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(doc_analyzer.execute, {'path': '/docs/'}),
        executor.submit(nlp_extractor.execute, {'text': spec_text}),
        executor.submit(cv_plan.execute, {'image_path': '/plans/plan1.png'})
    ]
    
    results = [f.result() for f in futures]

# Синтез результатов
from orchestrator import DataSynthesizer
synthesizer = DataSynthesizer()
final_result = synthesizer.execute({
    'doc_report': results[0].data,
    'nlp_devices': results[1].data,
    'cv_devices': results[2].data
})
```

---

## ⚙️ Настройка и конфигурация

### Конфигурационный файл (config.yaml)

```yaml
orchestrator:
  max_retries: 3
  stop_on_error: false
  verbose: true
  timeout_per_step: 300

tools:
  document_analyzer:
    use_ocr: true
    ocr_languages: 'rus+eng'
    keywords:
      - С2000
      - Болид
      - ДИП
      - ИПР
      - АПС
  
  nlp_extractor:
    use_spacy: true
    use_regex: true
    confidence_threshold: 0.7
  
  cv_plan_analyzer:
    use_opencv: true
    use_yolo: false
    min_symbol_size: 20
  
  data_synthesizer:
    match_threshold: 0.8
    validate_addresses: true
    resolve_conflicts: 'priority'
  
  config_generator:
    format_version: '2.0'
    include_checksums: true
    validate_output: true

llm:
  provider: 'openai'  # или 'claude', 'local'
  model: 'gpt-4'
  api_key: '${OPENAI_API_KEY}'
  enabled: false
```

### Загрузка конфигурации

```python
import yaml
from orchestrator import WorkflowManager

with open('config.yaml') as f:
    config = yaml.safe_load(f)

orchestrator = WorkflowManager(config=config['orchestrator'])

# Настройка инструментов
doc_analyzer = DocumentAnalyzer(config=config['tools']['document_analyzer'])
orchestrator.register_tool(doc_analyzer)
```

---

## 🔌 Интеграция с внешними сервисами

### Интеграция с LLM (GPT-4, Claude)

```python
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

# Настройка LLM
llm = ChatOpenAI(
    model='gpt-4',
    temperature=0.1,
    api_key='your-api-key'
)

# Промпт для анализа спецификаций
prompt = PromptTemplate(
    input_variables=['spec_text'],
    template="""
    Проанализируй следующую спецификацию оборудования АПС:
    {spec_text}
    
    Извлеки все устройства в формате JSON:
    - device_type (CONTROL_PANEL, SMOKE_DETECTOR, MANUAL_CALL_POINT)
    - model
    - quantity
    - location
    
    Верни только JSON без дополнительного текста.
    """
)

# Использование
chain = prompt | llm
response = chain.invoke({'spec_text': spec_text})
devices = json.loads(response.content)
```

### Интеграция с Label Studio

```python
from label_studio_sdk.client import Client

client = Client(url='http://localhost:8080', api_key='YOUR_KEY')

# Экспорт размеченных данных
project = client.get_project(id=1)
annotations = project.get_annotations()

# Преобразование в формат для обучения
training_data = []
for ann in annotations:
    training_data.append({
        'image': ann.task['data']['image'],
        'labels': ann.result
    })

# Сохранение датасета
import json
with open('training_dataset.json', 'w') as f:
    json.dump(training_data, f)
```

---

## ❓ Частые вопросы и решение проблем

### Q: OCR не распознаёт текст на сканах?

**A:** Попробуйте следующие решения:
1. Увеличьте разрешение скана (минимум 300 DPI)
2. Используйте предобработку изображений:
```python
import cv2
img = cv2.imread('scan.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
enhanced = cv2.equalizeHist(gray)
cv2.imwrite('enhanced.png', enhanced)
```
3. Настройте языки OCR: `ocr_languages='rus+eng'`

### Q: NLP извлекает неверные типы устройств?

**A:** 
1. Добавьте собственные паттерны:
```python
nlp_extractor = NLPSpecExtractor(config={
    'device_patterns': {
        'my_device': r'МойПрибор[-\s]?\d+'
    }
})
```
2. Используйте few-shot обучение с примерами
3. Интегрируйте LLM для сложных случаев

### Q: CV не находит устройства на планах?

**A:**
1. Проверьте контрастность изображения
2. Настройте минимальный размер символов: `min_symbol_size=15`
3. Обучите YOLO модель на ваших символах АПС

### Q: Конфликты адресов при синтезе?

**A:** DataSynthesizer автоматически разрешает конфликты:
```python
synthesizer = DataSynthesizer(config={
    'resolve_conflicts': 'priority',  # priority, manual, merge
    'validate_addresses': True
})
```

### Q: Как добавить собственный инструмент?

**A:** Наследуйтесь от базового класса `AITool`:
```python
from orchestrator.tools.base_tool import AITool

class MyCustomTool(AITool):
    def __init__(self, config=None):
        super().__init__('MyCustomTool', config)
    
    def initialize(self):
        # Инициализация
        pass
    
    def execute(self, input_data):
        # Логика выполнения
        return self.create_result(data={'result': 'success'})

# Регистрация
orchestrator.register_tool(MyCustomTool())
```

---

## 📞 Поддержка

- 📧 Email: support@example.com
- 📚 Документация: `/workspace/orchestrator/README.md`
- 🧪 Тесты: `python -m unittest tests.test_orchestrator`
- 💻 Demo: `python demo.py`

---

## 📝 Лицензия

[Укажите лицензию вашего проекта]
