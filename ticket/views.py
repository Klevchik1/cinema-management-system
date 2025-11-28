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
from .telegram_bot.bot import get_bot
from .email_utils import send_verification_email, send_welcome_email
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .models import PendingRegistration
from .models import PasswordResetRequest
from .forms import PasswordResetRequestForm, PasswordResetCodeForm, PasswordResetForm
from .email_utils import send_verification_email, send_welcome_email, send_password_reset_email
logger = logging.getLogger(__name__)
from .forms import ReportFilterForm
from .report_utils import ReportGenerator
from .pdf_utils import generate_pdf_report
from .logging_utils import OperationLogger




@staff_member_required
def admin_dashboard(request):
    return render(request, 'ticket/admin_dashboard.html')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            name = form.cleaned_data['name']
            surname = form.cleaned_data['surname']
            number = form.cleaned_data['number']
            password = form.cleaned_data['password1']

            # Удаляем старые просроченные регистрации
            from .models import PendingRegistration
            PendingRegistration.objects.filter(email=email).delete()

            # Генерируем код подтверждения
            import random
            import string
            verification_code = ''.join(random.choices(string.digits, k=6))

            # Сохраняем данные во временную модель
            pending_reg = PendingRegistration.objects.create(
                email=email,
                name=name,
                surname=surname,
                number=number,
                password=make_password(password),
                verification_code=verification_code
            )

            # ЛОГИРОВАНИЕ РЕГИСТРАЦИИ
            OperationLogger.log_operation(
                request=request,
                action_type='CREATE',
                module_type='USERS',
                description=f'Начата регистрация пользователя {email}',
                object_id=pending_reg.id,
                object_repr=f"{name} {surname}"
            )

            # ВАЖНО: Сохраняем данные в сессии ПЕРЕД redirect
            request.session['pending_registration_id'] = pending_reg.id
            request.session['pending_registration_email'] = email

            # Принудительно сохраняем сессию
            request.session.save()

            logger.info(f"Session data saved: {request.session.session_key}")
            logger.info(f"Pending registration ID: {pending_reg.id}")

            # Отправляем email
            try:
                from .email_utils import send_verification_email
                if send_verification_email(pending_reg):
                    messages.success(request, f'Код подтверждения отправлен на email {email}')
                    logger.info(f"Email sent successfully to {email}")
                else:
                    messages.warning(request, f'Письмо отправлено, но возникли проблемы с доставкой.')
            except Exception as e:
                logger.error(f"Email sending error: {e}")
                messages.warning(request, f'Код подтверждения: {verification_code}')

            # ВАЖНО: redirect после сохранения сессии
            return redirect('verify_email')

        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = RegistrationForm()

    return render(request, 'ticket/register.html', {'form': form})


def verify_email(request):
    """Страница ввода кода подтверждения"""
    pending_reg_id = request.session.get('pending_registration_id')
    email = request.session.get('pending_registration_email')

    logger.info(f"Session data in verify_email: pending_reg_id={pending_reg_id}, email={email}")

    if not pending_reg_id or not email:
        logger.error("Missing session data in verify_email")
        messages.error(request, 'Сессия истекла. Пожалуйста, начните регистрацию заново.')
        return redirect('register')

    try:
        from .models import PendingRegistration
        pending_reg = PendingRegistration.objects.get(id=pending_reg_id, email=email)
        logger.info(f"Found pending registration: {pending_reg.id}")
    except PendingRegistration.DoesNotExist:
        logger.error(f"Pending registration not found: id={pending_reg_id}, email={email}")
        messages.error(request, 'Регистрация не найдена. Пожалуйста, зарегистрируйтесь заново.')
        # Очищаем невалидную сессию
        if 'pending_registration_id' in request.session:
            del request.session['pending_registration_id']
        if 'pending_registration_email' in request.session:
            del request.session['pending_registration_email']
        return redirect('register')

    # Проверяем не истекла ли регистрация
    if pending_reg.is_expired():
        logger.warning(f"Pending registration expired: {pending_reg.id}")
        pending_reg.delete()
        messages.error(request, 'Время для подтверждения истекло. Пожалуйста, зарегистрируйтесь заново.')
        # Очищаем сессию
        if 'pending_registration_id' in request.session:
            del request.session['pending_registration_id']
        if 'pending_registration_email' in request.session:
            del request.session['pending_registration_email']
        return redirect('register')

    if request.method == 'POST':
        code = request.POST.get('verification_code', '').strip()

        if not code:
            messages.error(request, 'Введите код подтверждения')
            return render(request, 'ticket/verify_email.html', {
                'email': pending_reg.email
            })

        if pending_reg.verification_code == code:
            # Код верный - создаем пользователя
            user = pending_reg.create_user()

            # ЛОГИРОВАНИЕ УСПЕШНОЙ РЕГИСТРАЦИИ
            OperationLogger.log_operation(
                request=request,
                action_type='CREATE',
                module_type='USERS',
                description=f'Успешная регистрация и верификация пользователя {user.email}',
                object_id=user.id,
                object_repr=str(user)
            )

            # Отправляем приветственное письмо
            try:
                from .email_utils import send_welcome_email
                send_welcome_email(user)
            except Exception as e:
                logger.error(f"Welcome email error: {e}")

            # Логиним пользователя
            login(request, user)

            # Удаляем временную запись
            pending_reg.delete()

            # Очищаем сессию
            session_keys = ['pending_registration_id', 'pending_registration_email']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            messages.success(request, 'Email успешно подтвержден! Добро пожаловать!')
            return redirect('home')
        else:
            # ЛОГИРОВАНИЕ НЕВЕРНОГО КОДА
            OperationLogger.log_operation(
                request=request,
                action_type='OTHER',
                module_type='AUTH',
                description=f'Неверный код подтверждения для {pending_reg.email}'
            )
            messages.error(request, 'Неверный код подтверждения')
            logger.warning(f"Invalid verification code entered for {pending_reg.email}")

        return render(request, 'ticket/verify_email.html', {
            'email': pending_reg.email
        })


def resend_verification_code(request):
    """Повторная отправка кода подтверждения"""
    pending_reg_id = request.session.get('pending_registration_id')

    if not pending_reg_id:
        messages.error(request, 'Сессия истекла.')
        return redirect('register')

    try:
        pending_reg = PendingRegistration.objects.get(id=pending_reg_id)

        # Генерируем новый код
        import random
        import string
        new_code = ''.join(random.choices(string.digits, k=6))

        # Обновляем код
        pending_reg.verification_code = new_code
        pending_reg.save()

        # Отправляем email
        if send_verification_email(pending_reg):
            messages.success(request, 'Новый код подтверждения отправлен на ваш email')
        else:
            messages.error(request, 'Ошибка при отправке кода. Попробуйте позже.')

    except PendingRegistration.DoesNotExist:
        messages.error(request, 'Регистрация не найдена.')
        return redirect('register')

    return redirect('verify_email')


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
                # ПРОВЕРЯЕМ, ТРЕБУЕТСЯ ЛИ ПОДТВЕРЖДЕНИЕ EMAIL
                if user.requires_email_verification() and not user.is_email_verified:
                    # Если email не подтвержден, отправляем новый код
                    send_verification_email(user)
                    request.session['pending_verification_user_id'] = user.id
                    request.session['pending_verification_email'] = user.email
                    messages.warning(request, 'Ваш email не подтвержден. Новый код отправлен на вашу почту.')
                    return redirect('verify_email')

                login(request, user)

                # ЛОГИРОВАНИЕ ВХОДА
                OperationLogger.log_operation(
                    request=request,
                    action_type='LOGIN',
                    module_type='AUTH',
                    description=f'Успешный вход пользователя {user.email}'
                )

                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                # ЛОГИРОВАНИЕ НЕУДАЧНОЙ ПОПЫТКИ ВХОДА
                OperationLogger.log_operation(
                    request=request,
                    action_type='OTHER',
                    module_type='AUTH',
                    description=f'Неудачная попытка входа для email {email}'
                )
                messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()

    return render(request, 'ticket/login.html', {'form': form})


def home(request):
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()

    search_query = request.GET.get('search', '')
    hall_filter = request.GET.get('hall', '')
    genre_filter = request.GET.get('genre', '')
    selected_date = request.GET.get('date', today.isoformat())

    # Преобразуем выбранную дату
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        selected_date = today

    # Генерируем список дат для фильтра (5 дней)
    date_filters = []
    for i in range(5):
        filter_date = today + timedelta(days=i)
        date_filters.append({
            'date': filter_date,
            'is_today': i == 0,
            'is_tomorrow': i == 1,
            'label': get_date_label(filter_date, i)
        })

    # Получаем все фильмы
    movies = Movie.objects.prefetch_related('screening_set__hall').all()

    # Применяем текстовые фильтры
    if search_query:
        movies = movies.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if genre_filter:
        movies = movies.filter(genre__name=genre_filter)

    # Собираем данные для каждого фильма
    movies_data = []

    for movie in movies:
        # Базовый фильтр для сеансов
        screenings_filter = Q(
            start_time__date=selected_date,
            start_time__gt=local_now  # Только будущие сеансы
        )

        # Применяем фильтр по залу если выбран
        if hall_filter:
            screenings_filter &= Q(hall_id=hall_filter)

        # Получаем сеансы на выбранную дату с учетом всех фильтров
        screenings_on_date = movie.screening_set.filter(screenings_filter).order_by('start_time')

        # Получаем ближайшие сеансы (максимум 3)
        upcoming_screenings = screenings_on_date[:3]

        # Определяем самый ранний сеанс для сортировки
        earliest_screening = screenings_on_date.first()

        movies_data.append({
            'movie': movie,
            'upcoming_screenings': upcoming_screenings,
            'screening_count': screenings_on_date.count(),
            'earliest_screening': earliest_screening,
            'has_screenings_today': screenings_on_date.exists()
        })

    # Сортируем фильмы:
    movies_with_screenings = [m for m in movies_data if m['has_screenings_today']]
    movies_without_screenings = [m for m in movies_data if not m['has_screenings_today']]

    # Сортируем фильмы с сеансами по времени самого раннего сеанса
    movies_with_screenings.sort(
        key=lambda x: x['earliest_screening'].start_time if x['earliest_screening'] else local_now)

    # Объединяем списки
    sorted_movies_data = movies_with_screenings + movies_without_screenings

    # Получаем названия жанров
    genres = Movie.objects.select_related('genre').values_list(
        'genre__name',
        flat=True
    ).distinct().order_by('genre__name')

    return render(request, 'ticket/home.html', {
        'movies': sorted_movies_data,
        'halls': Hall.objects.all(),
        'genres': genres,
        'date_filters': date_filters,
        'selected_date': selected_date,
        'today': today,
        'current_filters': {
            'search': search_query,
            'hall': hall_filter,
            'genre': genre_filter,
            'date': selected_date.isoformat()
        }
    })


def get_date_label(date, index):
    """Генерирует подпись для даты в фильтре"""
    from django.utils import timezone
    today = timezone.localtime(timezone.now()).date()

    # Русские названия месяцев
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    day = date.day
    month = months[date.month]

    if index == 0:
        return {"label": "Сегодня", "date": f"{day} {month}"}
    elif index == 1:
        return {"label": "Завтра", "date": f"{day} {month}"}
    else:
        # Для дней послезавтра используем сокращенные названия дней недели
        days_of_week = {
            0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт',
            4: 'Пт', 5: 'Сб', 6: 'Вс'
        }
        day_of_week = days_of_week[date.weekday()]
        return {"label": day_of_week, "date": f"{day} {month}"}


def user_logout(request):
    # ЛОГИРОВАНИЕ ВЫХОДА
    if request.user.is_authenticated:
        OperationLogger.log_operation(
            request=request,
            action_type='LOGOUT',
            module_type='AUTH',
            description=f'Выход пользователя {request.user.email}'
        )

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
    except json.JSONDecodeError as e:
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

    # ЛОГИРОВАНИЕ ПОКУПКИ БИЛЕТОВ
    OperationLogger.log_operation(
        request=request,
        action_type='CREATE',
        module_type='TICKETS',
        description=f'Покупка {len(tickets)} билетов на фильм {screening.movie.title}',
        object_id=tickets[0].id if tickets else None,
        object_repr=f"Группа билетов {group_id}",
        additional_data={
            'screening_id': screening_id,
            'movie_title': screening.movie.title,
            'seat_count': len(tickets),
            'total_price': sum(ticket.screening.price for ticket in tickets),
            'group_id': group_id
        }
    )

    # Отправляем уведомление в Telegram
    if tickets:
        try:
            from ticket.telegram_bot.bot import get_bot
            import asyncio

            async def send_notification():
                bot = get_bot()
                if bot and request.user.is_telegram_verified:
                    await bot.send_ticket_notification(request.user, tickets)

            asyncio.run(send_notification())
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

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

    # ЛОГИРОВАНИЕ СКАЧИВАНИЯ PDF
    OperationLogger.log_operation(
        request=request,
        action_type='EXPORT',
        module_type='TICKETS',
        description=f'Скачивание PDF билета для фильма {ticket.screening.movie.title}',
        object_id=ticket.id,
        object_repr=str(ticket),
        additional_data={
            'format': 'PDF',
            'movie': ticket.screening.movie.title,
            'ticket_count': len(tickets),
            'group_id': ticket.group_id
        }
    )

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

    # ЛОГИРОВАНИЕ СКАЧИВАНИЯ PDF ГРУППЫ
    OperationLogger.log_operation(
        request=request,
        action_type='EXPORT',
        module_type='TICKETS',
        description=f'Скачивание PDF группы билетов для фильма {tickets[0].screening.movie.title}',
        object_id=tickets[0].id,
        object_repr=f"Группа билетов {group_id}",
        additional_data={
            'format': 'PDF',
            'movie': tickets[0].screening.movie.title,
            'ticket_count': len(tickets),
            'group_id': group_id
        }
    )

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

                # ЛОГИРОВАНИЕ ОБНОВЛЕНИЯ ПРОФИЛЯ
                OperationLogger.log_operation(
                    request=request,
                    action_type='UPDATE',
                    module_type='USERS',
                    description=f'Обновление профиля пользователя {request.user.email}',
                    object_id=request.user.id,
                    object_repr=str(request.user)
                )

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

                # ЛОГИРОВАНИЕ СМЕНЫ ПАРОЛЯ
                OperationLogger.log_operation(
                    request=request,
                    action_type='UPDATE',
                    module_type='AUTH',
                    description=f'Смена пароля пользователя {request.user.email}',
                    object_id=request.user.id,
                    object_repr=str(request.user)
                )

                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменен!')
                return redirect('profile')
            else:
                for field in password_form.errors:
                    if field in password_form.fields:
                        password_form[field].field.widget.attrs['class'] = 'form-control error-field'
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме смены пароля.')

        elif form_type == 'telegram_connect':
            # Генерация кода для привязки Telegram
            verification_code = request.user.generate_verification_code()

            # ЛОГИРОВАНИЕ ЗАПРОСА ПРИВЯЗКИ TELEGRAM
            OperationLogger.log_operation(
                request=request,
                action_type='OTHER',
                module_type='USERS',
                description=f'Запрос привязки Telegram для пользователя {request.user.email}',
                object_id=request.user.id,
                object_repr=str(request.user),
                additional_data={'verification_code': verification_code}
            )

            messages.success(
                request,
                f'Код для привязки Telegram: {verification_code}. Отправьте его боту @CinemaaPremierBot'
            )
            return redirect('profile')

    # Добавляем информацию о Telegram в контекст
    telegram_connected = request.user.is_telegram_verified
    telegram_username = request.user.telegram_username

    # ВАЖНО: ВСЕГДА возвращаем HttpResponse в конце функции
    return render(request, 'ticket/profile.html', {
        'form': profile_form,
        'password_form': password_form,
        'ticket_groups': ticket_groups,
        'telegram_connected': telegram_connected,
        'telegram_username': telegram_username,
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


def password_reset_request(request):
    """Шаг 1: Запрос на восстановление пароля"""
    from .forms import PasswordResetRequestForm
    from .email_utils import send_password_reset_email

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            logger.info(f"Password reset requested for email: {email}")

            # Проверяем, существует ли пользователь с таким email
            try:
                user = User.objects.get(email=email, is_email_verified=True)
                logger.info(f"User found: {user.name} {user.surname}")

                # Удаляем старые запросы для этого email
                PasswordResetRequest.objects.filter(email=email).delete()

                # Генерируем код восстановления
                import random
                import string
                reset_code = ''.join(random.choices(string.digits, k=6))
                logger.info(f"Generated reset code: {reset_code}")

                # Создаем запрос на восстановление
                reset_request = PasswordResetRequest.objects.create(
                    email=email,
                    reset_code=reset_code
                )

                # ЛОГИРОВАНИЕ ЗАПРОСА ВОССТАНОВЛЕНИЯ ПАРОЛЯ
                OperationLogger.log_operation(
                    request=request,
                    action_type='OTHER',
                    module_type='AUTH',
                    description=f'Запрос восстановления пароля для {email}',
                    additional_data={'reset_code': reset_code}
                )

                # Отправляем email с кодом
                logger.info(f"Attempting to send email to {email}")
                if send_password_reset_email(user, reset_code):
                    request.session['password_reset_email'] = email
                    messages.success(request, f'Код восстановления отправлен на email {email}')
                    logger.info(f"Email sent successfully to {email}")
                    return redirect('password_reset_code')
                else:
                    messages.error(request, 'Ошибка при отправке кода. Попробуйте позже.')
                    logger.error(f"Failed to send email to {email}")

            except User.DoesNotExist:
                logger.warning(f"User not found for email: {email}")
                # Не показываем, что пользователь не существует (безопасность)
                messages.success(request, 'Если email зарегистрирован, код восстановления будет отправлен')
                return redirect('password_reset_code')

    else:
        form = PasswordResetRequestForm()

    return render(request, 'ticket/password_reset_request.html', {'form': form})


def password_reset_code(request):
    """Шаг 2: Ввод кода подтверждения"""
    from .forms import PasswordResetCodeForm

    email = request.session.get('password_reset_email')
    logger.info(f"Password reset code page - Email from session: {email}")

    if not email:
        messages.error(request, 'Сессия истекла. Начните восстановление пароля заново.')
        return redirect('password_reset_request')

    all_requests = PasswordResetRequest.objects.filter(email=email)
    logger.info(f"All reset requests for {email}: {list(all_requests.values())}")

    try:
        # Ищем самый свежий НЕиспользованный запрос
        reset_request = PasswordResetRequest.objects.filter(
            email=email,
            is_used=False
        ).order_by('-created_at').first()  # Используем first() вместо latest()

        if not reset_request:
            messages.error(request, 'Запрос на восстановление не найден. Начните заново.')
            return redirect('password_reset_request')

    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Запрос на восстановление не найден. Начните заново.')
        return redirect('password_reset_request')

    # Проверяем не истекла ли регистрация
    if reset_request.is_expired():
        reset_request.delete()
        messages.error(request, 'Время действия кода истекло. Начните заново.')
        return redirect('password_reset_request')

    if request.method == 'POST':
        form = PasswordResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['reset_code']

            # ДОБАВИМ ОТЛАДОЧНУЮ ИНФОРМАЦИЮ
            logger.info(f"Entered code: {code}, Expected code: {reset_request.reset_code}")
            logger.info(f"Code match: {reset_request.reset_code == code}")

            if reset_request.reset_code == code:
                reset_request.mark_as_used()
                request.session['password_reset_verified'] = True
                messages.success(request, 'Код подтвержден. Установите новый пароль.')
                return redirect('password_reset_confirm')
            else:
                messages.error(request, 'Неверный код подтверждения')
                # Покажем ожидаемый код для отладки
                logger.error(f"Code mismatch. Expected: {reset_request.reset_code}, Got: {code}")
    else:
        form = PasswordResetCodeForm()

    return render(request, 'ticket/password_reset_code.html', {
        'form': form,
        'email': email
    })


def password_reset_confirm(request):
    """Шаг 3: Установка нового пароля"""
    email = request.session.get('password_reset_email')
    verified = request.session.get('password_reset_verified')

    if not email or not verified:
        messages.error(request, 'Сессия истекла. Начните восстановление пароля заново.')
        return redirect('password_reset_request')

    try:
        user = User.objects.get(email=email, is_email_verified=True)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден.')
        return redirect('password_reset_request')

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            # Устанавливаем новый пароль
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.save()

            # ЛОГИРОВАНИЕ УСПЕШНОГО ВОССТАНОВЛЕНИЯ ПАРОЛЯ
            OperationLogger.log_operation(
                request=request,
                action_type='UPDATE',
                module_type='AUTH',
                description=f'Успешное восстановление пароля для {email}',
                object_id=user.id,
                object_repr=str(user)
            )

            # Очищаем сессию
            session_keys = ['password_reset_email', 'password_reset_verified']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            # Удаляем использованные запросы восстановления
            PasswordResetRequest.objects.filter(email=email).delete()

            messages.success(request, 'Пароль успешно изменен! Теперь вы можете войти в систему.')
            return redirect('login')
    else:
        form = PasswordResetForm()

    return render(request, 'ticket/password_reset_confirm.html', {
        'form': form,
        'email': email
    })