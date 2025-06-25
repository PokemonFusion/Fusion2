from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0004_pokemon_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='OwnedPokemon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('species', models.CharField(max_length=50)),
                ('nickname', models.CharField(blank=True, max_length=50)),
                ('nature', models.CharField(max_length=20)),
                ('gender', models.CharField(max_length=10)),
                ('shiny', models.BooleanField(default=False)),
                ('level', models.IntegerField(default=1)),
                ('experience', models.IntegerField(default=0)),
                ('happiness', models.IntegerField(default=0)),
                ('bond', models.IntegerField(default=0)),
                ('ivs', models.JSONField(default=dict)),
                ('evs', models.JSONField(default=dict)),
                ('current_hp', models.IntegerField(default=0)),
                ('max_hp', models.IntegerField(default=0)),
                ('status_condition', models.CharField(blank=True, max_length=20)),
                ('walked_steps', models.IntegerField(default=0)),
                ('battle_id', models.IntegerField(blank=True, null=True)),
                ('battle_team', models.CharField(blank=True, max_length=1)),
                ('held_item', models.CharField(blank=True, max_length=50)),
                ('ability', models.CharField(max_length=50)),
                ('known_moves', models.JSONField(blank=True, default=list)),
                ('moveset', models.JSONField(blank=True, default=list)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('current_trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_pokemon', to='objects.objectdb')),
                ('original_trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='original_pokemon', to='objects.objectdb')),
            ],
        ),
        migrations.CreateModel(
            name='ActiveMoveset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('moves', models.JSONField(blank=True, default=list)),
                ('pokemon', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='active_moveset', to='pokemon.ownedpokemon')),
            ],
            bases=(models.Model,),
        ),
    ]
