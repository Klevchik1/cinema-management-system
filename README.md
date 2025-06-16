# 🎬 Cinema Management System

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

Полнофункциональная система управления кинотеатром с онлайн-бронированием билетов, разработанная на Django.

## ✨ Особенности

- 🎥 Управление фильмами, залами и сеансами
- 💻 Онлайн-бронирование мест с выбором на схеме зала
- 🎫 Генерация PDF-билетов с QR-кодами
- 👤 Личный кабинет пользователя с историей покупок
- 🔒 Административная панель для управления контентом
- ⚙️ Система проверки пересечений сеансов

## 🚀 Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Klevchik1/cinema-management-system.git
cd cinema-management-system
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте базу данных в `cinematic/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cinema_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. Примените миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Загрузите тестовые данные:
```bash
python manage.py populate_db
```

7. Запустите сервер:
```bash
python manage.py runserver
```

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/your-feature`)
3. Сделайте коммит изменений (`git commit -am 'Add some feature'`)
4. Запушьте ветку (`git push origin feature/your-feature`)
5. Создайте Pull Request
