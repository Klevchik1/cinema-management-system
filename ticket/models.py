# models.py
from audioop import reverse

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.core.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname', 'number']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.name} {self.surname})"


class Hall(models.Model):
    name = models.CharField(max_length=50)
    rows = models.IntegerField()
    seats_per_row = models.IntegerField()

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
    description = models.CharField(max_length=500)
    duration = models.DurationField()
    genre = models.CharField(max_length=50)
    poster = models.ImageField(
        upload_to='movie_posters/',
        blank=True,
        null=True,
        verbose_name='Постер фильма'
    )

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

    class Meta:
        unique_together = ('screening', 'seat')

    def get_pdf_url(self):
        return reverse('download_ticket_single', args=[self.id])

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