"""Explicit field feeding effects for existing recovery and EV berries."""

from django.core.exceptions import ValidationError

from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class _BerryMedicineUse(BattleMedicineUse):
    """Share durable medicine effects without invoking held-item consumption."""

    healing = {"oranberry": 10, "berryjuice": 20, "berry": 10, "goldberry": 30}
    fractions = {
        "sitrusberry": 4,
        "figyberry": 3, "wikiberry": 3, "magoberry": 3,
        "aguavberry": 3, "iapapaberry": 3,
    }
    statuses = {
        "cheriberry": {"par"}, "chestoberry": {"slp"},
        "pechaberry": {"psn", "tox"}, "rawstberry": {"brn"},
        "aspearberry": {"frz"},
        "lumberry": {"brn", "psn", "tox", "frz", "slp", "par"},
        "burntberry": {"frz"}, "iceberry": {"brn"}, "mintberry": {"slp"},
        "miracleberry": {"brn", "psn", "tox", "frz", "slp", "par"},
        "przcureberry": {"par"}, "psncureberry": {"psn", "tox"},
    }
    pp_items = {"leppaberry": (10, False), "mysteryberry": (5, False)}
    revivals = set()
    herbs = {}

    def __init__(self, pokemon, trainer=None, *, move=None):
        """Use the reviewed berries' fixed and fractional recovery amounts."""
        super().__init__(pokemon, trainer, move=move)
        self.healing = {
            **type(self).healing,
            **{key: max(1, pokemon.max_hp // divisor)
               for key, divisor in self.fractions.items()},
        }


class FieldBerryUse(FieldMedicineUse):
    """Feed allowlisted berries through the same owned-target transaction."""

    selected_move_items = {"leppaberry", "mysteryberry"}
    ev_stats = {
        "pomegberry": 0, "kelpsyberry": 1, "qualotberry": 2,
        "hondewberry": 3, "grepaberry": 4, "tamatoberry": 5,
    }

    @classmethod
    def supports(cls, item):
        """Keep combat-trigger and contest-only berries out of generic feeding."""
        key = normalize_name(item)
        return (key in cls.ev_stats or key in _BerryMedicineUse.healing
                or key in _BerryMedicineUse.fractions or key in _BerryMedicineUse.statuses
                or key in _BerryMedicineUse.pp_items)

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Apply either shared medicine recovery or a durable EV/friendship use."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        key = normalize_name(item)
        if key in self.ev_stats:
            return self._reduce_evs(key, pokemon, trainer)
        snapshot = build_battle_pokemon_from_model(pokemon)
        return _BerryMedicineUse(snapshot, trainer, move=move).use(
            key, lambda: self._consume(trainer, key)
        )

    @staticmethod
    def _consume(trainer, item):
        """Roll back a failed debit even if its writer made a partial change."""
        if not trainer.remove_item(item):
            raise FieldMedicineError("The berry could not be consumed. Nothing was changed.")
        return True

    def _reduce_evs(self, item, pokemon, trainer):
        """Remove up to ten EVs and raise friendship once, without reviving."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.models.validators import validate_evs

        evs = list(pokemon.evs)
        try:
            validate_evs(evs)
        except ValidationError as error:
            raise FieldMedicineError("Invalid saved EVs; contact staff before using an EV berry.") from error
        friendship = pokemon.friendship
        if not 0 <= friendship <= 255:
            raise FieldMedicineError("Invalid saved friendship; contact staff before using an EV berry.")
        index = self.ev_stats[item]
        updated = max(0, evs[index] - 10)
        gain = 10 if friendship < 100 else 5 if friendship < 200 else 2
        friendship = min(255, friendship + gain)
        if updated == evs[index] and friendship == pokemon.friendship:
            return False
        self._consume(trainer, item)
        old_max, old_hp = get_max_hp(pokemon), pokemon.current_hp
        evs[index] = updated
        pokemon.evs, pokemon.friendship = evs, friendship
        pokemon.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = (0 if old_hp <= 0 else
                              max(1, min(new_max, old_hp + new_max - old_max)))
        pokemon.save(update_fields=["evs", "friendship", "current_hp"])
        return True
