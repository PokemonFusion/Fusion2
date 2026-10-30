"""Six field-only recovery equivalents using the existing fresh item boundary."""

from pokemon.items import FIELD_RECOVERY_EQUIVALENTS
from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.field_berries import FieldBerryUse
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class _EquivalentMedicineUse(BattleMedicineUse):
    """Reuse durable status and exact selected-move PP effects without battle enablement."""

    healing = {key: item.amount for key, item in FIELD_RECOVERY_EQUIVALENTS.items() if item.effect == "heal"}
    fractions = {}
    statuses = {key: BattleMedicineUse.statuses["fullheal"]
                for key, item in FIELD_RECOVERY_EQUIVALENTS.items() if item.effect == "status"}
    pp_items = {"hopoberry": (10, False)}
    revivals = set()
    herbs = {key: item.friendship_cost for key, item in FIELD_RECOVERY_EQUIVALENTS.items()
             if item.friendship_cost is not None}


class FieldRecoveryEquivalentUse(FieldMedicineUse):
    """Keep all stock, target, move, ownership and rollback checks in field services."""

    selected_move_items = {"hopoberry"}

    @classmethod
    def supports(cls, item):
        """Recognize only the six complete reviewed supplemental identities."""
        return normalize_name(item) in FIELD_RECOVERY_EQUIVALENTS

    def use(self, item, target, *, move=None):
        """Require an explicit active move rather than choosing a default PP slot."""
        if normalize_name(item) == "hopoberry" and move is None:
            raise FieldMedicineError("Select an active move: +use Hopo Berry=<target>/<move name or slot>.")
        return super().use(item, target, move=move)

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Apply the existing medicine effect with a failure-raising atomic debit."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        snapshot = build_battle_pokemon_from_model(pokemon)
        return _EquivalentMedicineUse(snapshot, trainer, move=move).use(
            item, lambda: FieldBerryUse._consume(trainer, item)
        )
