"""
CV Schematic Analyzer - ИИ-инструмент для анализа электрических схем.
Этап 2: Разработка и Тестирование Прототипов ИИ-инструментов

Преобразует схему в граф (вершины - устройства, рёбра - соединения).
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

from orchestrator.tools.base_tool import AITool, ToolResult, ToolStatus
from orchestrator.models.domain import Connection, ConfidenceLevel

logger = logging.getLogger(__name__)


class CVSchematicAnalyzer(AITool):
    """
    ИИ-инструмент для анализа электрических схем подключения.
    
    Функции:
    - Детекция символов устройств на схемах
    - Детекция линий/узлов соединений
    - Преобразование схемы в граф
    - Анализ сложных соединений (пересечения без соединения)
    - Вывод графа подключений в JSON
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("CVSchematicAnalyzer", config)
        
        # Lazy imports
        self._cv2 = None
        self._nx = None  # networkx для работы с графами
    
    def _initialize(self):
        """Инициализация."""
        try:
            import cv2
            self._cv2 = cv2
            logger.info("OpenCV initialized")
        except ImportError:
            logger.warning("OpenCV not available")
        
        try:
            import networkx as nx
            self._nx = nx
            logger.info("NetworkX initialized")
        except ImportError:
            logger.warning("NetworkX not available")
    
    def execute(self, input_data: Any) -> ToolResult:
        """
        Выполнить анализ схемы.
        
        Args:
            input_data: Путь к изображению схемы или dict с данными
            
        Returns:
            ToolResult с графом подключений
        """
        start_time = time.time()
        
        try:
            # Обработка входных данных
            if isinstance(input_data, str):
                image_path = Path(input_data)
            elif isinstance(input_data, dict) and 'image_path' in input_data:
                image_path = Path(input_data['image_path'])
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=["Invalid input data. Expected image path."],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            if not image_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    errors=[f"Image not found: {image_path}"],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Анализ схемы
            graph_data = self._analyze_schematic(image_path)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if graph_data else ToolStatus.PARTIAL,
                data=graph_data,
                metadata={
                    'nodes': len(graph_data.get('nodes', [])),
                    'edges': len(graph_data.get('edges', [])),
                },
                execution_time_ms=execution_time,
                confidence=0.7,
            )
            
        except Exception as e:
            logger.exception(f"Error in CVSchematicAnalyzer: {e}")
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                errors=[str(e)],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _analyze_schematic(self, image_path: Path) -> Dict[str, Any]:
        """Анализ изображения схемы."""
        graph_data = {
            'nodes': [],
            'edges': [],
            'metadata': {
                'source': str(image_path),
            }
        }
        
        if not self._cv2:
            logger.warning("OpenCV not available, skipping schematic analysis")
            return graph_data
        
        # Чтение изображения
        img = self._cv2.imread(str(image_path))
        if img is None:
            return graph_data
        
        # Детекция линий (проводов)
        lines = self._detect_lines(img)
        
        # Детекция узлов (устройств)
        nodes = self._detect_nodes(img)
        
        # Построение графа соединений
        edges = self._build_connection_graph(nodes, lines)
        
        graph_data['nodes'] = nodes
        graph_data['edges'] = edges
        
        return graph_data
    
    def _detect_lines(self, img) -> List[Dict[str, Any]]:
        """Детектировать линии соединений."""
        lines = []
        
        # Конвертация в оттенки серого
        gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)
        
        # Детекция краев
        edges = self._cv2.Canny(gray, 50, 150)
        
        # Детекция линий через Hough Transform
        line_segments = self._cv2.HoughLinesP(
            edges,
            rho=1,
            theta=3.14159/180,
            threshold=50,
            minLineLength=30,
            maxLineGap=10
        )
        
        if line_segments is not None:
            for segment in line_segments:
                x1, y1, x2, y2 = segment[0]
                lines.append({
                    'type': 'line',
                    'start': (int(x1), int(y1)),
                    'end': (int(x2), int(y2)),
                })
        
        return lines
    
    def _detect_nodes(self, img) -> List[Dict[str, Any]]:
        """Детектировать узлы (устройства) на схеме."""
        nodes = []
        
        # Простая эвристика: поиск прямоугольных областей
        gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)
        
        # Бинаризация
        _, thresh = self._cv2.threshold(gray, 200, 255, self._cv2.THRESH_BINARY_INV)
        
        # Поиск контуров
        contours, _ = self._cv2.findContours(
            thresh,
            self._cv2.RETR_EXTERNAL,
            self._cv2.CHAIN_APPROX_SIMPLE
        )
        
        node_id = 0
        for contour in contours:
            area = self._cv2.contourArea(contour)
            # Фильтрация по размеру
            if 500 < area < 50000:
                x, y, w, h = self._cv2.boundingRect(contour)
                nodes.append({
                    'id': f'node_{node_id}',
                    'type': 'device',
                    'bbox': (x, y, w, h),
                    'center': (x + w//2, y + h//2),
                })
                node_id += 1
        
        return nodes
    
    def _build_connection_graph(
        self,
        nodes: List[Dict],
        lines: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Построить граф соединений из узлов и линий."""
        edges = []
        
        # Простая эвристика: линия соединяет узлы если её концы близко к центрам узлов
        tolerance = 30  # пикселей
        
        for line in lines:
            start = line['start']
            end = line['end']
            
            # Поиск ближайших узлов
            start_node = self._find_nearest_node(start, nodes, tolerance)
            end_node = self._find_nearest_node(end, nodes, tolerance)
            
            if start_node and end_node and start_node != end_node:
                edges.append({
                    'from_node': start_node['id'],
                    'to_node': end_node['id'],
                    'connection_type': 'wire',
                    'confidence': ConfidenceLevel.MEDIUM.value,
                })
        
        return edges
    
    def _find_nearest_node(
        self,
        point: tuple,
        nodes: List[Dict],
        tolerance: int,
    ) -> Optional[Dict]:
        """Найти ближайший узел к точке."""
        min_dist = float('inf')
        nearest = None
        
        for node in nodes:
            center = node['center']
            dist = ((point[0] - center[0])**2 + (point[1] - center[1])**2)**0.5
            if dist < min_dist and dist <= tolerance:
                min_dist = dist
                nearest = node
        
        return nearest
