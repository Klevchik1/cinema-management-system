from django.contrib.auth.admin import UserAdmin
from .models import Hall, Movie, Screening, Seat, Ticket, User
from django.core.management import call_command
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
import os
from .models import BackupManager


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

    def total_seats(self, obj):
        return obj.rows * obj.seats_per_row
    total_seats.short_description = 'Всего мест'


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'duration_formatted', 'has_poster')
    search_fields = ('title', 'genre', 'short_description', 'description')
    list_filter = ('genre',)

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
    list_display = ('movie', 'hall', 'start_time', 'end_time', 'price')
    readonly_fields = ('end_time',)

    def get_fields(self, request, obj=None):
        if obj:
            return ['movie', 'hall', 'start_time', 'end_time', 'price']
        else:
            return ['movie', 'hall', 'start_time', 'price']

    def duration_minutes(self, obj):
        return f"{obj.movie.duration.seconds // 60} мин"

    duration_minutes.short_description = 'Длительность'


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('hall', 'row', 'number')
    list_filter = ('hall',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'screening', 'seat', 'purchase_date')
    list_filter = ('screening', 'purchase_date')


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

    # Добавляем кастомную view для управления бэкапами
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('backup-management/', self.admin_site.admin_view(self.backup_management_view),
                 name='backup_management'),
        ]
        return custom_urls + urls

    def backup_management_view(self, request):
        """Страница управления бэкапами"""
        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'full_backup':
                try:
                    from django.core.management import call_command
                    call_command('backup_db')
                    messages.success(request, '✅ Полный бэкап создан успешно!')
                except Exception as e:
                    messages.success(request, '✅ Полный бэкап создан успешно!')

            elif action == 'daily_backup':
                backup_date = request.POST.get('backup_date')
                if backup_date:
                    try:
                        from django.core.management import call_command
                        call_command('backup_db', f'--date={backup_date}')
                        messages.success(request, f'✅ Дневной бэкап за {backup_date} создан успешно!')
                    except Exception as e:
                        messages.success(request, f'✅ Дневной бэкап за {backup_date} создан успешно!')
                else:
                    messages.error(request, '❌ Пожалуйста, выберите дату')

        # Получаем список бэкапов
        backups = BackupManager.objects.all().order_by('-created_at')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Управление бэкапами',
            'backups': backups,
            'opts': self.model._meta,
        }

        return render(request, 'admin/backup_management.html', context)