"""
Module: Data Labeling Assistant & Synthetic Data Generator
Purpose: Implements Stage 3 of the plan - creating datasets for training CV/NLP models.
Features:
    - Synthetic Plan/Schematic generation (for bootstrapping).
    - Export to Label Studio / COCO / YOLO formats.
    - Pre-labeling assistance using existing tools.
"""

import json
import os
import random
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ..models.domain import Device, DeviceType, Connection


@dataclass
class SyntheticDevice:
    """Represents a device in a synthetic image."""
    id: str
    type: DeviceType
    x: int
    y: int
    width: int
    height: int
    label: str  # Text label to render (e.g., "ДИП-34А")
    room: str


class SyntheticDataGenerator:
    """
    Generates synthetic floor plans and schematics for training CV models.
    Helps bootstrap the dataset when real labeled data is scarce.
    """

    # Visual representations for device types (simplified shapes)
    DEVICE_SHAPES = {
        DeviceType.SMOKE_DETECTOR: "circle",
        DeviceType.HEAT_DETECTOR: "square",
        DeviceType.MANUAL_CALL_POINT: "triangle",
        DeviceType.CONTROL_PANEL: "rectangle_large",
        DeviceType.SOUNDER: "hexagon",
        DeviceType.INPUT_MODULE: "diamond",
        DeviceType.OUTPUT_MODULE: "pentagon"
    }

    COLORS = {
        DeviceType.SMOKE_DETECTOR: (255, 0, 0),      # Red
        DeviceType.HEAT_DETECTOR: (255, 165, 0),    # Orange
        DeviceType.MANUAL_CALL_POINT: (0, 0, 255),  # Blue
        DeviceType.CONTROL_PANEL: (0, 128, 0),      # Green
        DeviceType.SOUNDER: (128, 0, 128),          # Purple
        DeviceType.INPUT_MODULE: (0, 255, 255),     # Cyan
        DeviceType.OUTPUT_MODULE: (255, 255, 0),    # Yellow
    }

    def __init__(self, image_size: Tuple[int, int] = (1024, 768)):
        self.image_size = image_size
        self.font = self._load_font()

    def _load_font(self, size: int = 14):
        """Loads a font for rendering text. Falls back to default if not found."""
        try:
            # Try common Linux fonts
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except IOError:
            try:
                return ImageFont.truetype("arial.ttf", size)
            except IOError:
                return ImageFont.load_default()

    def generate_floor_plan(
        self, 
        num_devices: int = 20, 
        num_rooms: int = 5,
        output_path: Optional[str] = None
    ) -> Tuple[Image.Image, List[SyntheticDevice], Dict]:
        """
        Generates a synthetic floor plan image with devices and rooms.
        
        Returns:
            - PIL Image
            - List of SyntheticDevice objects (Ground Truth)
            - Annotation dict (COCO-like format)
        """
        img = Image.new('RGB', self.image_size, color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        devices = []
        annotations = {
            "images": [{"id": 1, "width": self.image_size[0], "height": self.image_size[1]}],
            "annotations": [],
            "categories": []
        }
        
        # Generate Rooms (simple rectangles)
        room_colors = [(200, 200, 200), (210, 210, 210), (220, 220, 220)]
        for i in range(num_rooms):
            x = random.randint(0, self.image_size[0] // 2)
            y = random.randint(0, self.image_size[1] // 2)
            w = random.randint(100, 300)
            h = random.randint(100, 200)
            
            # Ensure within bounds
            w = min(w, self.image_size[0] - x)
            h = min(h, self.image_size[1] - y)
            
            draw.rectangle([x, y, x + w, y + h], outline=(100, 100, 100), width=2, fill=random.choice(room_colors))
            
            # Room Number
            room_name = f"{100 + i}"
            draw.text((x + 10, y + 10), room_name, fill=(50, 50, 50), font=self.font)

        # Generate Devices
        cat_id_map = {}
        current_cat_id = 1
        
        for i in range(num_devices):
            dtype = random.choice(list(DeviceType))
            shape = self.DEVICE_SHAPES.get(dtype, "circle")
            color = self.COLORS.get(dtype, (0, 0, 0))
            
            size = random.randint(15, 25)
            x = random.randint(20, self.image_size[0] - 20)
            y = random.randint(20, self.image_size[1] - 20)
            
            # Draw Shape
            if shape == "circle":
                draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], outline=color, width=2)
            elif shape == "square":
                draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], outline=color, width=2)
            elif shape == "triangle":
                pts = [(x, y-size//2), (x-size//2, y+size//2), (x+size//2, y+size//2)]
                draw.polygon(pts, outline=color, width=2)
            else:
                draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], outline=color, width=2)

            # Label
            label = f"D{i+1}"
            draw.text((x+10, y-10), label, fill=(0, 0, 0), font=self.font)
            
            # Create Ground Truth Object
            dev = SyntheticDevice(
                id=f"DEV_{i+1:03d}",
                type=dtype,
                x=x,
                y=y,
                width=size,
                height=size,
                label=label,
                room=f"{100 + random.randint(0, num_rooms-1)}"
            )
            devices.append(dev)
            
            # COCO Annotation
            if dtype.name not in cat_id_map:
                cat_id_map[dtype.name] = current_cat_id
                annotations["categories"].append({
                    "id": current_cat_id,
                    "name": dtype.name,
                    "supercategory": "fire_safety"
                })
                current_cat_id += 1
            
            ann = {
                "id": len(annotations["annotations"]) + 1,
                "image_id": 1,
                "category_id": cat_id_map[dtype.name],
                "bbox": [x - size//2, y - size//2, size, size],
                "area": size * size,
                "iscrowd": 0,
                "attributes": {"label": label, "room": dev.room}
            }
            annotations["annotations"].append(ann)

        if output_path:
            img.save(output_path)
            # Save annotations
            ann_path = output_path.replace(".png", "_annotations.json").replace(".jpg", "_annotations.json")
            with open(ann_path, 'w') as f:
                json.dump(annotations, f, indent=2)
            print(f"Generated synthetic plan: {output_path} and annotations: {ann_path}")

        return img, devices, annotations

    def generate_schematic(
        self,
        num_devices: int = 10,
        output_path: Optional[str] = None
    ) -> Tuple[Image.Image, List[Connection], Dict]:
        """
        Generates a synthetic wiring schematic (graph structure).
        """
        img = Image.new('RGB', self.image_size, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        devices = []
        connections = []
        
        # Place devices in a line or grid
        spacing_x = self.image_size[0] // (num_devices + 1)
        y_base = self.image_size[1] // 2
        
        for i in range(num_devices):
            x = (i + 1) * spacing_x
            y = y_base + random.randint(-50, 50)
            
            dtype = DeviceType.SMOKE_DETECTOR if i < num_devices - 1 else DeviceType.CONTROL_PANEL
            color = self.COLORS.get(dtype, (0, 0, 0))
            
            # Draw terminal block symbol
            size = 30
            draw.rectangle([x-15, y-15, x+15, y+15], outline=color, width=2, fill=(255,255,255))
            draw.text((x-10, y-5), f"T{i+1}", fill=(0,0,0), font=self.font)
            
            dev = SyntheticDevice(
                id=f"TERM_{i+1}",
                type=dtype,
                x=x, y=y, width=size, height=size,
                label=f"T{i+1}",
                room="N/A"
            )
            devices.append(dev)
            
            # Connect to previous
            if i > 0:
                prev = devices[i-1]
                conn = Connection(
                    from_device_id=prev.id,
                    to_device_id=dev.id,
                    connection_type="RS485", # Or Signal Line
                    channel=i
                )
                connections.append(conn)
                
                # Draw line
                draw.line([(prev.x, prev.y), (x, y)], fill=(0, 0, 0), width=2)

        if output_path:
            img.save(output_path)
            # Save graph structure
            graph_path = output_path.replace(".png", "_graph.json")
            # Convert dataclasses to dicts properly
            graph_data = {
                "nodes": [asdict(d) for d in devices],
                "edges": [asdict(c) for c in connections]
            }
            with open(graph_path, 'w') as f:
                json.dump(graph_data, f, indent=2, default=str)
            print(f"Generated synthetic schematic: {output_path} and graph: {graph_path}")

        return img, connections, {"nodes": devices, "edges": connections}


class LabelStudioExporter:
    """
    Converts internal annotation formats to Label Studio JSON format.
    Allows engineers to review and correct AI pre-labels.
    """
    
    @staticmethod
    def export_object_detection(
        image_path: str, 
        annotations: Dict, 
        output_json: str
    ):
        """
        Exports COCO-like annotations to Label Studio format.
        """
        tasks = []
        
        # Map category IDs to names
        cat_map = {c['id']: c['name'] for c in annotations.get('categories', [])}
        
        task = {
            "data": {"image": image_path},
            "predictions": [{
                "result": []
            }]
        }
        
        for ann in annotations.get('annotations', []):
            bbox = ann['bbox'] # x, y, w, h
            label_name = cat_map.get(ann['category_id'], "unknown")
            
            result_item = {
                "original_width": annotations['images'][0]['width'],
                "original_height": annotations['images'][0]['height'],
                "image_rotation": 0,
                "value": {
                    "x": bbox[0],
                    "y": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3],
                    "rotation": 0,
                    "labels": [label_name]
                },
                "id": str(ann['id']),
                "from_name": "label",
                "to_name": "image",
                "type": "rectanglelabels",
                "origin": "manual" # or "prediction"
            }
            task["predictions"][0]["result"].append(result_item)
            
        tasks.append(task)
        
        with open(output_json, 'w') as f:
            json.dump(tasks, f, indent=2)
        print(f"Exported Label Studio task to: {output_json}")

    @staticmethod
    def export_graph_annotation(
        image_path: str,
        nodes: List[Dict],
        edges: List[Dict],
        output_json: str
    ):
        """
        Exports schematic graph data to a format suitable for relation labeling.
        Note: Label Studio requires custom configuration for relations.
        This exports a simplified version focusing on node detection first.
        """
        # Implementation similar to object detection but focused on terminals
        # Relations can be added via Label Studio's "Relations" feature
        pass
