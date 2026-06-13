from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('insta_monitor', '0002_instaobserveduser_is_deleted'),
        ('telegram_users', '0003_webregistrationrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstaSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('observed_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='insta_monitor.instaobserveduser')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insta_subscriptions', to='telegram_users.telegramuser')),
            ],
            options={
                'db_table': 'insta_subscription',
                'ordering': ['observed_user__username'],
            },
        ),
        migrations.AddConstraint(
            model_name='instasubscription',
            constraint=models.UniqueConstraint(fields=('observed_user', 'user'), name='unique_insta_subscription_per_user'),
        ),
    ]
