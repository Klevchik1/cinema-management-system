from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Movie, Hall, Screening
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import RegexValidator

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'Ваш email'}))
    name = forms.CharField(
        label='Имя',
        widget=forms.TextInput(attrs={'placeholder': 'Ваше имя'}))
    surname = forms.CharField(
        label='Фамилия',
        widget=forms.TextInput(attrs={'placeholder': 'Ваша фамилия'}))
    number = forms.CharField(
        label='Телефон',
        widget=forms.TextInput(attrs={'placeholder': '+7 (XXX) XXX-XX-XX'}))
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Придумайте пароль'}),
        help_text='<ul><li>Пароль должен содержать не менее 8 символов</li><li>Не должен быть слишком простым</li><li>Не должен состоять только из цифр</li></ul>')
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'placeholder': 'Повторите пароль'}))

    class Meta:
        model = User
        fields = ['email', 'name', 'surname', 'number', 'password1', 'password2']

class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'Ваш email'}))
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Ваш пароль'}))

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'duration', 'genre', 'poster']
        widgets = {
            'duration': forms.TextInput(attrs={'placeholder': 'HH:MM:SS'}),
            'poster': forms.FileInput(attrs={'accept': 'image/*'})
        }
        labels = {
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

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'name', 'surname', 'number']
        number = forms.CharField(
            label='Телефон',
            validators=[RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Номер телефона должен быть в формате: '+79991234567'."
            )],
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (XXX) XXX-XX-XX'
            })
        )
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваш email'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя'
            }),
            'surname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваша фамилия'
            }),
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (XXX) XXX-XX-XX'
            }),
        }