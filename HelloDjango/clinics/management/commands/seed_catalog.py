"""
Сидер каталога «ПроДокторов вет»: клиники, врачи, специализации, услуги, отзывы.

Запуск:
    python manage.py seed_catalog
    python manage.py seed_catalog --reset   # сначала очистить
"""
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from clinics.models import Clinic, Specialization, VetProfile
from services.models import Service
from reviews.models import Review

User = get_user_model()


SPECIALIZATIONS = [
    ('Терапевт',       '🩺', 'Общий приём, диагностика'),
    ('Хирург',         '🔪', 'Операции и хирургические вмешательства'),
    ('Кардиолог',      '❤️', 'Болезни сердца и сосудов'),
    ('Дерматолог',     '🧴', 'Кожа, шерсть, аллергии'),
    ('Стоматолог',     '🦷', 'Зубы и полость рта'),
    ('Офтальмолог',    '👁', 'Глазные болезни'),
    ('Невролог',       '🧠', 'Неврологические заболевания'),
    ('Эндокринолог',   '🧬', 'Гормональные нарушения'),
    ('Онколог',        '🎗', 'Диагностика и лечение опухолей'),
    ('Репродуктолог',  '🐣', 'Беременность, роды, разведение'),
    ('Грумер-вет',     '✂️', 'Чистка ушей, стрижка когтей'),
    ('Экзотика',       '🦎', 'Рептилии, грызуны, птицы'),
]

CITIES = ['Краснодар', 'Москва', 'Санкт-Петербург', 'Екатеринбург', 'Новосибирск', 'Ростов-на-Дону']

CLINIC_NAMES = [
    ('Зоодоктор Плюс',       'Краснодар',        'ул. Красная, 145',                '+7 (861) 200-15-15'),
    ('Айболит-Центр',        'Краснодар',        'ул. Тургенева, 81',                '+7 (861) 211-22-33'),
    ('ВетКомфорт',           'Москва',           'Ленинский пр., 158',                '+7 (495) 555-10-10'),
    ('Доктор Зоо',           'Москва',           'ул. Мясницкая, 24',                 '+7 (495) 700-44-99'),
    ('Питерская Лапа',       'Санкт-Петербург',  'Невский пр., 88',                  '+7 (812) 333-77-77'),
    ('Хвостатый Друг',       'Санкт-Петербург',  'Лиговский пр., 50',                '+7 (812) 444-12-12'),
    ('Уральский Вет',        'Екатеринбург',     'ул. Малышева, 51',                  '+7 (343) 222-33-44'),
    ('Сибирская Клиника',    'Новосибирск',      'Красный пр., 27',                  '+7 (383) 100-25-25'),
    ('Зооветсервис Дон',     'Ростов-на-Дону',   'ул. Большая Садовая, 110',          '+7 (863) 220-15-15'),
    ('ВетЛайн 24',           'Краснодар',        'ул. Северная, 326',                 '+7 (861) 299-99-00'),
    ('Биосфера-Вет',         'Москва',           'Кутузовский пр., 36',               '+7 (495) 660-80-80'),
    ('Лучший Друг',          'Санкт-Петербург',  'Московский пр., 195',               '+7 (812) 700-15-15'),
]

VET_NAMES = [
    ('Анна',     'Соколова',    'female'),
    ('Дмитрий',  'Петров',      'male'),
    ('Ольга',    'Кравцова',    'female'),
    ('Сергей',   'Иванов',      'male'),
    ('Мария',    'Васильева',   'female'),
    ('Алексей',  'Морозов',     'male'),
    ('Екатерина','Смирнова',    'female'),
    ('Игорь',    'Романов',     'male'),
    ('Татьяна',  'Лебедева',    'female'),
    ('Виктор',   'Орлов',       'male'),
    ('Юлия',     'Новикова',    'female'),
    ('Андрей',   'Зайцев',      'male'),
    ('Ирина',    'Богданова',   'female'),
    ('Максим',   'Антонов',     'male'),
    ('Наталья',  'Громова',     'female'),
    ('Павел',    'Седов',       'male'),
    ('Елена',    'Калинина',    'female'),
    ('Роман',    'Тихонов',     'male'),
    ('Светлана', 'Карпова',     'female'),
    ('Алексей',  'Чернов',      'male'),
    ('Анастасия','Беляева',     'female'),
    ('Михаил',   'Гордеев',     'male'),
    ('Дарья',    'Ефимова',     'female'),
    ('Владимир', 'Жуков',       'male'),
]

SERVICES = [
    ('Первичный приём',                   1200),
    ('Повторный приём',                   800),
    ('Вакцинация',                        1500),
    ('Чипирование',                       1800),
    ('УЗИ брюшной полости',               2500),
    ('Рентген одной проекции',            1800),
    ('Кастрация кота',                    3500),
    ('Стерилизация кошки',                5500),
    ('Стерилизация суки (до 10 кг)',      7000),
    ('Чистка зубов под наркозом',         4500),
    ('Общий анализ крови',                950),
    ('Биохимический анализ крови',        2200),
    ('Анализ мочи',                       700),
    ('Капельница (1 час)',                900),
    ('Снятие швов',                       500),
    ('Онлайн-консультация',               700),
    ('Выезд на дом',                      1500),
]

EDUCATION_TEMPLATES = [
    'Московская государственная академия ветеринарной медицины и биотехнологии (МГАВМиБ), 20{y}',
    'СПбГАВМ — Санкт-Петербургский государственный университет ветеринарной медицины, 20{y}',
    'Кубанский государственный аграрный университет, факультет ветеринарной медицины, 20{y}',
    'Казанская государственная академия ветеринарной медицины им. Н.Э. Баумана, 20{y}',
]
BIO_TEMPLATES = [
    'Принимаю собак, кошек и грызунов. Особый интерес — профилактика и работа с возрастными животными.',
    'Помогаю владельцам разобраться в анализах и подобрать схему лечения. Без давления, спокойно и подробно.',
    'Веду пациентов с хроническими заболеваниями. Часто работаю в команде с узкими специалистами.',
    'Люблю свою работу — это не просто слова. Каждому хвостатому пациенту нужно время, и я его даю.',
    'Стажировки в Германии и Чехии. Регулярно обучаюсь на международных конференциях.',
]

REVIEW_TEXTS = [
    ('Очень внимательный врач. Объяснил всё про вакцинацию по полочкам.', 5,
     'внимательный, не торопит', ''),
    ('Спасибо доктору, кошку поставили на ноги. Запишусь ещё.', 5,
     'результат, забота', ''),
    ('В целом всё нормально, но пришлось долго ждать в очереди.', 4,
     'врач хороший', 'долгое ожидание'),
    ('Приём прошёл быстро, питомец не нервничал. Рекомендую!', 5,
     'спокойный приём', ''),
    ('Не понравилось обращение администратора, врач — отдельный плюс.', 3,
     'врач', 'администратор'),
    ('Делали стерилизацию — всё прошло хорошо, после операции связывались с нами.', 5,
     'звонок после операции', ''),
    ('Цены чуть выше среднего, но качество соответствует.', 4,
     'качество', 'цена'),
    ('Срочно понадобилась помощь ночью — приняли и помогли. Спасибо!', 5,
     'круглосуточно', ''),
    ('Назначили лечение, но улучшений не было — пришлось ехать в другую клинику.', 2,
     '', 'не помогло'),
    ('Замечательно объяснили, как ухаживать после операции. Питомец быстро восстановился.', 5,
     'подробные рекомендации', ''),
]


def _username(first, last, idx):
    base = slugify(f'{first}-{last}', allow_unicode=False) or f'vet{idx}'
    if not base or base == '-':
        base = f'vet{idx}'
    return f'{base}{idx}'


class Command(BaseCommand):
    help = 'Сидит каталог: специализации, клиники, врачей, услуги, отзывы.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Сбросить существующие данные сидинга')
        parser.add_argument('--seed', type=int, default=42, help='Random seed')

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(opts['seed'])

        if opts['reset']:
            self.stdout.write('Сброс…')
            Review.objects.all().delete()
            VetProfile.objects.all().delete()
            Service.objects.all().delete()
            Clinic.objects.all().delete()
            Specialization.objects.all().delete()
            User.objects.filter(user_type='vet', username__startswith='vet').delete()
            User.objects.filter(username__startswith='owner_demo').delete()

        # 1. Специализации
        specs = []
        for name, icon, desc in SPECIALIZATIONS:
            obj, _ = Specialization.objects.get_or_create(
                slug=slugify(name, allow_unicode=False),
                defaults={'name': name, 'icon': icon, 'description': desc},
            )
            specs.append(obj)
        self.stdout.write(self.style.SUCCESS(f'  специализаций: {len(specs)}'))

        # 2. Клиники
        clinics = []
        for idx, (name, city, address, phone) in enumerate(CLINIC_NAMES, start=1):
            clinic, _ = Clinic.objects.get_or_create(
                name=name,
                defaults={
                    'city': city,
                    'address': address,
                    'phone': phone,
                    'email': f'info{idx:02d}@vetclinic-demo.ru',
                    'working_hours': random.choice([
                        'Пн-Пт 9:00-20:00, Сб-Вс 10:00-18:00',
                        'Ежедневно 9:00-21:00',
                        'Круглосуточно',
                    ]),
                    'description': 'Команда опытных ветеринаров. Современное оборудование, собственная лаборатория.',
                    'is_24h': random.random() < 0.25,
                    'accepts_online': random.random() < 0.7,
                    'has_lab': random.random() < 0.6,
                    'has_surgery': random.random() < 0.8,
                },
            )
            clinics.append(clinic)
        self.stdout.write(self.style.SUCCESS(f'  клиник: {len(clinics)}'))

        # 3. Услуги для каждой клиники
        n_services = 0
        for clinic in clinics:
            for sname, base_price in SERVICES:
                price = Decimal(int(base_price * random.uniform(0.85, 1.25) // 50 * 50))
                Service.objects.get_or_create(
                    clinic=clinic,
                    name=sname,
                    defaults={'price': price, 'description': ''},
                )
                n_services += 1
        self.stdout.write(self.style.SUCCESS(f'  услуг: {n_services}'))

        # 4. Врачи
        vets = []
        for i, (first, last, _gender) in enumerate(VET_NAMES, start=1):
            username = _username(first, last, i)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'user_type': 'vet',
                    'email': f'{username}@demo-vet.ru',
                },
            )
            if created:
                user.set_password('demo12345')
                user.save()

            clinic = random.choice(clinics)
            vet, _ = VetProfile.objects.get_or_create(
                user=user,
                defaults={
                    'clinic': clinic,
                    'experience_years': random.randint(2, 28),
                    'price_consultation': Decimal(random.choice([900, 1100, 1300, 1500, 1800, 2200, 2800])),
                    'accepts_online': random.random() < 0.6,
                    'accepts_house_call': random.random() < 0.4,
                    'education': random.choice(EDUCATION_TEMPLATES).format(y=random.randint(5, 19)),
                    'bio': random.choice(BIO_TEMPLATES),
                },
            )
            # Специализации — 1-3 шт.
            picked = random.sample(specs, k=random.randint(1, 3))
            vet.specializations.set(picked)
            vets.append(vet)
            clinic.admins.add(user)
        self.stdout.write(self.style.SUCCESS(f'  врачей: {len(vets)}'))

        # 5. Демо-владельцы для отзывов
        owners = []
        for i in range(1, 16):
            u, created = User.objects.get_or_create(
                username=f'owner_demo_{i}',
                defaults={
                    'first_name': random.choice(['Илья', 'Ксения', 'Артём', 'Полина', 'Денис', 'Алиса']),
                    'last_name':  random.choice(['К.', 'Л.', 'М.', 'Н.', 'П.', 'С.']),
                    'user_type': 'owner',
                    'email': f'owner{i}@demo.ru',
                },
            )
            if created:
                u.set_password('demo12345')
                u.save()
            owners.append(u)

        # 6. Отзывы — рандомно на клиники и врачей
        n_reviews = 0
        created_ids = []
        for clinic in clinics:
            for _ in range(random.randint(3, 12)):
                text, rating, pros, cons = random.choice(REVIEW_TEXTS)
                r = Review.objects.create(
                    clinic=clinic,
                    author=random.choice(owners),
                    rating=rating,
                    text=text,
                    pros=pros,
                    cons=cons,
                )
                created_ids.append((r.pk, random.randint(1, 365)))
                n_reviews += 1
        for vet in vets:
            for _ in range(random.randint(0, 8)):
                text, rating, pros, cons = random.choice(REVIEW_TEXTS)
                r = Review.objects.create(
                    vet=vet,
                    author=random.choice(owners),
                    rating=rating,
                    text=text,
                    pros=pros,
                    cons=cons,
                )
                created_ids.append((r.pk, random.randint(1, 365)))
                n_reviews += 1

        # Перебиваем created_at (auto_now_add игнорирует значение из create).
        now = timezone.now()
        for pk, days_ago in created_ids:
            Review.objects.filter(pk=pk).update(
                created_at=now - timezone.timedelta(days=days_ago)
            )
        self.stdout.write(self.style.SUCCESS(f'  отзывов: {n_reviews}'))

        # Создаём суперпользователя, если ещё нет
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                password='admin',
                email='admin@example.com',
                user_type='clinic_admin',
            )
            self.stdout.write(self.style.WARNING('  создан суперпользователь admin/admin'))

        self.stdout.write(self.style.SUCCESS('\nГотово. Запустите: python manage.py runserver'))
