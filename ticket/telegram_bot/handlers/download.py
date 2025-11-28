from telegram import Update
from telegram.ext import ContextTypes
from ticket.models import User, Ticket
import logging
from asgiref.sync import sync_to_async
from django.utils import timezone
import io
from ticket.utils import generate_ticket_pdf

logger = logging.getLogger(__name__)


@sync_to_async
def get_user_by_telegram_id(telegram_id):
    """Асинхронно ищем пользователя по telegram_chat_id"""
    return User.objects.filter(
        telegram_chat_id=telegram_id,
        is_telegram_verified=True
    ).first()


@sync_to_async
def get_user_active_tickets(user):
    """Асинхронно получаем активные билеты пользователя"""
    now = timezone.now()
    return list(Ticket.objects.filter(
        user=user,
        screening__start_time__gt=now
    ).select_related('screening__movie', 'screening__hall', 'seat').order_by('screening__start_time'))


# Оборачиваем функцию генерации PDF в sync_to_async
@sync_to_async
def generate_ticket_pdf_async(tickets):
    """Асинхронная версия генерации PDF"""
    return generate_ticket_pdf(tickets)


async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /download"""
    user = update.effective_user
    logger.info(f"Download command received from user {user.id}")

    try:
        # Ищем пользователя в Django
        django_user = await get_user_by_telegram_id(user.id)
        logger.info(f"Found Django user: {django_user}")

        if not django_user:
            await update.message.reply_text(
                "❌ <b>Аккаунт не привязан</b>\n\n"
                "Для скачивания билетов необходимо привязать аккаунт в личном кабинете на сайте.",
                parse_mode='HTML'
            )
            return

        # Получаем активные билеты
        tickets = await get_user_active_tickets(django_user)
        logger.info(f"Found {len(tickets)} active tickets for user {django_user.email}")

        if not tickets:
            await update.message.reply_text(
                "🎫 <b>У вас нет активных билетов</b>\n\n"
                "Перейдите на сайт, чтобы купить билеты на сеансы.",
                parse_mode='HTML'
            )
            return

        # Группируем билеты по group_id
        from collections import defaultdict
        ticket_groups = defaultdict(list)

        for ticket in tickets:
            group_id = ticket.group_id if ticket.group_id else f"single_{ticket.id}"
            ticket_groups[group_id].append(ticket)

        logger.info(f"Ticket groups: {len(ticket_groups)}")

        # Отправляем сообщение о начале загрузки
        await update.message.reply_text(
            f"📥 <b>Начинаю загрузку билетов...</b>\n\n"
            f"Найдено {len(ticket_groups)} групп билетов.",
            parse_mode='HTML'
        )

        # Отправляем каждый групповой билет отдельным файлом
        success_count = 0
        for group_id, tickets_list in ticket_groups.items():
            try:
                await send_ticket_pdf(update, tickets_list)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send PDF for group {group_id}: {e}")
                await update.message.reply_text(
                    f"⚠️ Ошибка при загрузке билетов для {tickets_list[0].screening.movie.title}"
                )

        # Финальное сообщение
        if success_count > 0:
            await update.message.reply_text(
                f"✅ <b>Загрузка завершена!</b>\n\n"
                f"Успешно отправлено {success_count} из {len(ticket_groups)} файл(ов) с билетами.\n\n"
                f"Приятного просмотра! 🎬",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ <b>Не удалось загрузить билеты</b>\n\n"
                "Пожалуйста, попробуйте позже или скачайте билеты через личный кабинет на сайте.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in download handler: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при получении билетов.")


async def send_ticket_pdf(update: Update, tickets):
    """Отправка PDF билета"""
    try:
        logger.info(f"Starting PDF generation for {len(tickets)} tickets")

        # Генерируем PDF (асинхронно)
        pdf_buffer = await generate_ticket_pdf_async(tickets)
        logger.info("PDF generated successfully")

        # Создаем файл в памяти
        pdf_file = io.BytesIO(pdf_buffer.getvalue())

        # Формируем имя файла
        screening = tickets[0].screening
        local_time = timezone.localtime(screening.start_time)
        filename = f"билет_{screening.movie.title}_{local_time.strftime('%d.%m.%Y_%H-%M')}.pdf"
        pdf_file.name = filename

        logger.info(f"PDF file prepared: {filename}")

        # Формируем подпись
        seats_info = ", ".join([f"Ряд {t.seat.row}-{t.seat.number}" for t in tickets])
        caption = (
            f"🎫 <b>{screening.movie.title}</b>\n"
            f"📅 {local_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"🏠 {screening.hall.name}\n"
            f"💺 {seats_info}\n"
            f"👤 {tickets[0].user.name} {tickets[0].user.surname}"
        )

        logger.info("Sending PDF to Telegram...")

        # Отправляем файл
        await update.message.reply_document(
            document=pdf_file,
            filename=filename,
            caption=caption,
            parse_mode='HTML'
        )

        logger.info(f"Ticket PDF sent successfully to user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error generating/sending PDF: {e}", exc_info=True)

        # Детальная информация об ошибке
        error_details = f"""
        Error details:
        - Tickets count: {len(tickets) if tickets else 0}
        - Screening: {tickets[0].screening if tickets else 'No tickets'}
        - User: {tickets[0].user if tickets else 'No user'}
        - Exception: {str(e)}
        """
        logger.error(error_details)

        raise  # Пробрасываем ошибку дальше


# async def download_ticket_for_user(user, ticket_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Вспомогательная функция для скачивания билета по ID"""
#     try:
#         from asgiref.sync import sync_to_async
#
#         @sync_to_async
#         def get_ticket(user, ticket_id):
#             return Ticket.objects.filter(id=ticket_id, user=user).first()
#
#         ticket = await get_ticket(user, ticket_id)
#
#         if not ticket:
#             await update.message.reply_text("❌ Билет не найден или у вас нет доступа к этому билету.")
#             return
#
#         # Если билет в группе, получаем все билеты группы
#         if ticket.group_id:
#             @sync_to_async
#             def get_group_tickets(group_id, user):
#                 return list(Ticket.objects.filter(group_id=group_id, user=user))
#
#             tickets = await get_group_tickets(ticket.group_id, user)
#         else:
#             tickets = [ticket]
#
#         # Отправляем билет
#         await send_ticket_pdf(update, tickets)
#
#     except Exception as e:
#         logger.error(f"Error downloading specific ticket: {e}")
#         await update.message.reply_text("❌ Ошибка при скачивании билета.")