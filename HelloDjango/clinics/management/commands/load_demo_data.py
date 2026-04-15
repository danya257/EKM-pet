# clinics/management/commands/load_demo_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pets.models import Pet
from clinics.models import Clinic
from medical_records.models import MedicalRecord
from blog.models import Article
from services.models import Service, ServiceAssignment
from chat.models import Chat, Message
from django.utils import timezone
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = 'Загружает демонстрационные данные для дипломной работы VetMis'

    def handle(self, *args, **options):
        self.stdout.write('Удаление старых данных...')
        # Удаляем в обратном порядке (из-за foreign keys)
        # Удаляем в порядке, обратном зависимостям
        Message.objects.all().delete()
        Chat.objects.all().delete()
        ServiceAssignment.objects.all().delete()
        Service.objects.all().delete()
        MedicalRecord.objects.all().delete()
        Pet.objects.all().delete()
        Article.objects.all().delete()
        Clinic.admins.through.objects.all().delete()  # ManyToMany
        Clinic.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write('Создание пользователей...')

        # Админ сайта
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@vetmis.local',
            password='12345',
            first_name='Админ',
            last_name='Сайта'
        )

        # Владельцы
        owner1 = User.objects.create_user(
            username='ivan',
            email='ivan@example.com',
            password='12345',
            first_name='Иван',
            last_name='Петров',
            user_type='owner'
        )
        owner2 = User.objects.create_user(
            username='anna',
            email='anna@example.com',
            password='13245',
            first_name='Анна',
            last_name='Сидорова',
            user_type='owner'
        )

        # Ветеринары и админы клиник
        vet1 = User.objects.create_user(
            username='dr_kotov',
            email='kotov@vet.local',
            password='12345',
            first_name='Алексей',
            last_name='Котов',
            user_type='vet'
        )
        clinic_admin = User.objects.create_user(
            username='admin_zoovet',
            email='admin@zoovet.local',
            password='12345',
            first_name='Мария',
            last_name='Веткина',
            user_type='clinic_admin'
        )

        self.stdout.write('Создание питомцев...')
        pet1 = Pet.objects.create(
            owner=owner1,
            name='Барсик',
            species='cat',
            breed='Сиамский',
            birth_date='2020-05-15',
            chip_number='CH987654321'
        )
        pet2 = Pet.objects.create(
            owner=owner2,
            name='Рекс',
            species='dog',
            breed='Немецкая овчарка',
            birth_date='2021-03-10'
        )

        self.stdout.write('Создание клиник...')
        clinic1 = Clinic.objects.create(
            name='ЗооВет',
            address='г. Москва, ул. Ленина, д. 10',
            phone='+7 (495) 123-45-67',
            email='info@zoovet.ru',
            website='https://zoovet.ru'
        )
        clinic1.admins.add(vet1, clinic_admin)

        clinic2 = Clinic.objects.create(
            name='БиоКонтроль',
            address='г. Санкт-Петербург, Невский пр., 25',
            phone='+7 (812) 987-65-43',
            email='contact@biocontrol.ru'
        )
        clinic2.admins.add(vet1)

        self.stdout.write('Создание медицинских записей...')
        MedicalRecord.objects.create(
            pet=pet1,
            created_by=vet1,
            record_type='vaccination',
            title='Вакцинация от бешенства',
            description='Вакцина Nobivac Rabies',
            date='2023-06-01'
        )
        MedicalRecord.objects.create(
            pet=pet2,
            created_by=owner2,
            record_type='note',
            title='Аллергия на курицу',
            description='Проявляется зудом и покраснением',
            date='2023-08-15'
        )

        self.stdout.write('Создание статей блога...')
        Article.objects.create(
            title='Как правильно кормить кошку',
            slug='kak-kormit-koshku',
            content='Сбалансированное питание — залог здоровья вашей кошки. Рекомендуется...',
            author=admin,
            is_published=True
        )
        Article.objects.create(
            title='Прививки для собак: календарь 2025',
            slug='privivki-dlya-sobak-2025',
            content='Вакцинация защищает от чумки, бешенства и других опасных заболеваний...',
            author=admin,
            is_published=True
        )

        self.stdout.write('Создание услуг клиник...')
        service1 = Service.objects.create(
            clinic=clinic1,
            name='Вакцинация',
            description='Комплексная вакцинация по возрасту',
            price=1200.00
        )
        service2 = Service.objects.create(
            clinic=clinic1,
            name='Чипирование',
            description='Имплантация микрочипа',
            price=800.00
        )

        ServiceAssignment.objects.create(
            service=service1,
            vet=vet1,
            available_slots=[
                {"date": "2025-12-20", "times": ["10:00", "11:00", "15:00"]},
                {"date": "2025-12-21", "times": ["09:00", "14:00"]}
            ]
        )

        self.stdout.write('Создание чатов и сообщений...')
        chat1 = Chat.objects.create(
            owner=owner1,
            vet=vet1,
            clinic=clinic1,
            pet=pet1
        )
        Message.objects.create(
            chat=chat1,
            sender=owner1,
            text='Здравствуйте! У моего кота Барсика пропал аппетит. Что делать?'
        )
        Message.objects.create(
            chat=chat1,
            sender=vet1,
            text='Здравствуйте! Сколько дней нет аппетита? Есть ли рвота или понос?',
            is_read=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ Демо-данные успешно загружены!\n\n'
                'ЛОГИНЫ:\n'
                '• Админ сайта: admin / admin\n'
                '• Владелец: ivan / owner123\n'
                '• Ветеринар: dr_kotov / vet123\n\n'
                'Запустите сервер: python manage.py runserver\n'
            )
        )