from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='pin_hash',
            field=models.CharField(
                blank=True,
                help_text='Хэш 4-значного PIN-кода для быстрого входа',
                max_length=128,
                null=True,
                verbose_name='PIN-код (хэш)',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='pin_enabled',
            field=models.BooleanField(default=False, verbose_name='PIN включён'),
        ),
    ]
