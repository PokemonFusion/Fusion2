from collections import defaultdict

from django.db import migrations


def _ordered_manager_items(manager, *fields):
    items = manager.all()
    order_by = getattr(items, "order_by", None)
    if callable(order_by):
        return order_by(*fields)
    return items


def _extract_move_names(legacy_pokemon):
    slots = getattr(legacy_pokemon, "activemoveslot_set", None)
    if slots is not None:
        ordered_slots = slots.all() if hasattr(slots, "all") else slots
        order_by = getattr(ordered_slots, "order_by", None)
        if callable(order_by):
            ordered_slots = order_by("slot", "id")
        names = [
            getattr(getattr(slot, "move", None), "name", "")
            for slot in ordered_slots
            if getattr(getattr(slot, "move", None), "name", "")
        ]
        if names:
            return names

    learned_moves = getattr(legacy_pokemon, "learned_moves", None)
    if learned_moves is not None:
        moves = learned_moves.all() if hasattr(learned_moves, "all") else learned_moves
        order_by = getattr(moves, "order_by", None)
        if callable(order_by):
            moves = order_by("name")
        names = [getattr(move, "name", "") for move in moves if getattr(move, "name", "")]
        if names:
            return names

    return []


def migrate_legacy_ownedpokemon_temp_rows(apps, schema_editor):
    OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
    NPCPokemonTemplate = apps.get_model("pokemon", "NPCPokemonTemplate")

    next_sort_order = defaultdict(int)
    to_delete = []

    for legacy_pokemon in _ordered_manager_items(OwnedPokemon.objects, "created_at", "pk"):
        trainer_id = getattr(legacy_pokemon, "trainer_id", None)
        ai_trainer = getattr(legacy_pokemon, "ai_trainer", None)
        ai_trainer_id = getattr(legacy_pokemon, "ai_trainer_id", None) or getattr(ai_trainer, "pk", None)
        is_wild = bool(getattr(legacy_pokemon, "is_wild", False))
        is_template = bool(getattr(legacy_pokemon, "is_template", False))
        is_battle_instance = bool(getattr(legacy_pokemon, "is_battle_instance", False))

        should_convert_template = bool(
            ai_trainer_id
            and (
                is_template
                or (trainer_id is None and not is_wild and not is_battle_instance)
            )
        )
        should_delete = bool(is_wild or is_template or is_battle_instance or ai_trainer_id)

        if should_convert_template:
            next_sort_order[ai_trainer_id] += 1
            NPCPokemonTemplate.objects.create(
                npc_trainer=ai_trainer,
                template_key=getattr(legacy_pokemon, "nickname", "") or "",
                species=getattr(legacy_pokemon, "species", ""),
                level=getattr(legacy_pokemon, "level", 1) or 1,
                ability=getattr(legacy_pokemon, "ability", "") or "",
                nature=getattr(legacy_pokemon, "nature", "") or "",
                gender=getattr(legacy_pokemon, "gender", "") or "",
                ivs=list(getattr(legacy_pokemon, "ivs", []) or []),
                evs=list(getattr(legacy_pokemon, "evs", []) or []),
                held_item=getattr(legacy_pokemon, "held_item", "") or "",
                move_names=_extract_move_names(legacy_pokemon),
                sort_order=next_sort_order[ai_trainer_id],
            )

        if should_delete:
            to_delete.append(legacy_pokemon)

    for legacy_pokemon in to_delete:
        legacy_pokemon.delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("pokemon", "0036_alter_encounterpokemon_evs_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_ownedpokemon_temp_rows, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="ai_trainer",
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="is_battle_instance",
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="is_template",
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="is_wild",
        ),
    ]
