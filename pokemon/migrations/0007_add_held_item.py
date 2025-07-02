from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0006_pokemon_ability_alter_userstorage_stored_pokemon_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pokemon',
            name='held_item',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
