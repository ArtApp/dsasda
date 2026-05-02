"""
Базовый класс для всех ИИ-инструментов.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ToolStatus(str, Enum):
    """Статус выполнения инструмента."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Частичный успех


@dataclass
class ToolResult:
    """Результат выполнения ИИ-инструмента."""
    tool_name: str
    status: ToolStatus
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0
    confidence: float = 1.0
    
    def is_success(self) -> bool:
        """Проверка успешности выполнения."""
        return self.status in [ToolStatus.SUCCESS, ToolStatus.PARTIAL]
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'tool_name': self.tool_name,
            'status': self.status.value,
            'data': self.data,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'execution_time_ms': self.execution_time_ms,
            'confidence': self.confidence,
        }


class AITool(ABC):
    """
    Базовый абстрактный класс для всех ИИ-инструментов.
    Каждый инструмент реализует конкретную функцию в конвейере обработки.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self._is_initialized = False
    
    @abstractmethod
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить инструмент.
        
        Args:
            input_data: Входные данные для инструмента
            
        Returns:
            ToolResult с результатами выполнения
        """
        pass
    
    def initialize(self) -> bool:
        """
        Инициализировать инструмент (загрузить модели, проверить зависимости).
        
        Returns:
            True если инициализация успешна
        """
        self._is_initialized = True
        return True
    
    def create_result(self, status: ToolStatus = ToolStatus.SUCCESS, **kwargs) -> ToolResult:
        """
        Создать результат выполнения инструмента.
        
        Args:
            status: Статус выполнения (по умолчанию SUCCESS)
            **kwargs: Параметры для ToolResult
            
        Returns:
            ToolResult с заданными параметрами
        """
        return ToolResult(tool_name=self.name, status=status, **kwargs)
    
    @property
    def is_initialized(self) -> bool:
        """Проверка инициализации инструмента."""
        return self._is_initialized
    
    def _initialize(self):
        """Внутренний метод инициализации (переопределяется в подклассах)."""
        pass
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Проверить входные данные.
        
        Args:
            input_data: Входные данные
            
        Returns:
            True если данные валидны
        """
        return input_data is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Получить информацию об инструменте."""
        return {
            'name': self.name,
            'config': self.config,
            'is_initialized': self._is_initialized,
            'description': self.__doc__,
        }
