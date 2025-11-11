from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
import logging
from django.conf import settings
from ticket.models import User
from .handlers.start import start_handler
from .handlers.verification import verification_handler
from .handlers.tickets import tickets_handler
import asyncio
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class CinemaBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None

    async def start_async(self):
        """Асинхронный запуск бота"""
        try:
            logger.info(f"Starting bot with token: {self.token[:10]}...")

            self.application = Application.builder().token(self.token).build()

            # Регистрация обработчиков
            self.setup_handlers()

            # Запуск бота
            logger.info("Starting bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("✅ Telegram bot started successfully!")

            # Бесконечный цикл чтобы бот не завершался
            while True:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            raise

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Команды
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("tickets", tickets_handler))

        # Обработка кодов подтверждения (любое текстовое сообщение)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verification_handler))

        # Обработка ошибок
        self.application.add_error_handler(self.error_handler)

    async def error_handler(self, update, context):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")

    async def send_ticket_notification(self, user, tickets):
        """Отправка уведомления о покупке билетов"""
        try:
            if user.telegram_chat_id and self.application:
                message = self.format_ticket_notification(tickets)
                await self.application.bot.send_message(
                    chat_id=user.telegram_chat_id,
                    text=message,
                    parse_mode='HTML'
                )
                logger.info(f"Ticket notification sent to user {user.email}")
        except Exception as e:
            logger.error(f"Error sending ticket notification: {e}")

    def format_ticket_notification(self, tickets):
        """Форматирование уведомления о билетах"""
        if not tickets:
            return ""

        screening = tickets[0].screening
        seats_info = ", ".join([f"Ряд {t.seat.row}-{t.seat.number}" for t in tickets])
        total_price = sum(t.screening.price for t in tickets)

        message = (
            "🎫 <b>Покупка билетов подтверждена!</b>\n\n"
            f"<b>Фильм:</b> {screening.movie.title}\n"
            f"<b>Дата и время:</b> {screening.start_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"<b>Зал:</b> {screening.hall.name}\n"
            f"<b>Места:</b> {seats_info}\n"
            f"<b>Общая стоимость:</b> {total_price} ₽\n\n"
            "Билеты доступны в вашем личном кабинете на сайте."
        )
        return message


# Глобальный экземпляр бота
_bot_instance = None


def get_bot():
    """Получить экземпляр бота"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CinemaBot()
    return _bot_instance


async def start_bot_async():
    """Асинхронная функция запуска бота"""
    bot = get_bot()
    await bot.start_async()


def start_bot():
    """Синхронная обертка для запуска бота"""
    try:
        # Создаем и запускаем event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_bot_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        loop.close()


@sync_to_async
def get_user_tickets_for_notification(user, tickets):
    """Асинхронно получаем данные для уведомления"""
    # Просто возвращаем переданные данные, так как они уже загружены
    return {
        'user': user,
        'tickets': list(tickets)
    }


async def send_ticket_notification(self, user, tickets):
    """Отправка уведомления о покупке билетов"""
    try:
        if user.telegram_chat_id and self.application:
            # Асинхронно получаем данные
            notification_data = await get_user_tickets_for_notification(user, tickets)
            user_obj = notification_data['user']
            tickets_list = notification_data['tickets']

            message = self.format_ticket_notification(tickets_list)
            await self.application.bot.send_message(
                chat_id=user_obj.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Ticket notification sent to user {user_obj.email}")
    except Exception as e:
        logger.error(f"Error sending ticket notification: {e}")