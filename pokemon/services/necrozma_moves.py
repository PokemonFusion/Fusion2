"""Bound native source slots and deferred base knowledge for live Necrozma hosts."""

from copy import copy

from pokemon.names import normalize_name


def pair_for_model(pokemon, operation="inspect"):
    """Keep pure battle simulations separate from actual owned model writers."""
    if getattr(getattr(pokemon, "_meta", None), "label_lower", None) != "pokemon.ownedpokemon":
        return None
    from pokemon.services.necrozma_guards import assert_operation

    return assert_operation(pokemon.pk, operation)


def progression_species(pokemon):
    """The linked host earns its base Necrozma level-up knowledge, never R moves."""
    pair = pair_for_model(pokemon)
    return "Necrozma" if pair and str(pair["host_id"]) == str(pokemon.pk) else pokemon.species


def remember_progression(pokemon):
    """Store legitimate base knowledge without prompts, set switches or PP refills."""
    if not pair_for_model(pokemon, "progression"):
        return False
    from pokemon.utils.move_learning import get_learnable_levelup_moves, learn_move

    moves, _ = get_learnable_levelup_moves(pokemon)
    for name in moves:
        learn_move(pokemon, name, knowledge_only=True)
    return True


def remember_move(pokemon, name, *, knowledge_only=False):
    """Handle only a linked host's reviewed progression; manual writes reject."""
    if not pair_for_model(pokemon, "progression" if knowledge_only else "moves"):
        return False
    from pokemon.services.move_management import get_or_create_move, level_up_move_names_for_pokemon
    from pokemon.services.necrozma_guards import NecrozmaError

    allowed = {normalize_name(move) for move in level_up_move_names_for_pokemon(pokemon)}
    if not knowledge_only or normalize_name(name) not in allowed:
        raise NecrozmaError("Only earned base Necrozma knowledge can be stored while linked; active slots stay locked.")
    pokemon.learned_moves.add(get_or_create_move(name, pokemon=pokemon))
    return True


def gain_experience(pokemon, amount, *, rate=None):
    """Persist linked EXP/level and base knowledge together on the same owned row."""
    if not pair_for_model(pokemon, "progression"):
        return False
    from django.db import transaction
    from pokemon.models.stats import level_for_exp
    from pokemon.models.storage import UserStorage
    from pokemon.services.ownership import fresh_owned
    from pokemon.names import resolve_dex_entry
    from pokemon.dex import POKEDEX

    with transaction.atomic():
        # Reward claims acquire storage before trainer/owned, matching field use.
        UserStorage.objects.select_for_update().filter(user_id=pokemon.trainer.user_id).values("pk").get()
        current = copy(fresh_owned(pokemon.pk, lock=True))
        current._state = copy(current._state)
        pair_for_model(current, "progression")
        growth = rate or resolve_dex_entry(POKEDEX, "Necrozma").raw.get("growthRate", "medium_fast")
        if level_for_exp(current.total_exp, growth) != current.level:
            from pokemon.services.necrozma_guards import NecrozmaError

            raise NecrozmaError("Invalid saved level/EXP; source progression needs staff review.")
        current.total_exp += amount
        current.level = level_for_exp(current.total_exp, growth)
        current.save(update_fields=["total_exp", "level"])
        remember_progression(current)
        pokemon.total_exp, pokemon.level = current.total_exp, current.level
        pokemon.__dict__.pop("_cached_stats", None)
    return True


def heal_native(pokemon):
    """Serialize native-source Center healing with combine/separate and use fresh slots."""
    if getattr(getattr(pokemon, "_meta", None), "label_lower", None) != "pokemon.ownedpokemon":
        return False
    from pokemon.models.core import OwnedPokemon

    row = OwnedPokemon.objects.filter(pk=pokemon.pk).values("species", "trainer__user_id").first()
    if not row or normalize_name(row["species"]) not in {
        "necrozma", "solgaleo", "lunala", "necrozmaduskmane", "necrozmadawnwings"
    }:
        return False
    from django.db import transaction
    from pokemon.helpers.pokemon_helpers import get_max_hp
    from pokemon.models.storage import UserStorage
    from pokemon.services.move_management import apply_current_pp
    from pokemon.services.ownership import fresh_owned

    with transaction.atomic():
        UserStorage.objects.select_for_update().filter(user_id=row["trainer__user_id"]).values("pk").get()
        current = copy(fresh_owned(pokemon.pk, lock=True))
        current._state = copy(current._state)
        pair_for_model(current, "heal")
        current.current_hp, current.status, current.sleep_turns = get_max_hp(current), "", None
        apply_current_pp(current)
        current.save(update_fields=["current_hp", "status", "sleep_turns"])
        from pokemon.services.necrozma import NecrozmaService

        NecrozmaService._resync({pokemon.pk})
        def publish():
            """Retain the model method's immediate post-commit instance contract."""
            row = OwnedPokemon.objects.filter(pk=pokemon.pk).values().first()
            if row:
                for key, value in row.items():
                    setattr(pokemon, key, value)
                pokemon._state.fields_cache.clear()
                for key in ("_cached_stats", "_types_override", "_prefetched_objects_cache"):
                    pokemon.__dict__.pop(key, None)
        transaction.on_commit(publish, robust=True)
    return True
