"""Canonical, slot-scoped persistence for a successful owned Pokemon Sketch."""


class SketchWriter:
    """Replace one active Sketch slot without rebuilding unrelated PP or sets."""

    def replace(self, identifier, slot_number, move_name):
        """Lock the actual owner, validate Sketch, then update just its active slot."""
        from django.db import transaction
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.move_management import get_or_create_move, normalize_move_key

        with transaction.atomic():
            pokemon = OwnedPokemon.objects.select_for_update().get(unique_id=identifier)
            slot = pokemon.activemoveslot_set.select_for_update().filter(slot=slot_number).first()
            if slot is None or normalize_move_key(slot.move.name) != normalize_move_key("Sketch"):
                return False
            move = get_or_create_move(move_name, pokemon=pokemon)
            pokemon.learned_moves.add(move)
            slot.move = move
            slot.current_pp = pokemon.get_max_pp(move.name)
            slot.save(update_fields=["move", "current_pp"])
            if pokemon.active_moveset_id:
                pokemon.active_moveset.slots.filter(slot=slot_number).update(move=move)
            return True
