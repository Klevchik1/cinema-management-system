from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import Ticket, Screening, Movie, Hall
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    @staticmethod
    def get_revenue_stats(period='daily', start_date=None, end_date=None):
        """Статистика выручки по периодам"""
        # Базовый queryset - только оплаченные билеты
        tickets = Ticket.objects.select_related('screening').filter(
            screening__isnull=False
        )

        # Фильтр по дате если указан
        if start_date:
            tickets = tickets.filter(purchase_date__date__gte=start_date)
        if end_date:
            tickets = tickets.filter(purchase_date__date__lte=end_date)

        if period == 'daily':
            # Группировка по дням
            data = tickets.extra({
                'date': "date(purchase_date)"
            }).values('date').annotate(
                revenue=Sum('screening__price'),
                tickets_sold=Count('id')
            ).order_by('date')

        elif period == 'weekly':
            # Группировка по неделям
            data = tickets.extra({
                'week': "EXTRACT(week FROM purchase_date)",
                'year': "EXTRACT(year FROM purchase_date)"
            }).values('year', 'week').annotate(
                revenue=Sum('screening__price'),
                tickets_sold=Count('id')
            ).order_by('year', 'week')

        elif period == 'monthly':
            # Группировка по месяцам
            data = tickets.extra({
                'month': "EXTRACT(month FROM purchase_date)",
                'year': "EXTRACT(year FROM purchase_date)"
            }).values('year', 'month').annotate(
                revenue=Sum('screening__price'),
                tickets_sold=Count('id')
            ).order_by('year', 'month')

        # Преобразуем в список и заменяем None на 0
        result = []
        for item in data:
            result.append({
                'date': item.get('date'),
                'week': item.get('week'),
                'month': item.get('month'),
                'year': item.get('year'),
                'revenue': item['revenue'] or 0,
                'tickets_sold': item['tickets_sold']
            })

        return result

    @staticmethod
    def get_popular_movies(limit=10, start_date=None, end_date=None):
        """Самые популярные фильмы - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # Создаем базовый запрос с правильной агрегацией
        movies = Movie.objects.annotate(
            tickets_sold=Count(
                'screening__ticket',
                filter=Q(screening__ticket__isnull=False)
            ),
            total_revenue=Sum(
                'screening__ticket__screening__price',
                filter=Q(screening__ticket__isnull=False)
            )
        ).filter(tickets_sold__gt=0)

        # Фильтр по дате если указан
        if start_date or end_date:
            date_filter = Q()
            if start_date:
                date_filter &= Q(screening__ticket__purchase_date__date__gte=start_date)
            if end_date:
                date_filter &= Q(screening__ticket__purchase_date__date__lte=end_date)

            # Пересчитываем аннотации с фильтром по дате
            movies = Movie.objects.filter(date_filter).annotate(
                tickets_sold=Count(
                    'screening__ticket',
                    filter=date_filter
                ),
                total_revenue=Sum(
                    'screening__ticket__screening__price',
                    filter=date_filter
                )
            ).filter(tickets_sold__gt=0).distinct()

        return list(movies.order_by('-tickets_sold')[:limit])

    @staticmethod
    def get_hall_occupancy(start_date=None, end_date=None):
        """Загруженность залов - ИСПРАВЛЕННАЯ ВЕРСИЯ с правильным подсчетом"""
        # Базовый запрос для залов
        halls = Hall.objects.all()

        hall_list = []
        for hall in halls:
            # Получаем сеансы с фильтром по дате
            screenings = hall.screening_set.all()
            if start_date:
                screenings = screenings.filter(start_time__date__gte=start_date)
            if end_date:
                screenings = screenings.filter(start_time__date__lte=end_date)

            total_screenings = screenings.count()

            # Получаем билеты для этих сеансов - ИСПРАВЛЕНО: тот же фильтр по дате
            tickets = Ticket.objects.filter(
                screening__in=screenings
            )
            if start_date:
                tickets = tickets.filter(purchase_date__date__gte=start_date)
            if end_date:
                tickets = tickets.filter(purchase_date__date__lte=end_date)

            sold_tickets = tickets.count()

            # Рассчитываем общее количество возможных билетов
            total_seats = hall.rows * hall.seats_per_row
            total_possible_tickets = total_seats * total_screenings

            # Рассчитываем процент загруженности
            if total_possible_tickets > 0:
                occupancy_percent = (sold_tickets / total_possible_tickets) * 100
            else:
                occupancy_percent = 0

            # Считаем выручку
            total_revenue_result = tickets.aggregate(
                total=Sum('screening__price')
            )
            total_revenue = total_revenue_result['total'] or 0

            hall_data = {
                'id': hall.id,
                'name': hall.name,
                'total_seats': total_seats,
                'total_screenings': total_screenings,
                'sold_tickets': sold_tickets,
                'total_revenue': total_revenue,
                'occupancy_percent': round(occupancy_percent, 1)
            }
            hall_list.append(hall_data)

        return sorted(hall_list, key=lambda x: x['occupancy_percent'], reverse=True)

    @staticmethod
    def get_sales_statistics(start_date=None, end_date=None):
        """Общая статистика продаж - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        tickets = Ticket.objects.select_related('screening')

        # Фильтр по дате если указан
        if start_date:
            tickets = tickets.filter(purchase_date__date__gte=start_date)
        if end_date:
            tickets = tickets.filter(purchase_date__date__lte=end_date)

        total_tickets = tickets.count()

        # Считаем выручку через агрегацию
        revenue_result = tickets.aggregate(
            total=Sum('screening__price')
        )
        total_revenue = revenue_result['total'] or 0

        # Средняя цена билета
        if total_tickets > 0:
            avg_ticket_price = total_revenue / total_tickets
        else:
            avg_ticket_price = 0

        # Самый популярный фильм
        popular_movie_result = tickets.values(
            'screening__movie__title'
        ).annotate(
            count=Count('id')
        ).order_by('-count').first()

        popular_movie = popular_movie_result['screening__movie__title'] if popular_movie_result else 'Нет данных'
        popular_movie_tickets = popular_movie_result['count'] if popular_movie_result else 0

        return {
            'total_tickets': total_tickets,
            'total_revenue': float(total_revenue),
            'avg_ticket_price': round(float(avg_ticket_price), 2),
            'popular_movie': popular_movie,
            'popular_movie_tickets': popular_movie_tickets
        }