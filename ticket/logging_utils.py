import logging
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .models import OperationLog

logger = logging.getLogger(__name__)


class OperationLogger:
    """Утилита для логирования операций в системе"""

    @staticmethod
    def log_operation(request, action_type, module_type, description, object_id=None, object_repr=None,
                      additional_data=None):
        """
        Логирование операции

        Args:
            request: HttpRequest объект
            action_type: тип действия (CREATE, UPDATE, DELETE, etc.)
            module_type: модуль системы (USERS, MOVIES, etc.)
            description: описание операции
            object_id: ID объекта (опционально)
            object_repr: строковое представление объекта (опционально)
            additional_data: дополнительные данные в виде словаря (опционально)
        """
        try:
            # Получаем информацию о пользователе
            user = None
            ip_address = None
            user_agent = None

            if request and hasattr(request, 'user'):
                if not isinstance(request.user, AnonymousUser):
                    user = request.user

                # Получаем IP адрес
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')

                # Получаем User Agent
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Ограничиваем длину

            # Создаем запись лога
            log_entry = OperationLog(
                user=user,
                action_type=action_type,
                module_type=module_type,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                object_id=object_id,
                object_repr=object_repr,
                additional_data=additional_data,
                timestamp=timezone.now()
            )
            log_entry.save()

            # Также пишем в системный лог
            logger.info(f"Operation logged: {action_type} - {module_type} - {description}")

            return log_entry

        except Exception as e:
            logger.error(f"Error logging operation: {str(e)}")
            return None

    @staticmethod
    def log_model_operation(request, action_type, instance, description=None, additional_data=None):
        """
        Логирование операций с моделями

        Args:
            request: HttpRequest объект
            action_type: тип действия
            instance: экземпляр модели
            description: описание (если None - генерируется автоматически)
            additional_data: дополнительные данные
        """
        if description is None:
            model_name = instance._meta.verbose_name
            description = f"{action_type} {model_name}"

        object_repr = str(instance)

        # Определяем тип модуля
        module_type = instance._meta.model_name.upper()

        # Специальная обработка для некоторых моделей
        module_map = {
            'SCREENING': 'SCREENINGS',
            'TICKET': 'TICKETS',
            'MOVIE': 'MOVIES',
            'USER': 'USERS',
            'HALL': 'HALLS',
            'GENRE': 'MOVIES',
            'AGERATING': 'MOVIES',
            'SEAT': 'HALLS',
            'TICKETSTATUS': 'TICKETS',
            'BACKUPMANAGER': 'BACKUPS',
            'OPERATIONLOG': 'SYSTEM',
            'PENDINGREGISTRATION': 'AUTH',
            'PASSWORDRESETREQUEST': 'AUTH',
            'EMAILCHANGEREQUEST': 'AUTH',
            'REPORT': 'REPORTS'
        }

        module_type = module_map.get(module_type, 'SYSTEM')

        return OperationLogger.log_operation(
            request=request,
            action_type=action_type,
            module_type=module_type,
            description=description,
            object_id=instance.pk,
            object_repr=object_repr,
            additional_data=additional_data
        )

    @staticmethod
    def log_report_export(request, report_type, format_type, filters=None):
        """Логирование экспорта отчетов"""
        description = f"Экспорт отчета {report_type} в формате {format_type}"

        if filters:
            description += f" с фильтрами: {filters}"

        return OperationLogger.log_operation(
            request=request,
            action_type='EXPORT',
            module_type='REPORTS',
            description=description,
            additional_data={
                'report_type': report_type,
                'format_type': format_type,
                'filters': filters
            }
        )

    @staticmethod
    def log_backup_operation(request, backup_type, description):
        """Логирование операций с бэкапами"""
        return OperationLogger.log_operation(
            request=request,
            action_type='BACKUP',
            module_type='BACKUPS',
            description=description,
            additional_data={'backup_type': backup_type}
        )

    @staticmethod
    def log_system_operation(action_type, module_type, description, object_id=None, object_repr=None,
                             additional_data=None):
        """Логирование системных операций (без request)"""
        try:
            OperationLog.objects.create(
                user=None,  # Системная операция
                action_type=action_type,
                module_type=module_type,
                description=description,
                object_id=object_id,
                object_repr=object_repr,
                additional_data=additional_data,
                timestamp=timezone.now()
            )
            logger.info(f"System operation logged: {action_type} - {module_type} - {description}")
        except Exception as e:
            logger.error(f"Error logging system operation: {e}")