from django.db import migrations, models


def load_species(apps, schema_editor):
    SpeciesEntry = apps.get_model('pokemon', 'SpeciesEntry')
    try:
        from pokemon.dex.functions.pokedex_funcs import get_national_entries
    except Exception:
        return
    for dex_id, name in get_national_entries():
        SpeciesEntry.objects.get_or_create(dex_id=dex_id, name=name)


def transfer_seen(apps, schema_editor):
    Trainer = apps.get_model('pokemon', 'Trainer')
    Pokemon = apps.get_model('pokemon', 'Pokemon')
    SpeciesEntry = apps.get_model('pokemon', 'SpeciesEntry')

    for trainer in Trainer.objects.all():
        for mon in trainer.seen_pokemon.all():
            entry = SpeciesEntry.objects.filter(name__iexact=mon.name).first()
            if entry:
                trainer.seen_species.add(entry)


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0012_activepokemonslot'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpeciesEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('dex_id', models.PositiveIntegerField(blank=True, null=True, db_index=True)),
            ],
        ),
        migrations.AddField(
            model_name='trainer',
            name='seen_species',
            field=models.ManyToManyField(blank=True, related_name='seen_by_trainers', to='pokemon.speciesentry'),
        ),
        migrations.RunPython(load_species, migrations.RunPython.noop),
        migrations.RunPython(transfer_seen, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='trainer',
            name='seen_pokemon',
        ),
        migrations.RenameField(
            model_name='trainer',
            old_name='seen_species',
            new_name='seen_pokemon',
        ),
    ]
