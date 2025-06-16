from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Hall, Movie, Screening, Seat, Ticket


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