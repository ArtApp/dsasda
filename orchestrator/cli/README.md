# CLI для AI Orchestrator Project-to-PProg

## Установка

Система не требует дополнительной установки. Запуск через Python:

```bash
python -m orchestrator.cli.main --help
```

## Команды

### 1. Полный конвейер обработки

Запускает все этапы: анализ документов → NLP/CV извлечение → синтез → генерация конфигурации и отчета.

```bash
python -m orchestrator.cli.main run \
    --input ./data_synthetic \
    --output ./output
```

**Результат в `./output/`:**
- `document_analysis_report.txt` - отчет по анализу документов
- `specifications.json` - извлеченные устройства из спецификаций
- `plans_detection.json` - устройства, обнаруженные на планах
- `schematic_graph.json` - граф соединений из схем
- `domain_model.json` - единая доменная модель проекта
- `config.pprog` - готовая конфигурация для загрузки
- `project_report.txt` - текстовый отчет
- `project_report.html` - HTML отчет с визуализацией

### 2. Анализ документов

Только анализ входных файлов без полной обработки:

```bash
python -m orchestrator.cli.main analyze \
    --input ./data_synthetic/specification.pdf
```

**Вывод:**
- Типы файлов
- Объем текста
- Количество изображений
- Найденные ключевые слова АПС

### 3. Генерация конфигурации

Генерация `.pprog` из готовой доменной модели:

```bash
python -m orchestrator.cli.main generate \
    --model ./output/domain_model.json \
    --output ./output/config.pprog
```

## Примеры использования

### Сценарий 1: Обработка нового проекта

```bash
# Создаем директорию с документами проекта
mkdir -p projects/project_001/docs
cp /path/to/specs.pdf projects/project_001/docs/
cp /path/to/plans/*.png projects/project_001/docs/
cp /path/to/schematics/*.dwg projects/project_001/docs/

# Запускаем полный конвейер
python -m orchestrator.cli.main run \
    --input projects/project_001/docs \
    --output projects/project_001/output

# Проверяем результаты
ls -la projects/project_001/output/
cat projects/project_001/output/project_report.txt
```

### Сценарий 2: Поэтапная обработка с проверкой

```bash
# Шаг 1: Анализ документов
python -m orchestrator.cli.main analyze \
    --input projects/project_001/docs \
    > analysis_summary.txt

# Просматриваем summary, проверяем ключевые слова
cat analysis_summary.txt

# Шаг 2: Если все ок, запускаем полный конвейер
python -m orchestrator.cli.main run \
    --input projects/project_001/docs \
    --output projects/project_001/output
```

### Сценарий 3: Повторная генерация после правки модели

```bash
# Инженер вручную исправил domain_model.json
nano projects/project_001/output/domain_model.json

# Перегенерировали конфигурацию
python -m orchestrator.cli.main generate \
    --model projects/project_001/output/domain_model_edited.json \
    --output projects/project_001/output/config_v2.pprog
```

## Логирование

При каждом запуске создается лог-файл:
```
orchestrator_YYYYMMDD_HHMMSS.log
```

Лог содержит:
- Детали выполнения каждого этапа
- Ошибки и предупреждения
- Статистику обработки
- Рекомендации по улучшению

## Требования

- Python 3.8+
- Установленные зависимости (см. `requirements.txt`):
  - pymupdf (fitz)
  - opencv-python
  - easyocr
  - spacy (опционально)
  - jinja2

## Интеграция в CI/CD

Пример GitHub Actions workflow:

```yaml
name: Process APS Project

on:
  push:
    paths:
      - 'projects/**/docs/**'

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run orchestrator
        run: |
          python -m orchestrator.cli.main run \
            --input projects/${{ github.event.repository.name }}/docs \
            --output projects/${{ github.event.repository.name }}/output
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: pprog-config
          path: projects/*/output/*.pprog
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `ORCHESTRATOR_LOG_LEVEL` | Уровень логирования | `INFO` |
| `ORCHESTRATOR_OUTPUT_DIR` | Директория по умолчанию для output | `./output` |
| `ORCHESTRATOR_CACHE_DIR` | Директория для кэша | `./cache` |

## Поддержка

При возникновении проблем:
1. Проверьте лог-файл `orchestrator_*.log`
2. Убедитесь, что входные файлы доступны и читаемы
3. Проверьте наличие всех зависимостей
4. Откройте issue с прикрепленным логом
