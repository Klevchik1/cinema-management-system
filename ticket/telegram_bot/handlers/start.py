from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    message = update.message

    welcome_text = (
        "👋 <b>Добро пожаловать в Cinema Premier Bot!</b>\n\n"
        "Я буду присылать вам:\n"
        "• Уведомления о покупке билетов\n"
        "• Напоминания о сеансах\n"
        "• Специальные предложения\n\n"
        "<b>Для привязки аккаунта:</b>\n"
        "1. Зайдите в личный кабинет на сайте\n"
        "2. Нажмите 'Привязать Telegram'\n"
        "3. Введите код подтверждения сюда\n\n"
        "<b>Доступные команды:</b>\n"
        "/start - показать это сообщение\n"
        "/tickets - мои билеты\n"
        "/help - помощь\n\n"
        "<b>Сайт кинотеатра:</b> ваш-домен-здесь"
    )

    await message.reply_text(welcome_text, parse_mode='HTML')
    logger.info(f"User {user.id} started the bot")