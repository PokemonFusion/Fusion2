from django.db import migrations, models
import django.contrib.postgres.fields
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0008_pokemon_temporary'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ActiveMoveset',
        ),
        migrations.DeleteModel(
            name='OwnedPokemon',
        ),
        migrations.CreateModel(
            name='Move',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='OwnedPokemon',
            fields=[
                ('unique_id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True, serialize=False)),
                ('species', models.CharField(max_length=50)),
                ('nickname', models.CharField(blank=True, max_length=50)),
                ('gender', models.CharField(blank=True, max_length=10)),
                ('nature', models.CharField(blank=True, max_length=20)),
                ('ability', models.CharField(blank=True, max_length=50)),
                ('held_item', models.CharField(blank=True, max_length=50)),
                ('tera_type', models.CharField(blank=True, max_length=20)),
                ('total_exp', models.BigIntegerField(default=0)),
                ('ivs', django.contrib.postgres.fields.ArrayField(models.PositiveSmallIntegerField(), size=6)),
                ('evs', django.contrib.postgres.fields.ArrayField(models.PositiveSmallIntegerField(), size=6)),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, db_index=True, to='pokemon.trainer')),
            ],
        ),
        migrations.CreateModel(
            name='ActiveMoveslot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot', models.PositiveSmallIntegerField(db_index=True)),
                ('move', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, db_index=True, to='pokemon.move')),
                ('pokemon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, db_index=True, to='pokemon.ownedpokemon')),
            ],
            options={'unique_together': {('pokemon', 'slot')}},
        ),
        migrations.AddField(
            model_name='ownedpokemon',
            name='learned_moves',
            field=models.ManyToManyField(related_name='owners', to='pokemon.move'),
        ),
        migrations.AddField(
            model_name='ownedpokemon',
            name='active_moveset',
            field=models.ManyToManyField(related_name='active_on', through='pokemon.ActiveMoveslot', to='pokemon.move'),
        ),
        migrations.CreateModel(
            name='BattleSlot',
            fields=[
                ('pokemon', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='pokemon.ownedpokemon')),
                ('battle_id', models.PositiveIntegerField(db_index=True)),
                ('battle_team', models.PositiveSmallIntegerField(db_index=True)),
                ('current_hp', models.PositiveIntegerField()),
                ('status', models.CharField(max_length=20)),
                ('fainted', models.BooleanField(default=False)),
            ],
            bases=(models.Model,),
        ),
    ]
