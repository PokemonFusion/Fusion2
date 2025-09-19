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


def pokemon_is_usable(pokemon) -> bool:
        """Return ``True`` if ``pokemon`` is conscious and able to battle."""

        if not pokemon:
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
        return any(pokemon_is_usable(mon) for mon in party)
