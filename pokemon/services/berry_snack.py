"""One deliberate PF2 Razz food equivalent through shared field item checks."""

from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.field_berries import FieldBerryUse
from pokemon.services.field_progression import FieldProgressionUse


class RazzMedicine(BattleMedicineUse):
    """Reuse existing healing persistence without granting any battle/held effect."""

    healing = {"razzberry": 10}
    fractions = {}
    statuses = {}
    pp_items = {}
    revivals = set()
    herbs = {}


class BerrySnack(FieldProgressionUse):
    """Retain fresh targets, atomic debits, rollback resync and after-commit notices."""

    selected_move_items = set()

    @classmethod
    def supports(cls, item):
        """Never infer another flavor berry's support from its name."""
        return normalize_name(item) == "razzberry"

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Feed a real bag copy to an eligible living target, with no side effects."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        snapshot = build_battle_pokemon_from_model(pokemon)
        return RazzMedicine(snapshot, trainer).use(item, lambda: FieldBerryUse._consume(trainer, item))
