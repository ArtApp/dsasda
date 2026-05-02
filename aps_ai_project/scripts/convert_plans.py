#!/usr/bin/env python3
"""
Конвертер планов из PDF в изображения для последующей разметки
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import subprocess


class PlanConverter:
    """Конвертер планов из различных форматов в изображения"""
    
    def __init__(self, output_dir: str = './data/processed/plans'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def convert_pdf_to_png(
        self, 
        pdf_path: str, 
        dpi: int = 300,
        output_prefix: Optional[str] = None
    ) -> List[str]:
        """
        Конвертация PDF в PNG
        
        Args:
            pdf_path: Путь к PDF файлу
            dpi: Разрешение в точках на дюйм
            output_prefix: Префикс для выходных файлов
            
        Returns:
            Список путей к созданным файлам
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")
        
        # Проверка наличия poppler-utils (pdftoppm)
        try:
            subprocess.run(['pdftoppm', '-h'], 
                         capture_output=True, check=False)
        except FileNotFoundError:
            print("⚠ pdftoppm не найден. Установите poppler-utils:")
            print("  Ubuntu/Debian: sudo apt-get install poppler-utils")
            print("  macOS: brew install poppler")
            return []
        
        pdf_name = Path(pdf_path).stem
        prefix = output_prefix or pdf_name
        
        output_pattern = os.path.join(self.output_dir, f"{prefix}_page")
        
        cmd = [
            'pdftoppm',
            '-png',
            '-r', str(dpi),
            pdf_path,
            output_pattern
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Ошибка конвертации: {result.stderr}")
                return []
            
            # Поиск созданных файлов
            output_files = []
            for f in os.listdir(self.output_dir):
                if f.startswith(prefix) and f.endswith('.png'):
                    output_files.append(os.path.join(self.output_dir, f))
            
            print(f"✓ Конвертировано страниц: {len(output_files)}")
            return sorted(output_files)
            
        except Exception as e:
            print(f"✗ Ошибка при конвертации: {e}")
            return []
    
    def convert_directory(
        self, 
        input_dir: str, 
        dpi: int = 300
    ) -> dict:
        """
        Конвертация всех PDF в директории
        
        Args:
            input_dir: Директория с PDF файлами
            dpi: Разрешение
            
        Returns:
            Словарь со статистикой конвертации
        """
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Директория не найдена: {input_dir}")
        
        pdf_files = list(Path(input_dir).rglob('*.pdf'))
        
        stats = {
            'total': len(pdf_files),
            'success': 0,
            'failed': 0,
            'pages': 0,
            'files': []
        }
        
        print(f"Найдено PDF файлов: {len(pdf_files)}")
        
        for pdf_path in pdf_files:
            print(f"\nОбработка: {pdf_path.name}")
            try:
                converted = self.convert_pdf_to_png(
                    str(pdf_path), 
                    dpi=dpi
                )
                if converted:
                    stats['success'] += 1
                    stats['pages'] += len(converted)
                    stats['files'].extend(converted)
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"✗ Ошибка: {e}")
                stats['failed'] += 1
        
        print(f"\n{'='*50}")
        print(f"Всего файлов: {stats['total']}")
        print(f"Успешно: {stats['success']}")
        print(f"Неудачно: {stats['failed']}")
        print(f"Всего страниц: {stats['pages']}")
        
        return stats
    
    def normalize_image(
        self, 
        image_path: str,
        target_size: tuple = None,
        remove_noise: bool = True
    ) -> str:
        """
        Нормализация изображения плана
        
        Args:
            image_path: Путь к изображению
            target_size: Целевой размер (width, height)
            remove_noise: Удалять шум
            
        Returns:
            Путь к нормализованному изображению
        """
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            
            img = Image.open(image_path)
            
            # Конвертация в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменение размера если указано
            if target_size:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Удаление шума
            if remove_noise:
                img = img.filter(ImageFilter.MedianFilter(size=3))
            
            # Улучшение контраста
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Сохранение
            base_name = Path(image_path).stem
            output_path = os.path.join(
                self.output_dir, 
                f"{base_name}_normalized.png"
            )
            img.save(output_path, 'PNG', optimize=True)
            
            print(f"✓ Нормализовано: {Path(image_path).name}")
            return output_path
            
        except ImportError:
            print("⚠ PIL/Pillow не установлен: pip install Pillow")
            return image_path
        except Exception as e:
            print(f"✗ Ошибка нормализации: {e}")
            return image_path


def main():
    """Точка входа для конвертера"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Конвертер планов АПС')
    parser.add_argument(
        'input',
        help='Путь к файлу PDF или директории с PDF'
    )
    parser.add_argument(
        '-o', '--output',
        help='Директория для сохранения изображений',
        default='./data/processed/plans'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Разрешение конвертации (по умолчанию 300)'
    )
    parser.add_argument(
        '--normalize',
        action='store_true',
        help='Нормализовать изображения после конвертации'
    )
    
    args = parser.parse_args()
    
    converter = PlanConverter(output_dir=args.output)
    
    if os.path.isfile(args.input):
        if args.input.lower().endswith('.pdf'):
            converted = converter.convert_pdf_to_png(
                args.input, 
                dpi=args.dpi
            )
            if converted and args.normalize:
                for img_path in converted:
                    converter.normalize_image(img_path)
        else:
            print("Поддерживаются только PDF файлы")
    elif os.path.isdir(args.input):
        stats = converter.convert_directory(args.input, dpi=args.dpi)
        
        if args.normalize and stats['files']:
            print("\nНормализация изображений...")
            for img_path in stats['files']:
                converter.normalize_image(img_path)
    else:
        print(f"Ошибка: путь не найден - {args.input}")


if __name__ == '__main__':
    main()
