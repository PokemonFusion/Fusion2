from django.db import migrations


def sync_levels(apps, schema_editor):
    OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
    from pokemon.stats import level_for_exp

    for mon in OwnedPokemon.objects.all():
        mon.level = level_for_exp(mon.total_exp)
        mon.save(update_fields=["level"])


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0024_alter_moveppboost_id_alter_pokemonfusion_id"),
    ]

    operations = [
        migrations.RunPython(sync_levels, migrations.RunPython.noop),
    ]

