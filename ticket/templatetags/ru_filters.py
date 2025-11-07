from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def russian_date(value):
    """
    Фильтр для преобразования даты в русский формат
    """
    if not value:
        return ""

    # Русские названия месяцев
    month_names = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    try:
        # Если значение - datetime объект
        day = value.day
        month = month_names[value.month]
        year = value.year

        return f"{day} {month} {year}"
    except (AttributeError, KeyError):
        return str(value)


@register.filter
def russian_datetime(value):
    """
    Фильтр для преобразования даты и времени в русский формат
    """
    if not value:
        return ""

    try:
        date_part = russian_date(value)
        time_part = value.strftime("%H:%M")

        return f"{date_part} {time_part}"
    except AttributeError:
        return str(value)


@register.filter
def russian_date_short(value):
    """
    Фильтр для короткого формата даты (без года)
    """
    if not value:
        return ""

    try:
        # Русские названия месяцев
        month_names = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }

        day = value.day
        month = month_names[value.month]

        return f"{day} {month}"
    except (AttributeError, KeyError):
        return str(value)