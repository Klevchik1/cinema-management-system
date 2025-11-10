from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime, time
import random
from faker import Faker
import os
from django.core.files import File
from django.conf import settings
from django.db.models import Q

from ticket.models import Hall, Movie, Screening, Seat, User

fake = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Заполняет базу данных расширенными тестовыми данными кинотеатра'

    def handle(self, *args, **options):
        self.clear_old_data()
        self.create_admin()
        halls = self.create_halls()
        movies = self.create_movies()
        self.create_screenings(halls, movies)

        self.stdout.write(self.style.SUCCESS('✅ База успешно заполнена расширенными тестовыми данными!'))

    def clear_old_data(self):
        """Очистка старых данных (кроме суперпользователей)"""
        Hall.objects.all().delete()
        Movie.objects.all().delete()
        Screening.objects.all().delete()
        Seat.objects.all().delete()
        # Не удаляем пользователей, чтобы не потерять админа

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
        """Создание залов разных типов с описаниями"""
        halls_data = [
            {
                'name': 'Стандарт 1',
                'type': 'Стандарт',
                'rows': 10,
                'seats_per_row': 15,
                'description': 'Классический кинозал с комфортными тканевыми креслами, системой звука Dolby Digital и качественным проектором. Идеальный выбор для просмотра фильмов любого жанра.'
            },
            {
                'name': 'Стандарт 2',
                'type': 'Стандарт',
                'rows': 8,
                'seats_per_row': 12,
                'description': 'Уютный зал среднего размера с улучшенной акустикой и панорамным экраном. Отличная видимость с любого места.'
            },
            {
                'name': 'Love Hall',
                'type': 'Love',
                'rows': 6,
                'seats_per_row': 8,
                'description': 'Романтический зал с двухместными диванами вместо кресел. Идеально для пар: уютные пледы, приглушенный свет и интимная атмосфера. 1 билет = 2 места на диване.'
            },
            {
                'name': 'VIP Зал',
                'type': 'VIP',
                'rows': 4,
                'seats_per_row': 6,
                'description': 'Премиальный зал с кожаными креслами-реклайнерами, увеличенным расстоянием между рядами, индивидуальными столиками для напитков и закусок. Обслуживание официантом.'
            },
            {
                'name': 'Комфорт',
                'type': 'Комфорт',
                'rows': 5,
                'seats_per_row': 10,
                'description': 'Зал с мягкими бескаркасными креслами-подушками, расслабляющей атмосферой. Идеален для комфортного просмотра длинных фильмов.'
            },
            {
                'name': 'IMAX',
                'type': 'IMAX',
                'rows': 12,
                'seats_per_row': 20,
                'description': 'Легендарный формат IMAX с гигантским изогнутым экраном, лазерной проекцией и 12-канальной системой звука. Погружение в фильм на 100%.'
            },
            {
                'name': '4DX',
                'type': '4DX',
                'rows': 6,
                'seats_per_row': 8,
                'description': 'Инновационный формат с движущимися креслами, ветром, брызгами воды, ароматами и другими спецэффектами. Полное погружение в действие на экране.'
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
            self.stdout.write(self.style.SUCCESS(f'Создан зал: {hall.name} ({data["type"]})'))

        return halls

    def create_movies(self):
        """Создание фильмов с реальными описаниями"""
        posters_dir = os.path.join(settings.BASE_DIR, 'ticket', 'management', 'commands', 'posters')

        movies_data = [
            {
                'title': 'Аватар: Путь воды',
                'duration': 192,
                'genre': 'фантастика',
                'poster': 'avatar.jpg',
                'description': 'Джейк Салли и Нейтири создали семью, но им вновь угрожают люди с Земли. Чтобы защитить свой дом, им придется отправиться в разные уголки Пандоры и объединиться с другими кланами Нави.'
            },
            {
                'title': 'Оппенгеймер',
                'duration': 180,
                'genre': 'биография',
                'poster': 'oppenheimer.jpg',
                'description': 'История жизни американского физика-теоретика Роберта Оппенгеймера, который руководил Манхэттенским проектом по созданию атомной бомбы во время Второй мировой войны.'
            },
            {
                'title': 'Барби',
                'duration': 114,
                'genre': 'комедия',
                'poster': 'barbie.jpg',
                'description': 'Кукла Барби живет в идеальном мире Барбиленда, но однажды обнаруживает, что ее мир не так прекрасен, как кажется. Вместе с Кеном она отправляется в реальный мир.'
            },
            {
                'title': 'Джон Уик 4',
                'duration': 169,
                'genre': 'боевик',
                'poster': 'john_wick.jpg',
                'description': 'Джон Уик обнаруживает путь к победе над Правлением Кланов. Но прежде чем он сможет заслужить свободу, ему предстоит столкнуться с новым врагом и мощными альянсами.'
            },
            {
                'title': 'Стражи Галактики 3',
                'duration': 150,
                'genre': 'фантастика',
                'poster': 'guardians.jpg',
                'description': 'Питер Квилл все еще оплакивает потерю Гаморы и должен сплотить свою команду, чтобы защитить Вселенную и защитить одного из своих.'
            },
            {
                'title': 'Человек-паук: Паутина вселенных',
                'duration': 140,
                'genre': 'мультфильм',
                'poster': 'spiderman.jpg',
                'description': 'Майлз Моралес переносится через Мультивселенную и встречает команду Людей-пауков, которые должны защитить само ее существование.'
            },
            {
                'title': 'Миссия невыполнима 7',
                'duration': 163,
                'genre': 'боевик',
                'poster': 'mission_impossible.jpg',
                'description': 'Итан Хант и его команда МВФ должны отследить новое ужасающее оружие, которое угрожает всему человечеству.'
            },
            {
                'title': 'Индиана Джонс и реликвия судьбы',
                'duration': 154,
                'genre': 'приключения',
                'poster': 'indiana_jones.jpg',
                'description': 'Археолог Индиана Джонс отправляется в новое опасное приключение, чтобы найти древнюю реликвию, обладающую невероятной силой.'
            },
            {
                'title': 'Дюна',
                'duration': 155,
                'genre': 'фантастика',
                'poster': 'dune.jpg',
                'description': 'Пол Атрейдес вместе с семьей отправляется на опасную планету Арракис, где сталкивается с врагами и начинает путь к своей судьбе.'
            },
            {
                'title': 'Трансформеры: Эпоха зверей',
                'duration': 127,
                'genre': 'фантастика',
                'poster': 'transformers.jpg',
                'description': 'Автоботы и Максималы объединяются с человечеством против террористических Предаконов в битве за Землю.'
            }
        ]

        movies = []
        for data in movies_data:
            movie = Movie.objects.create(
                title=data['title'],
                description=data['description'],
                duration=timedelta(minutes=data['duration']),
                genre=data['genre']
            )

            # Загрузка постера (если файл существует)
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

    def get_time_multiplier(self, screening_time):
        """Возвращает множитель цены в зависимости от времени сеанса"""
        hour = screening_time.hour

        if 8 <= hour < 12:  # Утро
            return 0.8
        elif 12 <= hour < 16:  # День
            return 1.0
        elif 16 <= hour < 20:  # Вечер
            return 1.2
        else:  # Ночь (20-24)
            return 1.4

    def get_hall_base_price(self, hall_name):
        """Базовая цена в зависимости от типа зала"""
        price_ranges = {
            'Стандарт': (300, 400),
            'Love': (800, 1000),  # 2 места = выше цена
            'VIP': (1200, 1500),
            'Комфорт': (500, 600),
            'IMAX': (700, 900),
            '4DX': (800, 1000)
        }

        for hall_type, price_range in price_ranges.items():
            if hall_type in hall_name:
                return random.randint(price_range[0], price_range[1])

        return random.randint(300, 400)  # По умолчанию

    def is_time_slot_available(self, hall, start_time, duration):
        """Проверяет, свободен ли временной слот в зале"""
        end_time = start_time + duration

        # Проверяем пересечения с существующими сеансами
        conflicting_screenings = Screening.objects.filter(
            hall=hall
        ).filter(
            Q(start_time__lt=end_time, end_time__gt=start_time)
        )

        return not conflicting_screenings.exists()

    def create_screenings(self, halls, movies):
        """Создание сеансов на месяц вперед без пересечений"""
        now = timezone.localtime(timezone.now())

        # Времена сеансов с 8 утра до 23:00
        screening_times = [
            '08:00', '09:30', '11:00', '12:30', '14:00',
            '15:30', '17:00', '18:30', '20:00', '21:30', '23:00'
        ]

        created_count = 0
        max_attempts_per_movie = 5  # Максимальное количество попыток найти свободный слот

        # Создаем сеансы на 30 дней вперед
        for day in range(30):
            current_date = now + timedelta(days=day)

            self.stdout.write(f'Создание сеансов на {current_date.strftime("%d.%m.%Y")}...')

            for movie in movies:
                attempts = 0
                screenings_created = 0
                target_screenings = random.randint(2, 4)  # 2-4 сеанса на фильм в день

                while screenings_created < target_screenings and attempts < max_attempts_per_movie:
                    # Случайный зал
                    hall = random.choice(halls)

                    # Случайное время
                    time_str = random.choice(screening_times)
                    screening_time = datetime.combine(
                        current_date.date(),
                        datetime.strptime(time_str, '%H:%M').time()
                    )
                    screening_time = timezone.make_aware(screening_time)

                    # Проверяем, что сеанс заканчивается до 00:00
                    end_time = screening_time + movie.duration + timedelta(minutes=20)  # +20 мин на уборку
                    if end_time.time() > time(23, 59):
                        attempts += 1
                        continue

                    # Проверяем доступность временного слота
                    if not self.is_time_slot_available(hall, screening_time, movie.duration + timedelta(minutes=30)):
                        attempts += 1
                        continue

                    # Рассчитываем цену
                    base_price = self.get_hall_base_price(hall.name)
                    time_multiplier = self.get_time_multiplier(screening_time)
                    final_price = int(base_price * time_multiplier)

                    # Создаем сеанс
                    screening = Screening.objects.create(
                        movie=movie,
                        hall=hall,
                        start_time=screening_time,
                        price=final_price
                    )

                    created_count += 1
                    screenings_created += 1

                    self.stdout.write(
                        f'  ✅ {movie.title} в {screening_time.strftime("%H:%M")} '
                        f'({hall.name}) - {final_price}₽'
                    )

            self.stdout.write(f'  Создано сеансов за день: {created_count}')

        self.stdout.write(self.style.SUCCESS(f'Всего создано {created_count} сеансов'))

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-movies',
            action='store_true',
            help='Пропустить создание фильмов',
        )
        parser.add_argument(
            '--skip-halls',
            action='store_true',
            help='Пропустить создание залов',
        )
        parser.add_argument(
            '--skip-screenings',
            action='store_true',
            help='Пропустить создание сеансов',
        )