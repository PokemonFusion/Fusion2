"""Atomic trained stat Nature on a fresh owned field target, preserving genetics."""

from copy import copy

from pokemon.names import normalize_name
from pokemon.nature_training import NatureTraining
from pokemon.services.field_items import FieldMedicineError
from pokemon.services.field_progression import FieldProgressionUse


class FieldMintUse(FieldProgressionUse):
    """Reuse the paid field boundary for exactly21 reviewed Nature preferences."""

    selected_move_items = set()
    preferences = {normalize_name(name + " Mint"): name for name in NatureTraining.mint_names}

    @classmethod
    def supports(cls, item):
        """No generic Mint suffix, neutral extras or Mint Berry fallback."""
        return normalize_name(item) in cls.preferences

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Commit one useful overlay/debit/HP refresh without changing any genetics."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats

        pokemon = copy(pokemon)
        pokemon._state = copy(pokemon._state)
        target = self.preferences[normalize_name(item)]
        if not NatureTraining.useful(pokemon, target):
            return False
        maximum, hp = get_max_hp(pokemon), pokemon.current_hp
        if type(hp) is not int or not 0 <= hp <= maximum:
            raise FieldMedicineError("Invalid saved HP; no mint was consumed.")
        if not trainer.remove_item(item):
            raise FieldMedicineError("The mint could not be consumed. Nothing was changed.")
        pokemon.trained_stat_nature = target
        pokemon.__dict__.pop("_cached_stats", None)
        pokemon.__dict__.pop("_cached_stats_nature", None)
        new_max = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = 0 if hp == 0 else max(1, min(new_max, hp + new_max - maximum))
        pokemon.save(update_fields=["trained_stat_nature", "current_hp"])
        self.result_name, self.result_trained, self.result_genetic = (
            pokemon.name,
            target,
            pokemon.nature,
        )
        return True

    def success_message(self, item, target):
        """Name the paid stat preference and unchanged genetic Nature explicitly."""
        return (
            f"{self.result_name}'s mint stat preference is {self.result_trained}; "
            f"genetic Nature remains {self.result_genetic}."
        )
