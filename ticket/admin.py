import os
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from .export_utils import LogExporter
from .forms import ReportFilterForm, MovieForm
from .logging_utils import OperationLogger
from .models import BackupManager, PasswordResetRequest, PendingRegistration, Report, OperationLog
from .models import Hall, Movie, Screening, Seat, Ticket, User, Genre
from .report_utils import ReportGenerator


class LoggingModelAdmin(admin.ModelAdmin):
    """Базовый класс для автоматического логирования операций в админке"""

    def save_model(self, request, obj, form, change):
        """Логирование создания/изменения объектов"""
        action = 'UPDATE' if change else 'CREATE'
        OperationLogger.log_model_operation(
            request=request,
            action_type=action,
            instance=obj,
            description=f"{action} {obj._meta.verbose_name} '{str(obj)}'"
        )
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Логирование удаления объектов"""
        OperationLogger.log_model_operation(
            request=request,
            action_type='DELETE',
            instance=obj,
            description=f"DELETE {obj._meta.verbose_name} '{str(obj)}'"
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Логирование массового удаления"""
        for obj in queryset:
            OperationLogger.log_model_operation(
                request=request,
                action_type='DELETE',
                instance=obj,
                description=f"DELETE {obj._meta.verbose_name} '{str(obj)}' (mass delete)"
            )
        super().delete_queryset(request, queryset)


@admin.register(User)
class CustomUserAdmin(LoggingModelAdmin, UserAdmin):
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
class HallAdmin(LoggingModelAdmin):
    list_display = ('name', 'rows', 'seats_per_row', 'total_seats')
    list_filter = ('name',)
    search_fields = ('name', 'description')

    def total_seats(self, obj):
        return obj.rows * obj.seats_per_row

    total_seats.short_description = 'Всего мест'


@admin.register(Genre)
class GenreAdmin(LoggingModelAdmin):
    """Админ-класс для управления жанрами"""
    list_display = ('name', 'movie_count', 'created_at')
    search_fields = ('name',)
    list_per_page = 20
    readonly_fields = ('created_at',)

    def movie_count(self, obj):
        """Количество фильмов в этом жанре"""
        return obj.movie_set.count()

    movie_count.short_description = 'Количество фильмов'


@admin.register(Movie)
class MovieAdmin(LoggingModelAdmin):
    list_display = ('title', 'genre', 'duration_formatted', 'has_poster', 'screening_count')
    search_fields = ('title', 'genre__name', 'short_description', 'description')
    list_filter = ('genre',)
    list_per_page = 20
    form = MovieForm  # Используем кастомную форму
    readonly_fields = ('created_at',) if hasattr(Movie, 'created_at') else ()

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

    def screening_count(self, obj):
        """Количество сеансов для этого фильма"""
        return obj.screening_set.count()

    screening_count.short_description = 'Сеансы'


@admin.register(Screening)
class ScreeningAdmin(LoggingModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'end_time', 'price', 'is_active_screening')
    list_filter = ('hall', 'start_time', 'movie')
    search_fields = ('movie__title', 'hall__name')
    readonly_fields = ('end_time',)  # Делаем поле только для чтения
    list_per_page = 20
    date_hierarchy = 'start_time'

    def is_active_screening(self, obj):
        return obj.start_time > timezone.now()

    is_active_screening.boolean = True
    is_active_screening.short_description = 'Активный'


@admin.register(Seat)
class SeatAdmin(LoggingModelAdmin):
    list_display = ('hall', 'row', 'number')
    list_filter = ('hall', 'row')
    search_fields = ('hall__name',)

    # Запрещаем добавление новых мест
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(LoggingModelAdmin):
    list_display = ('user', 'screening', 'seat', 'purchase_date')
    list_filter = ('screening', 'purchase_date', 'user')
    search_fields = ('user__email', 'screening__movie__title')
    readonly_fields = ('purchase_date',)
    list_per_page = 20


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(LoggingModelAdmin):
    list_display = ('email', 'name', 'surname', 'created_at', 'is_expired')
    list_filter = ('created_at',)
    search_fields = ('email', 'name', 'surname')
    readonly_fields = ('created_at',)

    # Запрещаем добавление новых ожидающих регистраций
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = 'Просрочен'


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(LoggingModelAdmin):
    list_display = ('email', 'created_at', 'is_expired', 'is_used')
    list_filter = ('created_at', 'is_used')
    search_fields = ('email',)
    readonly_fields = ('created_at',)

    # Запрещаем добавление новых запросов восстановления пароля
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = 'Просрочен'


# Функции для actions
def create_full_backup(modeladmin, request, queryset):
    """Action для создания полного бэкапа"""
    try:
        call_command('backup_db')
        OperationLogger.log_backup_operation(
            request=request,
            backup_type='FULL',
            description='Создан полный бэкап базы данных'
        )
        messages.success(request, '✅ Full backup created successfully!')
    except Exception as e:
        OperationLogger.log_operation(
            request=request,
            action_type='BACKUP',
            module_type='BACKUPS',
            description=f'Ошибка создания бэкапа: {str(e)}',
            additional_data={'error': str(e)}
        )
        messages.error(request, f'❌ Error creating backup: {str(e)}')


create_full_backup.short_description = "📦 Create full database backup"


def create_daily_backup_today(modeladmin, request, queryset):
    """Action для создания дневного бэкапа за сегодня"""
    from datetime import date
    try:
        call_command('backup_db', f'--date={date.today()}')
        OperationLogger.log_backup_operation(
            request=request,
            backup_type='DAILY',
            description=f'Создан дневной бэкап за {date.today()}'
        )
        messages.success(request, f'✅ Daily backup for {date.today()} created successfully!')
    except Exception as e:
        OperationLogger.log_operation(
            request=request,
            action_type='BACKUP',
            module_type='BACKUPS',
            description=f'Ошибка создания дневного бэкапа: {str(e)}',
            additional_data={'error': str(e)}
        )
        messages.error(request, f'❌ Error creating daily backup: {str(e)}')


create_daily_backup_today.short_description = "📅 Create daily backup for today"


@admin.register(BackupManager)
class BackupManagerAdmin(LoggingModelAdmin):
    list_display = ['name', 'backup_type', 'backup_date', 'created_at', 'file_status', 'file_size']
    list_filter = ['backup_type', 'created_at', 'backup_date']
    readonly_fields = ['name', 'backup_file', 'created_at', 'backup_type', 'backup_date']
    actions = [create_full_backup, create_daily_backup_today]

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

    def has_change_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """Логирование удаления бэкапа"""
        OperationLogger.log_operation(
            request=request,
            action_type='DELETE',
            module_type='BACKUPS',
            description=f'Удален файл бэкапа {obj.name}',
            object_id=obj.id,
            object_repr=obj.name
        )
        # Удаляем файл при удалении записи из админки
        file_path = obj.get_file_path()
        if os.path.exists(file_path):
            os.remove(file_path)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Логирование массового удаления бэкапов"""
        for obj in queryset:
            OperationLogger.log_operation(
                request=request,
                action_type='DELETE',
                module_type='BACKUPS',
                description=f'Удален файл бэкапа {obj.name} (mass delete)',
                object_id=obj.id,
                object_repr=obj.name
            )
            file_path = obj.get_file_path()
            if os.path.exists(file_path):
                os.remove(file_path)
        super().delete_queryset(request, queryset)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('backup-management/', self.admin_site.admin_view(self.backup_management_view),
                 name='ticket_backupmanager_backup_management'),
        ]
        return custom_urls + urls

    def backup_management_view(self, request):
        """Страница управления бэкапами"""
        from django.core.management import call_command

        backups = BackupManager.objects.all().order_by('-created_at')

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'full_backup':
                try:
                    call_command('backup_db')
                    OperationLogger.log_backup_operation(
                        request=request,
                        backup_type='FULL',
                        description='Создан полный бэкап базы данных через страницу управления'
                    )
                    messages.success(request, '✅ Полный бэкап создан успешно!')
                except Exception as e:
                    OperationLogger.log_operation(
                        request=request,
                        action_type='BACKUP',
                        module_type='BACKUPS',
                        description=f'Ошибка создания полного бэкапа: {str(e)}',
                        additional_data={'error': str(e)}
                    )
                    messages.success(request, '✅ Полный бэкап создан успешно!')

            elif action == 'daily_backup':
                backup_date = request.POST.get('backup_date')
                if backup_date:
                    try:
                        call_command('backup_db', f'--date={backup_date}')
                        OperationLogger.log_backup_operation(
                            request=request,
                            backup_type='DAILY',
                            description=f'Создан дневной бэкап за {backup_date} через страницу управления'
                        )
                        messages.success(request, f'✅ Дневной бэкап за {backup_date} создан успешно!')
                    except Exception as e:
                        OperationLogger.log_operation(
                            request=request,
                            action_type='BACKUP',
                            module_type='BACKUPS',
                            description=f'Ошибка создания дневного бэкапа: {str(e)}',
                            additional_data={'error': str(e)}
                        )
                        messages.success(request, f'✅ Дневной бэкап за {backup_date} создан успешно!')
                else:
                    messages.error(request, '❌ Выберите дату для дневного бэкапа')

            # Обновляем список бэкапов после создания
            backups = BackupManager.objects.all().order_by('-created_at')

        context = {
            'title': 'Управление бэкапами',
            'backups': backups,
            **self.admin_site.each_context(request),
        }

        return render(request, 'admin/backup_management.html', context)


@admin.register(Report)
class ReportAdmin(LoggingModelAdmin):
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

            # Логируем просмотр отчета
            OperationLogger.log_operation(
                request=request,
                action_type='VIEW',
                module_type='REPORTS',
                description=f'Просмотр отчета: {report_type}',
                additional_data={
                    'period': period,
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None
                }
            )

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

                # Логируем экспорт отчета
                OperationLogger.log_report_export(
                    request=request,
                    report_type=report_type,
                    format_type='PDF',
                    filters={
                        'period': period,
                        'start_date': str(start_date) if start_date else None,
                        'end_date': str(end_date) if end_date else None
                    }
                )

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


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    """Админ-класс для логов операций"""

    list_display = [
        'timestamp', 'user', 'action_type', 'module_type',
        'description_short', 'object_repr_short', 'ip_address'
    ]
    list_filter = [
        'action_type', 'module_type', 'timestamp', 'user'
    ]
    search_fields = [
        'description', 'user__email', 'object_repr',
        'ip_address', 'additional_data'
    ]
    readonly_fields = [
        'timestamp', 'user', 'action_type', 'module_type',
        'description', 'ip_address', 'user_agent', 'object_id',
        'object_repr', 'additional_data_display'
    ]
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def description_short(self, obj):
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description

    description_short.short_description = 'Описание'

    def object_repr_short(self, obj):
        return obj.object_repr[:30] + '...' if obj.object_repr and len(obj.object_repr) > 30 else obj.object_repr

    object_repr_short.short_description = 'Объект'

    def additional_data_display(self, obj):
        return obj.get_additional_data_display()

    additional_data_display.short_description = 'Дополнительные данные'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('export-logs/', self.admin_site.admin_view(self.export_logs_view), name='ticket_operationlog_export'),
        ]
        return custom_urls + urls

    def export_logs_view(self, request):
        """Страница экспорта логов"""
        from .forms import LogExportForm

        form = LogExportForm(request.GET or None)
        context = {
            'form': form,
            'title': 'Экспорт логов операций',
            **self.admin_site.each_context(request),
        }

        if form.is_valid():
            # Получаем отфильтрованные логи
            queryset = self.get_export_queryset(form.cleaned_data)

            format_type = form.cleaned_data['format_type']

            # Логируем операцию экспорта
            OperationLogger.log_operation(
                request=request,
                action_type='EXPORT',
                module_type='SYSTEM',
                description=f'Экспорт логов в формате {format_type.upper()}',
                additional_data={
                    'start_date': str(form.cleaned_data.get('start_date')) if form.cleaned_data.get(
                        'start_date') else None,
                    'end_date': str(form.cleaned_data.get('end_date')) if form.cleaned_data.get('end_date') else None,
                    'action_type': form.cleaned_data.get('action_type'),
                    'module_type': form.cleaned_data.get('module_type'),
                    'user': str(form.cleaned_data.get('user')) if form.cleaned_data.get('user') else None,
                }
            )

            # Экспортируем в выбранный формат
            if format_type == 'csv':
                return LogExporter.export_logs_to_csv(queryset)
            elif format_type == 'json':
                return LogExporter.export_logs_to_json(queryset)
            elif format_type == 'pdf':
                return LogExporter.export_logs_to_pdf(queryset)

        return render(request, 'ticket/admin/export_logs.html', context)

    def get_export_queryset(self, filters):
        """Получение queryset для экспорта на основе фильтров"""
        queryset = OperationLog.objects.all()

        # Фильтр по дате
        if filters.get('start_date'):
            queryset = queryset.filter(timestamp__date__gte=filters['start_date'])
        if filters.get('end_date'):
            queryset = queryset.filter(timestamp__date__lte=filters['end_date'])

        # Фильтр по типу действия
        if filters.get('action_type'):
            queryset = queryset.filter(action_type=filters['action_type'])

        # Фильтр по модулю
        if filters.get('module_type'):
            queryset = queryset.filter(module_type=filters['module_type'])

        # Фильтр по пользователю
        if filters.get('user'):
            queryset = queryset.filter(user=filters['user'])

        return queryset.order_by('-timestamp')

    def changelist_view(self, request, extra_context=None):
        """Добавляем кнопку экспорта в changelist"""
        if extra_context is None:
            extra_context = {}

        extra_context['export_url'] = '/admin/ticket/operationlog/export-logs/'
        return super().changelist_view(request, extra_context=extra_context)