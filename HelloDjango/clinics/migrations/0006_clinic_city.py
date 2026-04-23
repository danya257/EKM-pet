from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0005_alter_clinic_reviews'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinic',
            name='city',
            field=models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Город'),
        ),
    ]
