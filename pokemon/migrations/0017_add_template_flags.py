from django.db import migrations, models


def mark_templates(apps, schema_editor):
    OwnedPokemon = apps.get_model('pokemon', 'OwnedPokemon')
    OwnedPokemon.objects.filter(
        ai_trainer__isnull=False,
        trainer__isnull=True,
        is_wild=False,
    ).update(is_template=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0016_unify_ownedpokemon"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="is_template",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="is_battle_instance",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.RunPython(mark_templates, reverse_code=noop),
    ]
