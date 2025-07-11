from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0010_update_storage_and_add_npctrainers'),
    ]

    operations = [
        migrations.AddField(
            model_name='ownedpokemon',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
