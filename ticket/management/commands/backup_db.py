import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from ticket.models import BackupManager


class Command(BaseCommand):
    help = 'Create database backup using pg_dump'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Create backup for specific date (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        backup_date = options.get('date')

        # Конфигурация БД
        db_config = settings.DATABASES['default']

        # Директория для бэкапов
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Создаем имя файла
        if backup_date:
            filename = f"backup_{backup_date}.sql"
            self.stdout.write(f"Creating backup for date: {backup_date}")
            backup_type = 'daily'
            name = f"Daily Backup {backup_date}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"full_backup_{timestamp}.sql"
            self.stdout.write("Creating full backup")
            backup_type = 'full'
            name = f"Full Backup {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        backup_path = os.path.join(backup_dir, filename)

        try:
            # Команда pg_dump
            cmd = [
                'pg_dump',
                '-h', db_config.get('HOST', 'localhost'),
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-f', backup_path
            ]

            # Устанавливаем пароль
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']

            # Выполняем команду
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                # Сохраняем информацию о бэкапе в базу
                backup = BackupManager.objects.create(
                    name=name,
                    backup_file=filename,
                    backup_type=backup_type,
                    backup_date=backup_date
                )

                file_size = os.path.getsize(backup_path)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Backup created: {filename} ({file_size} bytes)'
                    )
                )
                return backup
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Backup failed: {result.stderr}')
                )
                return None

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Exception: {str(e)}')
            )
            return None