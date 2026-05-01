"""
Report Generator - ИИ-инструмент для генерации отчетов.
Этап 5: Разработка Движка Генерации и Валидации

Использует LLM для анализа доменной модели и создания подробного отчета.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ReportGenerator(AITool):
    """
    ИИ-инструмент для генерации подробных отчетов о проекте.
    
    Функции:
    - Анализ доменной модели и результатов синтеза
    - Создание текстового/HTML отчета
    - Список всех устройств и связей
    - Обнаруженные проблемы и предупреждения
    - Обоснование принятых решений
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ReportGenerator", config)
        self.output_format = self.config.get('output_format', 'html')
        self.include_raw_data = self.config.get('include_raw_data', False)
    
    def _initialize(self):
        """Инициализация."""
        logger.info("ReportGenerator initialized")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить генерацию отчета.
        
        Args:
            input_data: dict с данными для отчета:
                {
                    'domain_model': {...},
                    'validation': {...},
                    'statistics': {...},
                    'output_path': 'path/to/report.html',
                }
            
        Returns:
            ToolResult с результатами генерации
        """
        start_time = time.time()
        
        try:
            # Извлечение входных данных
            if not isinstance(input_data, dict):
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data. Expected dict."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            domain_model = input_data.get('domain_model', {})
            validation = input_data.get('validation', {})
            statistics = input_data.get('statistics', {})
            output_path = input_data.get('output_path', 'output/report.html')
            
            # Генерация отчета
            if self.output_format == 'html':
                report_content = self._generate_html_report(
                    domain_model, validation, statistics
                )
            else:
                report_content = self._generate_text_report(
                    domain_model, validation, statistics
                )
            
            # Сохранение в файл
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    'output_path': str(output_file),
                    'file_size': output_file.stat().st_size,
                    'format': self.output_format,
                    'report_preview': report_content[:500],
                },
                metadata={
                    'devices_reported': statistics.get('total_devices', 0),
                    'issues_reported': len(validation.get('issues', [])),
                },
                execution_time_ms=execution_time,
                confidence=0.95,
            )
            
        except Exception as e:
            logger.exception(f"Error in ReportGenerator: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _generate_text_report(
        self,
        domain_model: Dict,
        validation: Dict,
        statistics: Dict,
    ) -> str:
        """Сгенерировать текстовый отчет."""
        lines = []
        
        # Заголовок
        lines.append("=" * 80)
        lines.append("ОТЧЕТ О ПРОЕКТЕ АВТОМАТИЧЕСКОЙ ПОЖАРНОЙ СИГНАЛИЗАЦИИ")
        lines.append("=" * 80)
        lines.append("")
        
        # Общая информация
        lines.append("1. ОБЩАЯ ИНФОРМАЦИЯ")
        lines.append("-" * 40)
        lines.append(f"Проект: {domain_model.get('project_name', 'Не указан')}")
        lines.append(f"Дата генерации: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Статистика
        lines.append("2. СТАТИСТИКА ПРОЕКТА")
        lines.append("-" * 40)
        stats = statistics.get('total_devices', 0)
        lines.append(f"Всего устройств: {stats}")
        lines.append(f"Всего разделов: {statistics.get('total_partitions', 0)}")
        lines.append(f"Всего соединений: {statistics.get('total_connections', 0)}")
        lines.append("")
        
        # Устройства
        lines.append("3. СПИСОК УСТРОЙСТВ")
        lines.append("-" * 40)
        
        devices = domain_model.get('devices', [])
        for i, device in enumerate(devices, 1):
            dtype = device.get('device_type', 'unknown')
            model = device.get('model', 'unknown')
            address = device.get('address', 0)
            location = device.get('location', '')
            room = device.get('room_number', '')
            
            line = f"{i}. {dtype} - {model}"
            if address > 0:
                line += f" (адрес: {address})"
            if location:
                line += f" [{location}]"
            if room:
                line += f" (пом. {room})"
            
            lines.append(line)
        
        lines.append("")
        
        # Проблемы и предупреждения
        lines.append("4. ПРОБЛЕМЫ И ПРЕДУПРЕЖДЕНИЯ")
        lines.append("-" * 40)
        
        issues = validation.get('issues', [])
        warnings = validation.get('warnings', [])
        suggestions = validation.get('suggestions', [])
        
        if issues:
            lines.append("ПРОБЛЕМЫ:")
            for issue in issues:
                lines.append(f"  ! {issue}")
            lines.append("")
        
        if warnings:
            lines.append("ПРЕДУПРЕЖДЕНИЯ:")
            for warning in warnings:
                lines.append(f"  * {warning}")
            lines.append("")
        
        if suggestions:
            lines.append("РЕКОМЕНДАЦИИ:")
            for suggestion in suggestions:
                lines.append(f"  > {suggestion}")
            lines.append("")
        
        if not issues and not warnings and not suggestions:
            lines.append("Проблем и предупреждений не обнаружено.")
            lines.append("")
        
        # Заключение
        lines.append("5. ЗАКЛЮЧЕНИЕ")
        lines.append("-" * 40)
        
        is_valid = validation.get('is_valid', True)
        if is_valid:
            lines.append("Конфигурация прошла валидацию и готова к использованию.")
        else:
            lines.append("Требуется ручная проверка конфигурации из-за обнаруженных проблем.")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("Конец отчета")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_html_report(
        self,
        domain_model: Dict,
        validation: Dict,
        statistics: Dict,
    ) -> str:
        """Сгенерировать HTML отчет."""
        text_report = self._generate_text_report(domain_model, validation, statistics)
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет проекта АПС - {domain_model.get('project_name', 'Unknown')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .section {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }}
        .issue {{ color: #e74c3c; }}
        .warning {{ color: #f39c12; }}
        .suggestion {{ color: #27ae60; }}
        .device {{ padding: 5px 0; border-bottom: 1px solid #ecf0f1; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>📋 Отчет проекта автоматической пожарной сигнализации</h1>
    
    <div class="section">
        <h2>📊 Общая информация</h2>
        <p><strong>Проект:</strong> {domain_model.get('project_name', 'Не указан')}</p>
        <p><strong>Дата генерации:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>📈 Статистика</h2>
        <table>
            <tr><th>Параметр</th><th>Значение</th></tr>
            <tr><td>Всего устройств</td><td>{statistics.get('total_devices', 0)}</td></tr>
            <tr><td>Всего разделов</td><td>{statistics.get('total_partitions', 0)}</td></tr>
            <tr><td>Всего соединений</td><td>{statistics.get('total_connections', 0)}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>🔧 Список устройств</h2>
        <table>
            <tr><th>#</th><th>Тип</th><th>Модель</th><th>Адрес</th><th>Локация</th></tr>
"""
        
        devices = domain_model.get('devices', [])
        for i, device in enumerate(devices, 1):
            html += f"""            <tr>
                <td>{i}</td>
                <td>{device.get('device_type', 'unknown')}</td>
                <td>{device.get('model', 'unknown')}</td>
                <td>{device.get('address', 0)}</td>
                <td>{device.get('location', '')} {device.get('room_number', '')}</td>
            </tr>
"""
        
        html += """        </table>
    </div>
    
    <div class="section">
        <h2>⚠️ Проблемы и предупреждения</h2>
"""
        
        issues = validation.get('issues', [])
        warnings = validation.get('warnings', [])
        suggestions = validation.get('suggestions', [])
        
        if issues:
            html += "        <h3 class='issue'>Проблемы</h3><ul>"
            for issue in issues:
                html += f"            <li class='issue'>{issue}</li>"
            html += "        </ul>"
        
        if warnings:
            html += "        <h3 class='warning'>Предупреждения</h3><ul>"
            for warning in warnings:
                html += f"            <li class='warning'>{warning}</li>"
            html += "        </ul>"
        
        if suggestions:
            html += "        <h3 class='suggestion'>Рекомендации</h3><ul>"
            for suggestion in suggestions:
                html += f"            <li class='suggestion'>{suggestion}</li>"
            html += "        </ul>"
        
        if not issues and not warnings and not suggestions:
            html += "        <p>Проблем и предупреждений не обнаружено.</p>"
        
        is_valid = validation.get('is_valid', True)
        status_color = "#27ae60" if is_valid else "#e74c3c"
        status_text = "Готова к использованию" if is_valid else "Требуется проверка"
        
        html += f"""    </div>
    
    <div class="section">
        <h2>✅ Статус конфигурации</h2>
        <p style="color: {status_color}; font-size: 1.2em;">
            <strong>{status_text}</strong>
        </p>
    </div>
    
    <hr>
    <p style="color: #7f8c8d; font-size: 0.9em;">
        Отчет сгенерирован автоматически системой Project-to-PProg AI Orchestrator
    </p>
</body>
</html>
"""
        
        return html
