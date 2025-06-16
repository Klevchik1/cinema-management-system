from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from faker import Faker
import os
from django.core.files import File
from django.conf import settings  # Исправленный импорт

# Импорт моделей
from ticket.models import Hall, Movie, Screening, Seat, User

fake = Faker('ru_RU')  # Для русскоязычных данных


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными кинотеатра'

    def handle(self, *args, **options):
        self.clear_old_data()
        self.create_admin()
        halls = self.create_halls()
        movies = self.create_movies()
        self.create_screenings(halls, movies)

        self.stdout.write(self.style.SUCCESS('✅ База успешно заполнена тестовыми данными!'))

    def clear_old_data(self):
        User.objects.all().delete()
        Hall.objects.all().delete()
        Movie.objects.all().delete()
        Screening.objects.all().delete()
        Seat.objects.all().delete()

    def create_admin(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin',
            name='Администратор',
            surname='Системы',
            number='+79001234567'
        )
        self.stdout.write(self.style.SUCCESS(f'Создан администратор: {admin.email}'))
        return admin

    def create_halls(self):
        hall1 = Hall.objects.create(
            name="Красный зал",
            rows=10,
            seats_per_row=15
        )
        hall2 = Hall.objects.create(
            name="Синий зал",
            rows=8,
            seats_per_row=12
        )
        self.stdout.write(self.style.SUCCESS('Созданы кинозалы'))
        return [hall1, hall2]

    def create_movies(self):
        posters_dir = os.path.join(settings.BASE_DIR, 'ticket', 'management', 'commands', 'posters')

        movies_data = [
            {
                'title': 'Аватар: Путь воды',
                'duration': 192,
                'genre': 'фантастика',
                'poster': 'avatar.jpg'
            },
            {
                'title': 'Один дома',
                'duration': 103,
                'genre': 'комедия',
                'poster': 'home_alone.jpg'
            },
            {
                'title': 'Интерстеллар',
                'duration': 169,
                'genre': 'фантастика',
                'poster': 'interstellar.jpg'
            }
        ]

        movies = []
        for data in movies_data:
            movie = Movie.objects.create(
                title=data['title'],
                description=fake.text(max_nb_chars=200),
                duration=timedelta(minutes=data['duration']),
                genre=data['genre']
            )

            poster_path = os.path.join(posters_dir, data['poster'])
            if os.path.exists(poster_path):
                with open(poster_path, 'rb') as f:
                    movie.poster.save(data['poster'], File(f))
                    movie.save()

            movies.append(movie)

        self.stdout.write(self.style.SUCCESS('Созданы фильмы с постерами'))
        return movies

    def create_screenings(self, halls, movies):
        now = timezone.now()

        Screening.objects.create(
            movie=movies[0],
            hall=halls[0],
            start_time=now + timedelta(hours=3),
            price=450.00
        )

        Screening.objects.create(
            movie=movies[2],
            hall=halls[0],
            start_time=now + timedelta(days=1, hours=18),
            price=500.00
        )

        Screening.objects.create(
            movie=movies[1],
            hall=halls[1],
            start_time=now + timedelta(days=1, hours=14),
            price=350.00
        )

        Screening.objects.create(
            movie=movies[0],
            hall=halls[1],
            start_time=now + timedelta(days=2, hours=12),
            price=400.00
        )

        self.stdout.write(self.style.SUCCESS('Созданы сеансы'))