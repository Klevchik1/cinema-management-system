import logging
logger = logging.getLogger(__name__)
from audioop import reverse
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_email
import re
import logging
logger = logging.getLogger(__name__)
import os
from django.conf import settings


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(max_length=100, unique=True)
    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    number = models.CharField(max_length=50)

    # Telegram fields
    telegram_chat_id = models.CharField(max_length=20, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    is_telegram_verified = models.BooleanField(default=False)
    telegram_verification_code = models.CharField(max_length=10, blank=True, null=True)

    # Email verification fields
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_verification_code_sent_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname', 'number']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.name} {self.surname})"

    def generate_verification_code(self):
        """Генерация кода подтверждения"""
        import random
        import string
        code = ''.join(random.choices(string.digits, k=6))
        self.telegram_verification_code = code
        self.is_telegram_verified = False
        self.save()
        logger.info(f"Generated verification code {code} for user {self.email}")
        return code

    # МЕТОДЫ ДЛЯ EMAIL
    def generate_email_verification_code(self):
        """Генерация кода подтверждения email"""
        import random
        import string
        from django.utils import timezone

        code = ''.join(random.choices(string.digits, k=6))
        self.email_verification_code = code
        self.email_verification_code_sent_at = timezone.now()
        self.is_email_verified = False
        self.save()
        logger.info(f"Generated email verification code for user {self.email}")
        return code

    def is_verification_code_expired(self):
        """Проверка истечения срока действия кода (10 минут)"""
        from django.utils import timezone
        if not self.email_verification_code_sent_at:
            return True
        expiration_time = self.email_verification_code_sent_at + timezone.timedelta(minutes=10)
        return timezone.now() > expiration_time

    def verify_email(self, code):
        """Подтверждение email"""
        if (self.email_verification_code == code and
                not self.is_verification_code_expired()):
            self.is_email_verified = True
            self.email_verification_code = ''
            self.save()
            return True
        return False

    def requires_email_verification(self):
        """Проверяет, требуется ли подтверждение email для этого пользователя"""
        # Администраторам и суперпользователям не требуется подтверждение
        return not (self.is_staff or self.is_superuser)

class PendingRegistration(models.Model):
    """Временное хранение данных регистрации до подтверждения email"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    number = models.CharField(max_length=50)
    password = models.CharField(max_length=128)  # Хэшированный пароль
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """Проверка истечения срока действия (30 минут)"""
        from django.utils import timezone
        expiration_time = self.created_at + timezone.timedelta(minutes=30)
        return timezone.now() > expiration_time

    def create_user(self):
        """Создание пользователя после подтверждения"""
        from django.contrib.auth.hashers import make_password

        user = User.objects.create(
            email=self.email,
            name=self.name,
            surname=self.surname,
            number=self.number,
            password=make_password(self.password),  # Пароль уже хэширован
            is_email_verified=True
        )
        return user

    class Meta:
        verbose_name = "Ожидающая регистрация"
        verbose_name_plural = "Ожидающие регистрации"

class Hall(models.Model):
    name = models.CharField(max_length=50)
    rows = models.IntegerField()
    seats_per_row = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        logger.info(f"Сохранение зала {self.name}, новый: {self._state.adding}")
        super().save(*args, **kwargs)

        if self._state.adding:
            logger.info(f"Создаю места для нового зала {self.name}")
            self.create_seats()

    def create_seats(self):
        logger.info(f"Создание мест для зала {self.name}: {self.rows} рядов × {self.seats_per_row} мест")
        for row in range(1, self.rows + 1):
            for seat_num in range(1, self.seats_per_row + 1):
                Seat.objects.get_or_create(
                    hall=self,
                    row=row,
                    number=seat_num
                )

class Movie(models.Model):
    title = models.CharField(max_length=100)
    short_description = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Короткое описание'
    )
    description = models.TextField(
        max_length=1000,
        verbose_name='Полное описание'
    )
    duration = models.DurationField()
    genre = models.CharField(max_length=50)
    poster = models.ImageField(
        upload_to='movie_posters/',
        blank=True,
        null=True,
        verbose_name='Постер фильма'
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Если короткое описание не задано, создаем его из полного
        if not self.short_description and self.description:
            self.short_description = self.description[:197] + '...' if len(self.description) > 200 else self.description
        super().save(*args, **kwargs)

class Screening(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Время окончания сеанса должно быть позже времени начала")

        if self.movie and self.start_time and not self.end_time:
            self.end_time = self.start_time + self.movie.duration + timedelta(minutes=10)

        if self.hall and self.start_time and self.end_time:
            overlapping_screenings = Screening.objects.filter(
                hall=self.hall,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk)

            if overlapping_screenings.exists():
                raise ValidationError("Сеанс пересекается с другим сеансом в этом зале")

    def save(self, *args, **kwargs):
        if self.movie and self.start_time and not self.end_time:
            self.end_time = self.start_time + self.movie.duration + timedelta(minutes=10)
        super().save(*args, **kwargs)

class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    row = models.IntegerField()
    number = models.IntegerField()

class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    group_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    class Meta:
        unique_together = ('screening', 'seat')

    def get_pdf_url(self):
        return reverse('download_ticket_single', args=[self.id])

    def get_group_tickets(self):
        """Получить все билеты из той же группы"""
        if self.group_id:
            return Ticket.objects.filter(group_id=self.group_id)
        return Ticket.objects.filter(id=self.id)

@receiver(post_save, sender=Hall)
def create_hall_seats(sender, instance, created, **kwargs):
    if created:
        for row in range(1, instance.rows + 1):
            for seat_num in range(1, instance.seats_per_row + 1):
                Seat.objects.get_or_create(
                    hall=instance,
                    row=row,
                    number=seat_num
                )


class BackupManager(models.Model):
    """Модель для управления бэкапами"""
    name = models.CharField(max_length=255)
    backup_file = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    backup_type = models.CharField(max_length=50, choices=[
        ('full', 'Full Backup'),
        ('daily', 'Daily Backup')
    ])
    backup_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Backup"
        verbose_name_plural = "Backups"

    def __str__(self):
        return self.name

    def get_file_path(self):
        """Получить полный путь к файлу бэкапа"""
        return os.path.join(settings.BASE_DIR, 'backups', self.backup_file)

    def file_exists(self):
        """Проверить существует ли файл бэкапа"""
        return os.path.exists(self.get_file_path())

    def file_size(self):
        """Получить размер файла"""
        if self.file_exists():
            size = os.path.getsize(self.get_file_path())
            return f"{size / 1024 / 1024:.2f} MB"
        return "File not found"