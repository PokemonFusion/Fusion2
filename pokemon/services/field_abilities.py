"""Canonical native-slot field use for existing ability-changing items."""

from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class FieldAbilityUse(FieldMedicineUse):
    """Change one legal ability name and debit one bag item atomically."""

    selected_move_items = set()

    @classmethod
    def supports(cls, item):
        """Allow only the two existing ability consumables."""
        return normalize_name(item) in {"abilitycapsule", "abilitypatch"}

    @staticmethod
    def _slots(pokemon):
        """Read exact saved species/form slots without nickname or form fallback."""
        from pokemon.data.evolution import lookup_species

        data = lookup_species(pokemon.species)
        if data is None:
            raise FieldMedicineError("Unknown saved species/form; no ability item was consumed.")
        raw = data.raw
        native = normalize_name(raw.get("baseSpecies") or data.name)
        cached_native = getattr(pokemon, "base_species", None)
        if (getattr(pokemon, "transformed", False)
                or cached_native and normalize_name(cached_native) not in {
                    native, normalize_name(data.name)
                }
                or any(raw.get(key) for key in (
                    "battleOnly", "requiredAbility", "requiredItem", "requiredItems"
                )) or raw.get("gender") in {"M", "F"} and pokemon.gender != raw["gender"]):
            raise FieldMedicineError("That transformed or locked form cannot use ability items.")
        slots = raw.get("abilities", {})
        if (not isinstance(slots, dict) or "0" not in slots or set(slots) - {"0", "1", "H", "S"}
                or any(not isinstance(name, str) or not normalize_name(name) for name in slots.values())):
            raise FieldMedicineError("Invalid species ability slots; no item was consumed.")
        return slots

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Use SV ordinary-slot Capsule and reversible hidden/slot-0 Patch rules."""
        slots = self._slots(pokemon)
        current = normalize_name(pokemon.ability)
        matches = [slot for slot, name in slots.items() if normalize_name(name) == current]
        if len(matches) != 1:
            raise FieldMedicineError("Saved ability is foreign or ambiguous for this species/form; no item was consumed.")
        slot = matches[0]
        if normalize_name(item) == "abilitycapsule":
            destination = {"0": "1", "1": "0"}.get(slot)
        else:
            destination = {"0": "H", "1": "H", "H": "0"}.get(slot)
        ability = slots.get(destination)
        if not ability or normalize_name(ability) == current:
            return False
        if sum(normalize_name(name) == normalize_name(ability) for name in slots.values()) != 1:
            raise FieldMedicineError("Destination ability slot is ambiguous; no item was consumed.")
        if not trainer.remove_item(item):
            raise FieldMedicineError("The ability item could not be consumed. Nothing was changed.")
        old_ability = slots[slot]
        pokemon.ability = ability
        pokemon.save(update_fields=["ability"])
        self.change = (old_ability, ability)
        return True

    def success_message(self, item, target):
        """Show the committed legal transition without rereading mutable state."""
        old, new = self.change
        return f"Used {item} on {target}: {old} -> {new}."
