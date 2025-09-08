"""Adapter producing battle start snapshots for trainers and Pokémon."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from pokemon.models.core import ActiveMoveslot, OwnedPokemon
from pokemon.models.stats import calculate_stats
from pokemon.models.storage import ActivePokemonSlot, UserStorage


class SnapshotAdapter:
    """Build battle-ready snapshots from persistent Pokémon data."""

    STAT_KEYS = [
        "hp",
        "attack",
        "defense",
        "special_attack",
        "special_defense",
        "speed",
    ]

    @staticmethod
    def _stat_list(source: Any) -> List[int]:
        """Return a six-length list of stats from ``source``.

        Parameters
        ----------
        source:
            Any structure containing stat information. Supported formats are a
            list/tuple, dictionary or an object with stat attributes.
        """
        if isinstance(source, (list, tuple)):
            vals = list(source)[:6]
            return [int(v) for v in vals] + [0] * (6 - len(vals))
        if isinstance(source, dict):
            return [int(source.get(k, 0)) for k in SnapshotAdapter.STAT_KEYS]
        return [
            int(getattr(source, "hp", 0)),
            int(getattr(source, "atk", getattr(source, "attack", 0))),
            int(
                getattr(source, "def_", getattr(source, "def", getattr(source, "defense", 0)))
            ),
            int(
                getattr(
                    source,
                    "spa",
                    getattr(source, "special_attack", 0),
                )
            ),
            int(
                getattr(
                    source,
                    "spd",
                    getattr(source, "special_defense", 0),
                )
            ),
            int(getattr(source, "spe", getattr(source, "speed", 0))),
        ]

    @staticmethod
    def _display_name(mon: OwnedPokemon) -> str:
        """Return nickname/species composite or species when no nickname."""

        nickname = (getattr(mon, "nickname", "") or "").strip()
        species = (getattr(mon, "species", "") or "").strip()
        if nickname and nickname.lower() != species.lower():
            return f"{nickname} ({species})"
        return nickname or species or "?"

    @classmethod
    def pokemon(cls, mon: OwnedPokemon) -> Dict[str, Any]:
        """Return a snapshot dictionary for ``mon``."""

        level = getattr(mon, "level", None) or getattr(mon, "computed_level", 1)
        ivs_list = cls._stat_list(getattr(mon, "ivs", None))
        evs_list = cls._stat_list(getattr(mon, "evs", None))
        ivs = dict(zip(cls.STAT_KEYS, ivs_list))
        evs = dict(zip(cls.STAT_KEYS, evs_list))

        try:
            stats = calculate_stats(
                getattr(mon, "species", ""), level, ivs, evs, getattr(mon, "nature", "Hardy")
            )
        except Exception:
            stats = {key: 0 for key in cls.STAT_KEYS}

        # Gather moves ordered by slot
        move_data: List[Dict[str, Any]] = []
        slots = getattr(mon, "activemoveslot_set", None)
        if slots is not None:
            try:
                iterable: Iterable[ActiveMoveslot] = slots.order_by("slot").all()
            except Exception:
                try:
                    iterable = sorted(slots.all(), key=lambda s: getattr(s, "slot", 0))
                except Exception:
                    iterable = sorted(list(slots), key=lambda s: getattr(s, "slot", 0))
            for slot in iterable:
                move_name = getattr(getattr(slot, "move", None), "name", "")
                move_data.append(
                    {
                        "name": move_name,
                        "current_pp": getattr(slot, "current_pp", None),
                    }
                )

        snapshot: Dict[str, Any] = {
            "unique_id": str(getattr(mon, "unique_id", "")),
            "display_name": cls._display_name(mon),
            "species": getattr(mon, "species", ""),
            "level": level,
            "ability": getattr(mon, "ability", ""),
            "nature": getattr(mon, "nature", ""),
            "gender": getattr(mon, "gender", ""),
            "ivs": ivs_list,
            "evs": evs_list,
            "held_item": getattr(mon, "held_item", ""),
            "is_shiny": bool(getattr(mon, "is_shiny", False)),
            "friendship": getattr(mon, "friendship", 0),
            "tera_type": getattr(mon, "tera_type", ""),
            "flags": list(getattr(mon, "flags", []) or []),
            "current_hp": getattr(mon, "current_hp", 0),
            "moves": move_data,
            "stats": stats,
        }
        return snapshot

    @classmethod
    def party(cls, storage: UserStorage) -> List[Dict[str, Any]]:
        """Return ordered snapshots for all active Pokémon in ``storage``."""

        results: List[Dict[str, Any]] = []
        slots_rel = getattr(storage, "active_slots", None)
        if not slots_rel:
            return results
        try:
            slot_iter: Iterable[ActivePokemonSlot] = slots_rel.order_by("slot").all()
        except Exception:
            try:
                slot_iter = sorted(slots_rel.all(), key=lambda s: getattr(s, "slot", 0))
            except Exception:
                slot_iter = sorted(list(slots_rel), key=lambda s: getattr(s, "slot", 0))
        for rel in slot_iter:
            mon = getattr(rel, "pokemon", None)
            if not mon:
                continue
            snap = cls.pokemon(mon)
            snap["slot"] = getattr(rel, "slot", None)
            results.append(snap)
        return results


__all__ = ["SnapshotAdapter"]
