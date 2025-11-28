from telegram import Update
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
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

    logger.info(f"Received message from user {user.id}: {message_text}")

    try:
        # Сначала проверяем, не привязан ли пользователь уже
        existing_user = await get_user_by_telegram_id(user.id)
        if existing_user:
            await update.message.reply_text(
                "✅ Ваш аккаунт уже привязан! Используйте кнопки для управления билетами.",
                parse_mode='HTML'
            )
            return

        # Ищем пользователя с таким кодом подтверждения
        django_user = await get_user_by_verification_code(message_text)

        logger.info(f"Found user with code: {django_user}")

        if django_user:
            # Проверяем, не привязан ли уже этот Telegram к другому аккаунту
            existing_user_with_same_telegram = await get_user_by_telegram_id(user.id)

            if existing_user_with_same_telegram:
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

            # Сохраняем пользователя
            await save_user(django_user)

            success_text = (
                "✅ <b>Аккаунт успешно привязан!</b>\n\n"
                f"Привет, {django_user.name}!\n"
                "Теперь вы будете получать уведомления о покупках билетов.\n\n"
                "Используйте кнопки ниже для управления билетами."
            )

            # Показываем меню с кнопками
            keyboard = [
                [KeyboardButton("🎫 Мои билеты")],
                [KeyboardButton("👤 Профиль"), KeyboardButton("ℹ️ Помощь")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(success_text, parse_mode='HTML', reply_markup=reply_markup)
            logger.info(f"User {django_user.email} successfully linked Telegram account")

        else:
            # Неверный код - показываем инструкцию
            error_text = (
                "❌ <b>Неверный код подтверждения</b>\n\n"
                "💡 <b>Как получить правильный код:</b>\n"
                "1. Перейдите в личный кабинет на сайте\n"
                "2. В разделе Telegram нажмите 'Получить код привязки'\n"
                "3. Скопируйте новый код\n"
                "4. Отправьте его мне\n\n"
                "Код действителен в течение 10 минут."
            )
            await update.message.reply_text(error_text, parse_mode='HTML')
            logger.warning(f"User {user.id} entered invalid code: {message_text}")

    except Exception as e:
        logger.error(f"Error in verification handler: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )