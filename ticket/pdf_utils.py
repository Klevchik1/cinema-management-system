from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm


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
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=15 * mm, leftMargin=15 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    elements = []

    # Регистрируем шрифты
    has_custom_font = register_custom_fonts()

    # Заголовок
    title_style = ParagraphStyle(
        name='CustomTitle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.black
    )

    title_text = Paragraph(f"<b>Отчет кинотеатра: {title}</b>", title_style)
    elements.append(title_text)

    # Информация о фильтрах
    if filters.get('start_date') or filters.get('end_date'):
        filter_text = "<b>Период:</b> "
        if filters.get('start_date'):
            filter_text += f"с {filters['start_date']} "
        if filters.get('end_date'):
            filter_text += f"по {filters['end_date']}"

        filter_style = ParagraphStyle(
            name='FilterStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica',
            fontSize=9,
            spaceAfter=15,
            alignment=TA_CENTER
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


def create_wrapped_text(text, font_name='Helvetica', font_size=9, alignment=TA_CENTER, width=None):
    """Создает Paragraph с переносом текста"""
    wrap_style = ParagraphStyle(
        name='WrapStyle',
        fontName=font_name,
        fontSize=font_size,
        alignment=alignment,
        wordWrap='CJK',  # Полный перенос текста
        spaceBefore=2,
        spaceAfter=2
    )
    return Paragraph(str(text), wrap_style)


def generate_revenue_table(data, has_custom_font, period):
    """Генерация таблицы выручки с переносом текста"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    # Описание периода
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
            fontSize=9,
            spaceAfter=8,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(f"<i>Отчет {period_text}</i>", period_style))

    # Заголовки таблицы
    font_name = 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'
    table_data = [[
        create_wrapped_text('Период', font_name, 9, TA_CENTER),
        create_wrapped_text('Выручка (руб.)', font_name, 9, TA_CENTER),
        create_wrapped_text('Продано билетов', font_name, 9, TA_CENTER),
        create_wrapped_text('Средний чек (руб.)', font_name, 9, TA_CENTER)
    ]]

    # Данные таблицы
    normal_font = 'DejaVuSans' if has_custom_font else 'Helvetica'
    for item in data:
        if 'date' in item and item['date']:
            period_display = item['date'].strftime('%d.%m.%Y')
        elif 'week' in item:
            period_display = f"Неделя {int(item['week'])}, {int(item['year'])}"
        elif 'month' in item:
            period_display = f"{int(item['month']):02d}/{int(item['year'])}"
        else:
            period_display = "Неизвестный период"

        # Расчет среднего чека
        tickets = item.get('tickets_sold', 0)
        revenue = item.get('revenue', 0) or 0
        avg_ticket = revenue / tickets if tickets > 0 else 0

        table_data.append([
            create_wrapped_text(period_display, normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{revenue:.2f}", normal_font, 8, TA_CENTER),
            create_wrapped_text(str(tickets), normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{avg_ticket:.2f}", normal_font, 8, TA_CENTER)
        ])

    # Создание таблицы с правильными ширинами
    table = Table(table_data, colWidths=[60 * mm, 40 * mm, 40 * mm, 40 * mm])

    # Стили таблицы
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])

    # Чередование цветов строк
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F9FA'))

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # Итоги
    total_revenue = sum(item.get('revenue', 0) or 0 for item in data)
    total_tickets = sum(item.get('tickets_sold', 0) for item in data)
    total_avg = total_revenue / total_tickets if total_tickets > 0 else 0

    total_style = ParagraphStyle(
        name='TotalStyle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=10,
        spaceAfter=6,
        textColor=colors.black,
        alignment=TA_CENTER
    )

    elements.append(Paragraph(f"<b>Общая выручка:</b> {total_revenue:.2f} руб.", total_style))
    elements.append(Paragraph(f"<b>Всего билетов:</b> {total_tickets}", total_style))
    elements.append(Paragraph(f"<b>Средний чек:</b> {total_avg:.2f} руб.", total_style))

    return elements


def generate_movies_table(data, has_custom_font):
    """Генерация таблицы популярных фильмов с полным переносом текста"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    # Заголовки таблицы
    font_name = 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'
    table_data = [[
        create_wrapped_text('№', font_name, 9, TA_CENTER),
        create_wrapped_text('Фильм', font_name, 9, TA_CENTER),
        create_wrapped_text('Жанр', font_name, 9, TA_CENTER),
        create_wrapped_text('Продано билетов', font_name, 9, TA_CENTER),
        create_wrapped_text('Общая выручка (руб.)', font_name, 9, TA_CENTER),
        create_wrapped_text('Популярность (%)', font_name, 9, TA_CENTER)
    ]]

    # Данные таблицы
    normal_font = 'DejaVuSans' if has_custom_font else 'Helvetica'
    for idx, movie in enumerate(data, 1):
        title = str(movie.get('title', 'Без названия'))
        genre = str(movie.get('genre', ''))
        tickets_sold = movie.get('tickets_sold', 0)
        total_revenue = movie.get('total_revenue', 0)
        popularity = movie.get('popularity_percentage', 0)

        table_data.append([
            create_wrapped_text(str(idx), normal_font, 8, TA_CENTER),
            create_wrapped_text(title, normal_font, 8, TA_CENTER),
            create_wrapped_text(genre, normal_font, 8, TA_CENTER),
            create_wrapped_text(str(tickets_sold), normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{total_revenue:.2f}", normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{popularity:.1f}", normal_font, 8, TA_CENTER)
        ])

    # Создание таблицы с правильными ширинами
    table = Table(table_data, colWidths=[15 * mm, 55 * mm, 30 * mm, 35 * mm, 40 * mm, 30 * mm])

    # Стили таблицы
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])

    # Чередование цветов строк
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F9FA'))

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 8 * mm))

    # Итоги
    total_tickets = sum(m.get('tickets_sold', 0) for m in data)
    total_revenue = sum(m.get('total_revenue', 0) for m in data)

    total_style = ParagraphStyle(
        name='MovieTotalStyle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=10,
        spaceAfter=6,
        textColor=colors.black,
        alignment=TA_CENTER
    )

    elements.append(Paragraph(f"<b>Всего билетов:</b> {total_tickets}", total_style))
    elements.append(Paragraph(f"<b>Общая выручка:</b> {total_revenue:.2f} руб.", total_style))

    return elements


def generate_halls_table(data, has_custom_font):
    """Генерация таблицы загруженности залов с полным переносом текста"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    # Заголовки таблицы
    font_name = 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'
    table_data = [[
        create_wrapped_text('Зал', font_name, 9, TA_CENTER),
        create_wrapped_text('Всего мест', font_name, 9, TA_CENTER),
        create_wrapped_text('Сеансов', font_name, 9, TA_CENTER),
        create_wrapped_text('Продано билетов', font_name, 9, TA_CENTER),
        create_wrapped_text('Выручка (руб.)', font_name, 9, TA_CENTER),
        create_wrapped_text('Загруженность (%)', font_name, 9, TA_CENTER)
    ]]

    # Данные таблицы
    normal_font = 'DejaVuSans' if has_custom_font else 'Helvetica'
    for hall in data:
        hall_name = str(hall.get('name', ''))
        total_seats = hall.get('total_seats', 0)
        total_screenings = hall.get('total_screenings', 0)
        sold_tickets = hall.get('sold_tickets', 0)
        total_revenue = hall.get('total_revenue', 0)
        occupancy_percent = hall.get('occupancy_percent', 0)

        table_data.append([
            create_wrapped_text(hall_name, normal_font, 8, TA_CENTER),
            create_wrapped_text(str(total_seats), normal_font, 8, TA_CENTER),
            create_wrapped_text(str(total_screenings), normal_font, 8, TA_CENTER),
            create_wrapped_text(str(sold_tickets), normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{total_revenue:.2f}", normal_font, 8, TA_CENTER),
            create_wrapped_text(f"{occupancy_percent:.1f}", normal_font, 8, TA_CENTER)
        ])

    # Создание таблицы с правильными ширинами
    table = Table(table_data, colWidths=[35 * mm, 25 * mm, 25 * mm, 35 * mm, 35 * mm, 35 * mm])

    # Стили таблицы
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FFC107')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])

    # Чередование цветов строк
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F9FA'))

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 8 * mm))

    # Итоги
    if data:
        avg_occupancy = sum(h.get('occupancy_percent', 0) for h in data) / len(data) if data else 0
        total_revenue = sum(h.get('total_revenue', 0) for h in data)
        total_tickets = sum(h.get('sold_tickets', 0) for h in data)

        total_style = ParagraphStyle(
            name='HallTotalStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
            fontSize=10,
            spaceAfter=6,
            textColor=colors.black,
            alignment=TA_CENTER
        )

        elements.append(Paragraph(f"<b>Средняя загруженность:</b> {avg_occupancy:.1f}%", total_style))
        elements.append(Paragraph(f"<b>Общая выручка:</b> {total_revenue:.2f} руб.", total_style))
        elements.append(Paragraph(f"<b>Всего билетов:</b> {total_tickets}", total_style))

    return elements


def generate_sales_table(data, has_custom_font):
    """Генерация таблицы общей статистики с полным переносом текста"""
    elements = []

    if not data:
        elements.append(Paragraph("Нет данных для отображения", getSampleStyleSheet()['Normal']))
        return elements

    # Стиль для ячеек с переносом текста
    cell_style = ParagraphStyle(
        name='CellStyle',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica',
        fontSize=9,
        wordWrap='CJK',  # Полный перенос текста
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=4
    )

    cell_style_bold = ParagraphStyle(
        name='CellStyleBold',
        fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
        fontSize=9,
        wordWrap='CJK',
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=4
    )

    # Создаем данные таблицы с использованием Paragraph для полного переноса
    popular_movie = str(data.get('popular_movie', ''))

    table_data = [
        [
            Paragraph("<b>Показатель</b>", cell_style_bold),
            Paragraph("<b>Значение</b>", cell_style_bold)
        ],
        [
            Paragraph("Всего продано билетов", cell_style),
            Paragraph(str(data.get('total_tickets', 0)), cell_style)
        ],
        [
            Paragraph("Общая выручка (руб.)", cell_style),
            Paragraph(f"{data.get('total_revenue', 0):.2f}", cell_style)
        ],
        [
            Paragraph("Средняя цена билета (руб.)", cell_style),
            Paragraph(f"{data.get('avg_ticket_price', 0):.2f}", cell_style)
        ],
        [
            Paragraph("Самый популярный фильм", cell_style),
            Paragraph(popular_movie, cell_style)
        ],
        [
            Paragraph("Билетов на популярный фильм", cell_style),
            Paragraph(str(data.get('popular_movie_tickets', 0)), cell_style)
        ]
    ]

    # Создание таблицы
    table = Table(table_data, colWidths=[80 * mm, 80 * mm])

    # Стили таблицы
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6F42C1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])

    # Чередование цветов строк
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8F9FA'))

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # Добавляем информацию о доле популярного фильма
    total_tickets = data.get('total_tickets', 0)
    popular_tickets = data.get('popular_movie_tickets', 0)

    if total_tickets > 0:
        share_percent = (popular_tickets / total_tickets) * 100

        share_style = ParagraphStyle(
            name='ShareStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
            fontSize=10,
            spaceBefore=5,
            spaceAfter=5,
            textColor=colors.HexColor('#28A745'),
            alignment=TA_CENTER
        )

        elements.append(Paragraph(f"<b>Доля популярного фильма:</b> {share_percent:.1f}% от всех продаж", share_style))

    return elements