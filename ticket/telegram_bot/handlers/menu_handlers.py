from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from ticket.models import User, Ticket
from django.utils import timezone
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)


@sync_to_async
def check_user_verified(user_id):
    """Проверяем, привязан ли пользователь"""
    user = User.objects.filter(telegram_chat_id=str(user_id)).first()
    return user and user.is_telegram_verified


@sync_to_async
def get_user_tickets(user_id):
    """Получаем билеты пользователя"""
    user = User.objects.filter(telegram_chat_id=str(user_id)).first()
    if not user:
        return []

    tickets = Ticket.objects.filter(
        user=user
    ).select_related(
        'screening__movie', 'screening__hall'
    ).order_by('-purchase_date')

    return list(tickets)


@sync_to_async
def get_ticket_by_id(ticket_id, user_id):
    """Получаем билет по ID с проверкой владельца"""
    user = User.objects.filter(telegram_chat_id=str(user_id)).first()
    if not user:
        return None

    return Ticket.objects.filter(
        id=ticket_id,
        user=user
    ).select_related(
        'screening__movie', 'screening__hall', 'seat'
    ).first()


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню с кнопками"""
    user = update.effective_user

    # Создаем клавиатуру с кнопками
    keyboard = [
        [KeyboardButton("🎫 Мои билеты")],
        [KeyboardButton("👤 Профиль"), KeyboardButton("ℹ️ Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = f"""
Привет, {user.first_name}! 👋

Добро пожаловать в Кинотеатр Премьера!

Выберите действие:
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def show_tickets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список билетов пользователя"""
    user = update.effective_user

    try:
        tickets = await get_user_tickets(user.id)

        if not tickets:
            await update.message.reply_text(
                "🎫 У вас пока нет купленных билетов.\n\n"
                "Перейдите на сайт, чтобы купить билеты на сеансы."
            )
            return

        # Группируем билеты по group_id
        from collections import defaultdict
        ticket_groups = defaultdict(list)

        for ticket in tickets:
            group_id = ticket.group_id if ticket.group_id else f"single_{ticket.id}"
            ticket_groups[group_id].append(ticket)

        # Создаем инлайн-кнопки для каждой группы билетов
        keyboard = []
        for group_id, tickets_list in list(ticket_groups.items())[:10]:  # Ограничиваем 10 группами
            first_ticket = tickets_list[0]
            local_time = timezone.localtime(first_ticket.screening.start_time)

            # Формируем текст для кнопки
            button_text = f"🎬 {first_ticket.screening.movie.title} - {local_time.strftime('%d.%m %H:%M')}"

            # Создаем callback data
            callback_data = f"download_group:{group_id}"

            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        response = "🎫 <b>Ваши билеты:</b>\n\n"
        response += "Выберите билет для скачивания:\n\n"

        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error showing tickets list: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка билетов.")


async def handle_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на инлайн-кнопки билетов"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "back_to_main":
        await show_main_menu_from_callback(query)

    elif callback_data.startswith("download_group:"):
        group_id = callback_data.split(":")[1]
        await download_ticket_group(query, group_id)


async def show_main_menu_from_callback(query):
    """Показать главное меню из callback"""
    keyboard = [
        [KeyboardButton("🎫 Мои билеты")],
        [KeyboardButton("👤 Профиль"), KeyboardButton("ℹ️ Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await query.edit_message_text(
        "Главное меню:",
        reply_markup=None
    )
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def download_ticket_group(query, group_id):
    """Скачать группу билетов"""
    try:
        user = query.from_user

        if group_id.startswith("single_"):
            ticket_id = group_id.replace("single_", "")
            ticket = await get_ticket_by_id(ticket_id, user.id)
            if ticket:
                tickets = [ticket]
            else:
                await query.edit_message_text("❌ Билет не найден.")
                return
        else:
            # Получаем все билеты группы
            @sync_to_async
            def get_group_tickets(group_id, user_id):
                user = User.objects.filter(telegram_chat_id=str(user_id)).first()
                if not user:
                    return []
                return list(Ticket.objects.filter(group_id=group_id, user=user))

            tickets = await get_group_tickets(group_id, user.id)

        if not tickets:
            await query.edit_message_text("❌ Билеты не найдены.")
            return

        # Генерируем и отправляем PDF - используем локальный импорт чтобы избежать циклической зависимости
        from io import BytesIO
        from ticket.utils import generate_ticket_pdf

        @sync_to_async
        def generate_pdf_async(tickets):
            return generate_ticket_pdf(tickets)

        pdf_buffer = await generate_pdf_async(tickets)

        # Создаем файл в памяти
        pdf_file = BytesIO(pdf_buffer.getvalue())

        # Формируем имя файла
        first_ticket = tickets[0]
        local_time = timezone.localtime(first_ticket.screening.start_time)
        filename = f"билет_{first_ticket.screening.movie.title}_{local_time.strftime('%d.%m.%Y_%H-%M')}.pdf"
        pdf_file.name = filename

        # Формируем подпись
        seats_info = ", ".join([f"Ряд {t.seat.row}-{t.seat.number}" for t in tickets])
        caption = (
            f"🎫 <b>{first_ticket.screening.movie.title}</b>\n"
            f"📅 {local_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"🏠 {first_ticket.screening.hall.name}\n"
            f"💺 {seats_info}\n"
            f"👤 {first_ticket.user.name} {first_ticket.user.surname}"
        )

        # Отправляем файл
        await query.message.reply_document(
            document=pdf_file,
            filename=filename,
            caption=caption,
            parse_mode='HTML'
        )

        # Показываем сообщение об успехе
        success_text = f"""
✅ <b>Билет успешно скачан!</b>

🎬 <b>{first_ticket.screening.movie.title}</b>
📅 {local_time.strftime('%d.%m.%Y %H:%M')}
🎭 Зал: {first_ticket.screening.hall.name}
🎫 Билетов: {len(tickets)}

Приятного просмотра! 🍿
"""
        await query.message.reply_text(success_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error downloading ticket group: {e}")
        await query.edit_message_text("❌ Ошибка при скачивании билета.")


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик профиля"""
    user = update.effective_user

    try:
        @sync_to_async
        def get_user_profile(user_id):
            user_obj = User.objects.filter(telegram_chat_id=str(user_id)).first()
            if not user_obj:
                return None

            # Статистика билетов
            total_tickets = Ticket.objects.filter(user=user_obj).count()
            upcoming_tickets = Ticket.objects.filter(
                user=user_obj,
                screening__start_time__gt=timezone.now()
            ).count()
            past_tickets = total_tickets - upcoming_tickets

            return user_obj, total_tickets, upcoming_tickets, past_tickets

        result = await get_user_profile(user.id)
        if not result:
            await update.message.reply_text("❌ Ваш аккаунт не привязан.")
            return

        db_user, total_tickets, upcoming_tickets, past_tickets = result

        profile_text = f"""
👤 <b>Ваш профиль</b>

📧 <b>Email:</b> {db_user.email}
👤 <b>Имя:</b> {db_user.name} {db_user.surname}
📞 <b>Телефон:</b> {db_user.number}

🎫 <b>Статистика билетов:</b>
• Всего билетов: {total_tickets}
• Предстоящих сеансов: {upcoming_tickets}
• Прошедших сеансов: {past_tickets}

✅ <b>Telegram:</b> Привязан
"""
        await update.message.reply_text(profile_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in profile handler: {e}")
        await update.message.reply_text("❌ Ошибка при получении профиля.")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик помощи"""
    help_text = """
📋 <b>Доступные команды:</b>

<b>Основные кнопки:</b>
🎫 Мои билеты - Просмотр и скачивание билетов
👤 Профиль - Информация о вашем профиле
ℹ️ Помощь - Это сообщение

<b>Как скачать билеты:</b>
1. Нажмите "🎫 Мои билеты"
2. Выберите нужный сеанс из списка
3. Билет автоматически скачается в PDF формате

<b>Текстовые команды:</b>
/start - Главное меню
/profile - Информация о профиле

📞 <b>Поддержка:</b>
По вопросам работы бота обращайтесь в техническую поддержку.
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    text = update.message.text

    # Сначала проверяем, привязан ли пользователь
    user_verified = await check_user_verified(update.effective_user.id)

    if not user_verified:
        # Если пользователь не привязан, передаем обработку verification_handler
        from .verification import verification_handler
        await verification_handler(update, context)
        return

    # Обработка кнопок для привязанных пользователей
    if text == "🎫 Мои билеты":
        await show_tickets_list(update, context)

    elif text == "👤 Профиль":
        await profile_handler(update, context)

    elif text == "ℹ️ Помощь":
        await help_handler(update, context)

    else:
        # Если это не кнопка и пользователь привязан, показываем меню
        await show_main_menu(update, context)