from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings


def register_custom_fonts():
    """Регистрация кастомных шрифтов"""
    try:
        fonts_dir = os.path.join(settings.BASE_DIR, 'ticket', 'fonts')
        dejavu_sans_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')

        if os.path.exists(dejavu_sans_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_sans_path))
            return True
        return False
    except Exception:
        return False


def generate_pdf_report(data, report_type, title, filters):
    """Генерация PDF отчета"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []

    # Регистрируем шрифты
    has_custom_font = register_custom_fonts()

    styles = getSampleStyleSheet()

    # Заголовок
    title_style = ParagraphStyle(
        name='CustomTitle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # CENTER
        textColor=colors.darkblue
    )

    title_text = Paragraph(f"Отчет кинотеатра: {title}", title_style)
    elements.append(title_text)

    # Информация о фильтрах
    if filters.get('start_date') or filters.get('end_date'):
        filter_text = "Период: "
        if filters.get('start_date'):
            filter_text += f"с {filters['start_date']} "
        if filters.get('end_date'):
            filter_text += f"по {filters['end_date']}"

        filter_style = ParagraphStyle(
            name='FilterStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica',
            fontSize=10,
            spaceAfter=20,
            alignment=1
        )
        elements.append(Paragraph(filter_text, filter_style))

    # Генерация таблицы в зависимости от типа отчета
    if report_type == 'revenue':
        elements.extend(generate_revenue_table(data, has_custom_font))
    elif report_type == 'movies':
        elements.extend(generate_movies_table(data, has_custom_font))
    elif report_type == 'halls':
        elements.extend(generate_halls_table(data, has_custom_font))
    elif report_type == 'sales':
        elements.extend(generate_sales_table(data, has_custom_font))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_revenue_table(data, has_custom_font):
    """Генерация таблицы выручки"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [['Период', 'Выручка (руб.)', 'Продано билетов']]

    for item in data:
        if 'date' in item:
            period = item['date'].strftime('%d.%m.%Y')
        elif 'week' in item:
            period = f"Неделя {int(item['week'])}, {int(item['year'])}"
        else:
            period = f"{int(item['month']):02d}/{int(item['year'])}"

        table_data.append([
            period,
            f"{item['revenue'] or 0:.2f}",
            item['tickets_sold']
        ])

    table = Table(table_data, colWidths=[150, 120, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6'))
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Итоги
    total_revenue = sum(item['revenue'] or 0 for item in data)
    total_tickets = sum(item['tickets_sold'] for item in data)

    total_style = ParagraphStyle(
        name='TotalStyle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=12,
        spaceAfter=10,
        textColor=colors.darkgreen
    )

    elements.append(Paragraph(f"Общая выручка: {total_revenue:.2f} руб.", total_style))
    elements.append(Paragraph(f"Всего билетов: {total_tickets}", total_style))

    return elements


def generate_movies_table(data, has_custom_font):
    """Генерация таблицы популярных фильмов"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [['Фильм', 'Жанр', 'Продано билетов', 'Общая выручка (руб.)']]

    for movie in data:
        table_data.append([
            movie.title,
            movie.genre,
            movie.tickets_sold,
            f"{movie.total_revenue or 0:.2f}"
        ])

    table = Table(table_data, colWidths=[200, 100, 100, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6'))
    ]))

    elements.append(table)
    return elements


def generate_halls_table(data, has_custom_font):
    """Генерация таблицы загруженности залов"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [['Зал', 'Всего мест', 'Сеансов', 'Продано билетов', 'Выручка (руб.)', 'Загруженность (%)']]

    for hall in data:
        table_data.append([
            hall.name,
            hall.total_seats,
            hall.total_screenings,
            hall.sold_tickets,
            f"{hall.total_revenue or 0:.2f}",
            f"{getattr(hall, 'occupancy_percent', 0):.1f}%"
        ])

    table = Table(table_data, colWidths=[120, 80, 80, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FFC107')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6'))
    ]))

    elements.append(table)
    return elements


def generate_sales_table(data, has_custom_font):
    """Генерация таблицы общей статистики"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [
        ['Показатель', 'Значение'],
        ['Всего продано билетов', str(data['total_tickets'])],
        ['Общая выручка', f"{data['total_revenue']:.2f} руб."],
        ['Средняя цена билета', f"{data['avg_ticket_price']:.2f} руб."],
        ['Самый популярный фильм', data['popular_movie']],
        ['Билетов на популярный фильм', str(data['popular_movie_tickets'])]
    ]

    table = Table(table_data, colWidths=[200, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6F42C1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6'))
    ]))

    elements.append(table)
    return elements