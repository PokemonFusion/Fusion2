from django.db import transaction
try:
    from pokemon.models import OwnedPokemon
except Exception:  # pragma: no cover - optional in tests
    OwnedPokemon = None

try:
    from pokemon.battle.battledata import Pokemon, Move
except Exception:  # pragma: no cover - allow tests to stub
    Pokemon = Move = None


def _get_calc_stats_from_model():
    try:
        from pokemon.battle import battleinstance as bi
        return getattr(bi, "_calc_stats_from_model", None)
    except Exception:  # pragma: no cover
        return None


def _get_create_battle_pokemon():
    try:
        from pokemon.battle import battleinstance as bi
        return getattr(bi, "create_battle_pokemon", None)
    except Exception:  # pragma: no cover
        return None


def clone_pokemon(pokemon: OwnedPokemon, for_ai: bool = True) -> OwnedPokemon:
    """Create a battle-only clone of ``pokemon``."""
    if OwnedPokemon is None:
        raise RuntimeError("OwnedPokemon model not available")

    with transaction.atomic():
        clone = OwnedPokemon.objects.create(
            species=pokemon.species,
            ability=pokemon.ability,
            nature=pokemon.nature,
            gender=pokemon.gender,
            ivs=list(pokemon.ivs),
            evs=list(pokemon.evs),
            held_item=pokemon.held_item,
            tera_type=pokemon.tera_type,
            total_exp=pokemon.total_exp,
            current_hp=pokemon.current_hp,
            is_battle_instance=True,
            ai_trainer=pokemon.ai_trainer if for_ai else None,
        )
        clone.learned_moves.set(pokemon.learned_moves.all())
        for ms in pokemon.movesets.all():
            new_set = clone.movesets.create(index=ms.index)
            for slot in ms.slots.all():
                new_set.slots.create(move=slot.move, slot=slot.slot)
            if pokemon.active_moveset and ms.index == pokemon.active_moveset.index:
                clone.active_moveset = new_set
        clone.save()
        for boost in getattr(pokemon, "pp_boosts", []).all() if hasattr(pokemon, "pp_boosts") else []:
            clone.pp_boosts.create(move=boost.move, bonus_pp=boost.bonus_pp)
        for slot in pokemon.activemoveslot_set.all():
            clone.activemoveslot_set.create(
                move=slot.move,
                slot=slot.slot,
                current_pp=slot.current_pp,
            )
        return clone


def build_battle_pokemon_from_model(model, *, full_heal: bool = False) -> Pokemon:
    """Return a battle-ready ``Pokemon`` object from a stored model."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")

    calc_stats = _get_calc_stats_from_model()
    stats = calc_stats(model) if calc_stats else {"hp": getattr(model, "current_hp", 1)}

    level = getattr(model, "computed_level", getattr(model, "level", 1))
    name = getattr(model, "name", getattr(model, "species", "Pikachu"))

    move_names = getattr(model, "moves", None) or []
    slots = getattr(model, "activemoveslot_set", None)
    if slots is None:
        active_ms = getattr(model, "active_moveset", None)
        if active_ms is not None:
            slots = getattr(active_ms, "slots", None)
    if not move_names and slots is not None:
        try:
            iterable = slots.all().order_by("slot")
        except Exception:
            try:
                iterable = slots.order_by("slot")
            except Exception:
                iterable = slots
        move_names = [getattr(s.move, "name", "") for s in iterable]
    if not move_names:
        if hasattr(model, "learned_moves"):
            try:
                move_names = [m.name for m in model.learned_moves.all()[:4]]
            except Exception:
                move_names = [m.name for m in model.learned_moves][:4]
    if not move_names:
        move_names = ["Flail"]

    moves = [Move(name=m) for m in move_names[:4]]

    current_hp = stats.get("hp", level)
    if not full_heal:
        current_hp = getattr(model, "current_hp", current_hp)

    battle_poke = Pokemon(
        name=name,
        level=level,
        hp=current_hp,
        max_hp=stats.get("hp", getattr(model, "current_hp", level)),
        moves=moves,
        ability=getattr(model, "ability", None),
        data=getattr(model, "data", {}),
        model_id=str(getattr(model, "unique_id", getattr(model, "model_id", ""))) or None,
    )
    if slots is not None:
        battle_poke.activemoveslot_set = slots
    return battle_poke


def battle_pokemon_from_owned(pokemon: OwnedPokemon) -> Pokemon:
    """Create a battle-ready :class:`Pokemon` object from an ``OwnedPokemon``."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")
    return build_battle_pokemon_from_model(pokemon)


def spawn_npc_pokemon(trainer, *, use_templates: bool = True) -> Pokemon:
    """Return a battle-ready Pokémon for an NPC trainer."""

    if use_templates:
        qs = OwnedPokemon.objects.filter(ai_trainer=trainer, is_template=True)
        template = qs.order_by("unique_id").first() if hasattr(qs, "order_by") else (qs[0] if qs else None)
        if template:
            clone = clone_pokemon(template, for_ai=True)
            return battle_pokemon_from_owned(clone)

    create_poke = _get_create_battle_pokemon()
    if create_poke is None:
        raise RuntimeError("Battle modules not available")
    return create_poke("Charmander", 5, trainer=trainer, is_wild=False)

