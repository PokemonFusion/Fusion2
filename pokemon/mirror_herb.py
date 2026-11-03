"""Reviewed Generation 9 egg-species data for explicit Mirror Herb teaching."""

from collections.abc import Mapping

from pokemon.names import normalize_name, resolve_dex_entry


class MirrorHerbRuleError(ValueError):
    """The native recipient lacks unambiguous supported egg-move metadata."""


class MirrorHerbRules:
    """Follow exact native pre-evolutions; never borrow a different regional learnset."""

    @staticmethod
    def egg_moves(species):
        """Resolve a bounded verified pre-evolution chain and exact generation-nine egg codes."""
        from pokemon.dex import POKEDEX
        from pokemon.data.learnsets.learnsets import LEARNSETS

        entry, seen = resolve_dex_entry(POKEDEX, species), set()
        for _ in range(6):
            if entry is None or normalize_name(entry.name) in seen:
                raise MirrorHerbRuleError("Native egg-species data needs review; nothing was taught.")
            seen.add(normalize_name(entry.name))
            raw = entry.raw
            if (type(raw.get("num")) is not int or raw["num"] <= 0
                    or raw.get("isNonstandard") in {"CAP", "Custom"}):
                raise MirrorHerbRuleError("This teaching route requires supported native species data.")
            if any(raw.get(key) for key in ("battleOnly", "requiredItem", "requiredItems", "requiredAbility", "changesFrom")):
                raise MirrorHerbRuleError("Battle or item-dependent forms cannot use this teaching route.")
            previous = raw.get("prevo")
            if not previous:
                break
            parent = resolve_dex_entry(POKEDEX, previous)
            if parent is None or normalize_name(entry.name) not in {normalize_name(name) for name in parent.evos}:
                raise MirrorHerbRuleError("Native evolution ancestry needs review; nothing was taught.")
            entry = parent
        else:
            raise MirrorHerbRuleError("Native egg-species ancestry is ambiguous; nothing was taught.")
        record = LEARNSETS.get(normalize_name(entry.name))
        if not isinstance(record, Mapping) or not isinstance(record.get("learnset"), Mapping):
            raise MirrorHerbRuleError("This native egg species has no verified move metadata.")
        learnset = record["learnset"]
        if not any(isinstance(codes, (list, tuple)) and any(code.startswith("9L") for code in codes
                   if isinstance(code, str)) for codes in learnset.values()):
            raise MirrorHerbRuleError("This native egg species needs Generation 9 move data before teaching.")
        egg = frozenset(key for key, codes in learnset.items()
                        if isinstance(codes, (list, tuple)) and "9E" in codes)
        return entry.name, egg
