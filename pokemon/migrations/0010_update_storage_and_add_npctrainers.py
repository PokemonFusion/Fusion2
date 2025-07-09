from django.db import migrations, models
import django.contrib.postgres.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0009_refactor_ownedpokemon_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstorage',
            name='active_pokemon',
            field=models.ManyToManyField(related_name='active_users', to='pokemon.ownedpokemon'),
        ),
        migrations.AlterField(
            model_name='userstorage',
            name='stored_pokemon',
            field=models.ManyToManyField(blank=True, related_name='stored_users', to='pokemon.ownedpokemon'),
        ),
        migrations.AlterField(
            model_name='storagebox',
            name='pokemon',
            field=models.ManyToManyField(blank=True, related_name='boxes', to='pokemon.ownedpokemon'),
        ),
        migrations.CreateModel(
            name='NPCTrainer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='NPCTrainerPokemon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('species', models.CharField(max_length=50)),
                ('level', models.PositiveSmallIntegerField(default=1)),
                ('ability', models.CharField(blank=True, max_length=50)),
                ('nature', models.CharField(blank=True, max_length=20)),
                ('gender', models.CharField(blank=True, max_length=10)),
                ('ivs', django.contrib.postgres.fields.ArrayField(models.PositiveSmallIntegerField(), size=6)),
                ('evs', django.contrib.postgres.fields.ArrayField(models.PositiveSmallIntegerField(), size=6)),
                ('held_item', models.CharField(blank=True, max_length=50)),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pokemon', to='pokemon.npctrainer')),
            ],
        ),
    ]
