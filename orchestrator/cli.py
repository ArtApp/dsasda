"""
CLI интерфейс для AI Orchestrator системы преобразования АПС в PProg.

Использование:
    python cli.py analyze <input_path>           # Анализ документов
    python cli.py extract <input_path>           # Извлечение спецификаций
    python cli.py process <input_path>           # Полный конвейер
    python cli.py validate <config_path>         # Валидация конфигурации
    python cli.py report <input_path>            # Генерация отчёта
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import (
    WorkflowManager,
    DocumentAnalyzer,
    ConfigFormatAnalyzer,
    NLPSpecExtractor,
    CVPlanAnalyzer,
    CVSchematicAnalyzer,
    DataSynthesizer,
    ConfigGenerator,
    ReportGenerator
)
from orchestrator.models.workflow import WorkflowStatus


def setup_orchestrator() -> WorkflowManager:
    """Создаёт и настраивает оркестратор со всеми инструментами."""
    orchestrator = WorkflowManager()
    
    # Регистрируем все инструменты
    orchestrator.register_tool(DocumentAnalyzer())
    orchestrator.register_tool(ConfigFormatAnalyzer())
    orchestrator.register_tool(NLPSpecExtractor())
    orchestrator.register_tool(CVPlanAnalyzer())
    orchestrator.register_tool(CVSchematicAnalyzer())
    orchestrator.register_tool(DataSynthesizer())
    orchestrator.register_tool(ConfigGenerator())
    orchestrator.register_tool(ReportGenerator())
    
    return orchestrator


def cmd_analyze(args):
    """Анализ входных документов."""
    print(f"🔍 Анализ документов: {args.input}")
    
    orchestrator = setup_orchestrator()
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        return 1
    
    result = orchestrator.execute_workflow(
        input_data=str(input_path),
        steps=[{'tool': 'DocumentAnalyzer', 'name': 'analyze'}]
    )
    
    # Вывод результатов
    if result.status == WorkflowStatus.COMPLETED:
        analysis_result = result.context.get('last_output', {})
        print("\n✅ Анализ завершён:")
        print(f"   Типов файлов: {len(analysis_result.get('file_types', {}))}")
        print(f"   Объём текста: {analysis_result.get('text_stats', {}).get('total_chars', 0)} символов")
        print(f"   Изображений: {analysis_result.get('image_count', 0)}")
        
        if analysis_result.get('keywords'):
            print(f"\n   Ключевые слова АПС:")
            for kw in analysis_result['keywords'][:10]:
                print(f"      - {kw}")
        
        # Сохранение отчёта
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Отчёт сохранён: {output_path}")
        
        return 0
    else:
        print(f"❌ Ошибка анализа: {result.errors}")
        return 1


def cmd_extract(args):
    """Извлечение спецификаций из документов."""
    print(f"📋 Извлечение спецификаций: {args.input}")
    
    orchestrator = setup_orchestrator()
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        return 1
    
    # Сначала анализируем документы
    analyze_result = orchestrator.execute_workflow(
        input_data=str(input_path),
        steps=[{'tool': 'DocumentAnalyzer', 'name': 'analyze'}]
    )
    
    if analyze_result.status != 'completed':
        print(f"❌ Ошибка анализа: {analyze_result.error}")
        return 1
    
    # Затем извлекаем спецификации
    extract_result = orchestrator.execute_workflow(
        input_data=analyze_result.state.data,
        steps=[{'tool': 'NLPSpecExtractor', 'name': 'extract'}]
    )
    
    if extract_result.status == 'completed':
        spec_result = extract_result.tool_results.get('extract', {})
        devices = spec_result.get('devices', [])
        
        print(f"\n✅ Найдено устройств: {len(devices)}")
        
        # Группировка по типам
        by_type = {}
        for device in devices:
            dtype = device.get('device_type', 'Unknown')
            by_type[dtype] = by_type.get(dtype, 0) + 1
        
        print("\n   По типам:")
        for dtype, count in sorted(by_type.items()):
            print(f"      {dtype}: {count}")
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(spec_result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Спецификация сохранена: {output_path}")
        
        return 0
    else:
        print(f"❌ Ошибка извлечения: {extract_result.error}")
        return 1


def cmd_process(args):
    """Полный конвейер обработки проекта."""
    print(f"⚙️ Полный конвейер обработки: {args.input}")
    print(f"   Вход: {args.input}")
    print(f"   Выход: {args.output or './output'}")
    
    orchestrator = setup_orchestrator()
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else Path('./output')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        return 1
    
    start_time = datetime.now()
    
    # Этап 1: Анализ документов
    print("\n[1/5] 🔍 Анализ документов...")
    analyze_result = orchestrator.execute_workflow(
        input_data=str(input_path),
        steps=[{'tool': 'DocumentAnalyzer', 'name': 'analyze'}]
    )
    
    if analyze_result.status != 'completed':
        print(f"❌ Ошибка анализа: {analyze_result.error}")
        return 1
    print(f"    ✅ Анализ завершён")
    
    # Этап 2: Извлечение спецификаций
    print("\n[2/5] 📋 Извлечение спецификаций...")
    extract_result = orchestrator.execute_workflow(
        input_data=analyze_result.state.data,
        steps=[{'tool': 'NLPSpecExtractor', 'name': 'extract'}]
    )
    
    if extract_result.status != 'completed':
        print(f"❌ Ошибка извлечения: {extract_result.error}")
        return 1
    print(f"    ✅ Найдено устройств: {len(extract_result.tool_results.get('extract', {}).get('devices', []))}")
    
    # Этап 3: Анализ планов (если есть изображения)
    print("\n[3/5] 🗺️ Анализ планов этажей...")
    plan_result = orchestrator.execute_workflow(
        input_data=analyze_result.state.data,
        steps=[{'tool': 'CVPlanAnalyzer', 'name': 'analyze_plans'}]
    )
    
    if plan_result.status == 'completed':
        plan_devices = plan_result.tool_results.get('analyze_plans', {}).get('devices', [])
        print(f"    ✅ Обнаружено на планах: {len(plan_devices)}")
    else:
        print(f"    ⚠️ Предупреждение: {plan_result.error}")
    
    # Этап 4: Синтез данных
    print("\n[4/5] 🔗 Синтез данных и валидация...")
    synthesize_result = orchestrator.execute_workflow(
        input_data={
            'specifications': extract_result.tool_results.get('extract', {}),
            'plans': plan_result.tool_results.get('analyze_plans', {}) if plan_result.status == 'completed' else {},
            'original_analysis': analyze_result.tool_results.get('analyze', {})
        },
        steps=[{'tool': 'DataSynthesizer', 'name': 'synthesize'}]
    )
    
    if synthesize_result.status != 'completed':
        print(f"❌ Ошибка синтеза: {synthesize_result.error}")
        return 1
    
    domain_model = synthesize_result.tool_results.get('synthesize', {}).get('domain_model')
    validation = synthesize_result.tool_results.get('synthesize', {}).get('validation', {})
    print(f"    ✅ Доменная модель создана")
    print(f"    ✅ Проверок пройдено: {len(validation.get('passed_checks', []))}")
    if validation.get('warnings'):
        print(f"    ⚠️ Предупреждений: {len(validation['warnings'])}")
    
    # Этап 5: Генерация конфигурации
    print("\n[5/5] ⚡ Генерация конфигурации PProg...")
    config_result = orchestrator.execute_workflow(
        input_data=domain_model,
        steps=[{'tool': 'ConfigGenerator', 'name': 'generate_config'}]
    )
    
    if config_result.status != 'completed':
        print(f"❌ Ошибка генерации: {config_result.error}")
        return 1
    
    # Сохранение конфигурации
    config_file = output_dir / 'project.pprog'
    config_data = config_result.tool_results.get('generate_config', {})
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_data.get('config_content', ''))
    print(f"    ✅ Конфигурация сохранена: {config_file}")
    
    # Генерация отчёта
    print("\n📊 Генерация итогового отчёта...")
    report_result = orchestrator.execute_workflow(
        input_data={
            'domain_model': domain_model,
            'config': config_data,
            'validation': validation
        },
        steps=[{'tool': 'ReportGenerator', 'name': 'generate_report'}]
    )
    
    if report_result.status == 'completed':
        report_data = report_result.tool_results.get('generate_report', {})
        
        # Текстовый отчёт
        text_report = output_dir / 'report.txt'
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write(report_data.get('text_report', ''))
        print(f"    ✅ Текстовый отчёт: {text_report}")
        
        # HTML отчёт
        html_report = output_dir / 'report.html'
        with open(html_report, 'w', encoding='utf-8') as f:
            f.write(report_data.get('html_report', ''))
        print(f"    ✅ HTML отчёт: {html_report}")
    
    elapsed = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"✅ КОНВЕЙЕР ЗАВЕРШЁН УСПЕШНО")
    print(f"   Время выполнения: {elapsed}")
    print(f"   Выходные файлы в: {output_dir.absolute()}")
    print(f"{'='*60}")
    
    return 0


def cmd_validate(args):
    """Валидация существующей конфигурации."""
    print(f"✓ Валидация конфигурации: {args.config}")
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Файл не найден: {config_path}")
        return 1
    
    orchestrator = setup_orchestrator()
    
    # Чтение конфигурации
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    result = orchestrator.execute_workflow(
        input_data={'config_content': config_content},
        steps=[{'tool': 'ConfigFormatAnalyzer', 'name': 'validate'}]
    )
    
    if result.status == 'completed':
        validation = result.tool_results.get('validate', {})
        print("\n✅ Валидация завершена:")
        print(f"   Структура: {'OK' if validation.get('structure_valid') else 'ERROR'}")
        print(f"   Контрольные суммы: {'OK' if validation.get('checksum_valid') else 'WARNING'}")
        
        if validation.get('issues'):
            print(f"\n   Найдено проблем: {len(validation['issues'])}")
            for issue in validation['issues'][:5]:
                print(f"      - {issue}")
        
        return 0
    else:
        print(f"❌ Ошибка валидации: {result.error}")
        return 1


def cmd_report(args):
    """Генерация отчёта по проекту."""
    print(f"📊 Генерация отчёта: {args.input}")
    
    orchestrator = setup_orchestrator()
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        return 1
    
    # Быстрый анализ и отчёт
    analyze_result = orchestrator.execute_workflow(
        input_data=str(input_path),
        steps=[{'tool': 'DocumentAnalyzer', 'name': 'analyze'}]
    )
    
    if analyze_result.status != 'completed':
        print(f"❌ Ошибка анализа: {analyze_result.error}")
        return 1
    
    report_result = orchestrator.execute_workflow(
        input_data=analyze_result.tool_results.get('analyze', {}),
        steps=[{'tool': 'ReportGenerator', 'name': 'quick_report'}]
    )
    
    if report_result.status == 'completed':
        report_data = report_result.tool_results.get('quick_report', {})
        
        output_path = args.output or './quick_report.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_data.get('text_report', 'Отчёт не сгенерирован'))
        
        print(f"\n✅ Отчёт сохранён: {output_path}")
        return 0
    else:
        print(f"❌ Ошибка генерации отчёта: {report_result.error}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='AI Orchestrator для преобразования АПС в PProg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s analyze project_docs.pdf -o analysis.json
  %(prog)s extract specification.docx -o devices.json
  %(prog)s process ./input_docs -o ./output
  %(prog)s validate config.pprog
  %(prog)s report project_docs.pdf -o report.txt
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Команда analyze
    parser_analyze = subparsers.add_parser('analyze', help='Анализ документов')
    parser_analyze.add_argument('input', help='Входной файл или каталог')
    parser_analyze.add_argument('-o', '--output', help='Выходной файл JSON')
    parser_analyze.set_defaults(func=cmd_analyze)
    
    # Команда extract
    parser_extract = subparsers.add_parser('extract', help='Извлечение спецификаций')
    parser_extract.add_argument('input', help='Входной файл')
    parser_extract.add_argument('-o', '--output', help='Выходной файл JSON')
    parser_extract.set_defaults(func=cmd_extract)
    
    # Команда process
    parser_process = subparsers.add_parser('process', help='Полный конвейер')
    parser_process.add_argument('input', help='Входной файл или каталог')
    parser_process.add_argument('-o', '--output', help='Выходной каталог', default='./output')
    parser_process.set_defaults(func=cmd_process)
    
    # Команда validate
    parser_validate = subparsers.add_parser('validate', help='Валидация конфигурации')
    parser_validate.add_argument('config', help='Файл конфигурации .pprog')
    parser_validate.set_defaults(func=cmd_validate)
    
    # Команда report
    parser_report = subparsers.add_parser('report', help='Генерация отчёта')
    parser_report.add_argument('input', help='Входной файл или каталог')
    parser_report.add_argument('-o', '--output', help='Выходной файл отчёта')
    parser_report.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
