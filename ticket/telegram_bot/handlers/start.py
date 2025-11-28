from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from ticket.models import User
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)


@sync_to_async
def get_user_by_telegram_id(telegram_id):
    """Асинхронно ищем пользователя по telegram_chat_id"""
    return User.objects.filter(telegram_chat_id=str(telegram_id)).first()


@sync_to_async
def generate_verification_code_for_user(user):
    """Асинхронно генерируем код подтверждения"""
    if user:
        return user.generate_verification_code()
    else:
        # Генерируем код без создания пользователя
        import random
        import string
        return ''.join(random.choices(string.digits, k=6))


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user

    try:
        # Асинхронно ищем пользователя
        db_user = await get_user_by_telegram_id(user.id)

        if db_user and db_user.is_telegram_verified:
            # ПОКАЗЫВАЕМ ТОЛЬКО 3 КНОПКИ
            keyboard = [
                [KeyboardButton("🎫 Мои билеты")],
                [KeyboardButton("👤 Профиль"), KeyboardButton("ℹ️ Помощь")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            welcome_text = f"""
✅ Ваш аккаунт привязан: {db_user.email}

Добро пожаловать в бот Кинотеатра Премьера! 🎬

Используйте кнопки ниже для управления билетами.
"""
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)

        else:
            # Пользователь не привязан - просто сообщаем
            help_text = f"""
👋 Привет, {user.first_name}!

Для привязки аккаунта отправьте мне код подтверждения из личного кабинета.

💡 <b>Как получить код:</b>
1. Перейдите в личный кабинет на сайте
2. В разделе Telegram нажмите "Получить код привязки"
3. Скопируйте полученный код
4. Отправьте его мне в этом чате

После привязки вы сможете управлять билетами через бота!
"""
            await update.message.reply_text(
                help_text,
                parse_mode='HTML',
                reply_markup=None
            )

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=None
        )