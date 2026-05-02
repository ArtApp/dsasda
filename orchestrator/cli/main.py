#!/usr/bin/env python3
"""
CLI интерфейс для системы AI Orchestrator Project-to-PProg.
Позволяет запускать полный конвейер обработки из командной строки.

Использование:
    python -m orchestrator.cli.main run --input ./data_synthetic --output ./output
    python -m orchestrator.cli.main analyze --input ./data_synthetic/specification.pdf
    python -m orchestrator.cli.main generate --model ./output/domain_model.json --output ./output/config.pprog
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Добавляем родительскую директорию в path для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
    ProjectDomainModel
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)


def setup_orchestrator() -> WorkflowManager:
    """Создает и настраивает оркестратор со всеми инструментами."""
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
    
    logger.info("Оркестратор настроен с 8 инструментами")
    return orchestrator


def execute_single_tool(orchestrator: WorkflowManager, tool_name: str, input_data: any):
    """Выполняет один инструмент через workflow manager."""
    result = orchestrator.execute_workflow(
        input_data=input_data,
        steps=[{'tool': tool_name, 'name': tool_name.lower()}]
    )
    # Возвращаем данные из последнего шага
    if hasattr(result, 'current_step_result') and result.current_step_result:
        return result.current_step_result.data if hasattr(result.current_step_result, 'data') else result.current_step_result
    return {}


def cmd_run(args):
    """Запускает полный конвейер обработки."""
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        logger.error(f"Входная директория не найдена: {input_path}")
        return 1
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Запуск полного конвейера для: {input_path}")
    logger.info(f"Результаты будут сохранены в: {output_path}")
    
    try:
        orchestrator = setup_orchestrator()
        
        # Шаг 1: Анализ документов
        logger.info("=" * 60)
        logger.info("ШАГ 1: Анализ входных документов")
        doc_result = execute_single_tool(
            orchestrator, "DocumentAnalyzer", str(input_path)
        )
        doc_report_path = output_path / "document_analysis_report.txt"
        with open(doc_report_path, 'w', encoding='utf-8') as f:
            f.write(doc_result.get('report', 'Отчет не сгенерирован'))
        logger.info(f"Отчет по анализу документов: {doc_report_path}")
        
        # Шаг 2: Извлечение из спецификаций
        logger.info("=" * 60)
        logger.info("ШАГ 2: NLP анализ спецификаций")
        nlp_result = execute_single_tool(orchestrator, 
            "NLPSpecExtractor",
            input_data=open(input_path / "specification.txt" if input_path.is_dir() else input_path, 'r', encoding='utf-8').read() if (input_path / "specification.txt" if input_path.is_dir() else input_path).exists() else ""
        )
        spec_json_path = output_path / "specifications.json"
        with open(spec_json_path, 'w', encoding='utf-8') as f:
            json.dump(nlp_result.get('devices', []), f, indent=2, ensure_ascii=False)
        logger.info(f"Извлеченные устройства: {spec_json_path}")
        
        # Шаг 3: Анализ планов (если есть изображения)
        logger.info("=" * 60)
        logger.info("ШАГ 3: CV анализ планов этажей")
        images = doc_result.get('images', [])
        if images:
            plan_result = execute_single_tool(orchestrator, 
                "CVPlanAnalyzer",
                input_data={'images': images}
            )
            plans_json_path = output_path / "plans_detection.json"
            with open(plans_json_path, 'w', encoding='utf-8') as f:
                json.dump(plan_result.get('detected_devices', []), f, indent=2, ensure_ascii=False)
            logger.info(f"Обнаруженные устройства на планах: {plans_json_path}")
        else:
            logger.warning("Изображения планов не найдены, пропускаем шаг CV планов")
            plan_result = {'detected_devices': []}
        
        # Шаг 4: Анализ схем (если есть)
        logger.info("=" * 60)
        logger.info("ШАГ 4: CV анализ схем подключений")
        schematic_result = execute_single_tool(orchestrator, 
            "CVSchematicAnalyzer",
            input_data={'images': images}  # В реальном проекте нужны отдельные изображения схем
        )
        schema_json_path = output_path / "schematic_graph.json"
        with open(schema_json_path, 'w', encoding='utf-8') as f:
            json.dump(schematic_result.get('connection_graph', {}), f, indent=2, ensure_ascii=False)
        logger.info(f"Граф соединений: {schema_json_path}")
        
        # Шаг 5: Синтез данных
        logger.info("=" * 60)
        logger.info("ШАГ 5: Синтез и валидация данных")
        synth_input = {
            'specifications': nlp_result.get('devices', []),
            'plan_devices': plan_result.get('detected_devices', []),
            'schema_graph': schematic_result.get('connection_graph', {})
        }
        synth_result = execute_single_tool(orchestrator, 
            "DataSynthesizer",
            input_data=synth_input
        )
        
        # Сохраняем доменную модель
        domain_model = synth_result.get('domain_model')
        if domain_model:
            model_json_path = output_path / "domain_model.json"
            # Сериализуем модель в JSON
            model_dict = {
                'project_name': getattr(domain_model, 'project_name', 'Unknown'),
                'devices': [
                    {
                        'id': d.id,
                        'type': d.type.value if hasattr(d.type, 'value') else str(d.type),
                        'model': d.model,
                        'location': d.location,
                        'partition': d.partition,
                        'channels': d.channels,
                        'confidence': d.confidence.value if hasattr(d.confidence, 'value') else str(d.confidence)
                    }
                    for d in domain_model.devices
                ],
                'connections': [
                    {
                        'source_id': c.source_id,
                        'target_id': c.target_id,
                        'connection_type': c.connection_type.value if hasattr(c.connection_type, 'value') else str(c.connection_type)
                    }
                    for c in domain_model.connections
                ],
                'partitions': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'device_ids': p.device_ids
                    }
                    for p in domain_model.partitions
                ],
                'validation_results': synth_result.get('validation_report', {})
            }
            with open(model_json_path, 'w', encoding='utf-8') as f:
                json.dump(model_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"Доменная модель: {model_json_path}")
        else:
            logger.error("Не удалось создать доменную модель")
            return 1
        
        # Шаг 6: Генерация конфигурации
        logger.info("=" * 60)
        logger.info("ШАГ 6: Генерация конфигурации PProg")
        config_result = execute_single_tool(orchestrator, 
            "ConfigGenerator",
            input_data={'domain_model': domain_model}
        )
        
        config_path = output_path / "config.pprog"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_result.get('config_content', ''))
        logger.info(f"Конфигурация сгенерирована: {config_path}")
        
        # Шаг 7: Генерация отчета
        logger.info("=" * 60)
        logger.info("ШАГ 7: Генерация итогового отчета")
        report_result = execute_single_tool(orchestrator, 
            "ReportGenerator",
            input_data={
                'domain_model': domain_model,
                'validation_results': synth_result.get('validation_report', {}),
                'config_content': config_result.get('config_content', '')
            }
        )
        
        # Текстовый отчет
        txt_report_path = output_path / "project_report.txt"
        with open(txt_report_path, 'w', encoding='utf-8') as f:
            f.write(report_result.get('text_report', ''))
        logger.info(f"Текстовый отчет: {txt_report_path}")
        
        # HTML отчет
        html_report_path = output_path / "project_report.html"
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(report_result.get('html_report', ''))
        logger.info(f"HTML отчет: {html_report_path}")
        
        logger.info("=" * 60)
        logger.info("✅ КОНВЕЙЕР ЗАВЕРШЕН УСПЕШНО")
        logger.info(f"Выходные файлы в: {output_path}")
        return 0
        
    except Exception as e:
        logger.exception(f"Критическая ошибка при выполнении конвейера: {e}")
        return 1


def cmd_analyze(args):
    """Анализирует входные документы без полной обработки."""
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"Файл/директория не найдены: {input_path}")
        return 1
    
    logger.info(f"Анализ: {input_path}")
    
    try:
        analyzer = DocumentAnalyzer()
        result = analyzer.execute(str(input_path))
        
        # Получаем данные из ToolResult
        data = result.data if hasattr(result, 'data') else result
        
        # Извлекаем отчет (может быть объектом AnalysisReport)
        report = data.get('report') if isinstance(data, dict) else getattr(data, 'report', None)
        
        # Конвертируем в dict если это объект
        if hasattr(report, '__dict__'):
            report_dict = {
                'total_files': getattr(report, 'total_files', 0),
                'file_types': getattr(report, 'file_types', {}),
                'total_text_length': getattr(report, 'total_text_length', 0),
                'total_images': getattr(report, 'total_images', 0),
                'keywords_found': getattr(report, 'keywords_found', []),
                'summary': getattr(report, 'summary', ''),
            }
        elif isinstance(report, dict):
            report_dict = report
        else:
            report_dict = {}
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА ДОКУМЕНТОВ")
        print("=" * 60)
        print(f"Типы файлов: {report_dict.get('file_types', {})}")
        print(f"Объем текста: {report_dict.get('total_text_length', 0)} символов")
        print(f"Изображений: {report_dict.get('total_images', 0)}")
        print(f"Ключевые слова АПС: {report_dict.get('keywords_found', [])}")
        print(f"\n{report_dict.get('summary', '')}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Ошибка анализа: {e}")
        return 1


def cmd_generate(args):
    """Генерирует конфигурацию из готовой доменной модели."""
    model_path = Path(args.model)
    output_path = Path(args.output)
    
    if not model_path.exists():
        logger.error(f"Файл модели не найден: {model_path}")
        return 1
    
    logger.info(f"Генерация конфигурации из: {model_path}")
    
    try:
        # Загружаем доменную модель из JSON
        with open(model_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        
        # Восстанавливаем объект DomainModel (упрощенно)
        # В реальном проекте нужна полноценная десериализация
        from orchestrator.models.domain import Device, Connection, Partition, ProjectDomainModel, DeviceType, ConfidenceLevel
        
        devices = []
        for d in model_data.get('devices', []):
            device = Device(
                id=d['id'],
                type=DeviceType(d['type']) if isinstance(d['type'], str) else d['type'],
                model=d.get('model', ''),
                location=d.get('location', ''),
                partition=d.get('partition', 0),
                channels=d.get('channels', 0),
                confidence=ConfidenceLevel(d.get('confidence', 'medium'))
            )
            devices.append(device)
        
        connections = []
        for c in model_data.get('connections', []):
            conn = Connection(
                source_id=c['source_id'],
                target_id=c['target_id'],
                connection_type=c.get('connection_type', 'signal')
            )
            connections.append(conn)
        
        partitions = []
        for p in model_data.get('partitions', []):
            part = Partition(
                id=p['id'],
                name=p.get('name', f'Раздел {p["id"]}'),
                device_ids=p.get('device_ids', [])
            )
            partitions.append(part)
        
        domain_model = ProjectDomainModel(
            project_name=model_data.get('project_name', 'Project'),
            devices=devices,
            connections=connections,
            partitions=partitions
        )
        
        # Генерируем конфигурацию
        generator = ConfigGenerator()
        result = generator.execute({'domain_model': domain_model})
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.get('config_content', ''))
        
        logger.info(f"✅ Конфигурация сгенерирована: {output_path}")
        return 0
        
    except Exception as e:
        logger.exception(f"Ошибка генерации: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="AI Orchestrator для преобразования проектной документации АПС в PProg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s run --input ./project_docs --output ./output
  %(prog)s analyze --input ./project_docs/specification.pdf
  %(prog)s generate --model ./output/domain_model.json --output ./output/config.pprog
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда run
    run_parser = subparsers.add_parser('run', help='Запустить полный конвейер обработки')
    run_parser.add_argument('--input', '-i', required=True, help='Входная директория с документами')
    run_parser.add_argument('--output', '-o', required=True, help='Выходная директория для результатов')
    run_parser.set_defaults(func=cmd_run)
    
    # Команда analyze
    analyze_parser = subparsers.add_parser('analyze', help='Анализировать входные документы')
    analyze_parser.add_argument('--input', '-i', required=True, help='Файл или директория для анализа')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Команда generate
    gen_parser = subparsers.add_parser('generate', help='Сгенерировать конфигурацию из модели')
    gen_parser.add_argument('--model', '-m', required=True, help='JSON файл доменной модели')
    gen_parser.add_argument('--output', '-o', required=True, help='Выходной файл конфигурации')
    gen_parser.set_defaults(func=cmd_generate)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
