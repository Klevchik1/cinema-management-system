from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from django.core.management import call_command
from .models import Hall, Movie, Screening, Seat, Ticket, User, BackupManager
from .forms import DailyBackupForm


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
    list_display = ('title', 'genre', 'duration_formatted')
    search_fields = ('title', 'genre')

    def duration_formatted(self, obj):
        hours, minutes = divmod(obj.duration.seconds // 60, 60)
        return f"{hours}ч {minutes}мин"


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


# Кастомная админка для BackupManager
@admin.register(BackupManager)
class BackupManagerAdmin(admin.ModelAdmin):
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
        return False  # Запрещаем ручное добавление

    # Добавляем кастомную view для выбора даты
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('daily-backup/', self.admin_site.admin_view(self.daily_backup_view), name='daily_backup'),
        ]
        return custom_urls + urls

    def daily_backup_view(self, request):
        if request.method == 'POST':
            form = DailyBackupForm(request.POST)
            if form.is_valid():
                selected_date = form.cleaned_data['backup_date']
                try:
                    call_command('backup_db', f'--date={selected_date}')
                    messages.success(request, f'✅ Daily backup for {selected_date} created successfully!')
                except Exception as e:
                    messages.error(request, f'❌ Error: {str(e)}')

                return HttpResponseRedirect('../')
        else:
            form = DailyBackupForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Create Daily Backup',
            'opts': self.model._meta,
        }
        return render(request, 'admin/daily_backup_form.html', context)


# Добавляем actions к уже зарегистрированным моделям
# Находим уже зарегистрированные админ-классы и добавляем actions
def add_backup_actions():
    # Получаем все зарегистрированные модели
    registered_models = admin.site._registry

    for model, model_admin in registered_models.items():
        # Добавляем actions если их еще нет
        if hasattr(model_admin, 'actions'):
            # Создаем новый список actions если нужно
            current_actions = list(model_admin.actions) if model_admin.actions else []

            # Добавляем наши actions если их еще нет
            if create_full_backup not in current_actions:
                current_actions.append(create_full_backup)
            if create_daily_backup_today not in current_actions:
                current_actions.append(create_daily_backup_today)

            model_admin.actions = current_actions


# Вызываем функцию после загрузки всех моделей
add_backup_actions()