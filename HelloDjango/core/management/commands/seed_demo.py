"""
Сидер реалистичных данных для EKM-PET (только владельцы, собаки и кошки).

Создаёт:
  • ~32 пользователя — все владельцы, с русскими именами, правдоподобными
    логинами и реальными провайдерами почты, регистрациями в окне 22.04.2026 — сегодня;
  • Питомцев у 14 владельцев (1–3 на хозяина), только собаки и кошки,
    с чипами у большинства;
  • Документы в личных кабинетах (PDF — реальные, по умолчанию);
  • Медицинские записи (диагнозы, прививки, процедуры, анализы);
  • Статьи в блоге (про уход за питомцами).

Запуск:
    python manage.py seed_demo                # 32 владельца, реальные PDF
    python manage.py seed_demo --users 40     # больше юзеров
    python manage.py seed_demo --no-files     # без PDF (быстрее, для теста)
"""
import io
import random
from datetime import date, datetime, timedelta, time as dt_time

from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from users.models import User
from pets.models import Pet, PetDocument
from medical_records.models import MedicalRecord
from blog.models import Article


# ── Имена / фамилии ───────────────────────────────────────────────────────────
FIRST_M = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей', 'Алексей',
           'Артём', 'Илья', 'Кирилл', 'Михаил', 'Никита', 'Иван', 'Роман',
           'Егор', 'Павел', 'Денис', 'Антон', 'Владимир', 'Тимур']
FIRST_F = ['Анна', 'Мария', 'Елена', 'Ольга', 'Наталья', 'Екатерина',
           'Ирина', 'Татьяна', 'Светлана', 'Юлия', 'Дарья', 'Виктория',
           'Полина', 'Алина', 'Ксения', 'Алиса', 'София', 'Кристина']
LAST_M = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов',
          'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Волков',
          'Соловьёв', 'Васильев', 'Зайцев', 'Павлов', 'Семёнов', 'Голубев']
LAST_F = [n + 'а' for n in LAST_M]

TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}


def translit(s: str) -> str:
    return ''.join(TRANSLIT.get(ch.lower(), ch.lower()) for ch in s if ch.isalpha())


def make_username(first: str, last: str, idx: int) -> str:
    f = translit(first)
    l = translit(last)
    patterns = [
        lambda: f'{f}.{l}',
        lambda: f'{f}_{l}',
        lambda: f'{l}.{f[:1]}',
        lambda: f'{f}{random.randint(80, 99)}',
        lambda: f'{f}_{random.randint(1990, 2003)}',
        lambda: f'{l}{random.randint(1, 99)}',
        lambda: f'{f[:1]}.{l}',
        lambda: f'{f}{l[:3]}',
    ]
    base = random.choice(patterns)()
    return base if random.random() < 0.55 else f'{base}{idx}'


def make_email(username: str) -> str:
    providers = [('mail.ru', 35), ('yandex.ru', 25), ('gmail.com', 22),
                 ('bk.ru', 8), ('list.ru', 5), ('inbox.ru', 5)]
    total = sum(w for _, w in providers)
    r = random.uniform(0, total)
    upto = 0
    for prov, w in providers:
        upto += w
        if upto >= r:
            return f'{username}@{prov}'.lower()
    return f'{username}@mail.ru'.lower()


# ── Питомцы ───────────────────────────────────────────────────────────────────
PET_NAMES = ['Барсик', 'Мурка', 'Рекс', 'Шарик', 'Жучка', 'Боня', 'Тёма',
             'Тузик', 'Симба', 'Локи', 'Маркиз', 'Ватрушка', 'Бося', 'Ричи',
             'Леопольд', 'Снежок', 'Пушок', 'Чарли', 'Беляш', 'Тоша', 'Гоша',
             'Кеша', 'Пиксель', 'Зефир', 'Космос', 'Юпитер', 'Бакс', 'Феня',
             'Лиса', 'Найда', 'Гера', 'Зося', 'Ника', 'Арчи', 'Бади']

BREEDS = {
    'dog': ['Лабрадор', 'Немецкая овчарка', 'Хаски', 'Корги', 'Такса', 'Мопс',
            'Дворняжка', 'Шпиц', 'Йорк', 'Бигль', 'Чихуахуа', 'Стаффорд',
            'Золотистый ретривер', 'Французский бульдог', 'Метис'],
    'cat': ['Британская', 'Шотландская вислоухая', 'Сфинкс', 'Мейн-кун',
            'Сибирская', 'Беспородная', 'Бенгальская', 'Метис', 'Невская маскарадная'],
}
SPECIES_WEIGHTS = [('dog', 50), ('cat', 50)]


# ── Документы / медзаписи / статьи / чаты ─────────────────────────────────────
def doc_titles():
    return {
        'vaccination': [
            ('Вакцина «Нобивак DHPPI» {year}', 'Комплексная вакцинация (чума, гепатит, парвовирус, парагрипп). Серия №{ser}.'),
            ('Прививка от бешенства {year}', 'Ежегодная вакцинация по графику. Серия №RB-{ser}.'),
            ('Сертификат о вакцинации', 'Международный ветеринарный паспорт, отметка о ревакцинации.'),
            ('Вакцина «Мультифел-4»', 'Кошачья комплексная вакцина: ринотрахеит, кальцивироз, панлейкопения, хламидиоз.'),
            ('Дегельминтизация', 'Профилактическая обработка препаратом «Мильбемакс».'),
        ],
        'analysis': [
            ('Общий анализ крови от {date}', 'Все показатели в пределах референса. Гематологический анализатор Mindray.'),
            ('Биохимия крови от {date}', 'АЛТ, АСТ, креатинин, мочевина, глюкоза. Заключение: норма.'),
            ('Общий анализ мочи', 'Цвет — соломенно-жёлтый, прозрачность — полная, плотность 1.025.'),
            ('УЗИ брюшной полости', 'Без структурных изменений. Заключение врача УЗД.'),
            ('Соскоб с кожи', 'Цитологическое исследование. Грибковая флора не обнаружена.'),
        ],
        'surgery': [
            ('Кастрация', 'Плановая операция. Послеоперационный период без осложнений.'),
            ('Стерилизация (ОГЭ)', 'Овариогистерэктомия. Швы сняты на 10-й день.'),
            ('Удаление новообразования', 'Гистология: доброкачественная опухоль.'),
        ],
        'prescription': [
            ('Назначение «Синулокс 250» 7 дней', 'Антибиотик, по 1 таб. 2 раза в день.'),
            ('«Ципровет» глазные капли', 'По 1–2 капли в каждый глаз 3 раза в день, 7 дней.'),
            ('Витаминный курс «Канвит»', 'Поддерживающая терапия, 30 дней.'),
            ('«Метронидазол» 10 дней', 'По схеме, рассчитано по весу.'),
        ],
        'certificate': [
            ('Справка для перевозки (форма №1)', 'Ветеринарная справка о клиническом здоровье и вакцинациях.'),
            ('Заключение по результатам осмотра', 'Состояние удовлетворительное, противопоказаний нет.'),
            ('Свидетельство о здоровье', 'Для участия в выставке.'),
        ],
        'other': [
            ('Чек ветаптеки', 'Покупка корма и витаминов.'),
            ('Фото жетона с QR', 'Идентификационный жетон на ошейнике.'),
            ('Договор с клиникой', 'Договор на оказание ветеринарных услуг.'),
        ],
    }


RECORD_TEMPLATES = {
    'vaccination': ['Плановая вакцинация', 'Ревакцинация', 'Вакцинация от бешенства'],
    'diagnosis': ['Гастрит', 'Отит наружный', 'Атопический дерматит', 'Аллергическая реакция',
                  'Цистит', 'Конъюнктивит', 'Пиодермия'],
    'procedure': ['Чистка ушей', 'Стрижка когтей', 'Обработка от паразитов', 'Чистка зубов'],
    'lab_test': ['Общий анализ крови', 'Биохимия крови', 'Общий анализ мочи',
                 'Соскоб с кожи', 'Цитология'],
    'medication': ['Курс антибиотиков', 'Противовоспалительная терапия', 'Антигистаминные'],
    'note': ['Контрольный осмотр', 'Рекомендации по питанию', 'Профилактический визит'],
    'surgery': ['Стерилизация', 'Удаление зуба', 'Удаление образования'],
}

ARTICLES = [
    {
        'title': 'Как подготовить котёнка к первой вакцинации',
        'content': (
            'Первая вакцинация — важный этап в жизни котёнка. Обычно её проводят в возрасте 8–9 недель. '
            'За 10 дней до прививки необходимо провести дегельминтизацию: дать препарат от глистов в '
            'дозировке, рассчитанной по весу.\n\n'
            'В день вакцинации убедитесь, что котёнок здоров: нет насморка, диареи, температуры. '
            'После прививки в течение 14 дней избегайте переохлаждения, купания и активных контактов '
            'с другими животными — иммунитет ещё формируется.\n\n'
            'Стандартная схема: первая вакцина в 8–9 недель, ревакцинация через 3–4 недели, '
            'затем добавляется прививка от бешенства. Все отметки должны быть в международном '
            'ветеринарном паспорте.'
        ),
    },
    {
        'title': '5 признаков того, что собаке пора к ветеринару',
        'content': (
            'Собаки терпеливы и часто скрывают недомогание. Внимательный хозяин заметит изменения '
            'раньше, чем разовьётся серьёзное заболевание.\n\n'
            '1. Изменение аппетита — отказ от еды более суток или внезапная жадность.\n'
            '2. Изменение поведения — апатия, агрессия без причины, поиск укромных мест.\n'
            '3. Проблемы со стулом — диарея, запор, кровь в кале более 24 часов.\n'
            '4. Хромота, скованность движений, особенно после сна.\n'
            '5. Изменения кожи и шерсти — зуд, покраснения, выпадение шерсти, запах.\n\n'
            'Любой из этих симптомов — повод записаться к врачу. Лучше перестраховаться и '
            'получить «всё в порядке», чем упустить начало болезни.'
        ),
    },
    {
        'title': 'Чипирование питомца: зачем и как это делается',
        'content': (
            'Микрочип — это крошечный электронный носитель размером с рисовое зёрнышко. Он '
            'вживляется под кожу в области холки и хранит уникальный 15-значный номер по стандарту '
            'ISO 11784/11785.\n\n'
            'Зачем нужен чип:\n— Идентификация питомца на всю жизнь, не теряется как ошейник.\n'
            '— Обязательное условие для перевозки за границу.\n'
            '— Повышает шансы найти животное при потере: волонтёры и клиники сканируют чипы.\n\n'
            'Процедура занимает 1 минуту, переносится легко. Номер заносится в международную базу. '
            'В EKM-PET к карточке питомца можно прикрепить QR-код — отдельную защиту от потери.'
        ),
    },
    {
        'title': 'Как часто нужно показывать кошку ветеринару',
        'content': (
            'Здоровая кошка любого возраста должна посещать врача минимум раз в год — '
            'для профилактического осмотра и плановой вакцинации.\n\n'
            'Котята до года — каждые 3 месяца: вакцинации, дегельминтизация, контроль развития.\n'
            'Взрослые (1–7 лет) — раз в год.\n'
            'Пожилые (старше 7 лет) — раз в 6 месяцев, с биохимией крови и УЗИ.\n\n'
            'Внеплановые визиты обязательны при любых изменениях поведения, аппетита и стула. '
            'Раннее обнаружение болезни почек или щитовидной железы у пожилых кошек существенно '
            'продлевает жизнь.'
        ),
    },
    {
        'title': 'Электронная медкарта: что хранить и как организовать',
        'content': (
            'Бумажные ветеринарные карты теряются, выцветают, остаются в одной клинике. '
            'Электронная медкарта решает эти проблемы — все документы доступны с любого устройства.\n\n'
            'Что обязательно хранить:\n'
            '— Сертификаты вакцинаций и отметки о ревакцинации.\n'
            '— Результаты анализов (кровь, моча, УЗИ).\n'
            '— Назначения и рецепты.\n'
            '— Справки и заключения хирурга после операций.\n'
            '— Фото жетонов и чипов.\n\n'
            'В EKM-PET документы группируются по категориям, привязываются к конкретному питомцу '
            'и доступны ветеринару с разрешения владельца.'
        ),
    },
    {
        'title': 'Что положить в аптечку для собаки',
        'content': (
            'Минимальный набор средств первой помощи для собаки помещается в обычную косметичку. '
            'Главное — не доставать его раз в год, а регулярно проверять сроки годности.\n\n'
            'Антисептики: хлоргексидин, мирамистин (без спирта).\n'
            'Перевязочные: стерильные бинты, ватные диски, эластичный бинт.\n'
            'Сорбенты: «Энтеросгель» или активированный уголь — при отравлениях.\n'
            'От аллергии: «Супрастин» (дозировка по весу, уточнить у врача).\n'
            'Термометр электронный — нормальная температура у собак 37,5–39 °C.\n\n'
            'Не давайте без консультации: жаропонижающие для людей, антибиотики, обезболивающие. '
            'Многие из них токсичны для собак.'
        ),
    },
]

# ── Утилиты ──────────────────────────────────────────────────────────────────
def fake_pdf_bytes(title: str, body: str) -> bytes:
    """Минимальный валидный PDF без сторонних зависимостей."""
    safe = lambda s: s.encode('latin-1', 'replace').decode('latin-1')
    text = f"BT /F1 14 Tf 50 770 Td ({safe(title)}) Tj 0 -22 Td /F1 10 Tf ({safe(body[:80])}) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        ("<< /Length " + str(len(text)) + " >>\nstream\n" + text + "\nendstream").encode('latin-1'),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode())
    return out.getvalue()


def weighted_choice(items):
    total = sum(w for _, w in items)
    r = random.uniform(0, total)
    upto = 0
    for value, w in items:
        upto += w
        if upto >= r:
            return value
    return items[-1][0]


def random_datetime_in_range(start: date, end: date, tz):
    span_days = max((end - start).days, 0)
    d = start + timedelta(days=random.randint(0, span_days))
    hour = random.choices(
        range(0, 24),
        weights=[1, 1, 1, 1, 1, 1, 2, 4, 6, 7, 7, 7, 8, 8, 7, 7, 7, 8, 9, 9, 8, 6, 4, 2],
        k=1,
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return timezone.make_aware(datetime.combine(d, dt_time(hour, minute, second)), tz)


def gen_chip() -> str:
    """ISO 11784/11785: 15 цифр. Префикс 643 — Россия."""
    return '643' + ''.join(str(random.randint(0, 9)) for _ in range(12))


def make_unique_slug(title: str, existing: set) -> str:
    base = slugify(title, allow_unicode=False)
    if not base:
        base = f'article-{random.randint(1000, 9999)}'
    slug = base
    n = 2
    while slug in existing:
        slug = f'{base}-{n}'
        n += 1
    existing.add(slug)
    return slug


# ── Команда ───────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = 'Генерит реалистичные данные: пользователей, клиники, услуги, питомцев, документы, чаты, статьи.'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=32)
        parser.add_argument('--no-files', action='store_true', help='Не создавать реальные PDF (быстрее)')
        parser.add_argument('--start', default='2026-04-22', help='Начало окна регистраций (YYYY-MM-DD)')
        parser.add_argument('--end', default=None, help='Конец окна (YYYY-MM-DD), по умолчанию — сегодня')
        parser.add_argument('--seed', type=int, default=None, help='Зерно ГСЧ для воспроизводимости')
        parser.add_argument('--skip-articles', action='store_true', help='Не создавать статьи блога')
        parser.add_argument(
            '--reset', action='store_true',
            help='ОПАСНО: перед сидингом удалить ВСЕХ не-суперюзеров и связанные данные '
                 '(питомцев, документы, медзаписи, статьи). Супер-юзеры и их данные не трогаются.',
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            start_d = datetime.strptime(opts['start'], '%Y-%m-%d').date()
            end_d = (datetime.strptime(opts['end'], '%Y-%m-%d').date()
                     if opts['end'] else timezone.localdate())
        except ValueError:
            raise CommandError('Дата должна быть в формате YYYY-MM-DD')
        if end_d < start_d:
            raise CommandError('Конец окна не может быть раньше начала')

        if opts['seed'] is not None:
            random.seed(opts['seed'])

        # ── 0. Сброс старых данных, если попросили ─────────────────────────
        if opts['reset']:
            # Удаляем всех не-суперюзеров. Каскадом снесутся: pets, documents,
            # medical_records, чаты, авторство статей (на статьях ставится NULL).
            removed = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING(
                f'⚠ Сброс: удалено {removed[0]} объектов '
                f'(пользователи + связанные питомцы / документы / медзаписи).'
            ))
            # Удалим осиротевшие статьи, у которых author стал NULL после сброса —
            # чтобы не было «двух источников» статей.
            Article.objects.filter(author__isnull=True).delete()

        tz = timezone.get_current_timezone()
        password_hash = make_password('Petrov2026!')
        created_pdfs = not opts['no_files']

        # ── 1. Пользователи (только владельцы) ──────────────────────────────
        n_users = opts['users']
        n_owners = n_users
        n_vets = 0
        n_admins = 0

        existing_usernames = set(User.objects.values_list('username', flat=True))
        existing_emails = set(User.objects.values_list('email', flat=True))

        def fresh_username(first, last, idx):
            for _ in range(15):
                u = make_username(first, last, idx)
                if u and u not in existing_usernames:
                    existing_usernames.add(u)
                    return u
                idx += 1
            u = f'{translit(first)}{translit(last)[:3]}{random.randint(100, 9999)}'
            existing_usernames.add(u)
            return u

        def fresh_email(username):
            for _ in range(8):
                e = make_email(username)
                if e not in existing_emails:
                    existing_emails.add(e)
                    return e
                username = f'{username}{random.randint(1, 99)}'
            return f'{username}.{random.randint(1000, 9999)}@mail.ru'

        def build_user(role, idx):
            is_female = random.random() < 0.55
            first = random.choice(FIRST_F if is_female else FIRST_M)
            last = random.choice(LAST_F if is_female else LAST_M)
            username = fresh_username(first, last, idx)
            email = fresh_email(username)
            joined = random_datetime_in_range(start_d, end_d, tz)
            last_login = None
            if random.random() < 0.7:
                gap = max((end_d - joined.date()).days, 0)
                last_login = joined + timedelta(days=random.randint(0, gap),
                                                hours=random.randint(0, 23),
                                                minutes=random.randint(0, 59))
                if last_login.date() > end_d:
                    last_login = timezone.make_aware(
                        datetime.combine(end_d, dt_time(random.randint(8, 22), random.randint(0, 59))), tz)
            user = User(
                username=username, first_name=first, last_name=last, email=email,
                user_type=role, date_joined=joined, last_login=last_login,
                is_active=True, password=password_hash,
            )
            if random.random() < 0.3:
                user.pin_hash = make_password(f'{random.randint(0, 9999):04d}')
                user.pin_enabled = True
            return user

        owners = [build_user('owner', i + 1) for i in range(n_owners)]
        new_users = owners
        User.objects.bulk_create(new_users)
        owners = list(User.objects.filter(username__in=[u.username for u in owners]))

        # vets — только существующие в БД (если есть), для авторства медзаписей и статей
        vets = list(User.objects.filter(user_type='vet'))

        self.stdout.write(self.style.SUCCESS(
            f'✓ Владельцев питомцев создано: {len(new_users)}. '
            f'Окно регистрации: {start_d.strftime("%d.%m.%Y")} — {end_d.strftime("%d.%m.%Y")}.'
        ))

        # ── 2. Питомцы (только собаки и кошки) ──────────────────────────────
        owners_with_pets = owners[:14]
        all_pets_to_create = []
        for o in owners_with_pets:
            for _ in range(random.randint(1, 3)):
                species = weighted_choice(SPECIES_WEIGHTS)
                breed = random.choice(BREEDS[species])
                age_days = random.randint(180, 4500)
                chip = gen_chip() if random.random() < 0.6 else None
                # Уникальность chip_number — проверим коллизии
                if chip and Pet.objects.filter(chip_number=chip).exists():
                    chip = None
                all_pets_to_create.append(Pet(
                    owner=o,
                    name=random.choice(PET_NAMES),
                    species=species,
                    breed=breed,
                    birth_date=(end_d - timedelta(days=age_days)),
                    chip_number=chip,
                ))

        # Создаём по одному, чтобы UUID/QR корректно сгенерировались (в bulk_create
        # default-функция тоже работает, но при коллизии chip падает вся пачка)
        pets_created = []
        for p in all_pets_to_create:
            try:
                p.save()
                pets_created.append(p)
            except Exception:
                p.chip_number = None
                p.save()
                pets_created.append(p)

        # Поправим created_at у питомцев (auto_now_add)
        for p in pets_created:
            cdate = random_datetime_in_range(p.owner.date_joined.date(), end_d, tz)
            Pet.objects.filter(pk=p.pk).update(created_at=cdate)

        self.stdout.write(self.style.SUCCESS(f'✓ Питомцы: {len(pets_created)}'))

        # ── 3. Документы (PetDocument) ──────────────────────────────────────
        docs_made = 0
        owners_with_3plus = set()
        templates = doc_titles()
        pets_by_owner = {}
        for p in pets_created:
            pets_by_owner.setdefault(p.owner_id, []).append(p)

        for owner_id, pets in pets_by_owner.items():
            target = random.randint(3, 7)
            owner_docs = 0
            owner_obj = pets[0].owner
            joined_date = owner_obj.date_joined.date()
            while owner_docs < target:
                pet = random.choice(pets)
                category = random.choice(list(templates.keys()))
                tpl_title, tpl_descr = random.choice(templates[category])
                doc_date = joined_date + timedelta(
                    days=random.randint(0, max((end_d - joined_date).days, 0)))
                title = tpl_title.format(year=doc_date.year,
                                         date=doc_date.strftime('%d.%m.%Y'),
                                         ser=random.randint(10000, 99999))
                doc = PetDocument(pet=pet, category=category, title=title,
                                  description=tpl_descr, date=doc_date)
                if created_pdfs:
                    pdf_bytes = fake_pdf_bytes(title, tpl_descr)
                    fname = f'{category}_{doc_date.strftime("%Y%m%d")}_{random.randint(100, 999)}.pdf'
                    doc.file.save(fname, ContentFile(pdf_bytes), save=False)
                else:
                    doc.file.name = f'documents/pet_{pet.pk}/{category}/{category}_{random.randint(1000, 9999)}.pdf'
                doc.save()
                # Поправим uploaded_at (auto_now_add)
                upload_dt = random_datetime_in_range(doc_date, end_d, tz)
                PetDocument.objects.filter(pk=doc.pk).update(uploaded_at=upload_dt)
                owner_docs += 1
                docs_made += 1
            if owner_docs >= 3:
                owners_with_3plus.add(owner_id)

        self.stdout.write(self.style.SUCCESS(
            f'✓ Документы: {docs_made} (владельцев с ≥3 доков: {len(owners_with_3plus)})'))

        # ── 4. Медзаписи (MedicalRecord) ────────────────────────────────────
        records_made = 0
        for pet in pets_created:
            for _ in range(random.randint(2, 5)):
                rtype = random.choice(list(RECORD_TEMPLATES.keys()))
                title = random.choice(RECORD_TEMPLATES[rtype])
                joined_date = pet.owner.date_joined.date()
                rec_date = joined_date + timedelta(
                    days=random.randint(0, max((end_d - joined_date).days, 0)))
                rec = MedicalRecord.objects.create(
                    pet=pet,
                    created_by=random.choice(vets) if vets else None,
                    record_type=rtype, title=title,
                    description=f'Запись по результатам приёма от {rec_date.strftime("%d.%m.%Y")}.',
                    date=rec_date,
                )
                created_dt = random_datetime_in_range(rec_date, end_d, tz)
                MedicalRecord.objects.filter(pk=rec.pk).update(created_at=created_dt)
                records_made += 1

        self.stdout.write(self.style.SUCCESS(f'✓ Медзаписи: {records_made}'))

        # ── 5. Статьи блога ─────────────────────────────────────────────────
        if not opts['skip_articles']:
            existing_slugs = set(Article.objects.values_list('slug', flat=True))
            articles_made = 0
            for art_data in ARTICLES:
                slug = make_unique_slug(art_data['title'], existing_slugs)
                author = random.choice(vets) if vets else None
                a = Article.objects.create(
                    title=art_data['title'], slug=slug, content=art_data['content'],
                    author=author, is_published=True,
                )
                pub_dt = random_datetime_in_range(start_d, end_d, tz)
                Article.objects.filter(pk=a.pk).update(published_at=pub_dt)
                articles_made += 1
            self.stdout.write(self.style.SUCCESS(f'✓ Статьи блога: {articles_made}'))

        # ── Финал ──────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Готово.'))
        self.stdout.write(f'   Пароль для всех созданных пользователей: Petrov2026!')
        self.stdout.write(f'   Чтобы войти от имени конкретного юзера — посмотри список '
                          f'в админке (/admin/) или возьми любой логин из выгрузки CSV в /dashboard/.')
