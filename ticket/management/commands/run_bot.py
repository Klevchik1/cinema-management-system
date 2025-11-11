from django.core.management.base import BaseCommand
from ticket.telegram_bot.bot import start_bot


class Command(BaseCommand):
    help = 'Run Telegram bot in polling mode'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Telegram bot...')
        )

        # Просто вызываем синхронную функцию
        start_bot()