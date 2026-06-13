from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insta_monitor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='instaobserveduser',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
