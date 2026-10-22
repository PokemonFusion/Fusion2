"""Owned-target field use for the twelve existing EV training items."""

from django.core.exceptions import ValidationError

from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class FieldTrainingUse(FieldMedicineUse):
    """Serialize useful EV increases with canonical field eligibility and stock."""

    selected_move_items = set()
    increases = {
        "hpup": (0, 10), "protein": (1, 10), "iron": (2, 10),
        "calcium": (3, 10), "zinc": (4, 10), "carbos": (5, 10),
        "healthfeather": (0, 1), "musclefeather": (1, 1),
        "resistfeather": (2, 1), "geniusfeather": (3, 1),
        "cleverfeather": (4, 1), "swiftfeather": (5, 1),
    }

    @classmethod
    def supports(cls, item):
        """Allow only existing vitamins and stat-raising feathers."""
        return normalize_name(item) in cls.increases

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Commit one capped EV increase and its HP adjustment with one debit."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.models.validators import EV_LIMIT, STAT_EV_LIMIT, validate_evs

        try:
            validate_evs(pokemon.evs)
        except ValidationError as error:
            raise FieldMedicineError(
                "Invalid saved EVs; contact staff before using a training item."
            ) from error
        evs = list(pokemon.evs)
        index, amount = self.increases[normalize_name(item)]
        gain = min(amount, STAT_EV_LIMIT - evs[index], EV_LIMIT - sum(evs))
        if gain <= 0:
            return False
        evs[index] += gain
        validate_evs(evs)
        old_max, old_hp = get_max_hp(pokemon), pokemon.current_hp
        if not trainer.remove_item(item):
            raise FieldMedicineError("The training item could not be consumed. Nothing was changed.")
        pokemon.evs = evs
        pokemon.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = (0 if old_hp <= 0 else
                              max(1, min(new_max, old_hp + new_max - old_max)))
        pokemon.save(update_fields=["evs", "current_hp"])
        return True
