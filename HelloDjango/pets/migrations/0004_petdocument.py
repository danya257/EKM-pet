from django.db import migrations, models
import django.db.models.deletion
import pets.models


class Migration(migrations.Migration):

    dependencies = [
        ('pets', '0003_pet_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PetDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(
                    choices=[
                        ('vaccination', 'Прививки'),
                        ('analysis', 'Анализы'),
                        ('surgery', 'Операции'),
                        ('prescription', 'Рецепты'),
                        ('certificate', 'Справки'),
                        ('other', 'Другое'),
                    ],
                    default='other',
                    max_length=20,
                    verbose_name='Категория',
                )),
                ('title', models.CharField(max_length=200, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('file', models.FileField(
                    help_text='PDF, JPG, PNG — до 10 МБ',
                    upload_to=pets.models.document_upload_path,
                    verbose_name='Файл',
                )),
                ('date', models.DateField(blank=True, null=True, verbose_name='Дата документа')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Загружен')),
                ('pet', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='pets.pet',
                    verbose_name='Питомец',
                )),
            ],
            options={
                'verbose_name': 'Документ питомца',
                'verbose_name_plural': 'Документы питомцев',
                'ordering': ['-date', '-uploaded_at'],
            },
        ),
    ]
