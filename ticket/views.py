from django.shortcuts import render

# Create your views here.
from .forms import RegistrationForm, LoginForm, UserUpdateForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Screening, Ticket, Seat, Movie, Hall
from django.utils import timezone
from .utils import generate_ticket_pdf
from django.http import HttpResponse
import json
from django.contrib.auth import logout
from django.contrib.admin.views.decorators import staff_member_required
from .forms import MovieForm, HallForm, ScreeningForm
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.db.models import Q
from django.db.models.functions import TruncHour
import logging
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
            return redirect('home')
        else:
            messages.error(request, 'Ошибка регистрации')
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
                return redirect('home')
            else:
                messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()
    return render(request, 'ticket/login.html', {'form': form})


@login_required
def home(request):
    local_now = timezone.localtime(timezone.now())

    search_query = request.GET.get('search', '')
    hall_filter = request.GET.get('hall', '')
    genre_filter = request.GET.get('genre', '')
    time_filter = request.GET.get('time', '')

    screenings = Screening.objects.filter(
        start_time__gt=local_now
    ).order_by('start_time')

    if search_query:
        screenings = screenings.filter(
            Q(movie__title__icontains=search_query) |
            Q(movie__description__icontains=search_query)
        )

    if hall_filter:
        screenings = screenings.filter(hall_id=hall_filter)

    if genre_filter:
        screenings = screenings.filter(movie__genre=genre_filter)

    if time_filter:
        screenings = screenings.filter(start_time__hour=time_filter)

    genres = Movie.objects.values_list('genre', flat=True).distinct()

    time_slots = sorted(set(
        s.start_time.hour for s in Screening.objects.all()
    ))

    return render(request, 'ticket/home.html', {
        'screenings': screenings,
        'halls': Hall.objects.all(),
        'genres': genres,
        'time_slots': time_slots,
        'current_filters': {
            'search': search_query,
            'hall': hall_filter,
            'genre': genre_filter,
            'time': time_filter
        }
    })


def user_logout(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('login')


@login_required
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
        'booked_seat_ids': booked_seat_ids
    })


@login_required
@require_POST
def book_tickets(request):
    screening_id = request.POST.get('screening_id')
    seat_ids = json.loads(request.POST.get('selected_seats'))

    if not seat_ids:
        messages.error(request, "Выберите хотя бы одно место.")
        return redirect('screening_detail', screening_id=screening_id)

    screening = get_object_or_404(Screening, pk=screening_id)

    for seat_id in seat_ids:
        seat = get_object_or_404(Seat, pk=seat_id)
        if Ticket.objects.filter(screening=screening, seat=seat).exists():
            messages.error(request, f"Место {seat.row}-{seat.number} уже занято.")
            return redirect('screening_detail', screening_id=screening_id)

    tickets = []
    for seat_id in seat_ids:
        seat = get_object_or_404(Seat, pk=seat_id)
        ticket = Ticket.objects.create(
            user=request.user,
            screening=screening,
            seat=seat
        )
        tickets.append(ticket)

    request.session['booked_ticket_ids'] = [t.id for t in tickets]

    messages.success(request, f"Вы успешно купили {len(tickets)} место(а)! Скачайте ваш билет здесь:")
    return redirect('screening_detail', screening_id=screening_id)

def user_logout(request):
    logout(request)
    return redirect('home')


def download_ticket(request):
    if 'booked_ticket_ids' not in request.session:
        return redirect('home')

    ticket_ids = request.session['booked_ticket_ids']
    tickets = Ticket.objects.filter(id__in=ticket_ids)

    if not tickets.exists():
        return redirect('home')

    pdf_buffer = generate_ticket_pdf(tickets)

    del request.session['booked_ticket_ids']

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    filename = f"билеты_{tickets[0].screening.movie.title}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@staff_member_required
def movie_manage(request):
    movies = Movie.objects.all()
    return render(request, 'ticket/admin/movie_manage.html', {'movies': movies})

@staff_member_required
def movie_add(request):
    if request.method == 'POST':
        form = MovieForm(request.POST)
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
        form = MovieForm(request.POST, instance=movie)
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
        form = MovieForm(instance=hall)
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
    screening = Screening.objects.all()
    return render(request, 'ticket/admin/screening_manage.html', {'screening': screening})


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


@login_required
def profile(request):
    tickets = Ticket.objects.filter(user=request.user).order_by('-purchase_date')

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваши данные успешно обновлены!')
            return redirect('profile')
        else:
            for field in form.errors:
                form[field].field.widget.attrs['class'] = 'form-control error-field'
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'ticket/profile.html', {
        'form': form,
        'tickets': tickets
    })


@login_required
def download_ticket_single(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    try:
        pdf_buffer = generate_ticket_pdf([ticket])
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"билет_{ticket.screening.movie.title}_{ticket.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {str(e)}")
        messages.error(request, "Ошибка при генерации билета. Пожалуйста, попробуйте позже.")
        return redirect('profile')