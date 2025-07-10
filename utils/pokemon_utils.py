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
        for slot in pokemon.activemoveslot_set.all():
            clone.activemoveslot_set.create(
                move=slot.move,
                slot=slot.slot,
                current_pp=slot.current_pp,
            )
        return clone
