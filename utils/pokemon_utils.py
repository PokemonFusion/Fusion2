from django.db import transaction
from pokemon.models import OwnedPokemon


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
