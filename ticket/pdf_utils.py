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
    # ИСПРАВЛЕНО: уменьшены отступы для большего пространства
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elements = []

    # Регистрируем шрифты
    has_custom_font = register_custom_fonts()

    styles = getSampleStyleSheet()

    # Заголовок - ЧЕРНЫЙ как требовалось
    title_style = ParagraphStyle(
        name='CustomTitle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # CENTER
        textColor=colors.black
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
        elements.extend(generate_revenue_table(data, has_custom_font, filters.get('period')))
    elif report_type == 'movies':
        elements.extend(generate_movies_table(data, has_custom_font))
    elif report_type == 'halls':
        elements.extend(generate_halls_table(data, has_custom_font))
    elif report_type == 'sales':
        elements.extend(generate_sales_table(data, has_custom_font))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_revenue_table(data, has_custom_font, period):
    """Генерация таблицы выручки"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    # Добавляем описание периода на русском
    period_map = {
        'daily': 'по дням',
        'weekly': 'по неделям',
        'monthly': 'по месяцам'
    }
    period_text = period_map.get(period, '')

    if period_text:
        period_style = ParagraphStyle(
            name='PeriodStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica',
            fontSize=10,
            spaceAfter=10,
            alignment=1
        )
        elements.append(Paragraph(f"Отчет {period_text}", period_style))

    table_data = [['Период', 'Выручка (руб.)', 'Продано билетов']]

    for item in data:
        if 'date' in item and item['date']:
            period_display = item['date'].strftime('%d.%m.%Y')
        elif 'week' in item:
            period_display = f"Неделя {int(item['week'])}, {int(item['year'])}"
        elif 'month' in item:
            period_display = f"{int(item['month']):02d}/{int(item['year'])}"
        else:
            period_display = "Неизвестный период"

        table_data.append([
            period_display,
            f"{item['revenue'] or 0:.2f}",
            str(item['tickets_sold'])
        ])

    # ИСПРАВЛЕНО: увеличены ширины столбцов
    table = Table(table_data, colWidths=[180, 130, 120])  # Увеличена ширина периода и выручки
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),  # Увеличен шрифт
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),  # Увеличен шрифт
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Итоги - ЧЕРНЫЙ цвет как требовалось
    total_revenue = sum(item['revenue'] or 0 for item in data)
    total_tickets = sum(item['tickets_sold'] for item in data)

    total_style = ParagraphStyle(
        name='TotalStyle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=12,
        spaceAfter=10,
        textColor=colors.black
    )

    elements.append(Paragraph(f"Общая выручка: {total_revenue:.2f} руб.", total_style))
    elements.append(Paragraph(f"Всего билетов: {total_tickets}", total_style))

    return elements


def generate_movies_table(data, has_custom_font):
    """Генерация таблицы популярных фильмов - ИСПРАВЛЕНО: увеличены ширины"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [['Фильм', 'Жанр', 'Продано билетов', 'Общая выручка (руб.)']]

    for movie in data:
        table_data.append([
            movie.title,
            movie.genre,
            str(movie.tickets_sold),
            f"{movie.total_revenue or 0:.2f}"
        ])

    # ИСПРАВЛЕНО: значительно увеличены ширины колонок
    table = Table(table_data, colWidths=[220, 100, 100, 130])  # Увеличена ширина фильма и выручки
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),  # Увеличен шрифт
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),  # Увеличен шрифт
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black)
    ]))

    elements.append(table)
    return elements


def generate_halls_table(data, has_custom_font):
    """Генерация таблицы загруженности залов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    table_data = [['Зал', 'Всего мест', 'Сеансов', 'Продано билетов', 'Выручка (руб.)', 'Загруженность (%)']]

    for hall in data:
        table_data.append([
            hall['name'],
            str(hall['total_seats']),
            str(hall['total_screenings']),
            str(hall['sold_tickets']),
            f"{hall['total_revenue'] or 0:.2f}",
            f"{hall['occupancy_percent']:.1f}%"
        ])

    # ИСПРАВЛЕНО: значительно увеличены ширины всех колонок
    table = Table(table_data, colWidths=[120, 80, 80, 100, 110, 100])  # Увеличены все ширины
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FFC107')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),  # Увеличен шрифт
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),  # Увеличен шрифт
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Увеличены отступы
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Увеличены отступы
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

    # ИСПРАВЛЕНО: увеличены ширины столбцов
    table = Table(table_data, colWidths=[220, 180])  # Увеличены ширины
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
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black)
    ]))

    elements.append(table)
    return elements