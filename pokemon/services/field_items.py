"""Owner-validated field entry point for the existing medicine effects."""

from pokemon.names import normalize_name
from pokemon.services.battle_items import BattleMedicineUse
from pokemon.services.placement import PlacementError, PlacementService
from utils.locks import require_no_battle_lock


class FieldMedicineError(ValueError):
    """A field use was rejected without consuming an item."""


class FieldMedicineUse:
    """Resolve canonical targets and serialize placement, inventory and effects."""

    def __init__(self, caller):
        """Bind the character, never a client-provided trainer or Pokemon."""
        self.caller = caller

    selected_move_items = {"ether", "maxether"}

    @classmethod
    def supports(cls, item):
        """Share the battle medicine allowlist without adding new item families."""
        return BattleMedicineUse.supports(item)

    def _target(self, storage, query):
        """Match a real party slot, exact name/UUID, or the current Fusion."""
        placements = list(storage.placements.filter(
            location_type__in=["party", "fusion"]
        ).order_by("slot", "pk").values(
            "pokemon_id", "location_type", "slot", "pokemon__nickname", "pokemon__species"
        ))
        fusion_id = str(getattr(self.caller.db, "fusion_id", ""))
        eligible = [p for p in placements if p["location_type"] == "party"
                    or str(p["pokemon_id"]) == fusion_id]
        text = query.strip()
        key = normalize_name(text)
        if not key:
            raise FieldMedicineError("Specify a Pokemon target.")
        if text.isdigit():
            matches = [p for p in eligible if p["location_type"] == "party" and p["slot"] == int(text)]
        elif key in {"fusion", "self", "me"}:
            matches = [p for p in eligible if p["location_type"] == "fusion"]
        else:
            matches = [p for p in eligible if key in {
                normalize_name(p["pokemon__nickname"]), normalize_name(p["pokemon__species"]),
                normalize_name(str(p["pokemon_id"])),
            }]
        if len(matches) > 1:
            raise FieldMedicineError("That Pokemon name is ambiguous; use its party slot or full ID.")
        if not matches:
            raise FieldMedicineError("Choose an owned party Pokemon by slot, name or full ID, or your current Fusion.")
        return matches[0]["pokemon_id"]

    def _targets(self, storage, query, item):
        """Resolve one target by default; party medicines override the selection."""
        return [self._target(storage, query)]

    @staticmethod
    def _refresh(pokemon, row):
        """Bypass Evennia's identity map and discard stale derived relations."""
        for name, value in row.items():
            setattr(pokemon, name, value)
        pokemon._state.fields_cache.clear()
        for attr in ("_cached_stats", "_types_override", "_prefetched_objects_cache"):
            pokemon.__dict__.pop(attr, None)

    def use(self, item, target, *, move=None):
        """Apply one fresh, atomic field use; return success, no effect, or a guard."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        if not self.supports(item):
            raise FieldMedicineError("That item cannot be used in the field.")
        if move is not None and normalize_name(item) not in self.selected_move_items:
            raise FieldMedicineError("That item does not accept a move selector.")
        pokemon_targets = []
        try:
            storage = UserStorage.objects.get(user_id=self.caller.pk)
            with PlacementService(storage).locked() as storage:
                trainer = Trainer.objects.select_for_update().get(user_id=storage.user_id)
                if not require_no_battle_lock(self.caller):
                    return None
                for identifier in self._targets(storage, target, item):
                    row = OwnedPokemon.objects.select_for_update().filter(pk=identifier).values().get()
                    pokemon = OwnedPokemon.objects.get(pk=identifier)
                    self._refresh(pokemon, row)
                    pokemon_targets.append(pokemon)
                    pokemon, placement = PlacementService(storage)._pokemon(pokemon, storage)
                    if pokemon.trainer_id != trainer.pk or pokemon.is_egg:
                        raise FieldMedicineError("Field items require an eligible owned party Pokemon; eggs cannot use them.")
                    if placement is None or placement.location_type not in {"party", "fusion"}:
                        raise FieldMedicineError("That Pokemon is no longer in your party or current Fusion.")
                if not trainer.has_item(item):
                    raise FieldMedicineError("You don't have any of that item to use.")
                return self._apply_targets(item, pokemon_targets, trainer, move=move)
        except (UserStorage.DoesNotExist, Trainer.DoesNotExist,
                OwnedPokemon.DoesNotExist, PlacementError) as error:
            raise FieldMedicineError("That Pokemon is no longer an eligible owned party member.") from error
        finally:
            # atomic() rolls back rows, not shared Evennia model instances.
            for pokemon in pokemon_targets:
                row = OwnedPokemon.objects.filter(pk=pokemon.pk).values().first()
                if row is not None:
                    self._refresh(pokemon, row)
                    OwnedPokemon.cache_instance(pokemon)

    def _apply_targets(self, item, pokemon_targets, trainer, *, move=None):
        """Preserve the existing single-target effect dispatch by default."""
        return bool(pokemon_targets) and self._apply(item, pokemon_targets[0], trainer, move=move)

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Reuse medicine effects only after the shared field checks and locks."""
        from utils.pokemon_utils import build_battle_pokemon_from_model

        snapshot = build_battle_pokemon_from_model(pokemon)
        return BattleMedicineUse(snapshot, trainer, move=move).use(
            item, lambda: trainer.remove_item(item)
        )
