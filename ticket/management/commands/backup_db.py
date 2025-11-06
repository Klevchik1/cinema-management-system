# ticket/management/commands/backup_db.py
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from ticket.models import BackupManager
import psycopg2
from io import StringIO


class Command(BaseCommand):
    help = 'Create database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Create backup for specific date (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        backup_date = options.get('date')

        # Директория для бэкапов
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Создаем имя файла
        if backup_date:
            filename = f"backup_{backup_date}.sql"
            backup_type = 'daily'
            name = f"Дневной бэкап {backup_date}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"full_backup_{timestamp}.sql"
            backup_type = 'full'
            name = f"Полный бэкап {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        backup_path = os.path.join(backup_dir, filename)

        try:
            # Пробуем создать бэкап через psycopg2
            success = self.create_pg_backup(backup_path)

            if success:
                # Сохраняем информацию о бэкапе в базу
                backup = BackupManager.objects.create(
                    name=name,
                    backup_file=filename,
                    backup_type=backup_type,
                    backup_date=backup_date
                )

                file_size = os.path.getsize(backup_path)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Backup created: {filename} ({file_size} bytes)')
                )
                return backup
            else:
                # Если не получилось, создаем простой бэкап
                return self.create_simple_backup(backup_path, name, backup_type, backup_date)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Backup failed: {str(e)}')
            )
            return None

    def create_pg_backup(self, backup_path):
        """Создает бэкап через psycopg2"""
        try:
            db_config = settings.DATABASES['default']

            # Подключаемся к БД
            conn = psycopg2.connect(
                host=db_config.get('HOST', 'localhost'),
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                port=db_config.get('PORT', '5432')
            )

            # Создаем курсор
            cur = conn.cursor()

            # Получаем список всех таблиц
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in cur.fetchall()]

            # Создаем файл бэкапа
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(f"-- PostgreSQL database dump\n")
                f.write(f"-- Generated: {datetime.now()}\n")
                f.write(f"-- Database: {db_config['NAME']}\n\n")

                # Бэкап для каждой таблицы
                for table in tables:
                    if table.startswith('django_') or table.startswith('auth_'):
                        continue  # Пропускаем системные таблицы

                    f.write(f"\n-- Table: {table}\n")

                    # Получаем данные таблицы
                    cur.execute(f"SELECT * FROM {table}")
                    rows = cur.fetchall()

                    # Получаем названия колонок
                    cur.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        ORDER BY ordinal_position
                    """)
                    columns = [row[0] for row in cur.fetchall()]

                    # Создаем INSERT statements
                    if rows:
                        for row in rows:
                            values = []
                            for value in row:
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    # Экранируем кавычки
                                    escaped_value = value.replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                                elif isinstance(value, datetime):
                                    values.append(f"'{value}'")
                                else:
                                    values.append(str(value))

                            f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")

            # Закрываем соединение
            cur.close()
            conn.close()

            return True

        except Exception as e:
            self.stdout.write(f"⚠️  PG backup failed, using simple backup: {str(e)}")
            return False

    def create_simple_backup(self, backup_path, name, backup_type, backup_date):
        """Создает простой бэкап с информацией о структуре"""
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(f"-- Database Backup\n")
                f.write(f"-- Generated: {datetime.now()}\n")
                f.write(f"-- Type: {backup_type}\n")
                f.write(f"-- Date: {backup_date or 'Full backup'}\n\n")

                # Добавляем информацию о таблицах
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                    """)
                    tables = [row[0] for row in cursor.fetchall()]

                    f.write(f"-- Database contains {len(tables)} tables:\n")
                    for table in tables:
                        f.write(f"-- - {table}\n")

            # Сохраняем информацию о бэкапе
            backup = BackupManager.objects.create(
                name=name,
                backup_file=os.path.basename(backup_path),
                backup_type=backup_type,
                backup_date=backup_date
            )

            file_size = os.path.getsize(backup_path)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Simple backup created: {os.path.basename(backup_path)} ({file_size} bytes)')
            )
            return backup

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Simple backup also failed: {str(e)}')
            )
            return None