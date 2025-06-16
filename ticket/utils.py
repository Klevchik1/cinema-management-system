import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import cm
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)


try:
    font_path = os.path.join(settings.BASE_DIR, 'ticket', 'fonts', 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    base_font_name = 'DejaVuSans'
except:
    base_font_name = 'Helvetica'

try:
    font_path = os.path.join(settings.BASE_DIR, 'ticket', 'fonts', 'DejaVuSans.ttf')
    bold_font_path = os.path.join(settings.BASE_DIR, 'ticket', 'fonts', 'DejaVuSans-Bold.ttf')

    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_font_path))

    base_font_name = 'DejaVuSans'
    bold_font_name = 'DejaVuSans-Bold'
except Exception as e:
    print(f"Error loading fonts: {e}")
    base_font_name = 'Helvetica'
    bold_font_name = 'Helvetica-Bold'

styles = getSampleStyleSheet()
custom_styles = {
    'Title': ParagraphStyle(
        name='Title',
        fontName=base_font_name,
        fontSize=18,
        alignment=1,
        spaceAfter=12
    ),
    'Header': ParagraphStyle(
        name='Header',
        fontName=base_font_name,
        fontSize=12,
        textColor=colors.darkblue,
        spaceAfter=6
    ),
    'NormalCenter': ParagraphStyle(
        name='NormalCenter',
        fontName=base_font_name,
        fontSize=10,
        alignment=1,
        spaceAfter=6
    ),
    'SmallCenter': ParagraphStyle(
        name='SmallCenter',
        fontName=base_font_name,
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    ),
    'Bold': ParagraphStyle(
        name='Bold',
        fontName=base_font_name,
        fontSize=10,
        leading=14,
        textColor=colors.black,
        spaceAfter=6,
        alignment=1
    )
}

def generate_ticket_pdf(tickets):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        title=f"Билеты на сеанс",
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    elements = []

    first_ticket = tickets[0]
    total_price = sum(ticket.screening.price for ticket in tickets)

    if len(tickets) == 1:
        title_text = "БИЛЕТ НА СЕАНС"
    else:
        title_text = "КИНОТЕАТР 'ПРЕМЬЕРА'"

    elements.append(Paragraph(title_text, custom_styles['Title']))
    elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph(f"<b>{first_ticket.screening.movie.title}</b>", custom_styles['Header']))
    elements.append(Paragraph(f"Жанр: {first_ticket.screening.movie.genre}", custom_styles['NormalCenter']))
    elements.append(Paragraph(f"Продолжительность: {first_ticket.screening.movie.duration}", custom_styles['NormalCenter']))
    elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph(f"<b>Сеанс</b>", custom_styles['Header']))
    elements.append(Paragraph(
        f"{first_ticket.screening.start_time.strftime('%d.%m.%Y %H:%M')} - "
        f"{first_ticket.screening.end_time.strftime('%H:%M')}",
        custom_styles['NormalCenter']
    ))
    elements.append(Paragraph(f"Зал: {first_ticket.screening.hall.name}", custom_styles['NormalCenter']))
    elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph(f"<b>Покупатель</b>", custom_styles['Header']))
    elements.append(Paragraph(
        f"{first_ticket.user.name} {first_ticket.user.surname}",
        custom_styles['NormalCenter']
    ))
    elements.append(Paragraph(f"Телефон: {first_ticket.user.number}", custom_styles['NormalCenter']))
    elements.append(Spacer(1, 0.2 * cm))

    ticket_data = [
        [Paragraph("<b>Ряд</b>", custom_styles['Bold']),
         Paragraph("<b>Место</b>", custom_styles['Bold']),
         Paragraph("<b>Цена</b>", custom_styles['Bold'])]
    ]

    for ticket in tickets:
        ticket_data.append([
            Paragraph(str(ticket.seat.row), custom_styles['NormalCenter']),
            Paragraph(str(ticket.seat.number), custom_styles['NormalCenter']),
            Paragraph(f"{ticket.screening.price} ₽", custom_styles['NormalCenter'])
        ])

    col_widths = [3 * cm, 3 * cm, 3 * cm]
    ticket_table = Table(ticket_data, colWidths=col_widths, repeatRows=1)  # repeatRows=1 для повторения заголовков

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), bold_font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), base_font_name),
    ])

    ticket_table.setStyle(table_style)

    elements.append(ticket_table)
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph(
        f"<b>ИТОГО: {len(tickets)} билет(а) на сумму {total_price} ₽</b>",
        custom_styles['NormalCenter']
    ))
    elements.append(Spacer(1, 0.3 * cm))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )

    qr_data = {
        "ticket_id": tickets[0].id,
        "film": first_ticket.screening.movie.title,
        "datetime": first_ticket.screening.start_time.isoformat(),
        "hall": first_ticket.screening.hall.name,
        "seats": ", ".join(f"{t.seat.row}-{t.seat.number}" for t in tickets),
        "price": total_price,
        "user": f"{first_ticket.user.name} {first_ticket.user.surname}"
    }

    qr.add_data(str(qr_data))
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    elements.append(Image(qr_buffer, width=5 * cm, height=5 * cm))
    elements.append(Paragraph(
        f"Билет ID: {tickets[0].id} | "
        f"Дата покупки: {timezone.now().strftime('%d.%m.%Y %H:%M')}",
        custom_styles['SmallCenter']
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer