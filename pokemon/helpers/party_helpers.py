"""Utilities for inspecting a trainer's active Pokémon party."""

from __future__ import annotations

from typing import Iterable, List, Protocol, Sequence


class _SupportsAll(Protocol):
        def all(self) -> Iterable:
                ...


def _iter_party_storage(storage) -> Iterable:
        """Yield Pokémon from ``storage``'s active party.

        The helper gracefully handles bare sequences and simple stand-ins used
        throughout the test-suite.  When the storage object exposes a
        ``get_party`` method it is preferred since it preserves the canonical
        ordering of party slots.
        """

        if storage is None:
                return []
        if hasattr(storage, "get_party"):
                try:
                        return list(storage.get_party())
                except Exception:
                        return []
        active = getattr(storage, "active_pokemon", None)
        if isinstance(active, Sequence):
                return list(active)
        if isinstance(active, _SupportsAll):  # pragma: no cover - best effort
                try:
                        return list(active.all())
                except Exception:
                        pass
        return []


def get_active_party(character) -> List:
        """Return a list of the character's active Pokémon."""

        storage = getattr(character, "storage", None)
        return list(_iter_party_storage(storage))


def get_party_slots(character) -> List:
        """Return six player-facing party positions without closing empty gaps."""

        storage = getattr(character, "storage", None)
        getter = getattr(storage, "get_party_slots", None)
        party = list(getter() if callable(getter) else get_active_party(character))
        return (party + [None] * 6)[:6]


def get_battle_switch_choices(character, roster) -> dict:
        """Map canonical party/Fusion selectors to internal battle roster indices."""
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        if getattr(character, "storage", None) is None:
                return {i: (i, mon) for i, mon in enumerate(roster, 1) if mon is not None}
        party = get_party_slots(character)
        choices = {}
        for slot, model in enumerate(party, 1):
                if model is None:
                        continue
                identifier = str(getattr(model, "unique_id", "") or "")
                for index, mon in enumerate(roster, 1):
                        kind, model_id = parse_pokemon_ref(getattr(mon, "model_id", None))
                        if mon is model or (identifier and kind == "owned" and model_id == identifier):
                                choices[slot] = (index, mon)
                                break
        fusion_id = str(getattr(getattr(character, "db", None), "fusion_id", "") or "")
        if fusion_id:
                for index, mon in enumerate(roster, 1):
                        kind, model_id = parse_pokemon_ref(getattr(mon, "model_id", None))
                        if kind == "owned" and model_id == fusion_id and not any(mon is p for _, p in choices.values()):
                                key = party.index(None) + 1 if None in party else "fusion"
                                choices[key] = (index, mon)
                                break
        return dict(sorted(choices.items(), key=lambda choice: 7 if choice[0] == "fusion" else choice[0]))


def resolve_battle_switch_choice(character, choices, selection):
        """Resolve a canonical slot or the Fusion alias without roster renumbering."""
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        if str(selection).strip().lower() == "fusion":
                fusion_id = str(getattr(getattr(character, "db", None), "fusion_id", "") or "")
                key = next((slot for slot, (_, mon) in choices.items()
                            if parse_pokemon_ref(getattr(mon, "model_id", None)) == ("owned", fusion_id)), "fusion")
        else:
                key = int(selection)
        return choices[key]


def pokemon_is_usable(pokemon) -> bool:
        """Return ``True`` if ``pokemon`` is conscious and able to battle."""

        if not pokemon or getattr(pokemon, "is_egg", False):
                return False
        if getattr(pokemon, "fainted", False) or getattr(pokemon, "is_fainted", False):
                return False
        hp = getattr(pokemon, "current_hp", None)
        if hp is None:
                hp = getattr(pokemon, "hp", None)
        try:
                if hp is not None and hp <= 0:
                        return False
        except TypeError:  # pragma: no cover - defensive for bad stubs
                return False
        return True


def has_usable_pokemon(character) -> bool:
        """Return ``True`` if any party member can participate in battle."""

        party = get_active_party(character)
        try:
                from utils.fusion import get_battle_party_with_fusion

                party = get_battle_party_with_fusion(character, party)
        except Exception:
                pass
        return any(pokemon_is_usable(mon) for mon in party)
