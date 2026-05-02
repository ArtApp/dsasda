#!/usr/bin/env python3
"""
Парсер файлов .pprog для извлечения спецификаций и метаданных
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any


class PProgParser:
    """Парсер для файлов формата .pprog"""
    
    def __init__(self):
        self.data = {}
        
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Парсинг одного .pprog файла
        
        Args:
            file_path: Путь к файлу .pprog
            
        Returns:
            Словарь с извлечёнными данными
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        result = {
            'file_name': os.path.basename(file_path),
            'file_path': file_path,
            'metadata': {},
            'specifications': [],
            'devices': [],
            'loops': [],
            'zones': []
        }
        
        # Извлечение метаданных (примерные паттерны)
        result['metadata'] = self._extract_metadata(content)
        
        # Извлечение спецификаций
        result['specifications'] = self._extract_specifications(content)
        
        # Извлечение устройств
        result['devices'] = self._extract_devices(content)
        
        # Извлечение шлейфов
        result['loops'] = self._extract_loops(content)
        
        # Извлечение зон
        result['zones'] = self._extract_zones(content)
        
        return result
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Извлечение метаданных проекта"""
        metadata = {}
        
        # Паттерны для поиска (адаптировать под реальный формат)
        patterns = {
            'project_name': r'Проект[:\s]+(.+?)(?:\n|$)',
            'object_name': r'Объект[:\s]+(.+?)(?:\n|$)',
            'date': r'Дата[:\s]+(\d{2}\.\d{2}\.\d{4})',
            'version': r'Версия[:\s]+([\d\.]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()
        
        return metadata
    
    def _extract_specifications(self, content: str) -> List[Dict[str, Any]]:
        """Извлечение спецификаций оборудования"""
        specifications = []
        
        # Примерный паттерн - адаптировать под реальный формат
        spec_pattern = r'([А-Я]{2,}\d+[А-Я]?)\s*[-:]\s*(.+?)(?:\n|$)'
        
        for match in re.finditer(spec_pattern, content, re.IGNORECASE):
            spec = {
                'code': match.group(1),
                'description': match.group(2).strip(),
                'quantity': 1  # По умолчанию
            }
            
            # Поиск количества
            qty_match = re.search(r'(\d+)\s*[шт\.]', match.group(0))
            if qty_match:
                spec['quantity'] = int(qty_match.group(1))
            
            specifications.append(spec)
        
        return specifications
    
    def _extract_devices(self, content: str) -> List[Dict[str, Any]]:
        """Извлечение информации об устройствах"""
        devices = []
        
        # Паттерн для устройств (адаптировать)
        device_pattern = r'(Датчик|Прибор|Извещатель)[:\s]+(.+?)(?:\n|$)'
        
        for match in re.finditer(device_pattern, content, re.IGNORECASE):
            device = {
                'type': match.group(1),
                'model': match.group(2).strip()
            }
            devices.append(device)
        
        return devices
    
    def _extract_loops(self, content: str) -> List[Dict[str, Any]]:
        """Извлечение информации о шлейфах"""
        loops = []
        
        # Паттерн для шлейфов
        loop_pattern = r'Шлейф[:\s]*(\d+)\s*[-:]\s*(.+?)(?:\n|$)'
        
        for match in re.finditer(loop_pattern, content, re.IGNORECASE):
            loop = {
                'number': int(match.group(1)),
                'description': match.group(2).strip()
            }
            loops.append(loop)
        
        return loops
    
    def _extract_zones(self, content: str) -> List[Dict[str, Any]]:
        """Извлечение информации о зонах"""
        zones = []
        
        # Паттерн для зон
        zone_pattern = r'Зона[:\s]*(\d+)\s*[-:]\s*(.+?)(?:\n|$)'
        
        for match in re.finditer(zone_pattern, content, re.IGNORECASE):
            zone = {
                'number': int(match.group(1)),
                'description': match.group(2).strip()
            }
            zones.append(zone)
        
        return zones
    
    def parse_directory(self, dir_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Парсинг всех .pprog файлов в директории
        
        Args:
            dir_path: Путь к директории с файлами
            output_dir: Директория для сохранения результатов (опционально)
            
        Returns:
            Список результатов парсинга
        """
        results = []
        pprog_files = list(Path(dir_path).rglob('*.pprog'))
        
        print(f"Найдено файлов .pprog: {len(pprog_files)}")
        
        for file_path in pprog_files:
            try:
                result = self.parse_file(str(file_path))
                results.append(result)
                print(f"✓ Обработан: {file_path.name}")
            except Exception as e:
                print(f"✗ Ошибка при обработке {file_path.name}: {e}")
        
        # Сохранение результатов
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # Сохранение общего JSON
            output_file = os.path.join(output_dir, 'parsed_pprog.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"Результаты сохранены в: {output_file}")
            
            # Сохранение индивидуальных файлов
            for result in results:
                individual_file = os.path.join(
                    output_dir, 
                    f"{Path(result['file_name']).stem}_parsed.json"
                )
                with open(individual_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
        
        return results


def main():
    """Точка входа для запуска парсера"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Парсер файлов .pprog')
    parser.add_argument(
        'input',
        help='Путь к файлу или директории с .pprog файлами'
    )
    parser.add_argument(
        '-o', '--output',
        help='Директория для сохранения результатов',
        default='./processed/pprog_parsed'
    )
    
    args = parser.parse_args()
    
    pprog_parser = PProgParser()
    
    if os.path.isfile(args.input):
        result = pprog_parser.parse_file(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif os.path.isdir(args.input):
        pprog_parser.parse_directory(args.input, args.output)
    else:
        print(f"Ошибка: путь не найден - {args.input}")


if __name__ == '__main__':
    main()
