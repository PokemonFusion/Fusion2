from django.db import migrations, models


def sync_levels(apps, schema_editor):
    """Ensure the new ``level`` field reflects stored experience."""

    OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
    from pokemon.stats import level_for_exp

    for mon in OwnedPokemon.objects.all():
        level = level_for_exp(mon.total_exp)
        if hasattr(mon, "level"):
            mon.level = level
            mon.save(update_fields=["level"])


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0024_alter_moveppboost_id_alter_pokemonfusion_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="level",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.RunPython(sync_levels, migrations.RunPython.noop),
    ]

