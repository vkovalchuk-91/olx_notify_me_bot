import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_users', '0002_web_registration'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebRegistrationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=64, unique=True)),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'telegram_user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='web_registration_requests',
                        to='telegram_users.telegramuser',
                    ),
                ),
            ],
            options={
                'db_table': 'web_registration_request',
                'ordering': ['-created_at'],
            },
        ),
    ]
