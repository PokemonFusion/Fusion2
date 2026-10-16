"""Transfer durable major conditions without retaining battle-only effects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistentStatus:
    """A major condition and its remaining sleep turns across battles."""

    status: str = ""
    sleep_turns: int | None = None

    @classmethod
    def from_pokemon(cls, pokemon, *, battle: bool = False) -> "PersistentStatus":
        """Read model fields or live battle state, excluding volatile effects."""
        status = str(getattr(pokemon, "status", "") or "").strip().lower()
        if status not in {"brn", "psn", "tox", "par", "slp", "frz"}:
            return cls()
        turns = None
        if status == "slp":
            if battle:
                turns = (getattr(pokemon, "tempvals", {}) or {}).get("sleep_turns")
            else:
                turns = getattr(pokemon, "sleep_turns", None)
            # Older/incomplete adapters may lack a counter. Keep sleep finite.
            turns = max(0, min(3, int(turns))) if turns is not None else 1
        return cls(status, turns)

    def apply_to_model(self, pokemon) -> None:
        """Set durable fields on a stored Pokémon or compatible adapter."""
        if hasattr(pokemon, "status"):
            pokemon.status = self.status
        if hasattr(pokemon, "sleep_turns"):
            pokemon.sleep_turns = self.sleep_turns

    def apply_to_battle(self, pokemon) -> None:
        """Restore an existing condition without inflicting or rerolling it."""
        pokemon.status = self.status or 0
        pokemon.status_state = {"id": self.status} if self.status else {}
        # Toxic damage escalates within a battle, not across new battles.
        pokemon.toxic_counter = 1 if self.status == "tox" else 0
        pokemon.tempvals.pop("sleep_turns", None)
        if self.sleep_turns is not None:
            pokemon.tempvals["sleep_turns"] = self.sleep_turns
