import csv
import json
from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings


class LogExporter:
    """Утилита для экспорта логов в различные форматы"""

    @staticmethod
    def export_logs_to_csv(queryset, filename=None):
        """Экспорт логов в CSV"""
        if filename is None:
            filename = f"logs_export_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Создаем CSV writer с поддержкой кириллицы
        response.write('\ufeff')  # BOM для Excel
        writer = csv.writer(response, delimiter=';')

        # Заголовки
        writer.writerow([
            'Время операции',
            'Пользователь',
            'Тип действия',
            'Модуль',
            'Описание',
            'Объект',
            'ID объекта',
            'IP адрес',
            'User Agent',
            'Дополнительные данные'
        ])

        # Данные
        for log in queryset:
            writer.writerow([
                log.timestamp.strftime('%d.%m.%Y %H:%M:%S'),
                log.user.email if log.user else 'Система',
                log.get_action_type_display(),
                log.get_module_type_display(),
                log.description,
                log.object_repr or '-',
                log.object_id or '-',
                log.ip_address or '-',
                log.user_agent or '-',
                log.get_additional_data_display()
            ])

        return response

    @staticmethod
    def export_logs_to_json(queryset, filename=None):
        """Экспорт логов в JSON"""
        if filename is None:
            filename = f"logs_export_{timezone.now().strftime('%Y%m%d_%H%M')}.json"

        logs_data = []
        for log in queryset:
            log_data = {
                'timestamp': log.timestamp.isoformat(),
                'user': log.user.email if log.user else None,
                'action_type': log.action_type,
                'action_type_display': log.get_action_type_display(),
                'module_type': log.module_type,
                'module_type_display': log.get_module_type_display(),
                'description': log.description,
                'object_repr': log.object_repr,
                'object_id': log.object_id,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'additional_data': log.additional_data
            }
            logs_data.append(log_data)

        response = HttpResponse(
            json.dumps(logs_data, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_logs_to_pdf(queryset, filename=None):
        """Экспорт логов в PDF"""
        if filename is None:
            filename = f"logs_export_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        elements = []

        # Регистрируем шрифты
        has_custom_font = LogExporter._register_custom_fonts()

        styles = getSampleStyleSheet()

        # Заголовок
        title_style = ParagraphStyle(
            name='CustomTitle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica-Bold',
            fontSize=16,
            spaceAfter=30,
            alignment=1,
            textColor=colors.black
        )

        title_text = Paragraph(f"Экспорт логов операций - {timezone.now().strftime('%d.%m.%Y %H:%M')}", title_style)
        elements.append(title_text)

        # Статистика
        stats_style = ParagraphStyle(
            name='StatsStyle',
            fontName='DejaVuSans' if has_custom_font else 'Helvetica',
            fontSize=10,
            spaceAfter=20,
            alignment=1
        )

        total_logs = queryset.count()
        stats_text = Paragraph(f"Всего записей: {total_logs}", stats_style)
        elements.append(stats_text)

        # Таблица логов
        if queryset.exists():
            table_data = [['Время', 'Пользователь', 'Действие', 'Модуль', 'Описание']]

            for log in queryset:
                table_data.append([
                    log.timestamp.strftime('%d.%m.%Y %H:%M'),
                    log.user.email if log.user else 'Система',
                    log.get_action_type_display(),
                    log.get_module_type_display(),
                    log.description[:50] + '...' if len(log.description) > 50 else log.description
                ])

            table = Table(table_data, colWidths=[80, 80, 80, 80, 180])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if has_custom_font else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
                ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans' if has_custom_font else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            elements.append(table)
        else:
            no_data_style = ParagraphStyle(
                name='NoDataStyle',
                fontName='DejaVuSans' if has_custom_font else 'Helvetica',
                fontSize=12,
                spaceAfter=20,
                alignment=1,
                textColor=colors.gray
            )
            elements.append(Paragraph("Нет данных для экспорта", no_data_style))

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def _register_custom_fonts():
        """Регистрация кастомных шрифтов для PDF"""
        try:
            fonts_dir = os.path.join(settings.BASE_DIR, 'ticket', 'fonts')
            dejavu_sans_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')

            if os.path.exists(dejavu_sans_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_sans_path))
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_export_formats():
        """Возвращает доступные форматы экспорта"""
        return [
            ('csv', 'CSV (Excel)'),
            ('json', 'JSON'),
            ('pdf', 'PDF'),
        ]