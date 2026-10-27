"""Add an empty mint overlay; refuse rollback that would discard paid training."""

from django.db import migrations, models

MINT_NATURES = (
    "Lonely",
    "Brave",
    "Adamant",
    "Naughty",
    "Bold",
    "Relaxed",
    "Impish",
    "Lax",
    "Timid",
    "Hasty",
    "Serious",
    "Jolly",
    "Naive",
    "Modest",
    "Mild",
    "Quiet",
    "Rash",
    "Calm",
    "Gentle",
    "Sassy",
    "Careful",
)


def refuse_training_loss(apps, schema_editor):
    """Require a separately reviewed preserving plan before removing nonblank training."""
    owned = apps.get_model("pokemon", "OwnedPokemon")
    blank = models.Q(trained_stat_nature__isnull=True) | models.Q(trained_stat_nature="")
    if owned.objects.using(schema_editor.connection.alias).exclude(blank).exists():
        raise RuntimeError(
            "Mint training exists; rollback requires a separately reviewed data-preserving plan. No training was removed."
        )


class Migration(migrations.Migration):
    """No genetic updates, inferred training, backfill or automatic item grants."""

    atomic = True
    dependencies = [("pokemon", "0058_necrozma_integrity")]
    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="trained_stat_nature",
            field=models.CharField(
                max_length=20,
                null=True,
                blank=True,
                default=None,
                choices=[(name, name) for name in MINT_NATURES],
            ),
        ),
        migrations.AddConstraint(
            model_name="ownedpokemon",
            constraint=models.CheckConstraint(
                name="owned_trained_nature_valid",
                condition=(
                    models.Q(trained_stat_nature__isnull=True)
                    | models.Q(trained_stat_nature="")
                    | models.Q(trained_stat_nature__in=MINT_NATURES)
                ),
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, refuse_training_loss),
    ]
