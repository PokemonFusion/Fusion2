"""Transactional PP restoration for battle items."""

from __future__ import annotations

from django.db import transaction

from pokemon.names import normalize_name
from pokemon.services.move_management import _get_move_pp_from_dex, _get_movedex
from pokemon.services.pokemon_refs import parse_pokemon_ref


class ItemUnavailable(Exception):
    """An item debit failed; roll back any partial inventory changes."""


class BattlePPRestoration:
    """Restore the first depleted active move, using stored PP when owned."""

    def __init__(self, pokemon, trainer=None, *, amount=10):
        """Bind the battle snapshot, item owner and restoration amount."""
        self.pokemon = pokemon
        self.trainer = trainer
        self.amount = amount

    @staticmethod
    def _maximum(move_name, bonus=0):
        """Resolve display and compact move names to their boosted PP cap."""
        _, base = _get_move_pp_from_dex(_get_movedex(), move_name)
        return int(base) + int(bonus) if base is not None else None

    def _update_snapshot(self, move_name, pp):
        """Keep serialised battle moves consistent with the committed slot."""
        for move in self.pokemon.moves:
            if normalize_name(move.name) == normalize_name(move_name):
                move.pp = pp

    def restore(self, consume_item) -> bool:
        """Commit one item debit and one capped PP write, or apply no effect."""
        kind, identifier = parse_pokemon_ref(getattr(self.pokemon, "model_id", None))
        try:
            if kind == "owned" and identifier:
                return self._restore_owned(identifier, consume_item)
            return self._restore_temporary(consume_item)
        except ItemUnavailable:
            return False

    def _restore_owned(self, identifier, consume_item):
        """Lock fresh owned slots so reconnects and competing uses agree."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost

        with transaction.atomic():
            owned = OwnedPokemon.objects.select_for_update().get(pk=identifier)
            owned.refresh_from_db()
            if owned.trainer_id != getattr(self.trainer, "pk", None):
                raise ValueError("PP restoration requires the owning trainer.")
            slots = list(ActiveMoveslot.objects.select_for_update(of=("self",)).filter(
                pokemon_id=identifier,
            ).select_related("move").order_by("slot"))
            bonuses = dict(MovePPBoost.objects.filter(pokemon_id=identifier).values_list("move_id", "bonus_pp"))
            for move in self.pokemon.moves:
                slot = next((s for s in slots if normalize_name(s.move.name) == normalize_name(move.name)), None)
                if slot is None:
                    continue
                maximum = self._maximum(slot.move.name, bonuses.get(slot.move_id, 0))
                if maximum is None:
                    continue
                current = slot.current_pp if slot.current_pp is not None else maximum
                if current >= maximum:
                    continue
                if not consume_item():
                    raise ItemUnavailable
                updated = min(maximum, max(0, current) + self.amount)
                slot.current_pp = updated
                slot.save(update_fields=["current_pp"])
                transaction.on_commit(lambda: self._update_snapshot(slot.move.name, updated))
                return True
        return False

    def _restore_temporary(self, consume_item):
        """Support transient battle simulations without requiring model rows."""
        for move in self.pokemon.moves:
            maximum = getattr(move, "max_pp", None)
            if maximum is None:
                maximum = self._maximum(move.name)
            current = getattr(move, "pp", maximum)
            if maximum is None or current is None or current >= maximum:
                continue
            if not consume_item():
                raise ItemUnavailable
            move.pp = min(maximum, max(0, current) + self.amount)
            return True
        return False
