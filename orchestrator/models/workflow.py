"""
Модели дляorchestrator workflow.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class WorkflowStatus(str, Enum):
    """Статус выполнения workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class WorkflowState:
    """Состояние выполнения workflow."""
    
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.status = WorkflowStatus.PENDING
        self.current_step: Optional[str] = None
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def start(self):
        """Начать выполнение workflow."""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete_step(self, step_name: str):
        """Отметить шаг как выполненный."""
        self.completed_steps.append(step_name)
        if self.current_step == step_name:
            self.current_step = None
    
    def fail_step(self, step_name: str, error: str):
        """Отметить шаг как неудачный."""
        self.failed_steps.append(step_name)
        self.errors.append(f"Step {step_name}: {error}")
        if self.current_step == step_name:
            self.current_step = None
    
    def warn(self, warning: str):
        """Добавить предупреждение."""
        self.warnings.append(warning)
    
    def complete(self):
        """Завершить workflow успешно."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def fail(self, error: str):
        """Завершить workflow с ошибкой."""
        self.status = WorkflowStatus.FAILED
        self.errors.append(error)
        self.completed_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'workflow_id': self.workflow_id,
            'status': self.status.value,
            'current_step': self.current_step,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'context': self.context,
            'errors': self.errors,
            'warnings': self.warnings,
        }
