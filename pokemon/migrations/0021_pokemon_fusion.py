from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0020_persistent_hp_pp"),
    ]

    operations = [
        migrations.CreateModel(
            name="PokemonFusion",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "parent_a",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fusion_parent_a",
                        to="pokemon.ownedpokemon",
                    ),
                ),
                (
                    "parent_b",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fusion_parent_b",
                        to="pokemon.ownedpokemon",
                    ),
                ),
                (
                    "result",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fusion_result",
                        to="pokemon.ownedpokemon",
                    ),
                ),
            ],
            options={"unique_together": {("parent_a", "parent_b")}},
        ),
    ]
