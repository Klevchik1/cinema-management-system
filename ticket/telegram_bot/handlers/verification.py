from telegram import Update
from telegram.ext import ContextTypes
from ticket.models import User
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


# Создаем асинхронные версии методов ORM
@sync_to_async
def get_user_by_verification_code(code):
    """Асинхронно ищем пользователя по коду подтверждения"""
    return User.objects.filter(
        telegram_verification_code=code,
        is_telegram_verified=False
    ).first()


@sync_to_async
def get_user_by_telegram_id(telegram_id):
    """Асинхронно ищем пользователя по telegram_chat_id"""
    return User.objects.filter(
        telegram_chat_id=telegram_id,
        is_telegram_verified=True
    ).first()


@sync_to_async
def save_user(user):
    """Асинхронно сохраняем пользователя"""
    user.save()


async def verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кодов подтверждения"""
    user = update.effective_user
    message_text = update.message.text.strip()

    # Логируем полученное сообщение для отладки
    logger.info(f"Received message from user {user.id}: {message_text}")

    try:
        # Ищем пользователя с таким кодом подтверждения (асинхронно)
        django_user = await get_user_by_verification_code(message_text)

        logger.info(f"Found user with code: {django_user}")

        if django_user:
            # Проверяем, не привязан ли уже этот Telegram к другому аккаунту (асинхронно)
            existing_user = await get_user_by_telegram_id(user.id)

            if existing_user:
                await update.message.reply_text(
                    "❌ Этот Telegram аккаунт уже привязан к другому пользователю.",
                    parse_mode='HTML'
                )
                return

            # Привязываем Telegram аккаунт
            django_user.telegram_chat_id = user.id
            django_user.telegram_username = user.username
            django_user.is_telegram_verified = True
            django_user.telegram_verification_code = ''  # Очищаем код

            # Сохраняем пользователя (асинхронно)
            await save_user(django_user)

            success_text = (
                "✅ <b>Аккаунт успешно привязан!</b>\n\n"
                f"Привет, {django_user.name}!\n"
                "Теперь вы будете получать уведомления о покупках билетов.\n\n"
                "Используйте команду /tickets для просмотра ваших билетов."
            )
            await update.message.reply_text(success_text, parse_mode='HTML')
            logger.info(f"User {django_user.email} successfully linked Telegram account")

        else:
            # Неверный код
            error_text = (
                "❌ <b>Неверный код подтверждения</b>\n\n"
                "Пожалуйста, проверьте код и попробуйте снова.\n"
                "Код можно получить в личном кабинете на сайте."
            )
            await update.message.reply_text(error_text, parse_mode='HTML')
            logger.warning(f"User {user.id} entered invalid code: {message_text}")

    except Exception as e:
        logger.error(f"Error in verification handler: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )