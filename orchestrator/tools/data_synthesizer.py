"""
Data Synthesizer - ИИ-инструмент для синтеза данных из различных источников.
Этап 4: Обучение и Интеграция Основных ИИ-моделей

Принимает результаты от NLP, CV-планов, CV-схем и формирует единую доменную модель.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus
from orchestrator.models.domain import (
    ProjectDomainModel, Device, Connection, Partition,
    DeviceType, ConfidenceLevel, ValidationResult,
)

logger = logging.getLogger(__name__)


class DataSynthesizer(AITool):
    """
    ИИ-инструмент для синтеза и согласования данных из различных источников.
    
    Функции:
    - Сопоставление сущностей (ID из текста -> ID на плане/схеме)
    - Проверка консистентности (кол-во устройств, соединения)
    - Выявление расхождений и несоответствий
    - Формирование единой доменной модели проекта
    - Вывод отчета о валидации
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("DataSynthesizer", config)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
    
    def _initialize(self):
        """Инициализация."""
        logger.info("DataSynthesizer initialized")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить синтез данных.
        
        Args:
            input_data: dict с результатами от других инструментов:
                {
                    'nlp_result': {...},
                    'plan_result': {...},
                    'schematic_result': {...},
                }
            
        Returns:
            ToolResult с единой доменной моделью
        """
        start_time = time.time()
        
        try:
            # Извлечение результатов от других инструментов
            nlp_devices = self._extract_devices_from_nlp(input_data.get('nlp_result', {}))
            plan_devices = self._extract_devices_from_plan(input_data.get('plan_result', {}))
            schematic_connections = self._extract_connections_from_schematic(
                input_data.get('schematic_result', {})
            )
            
            # Создание доменной модели
            domain_model = ProjectDomainModel(project_name="Auto-generated Project")
            
            # Добавление устройств из всех источников
            all_devices = self._merge_devices(nlp_devices, plan_devices)
            for device in all_devices:
                domain_model.add_device(device)
            
            # Добавление соединений
            for conn_data in schematic_connections:
                connection = Connection(**conn_data) if isinstance(conn_data, dict) else conn_data
                domain_model.add_connection(connection)
            
            # Валидация и выявление расхождений
            validation_result = self._validate_domain_model(domain_model)
            domain_model.validation_issues = validation_result.issues
            domain_model.warnings = validation_result.warnings
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    'domain_model': domain_model.to_dict(),
                    'validation': {
                        'is_valid': validation_result.is_valid,
                        'issues': validation_result.issues,
                        'warnings': validation_result.warnings,
                        'suggestions': validation_result.suggestions,
                    },
                    'statistics': {
                        'total_devices': domain_model.total_devices,
                        'total_connections': len(domain_model.connections),
                        'total_partitions': domain_model.total_partitions,
                        'sources_used': {
                            'nlp': len(nlp_devices) > 0,
                            'plan': len(plan_devices) > 0,
                            'schematic': len(schematic_connections) > 0,
                        }
                    }
                },
                metadata={
                    'devices_merged': len(all_devices),
                    'discrepancies_found': len(validation_result.issues),
                },
                execution_time_ms=execution_time,
                confidence=0.85 if validation_result.is_valid else 0.6,
            )
            
        except Exception as e:
            logger.exception(f"Error in DataSynthesizer: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _extract_devices_from_nlp(self, nlp_result: Dict) -> List[Device]:
        """Извлечь устройства из NLP результата."""
        devices = []
        
        if not nlp_result:
            return devices
        
        # nlp_result может быть ToolResult или dict
        if hasattr(nlp_result, 'data'):
            # Это ToolResult
            nlp_data = nlp_result.data.get('devices', [])
        else:
            # Это dict
            nlp_data = nlp_result.get('data', {}).get('devices', [])
        
        for d in nlp_data:
            try:
                device_type = DeviceType(d.get('device_type', 'other'))
            except ValueError:
                device_type = DeviceType.OTHER
            
            devices.append(Device(
                device_type=device_type,
                model=d.get('model', 'unknown'),
                address=d.get('address', 0),
                quantity=d.get('quantity', 1),
                location=d.get('location'),
                confidence=ConfidenceLevel(d.get('confidence', 0.6)),
                source='nlp',
            ))
        
        return devices
    
    def _extract_devices_from_plan(self, plan_result: Dict) -> List[Device]:
        """Извлечь устройства из результата анализа планов."""
        devices = []
        
        if not plan_result:
            return devices
        
        # plan_result может быть ToolResult или dict
        if hasattr(plan_result, 'data'):
            # Это ToolResult
            plan_data = plan_result.data.get('detected_devices', [])
        else:
            # Это dict
            plan_data = plan_result.get('data', {}).get('detected_devices', [])
        
        for d in plan_data:
            # Обработка d как dict или как объекта
            if isinstance(d, dict):
                device_type_str = d.get('device_type', d.get('type', 'other'))
                model = d.get('model', 'unknown')
                location = d.get('location', d.get('room', ''))
                room_number = d.get('room_number', d.get('room', ''))
                confidence_val = d.get('confidence', 0.75)
            else:
                # Объект с атрибутами
                device_type_str = getattr(d, 'device_type', getattr(d, 'type', 'other'))
                model = getattr(d, 'model', 'unknown')
                location = getattr(d, 'location', getattr(d, 'room', ''))
                room_number = getattr(d, 'room_number', getattr(d, 'room', ''))
                confidence_val = getattr(d, 'confidence', 0.75)
            
            try:
                device_type = DeviceType(device_type_str)
            except ValueError:
                device_type = DeviceType.OTHER
            
            # Конвертация confidence в ConfidenceLevel enum
            confidence = self._get_confidence_level(confidence_val)
            
            devices.append(Device(
                device_type=device_type,
                model=model,
                address=0,  # На планах адреса обычно не указаны
                quantity=1,
                location=location,
                room_number=room_number,
                confidence=confidence,
                source='plan',
                metadata={'coordinates': getattr(d, 'coordinates', None)},
            ))
        
        return devices
    
    def _get_confidence_level(self, value: float) -> ConfidenceLevel:
        """Конвертировать числовое значение в ConfidenceLevel enum."""
        if value >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif value >= 0.7:
            return ConfidenceLevel.HIGH
        elif value >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif value >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _extract_connections_from_schematic(self, schematic_result: Dict) -> List[Dict]:
        """Извлечь соединения из результата анализа схем."""
        connections = []
        
        if not schematic_result:
            return connections
        
        schematic_data = schematic_result.get('data', {})
        edge_list = schematic_data.get('edges', [])
        
        for edge in edge_list:
            connections.append({
                'from_device_id': edge.get('from_node', ''),
                'to_device_id': edge.get('to_node', ''),
                'connection_type': edge.get('connection_type', 'wire'),
                'confidence': ConfidenceLevel(edge.get('confidence', 0.7)),
            })
        
        return connections
    
    def _merge_devices(
        self,
        nlp_devices: List[Device],
        plan_devices: List[Device],
    ) -> List[Device]:
        """Объединить устройства из разных источников."""
        merged = []
        
        # Простое объединение (в полной версии нужно сопоставление по ID/локации)
        merged.extend(nlp_devices)
        
        # Добавляем устройства с планов которых нет в спецификации
        for plan_device in plan_devices:
            # Проверка на дубликат (упрощенная)
            is_duplicate = False
            for nlp_device in nlp_devices:
                if (nlp_device.device_type == plan_device.device_type and
                    nlp_device.model == plan_device.model):
                    is_duplicate = True
                    # Обновляем информацию о локации
                    if plan_device.room_number:
                        nlp_device.room_number = plan_device.room_number
                    break
            
            if not is_duplicate:
                merged.append(plan_device)
        
        return merged
    
    def _validate_domain_model(self, model: ProjectDomainModel) -> ValidationResult:
        """Валидировать доменную модель."""
        result = ValidationResult(is_valid=True)
        
        # Проверка на дубликаты адресов
        addresses = [d.address for d in model.devices if d.address > 0]
        if len(addresses) != len(set(addresses)):
            result.issues.append("Обнаружены дубликаты адресов устройств")
            result.is_valid = False
        
        # Проверка количества устройств
        if model.total_devices == 0:
            result.issues.append("Не найдено ни одного устройства")
            result.is_valid = False
        
        # Предупреждения
        low_confidence_devices = [
            d for d in model.devices 
            if d.confidence.value < self.confidence_threshold
        ]
        if low_confidence_devices:
            result.warnings.append(
                f"{len(low_confidence_devices)} устройств имеют низкую уверенность распознавания"
            )
        
        # Рекомендации
        if model.total_partitions == 0:
            result.suggestions.append("Рекомендуется создать разделы для группировки устройств")
        
        return result
