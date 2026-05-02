#!/usr/bin/env python3
"""
Генератор синтетических тестовых данных для AI Orchestrator.
Создает реалистичные спецификации, планы и схемы АПС для тестирования.
"""

import json
import random
from pathlib import Path
from datetime import datetime


def generate_specification_text():
    """Генерирует текст спецификации оборудования АПС."""
    
    devices = [
        # Приборы контроля
        {"type": "ПК", "model": "С2000-М", "desc": "Прибор приемно-контрольный"},
        {"type": "ПК", "model": "С2000-КДЛ", "desc": "Контроллер двухпроводной линии связи"},
        {"type": "ПК", "model": "С2000-БИ", "desc": "Блок индикации"},
        {"type": "ПК", "model": "С2000-4Б", "desc": "Блок четырехрелейный"},
        
        # Извещатели
        {"type": "ДИП", "model": "ДИП-34А", "desc": "Извещатель дымовой оптический"},
        {"type": "ДИП", "model": "ДИП-34СУ", "desc": "Извещатель дымовой с установкой в стену"},
        {"type": "ИПР", "model": "ИПР-513-3А", "desc": "Извещатель пожарный ручной"},
        {"type": "ИПТ", "model": "ИПТ-34", "desc": "Извещатель пламени"},
        
        # Оповещатели
        {"type": "ОС", "model": "С2000-СП1", "desc": "Оповещатель световой"},
        {"type": "ОЗ", "model": "С2000-ЗВ", "desc": "Оповещатель звуковой"},
        
        # Модули
        {"type": "МШС", "model": "С2000-МШС", "desc": "Модуль шлейфа расширенный"},
        {"type": "АРМ", "model": "АРМ Орион Про", "desc": "Автоматизированное рабочее место"},
    ]
    
    locations = [
        "1 этаж, коридор", "1 этаж, помещение 101", "1 этаж, помещение 102",
        "2 этаж, коридор", "2 этаж, помещение 201", "2 этаж, помещение 202",
        "3 этаж, серверная", "3 этаж, архив", "Подвал, насосная",
        "Чердак, вентиляция"
    ]
    
    spec_lines = []
    spec_lines.append("=" * 80)
    spec_lines.append("СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ АВТОМАТИЧЕСКОЙ ПОЖАРНОЙ СИГНАЛИЗАЦИИ (АПС)")
    spec_lines.append("=" * 80)
    spec_lines.append(f"Проект: Офисное здание 'Бизнес-Центр', г. Москва")
    spec_lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y')}")
    spec_lines.append(f"Раздел: Технические средства пожарной автоматики")
    spec_lines.append("")
    spec_lines.append("-" * 80)
    spec_lines.append("№ п/п | Наименование | Тип | Модель | Кол-во | Примечание")
    spec_lines.append("-" * 80)
    
    total_devices = {}
    item_num = 1
    
    for device in devices:
        qty = random.randint(2, 15)
        note = f"{device['desc']}, исполнение: стандартное"
        line = f"{item_num:5d} | {device['type']:15s} | {device['model']:12s} | {qty:6d} | {note}"
        spec_lines.append(line)
        
        if device['type'] not in total_devices:
            total_devices[device['type']] = 0
        total_devices[device['type']] += qty
        item_num += 1
    
    spec_lines.append("-" * 80)
    spec_lines.append("")
    spec_lines.append("ИТОГО:")
    for dtype, count in total_devices.items():
        spec_lines.append(f"  {dtype}: {count} шт.")
    
    spec_lines.append("")
    spec_lines.append("-" * 80)
    spec_lines.append("РАСПРЕДЕЛЕНИЕ ПО ПОМЕЩЕНИЯМ:")
    spec_lines.append("-" * 80)
    
    for loc in locations:
        floor_devices = random.sample(devices, k=random.randint(3, 6))
        spec_lines.append(f"\n{loc}:")
        for dev in floor_devices:
            qty = random.randint(1, 4)
            spec_lines.append(f"  - {dev['model']} ({dev['type']}): {qty} шт.")
    
    spec_lines.append("")
    spec_lines.append("=" * 80)
    spec_lines.append("ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ:")
    spec_lines.append("=" * 80)
    spec_lines.append("""
1. Прибор С2000-М:
   - Количество шлейфов: до 256
   - Напряжение питания: 12В DC
   - Ток потребления: не более 100 мА
   - Рабочая температура: -35...+55 °C

2. Контроллер С2000-КДЛ:
   - Адресных устройств: до 127
   - Длина линии: до 3000 м
   - Защита от КЗ: есть

3. Извещатель ДИП-34А:
   - Чувствительность: 0.05-0.2 дБ/м
   - Питание: по шлейфу 9-30В
   - Индикация: светодиодная
""")
    
    spec_lines.append("=" * 80)
    spec_lines.append("Конец спецификации")
    spec_lines.append("=" * 80)
    
    return "\n".join(spec_lines)


def generate_device_list():
    """Генерирует список конкретных устройств с ID и координатами."""
    
    devices = []
    device_id = 1
    
    # Генерируем устройства для разных типов
    types_config = [
        {"type": "ДИП-34А", "base_count": 20, "partition_range": (1, 5)},
        {"type": "ДИП-34СУ", "base_count": 10, "partition_range": (1, 3)},
        {"type": "ИПР-513-3А", "base_count": 8, "partition_range": (1, 5)},
        {"type": "С2000-М", "base_count": 2, "partition_range": (1, 1)},
        {"type": "С2000-КДЛ", "base_count": 3, "partition_range": (1, 3)},
        {"type": "С2000-БИ", "base_count": 4, "partition_range": (1, 4)},
        {"type": "С2000-СП1", "base_count": 15, "partition_range": (1, 5)},
        {"type": "С2000-ЗВ", "base_count": 12, "partition_range": (1, 5)},
    ]
    
    rooms = ["101", "102", "103", "201", "202", "203", "301", "коридор 1", "коридор 2"]
    
    for config in types_config:
        count = config["base_count"] + random.randint(-3, 5)
        for i in range(max(1, count)):
            room = random.choice(rooms)
            partition = random.randint(*config["partition_range"])
            
            device = {
                "id": f"D{device_id:04d}",
                "type": config["type"],
                "address": device_id % 127 + 1,  # Адрес в линии 1-127
                "partition": partition,
                "room": room,
                "floor": int(room[0]) if room[0].isdigit() else 1,
                "x": random.uniform(10, 100),  # Координаты на плане
                "y": random.uniform(10, 80),
                "zone": f"Зона {random.randint(1, 10)}",
                "channels": random.randint(1, 4) if "КДЛ" in config["type"] or "М" in config["type"] else 0,
            }
            devices.append(device)
            device_id += 1
    
    return devices


def generate_connections(devices):
    """Генерирует граф соединений между устройствами."""
    
    connections = []
    
    # Находим контроллеры
    kdls = [d for d in devices if "КДЛ" in d["type"]]
    main_panel = next((d for d in devices if "С2000-М" in d["type"]), None)
    
    # Подключаем КДЛ к главному прибору
    if main_panel and kdls:
        for kdl in kdls:
            connections.append({
                "source": main_panel["id"],
                "target": kdl["id"],
                "type": "RS485",
                "ports": {"source": "L1", "target": "LINE"}
            })
    
    # Подключаем устройства к КДЛ
    addressable_devices = [d for d in devices if any(x in d["type"] for x in ["ДИП", "ИПР", "БИ", "СП1", "ЗВ"])]
    
    for i, device in enumerate(addressable_devices):
        if kdls:
            kdl = kdls[i % len(kdls)]  # Распределяем по контроллерам
            connections.append({
                "source": kdl["id"],
                "target": device["id"],
                "type": "DLT",  # Двухпроводная линия
                "address": device["address"]
            })
    
    # Добавляем логические связи (запуск оповещения)
    sounders = [d for d in devices if "ЗВ" in d["type"] or "СП1" in d["type"]]
    detectors = [d for d in devices if "ДИП" in d["type"] or "ИПР" in d["type"]]
    
    # Каждые 5 детекторов запускают один оповещатель (логическая связь)
    for i in range(0, min(len(detectors), 20), 5):
        if i < len(detectors) and i // 5 < len(sounders):
            connections.append({
                "source": detectors[i]["id"],
                "target": sounders[i // 5]["id"],
                "type": "LOGIC",
                "action": "ALARM_TRIGGER"
            })
    
    return connections


def generate_partitions(devices):
    """Генерирует разделы пожарной сигнализации."""
    
    partitions = []
    max_partition = max(d.get("partition", 1) for d in devices)
    
    for p_id in range(1, max_partition + 1):
        partition_devices = [d["id"] for d in devices if d.get("partition") == p_id]
        
        partitions.append({
            "id": p_id,
            "name": f"Раздел {p_id} - Этаж/Зона {p_id}",
            "device_ids": partition_devices,
            "type": "FIRE",
            "priority": p_id,
        })
    
    return partitions


def save_synthetic_data(output_dir: Path):
    """Сохраняет все синтетические данные в файлы."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Текст спецификации
    spec_text = generate_specification_text()
    with open(output_dir / "specification.txt", "w", encoding="utf-8") as f:
        f.write(spec_text)
    print(f"✓ Создана спецификация: {output_dir / 'specification.txt'}")
    
    # 2. Список устройств
    devices = generate_device_list()
    with open(output_dir / "devices.json", "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)
    print(f"✓ Создан список устройств: {output_dir / 'devices.json'} ({len(devices)} устройств)")
    
    # 3. Граф соединений
    connections = generate_connections(devices)
    with open(output_dir / "connections.json", "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)
    print(f"✓ Создан граф соединений: {output_dir / 'connections.json'} ({len(connections)} соединений)")
    
    # 4. Разделы
    partitions = generate_partitions(devices)
    with open(output_dir / "partitions.json", "w", encoding="utf-8") as f:
        json.dump(partitions, f, indent=2, ensure_ascii=False)
    print(f"✓ Созданы разделы: {output_dir / 'partitions.json'} ({len(partitions)} разделов)")
    
    # 5. Полный датасет для обучения
    full_dataset = {
        "metadata": {
            "project_name": "Бизнес-Центр Москва",
            "generated_at": datetime.now().isoformat(),
            "version": "1.0"
        },
        "specification_text": spec_text,
        "devices": devices,
        "connections": connections,
        "partitions": partitions,
        "statistics": {
            "total_devices": len(devices),
            "total_connections": len(connections),
            "total_partitions": len(partitions),
            "device_types": list(set(d["type"] for d in devices))
        }
    }
    
    with open(output_dir / "full_dataset.json", "w", encoding="utf-8") as f:
        json.dump(full_dataset, f, indent=2, ensure_ascii=False)
    print(f"✓ Создан полный датасет: {output_dir / 'full_dataset.json'}")
    
    return full_dataset


if __name__ == "__main__":
    import sys
    
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data_synthetic")
    
    print("=" * 60)
    print("Генерация синтетических данных для AI Orchestrator")
    print("=" * 60)
    
    dataset = save_synthetic_data(output_path)
    
    print("\n" + "=" * 60)
    print("СТАТИСТИКА:")
    print(f"  Устройств: {dataset['statistics']['total_devices']}")
    print(f"  Соединений: {dataset['statistics']['total_connections']}")
    print(f"  Разделов: {dataset['statistics']['total_partitions']}")
    print(f"  Типов устройств: {len(dataset['statistics']['device_types'])}")
    print("=" * 60)
    print("\n✅ Синтетические данные успешно сгенерированы!")
