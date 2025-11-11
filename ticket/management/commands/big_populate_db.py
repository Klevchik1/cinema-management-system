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
        """Создание 5 залов разных типов с описаниями"""
        halls_data = [
            {
                'name': 'Стандарт',
                'rows': 10,
                'seats_per_row': 15,
                'description': 'Классический кинозал с комфортными тканевыми креслами, системой звука Dolby Digital и качественным проектором. Идеальный выбор для просмотра фильмов любого жанра.'
            },
            {
                'name': 'VIP Зал',
                'rows': 6,
                'seats_per_row': 8,
                'description': 'Премиальный зал с кожаными креслами-реклайнерами, увеличенным расстоянием между рядами, индивидуальными столиками для напитков и закусок. Обслуживание официантом.'
            },
            {
                'name': 'Love Hall',
                'rows': 5,
                'seats_per_row': 6,
                'description': 'Романтический зал с двухместными диванами вместо кресел. 1 билет = диван на двух человек. Идеально для пар: уютные пледы, приглушенный свет и интимная атмосфера.'
            },
            {
                'name': 'Комфорт',
                'rows': 7,
                'seats_per_row': 10,
                'description': 'Зал с мягкими бескаркасными креслами-подушками вместо обычных кресел. Расслабляющая атмосфера, идеально для комфортного просмотра длинных фильмов.'
            },
            {
                'name': 'IMAX',
                'rows': 12,
                'seats_per_row': 18,
                'description': 'Легендарный формат IMAX с гигантским изогнутым экраном, лазерной проекцией и 12-канальной системой звука. Погружение в фильм на 100%.'
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

    def create_movies(self):
        """Создание 12 фильмов с реальными описаниями"""
        posters_dir = os.path.join(settings.BASE_DIR, 'ticket', 'management', 'commands', 'posters')

        movies_data = [
            {
                'title': 'Аватар: Путь воды',
                'duration': 192,
                'genre': 'фантастика',
                'poster': 'avatar.jpg',
                'short_description': 'Джейк Салли и Нейтири создали семью, но им вновь угрожают люди с Земли.',
                'description': 'Прошло более десяти лет после событий первого фильма "Аватар". Джейк Салли и Нейтири создали семью и делают всё возможное, чтобы оставаться вместе. Однако им вновь угрожает опасность с Земли. Когда древние метки снова появляются, Джейк должен вести войну против людей. В поисках убежища семья Салли отправляется в регионы Пандоры, населённые другими кланами На\'ви. Живя среди нового племени, они учатся жить и выживать в водной среде, одновременно готовясь к неизбежной битве, которая определит будущее Пандоры.'
            },
            {
                'title': 'Один дома',
                'duration': 103,
                'genre': 'комедия',
                'poster': 'home_alone.jpg',
                'short_description': '8-летний Кевин случайно остается один дома и защищает свой дом от грабителей.',
                'description': 'Семья Маккаллистеров в спешке собирается в рождественское путешествие в Париж. В суматохе они забывают дома своего восьмилетнего сына Кевина. Поначалу мальчик рад возможности пожить самостоятельно: он ест сладости, смотрит запрещённые фильмы и устраивает беспорядок. Но вскоре он обнаруживает, что его дом стал мишенью для двух незадачливых грабителей — Гарри и Марва. Используя всю свою смекалку, Кевин превращает дом в крепость с хитроумными ловушками, чтобы дать отпор непрошеным гостям в канун Рождества.'
            },
            {
                'title': 'Интерстеллар',
                'duration': 169,
                'genre': 'фантастика',
                'poster': 'interstellar.jpg',
                'short_description': 'Команда исследователей совершает путешествие через червоточину в поисках нового дома для человечества.',
                'description': 'В недалёком будущем из-за глобального потепления и пыльных бурь человечество переживает продовольственный кризис. Бывший пилот НАСА Купер ведёт фермерское хозяйство вместе со своей семьёй в американской глубинке. Когда его дочь Мёрф утверждает, что в её комнате живёт призрак, Купер понимает, что аномалии гравитации — это послание от пришельцев, которые дают человечеству шанс на спасение. Он присоединяется к секретной экспедиции НАСА, целью которой является поиск нового дома для человечества за пределами Солнечной системы через червоточину.'
            },
            {
                'title': 'Оппенгеймер',
                'duration': 180,
                'genre': 'биография',
                'poster': 'oppenheimer.jpg',
                'short_description': 'История жизни американского физика Роберта Оппенгеймера, создателя атомной бомбы.',
                'description': 'Фильм рассказывает о жизни американского физика-теоретика Роберта Оппенгеймера, который во время Второй мировой войны руководил Манхэттенским проектом — программой по созданию атомной бомбы. Картина охватывает разные периоды его жизни: учёбу в Европе, работу в Калифорнийском университете в Беркли, руководство Лос-Аламосской лабораторией и последующие слушания по допуску к секретной информации в 1954 году. Фильм исследует моральные дилеммы, с которыми столкнулся учёный, создавая оружие массового уничтожения.'
            },
            {
                'title': 'Барби',
                'duration': 114,
                'genre': 'комедия',
                'poster': 'barbie.jpg',
                'short_description': 'Кукла Барби живет в идеальном мире, но обнаруживает, что её мир не так прекрасен.',
                'description': 'Кукла Барби живёт в идеальном мире Барбиленда, где каждый день — самый лучший. Однако однажды она начинает замечать странные изменения: её утренний тост подгорает, а во время вечеринки у бассейна она внезапно задумывается о смерти. Чтобы исправить ситуацию, она отправляется в реальный мир вместе с Кеном. В ходе путешествия они сталкиваются с радостями и трудностями жизни среди людей, узнают ценность настоящей дружбы и самопознания, а также понимают, что совершенство — это не всегда то, к чему нужно стремиться.'
            },
            {
                'title': 'Джон Уик 4',
                'duration': 169,
                'genre': 'боевик',
                'poster': 'john_wick.jpg',
                'short_description': 'Джон Уик обнаруживает путь к победе над Правлением Кланов.',
                'description': 'Джон Уик продолжает свой путь к свободе, сталкиваясь с новыми врагами и могущественными альянсами. На этот раз ему предстоит сразиться с Правлением Кланов, которое сосредоточило против него все свои силы. Чтобы победить, Уик должен найти способ уничтожить организацию изнутри. Его ждут эпические сражения в Париже, Берлине, Нью-Йорке и Осаке, где он столкнётся с самыми опасными противниками в своей жизни.'
            },
            {
                'title': 'Стражи Галактики 3',
                'duration': 150,
                'genre': 'фантастика',
                'poster': 'guardians.jpg',
                'short_description': 'Питер Квилл все еще оплачивает потерю Гаморы и должен сплотить свою команду.',
                'description': 'Питер Квилл всё ещё оплакивает потерю Гаморы и должен сплотить свою команду, чтобы защитить Вселенную и защитить одного из своих. В этой заключительной главе Стражи Галактики отправляются в опасное путешествие, чтобы раскрыть тайны происхождения Ракеты. По пути они сталкиваются с новыми и старыми врагами, которые угрожают уничтожить их и всю галактику. Команде предстоит пройти через самые трудные испытания, чтобы остаться вместе.'
            },
            {
                'title': 'Человек-паук: Паутина вселенных',
                'duration': 140,
                'genre': 'мультфильм',
                'poster': 'spiderman.jpg',
                'short_description': 'Майлз Моралес переносится через Мультивселенную и встречает команду Людей-пауков.',
                'description': 'Майлз Моралес возвращается в следующей главе оскароносной саги "Человек-паук: Через вселенные". Во время путешествия по Мультивселенной он встречает команду Людей-пауков, которые должны защитить само её существование. Когда герои сталкиваются с новым врагом, Майлзу приходится переосмыслить всё, что значит быть героем, чтобы спасти близких из разных измерений. Фильм исследует идею о том, что любой человек может надеть маску и стать героем.'
            },
            {
                'title': 'Миссия невыполнима 7',
                'duration': 163,
                'genre': 'боевик',
                'poster': 'mission_impossible.jpg',
                'short_description': 'Итан Хант и его команда МВФ должны отследить новое ужасающее оружие.',
                'description': 'Итан Хант и его команда МВФ должны отследить новое ужасающее оружие, которое угрожает всему человечеству, если оно окажется в неправильных руках. С контролем над будущим и судьбой мира в своих руках, и с темными силами из прошлого Итана, начинается смертельная гонка по всему миру. Столкнувшись с загадочным и всемогущим противником, Итан вынужден считать, что ничто не имеет значения больше, чем его миссия — даже жизни тех, кто ему дорог.'
            },
            {
                'title': 'Индиана Джонс и реликвия судьбы',
                'duration': 154,
                'genre': 'приключения',
                'poster': 'indiana_jones.jpg',
                'short_description': 'Археолог Индиана Джонс отправляется в новое опасное приключение.',
                'description': 'Археолог Индиана Джонс отправляется в новое опасное приключение, чтобы найти древнюю реликвию, обладающую невероятной силой. Действие фильма происходит в 1969 году, на фоне космической гонки. Джонс понимает, что его давно потерянный племянник работает на злодейскую организацию, которая надеется использовать артефакт для изменения хода истории. Чтобы сорвать их планы, Индиана должен объединиться со своей крестницей и отправиться в путешествие, которое приведёт его в самые отдалённые уголки мира.'
            },
            {
                'title': 'Дюна',
                'duration': 155,
                'genre': 'фантастика',
                'poster': 'dune.jpg',
                'short_description': 'Пол Атрейдес вместе с семьей отправляется на опасную планету Арракис.',
                'description': 'Пол Атрейдес вместе с семьёй отправляется на опасную планету Арракис, где сталкивается с врагами и начинает путь к своей судьбе. На этой пустынной планете находится самый ценный ресурс во вселенной — пряность, которая продлевает жизнь и делает возможными межзвёздные путешествия. Когда его семья попадает в ловушку зловещего заговора, Пол должен отправиться в самое сердце Арракиса, чтобы встретиться с фрименами и исполнить древнее пророчество, которое изменит судьбу галактики.'
            },
            {
                'title': 'Трансформеры: Эпоха зверей',
                'duration': 127,
                'genre': 'фантастика',
                'poster': 'transformers.jpg',
                'short_description': 'Автоботы и Максималы объединяются с человечеством против террористических Предаконов.',
                'description': 'Автоботы и Максималы объединяются с человечеством против террористических Предаконов в битве за Землю. Действие фильма происходит в 1994 году, когда гигантские роботы скрываются среди людей. Когда новая угроза emerges из космоса, Автоботы должны объединиться с племенем Максималов, чтобы защитить планету от уничтожения. В этой эпической битве решается судьба не только Земли, но и всей галактики.'
            }
        ]

        movies = []
        for data in movies_data:
            movie = Movie.objects.create(
                title=data['title'],
                short_description=data['short_description'],
                description=data['description'],
                duration=timedelta(minutes=data['duration']),
                genre=data['genre']
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

    def get_time_multiplier(self, screening_time):
        """Возвращает множитель цены в зависимости от времени сеанса"""
        hour = screening_time.hour
        if 8 <= hour < 12:  # Утро (самые дешевые)
            return 0.7
        elif 12 <= hour < 16:  # День
            return 0.9
        elif 16 <= hour < 20:  # Вечер (популярное время)
            return 1.2
        else:  # Ночь (20-24) - дороже
            return 1.4

    def get_hall_base_price(self, hall_name):
        """Базовая цена в зависимости от типа зала"""
        price_ranges = {
            'Стандарт': (300, 400),
            'VIP': (1000, 1200),  # Самые дорогие - VIP
            'Love': (800, 1000),  # Love Hall дороже стандарта (2 места)
            'Комфорт': (500, 600),  # Комфорт дороже стандарта
            'IMAX': (700, 900)  # IMAX дороже стандарта
        }
        for hall_type, price_range in price_ranges.items():
            if hall_type in hall_name:
                return random.randint(price_range[0], price_range[1])
        return random.randint(300, 400)

    def is_time_slot_available(self, hall, start_time, duration):
        """Проверяет, свободен ли временной слот в зале"""
        end_time = start_time + duration + timedelta(minutes=20)  # +20 минут на уборку

        # Проверяем, что сеанс заканчивается до 00:00
        if end_time.time() > time(23, 59):
            return False

        conflicting_screenings = Screening.objects.filter(
            hall=hall
        ).filter(
            Q(start_time__lt=end_time, end_time__gt=start_time)
        )
        return not conflicting_screenings.exists()

    def create_screenings(self, halls, movies):
        """Создание сеансов на месяц вперед - минимум 10 сеансов на фильм"""
        now = timezone.localtime(timezone.now())
        # Сеансы с 8 утра до 22:00 (последний сеанс должен закончиться до 00:00)
        screening_times = ['08:00', '10:30', '13:00', '15:30', '18:00', '20:30', '22:00']
        created_count = 0
        screenings_per_movie = {movie.id: 0 for movie in movies}

        # Создаем сеансы на 30 дней вперед
        for day in range(30):
            current_date = now + timedelta(days=day)
            if day % 7 == 0:
                self.stdout.write(f'Создание сеансов на {current_date.strftime("%d.%m.%Y")}...')

            # Для каждого дня создаем расписание для каждого зала
            for hall in halls:
                available_times = screening_times.copy()
                random.shuffle(available_times)  # Перемешиваем времена для разнообразия

                for time_str in available_times:
                    # Выбираем случайный фильм, у которого еще мало сеансов
                    available_movies = [m for m in movies if screenings_per_movie[m.id] < 15]
                    if not available_movies:
                        available_movies = movies

                    movie = random.choice(available_movies)

                    screening_time = datetime.combine(
                        current_date.date(),
                        datetime.strptime(time_str, '%H:%M').time()
                    )
                    screening_time = timezone.make_aware(screening_time)

                    # Проверяем, что сеанс не в прошлом и слот свободен
                    if screening_time < now:
                        continue

                    if not self.is_time_slot_available(hall, screening_time, movie.duration):
                        continue

                    # Рассчитываем цену
                    base_price = self.get_hall_base_price(hall.name)
                    time_multiplier = self.get_time_multiplier(screening_time)
                    final_price = int(base_price * time_multiplier)

                    # Создаем сеанс
                    Screening.objects.create(
                        movie=movie,
                        hall=hall,
                        start_time=screening_time,
                        price=final_price
                    )

                    created_count += 1
                    screenings_per_movie[movie.id] += 1

        # Выводим статистику
        self.stdout.write(self.style.SUCCESS(f'Всего создано {created_count} сеансов'))
        for movie in movies:
            self.stdout.write(self.style.SUCCESS(f'  {movie.title}: {screenings_per_movie[movie.id]} сеансов'))

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