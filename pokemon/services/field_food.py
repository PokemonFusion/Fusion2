"""Healing foods/drinks and revival equivalents using shared field medicine."""

from pokemon.items import FIELD_RECOVERY_ITEMS
from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class _FoodMedicineUse(BattleMedicineUse):
    """Reuse durable medicine effects without adding battle item support."""

    healing = {key: item.amount for key, item in FIELD_RECOVERY_ITEMS.items() if item.effect == "heal"}
    statuses = {key: BattleMedicineUse.statuses["fullheal"]
                for key, item in FIELD_RECOVERY_ITEMS.items() if item.effect == "status"}
    revivals = {key for key, item in FIELD_RECOVERY_ITEMS.items() if item.effect == "revive"}
    herbs = {}
    pp_items = {}


class FieldFoodUse(FieldMedicineUse):
    """Keep all targeting, locking and rollback inside the field service."""

    selected_move_items = set()

    @classmethod
    def supports(cls, item):
        """Recognize only the fourteen reviewed field recovery definitions."""
        return normalize_name(item) in FIELD_RECOVERY_ITEMS

    def _targets(self, storage, query, item):
        """Sacred Ash targets the canonical party, excluding eggs and Fusion."""
        definition = FIELD_RECOVERY_ITEMS[normalize_name(item)]
        if definition.target_scope != "party":
            return super()._targets(storage, query, item)
        if query.strip().casefold() != "party":
            raise FieldMedicineError("Use +use Sacred Ash=party to revive your eligible party members.")
        return list(storage.placements.filter(location_type="party", pokemon__is_egg=False)
                    .order_by("pokemon_id").values_list("pokemon_id", flat=True))

    def _apply_targets(self, item, pokemon_targets, trainer, *, move=None):
        """Share one inventory debit across an atomic whole-party revival."""
        if FIELD_RECOVERY_ITEMS[normalize_name(item)].target_scope != "party":
            return super()._apply_targets(item, pokemon_targets, trainer, move=move)
        consumed = None

        def consume_once():
            """Debit only on the first effective revival, including failed debits."""
            nonlocal consumed
            if consumed is None:
                consumed = trainer.remove_item(item)
            return consumed

        used = False
        for pokemon in pokemon_targets:
            used = self._medicine(item, pokemon, trainer, consume_once) or used
        return used

    @staticmethod
    def _medicine(item, pokemon, trainer, consume):
        """Build the normal saved-state snapshot and apply the shared effect."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        snapshot = build_battle_pokemon_from_model(pokemon)
        return _FoodMedicineUse(snapshot, trainer).use(item, consume)

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Single-target equivalents retain the same one-item transaction."""
        return self._medicine(item, pokemon, trainer, lambda: trainer.remove_item(item))
