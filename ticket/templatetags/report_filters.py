from django import template

register = template.Library()

@register.filter
def sum_revenue(data):
    """Сумма выручки из данных отчета"""
    return sum(item['revenue'] or 0 for item in data)

@register.filter
def sum_tickets(data):
    """Сумма билетов из данных отчета"""
    return sum(item['tickets_sold'] for item in data)

@register.filter
def get_period_display(period):
    """Отображение периода на русском"""
    period_map = {
        'daily': 'по дням',
        'weekly': 'по неделям',
        'monthly': 'по месяцам'
    }
    return period_map.get(period, '')