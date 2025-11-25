from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Ticket, Screening, Movie, Hall
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    @staticmethod
    def get_revenue_stats(period='daily', start_date=None, end_date=None):
        """Статистика выручки по периодам"""
        # Базовый queryset
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

        return list(data)

    @staticmethod
    def get_popular_movies(limit=10, start_date=None, end_date=None):
        """Самые популярные фильмы"""
        movies = Movie.objects.annotate(
            tickets_sold=Count('screening__ticket'),
            total_revenue=Sum('screening__ticket__screening__price')
        ).filter(tickets_sold__gt=0)

        # Фильтр по дате если указан
        if start_date or end_date:
            screenings_filter = {}
            if start_date:
                screenings_filter['screening__ticket__purchase_date__date__gte'] = start_date
            if end_date:
                screenings_filter['screening__ticket__purchase_date__date__lte'] = end_date

            movies = movies.filter(**screenings_filter).distinct()

        return list(movies.order_by('-tickets_sold')[:limit])

    @staticmethod
    def get_hall_occupancy(start_date=None, end_date=None):
        """Загруженность залов"""
        halls = Hall.objects.annotate(
            total_seats=Count('seat'),
            total_screenings=Count('screening'),
            sold_tickets=Count('screening__ticket'),
            total_revenue=Sum('screening__ticket__screening__price')
        )

        # Рассчитываем процент загруженности
        hall_list = []
        for hall in halls:
            total_possible_tickets = hall.total_seats * hall.total_screenings
            if total_possible_tickets > 0:
                occupancy_percent = (hall.sold_tickets / total_possible_tickets) * 100
            else:
                occupancy_percent = 0

            hall_data = {
                'id': hall.id,
                'name': hall.name,
                'total_seats': hall.total_seats,
                'total_screenings': hall.total_screenings,
                'sold_tickets': hall.sold_tickets,
                'total_revenue': hall.total_revenue or 0,
                'occupancy_percent': round(occupancy_percent, 1)
            }
            hall_list.append(hall_data)

        return hall_list

    @staticmethod
    def get_sales_statistics(start_date=None, end_date=None):
        """Общая статистика продаж"""
        tickets = Ticket.objects.select_related('screening')

        # Фильтр по дате если указан
        if start_date:
            tickets = tickets.filter(purchase_date__date__gte=start_date)
        if end_date:
            tickets = tickets.filter(purchase_date__date__lte=end_date)

        total_tickets = tickets.count()
        total_revenue_result = tickets.aggregate(
            total=Sum('screening__price')
        )
        total_revenue = total_revenue_result['total'] or 0

        avg_ticket_price_result = tickets.aggregate(
            avg=Avg('screening__price')
        )
        avg_ticket_price = avg_ticket_price_result['avg'] or 0

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