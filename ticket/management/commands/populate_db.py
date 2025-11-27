from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from faker import Faker
import os
from django.core.files import File
from django.conf import settings

from ticket.models import Hall, Movie, Screening, Seat, User, Genre

fake = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными кинотеатра'

    def handle(self, *args, **options):
        self.clear_old_data()
        self.create_admin()
        genres = self.create_genres()  # создаем жанры первыми
        halls = self.create_halls()
        movies = self.create_movies(genres)  # передаем словарь жанров
        self.create_screenings(halls, movies)

        self.stdout.write(self.style.SUCCESS('✅ База успешно заполнена тестовыми данными!'))

    def clear_old_data(self):
        """Очистка старых данных (кроме суперпользователей и жанров)"""
        Screening.objects.all().delete()
        Seat.objects.all().delete()
        Movie.objects.all().delete()
        Hall.objects.all().delete()
        Genre.objects.all().delete()  # НЕ удаляем жанры, они постоянные

    def create_admin(self):
        """Создание администратора если его нет"""
        if not User.objects.filter(email='admin@example.com').exists():
            admin = User.objects.create_superuser(
                email='admin@example.com',
                password='admin',
                name='Администратор',
                surname='Системы',
                number='+79001234567'
            )
            self.stdout.write(self.style.SUCCESS(f'Создан администратор: {admin.email}'))
        else:
            self.stdout.write(self.style.SUCCESS('Администратор уже существует'))

    def create_halls(self):
        """Создание залов с описаниями"""
        halls_data = [
            {
                'name': "Красный зал",
                'rows': 10,
                'seats_per_row': 15,
                'description': "Стандартный зал с комфортными креслами и отличной акустикой"
            },
            {
                'name': "Синий зал",
                'rows': 8,
                'seats_per_row': 12,
                'description': "Уютный зал с улучшенной системой звука"
            },
            {
                'name': "VIP Зал",
                'rows': 6,
                'seats_per_row': 8,
                'description': "Премиальный зал с кожаными креслами и обслуживанием"
            }
        ]

        halls = []
        for data in halls_data:
            hall = Hall.objects.create(
                name=data['name'],
                rows=data['rows'],
                seats_per_row=data['seats_per_row'],
                description=data['description']
            )
            halls.append(hall)
            self.stdout.write(self.style.SUCCESS(f'Создан зал: {hall.name}'))

        return halls

    def create_genres(self):
        """Создание основных жанров"""
        genres = [
            'фантастика', 'комедия', 'боевик', 'драма', 'приключения',
            'биография', 'мультфильм', 'ужасы', 'триллер', 'мелодрама'
        ]

        created_genres = {}
        for genre_name in genres:
            genre, created = Genre.objects.get_or_create(name=genre_name)
            created_genres[genre_name] = genre
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан жанр: {genre_name}'))

        return created_genres

    def create_movies(self, genres):
        """Создание фильмов с полными и короткими описаниями"""
        posters_dir = os.path.join(settings.BASE_DIR, 'ticket', 'management', 'commands', 'posters')

        movies_data = [
            {
                'title': 'Аватар: Путь воды',
                'duration': 192,
                'genre': 'фантастика',
                'poster': 'avatar.jpg',
                'short_description': 'Джейк Салли и Нейтири создали семью, но им вновь угрожают люди с Земли.',
                'description': 'Прошло более десяти лет после событий первого фильма. История семьи Салли (Джейка, Нейтири и их детей), бедах, которые их преследуют, усилиях, которые они предпринимают, чтобы оставаться в безопасности, битвах, которые они ведут, чтобы выжить, и трагедиях, которые они переживают. Камерон описывает фильм как „семейную сагу“ о выживании и обязанностях родителей.'
            },
            {
                'title': 'Один дома',
                'duration': 103,
                'genre': 'комедия',
                'poster': 'home_alone.jpg',
                'short_description': '8-летний Кевин случайно остается один дома и защищает свой дом от грабителей.',
                'description': 'Семья Маккаллистеров собирается провести рождественские каникулы в Париже. В суматохе предотъездных сборов они забывают дома одного из своих детей — восьмилетнего Кевина. Поначалу мальчик рад тому, что остался один, и предается всем радостям безнадзорной жизни, но вскоре сталкивается с двумя ворами-неудачниками, задумавшими ограбить его дом. Кевину приходится проявить всю свою смекалку и изобретательность, чтобы защитить дом от грабителей.'
            },
            {
                'title': 'Интерстеллар',
                'duration': 169,
                'genre': 'фантастика',
                'poster': 'interstellar.jpg',
                'short_description': 'Команда исследователей совершает путешествие через червоточину в поисках нового дома для человечества.',
                'description': 'В недалёком будущем из-за глобального потепления и пыльных бурь человечество переживает продовольственный кризис. Бывший пилот НАСА Купер ведёт фермерское хозяйство вместе со своей семьёй. Его дочь Мёрф утверждает, что в её комнате живёт призрак. Купер понимает, что аномалии гравитации — это послание от пришельцев, которые дают человечеству шанс на спасение. Он присоединяется к секретной экспедиции НАСА, целью которой является поиск нового дома для человечества за пределами Солнечной системы.'
            },
            {
                'title': 'Оппенгеймер',
                'duration': 180,
                'genre': 'биография',
                'poster': 'oppenheimer.jpg',
                'short_description': 'История жизни американского физика Роберта Оппенгеймера, создателя атомной бомбы.',
                'description': 'Фильм рассказывает о жизни американского физика-теоретика Роберта Оппенгеймера, который во время Второй мировой войны руководил Манхэттенским проектом — программой по созданию атомной бомбы. Картина охватывает разные периоды его жизни: учёбу в Европе, работу в Калифорнийском университете в Беркли, руководство Лос-Аламосской лабораторией и последующие слушания по допуску к секретной информации в 1954 году.'
            },
            {
                'title': 'Барби',
                'duration': 114,
                'genre': 'комедия',
                'poster': 'barbie.jpg',
                'short_description': 'Кукла Барби живет в идеальном мире, но обнаруживает, что её мир не так прекрасен.',
                'description': 'Кукла Барби живёт в идеальном мире Барбиленда, где каждый день — самый лучший. Однако однажды она обнаруживает, что её мир не так прекрасен, как кажется. Вместе с Кеном она отправляется в реальный мир, чтобы найти ответы на свои вопросы. В ходе путешествия они сталкиваются с радостями и трудностями жизни среди людей и узнают ценность настоящей дружбы и самопознания.'
            }
        ]

        movies = []
        for data in movies_data:
            # Получаем объект Genre из словаря
            if genres and data['genre'] in genres:
                genre_obj = genres[data['genre']]
            else:
                # Если жанра нет в словаре, создаем его
                genre_obj, created = Genre.objects.get_or_create(name=data['genre'])
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Создан жанр: {data["genre"]}'))

            movie = Movie.objects.create(
                title=data['title'],
                short_description=data['short_description'],
                description=data['description'],
                duration=timedelta(minutes=data['duration']),
                genre=genre_obj  # передаем объект Genre
            )

            poster_path = os.path.join(posters_dir, data['poster'])
            if os.path.exists(poster_path):
                with open(poster_path, 'rb') as f:
                    movie.poster.save(data['poster'], File(f))
                    movie.save()
                self.stdout.write(self.style.SUCCESS(f'Создан фильм: {movie.title} (с постером)'))
            else:
                self.stdout.write(
                    self.style.WARNING(f'Создан фильм: {movie.title} (постер не найден: {data["poster"]})'))

            movies.append(movie)

        return movies

    def create_screenings(self, halls, movies):
        """Создание сеансов на ближайшие дни"""
        now = timezone.now()

        # Сеансы на сегодня и завтра
        screenings_data = [
            # Сегодня
            {
                'movie': movies[0],  # Аватар
                'hall': halls[0],
                'start_time': now.replace(hour=14, minute=0, second=0, microsecond=0),
                'price': 450.00
            },
            {
                'movie': movies[2],  # Интерстеллар
                'hall': halls[0],
                'start_time': now.replace(hour=18, minute=30, second=0, microsecond=0),
                'price': 500.00
            },
            {
                'movie': movies[1],  # Один дома
                'hall': halls[1],
                'start_time': now.replace(hour=16, minute=0, second=0, microsecond=0),
                'price': 350.00
            },
            # Завтра
            {
                'movie': movies[3],  # Оппенгеймер
                'hall': halls[0],
                'start_time': now.replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=1),
                'price': 550.00
            },
            {
                'movie': movies[4],  # Барби
                'hall': halls[1],
                'start_time': now.replace(hour=17, minute=30, second=0, microsecond=0) + timedelta(days=1),
                'price': 400.00
            },
            {
                'movie': movies[0],  # Аватар
                'hall': halls[2],
                'start_time': now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=1),
                'price': 800.00  # VIP цена
            },
            # Послезавтра
            {
                'movie': movies[2],  # Интерстеллар
                'hall': halls[0],
                'start_time': now.replace(hour=19, minute=0, second=0, microsecond=0) + timedelta(days=2),
                'price': 500.00
            },
            {
                'movie': movies[1],  # Один дома
                'hall': halls[1],
                'start_time': now.replace(hour=13, minute=0, second=0, microsecond=0) + timedelta(days=2),
                'price': 300.00
            }
        ]

        for screening_data in screenings_data:
            screening = Screening.objects.create(
                movie=screening_data['movie'],
                hall=screening_data['hall'],
                start_time=screening_data['start_time'],
                price=screening_data['price']
            )
            self.stdout.write(self.style.SUCCESS(
                f'Создан сеанс: {screening.movie.title} в {screening.start_time.strftime("%d.%m %H:%M")} '
                f'({screening.hall.name}) - {screening.price}₽'
            ))

        self.stdout.write(self.style.SUCCESS(f'Всего создано {len(screenings_data)} сеансов'))