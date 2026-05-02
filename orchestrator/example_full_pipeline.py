#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример полного конвейера обработки проекта АПС
================================================

Этот скрипт демонстрирует полный цикл работы AI Orchestrator:
1. Анализ проектной документации (PDF, изображения)
2. Извлечение устройств из спецификаций (NLP)
3. Анализ планов этажей (CV)
4. Синтез данных из всех источников
5. Генерация конфигурации PProg
6. Создание отчёта

Использование:
    python example_full_pipeline.py /path/to/project/

"""

import sys
import json
from pathlib import Path
from datetime import datetime

from orchestrator import (
    WorkflowManager,
    DocumentAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator,
    ProjectDomainModel
)


def create_sample_specification():
    """Создаёт пример текста спецификации для демонстрации."""
    return """
СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ АПС
Объект: Щеткина 4, мазутонасосная

Раздел 1. Приёмно-контрольные приборы
─────────────────────────────────────
1. С2000М - Прибор приёмно-контрольный охранно-пожарный - 2 шт.
   Место установки: щитовая, помещение 101

2. С2000-БИ - Блок индикации - 3 шт.
   Место установки: пост охраны, коридор 1 этаж

Раздел 2. Извещатели пожарные дымовые
──────────────────────────────────────
3. ДИП-34А - Извещатель дымовой адресный - 25 шт.
   Место установки: помещения 1-10, коридоры

4. ДИП-34А-02 - Извещатель дымовой адресный (взрывозащищённый) - 8 шт.
   Место установки: мазутонасосная, помещение 101

Раздел 3. Извещатели пожарные ручные
─────────────────────────────────────
5. ИПР-513-3А - Извещатель ручной адресный - 6 шт.
   Место установки: выходы с этажей, коридоры

Раздел 4. Оповещатели
─────────────────────
6. С2000-СП1 - Оповещатель световой адресный - 10 шт.
   Место установки: коридоры, выходы

7. С2000-Стрелец-М - Оповещатель речевой - 4 шт.
   Место установки: основные выходы

Раздел 5. Исполнительные устройства
───────────────────────────────────
8. С2000-КДЛ - Контроллер двухпроводной линии связи - 2 шт.
   Место установки: щитовая

9. С2000-СП2 - Релейный блок - 5 шт.
   Место установки: щитовая, управление вентиляцией

Раздел 6. Дополнительное оборудование
─────────────────────────────────────
10. БП-12В - Блок питания 12В 3А - 4 шт.
    Место установки: щитовая

11. АКБ 12В 7Ач - Аккумуляторная батарея - 8 шт.
    Место установки: щитовая
"""


def create_sample_plan_devices():
    """Создаёт пример данных с плана этажа для демонстрации."""
    return [
        {"id": "ДИП-001", "type": "SMOKE_DETECTOR", "model": "ДИП-34А", "x": 150, "y": 230, "room": "101"},
        {"id": "ДИП-002", "type": "SMOKE_DETECTOR", "model": "ДИП-34А", "x": 280, "y": 230, "room": "101"},
        {"id": "ДИП-003", "type": "SMOKE_DETECTOR", "model": "ДИП-34А", "x": 410, "y": 230, "room": "102"},
        {"id": "ДИП-004", "type": "SMOKE_DETECTOR", "model": "ДИП-34А-02", "x": 120, "y": 350, "room": "101-мазут"},
        {"id": "ДИП-005", "type": "SMOKE_DETECTOR", "model": "ДИП-34А-02", "x": 220, "y": 350, "room": "101-мазут"},
        {"id": "ИПР-001", "type": "MANUAL_CALL_POINT", "model": "ИПР-513-3А", "x": 50, "y": 180, "room": "коридор"},
        {"id": "ИПР-002", "type": "MANUAL_CALL_POINT", "model": "ИПР-513-3А", "x": 500, "y": 180, "room": "коридор"},
        {"id": "СП1-001", "type": "SOUNDER", "model": "С2000-СП1", "x": 300, "y": 100, "room": "коридор"},
        {"id": "СП1-002", "type": "SOUNDER", "model": "С2000-СП1", "x": 300, "y": 400, "room": "коридор"},
        {"id": "ПК-001", "type": "CONTROL_PANEL", "model": "С2000М", "x": 25, "y": 25, "room": "101-щитовая"},
        {"id": "ПК-002", "type": "CONTROL_PANEL", "model": "С2000М", "x": 75, "y": 25, "room": "101-щитовая"},
    ]


def run_full_pipeline(project_path=None):
    """
    Запускает полный конвейер обработки проекта АПС.
    
    Args:
        project_path: Путь к директории с проектной документацией
    """
    
    print("=" * 80)
    print("🔥 AI ORCHESTRATOR: Полный конвейер обработки проекта АПС")
    print("=" * 80)
    print(f"📅 Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if project_path:
        print(f"📁 Путь к проекту: {project_path}")
    print()
    
    # =========================================================================
    # ШАГ 0: Инициализация оркестратора
    # =========================================================================
    print("⚙️  ШАГ 0: Инициализация оркестратора")
    print("-" * 80)
    
    orchestrator = WorkflowManager(config={
        'max_retries': 3,
        'stop_on_error': False,
        'verbose': True,
        'timeout_per_step': 300
    })
    
    # Регистрация инструментов
    tools = [
        DocumentAnalyzer(config={
            'use_ocr': True,
            'ocr_languages': 'rus+eng',
            'keywords': ['С2000', 'Болид', 'ДИП', 'ИПР', 'АПС', 'пожарная']
        }),
        NLPSpecExtractor(config={
            'use_spacy': False,  # Отключено для демо
            'use_regex': True,
            'confidence_threshold': 0.7
        }),
        CVPlanAnalyzer(config={
            'use_opencv': False,  # Отключено для демо
            'min_symbol_size': 20
        }),
        CVSchematicAnalyzer(config={
            'use_hough_transform': False,  # Отключено для демо
            'build_graph': True
        }),
        DataSynthesizer(config={
            'match_threshold': 0.8,
            'validate_addresses': True,
            'resolve_conflicts': 'priority'
        }),
        ConfigGenerator(config={
            'format_version': '2.0',
            'include_checksums': True,
            'validate_output': True
        }),
        ReportGenerator(config={
            'format': 'html',
            'include_stats': True,
            'include_warnings': True,
            'include_recommendations': True,
            'language': 'ru'
        })
    ]
    
    for tool in tools:
        orchestrator.register_tool(tool)
        print(f"   ✅ Зарегистрирован инструмент: {tool.name}")
    
    print()
    
    # =========================================================================
    # ШАГ 1: Анализ документации
    # =========================================================================
    print("📄 ШАГ 1: Анализ проектной документации")
    print("-" * 80)
    
    doc_analyzer = orchestrator.tools['DocumentAnalyzer']
    
    # Для демо используем тестовые данные
    if project_path and Path(project_path).exists():
        doc_result = doc_analyzer.execute({'path': project_path})
    else:
        # Имитация результата анализа
        doc_result = doc_analyzer.create_result(data={
            'report': type('obj', (object,), {
                'file_types': ['PDF', 'PNG'],
                'text_length': 54212,
                'images_count': 18,
                'detected_keywords': ['С2000М', 'ДИП-34А', 'ИПР-513-3А', 'АПС'],
                'summary': 'Проект АУПС, Щеткина 4, мазутонасосная',
                'extracted_text': create_sample_specification()
            })()
        })
    
    report = doc_result.data['report']
    print(f"   📊 Типов файлов обнаружено: {len(report.file_types)}")
    print(f"   📝 Объём текста: {report.text_length:,} символов")
    print(f"   🖼️  Изображений найдено: {report.images_count}")
    print(f"   🔑 Ключевые слова: {', '.join(report.detected_keywords[:5])}")
    print(f"   📋 Краткое описание: {report.summary}")
    print()
    
    # =========================================================================
    # ШАГ 2: NLP анализ спецификаций
    # =========================================================================
    print("🧠 ШАГ 2: NLP анализ спецификаций")
    print("-" * 80)
    
    nlp_extractor = orchestrator.tools['NLPSpecExtractor']
    
    spec_text = report.extracted_text
    nlp_result = nlp_extractor.execute({'text': spec_text})
    
    devices_from_spec = nlp_result.data.get('devices', [])
    print(f"   🎯 Устройств извлечено: {len(devices_from_spec)}")
    
    # Группировка по типам
    by_type = {}
    for device in devices_from_spec:
        # Обработка device как dict или как объекта
        if isinstance(device, dict):
            dtype = device.get('device_type', 'unknown')
            quantity = device.get('quantity', 1)
        else:
            dtype = device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type)
            quantity = device.quantity
        by_type[dtype] = by_type.get(dtype, 0) + quantity
    
    for dtype, count in by_type.items():
        print(f"      • {dtype}: {count} шт.")
    print()
    
    # =========================================================================
    # ШАГ 3: CV анализ планов
    # =========================================================================
    print("👁️  ШАГ 3: CV анализ планов этажей")
    print("-" * 80)
    
    cv_plan = orchestrator.tools['CVPlanAnalyzer']
    
    # Для демо используем тестовые данные
    plan_devices_data = create_sample_plan_devices()
    cv_result = cv_plan.create_result(data={
        'detected_devices': [
            type('obj', (object,), d) for d in plan_devices_data
        ]
    })
    
    detected_devices = cv_result.data.get('detected_devices', [])
    print(f"   🎯 Устройств обнаружено на плане: {len(detected_devices)}")
    
    # Подсчёт по типам
    cv_by_type = {}
    for device in detected_devices:
        dtype = device.type
        cv_by_type[dtype] = cv_by_type.get(dtype, 0) + 1
    
    for dtype, count in cv_by_type.items():
        print(f"      • {dtype}: {count} шт.")
    print()
    
    # =========================================================================
    # ШАГ 4: Синтез данных
    # =========================================================================
    print("🔗 ШАГ 4: Синтез данных из всех источников")
    print("-" * 80)
    
    synthesizer = orchestrator.tools['DataSynthesizer']
    
    # Подготовка входных данных
    input_data = {
        'nlp_devices': devices_from_spec,
        'cv_plan_devices': detected_devices,
        'document_report': report
    }
    
    synth_result = synthesizer.execute(input_data)
    domain_model = synth_result.data.get('domain_model')
    
    if domain_model:
        # Обработка domain_model как dict или как объекта
        if isinstance(domain_model, dict):
            project_name = domain_model.get('project_name', 'Неизвестный проект')
            num_devices = len(domain_model.get('devices', []))
            num_connections = len(domain_model.get('connections', []))
            num_partitions = len(domain_model.get('partitions', []))
            validation_issues = domain_model.get('validation_issues', [])
            warnings = domain_model.get('warnings', [])
        else:
            project_name = domain_model.project_name
            num_devices = len(domain_model.devices)
            num_connections = len(domain_model.connections)
            num_partitions = len(domain_model.partitions)
            validation_issues = domain_model.validation_issues
            warnings = domain_model.warnings
        
        print(f"   🏷️  Название проекта: {project_name}")
        print(f"   📦 Всего устройств в модели: {num_devices}")
        print(f"   🔗 Соединений: {num_connections}")
        print(f"   📑 Разделов: {num_partitions}")
        print(f"   ⚠️  Проблем валидации: {len(validation_issues)}")
        print(f"   ⚡ Предупреждений: {len(warnings)}")
        
        if validation_issues:
            print("\n   Проблемы:")
            for issue in validation_issues[:3]:
                print(f"      ❌ {issue}")
    else:
        print("   ⚠️  Не удалось создать доменную модель")
        domain_model = {
            'project_name': "АУПС Щеткина 4",
            'devices': [],
            'connections': [],
            'partitions': [],
            'validation_issues': ["Демо режим: нет реальных данных"],
            'warnings': []
        }
    
    print()
    
    # =========================================================================
    # ШАГ 5: Генерация конфигурации
    # =========================================================================
    print("⚙️  ШАГ 5: Генерация конфигурации PProg")
    print("-" * 80)
    
    config_generator = orchestrator.tools['ConfigGenerator']
    
    config_result = config_generator.execute({
        'domain_model': domain_model
    })
    
    config_text = config_result.data.get('config_text', '')
    output_path = config_result.data.get('output_path', 'output/project.pprog')
    
    print(f"   📄 Конфигурация сгенерирована")
    print(f"   💾 Путь сохранения: {output_path}")
    print(f"   📏 Размер: {len(config_text)} байт")
    
    # Показываем первые строки конфигурации
    if config_text:
        preview_lines = config_text.split('\n')[:10]
        print("\n   Фрагмент конфигурации:")
        for line in preview_lines:
            print(f"      {line}")
        if len(config_text.split('\n')) > 10:
            print("      ...")
    print()
    
    # =========================================================================
    # ШАГ 6: Генерация отчёта
    # =========================================================================
    print("📊 ШАГ 6: Генерация отчёта")
    print("-" * 80)
    
    report_generator = orchestrator.tools['ReportGenerator']
    
    report_result = report_generator.execute({
        'domain_model': domain_model,
        'config': config_text,
        'validation_result': {'status': 'success', 'issues': []}
    })
    
    report_html = report_result.data.get('report_html', '')
    report_path = report_result.data.get('report_path', 'output/report.html')
    
    print(f"   📄 Отчёт сгенерирован")
    print(f"   💾 Путь сохранения: {report_path}")
    print(f"   📏 Размер: {len(report_html)} байт")
    
    # Извлекаем статистику из отчёта
    if report_result.data.get('statistics'):
        stats = report_result.data['statistics']
        print(f"\n   📊 Статистика проекта:")
        print(f"      • Всего устройств: {stats.get('total_devices', 0)}")
        print(f"      • Приборов С2000М: {stats.get('control_panels', 0)}")
        print(f"      • Дымовых извещателей: {stats.get('smoke_detectors', 0)}")
        print(f"      • Ручных извещателей: {stats.get('manual_call_points', 0)}")
        print(f"      • Разделов: {stats.get('partitions', 0)}")
    print()
    
    # =========================================================================
    # ЗАВЕРШЕНИЕ
    # =========================================================================
    print("=" * 80)
    print("✅ КОНВЕЙЕР ЗАВЕРШЕН УСПЕШНО")
    print("=" * 80)
    print(f"\n📁 Выходные файлы:")
    print(f"   • Конфигурация: {output_path}")
    print(f"   • Отчёт: {report_path}")
    print(f"\n💡 Следующие шаги:")
    print(f"   1. Проверьте сгенерированный отчёт")
    print(f"   2. При необходимости внесите коррективы")
    print(f"   3. Загрузите .pprog файл в прибор С2000М через UProg")
    print()
    
    return {
        'status': 'completed',
        'domain_model': domain_model,
        'config_path': output_path,
        'report_path': report_path,
        'config_text': config_text,
        'report_html': report_html
    }


if __name__ == '__main__':
    # Путь к проекту из командной строки или None для демо режима
    project_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    result = run_full_pipeline(project_path)
    
    # Сохранение результатов в JSON для дальнейшего использования
    output_file = Path('output/pipeline_result.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'status': result['status'],
            'config_path': result['config_path'],
            'report_path': result['report_path'],
            'timestamp': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Результаты сохранены в: {output_file}")
