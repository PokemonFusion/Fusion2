from django.db import transaction
from pokemon.models import OwnedPokemon

try:
    from pokemon.battle.battleinstance import _calc_stats_from_model, create_battle_pokemon
    from pokemon.battle.battledata import Pokemon, Move
except Exception:  # pragma: no cover - allow tests to stub
    _calc_stats_from_model = None
    create_battle_pokemon = None
    Pokemon = Move = None


def clone_pokemon(pokemon: OwnedPokemon, for_ai: bool = True) -> OwnedPokemon:
    """Create a battle-only clone of ``pokemon``."""
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


def battle_pokemon_from_owned(pokemon: OwnedPokemon) -> Pokemon:
    """Create a battle-ready :class:`Pokemon` object from an ``OwnedPokemon``."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")

    stats = _calc_stats_from_model(pokemon) if _calc_stats_from_model else {"hp": pokemon.current_hp}
    move_names = []
    slots = getattr(pokemon, "activemoveslot_set", None)
    if slots is None:
        active_ms = getattr(pokemon, "active_moveset", None)
        if active_ms is not None:
            slots = getattr(active_ms, "slots", None)
    if slots is not None:
        try:
            iterable = slots.all().order_by("slot")
        except Exception:
            try:
                iterable = slots.order_by("slot")
            except Exception:
                iterable = slots
        move_names = [getattr(s.move, "name", "") for s in iterable]
    if not move_names:
        move_names = [m.name for m in getattr(pokemon, "learned_moves", []).all()[:4]] if hasattr(pokemon, "learned_moves") else []
    if not move_names:
        move_names = ["Flail"]
    moves = [Move(name=m) for m in move_names[:4]]
    battle_poke = Pokemon(
        name=getattr(pokemon, "name", getattr(pokemon, "species", "Pikachu")),
        level=getattr(pokemon, "computed_level", getattr(pokemon, "level", 1)),
        hp=getattr(pokemon, "current_hp", stats.get("hp", 1)),
        max_hp=stats.get("hp", getattr(pokemon, "current_hp", 1)),
        moves=moves,
        ability=getattr(pokemon, "ability", None),
        data=getattr(pokemon, "data", {}),
        model_id=str(getattr(pokemon, "unique_id", "")) or None,
    )
    if slots is not None:
        battle_poke.activemoveslot_set = slots
    return battle_poke


def spawn_npc_pokemon(trainer, *, use_templates: bool = True) -> Pokemon:
    """Return a battle-ready Pokémon for an NPC trainer."""

    if use_templates:
        qs = OwnedPokemon.objects.filter(ai_trainer=trainer, is_template=True)
        template = qs.order_by("unique_id").first() if hasattr(qs, "order_by") else (qs[0] if qs else None)
        if template:
            clone = clone_pokemon(template, for_ai=True)
            return battle_pokemon_from_owned(clone)

    if create_battle_pokemon is None:
        raise RuntimeError("Battle modules not available")
    return create_battle_pokemon("Charmander", 5, trainer=trainer, is_wild=False)

