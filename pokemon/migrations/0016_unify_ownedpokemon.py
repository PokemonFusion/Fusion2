from django.db import migrations, models
import django.db.models.deletion
from pokemon.stats import exp_for_level

def copy_npc_pokemon(apps, schema_editor):
    OwnedPokemon = apps.get_model('pokemon', 'OwnedPokemon')
    NPCTrainerPokemon = apps.get_model('pokemon', 'NPCTrainerPokemon')
    NPCTrainer = apps.get_model('pokemon', 'NPCTrainer')
    for mon in NPCTrainerPokemon.objects.all():
        OwnedPokemon.objects.create(
            species=mon.species,
            ability=mon.ability,
            nature=mon.nature,
            gender=mon.gender,
            ivs=mon.ivs,
            evs=mon.evs,
            held_item=mon.held_item,
            ai_trainer=mon.trainer,
            total_exp=exp_for_level(mon.level),
        )

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0015_remove_pokemon_name_pokemon_evs_pokemon_gender_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="is_wild",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="ai_trainer",
            field=models.ForeignKey(
                related_name="wild_or_ai_pokemon",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="pokemon.npctrainer",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="ownedpokemon",
            name="trainer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="pokemon.trainer",
                null=True,
                blank=True,
                db_index=True,
            ),
        ),
        migrations.RunPython(copy_npc_pokemon, reverse_code=noop),
        migrations.DeleteModel(name="NPCTrainerPokemon"),
    ]
