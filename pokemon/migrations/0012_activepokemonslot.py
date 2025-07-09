from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0011_ownedpokemon_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivePokemonSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot', models.PositiveSmallIntegerField(db_index=True)),
                ('pokemon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='active_slots', to='pokemon.ownedpokemon', db_index=True)),
                ('storage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='active_slots', to='pokemon.userstorage', db_index=True)),
            ],
            options={
                'unique_together': {('storage', 'slot'), ('storage', 'pokemon')},
            },
        ),
        migrations.AlterField(
            model_name='userstorage',
            name='active_pokemon',
            field=models.ManyToManyField(related_name='active_users', through='pokemon.ActivePokemonSlot', to='pokemon.ownedpokemon'),
        ),
    ]
