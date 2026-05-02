# Инструкция по сбору данных для АПС AI

## Быстрый старт

### 1. Установка зависимостей

```bash
# Для конвертации PDF
sudo apt-get install poppler-utils  # Ubuntu/Debian
# или
brew install poppler  # macOS

# Python зависимости
pip install Pillow opencv-python
```

### 2. Сбор .pprog файлов

Поместите файлы `.pprog` в директорию `data/raw/pprog/` и запустите парсер:

```bash
python scripts/parse_pprog.py data/raw/pprog/ -o data/processed/parsed_pprog/
```

Результат будет сохранён в JSON формате.

### 3. Конвертация планов из PDF

Поместите PDF файлы планов в `data/raw/plans_pdf/`:

```bash
python scripts/convert_plans.py data/raw/plans_pdf/ -o data/processed/plans --dpi 300 --normalize
```

### 4. Разметка изображений

#### Вариант A: LabelImg (рекомендуется для начала)

```bash
pip install labelImg
labelImg data/processed/plans/
```

**Классы для разметки:**
- `sensor` - датчики/извещатели
- `device` - приборы (ППКОП, реле, модули)
- `loop` - шлейфы сигнализации
- `zone` - зоны защиты
- `cable` - кабельные трассы

#### Вариант B: CVAT (для командной работы)

1. Установите Docker
2. Запустите CVAT:
```bash
docker run -p 8080:80 cvat/cvat
```
3. Откройте http://localhost:8080
4. Создайте проект и загрузите изображения

### 5. Структура данных после сбора

```
data/
├── raw/
│   ├── projects/           # Исходные проекты
│   ├── pprog/              # .pprog файлы
│   └── plans_pdf/          # PDF планы
├── processed/
│   ├── parsed_pprog/       # Распарсенные .pprog (JSON)
│   └── plans/              # Конвертированные PNG
└── annotated/
    ├── yolo_labels/        # Разметка для YOLO (.txt)
    └── ner_texts/          # Тексты для NER модели
```

## Контрольный список

- [ ] Собрать минимум 10 проектов для начала
- [ ] Получить 10+ файлов .pprog
- [ ] Конвертировать 50+ изображений планов
- [ ] Разметить 100+ изображений (начальная выборка)
- [ ] Проверить качество разметки

## Форматы данных

### .pprog (пример структуры после парсинга)

```json
{
  "file_name": "project_001.pprog",
  "metadata": {
    "project_name": "ЖК Солнечный",
    "object_name": "Корпус 1",
    "date": "15.03.2024"
  },
  "specifications": [
    {
      "code": "ИП212-63",
      "description": "Извещатель пожарный дымовой",
      "quantity": 150
    }
  ],
  "devices": [...],
  "loops": [...],
  "zones": [...]
}
```

### YOLO разметка (example.txt)

```
0 0.45 0.62 0.03 0.04
1 0.78 0.34 0.05 0.06
...
```

Где: `<class> <x_center> <y_center> <width> <height>`

## Контакты для вопросов

По вопросам формата данных и уточнению требований обращайтесь к ведущему инженеру проекта.

---

*Документ создан автоматически. Последнее обновление: 2024*
