from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_verification_email(pending_registration):
    """Отправка email с кодом подтверждения для временной регистрации"""
    try:
        subject = 'Подтверждение email - Кинотеатр Премьера'

        # HTML версия письма
        html_message = render_to_string('ticket/email_verification.html', {
            'user_name': pending_registration.name,
            'verification_code': pending_registration.verification_code,
        })

        # Текстовая версия письма
        plain_message = f"""
        Подтверждение email - Кинотеатр Премьера

        Здравствуйте, {pending_registration.name}!

        Для завершения регистрации введите следующий код подтверждения:

        {pending_registration.verification_code}

        Код действителен в течение 30 минут.

        Если вы не регистрировались в нашем кинотеатре, просто проигнорируйте это письмо.

        С уважением,
        Команда Кинотеатра Премьера
        """

        # Отправляем email
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pending_registration.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Verification email sent to {pending_registration.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {pending_registration.email}: {str(e)}")
        return False


def send_welcome_email(user):
    """Отправка приветственного письма после подтверждения"""
    try:
        subject = 'Добро пожаловать в Кинотеатр Премьера!'

        html_message = render_to_string('ticket/welcome_email.html', {
            'user': user,
        })

        plain_message = f"""
        Добро пожаловать в Кинотеатр Премьера!

        Здравствуйте, {user.name} {user.surname}!

        Ваш email успешно подтверждён. Теперь вы можете:

        • Покупать билеты на сеансы
        • Получать уведомления о покупках
        • Привязать Telegram для получения уведомлений
        • Скачивать электронные билеты

        Начните прямо сейчас: http://localhost:8000

        С уважением,
        Команда Кинотеатра Премьера
        """

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, reset_code):
    """Отправка email с кодом восстановления пароля"""
    try:
        subject = 'Восстановление пароля - Кинотеатр Премьера'

        # HTML версия письма
        html_message = render_to_string('ticket/password_reset_email.html', {
            'user': user,
            'reset_code': reset_code,
        })

        # Текстовая версия письма
        plain_message = f"""
        Восстановление пароля - Кинотеатр Премьера

        Здравствуйте, {user.name}!

        Для восстановления пароля введите следующий код:

        {reset_code}

        Код действителен в течение 30 минут.

        Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.

        С уважением,
        Команда Кинотеатра Премьера
        """

        # Отправляем email
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False