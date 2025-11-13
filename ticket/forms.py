from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Movie, Hall, Screening
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import RegexValidator, validate_email
import re
from datetime import date
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation


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
    email = forms.EmailField(
        validators=[validate_email],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваш email'
        })
    )
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
        fields = ['email', 'name', 'surname', 'number']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверяем, что email не занят другим пользователем
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

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
    class Meta:
        model = Movie
        fields = ['title', 'short_description', 'description', 'duration', 'genre', 'poster']
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
        labels = {
            'short_description': 'Короткое описание',
            'description': 'Полное описание',
            'poster': 'Постер фильма'
        }


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ['name', 'rows', 'seats_per_row']


class ScreeningForm(forms.ModelForm):
    class Meta:
        model = Screening
        fields = ['movie', 'hall', 'start_time', 'price']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise ValidationError("Время начала сеанса не может быть в прошлом")

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