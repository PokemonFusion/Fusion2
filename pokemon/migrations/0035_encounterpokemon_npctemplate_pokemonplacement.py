from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.fields
import uuid


def backfill_pokemon_placements(apps, schema_editor):
    UserStorage = apps.get_model("pokemon", "UserStorage")
    PokemonPlacement = apps.get_model("pokemon", "PokemonPlacement")

    for storage in UserStorage.objects.all():
        seen = set()

        active_slots = (
            storage.active_slots.select_related("pokemon").order_by("slot", "id")
            if hasattr(storage, "active_slots")
            else []
        )
        for slot_rel in active_slots:
            pokemon = getattr(slot_rel, "pokemon", None)
            if pokemon is None:
                continue
            key = getattr(pokemon, "pk", None)
            if key in seen:
                continue
            PokemonPlacement.objects.update_or_create(
                pokemon=pokemon,
                defaults={
                    "storage": storage,
                    "location_type": "party",
                    "slot": slot_rel.slot,
                    "box": None,
                    "box_position": None,
                },
            )
            seen.add(key)

        boxes = storage.boxes.all().order_by("id") if hasattr(storage, "boxes") else []
        for box in boxes:
            pokemon_qs = box.pokemon.all().order_by("pk") if hasattr(box, "pokemon") else []
            for index, pokemon in enumerate(pokemon_qs, start=1):
                key = getattr(pokemon, "pk", None)
                if key in seen:
                    continue
                PokemonPlacement.objects.update_or_create(
                    pokemon=pokemon,
                    defaults={
                        "storage": storage,
                        "location_type": "box",
                        "slot": None,
                        "box": box,
                        "box_position": index,
                    },
                )
                seen.add(key)

        stored = storage.stored_pokemon.all().order_by("pk") if hasattr(storage, "stored_pokemon") else []
        default_box = boxes[0] if boxes else None
        for index, pokemon in enumerate(stored, start=1):
            key = getattr(pokemon, "pk", None)
            if key in seen:
                continue
            PokemonPlacement.objects.update_or_create(
                pokemon=pokemon,
                defaults={
                    "storage": storage,
                    "location_type": "box",
                    "slot": None,
                    "box": default_box,
                    "box_position": index,
                },
            )
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0034_delete_pokemonfusion"),
    ]

    operations = [
        migrations.CreateModel(
            name="EncounterPokemon",
            fields=[
                ("species", models.CharField(default="", max_length=50)),
                ("level", models.PositiveSmallIntegerField(default=1)),
                ("ability", models.CharField(blank=True, max_length=50)),
                ("nature", models.CharField(blank=True, max_length=20)),
                ("gender", models.CharField(blank=True, max_length=10)),
                (
                    "ivs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(),
                        default=list,
                        size=6,
                    ),
                ),
                (
                    "evs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(),
                        default=list,
                        size=6,
                    ),
                ),
                ("held_item", models.CharField(blank=True, max_length=50)),
                ("encounter_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_kind", models.CharField(choices=[("wild", "Wild"), ("npc", "NPC")], db_index=True, max_length=10)),
                ("template_key", models.CharField(blank=True, max_length=100)),
                ("current_hp", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(blank=True, max_length=20)),
                ("move_names", models.JSONField(blank=True, default=list)),
                ("move_pp", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "npc_trainer",
                    models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="encounter_pokemon", to="pokemon.npctrainer"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NPCPokemonTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("template_key", models.CharField(blank=True, max_length=100)),
                ("species", models.CharField(max_length=50)),
                ("level", models.PositiveSmallIntegerField(default=1)),
                ("ability", models.CharField(blank=True, max_length=50)),
                ("nature", models.CharField(blank=True, max_length=20)),
                ("gender", models.CharField(blank=True, max_length=10)),
                (
                    "ivs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(),
                        default=list,
                        size=6,
                    ),
                ),
                (
                    "evs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(),
                        default=list,
                        size=6,
                    ),
                ),
                ("held_item", models.CharField(blank=True, max_length=50)),
                ("move_names", models.JSONField(blank=True, default=list)),
                ("sort_order", models.PositiveSmallIntegerField(db_index=True, default=1)),
                ("npc_trainer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pokemon_templates", to="pokemon.npctrainer")),
            ],
            options={"ordering": ("sort_order", "id")},
        ),
        migrations.CreateModel(
            name="PokemonPlacement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location_type", models.CharField(choices=[("party", "Party"), ("box", "Box")], db_index=True, max_length=10)),
                ("slot", models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ("box_position", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("box", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="placements", to="pokemon.storagebox")),
                ("pokemon", models.OneToOneField(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="placement", to="pokemon.ownedpokemon")),
                ("storage", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="placements", to="pokemon.userstorage")),
            ],
        ),
        migrations.AddConstraint(
            model_name="pokemonplacement",
            constraint=models.UniqueConstraint(condition=models.Q(("location_type", "party")), fields=("storage", "slot"), name="pokemon_party_slot_unique"),
        ),
        migrations.RunPython(backfill_pokemon_placements, migrations.RunPython.noop),
    ]
