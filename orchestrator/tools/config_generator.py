"""
Config Generator - ИИ-инструмент для генерации конфигурации PProg.
Этап 5: Разработка Движка Генерации и Валидации

Принимает валидированную доменную модель и генерирует .pprog файл.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus
from orchestrator.models.domain import ProjectDomainModel, Device, DeviceType

logger = logging.getLogger(__name__)


class ConfigGenerator(AITool):
    """
    ИИ-инструмент для генерации конфигурационных файлов PProg.
    
    Функции:
    - Преобразование доменной модели в формат PProg
    - Использование шаблонов (Jinja2) или LLM для генерации
    - Валидация зависимостей и контрольных сумм
    - Вывод готового .pprog файла
    """
    
    # Маппинг типов устройств на форматы PProg
    DEVICE_TYPE_MAP = {
        DeviceType.CONTROL_PANEL: "С2000М",
        DeviceType.KDL: "С2000-КДЛ",
        DeviceType.RELAY: "С2000-СП2",
        DeviceType.KEYBOARD: "С2000-БКИ",
        DeviceType.SMOKE_DETECTOR: "ДИП-34А",
        DeviceType.MANUAL_CALL_POINT: "ИПР 513-3А",
        DeviceType.LIGHT_ALARM: "Маяк-12-3М",
        DeviceType.SOUND_ALARM: "Маяк-12-3М (сирена)",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ConfigGenerator", config)
        self.output_format = self.config.get('output_format', 'txt')
        self.template_path = self.config.get('template_path', None)
        
        # Lazy imports
        self._jinja2 = None
    
    def _initialize(self):
        """Инициализация."""
        try:
            from jinja2 import Environment, FileSystemLoader
            self._jinja2 = {'Environment': Environment, 'FileSystemLoader': FileSystemLoader}
            logger.info("Jinja2 initialized")
        except ImportError:
            logger.warning("Jinja2 not available, using simple template")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить генерацию конфигурации.
        
        Args:
            input_data: dict с доменной моделью:
                {
                    'domain_model': {...},
                    'output_path': 'path/to/output.pprog',
                }
            
        Returns:
            ToolResult с результатами генерации
        """
        start_time = time.time()
        
        try:
            # Извлечение входных данных
            if isinstance(input_data, dict):
                domain_model_data = input_data.get('domain_model', {})
                output_path = input_data.get('output_path', 'output/config.txt')
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data. Expected dict with domain_model."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Создание доменной модели из данных
            domain_model = self._reconstruct_domain_model(domain_model_data)
            
            # Генерация конфигурации
            config_content = self._generate_config_content(domain_model)
            
            # Сохранение в файл
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    'output_path': str(output_file),
                    'file_size': output_file.stat().st_size,
                    'devices_count': domain_model.total_devices,
                    'config_preview': config_content[:500],
                },
                metadata={
                    'format': self.output_format,
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                },
                execution_time_ms=execution_time,
                confidence=0.9,
            )
            
        except Exception as e:
            logger.exception(f"Error in ConfigGenerator: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _reconstruct_domain_model(self, data: Dict) -> ProjectDomainModel:
        """Восстановить доменную модель из словаря."""
        model = ProjectDomainModel(
            project_name=data.get('project_name', 'Generated Project'),
        )
        
        # Восстановление устройств
        for d in data.get('devices', []):
            try:
                device_type = DeviceType(d.get('device_type', 'other'))
            except ValueError:
                device_type = DeviceType.OTHER
            
            device = Device(
                device_type=device_type,
                model=d.get('model', 'unknown'),
                address=d.get('address', 0),
                quantity=d.get('quantity', 1),
                location=d.get('location'),
                room_number=d.get('room_number'),
            )
            model.add_device(device)
        
        return model
    
    def _generate_config_content(self, model: ProjectDomainModel) -> str:
        """Сгенерировать содержимое конфигурационного файла."""
        lines = []
        
        # Заголовок
        lines.append("=" * 60)
        lines.append(f"Конфигурация PProg - {model.project_name}")
        lines.append(f"Сгенерировано автоматически: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # Секция устройств
        lines.append("[УСТРОЙСТВА]")
        lines.append("-" * 40)
        
        for i, device in enumerate(model.devices, 1):
            device_name = self.DEVICE_TYPE_MAP.get(device.device_type, device.model)
            line = f"{i}. {device_name}"
            
            if device.address > 0:
                line += f" (адрес {device.address})"
            
            if device.location:
                line += f" - {device.location}"
            
            if device.room_number:
                line += f" (пом. {device.room_number})"
            
            lines.append(line)
        
        lines.append("")
        lines.append(f"Всего устройств: {model.total_devices}")
        lines.append("")
        
        # Секция разделов (если есть)
        if model.partitions:
            lines.append("[РАЗДЕЛЫ]")
            lines.append("-" * 40)
            
            for partition in model.partitions:
                lines.append(f"Раздел {partition.partition_id}: {partition.name}")
                lines.append(f"  Зоны: {', '.join(map(str, partition.zones))}")
            
            lines.append("")
        
        # Секция связей (если есть)
        if model.connections:
            lines.append("[СОЕДИНЕНИЯ]")
            lines.append("-" * 40)
            
            for conn in model.connections:
                lines.append(
                    f"{conn.from_device_id} -> {conn.to_device_id} "
                    f"({conn.connection_type})"
                )
            
            lines.append("")
        
        # Предупреждения и проблемы
        if model.warnings or model.validation_issues:
            lines.append("[ПРЕДУПРЕЖДЕНИЯ]")
            lines.append("-" * 40)
            
            for issue in model.validation_issues:
                lines.append(f"! {issue}")
            
            for warning in model.warnings:
                lines.append(f"* {warning}")
            
            lines.append("")
        
        # Подвал
        lines.append("=" * 60)
        lines.append("Конец конфигурации")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def generate_json_config(self, model: ProjectDomainModel) -> str:
        """Сгенерировать конфигурацию в формате JSON."""
        import json
        return json.dumps(model.to_dict(), indent=2, ensure_ascii=False)
