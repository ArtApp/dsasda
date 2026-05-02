"""
Тестовый PDF файл для демонстрации работы системы.
Содержит пример спецификации оборудования АПС.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import io


def create_sample_pdf(output_path: str):
    """Создаёт тестовый PDF с спецификацией оборудования АПС."""
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CustomTitle', fontSize=16, leading=20, spaceAfter=30))
    styles.add(ParagraphStyle(name='CustomHeading', fontSize=12, leading=14, spaceAfter=12))
    styles.add(ParagraphStyle(name='CustomNormal', fontSize=10, leading=12))
    
    story = []
    
    # Заголовок
    story.append(Paragraph("СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ АПС", styles['CustomTitle']))
    story.append(Paragraph("Объект: Административное здание, ул. Примерная, д. 15", styles['CustomNormal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Раздел 1: Приборы контроля
    story.append(Paragraph("1. Приборы приёмно-контрольные", styles['CustomHeading']))
    
    data_pk = [
        ['Наименование', 'Тип', 'Кол-во', 'Примечание'],
        ['Приёмно-контрольный прибор С2000-М', 'С2000-М', '2 шт', 'Основной и резервный'],
        ['Прибор управления С2000-БИ', 'С2000-БИ', '4 шт', 'Блоки индикации'],
        ['Сетевой контроллер С2000-ПИ', 'С2000-ПИ', '1 шт', 'Преобразователь интерфейса'],
        ['Блок питания С2000-БП-12', 'С2000-БП-12', '3 шт', 'Резервированные'],
        ['Аккумуляторная батарея 12В 7Ач', 'Delta DT 1207', '6 шт', 'Комплект по 2 на БП'],
    ]
    
    table_pk = Table(data_pk, colWidths=[5*cm, 2.5*cm, 2*cm, 4*cm])
    table_pk.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table_pk)
    story.append(Spacer(1, 0.5*cm))
    
    # Раздел 2: Извещатели
    story.append(Paragraph("2. Извещатели пожарные", styles['CustomHeading']))
    
    data_ip = [
        ['Наименование', 'Тип', 'Кол-во', 'Примечание'],
        ['Дымовой оптический извещатель', 'ДИП-34А', '125 шт', 'Помещения 1-50'],
        ['Тепловой максимальный извещатель', 'ИП 212-141', '35 шт', 'Технические помещения'],
        ['Извещатель пламени', 'С2000-ИП-УЛ', '8 шт', 'Залы серверные'],
        ['Извещатель ручной', 'ИПР-513-3А', '24 шт', 'Пути эвакуации'],
        ['Извещатель линейный дымовой', 'ДИП-Л', '12 шт', 'Атриум, высота > 10м'],
    ]
    
    table_ip = Table(data_ip, colWidths=[5*cm, 2.5*cm, 2*cm, 4*cm])
    table_ip.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table_ip)
    story.append(Spacer(1, 0.5*cm))
    
    # Раздел 3: Оповещение
    story.append(Paragraph("3. Система оповещения и управления эвакуацией", styles['CustomHeading']))
    
    data_so = [
        ['Наименование', 'Тип', 'Кол-во', 'Примечание'],
        ['Блок управления СОУЭ', 'С2000-КДЛ', '2 шт', 'Линии связи'],
        ['Громкоговоритель настенный', '3W-6T', '45 шт', 'Помещения и коридоры'],
        ['Громкоговоритель потолочный', 'PC-8T', '28 шт', 'Офисные помещения'],
        ['Табло ВЫХОД', 'Световой знак', '18 шт', 'Эвакуационные выходы'],
        ['Микрофон настольный', 'DN-630S', '2 шт', 'Посты охраны'],
    ]
    
    table_so = Table(data_so, colWidths=[5*cm, 2.5*cm, 2*cm, 4*cm])
    table_so.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table_so)
    story.append(Spacer(1, 0.5*cm))
    
    # Раздел 4: Кабельная продукция
    story.append(Paragraph("4. Кабельная продукция и материалы", styles['CustomHeading']))
    
    data_cable = [
        ['Наименование', 'Тип', 'Кол-во', 'Примечание'],
        ['Кабель огнестойкий', 'КПСнг(А)-FRLS 2x0.75', '2500 м', 'Шлейфы сигнализации'],
        ['Кабель интерфейсный', 'RS-485 2x2x0.5', '800 м', 'Сеть С2000'],
        ['Кабель акустический', 'JY(ST)Y 2x0.8', '1200 м', 'СОУЭ'],
        ['Короб монтажный', 'КМ-1', '85 шт', 'Для извещателей'],
        ['Труба гофрированная', 'НГ 20мм', '1800 м', 'Открытая прокладка'],
    ]
    
    table_cable = Table(data_cable, colWidths=[5*cm, 2.5*cm, 2*cm, 4*cm])
    table_cable.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.palegreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table_cable)
    story.append(Spacer(1, 1*cm))
    
    # Итого
    story.append(Paragraph("ИТОГО:", styles['CustomHeading']))
    story.append(Paragraph("Общее количество устройств: 502 шт", styles['CustomNormal']))
    story.append(Paragraph("Количество шлейфов: 48", styles['CustomNormal']))
    story.append(Paragraph("Площадь защиты: 4250 м²", styles['CustomNormal']))
    
    doc.build(story)
    print(f"✅ Создан тестовый PDF: {output_path}")


if __name__ == '__main__':
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else '/workspace/orchestrator/input/sample_specification.pdf'
    create_sample_pdf(output)
