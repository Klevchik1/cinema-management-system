import logging
logger = logging.getLogger(__name__)
from audioop import reverse
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.core.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)
import os
from django.conf import settings
from django.utils import timezone
import json


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
    name = models.CharField(max_length=30)
    surname = models.CharField(max_length=30)
    number = models.CharField(max_length=20)

    # Telegram fields
    telegram_chat_id = models.CharField(max_length=15, blank=True, null=True)
    telegram_username = models.CharField(max_length=32, blank=True, null=True)
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

    def unlink_telegram(self):
        """Отвязать Telegram аккаунт"""
        self.telegram_chat_id = None
        self.telegram_username = None
        self.is_telegram_verified = False
        self.telegram_verification_code = None
        self.save()

        logger.info(f"Telegram unlinked for user {self.email}")

        # Логируем операцию если есть request
        try:
            from .logging_utils import OperationLogger
            OperationLogger.log_system_operation(
                action_type='UPDATE',
                module_type='USERS',
                description=f'Отвязка Telegram для пользователя {self.email}',
                object_id=self.id,
                object_repr=str(self)
            )
        except Exception as e:
            logger.error(f"Error logging telegram unlink: {e}")

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

    def save(self, *args, **kwargs):
        # Проверяем уникальность email при сохранении
        if self.email and User.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['number']),
            models.Index(fields=['is_email_verified']),
        ]

class PendingRegistration(models.Model):
    """Временное хранение данных регистрации до подтверждения email"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=30)
    surname = models.CharField(max_length=30)
    number = models.CharField(max_length=20)
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


class PasswordResetRequest(models.Model):
    """Модель для хранения запросов на восстановление пароля"""
    email = models.EmailField(max_length=100)
    reset_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        """Проверка истечения срока действия кода (30 минут)"""
        from django.utils import timezone
        expiration_time = self.created_at + timezone.timedelta(minutes=30)
        return timezone.now() > expiration_time

    def mark_as_used(self):
        """Пометить код как использованный"""
        self.is_used = True
        self.save()

    class Meta:
        verbose_name = "Запрос восстановления пароля"
        verbose_name_plural = "Запросы восстановления пароля"

class Hall(models.Model):
    name = models.CharField(max_length=30)
    rows = models.IntegerField()
    seats_per_row = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

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

    class Meta:
        verbose_name = "Зал"
        verbose_name_plural = "Залы"


class Genre(models.Model):
    name = models.CharField(max_length=30, unique=True, verbose_name='Название жанра')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Приводим имя к стандартному виду: первая буква заглавная, остальные строчные
        if self.name:
            # Убираем лишние пробелы
            self.name = ' '.join(self.name.strip().split())
            # Делаем первую букву заглавной, остальные строчные
            self.name = self.name.title()

        # Проверяем уникальность перед сохранением
        if Genre.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(f'Жанр "{self.name}" уже существует')

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        indexes = [
            models.Index(fields=['name']),
        ]


class AgeRating(models.Model):
    """Модель для возрастных рейтингов """
    name = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Возрастной рейтинг',
        help_text='Например: 0+, 6+, 12+, 16+, 18+'
    )
    description = models.TextField(
        max_length=100,
        verbose_name='Описание ограничения',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Возрастной рейтинг'
        verbose_name_plural = 'Возрастные рейтинги'
        ordering = ['name']


class Movie(models.Model):
    title = models.CharField(max_length=100, verbose_name='Название')
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
    duration = models.DurationField(verbose_name='Длительность')
    genre = models.ForeignKey(
        Genre,
        on_delete=models.PROTECT,
        verbose_name='Жанр'
    )
    age_rating = models.ForeignKey(
        AgeRating,
        on_delete=models.PROTECT,
        verbose_name='Возрастное ограничение',
        related_name='movies'
    )
    poster = models.ImageField(
        upload_to='movie_posters/',
        blank=True,
        null=True,
        verbose_name='Постер фильма'
    )

    def __str__(self):
        return f"{self.title} ({self.age_rating})"

    def save(self, *args, **kwargs):
        # Если короткое описание не задано, создаем его из полного
        if not self.short_description and self.description:
            self.short_description = self.description[:197] + '...' if len(self.description) > 200 else self.description
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['genre']),
            models.Index(fields=['age_rating']),
        ]


class Screening(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name='Фильм')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, verbose_name='Зал')
    start_time = models.DateTimeField(verbose_name='Время начала')
    end_time = models.DateTimeField(verbose_name='Время окончания', blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Цена')

    def clean(self):
        # ВАЖНО: Сначала рассчитываем end_time если нужно
        if self.movie and self.start_time:
            self.end_time = self.start_time + self.movie.duration + timedelta(minutes=10)

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Время окончания сеанса должно быть позже времени начала")

        # Проверяем время работы кинотеатра
        if self.start_time:
            local_start = timezone.localtime(self.start_time)
            if local_start.hour < 8 or local_start.hour >= 23:
                raise ValidationError("Сеансы могут начинаться только с 8:00 до 23:00")

        if self.end_time:
            local_end = timezone.localtime(self.end_time)
            if local_end.hour >= 24 or (local_end.hour == 0 and local_end.minute > 0):
                raise ValidationError("Сеанс должен заканчиваться до 24:00")

        if self.hall and self.start_time and self.end_time:
            overlapping_screenings = Screening.objects.filter(
                hall=self.hall,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk)

            if overlapping_screenings.exists():
                raise ValidationError("Сеанс пересекается с другим сеансом в этом зале")

    def save(self, *args, **kwargs):
        # Всегда пересчитываем end_time при сохранении
        if self.movie and self.start_time:
            self.end_time = self.start_time + self.movie.duration + timedelta(minutes=10)

        # Вызываем clean для дополнительных проверок
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movie.title} - {self.hall.name} ({self.start_time.strftime('%d.%m.%Y %H:%M')})"

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['hall', 'start_time']),
            models.Index(fields=['movie', 'start_time']),
        ]

class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    row = models.IntegerField()
    number = models.IntegerField()

    def __str__(self):
        return f"{self.hall.name} - Ряд {self.row}, Место {self.number}"

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"
        unique_together = ('hall', 'row', 'number')
        indexes = [
            models.Index(fields=['hall', 'row']),
        ]

class TicketStatus(models.Model):
    """Модель для статусов билетов"""
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Код статуса'
    )
    name = models.CharField(
        max_length=30,
        verbose_name='Название статуса'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Описание статуса'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активный статус'
    )
    can_be_refunded = models.BooleanField(
        default=False,
        verbose_name='Можно вернуть из этого статуса'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Статус билета'
        verbose_name_plural = 'Статусы билетов'
        ordering = ['id']

class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    group_id = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    status = models.ForeignKey(
        TicketStatus,
        on_delete=models.PROTECT,
        verbose_name='Статус билета'
    )

    refund_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Запрос возврата'
    )

    refund_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Обработан возврат'
    )

    class Meta:
        unique_together = ('screening', 'seat')
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        indexes = [
            models.Index(fields=['user', 'purchase_date']),
            models.Index(fields=['screening']),
            models.Index(fields=['group_id']),
            models.Index(fields=['purchase_date']),
            models.Index(fields=['status']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем статус по умолчанию при создании
        if not self.pk and not self.status_id:
            try:
                default_status = TicketStatus.objects.filter(is_active=True).first()
                if default_status:
                    self.status = default_status
            except TicketStatus.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем статус при первом сохранении
        if not self.pk and not self.status_id:
            try:
                active_status = TicketStatus.objects.filter(code='active', is_active=True).first()
                if active_status:
                    self.status = active_status
                else:
                    # Создаем статус по умолчанию, если его нет
                    active_status = TicketStatus.objects.create(
                        code='active',
                        name='Активный',
                        description='Билет активен и действителен',
                        is_active=True,
                        can_be_refunded=True
                    )
                    self.status = active_status
            except Exception as e:
                logger.error(f"Error setting default ticket status: {e}")

        super().save(*args, **kwargs)

    def can_be_refunded(self):
        """Проверяет, можно ли вернуть билет с учетом всех условий"""
        from django.utils import timezone

        if not self.status or self.status.code != 'active':
            return False, 'Билет не активен'

        # Проверяем временное ограничение: не менее 30 минут до начала
        time_until_screening = self.screening.start_time - timezone.now()
        minutes_until = time_until_screening.total_seconds() / 60

        if minutes_until < 30:
            return False, f'Возврат невозможен. До сеанса осталось {int(minutes_until)} минут'

        # Проверяем что сеанс еще не начался
        if self.screening.start_time <= timezone.now():
            return False, 'Сеанс уже начался'

        return True, 'Возврат возможен'

    def request_refund(self):
        """Запрос возврата билета с автоматической обработкой"""
        from django.utils import timezone

        # Проверяем можно ли вернуть
        can_refund, message = self.can_be_refunded()

        if not can_refund:
            return False, message

        try:
            # Если все условия соблюдены, сразу обрабатываем возврат
            refunded_status = TicketStatus.objects.get(code='refunded')
            self.status = refunded_status
            self.refund_requested_at = timezone.now()
            self.refund_processed_at = timezone.now()  # сразу обработан
            self.save()

            # Логируем автоматический возврат
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Автоматический возврат билета #{self.id}, фильм: {self.screening.movie.title}")

            return True, '✅ Билет успешно возвращен! Полная стоимость будет возвращена.'

        except TicketStatus.DoesNotExist as e:
            logger.error(f"Статус 'refunded' не найден: {e}")
            return False, 'Ошибка: статус возврата не найден в системе'
        except Exception as e:
            logger.error(f"Ошибка при возврате билета #{self.id}: {e}")
            return False, f'Ошибка при обработке возврата: {str(e)}'

    def process_refund(self):
        """Обработка возврата (админ)"""
        try:
            refunded_status = TicketStatus.objects.get(code='refunded')
            if self.status.code != 'refund_requested':
                return False, 'Билет не запрашивал возврат'

            self.status = refunded_status
            self.refund_processed_at = timezone.now()
            self.save()
            return True, 'Возврат обработан'
        except TicketStatus.DoesNotExist:
            return False, 'Статус "Возвращен" не найден'

    def cancel_refund_request(self):
        """Отмена запроса на возврат"""
        try:
            active_status = TicketStatus.objects.get(code='active')
            if self.status.code != 'refund_requested':
                return False, 'Билет не запрашивал возврат'

            self.status = active_status
            self.refund_requested_at = None
            self.save()
            return True, 'Запрос на возврат отменен'
        except TicketStatus.DoesNotExist:
            return False, 'Статус "Активный" не найден'

    def get_status_display(self):
        """Получить отображаемое название статуса"""
        return self.status.name if self.status else "Неизвестно"

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
    name = models.CharField(max_length=100)
    backup_file = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    backup_type = models.CharField(max_length=15, choices=[
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


# Модель-заглушка для отчетов
class Report(models.Model):
    """Модель для отображения отчетов в админке"""

    class Meta:
        verbose_name = "Отчет"
        verbose_name_plural = "Отчеты"
        app_label = 'ticket'

    def __str__(self):
        return "Система отчетности"


class OperationLog(models.Model):
    """Модель для логирования операций в системе"""

    ACTION_TYPES = [
        ('CREATE', 'Создание'),
        ('UPDATE', 'Обновление'),
        ('DELETE', 'Удаление'),
        ('VIEW', 'Просмотр'),
        ('EXPORT', 'Экспорт'),
        ('LOGIN', 'Вход'),
        ('LOGOUT', 'Выход'),
        ('BACKUP', 'Бэкап'),
        ('REPORT', 'Отчет'),
        ('OTHER', 'Другое'),
    ]

    MODULE_TYPES = [
        ('USERS', 'Пользователи'),
        ('MOVIES', 'Фильмы'),
        ('HALLS', 'Залы'),
        ('SCREENINGS', 'Сеансы'),
        ('TICKETS', 'Билеты'),
        ('REPORTS', 'Отчеты'),
        ('BACKUPS', 'Бэкапы'),
        ('SYSTEM', 'Система'),
        ('AUTH', 'Аутентификация'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    action_type = models.CharField(
        max_length=10,
        choices=ACTION_TYPES,
        verbose_name='Тип действия'
    )
    module_type = models.CharField(
        max_length=15,
        choices=MODULE_TYPES,
        verbose_name='Модуль'
    )
    description = models.TextField(verbose_name='Описание')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP адрес')
    user_agent = models.TextField(null=True, blank=True, verbose_name='User Agent')
    object_id = models.IntegerField(null=True, blank=True, verbose_name='ID объекта')
    object_repr = models.CharField(max_length=100, null=True, blank=True, verbose_name='Объект')
    additional_data = models.JSONField(null=True, blank=True, verbose_name='Дополнительные данные')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='Время операции')

    class Meta:
        verbose_name = 'Лог операции'
        verbose_name_plural = 'Логи операций'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['action_type']),
            models.Index(fields=['module_type']),
        ]

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.get_module_type_display()} - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"

    def get_additional_data_display(self):
        """Форматированный вывод дополнительных данных"""
        if self.additional_data:
            try:
                return json.dumps(self.additional_data, ensure_ascii=False, indent=2)
            except:
                return str(self.additional_data)
        return "-"

class EmailChangeRequest(models.Model):
    """Модель для хранения запросов на смену email"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        """Проверка истечения срока действия кода (30 минут)"""
        from django.utils import timezone
        expiration_time = self.created_at + timezone.timedelta(minutes=30)
        return timezone.now() > expiration_time

    def mark_as_used(self):
        """Пометить запрос как использованный"""
        self.is_used = True
        self.save()

    class Meta:
        verbose_name = "Запрос смены email"
        verbose_name_plural = "Запросы смены email"