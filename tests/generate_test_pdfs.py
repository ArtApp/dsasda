"""
Генератор тестовых PDF файлов для проверки парсера.
Создает фиктивные проекты с различной структурой данных.
Использует шрифт DejaVu Sans для поддержки кириллицы.
"""

import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime


def get_cyrillic_font():
    """Получает шрифт с поддержкой кириллицы."""
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    
    for font_path in font_paths:
        if Path(font_path).exists():
            return fitz.Font('dejavu', fontfile=font_path)
    
    # Если не нашли, пробуем загрузить стандартный
    try:
        return fitz.Font('dejavu')
    except:
        return None


def create_simple_project_pdf(output_path: str = "tests/data/simple_project.pdf"):
    """Создает простой тестовый PDF с базовой спецификацией оборудования."""
    
    doc = fitz.open()
    page = doc.new_page()
    
    # Получаем шрифт с поддержкой кириллицы
    font = get_cyrillic_font()
    
    if not font:
        # Если шрифт не найден, создаем PDF с латиницей для тестирования
        content = [
            "PROJECT DOCUMENTATION",
            "Fire Alarm System",
            "",
            "EQUIPMENT SPECIFICATION",
            "1. S2000M control panel - 1 pcs",
            "2. KDL-2I line controller - 2 pcs", 
            "3. DIP-34A smoke detector - 15 pcs",
            "4. IPR 513-3A manual alarm - 4 pcs",
            "5. BKI-70 commutation block - 1 pcs",
            "6. SP2-1 light indicator - 2 pcs",
            "7. S2000-S1 sound siren - 3 pcs",
            "",
            "SECTIONS STRUCTURE",
            "Section 1: First floor (addresses 1-10)",
            "  - DIP-34A: addresses 1-8",
            "  - IPR 513-3A: address 9",
            "  - SP2-1: address 10",
            "",
            "Section 2: Second floor (addresses 11-20)",
            "  - DIP-34A: addresses 11-18",
            "  - IPR 513-3A: address 19",
            "  - SP2-1: address 20",
            "",
            "MANAGEMENT SCENARIOS",
            "1. On fire in any section:",
            "   - Turn on SP2-1 indicator (address 10, relay 1)",
            "   - Turn on S2000-S1 siren (address 12, relay 1)",
            "   - Send signal to console",
            "",
            "2. On error in section 1:",
            "   - Blink SP2-1 indicator (address 10, relay 2)",
            "",
            "3. On arm section:",
            "   - Disable all output devices",
        ]
        
        y = 50
        for line in content:
            page.insert_text((50, y), line, fontsize=12)
            y += 20
    else:
        # Используем TextWriter для кириллицы
        text_writer = fitz.TextWriter(page.rect)
        
        # Заголовок
        text_writer.append((50, 50), "ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ", font=font, fontsize=16)
        text_writer.append((50, 70), "Система пожарной сигнализации", font=font, fontsize=14)
        
        # Спецификация
        y = 110
        text_writer.append((50, y), "СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ", font=font, fontsize=14)
        
        equipment = [
            "1. Прибор приемно-контрольный С2000М - 1 шт.",
            "2. Контроллер двухпроводной линии связи КДЛ-2И - 2 шт.",
            "3. Извещатель пожарный дымовой ДИП-34А - 15 шт.",
            "4. Извещатель пожарный ручной ИПР 513-3А - 4 шт.",
            "5. Блок коммутации БКИ-70 - 1 шт.",
            "6. Табло световое СП2-1 - 2 шт.",
            "7. Сирена звуковая С2000-С1 - 3 шт.",
        ]
        
        y = 135
        for item in equipment:
            text_writer.append((50, y), item, font=font, fontsize=12)
            y += 22
        
        # Разделы
        y += 10
        text_writer.append((50, y), "СТРУКТУРА РАЗДЕЛОВ", font=font, fontsize=14)
        
        sections = [
            "Раздел 1: Первый этаж (адреса 1-10)",
            "  - ДИП-34А: адреса 1-8",
            "  - ИПР 513-3А: адрес 9",
            "  - СП2-1: адрес 10",
            "",
            "Раздел 2: Второй этаж (адреса 11-20)",
            "  - ДИП-34А: адреса 11-18",
            "  - ИПР 513-3А: адрес 19",
            "  - СП2-1: адрес 20",
        ]
        
        y += 25
        for line in sections:
            text_writer.append((50, y), line, font=font, fontsize=12)
            y += 20
        
        # Сценарии
        y += 10
        text_writer.append((50, y), "СЦЕНАРИИ УПРАВЛЕНИЯ", font=font, fontsize=14)
        
        scenarios = [
            "1. При пожаре в любом разделе:",
            "   - Включить табло СП2-1 (адрес 10, реле 1)",
            "   - Включить сирену С2000-С1 (адрес 12, реле 1)",
            "   - Передать сигнал на пульт",
            "",
            "2. При ошибке в разделе 1:",
            "   - Включить табло СП2-1 (адрес 10, реле 2) миганием",
            "",
            "3. При взятии раздела:",
            "   - Отключить все исполнительные устройства",
        ]
        
        y += 25
        for line in scenarios:
            text_writer.append((50, y), line, font=font, fontsize=12)
            y += 20
        
        text_writer.write_text(page)
    
    # Сохранение
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_file))
    doc.close()
    
    print(f"✓ Создан тестовый PDF: {output_path}")
    return str(output_file)


def create_complex_project_pdf(output_path: str = "tests/data/complex_project.pdf"):
    """Создает сложный тестовый PDF с несколькими этажами и зонами."""
    
    doc = fitz.open()
    
    # Страница 1: Общая информация
    page1 = doc.new_page()
    page1.insert_text((50, 50), "ПРОЕКТ АВТОМАТИЗИРОВАННОЙ СИСТЕМЫ", fontsize=16, fontname="helv")
    page1.insert_text((50, 80), "ПОЖАРНОЙ СИГНАЛИЗАЦИИ И ОПОВЕЩЕНИЯ", fontsize=16, fontname="helv")
    
    page1.insert_text((50, 120), "Объект: Административное здание, 3 этажа", fontsize=12)
    page1.insert_text((50, 140), "Дата проекта: " + datetime.now().strftime("%Y-%m-%d"), fontsize=12)
    
    # Спецификация оборудования
    page1.insert_text((50, 180), "СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ БОЛИД", fontsize=14, fontname="helv")
    
    equipment = [
        "Прибор С2000М (центральный контроллер) - 1 шт., адрес 1",
        "КДЛ-2И (линейный контроллер) - 3 шт., адреса 2-4",
        "ДИП-34А (дымовой извещатель) - 45 шт.",
        "ИПР 513-3А (ручной извещатель) - 12 шт.",
        "БКИ-70 (блок индикации) - 3 шт.",
        "СП2-1 (световое табло) - 6 шт.",
        "С2000-С1 (звуковая сирена) - 9 шт.",
        "РС-200Т (релейный блок) - 2 шт.",
    ]
    
    y = 220
    for item in equipment:
        page1.insert_text((50, y), item, fontsize=11)
        y += 18
    
    # Страница 2: Структура разделов
    page2 = doc.new_page()
    page2.insert_text((50, 50), "СТРУКТУРА РАЗДЕЛОВ И ЗОН", fontsize=14, fontname="helv")
    
    sections = [
        "РАЗДЕЛ 1: Первый этаж (офисы 101-110)",
        "  Адреса устройств: 10-25",
        "  Тип зоны: офисная",
        "  Алгоритм: 'B' (для ДИП)",
        "",
        "РАЗДЕЛ 2: Второй этаж (переговорные)",
        "  Адреса устройств: 26-40",
        "  Тип зоны: переговорная",
        "  Алгоритм: 'B'",
        "",
        "РАЗДЕЛ 3: Третий этаж (серверная)",
        "  Адреса устройств: 41-55",
        "  Тип зоны: серверная",
        "  Алгоритм: 'A' (усиленный)",
        "",
        "РАЗДЕЛ 4: Коридоры и пути эвакуации",
        "  Адреса устройств: 56-70",
        "  Тип зоны: коридор",
        "  Алгоритм: 'B'",
    ]
    
    y = 90
    for line in sections:
        page2.insert_text((50, y), line, fontsize=11)
        y += 18
    
    # Страница 3: Сценарии управления
    page3 = doc.new_page()
    page3.insert_text((50, 50), "СЦЕНАРИИ УПРАВЛЕНИЯ ИСПОЛНИТЕЛЬНЫМИ УСТРОЙСТВАМИ", fontsize=14, fontname="helv")
    
    scenarios = [
        "СЦЕНАРИЙ 1: ПОЖАР В ЛЮБОМ РАЗДЕЛЕ",
        "  Условия: Срабатывание 2-х извещателей в одном разделе ИЛИ",
        "           Срабатывание 1-го извещателя + ручной ИПР",
        "  Действия:",
        "    - Включить табло СП2-1 во всех разделах (реле 1)",
        "    - Включить сирены С2000-С1 (реле 1)",
        "    - Закрыть клапаны вентиляции (через РС-200Т, реле 1-2)",
        "    - Разблокировать СКУД (через РС-200Т, реле 3)",
        "    - Передать сигнал на пульт охраны",
        "",
        "СЦЕНАРИЙ 2: ОШИБКА В ЛИНИИ СВЯЗИ",
        "  Условия: Обрыв КДЛ или потеря связи с устройствами",
        "  Действия:",
        "    - Мигание табло СП2-1 в неисправном разделе (реле 2)",
        "    - Звуковой сигнал ошибки на БКИ",
        "",
        "СЦЕНАРИЙ 3: ВЗЯТИЕ РАЗДЕЛА НА ОХРАНУ",
        "  Условия: Команда с пульта или по расписанию",
        "  Действия:",
        "    - Отключить все исполнительные устройства",
        "    - Зеленая индикация на БКИ",
        "",
        "СЦЕНАРИЙ 4: СНЯТИЕ С ОХРАНЫ",
        "  Условия: Команда с пульта или ключ доступа",
        "  Действия:",
        "    - Отключить режим охраны",
        "    - Синяя индикация на БКИ",
    ]
    
    y = 90
    for line in scenarios:
        page3.insert_text((50, y), line, fontsize=10)
        y += 16
    
    # Сохранение
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_file))
    doc.close()
    
    print(f"✓ Создан сложный тестовый PDF: {output_path}")
    return str(output_file)


def create_edge_cases_pdf(output_path: str = "tests/data/edge_cases.pdf"):
    """Создает PDF с граничными случаями для тестирования устойчивости парсера."""
    
    doc = fitz.open()
    page = doc.new_page()
    
    page.insert_text((50, 50), "ТЕСТОВЫЕ ГРАНИЧНЫЕ СЛУЧАИ", fontsize=14, fontname="helv")
    
    edge_cases = [
        "1. Устройство без адреса: ДИП-34А - 5 шт.",
        "2. Нестандартное название: С2000-М (дефис вместо пробела)",
        "3. Дублирование: С2000М - 1 шт. (уже было в спецификации)",
        "4. Опечатки: ДИП-34А (дымавой извещатель) - 2 шт.",
        "5. Частичная информация: Табло световое - 1 шт.",
        "6. Неизвестное оборудование: XYZ-123 - 3 шт.",
        "7. Отрицательное количество: ИПР 513 - -2 шт. (ошибка в проекте)",
        "8. Очень большой адрес: Датчик на адресе 999",
        "9. Пустая строка в спецификации",
        "10. Специальные символы: Сирена <test> & 'сирена'",
    ]
    
    y = 90
    for case in edge_cases:
        page.insert_text((50, y), case, fontsize=11)
        y += 20
    
    # Сценарии с проблемами
    page.insert_text((50, y + 30), "ПРОБЛЕМНЫЕ СЦЕНАРИИ:", fontsize=12, fontname="helv")
    
    problem_scenarios = [
        "- При пожаре включить несуществующее устройство адрес 999",
        "- При ошибке сделать ничего (пустое действие)",
        "- Ссылка на несуществующий раздел №99",
        "- Циклическая зависимость: раздел 1 зависит от раздела 2, раздел 2 от раздела 1",
    ]
    
    y += 60
    for scenario in problem_scenarios:
        page.insert_text((50, y), scenario, fontsize=10)
        y += 18
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_file))
    doc.close()
    
    print(f"✓ Создан PDF с граничными случаями: {output_path}")
    return str(output_file)


if __name__ == "__main__":
    print("Генерация тестовых PDF файлов...")
    create_simple_project_pdf()
    create_complex_project_pdf()
    create_edge_cases_pdf()
    print("\n✓ Все тестовые файлы созданы успешно!")
    print("Расположение:")
    print("  - tests/data/simple_project.pdf")
    print("  - tests/data/complex_project.pdf")
    print("  - tests/data/edge_cases.pdf")
