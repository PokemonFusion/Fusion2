"""Explicit PF2 flavor-food equivalents through shared field item checks."""

from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.field_berries import FieldBerryUse
from pokemon.services.field_progression import FieldProgressionUse


SNACK_BERRIES = (
    "Razz Berry",
    "Bluk Berry", "Nanab Berry", "Pinap Berry", "Wepear Berry",
    "Cornn Berry", "Magost Berry", "Nomel Berry", "Rabuta Berry",
    "Belue Berry", "Durin Berry", "Pamtre Berry", "Spelon Berry", "Watmel Berry",
)


class SnackMedicine(BattleMedicineUse):
    """Reuse existing healing persistence without granting any battle/held effect."""

    healing = {normalize_name(item): 10 for item in SNACK_BERRIES}
    fractions = {}
    statuses = {}
    pp_items = {}
    revivals = set()
    herbs = {}


class BerrySnack(FieldProgressionUse):
    """Retain fresh targets, atomic debits, rollback resync and after-commit notices."""

    selected_move_items = set()
    names = {normalize_name(item): item for item in SNACK_BERRIES}

    @classmethod
    def canonical_name(cls, item):
        """Resolve only the explicitly selected snack names, never a berry suffix."""
        return cls.names.get(normalize_name(item))

    @classmethod
    def supports(cls, item):
        """Never infer another flavor berry's support from its name."""
        return cls.canonical_name(item) is not None

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Feed a real bag copy to an eligible living target, with no side effects."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        snapshot = build_battle_pokemon_from_model(pokemon)
        return SnackMedicine(snapshot, trainer).use(item, lambda: FieldBerryUse._consume(trainer, item))
