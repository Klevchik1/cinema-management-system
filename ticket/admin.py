from django.contrib.auth.admin import UserAdmin
from .models import Hall, Movie, Screening, Seat, Ticket, User
from django.core.management import call_command
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
import os
from .models import BackupManager, PasswordResetRequest, PendingRegistration, Report
from django.http import HttpResponse
from .report_utils import ReportGenerator
from .forms import ReportFilterForm
from django.contrib.admin.models import LogEntry


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'name', 'surname', 'number', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'surname', 'number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'surname', 'number', 'password1', 'password2'),
        }),
    )
    ordering = ('email',)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'rows', 'seats_per_row', 'total_seats')
    list_filter = ('name',)
    search_fields = ('name', 'description')

    def total_seats(self, obj):
        return obj.rows * obj.seats_per_row

    total_seats.short_description = 'Всего мест'


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'duration_formatted', 'has_poster')
    search_fields = ('title', 'genre', 'short_description', 'description')
    list_filter = ('genre',)
    list_per_page = 20

    def duration_formatted(self, obj):
        total_minutes = obj.duration.seconds // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}ч {minutes}мин"

    duration_formatted.short_description = 'Длительность'

    def has_poster(self, obj):
        return bool(obj.poster)

    has_poster.boolean = True
    has_poster.short_description = 'Есть постер'


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'end_time', 'price', 'is_active_screening')
    list_filter = ('hall', 'start_time', 'movie')
    search_fields = ('movie__title', 'hall__name')
    readonly_fields = ('end_time',)
    list_per_page = 20
    date_hierarchy = 'start_time'

    def is_active_screening(self, obj):
        return obj.start_time > timezone.now()

    is_active_screening.boolean = True
    is_active_screening.short_description = 'Активный'


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('hall', 'row', 'number')
    list_filter = ('hall', 'row')
    search_fields = ('hall__name',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'screening', 'seat', 'purchase_date')
    list_filter = ('screening', 'purchase_date', 'user')
    search_fields = ('user__email', 'screening__movie__title')
    readonly_fields = ('purchase_date',)
    list_per_page = 20


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'surname', 'created_at', 'is_expired')
    list_filter = ('created_at',)
    search_fields = ('email', 'name', 'surname')
    readonly_fields = ('created_at',)

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = 'Просрочен'


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'is_expired', 'is_used')
    list_filter = ('created_at', 'is_used')
    search_fields = ('email',)
    readonly_fields = ('created_at',)

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = 'Просрочен'


# Функции для actions
def create_full_backup(modeladmin, request, queryset):
    """Action для создания полного бэкапа"""
    try:
        call_command('backup_db')
        messages.success(request, '✅ Full backup created successfully!')
    except Exception as e:
        messages.error(request, f'❌ Error creating backup: {str(e)}')


create_full_backup.short_description = "📦 Create full database backup"


def create_daily_backup_today(modeladmin, request, queryset):
    """Action для создания дневного бэкапа за сегодня"""
    from datetime import date
    try:
        call_command('backup_db', f'--date={date.today()}')
        messages.success(request, f'✅ Daily backup for {date.today()} created successfully!')
    except Exception as e:
        messages.error(request, f'❌ Error creating daily backup: {str(e)}')


create_daily_backup_today.short_description = "📅 Create daily backup for today"


# Админка для BackupManager с кастомной view
@admin.register(BackupManager)
class BackupManagerAdmin(admin.ModelAdmin):
    list_display = ['name', 'backup_type', 'backup_date', 'created_at', 'file_status', 'file_size']
    list_filter = ['backup_type', 'created_at', 'backup_date']
    readonly_fields = ['name', 'backup_file', 'created_at', 'backup_type', 'backup_date']

    def file_status(self, obj):
        if obj.file_exists():
            return "✅ Available"
        return "❌ Missing"

    file_status.short_description = "Status"

    def file_size(self, obj):
        return obj.file_size()

    file_size.short_description = "Size"

    def has_add_permission(self, request):
        return False

    def delete_model(self, request, obj):
        """Удаляем файл при удалении записи из админки"""
        file_path = obj.get_file_path()
        if os.path.exists(file_path):
            os.remove(file_path)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Удаляем файлы при массовом удалении"""
        for obj in queryset:
            file_path = obj.get_file_path()
            if os.path.exists(file_path):
                os.remove(file_path)
        super().delete_queryset(request, queryset)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Админ-класс для управления отчетами"""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.reports_view), name='ticket_reports'),
        ]
        return custom_urls + urls

    def reports_view(self, request):
        """Страница отчетов в админке"""
        form = ReportFilterForm(request.GET or None)
        context = {
            'form': form,
            'report_data': None,
            'report_type': None,
            'title': 'Отчеты кинотеатра',
            **self.admin_site.each_context(request),
        }

        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            period = form.cleaned_data['period']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            context['report_type'] = report_type
            context['filters'] = {
                'period': period,
                'start_date': start_date,
                'end_date': end_date
            }

            if report_type == 'revenue':
                context['report_data'] = ReportGenerator.get_revenue_stats(period, start_date, end_date)
            elif report_type == 'movies':
                context['report_data'] = ReportGenerator.get_popular_movies(start_date=start_date, end_date=end_date)
            elif report_type == 'halls':
                context['report_data'] = ReportGenerator.get_hall_occupancy(start_date=start_date, end_date=end_date)
            elif report_type == 'sales':
                context['report_data'] = ReportGenerator.get_sales_statistics(start_date=start_date, end_date=end_date)

        # Обработка экспорта в PDF
        if request.method == 'POST' and 'export_pdf' in request.POST:
            if form.is_valid():
                report_type = form.cleaned_data['report_type']
                period = form.cleaned_data['period']
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']

                # Получаем данные для отчета
                if report_type == 'revenue':
                    report_data = ReportGenerator.get_revenue_stats(period, start_date, end_date)
                    report_title = f"Финансовая статистика ({period})"
                elif report_type == 'movies':
                    report_data = ReportGenerator.get_popular_movies(start_date=start_date, end_date=end_date)
                    report_title = "Популярные фильмы"
                elif report_type == 'halls':
                    report_data = ReportGenerator.get_hall_occupancy(start_date=start_date, end_date=end_date)
                    report_title = "Загруженность залов"
                elif report_type == 'sales':
                    report_data = ReportGenerator.get_sales_statistics(start_date=start_date, end_date=end_date)
                    report_title = "Статистика продаж"
                else:
                    report_data = []
                    report_title = "Отчет"

                # Генерируем PDF
                try:
                    from .pdf_utils import generate_pdf_report
                    pdf_buffer = generate_pdf_report(report_data, report_type, report_title, {
                        'period': period,
                        'start_date': start_date,
                        'end_date': end_date
                    })

                    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
                    filename = f"отчет_{report_type}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response

                except Exception as e:
                    messages.error(request, f'Ошибка при генерации PDF: {str(e)}')

        return render(request, 'ticket/admin/reports.html', context)

    def changelist_view(self, request, extra_context=None):
        """Перенаправляем на страницу отчетов при входе в раздел"""
        return self.reports_view(request)