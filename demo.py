#!/usr/bin/env python3
"""
Демонстрационный скрипт AI Orchestrator для Project-to-PProg.
Показывает полный цикл обработки проектной документации АПС.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    WorkflowManager,
    DocumentAnalyzer,
    ConfigFormatAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator,
)
from orchestrator.models.domain import (
    Device, DeviceType, Connection, Partition, ProjectDomainModel, ConfidenceLevel
)


def create_sample_project():
    """Создать тестовый проект с документами."""
    test_dir = tempfile.mkdtemp(prefix="aps_project_")
    print(f"📁 Создан тестовый проект: {test_dir}")
    
    try:
        import fitz
        
        # 1. Создаем спецификацию оборудования
        spec_path = Path(test_dir) / "specification.pdf"
        doc = fitz.open()
        page = doc.new_page()
        
        spec_text = """
        СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ АПС
        Объект: Административное здание
        
        Приборы управления:
        1. С2000-М - 1 шт. - Прибор управления системой
        2. С2000-КДЛ - 2 шт. - Контроллер ДПЛС адресный
        
        Извещатели пожарные:
        3. ДИП-34А - 25 шт. - Дымовой оптико-электронный
        4. ИПР 513-3А - 8 шт. - Ручной извещатель
        
        Оповещатели:
        5. С2000-СП2 - 3 шт. - Релейный прибор
        6. Маяк-24 - 10 шт. - Световой оповещатель
        
        Разделы охраны:
        - Раздел 1: Этаж 1 (помещения 101-110)
        - Раздел 2: Этаж 2 (помещения 201-210)
        """
        page.insert_text((50, 50), spec_text, fontsize=10)
        doc.save(str(spec_path))
        doc.close()
        print(f"   ✓ Спецификация: {spec_path.name}")
        
        # 2. Создаем план этажа с устройствами
        plan_path = Path(test_dir) / "floor_plan.pdf"
        doc = fitz.open()
        page = doc.new_page()
        
        # Рисуем простой план
        page.draw_rect(fitz.Rect(50, 100, 550, 400), color=(0, 0, 0), width=2)
        page.insert_text((60, 120), "ПЛАН ЭТАЖА 1 - Система АПС", fontsize=12)
        page.insert_text((60, 150), "Помещение 101: ДИП-34А (адрес 1), ДИП-34А (адрес 2)", fontsize=9)
        page.insert_text((60, 170), "Помещение 102: ДИП-34А (адрес 3), ИПР (адрес 4)", fontsize=9)
        page.insert_text((60, 190), "Помещение 103: ДИП-34А (адрес 5), ДИП-34А (адрес 6)", fontsize=9)
        page.insert_text((60, 210), "Коридор: Маяк-24 (адрес 7), ИПР (адрес 8)", fontsize=9)
        
        # Схематично рисуем устройства
        for i, (x, y) in enumerate([(100, 250), (200, 250), (300, 250), (400, 250)], 1):
            page.draw_circle(fitz.Point(x, y), 10, color=(1, 0, 0), fill=(1, 0.8, 0.8))
            page.insert_text((x-15, y+25), f"D{i}", fontsize=8)
            
        doc.save(str(plan_path))
        doc.close()
        print(f"   ✓ План этажа: {plan_path.name}")
        
        # 3. Создаем схему подключения
        schematic_path = Path(test_dir) / "connection_schematic.pdf"
        doc = fitz.open()
        page = doc.new_page()
        
        page.insert_text((50, 50), "СХЕМА ПОДКЛЮЧЕНИЯ УСТРОЙСТВ АПС", fontsize=12)
        page.insert_text((50, 80), "С2000-КДЛ №1 (шлейф А):", fontsize=10)
        page.insert_text((70, 100), "→ ДИП-34А (адрес 1) → ДИП-34А (адрес 2) → ИПР (адрес 4)", fontsize=9)
        page.insert_text((70, 120), "→ ДИП-34А (адрес 3) → ДИП-34А (адрес 5) → ДИП-34А (адрес 6)", fontsize=9)
        page.insert_text((50, 150), "С2000-КДЛ №2 (шлейф B):", fontsize=10)
        page.insert_text((70, 170), "→ Маяк-24 (адрес 7) → С2000-СП2 (адрес 8)", fontsize=9)
        
        # Рисуем линии соединений
        page.draw_line(fitz.Point(70, 220), fitz.Point(500, 220), color=(0, 0, 1), width=1)
        page.draw_line(fitz.Point(70, 240), fitz.Point(500, 240), color=(0, 0, 1), width=1)
        
        doc.save(str(schematic_path))
        doc.close()
        print(f"   ✓ Схема подключения: {schematic_path.name}")
        
    except ImportError:
        print("   ⚠ PyMuPDF не установлен, создаем текстовые файлы")
        
        # Создаем текстовые версии
        with open(Path(test_dir) / "specification.txt", "w", encoding="utf-8") as f:
            f.write("""СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ АПС
Объект: Административное здание

Приборы управления:
1. С2000-М - 1 шт.
2. С2000-КДЛ - 2 шт.

Извещатели пожарные:
3. ДИП-34А - 25 шт.
4. ИПР 513-3А - 8 шт.

Оповещатели:
5. С2000-СП2 - 3 шт.
6. Маяк-24 - 10 шт.
""")
        
    return test_dir


def demo_basic_workflow():
    """Демонстрация базового workflow."""
    print("\n" + "="*70)
    print("🚀 ДЕМО: Базовый workflow обработки проекта АПС")
    print("="*70)
    
    # Создаем тестовый проект
    project_dir = create_sample_project()
    
    try:
        # Инициализируем оркестратор
        orchestrator = WorkflowManager(config={'verbose': True})
        
        # Регистрируем все инструменты
        print("\n📦 Регистрация инструментов...")
        tools = [
            DocumentAnalyzer(config={'use_ocr': False}),
            ConfigFormatAnalyzer(),
            NLPSpecExtractor(),
            CVPlanAnalyzer(),
            CVSchematicAnalyzer(),
            DataSynthesizer(),
            ConfigGenerator(),
            ReportGenerator(),
        ]
        
        for tool in tools:
            orchestrator.register_tool(tool)
            print(f"   ✓ {tool.name}")
        
        # Выполняем анализ документов
        print(f"\n🔍 Анализ документов в: {project_dir}")
        print("-" * 70)
        
        state = orchestrator.execute_workflow(
            input_data=project_dir,
            steps=[
                {'tool': 'DocumentAnalyzer', 'name': 'analyze_documents', 'on_error': 'continue'}
            ]
        )
        
        print(f"\n📊 Статус workflow: {state.status.value}")
        print(f"   Выполнено шагов: {len(state.completed_steps)}")
        print(f"   Предупреждений: {len(state.warnings)}")
        
        if state.errors:
            print(f"   Ошибок: {len(state.errors)}")
            for error in state.errors[:3]:
                print(f"      - {error[:100]}...")
        
        # Получаем результат анализа
        analysis_result = state.context.get('outputs', {}).get('analyze_documents', {})
        if analysis_result and 'report' in analysis_result:
            report = analysis_result['report']
            print(f"\n📄 Результаты анализа:")
            print(f"   Файлов: {report.total_files}")
            print(f"   Типы файлов: {report.file_types}")
            print(f"   Ключевые слова: {', '.join(report.keywords_found[:5])}")
        
    finally:
        # Очистка
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)
        print(f"\n🧹 Тестовый проект удален")


def demo_domain_model():
    """Демонстрация работы с доменной моделью."""
    print("\n" + "="*70)
    print("🏗️  ДЕМО: Доменная модель проекта")
    print("="*70)
    
    # Создаем доменную модель
    model = ProjectDomainModel(project_name="Административное здание")
    
    # Добавляем устройства
    devices = [
        Device(DeviceType.CONTROL_PANEL, "С2000-М", address=1, location="Щит управления"),
        Device(DeviceType.KDL, "С2000-КДЛ", address=2, location="Щит управления"),
        Device(DeviceType.KDL, "С2000-КДЛ", address=3, location="Щит управления"),
        Device(DeviceType.SMOKE_DETECTOR, "ДИП-34А", address=1, room_number="101"),
        Device(DeviceType.SMOKE_DETECTOR, "ДИП-34А", address=2, room_number="101"),
        Device(DeviceType.MANUAL_CALL_POINT, "ИПР 513-3А", address=3, room_number="102"),
        Device(DeviceType.LIGHT_ALARM, "Маяк-24", address=4, room_number="Коридор"),
    ]
    
    for device in devices:
        model.add_device(device)
    
    # Добавляем соединения
    connections = [
        Connection("device_1", "device_2", channel=1, line="A"),
        Connection("device_2", "device_3", channel=1, line="A"),
        Connection("device_3", "device_4", channel=1, line="A"),
    ]
    
    for conn in connections:
        model.add_connection(conn)
    
    # Добавляем разделы
    partitions = [
        Partition(1, "Раздел 1 - Этаж 1", zones=[1, 2, 3], location="Этаж 1"),
        Partition(2, "Раздел 2 - Этаж 2", zones=[4, 5], location="Этаж 2"),
    ]
    
    for partition in partitions:
        model.add_partition(partition)
    
    # Выводим статистику
    print(f"\n📊 Статистика проекта:")
    print(f"   Название: {model.project_name}")
    print(f"   Устройств: {model.total_devices}")
    print(f"   Разделов: {model.total_partitions}")
    print(f"   Зон: {model.total_zones}")
    print(f"   Соединений: {len(model.connections)}")
    
    # Преобразуем в JSON
    print(f"\n📋 Пример JSON представления:")
    data = model.to_dict()
    print(json.dumps({
        'project_name': data['project_name'],
        'statistics': data['statistics'],
        'devices_count': len(data['devices']),
    }, indent=2, ensure_ascii=False))


def demo_custom_pipeline():
    """Демонстрация пользовательского конвейера."""
    print("\n" + "="*70)
    print("⚙️  ДЕМО: Пользовательский конвейер обработки")
    print("="*70)
    
    orchestrator = WorkflowManager()
    
    # Регистрируем только необходимые инструменты
    orchestrator.register_tool(DocumentAnalyzer())
    orchestrator.register_tool(NLPSpecExtractor())
    orchestrator.register_tool(DataSynthesizer())
    
    # Создаем пользовательский конвейер
    custom_pipeline = orchestrator.create_custom_pipeline([
        {
            'tool': 'DocumentAnalyzer',
            'name': 'step1_analyze',
            'on_error': 'continue',
        },
        {
            'tool': 'NLPSpecExtractor',
            'name': 'step2_extract',
            'condition': lambda ctx: True,
        },
        {
            'tool': 'DataSynthesizer',
            'name': 'step3_synthesize',
        },
    ])
    
    print(f"\n📋 Конвейер из {len(custom_pipeline)} шагов:")
    for i, step in enumerate(custom_pipeline, 1):
        print(f"   {i}. {step['name']} ({step['tool']})")


def demo_api_usage():
    """Демонстрация программного API."""
    print("\n" + "="*70)
    print("🔌 ДЕМО: Программное API")
    print("="*70)
    
    # Быстрый старт
    from orchestrator import WorkflowManager, DocumentAnalyzer
    
    orchestrator = WorkflowManager()
    orchestrator.register_tool(DocumentAnalyzer())
    
    print("\n💡 Пример кода:")
    print("""
    from orchestrator import WorkflowManager, DocumentAnalyzer
    
    # Создание оркестратора
    orchestrator = WorkflowManager()
    
    # Регистрация инструментов
    orchestrator.register_tool(DocumentAnalyzer())
    
    # Выполнение workflow
    result = orchestrator.execute_workflow(
        input_data="/path/to/project",
        steps=[
            {'tool': 'DocumentAnalyzer', 'name': 'analyze'}
        ]
    )
    
    # Проверка статуса
    if result.status.value == 'completed':
        print("Workflow выполнен успешно!")
    """)
    
    print("✅ Все инструменты готовы к использованию!")


def main():
    """Главная функция демонстрации."""
    print("\n" + "█"*70)
    print("█  AI ORCHESTRATOR FOR PROJECT-TO-PPROG")
    print("█  Автоматизация преобразования документации АПС")
    print("█"*70)
    
    print(f"\n📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    try:
        # Запускаем все демо
        demo_basic_workflow()
        demo_domain_model()
        demo_custom_pipeline()
        demo_api_usage()
        
        print("\n" + "█"*70)
        print("✅ ВСЕ ДЕМО ЗАВЕРШЕНЫ УСПЕШНО")
        print("█"*70)
        print("\n📚 Документация: /workspace/orchestrator/README.md")
        print("🧪 Тесты: python -m unittest tests.test_orchestrator")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении демо: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
