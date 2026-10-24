"""PP-capacity rules, preserving MovePPBoost.bonus_pp as raw extra PP."""

from dataclasses import dataclass

from pokemon.names import normalize_name, resolve_dex_entry


@dataclass(frozen=True)
class PPCapacity:
    """Compute the three legal boost stages with integer rounding."""

    base: int
    blocked: bool = False

    @classmethod
    def for_move(cls, name):
        """Respect the authoritative dex's PP and noPPBoosts policy."""
        from pokemon.dex import MOVEDEX

        entry = resolve_dex_entry(MOVEDEX, name)
        raw = entry if isinstance(entry, dict) else getattr(entry, "raw", {})
        base = raw.get("pp", 0)
        return cls(base if isinstance(base, int) else 0, bool(raw.get("noPPBoosts")))

    @property
    def stages(self):
        """Return raw extra PP after zero through three PP Ups."""
        return tuple(self.base * count // 5 for count in range(4))

    def increased_bonus(self, bonus, *, maximize=False):
        """Reject ambiguous legacy stages; PP Max can finish a bounded raw bonus.

        Never infer an old use count from a raw PP value. Noncanonical but
        in-range bonuses remain readable/restorable and PP Max can fill them.
        Out-of-range rows require staff investigation, without automatic edits.
        """
        if self.blocked or self.base < 5 or not 0 <= bonus < self.stages[-1]:
            return None
        if maximize:
            return self.stages[-1]
        if bonus not in self.stages:
            return None
        return self.stages[self.stages.index(bonus) + 1]


class PokemonPPCapacity:
    """Serialize model-level capacity and current PP writes without inventory."""

    @staticmethod
    def apply(pokemon, name, *, maximize=False):
        """Increase an unambiguous learned move; propagate persistence failures."""
        from django.db import transaction
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, Move, MovePPBoost

        with transaction.atomic():
            # All PP-capacity writers share the owned row, including callers
            # outside +use. Field use already holds storage/trainer/owned locks.
            OwnedPokemon.objects.select_for_update().filter(pk=pokemon.pk).values("pk").get()
            from pokemon.services.necrozma_moves import pair_for_model

            pair_for_model(pokemon, "pp")
            matches = [move for move in Move.objects.filter(pokemonlearnedmove__pokemon_id=pokemon.pk)
                       if normalize_name(move.name) == normalize_name(name)]
            if len(matches) != 1:
                return False
            move = matches[0]
            policy = PPCapacity.for_move(move.name)
            boost = MovePPBoost.objects.select_for_update().filter(pokemon_id=pokemon.pk, move=move).first()
            bonus = boost.bonus_pp if boost else 0
            increased = policy.increased_bonus(bonus, maximize=maximize)
            if increased is None:
                return False
            slots = list(ActiveMoveslot.objects.select_for_update().filter(pokemon_id=pokemon.pk, move=move))
            old_max = policy.base + bonus
            for slot in slots:
                current = old_max if slot.current_pp is None else slot.current_pp
                if not 0 <= current <= old_max:
                    raise ValueError("Invalid saved current PP; contact staff. No item was consumed.")
                slot.current_pp = current + increased - bonus
            if boost is None:
                MovePPBoost.objects.create(pokemon_id=pokemon.pk, move=move, bonus_pp=increased)
            else:
                boost.bonus_pp = increased
                boost.save(update_fields=["bonus_pp"])
            ActiveMoveslot.objects.bulk_update(slots, ["current_pp"])
            pokemon.__dict__.pop("_prefetched_objects_cache", None)
            return True
