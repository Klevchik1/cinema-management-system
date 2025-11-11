from django.shortcuts import render
from .forms import RegistrationForm, LoginForm, UserUpdateForm, CustomPasswordChangeForm
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Screening, Ticket, Seat, Movie, Hall, User
from django.utils import timezone
from .utils import generate_ticket_pdf
from django.http import HttpResponse
import json
from django.contrib.admin.views.decorators import staff_member_required
from .forms import MovieForm, HallForm, ScreeningForm
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.db.models import Q, Count
import logging
from datetime import datetime
import uuid
from django.urls import reverse
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@staff_member_required
def admin_dashboard(request):
    return render(request, 'ticket/admin_dashboard.html')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = RegistrationForm()
    return render(request, 'ticket/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()
    return render(request, 'ticket/login.html', {'form': form})


def home(request):
    local_now = timezone.localtime(timezone.now())

    search_query = request.GET.get('search', '')
    hall_filter = request.GET.get('hall', '')
    genre_filter = request.GET.get('genre', '')
    time_from = request.GET.get('time_from', '')
    time_to = request.GET.get('time_to', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Получаем фильмы с предварительной загрузкой сеансов
    movies = Movie.objects.prefetch_related('screening_set__hall').all()

    # Применяем фильтры к сеансам
    screenings_filter = Q(start_time__gt=local_now)

    if search_query:
        movies = movies.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if genre_filter:
        movies = movies.filter(genre=genre_filter)

    if hall_filter:
        screenings_filter &= Q(hall_id=hall_filter)

    if time_from:
        time_from_obj = datetime.strptime(time_from, '%H:%M').time()
        screenings_filter &= Q(start_time__time__gte=time_from_obj)

    if time_to:
        time_to_obj = datetime.strptime(time_to, '%H:%M').time()
        screenings_filter &= Q(start_time__time__lte=time_to_obj)

    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        screenings_filter &= Q(start_time__date__gte=date_from_obj)

    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        screenings_filter &= Q(start_time__date__lte=date_to_obj)

    # Собираем данные для каждого фильма
    movies_data = []
    for movie in movies:
        upcoming_screenings = movie.screening_set.filter(screenings_filter).order_by('start_time')[:3]

        # Если есть фильтры по залу/времени и нет подходящих сеансов - пропускаем фильм
        if (hall_filter or time_from or time_to or date_from or date_to) and not upcoming_screenings:
            continue

        movies_data.append({
            'movie': movie,
            'upcoming_screenings': upcoming_screenings
        })

    genres = Movie.objects.values_list('genre', flat=True).distinct()

    return render(request, 'ticket/home.html', {
        'movies': movies_data,
        'halls': Hall.objects.all(),
        'genres': genres,
        'current_filters': {
            'search': search_query,
            'hall': hall_filter,
            'genre': genre_filter,
            'time_from': time_from,
            'time_to': time_to,
            'date_from': date_from,
            'date_to': date_to
        }
    })


def user_logout(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('login')


def screening_detail(request, screening_id):
    screening = get_object_or_404(Screening, pk=screening_id)
    seats = Seat.objects.filter(hall=screening.hall).order_by('row', 'number')
    booked_tickets = Ticket.objects.filter(screening=screening)
    booked_seat_ids = [ticket.seat.id for ticket in booked_tickets]

    rows = {}
    for seat in seats:
        if seat.row not in rows:
            rows[seat.row] = []
        rows[seat.row].append(seat)

    return render(request, 'ticket/screening_detail.html', {
        'screening': screening,
        'rows': rows,
        'booked_seat_ids': booked_seat_ids,
        'is_guest': not request.user.is_authenticated  # Добавляем флаг гостя
    })


@login_required
@require_POST
def book_tickets(request):
    screening_id = request.POST.get('screening_id')
    selected_seats = request.POST.get('selected_seats')

    if not selected_seats:
        messages.error(request, "Выберите хотя бы одно место.")
        return redirect('screening_detail', screening_id=screening_id)

    try:
        seat_ids = json.loads(selected_seats)
    except json.JSONDecodeError:
        messages.error(request, "Ошибка при обработке выбранных мест. Попробуйте снова.")
        return redirect('screening_detail', screening_id=screening_id)

    if not seat_ids:
        messages.error(request, "Выберите хотя бы одно место.")
        return redirect('screening_detail', screening_id=screening_id)

    screening = get_object_or_404(Screening, pk=screening_id)

    # Проверяем доступность мест
    for seat_id in seat_ids:
        seat = get_object_or_404(Seat, pk=seat_id)
        if Ticket.objects.filter(screening=screening, seat=seat).exists():
            messages.error(request, f"Место {seat.row}-{seat.number} уже занято.")
            return redirect('screening_detail', screening_id=screening_id)

    # Создаем группу билетов с одним group_id
    group_id = str(uuid.uuid4())

    # Создаем билеты с одним group_id
    tickets = []
    for seat_id in seat_ids:
        seat = get_object_or_404(Seat, pk=seat_id)
        ticket = Ticket.objects.create(
            user=request.user,
            screening=screening,
            seat=seat,
            group_id=group_id
        )
        tickets.append(ticket)

    # Перенаправляем с флагом успешной покупки
    return redirect(f'{reverse("screening_detail", args=[screening_id])}?purchase_success=true&group_id={group_id}')


@login_required
def download_ticket(request):
    # Получаем group_id из GET параметров
    group_id = request.GET.get('group_id')

    if not group_id:
        return redirect('home')

    # Получаем все билеты из группы
    tickets = Ticket.objects.filter(group_id=group_id, user=request.user)

    if not tickets.exists():
        return redirect('home')

    pdf_buffer = generate_ticket_pdf(tickets)

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    filename = f"билет_{tickets[0].screening.movie.title}_{group_id[:8]}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def download_ticket_single(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Если билет входит в группу, скачиваем всю группу
    if ticket.group_id:
        tickets = Ticket.objects.filter(group_id=ticket.group_id, user=request.user)
    else:
        tickets = [ticket]

    try:
        pdf_buffer = generate_ticket_pdf(tickets)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

        if len(tickets) > 1:
            filename = f"билет_{ticket.screening.movie.title}_{ticket.group_id[:8]}.pdf"
        else:
            filename = f"билет_{ticket.screening.movie.title}_{ticket.id}.pdf"

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        messages.error(request, "Ошибка при генерации билета. Пожалуйста, попробуйте позже.")
        return redirect('profile')


@login_required
def download_ticket_group(request, group_id):
    tickets = Ticket.objects.filter(group_id=group_id, user=request.user)

    if not tickets.exists():
        messages.error(request, "Билеты не найдены.")
        return redirect('profile')

    try:
        pdf_buffer = generate_ticket_pdf(tickets)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"билет_{tickets[0].screening.movie.title}_{group_id[:8]}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        messages.error(request, "Ошибка при генерации билета. Пожалуйста, попробуйте позже.")
        return redirect('profile')


@login_required
def profile(request):
    # Получаем все билеты пользователя
    all_tickets = Ticket.objects.filter(user=request.user).select_related(
        'screening__movie', 'screening__hall', 'seat'
    ).order_by('-purchase_date')

    # Группируем билеты по group_id вручную
    groups_dict = {}

    for ticket in all_tickets:
        group_id = ticket.group_id if ticket.group_id else f"single_{ticket.id}"

        if group_id not in groups_dict:
            groups_dict[group_id] = {
                'group_id': group_id,
                'movie_title': ticket.screening.movie.title,
                'movie_poster': ticket.screening.movie.poster,
                'hall_name': ticket.screening.hall.name,
                'start_time': ticket.screening.start_time,
                'purchase_date': ticket.purchase_date,
                'screening': ticket.screening,
                'seats': [],
                'ticket_count': 0,
                'total_price': 0
            }

        # Добавляем информацию о месте
        groups_dict[group_id]['seats'].append({
            'row': ticket.seat.row,
            'number': ticket.seat.number
        })
        groups_dict[group_id]['ticket_count'] += 1
        groups_dict[group_id]['total_price'] += ticket.screening.price

    # Преобразуем словарь в список и сортируем по дате
    ticket_groups = sorted(groups_dict.values(), key=lambda x: x['purchase_date'], reverse=True)

    profile_form = UserUpdateForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            profile_form = UserUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Ваши данные успешно обновлены!')
                return redirect('profile')
            else:
                for field in profile_form.errors:
                    if field in profile_form.fields:
                        profile_form[field].field.widget.attrs['class'] = 'form-control error-field'
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')

        elif form_type == 'password':
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменен!')
                return redirect('profile')
            else:
                for field in password_form.errors:
                    if field in password_form.fields:
                        password_form[field].field.widget.attrs['class'] = 'form-control error-field'
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме смены пароля.')

    return render(request, 'ticket/profile.html', {
        'form': profile_form,
        'password_form': password_form,
        'ticket_groups': ticket_groups
    })


# Остальные admin views остаются без изменений
@staff_member_required
def movie_manage(request):
    movies = Movie.objects.all()
    return render(request, 'ticket/admin/movie_manage.html', {'movies': movies})


@staff_member_required
def movie_add(request):
    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('movie_manage')
    else:
        form = MovieForm()
    return render(request, 'ticket/admin/movie_form.html', {'form': form})


@staff_member_required
def movie_edit(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES, instance=movie)
        if form.is_valid():
            form.save()
            return redirect('movie_manage')
    else:
        form = MovieForm(instance=movie)
    return render(request, 'ticket/admin/movie_form.html', {'form': form})


@staff_member_required
def movie_delete(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    if request.method == 'POST':
        movie.delete()
        return redirect('movie_manage')
    return render(request, 'ticket/admin/movie_confirm_delete.html', {'movie': movie})


@staff_member_required
def hall_manage(request):
    halls = Hall.objects.all()
    return render(request, 'ticket/admin/hall_manage.html', {'halls': halls})


@staff_member_required
def hall_add(request):
    if request.method == 'POST':
        form = HallForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('hall_manage')
    else:
        form = HallForm()
    return render(request, 'ticket/admin/hall_form.html', {'form': form})


@staff_member_required
def hall_edit(request, hall_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    if request.method == 'POST':
        form = HallForm(request.POST, instance=hall)
        if form.is_valid():
            form.save()
            return redirect('hall_manage')
    else:
        form = HallForm(instance=hall)
    return render(request, 'ticket/admin/hall_form.html', {'form': form})


@staff_member_required
def hall_delete(request, hall_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    if request.method == 'POST':
        hall.delete()
        return redirect('hall_manage')
    return render(request, 'ticket/admin/hall_confirm_delete.html', {'hall': hall})


@staff_member_required
def screening_manage(request):
    screenings = Screening.objects.all()
    return render(request, 'ticket/admin/screening_manage.html', {'screenings': screenings})


@staff_member_required
def screening_add(request):
    if request.method == 'POST':
        form = ScreeningForm(request.POST)
        if form.is_valid():
            screening = form.save(commit=False)
            if not screening.end_time and screening.movie and screening.start_time:
                screening.end_time = screening.start_time + screening.movie.duration + timedelta(minutes=10)
            screening.save()
            return redirect('screening_manage')
    else:
        form = ScreeningForm()
    return render(request, 'ticket/admin/screening_form.html', {'form': form})


@staff_member_required
def screening_edit(request, screening_id):
    screening = get_object_or_404(Screening, pk=screening_id)
    if request.method == 'POST':
        form = ScreeningForm(request.POST, instance=screening)
        if form.is_valid():
            updated_screening = form.save(commit=False)
            if updated_screening.movie and updated_screening.start_time:
                updated_screening.end_time = updated_screening.start_time + updated_screening.movie.duration + timedelta(
                    minutes=10)
            updated_screening.save()
            return redirect('screening_manage')
    else:
        form = ScreeningForm(instance=screening)
    return render(request, 'ticket/admin/screening_form.html', {'form': form})


@staff_member_required
def screening_delete(request, screening_id):
    screening = get_object_or_404(Screening, pk=screening_id)
    if request.method == 'POST':
        screening.delete()
        return redirect('screening_manage')
    return render(request, 'ticket/admin/screening_confirm_delete.html', {'screening': screening})


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    local_now = timezone.localtime(timezone.now())

    # Предстоящие сеансы
    upcoming_screenings = Screening.objects.filter(
        movie=movie,
        start_time__gt=local_now
    ).order_by('start_time')

    # Прошедшие сеансы (последние 2)
    past_screenings = Screening.objects.filter(
        movie=movie,
        start_time__lte=local_now
    ).order_by('-start_time')[:2]

    return render(request, 'ticket/movie_detail.html', {
        'movie': movie,
        'upcoming_screenings': upcoming_screenings,
        'past_screenings': past_screenings,
    })


def screening_partial(request, screening_id):
    """Возвращает HTML для частичной информации о сеансе"""
    screening = get_object_or_404(Screening, pk=screening_id)

    # Получаем занятые места для этого сеанса
    booked_tickets = Ticket.objects.filter(screening=screening)
    booked_seat_ids = [ticket.seat.id for ticket in booked_tickets]

    # Получаем места зала
    seats = Seat.objects.filter(hall=screening.hall).order_by('row', 'number')

    # Группируем по рядам
    rows = {}
    for seat in seats:
        if seat.row not in rows:
            rows[seat.row] = []
        rows[seat.row].append(seat)

    return render(request, 'ticket/screening_partial.html', {
        'screening': screening,
        'rows': rows,
        'booked_seat_ids': booked_seat_ids
    })