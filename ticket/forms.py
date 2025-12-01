import re
from datetime import date, timedelta
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from .export_utils import LogExporter
from .models import User, Movie, Hall, Screening, OperationLog, Genre


class RegistrationForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@mail.ru',
            'class': 'form-control'
        })
    )
    name = forms.CharField(
        label='Имя',
        widget=forms.TextInput(attrs={
            'placeholder': 'Иван',
            'class': 'form-control'
        })
    )
    surname = forms.CharField(
        label='Фамилия',
        widget=forms.TextInput(attrs={
            'placeholder': 'Иванов',
            'class': 'form-control'
        })
    )
    number = forms.CharField(
        label='Телефон',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 999-99-99',
            'class': 'form-control'
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Придумайте пароль',
            'class': 'form-control'
        }),
        help_text='<ul><li>Пароль должен содержать не менее 8 символов</li><li>Не должен быть слишком простым</li><li>Не должен состоять только из цифр</li></ul>'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль',
            'class': 'form-control'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверяем, не занят ли email подтвержденным пользователем
        if User.objects.filter(email=email, is_email_verified=True).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')

        return cleaned_data

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not re.match(r'^[а-яА-Яa-zA-Z\- ]+$', name):
            raise ValidationError('Имя может содержать только буквы и дефисы')
        return name

    def clean_surname(self):
        surname = self.cleaned_data.get('surname')
        if not re.match(r'^[а-яА-Яa-zA-Z\- ]+$', surname):
            raise ValidationError('Фамилия может содержать только буквы и дефисы')
        return surname

    def clean_number(self):
        number = self.cleaned_data.get('number')
        cleaned_number = re.sub(r'[^\d+]', '', number)

        if cleaned_number.startswith('8'):
            cleaned_number = '+7' + cleaned_number[1:]
        elif cleaned_number.startswith('7'):
            cleaned_number = '+' + cleaned_number

        if len(cleaned_number) != 12:
            raise ValidationError('Номер телефона должен содержать 11 цифр')

        return cleaned_number


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Ваш email',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ваш пароль',
            'class': 'form-control'
        })
    )


class UserUpdateForm(forms.ModelForm):
    name = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z\- ]+$',
                message='Имя может содержать только буквы и дефисы'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваше имя'
        })
    )
    surname = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z\- ]+$',
                message='Фамилия может содержать только буквы и дефисы'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваша фамилия'
        })
    )
    number = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^(\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
                message='Введите корректный номер телефона РФ'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (XXX) XXX-XX-XX'
        })
    )

    class Meta:
        model = User
        fields = ['name', 'surname', 'number']

    def clean_number(self):
        number = self.cleaned_data.get('number')
        # Очищаем номер от лишних символов
        cleaned_number = re.sub(r'[^\d+]', '', number)

        # Если номер начинается с 8, заменяем на +7
        if cleaned_number.startswith('8'):
            cleaned_number = '+7' + cleaned_number[1:]
        elif cleaned_number.startswith('7'):
            cleaned_number = '+' + cleaned_number

        # Проверяем длину номера
        if len(cleaned_number) != 12:  # +79123456789
            raise ValidationError('Номер телефона должен содержать 11 цифр')

        # Проверяем, что номер не занят другим пользователем
        if User.objects.filter(number=cleaned_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Пользователь с таким номером телефона уже существует')

        return cleaned_number


class MovieForm(forms.ModelForm):
    genre_choice = forms.ChoiceField(
        choices=[],  # Будет заполнено динамически
        required=False,
        label='Выберите жанр',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    new_genre = forms.CharField(
        max_length=50,
        required=False,
        label='Или создайте новый жанр',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название нового жанра'
        })
    )

    class Meta:
        model = Movie
        fields = ['title', 'short_description', 'description', 'duration', 'poster']
        widgets = {
            'short_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Короткое описание для главной страницы (до 300 символов)'
            }),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Полное описание для страницы фильма'
            }),
            'duration': forms.TextInput(attrs={'placeholder': 'HH:MM:SS'}),
            'poster': forms.FileInput(attrs={'accept': 'image/*'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Заполняем выбор существующих жанров
        genres = Genre.objects.all().values_list('name', 'name')
        self.fields['genre_choice'].choices = [('', '---------')] + list(genres) + [('new', '➕ Создать новый жанр...')]

        # Если редактируем существующий фильм, устанавливаем текущий жанр
        if self.instance and self.instance.pk and self.instance.genre:
            self.fields['genre_choice'].initial = self.instance.genre.name

    def clean(self):
        cleaned_data = super().clean()
        genre_choice = cleaned_data.get('genre_choice')
        new_genre = cleaned_data.get('new_genre')

        if not genre_choice and not new_genre:
            raise ValidationError('Выберите жанр или создайте новый')

        if genre_choice == 'new':
            if not new_genre:
                raise ValidationError('Введите название нового жанра')
            # Создаем новый жанр
            genre, created = Genre.objects.get_or_create(name=new_genre)
            cleaned_data['genre'] = genre
        elif genre_choice:
            # Используем существующий жанр
            try:
                genre = Genre.objects.get(name=genre_choice)
                cleaned_data['genre'] = genre
            except Genre.DoesNotExist:
                raise ValidationError('Выбранный жанр не существует')

        return cleaned_data

    def save(self, commit=True):
        movie = super().save(commit=False)
        movie.genre = self.cleaned_data['genre']
        if commit:
            movie.save()
        return movie


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ['name', 'rows', 'seats_per_row']


class ScreeningForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'min': '08:00'
        }),
        label='Время начала'
    )

    class Meta:
        model = Screening
        fields = ['movie', 'hall', 'start_time', 'price']
        labels = {
            'movie': 'Фильм',
            'hall': 'Зал',
            'start_time': 'Время начала',
            'price': 'Цена (руб)'
        }
        help_texts = {
            'start_time': 'Сеансы доступны с 8:00 до 23:00',
            'price': 'Укажите цену в рублях'
        }

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time:
            # Приводим к локальному времени для проверки
            local_time = timezone.localtime(start_time)
            hour = local_time.hour

            # Проверяем что время между 8:00 и 23:00
            if hour < 8 or hour >= 23:
                raise ValidationError("Сеансы могут начинаться только с 8:00 до 23:00")

            # Проверяем что сеанс не в прошлом
            if start_time < timezone.now():
                raise ValidationError("Нельзя создавать сеансы в прошлом")

        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        movie = cleaned_data.get('movie')
        hall = cleaned_data.get('hall')

        if start_time and movie and hall:
            # Рассчитываем время окончания
            end_time = start_time + movie.duration + timedelta(minutes=10)

            # Проверяем что сеанс заканчивается до 24:00
            local_end_time = timezone.localtime(end_time)
            if local_end_time.hour >= 24 or (local_end_time.hour == 0 and local_end_time.minute > 0):
                raise ValidationError(
                    f"Сеанс заканчивается в {local_end_time.strftime('%H:%M')}. "
                    f"Кинотеатр работает до 24:00. Выберите более раннее время начала."
                )

            # Проверяем пересечения с другими сеансами
            overlapping_screenings = Screening.objects.filter(
                hall=hall,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(pk=self.instance.pk if self.instance else None)

            if overlapping_screenings.exists():
                overlapping = overlapping_screenings.first()
                raise ValidationError(
                    f"Сеанс пересекается с другим сеансом: "
                    f"{overlapping.movie.title} в {timezone.localtime(overlapping.start_time).strftime('%H:%M')}"
                )

        return cleaned_data

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time:
            # Приводим к локальному времени для проверки
            local_time = timezone.localtime(start_time)
            hour = local_time.hour

            # Проверяем что время между 8:00 и 23:00
            if hour < 8 or hour >= 23:
                raise ValidationError("Сеансы могут начинаться только с 8:00 до 23:00")

            # Проверяем что сеанс не в прошлом
            if start_time < timezone.now():
                raise ValidationError("Нельзя создавать сеансы в прошлом")

        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        movie = cleaned_data.get('movie')
        hall = cleaned_data.get('hall')

        if start_time and movie and hall:
            # Рассчитываем время окончания
            end_time = start_time + movie.duration + timedelta(minutes=10)

            # Проверяем что сеанс заканчивается до 24:00
            local_end_time = timezone.localtime(end_time)
            if local_end_time.hour >= 24:
                raise ValidationError("Сеанс должен заканчиваться до 24:00")

            # Проверяем пересечения с другими сеансами
            overlapping_screenings = Screening.objects.filter(
                hall=hall,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(pk=self.instance.pk if self.instance else None)

            if overlapping_screenings.exists():
                overlapping = overlapping_screenings.first()
                raise ValidationError(
                    f"Сеанс пересекается с другим сеансом: "
                    f"{overlapping.movie.title} в {timezone.localtime(overlapping.start_time).strftime('%H:%M')}"
                )

        return cleaned_data


class DailyBackupForm(forms.Form):
    backup_date = forms.DateField(
        label='Select date for backup',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'max': str(date.today()),
            'class': 'vDateField'
        })
    )

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите текущий пароль'
        })
    )
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите новый пароль'
        }),
        help_text=password_validation.password_validators_help_text_html()
    )
    new_password2 = forms.CharField(
        label='Подтверждение нового пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите новый пароль'
        })
    )


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Ваш email',
            'class': 'form-control'
        })
    )


class PasswordResetCodeForm(forms.Form):
    reset_code = forms.CharField(
        label='Код подтверждения',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '000000',
            'class': 'form-control',
            'style': 'text-align: center; letter-spacing: 5px;'
        })
    )


class PasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Введите новый пароль',
            'class': 'form-control'
        }),
        help_text=password_validation.password_validators_help_text_html()
    )
    new_password2 = forms.CharField(
        label='Подтверждение нового пароля',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите новый пароль',
            'class': 'form-control'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')

        # Валидация пароля
        if password1:
            try:
                password_validation.validate_password(password1)
            except ValidationError as error:
                raise ValidationError(error)

        return cleaned_data


class ReportFilterForm(forms.Form):
    REPORT_TYPE_CHOICES = [
        ('revenue', '📊 Финансовая статистика'),
        ('movies', '🎬 Популярность фильмов'),
        ('halls', '🏛️ Загруженность залов'),
        ('sales', '💰 Статистика продаж'),
    ]

    PERIOD_CHOICES = [
        ('daily', 'По дням'),
        ('weekly', 'По неделям'),
        ('monthly', 'По месяцам'),
    ]

    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        label='Тип отчета',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,
        label='Период',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Начальная дата'
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Конечная дата'
    )


# Добавить после существующих форм
class LogExportForm(forms.Form):
    """Форма для экспорта логов"""

    format_type = forms.ChoiceField(
        choices=LogExporter.get_export_formats(),
        label='Формат экспорта',
        initial='csv'
    )

    start_date = forms.DateField(
        label='Начальная дата',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = forms.DateField(
        label='Конечная дата',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    action_type = forms.ChoiceField(
        choices=[('', 'Все действия')] + list(OperationLog.ACTION_TYPES),
        label='Тип действия',
        required=False
    )

    module_type = forms.ChoiceField(
        choices=[('', 'Все модули')] + list(OperationLog.MODULE_TYPES),
        label='Модуль',
        required=False
    )

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label='Пользователь',
        required=False,
        empty_label='Все пользователи'
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('Начальная дата не может быть больше конечной')

        return cleaned_data


class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label='Новый email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите новый email'
        })
    )
    verification_code = forms.CharField(
        label='Код подтверждения',
        max_length=6,
        min_length=6,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'style': 'text-align: center; letter-spacing: 5px;'
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')

        if not self.user:
            raise ValidationError('Пользователь не определен')

        if new_email == self.user.email:
            raise ValidationError('Новый email совпадает с текущим')

        # Проверяем, не занят ли email другим пользователем (включая неподтвержденные)
        if User.objects.filter(email=new_email).exists():
            # Если email занят текущим пользователем (но не подтвержден) - разрешаем
            existing_user = User.objects.get(email=new_email)
            if existing_user.id != self.user.id:
                raise ValidationError('Пользователь с таким email уже существует')

        return new_email

    def clean(self):
        cleaned_data = super().clean()
        verification_code = cleaned_data.get('verification_code')
        new_email = cleaned_data.get('new_email')

        # Если введен код подтверждения, проверяем его
        if verification_code:
            try:
                from .models import EmailChangeRequest
                change_request = EmailChangeRequest.objects.filter(
                    user=self.user,
                    new_email=new_email,
                    is_used=False
                ).order_by('-created_at').first()

                if not change_request:
                    raise ValidationError('Запрос на смену email не найден')

                if change_request.is_expired():
                    change_request.delete()
                    raise ValidationError('Время действия кода истекло. Запросите новый код.')

                if change_request.verification_code != verification_code:
                    raise ValidationError('Неверный код подтверждения')

            except EmailChangeRequest.DoesNotExist:
                raise ValidationError('Запрос на смену email не найден')

        return cleaned_data