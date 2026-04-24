from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='opportunity',
            name='status',
            field=models.CharField(blank=True, default='Not Started', max_length=32),
        ),
    ]
