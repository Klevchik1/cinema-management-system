from telegram import Update
from telegram.ext import ContextTypes
from ticket.models import User, Ticket
import logging
from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


@sync_to_async
def get_user_by_telegram_id(telegram_id):
    """Асинхронно ищем пользователя по telegram_chat_id"""
    return User.objects.filter(
        telegram_chat_id=telegram_id,
        is_telegram_verified=True
    ).first()


@sync_to_async
def get_user_tickets(user):
    """Асинхронно получаем билеты пользователя"""
    now = timezone.now()
    return list(Ticket.objects.filter(
        user=user,
        screening__start_time__gt=now
    ).select_related('screening__movie', 'screening__hall', 'seat').order_by('screening__start_time'))


async def tickets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /tickets"""
    user = update.effective_user

    try:
        # Ищем пользователя в Django (асинхронно)
        django_user = await get_user_by_telegram_id(user.id)

        if not django_user:
            await update.message.reply_text(
                "❌ <b>Аккаунт не привязан</b>\n\n"
                "Для просмотра билетов необходимо привязать аккаунт в личном кабинете на сайте.",
                parse_mode='HTML'
            )
            return

        # Получаем активные билеты (асинхронно)
        tickets = await get_user_tickets(django_user)

        if not tickets:
            await update.message.reply_text(
                "🎫 <b>У вас нет активных билетов</b>\n\n"
                "Перейдите на сайт, чтобы купить билеты на сеансы.",
                parse_mode='HTML'
            )
            return

        # Группируем билеты по сеансам
        from collections import defaultdict
        screening_tickets = defaultdict(list)

        for ticket in tickets:
            screening_tickets[ticket.screening].append(ticket)

        # Формируем сообщение
        message = "🎫 <b>Ваши активные билеты:</b>\n\n"

        for screening, screening_tickets_list in screening_tickets.items():
            message += (
                f"<b>🎬 {screening.movie.title}</b>\n"
                f"📅 {screening.start_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"🏠 {screening.hall.name}\n"
                f"💺 {', '.join(f'Ряд {t.seat.row}-{t.seat.number}' for t in screening_tickets_list)}\n"
                f"💰 {screening.price * len(screening_tickets_list)} ₽\n\n"
            )

        message += "Для скачивания билетов перейдите в личный кабинет на сайте."

        await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in tickets handler: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при получении билетов.")