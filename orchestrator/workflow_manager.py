"""
Workflow Manager - Оркестратор для управления конвейером ИИ-инструментов.
Этап 0: Подготовка и Интеграция ИИ-Инструментов

Управляет вызовами всех ИИ-инструментов, передает данные между ними
и обрабатывает логику принятия решений.
"""

import logging
import time
import uuid
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from datetime import datetime

from orchestrator.models.workflow import WorkflowState, WorkflowStatus
from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    ИИ-оркестратор для управления конвейером обработки проектной документации.
    
    Отвечает за:
    - Управление последовательностью выполнения инструментов
    - Передачу данных между инструментами
    - Обработку ошибок и неопределенности
    - Логирование и мониторинг выполнения
    - Генерацию отчетов о выполнении workflow
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tools: Dict[str, AITool] = {}
        self.workflows: Dict[str, WorkflowState] = {}
        self.logger = logging.getLogger(f"{__name__}.WorkflowManager")
        
        # Настройки
        self.max_retries = self.config.get('max_retries', 3)
        self.stop_on_error = self.config.get('stop_on_error', False)
        self.verbose = self.config.get('verbose', True)
    
    def register_tool(self, tool: AITool):
        """
        Зарегистрировать ИИ-инструмент в оркестраторе.
        
        Args:
            tool: Экземпляр инструмента, наследующий AITool
        """
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Отменить регистрацию инструмента."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[AITool]:
        """Получить инструмент по имени."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """Получить список зарегистрированных инструментов."""
        return list(self.tools.keys())
    
    def execute_workflow(
        self,
        workflow_id: Optional[str] = None,
        input_data: Any = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkflowState:
        """
        Выполнить workflow - последовательность шагов с использованием ИИ-инструментов.
        
        Args:
            workflow_id: Уникальный идентификатор workflow (генерируется если не указан)
            input_data: Входные данные для workflow
            steps: Список шагов выполнения. Каждый шаг это dict:
                   {
                       'tool': 'ToolName',
                       'method': 'execute',  # опционально, по умолчанию 'execute'
                       'input_mapper': lambda x: x,  # опционально, функция преобразования входа
                       'output_mapper': lambda x: x,  # опционально, функция преобразования выхода
                       'on_error': 'continue|skip|abort',  # опционально
                       'condition': lambda ctx: True,  # опционально, условие выполнения
                   }
        
        Returns:
            WorkflowState с результатами выполнения
        """
        workflow_id = workflow_id or str(uuid.uuid4())
        state = WorkflowState(workflow_id)
        self.workflows[workflow_id] = state
        
        # Шаги по умолчанию - полный конвейер
        if steps is None:
            steps = self._get_default_pipeline()
        
        self.logger.info(f"Starting workflow {workflow_id} with {len(steps)} steps")
        state.start()
        
        context = {
            'input': input_data,
            'outputs': {},
            'current_step': 0,
            'total_steps': len(steps),
        }
        
        try:
            for step_idx, step_config in enumerate(steps):
                step_name = step_config.get('name', f"step_{step_idx}")
                tool_name = step_config['tool']
                
                state.current_step = step_name
                context['current_step'] = step_idx
                
                # Проверка условия выполнения
                condition = step_config.get('condition', lambda ctx: True)
                if not condition(context):
                    self.logger.info(f"Skipping step {step_name}: condition not met")
                    state.complete_step(step_name)
                    continue
                
                # Получение инструмента
                tool = self.tools.get(tool_name)
                if not tool:
                    error_msg = f"Tool not found: {tool_name}"
                    self._handle_step_error(state, step_name, error_msg, step_config)
                    if state.status == WorkflowStatus.FAILED:
                        break
                    continue
                
                # Инициализация инструмента
                if not tool.is_initialized:
                    if not tool.initialize():
                        error_msg = f"Failed to initialize tool: {tool_name}"
                        self._handle_step_error(state, step_name, error_msg, step_config)
                        if state.status == WorkflowStatus.FAILED:
                            break
                        continue
                
                # Подготовка входных данных
                input_mapper = step_config.get('input_mapper', lambda ctx: ctx.get('input'))
                try:
                    step_input = input_mapper(context)
                except Exception as e:
                    error_msg = f"Input mapping failed for step {step_name}: {e}"
                    self._handle_step_error(state, step_name, error_msg, step_config)
                    if state.status == WorkflowStatus.FAILED:
                        break
                    continue
                
                # Выполнение инструмента
                self.logger.info(f"Executing step {step_name} with tool {tool_name}")
                method_name = step_config.get('method', 'execute')
                method = getattr(tool, method_name, None)
                
                if not callable(method):
                    error_msg = f"Method {method_name} not found on tool {tool_name}"
                    self._handle_step_error(state, step_name, error_msg, step_config)
                    if state.status == WorkflowStatus.FAILED:
                        break
                    continue
                
                # Попытка выполнения с retry
                result = self._execute_with_retry(method, step_input, step_name, step_config)
                
                # Обработка результата
                if result.is_success():
                    output_mapper = step_config.get('output_mapper', lambda r: r.data)
                    try:
                        step_output = output_mapper(result)
                        context['outputs'][step_name] = step_output
                        # Обновляем input для следующего шага
                        context['input'] = step_output
                    except Exception as e:
                        error_msg = f"Output mapping failed for step {step_name}: {e}"
                        self._handle_step_error(state, step_name, error_msg, step_config)
                        if state.status == WorkflowStatus.FAILED:
                            break
                        continue
                    
                    state.complete_step(step_name)
                    self.logger.info(f"Step {step_name} completed successfully")
                    
                    # Добавление предупреждений из результата
                    for warning in result.warnings:
                        state.warn(f"{step_name}: {warning}")
                else:
                    error_msg = f"Tool execution failed: {result.errors}"
                    self._handle_step_error(state, step_name, error_msg, step_config)
                    if state.status == WorkflowStatus.FAILED:
                        break
            
            # Завершение workflow
            if state.status != WorkflowStatus.FAILED:
                state.complete()
                self.logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            self.logger.exception(f"Workflow {workflow_id} failed with exception: {e}")
            state.fail(str(e))
        
        return state
    
    def _execute_with_retry(
        self,
        method: Callable,
        input_data: Any,
        step_name: str,
        step_config: Dict[str, Any],
    ) -> ToolResult:
        """Выполнить метод с повторными попытками."""
        retries = 0
        max_retries = step_config.get('max_retries', self.max_retries)
        last_result = None
        
        while retries <= max_retries:
            try:
                result = method(input_data)
                last_result = result
                
                if result.is_success():
                    return result
                
                # Если частичный успех - возвращаем сразу
                if result.status == ToolStatus.PARTIAL:
                    return result
                
                retries += 1
                if retries <= max_retries:
                    self.logger.warning(
                        f"Step {step_name} failed, retry {retries}/{max_retries}"
                    )
                    time.sleep(0.5 * retries)  # Exponential backoff
                    
            except Exception as e:
                self.logger.exception(f"Step {step_name} exception: {e}")
                retries += 1
                if retries <= max_retries:
                    time.sleep(0.5 * retries)
        
        # Возвращаем последний результат или создаем ошибку
        if last_result:
            return last_result
        return ToolResult(
            tool_name=step_name,
            status=ToolStatus.FAILED,
            errors=[f"Failed after {max_retries} retries"],
        )
    
    def _handle_step_error(
        self,
        state: WorkflowState,
        step_name: str,
        error: str,
        step_config: Dict[str, Any],
    ):
        """Обработать ошибку шага."""
        on_error = step_config.get('on_error', 'continue' if not self.stop_on_error else 'abort')
        
        self.logger.error(f"Step {step_name} error: {error}")
        
        if on_error == 'abort':
            state.fail_step(step_name, error)
            state.fail(error)
        elif on_error == 'skip':
            state.fail_step(step_name, error)
            # Продолжаем выполнение
        else:  # continue
            state.fail_step(step_name, error)
            state.warn(f"Step {step_name} failed but continuing: {error}")
    
    def _get_default_pipeline(self) -> List[Dict[str, Any]]:
        """
        Получить конвейер по умолчанию.
        Может быть переопределен в подклассах или через конфигурацию.
        """
        return self.config.get('default_pipeline', [
            {'tool': 'DocumentAnalyzer', 'name': 'analyze_documents'},
            {'tool': 'NLPSpecExtractor', 'name': 'extract_specs'},
            {'tool': 'CVPlanAnalyzer', 'name': 'analyze_plans'},
            {'tool': 'CVSchematicAnalyzer', 'name': 'analyze_schematics'},
            {'tool': 'DataSynthesizer', 'name': 'synthesize_data'},
            {'tool': 'ConfigGenerator', 'name': 'generate_config'},
            {'tool': 'ReportGenerator', 'name': 'generate_report'},
        ])
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowState]:
        """Получить статус workflow."""
        return self.workflows.get(workflow_id)
    
    def get_all_workflows(self) -> Dict[str, WorkflowState]:
        """Получить все workflow."""
        return self.workflows
    
    def create_custom_pipeline(
        self,
        pipeline_config: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Создать пользовательский конвейер из конфигурации.
        
        Args:
            pipeline_config: Конфигурация конвейера
            
        Returns:
            Список шагов конвейера
        """
        # Валидация конфигурации
        for step in pipeline_config:
            if 'tool' not in step:
                raise ValueError(f"Step missing 'tool' field: {step}")
            
            tool_name = step['tool']
            if tool_name not in self.tools:
                self.logger.warning(f"Tool {tool_name} not registered")
        
        return pipeline_config
