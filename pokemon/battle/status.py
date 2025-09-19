"""Status condition helpers for the battle engine."""
from __future__ import annotations

from typing import Any, Iterable, Optional


class BurnStatus:
    """Implement mechanics for the burn (BRN) status condition."""

    IMMUNE_ABILITIES = {"water veil", "water bubble"}
    IGNORE_HALVING_ABILITIES = {"guts"}
    FACADE_NAMES = {"facade"}

    def _ability_name(self, pokemon) -> str:
        ability = getattr(pokemon, "ability", None)
        if not ability:
            return ""
        name = getattr(ability, "name", ability)
        if isinstance(name, str):
            return name.lower()
        return str(name).lower()

    def _has_ability(self, pokemon, names: Iterable[str]) -> bool:
        ability_name = self._ability_name(pokemon)
        names_lower = {str(n).lower() for n in names}
        return ability_name in names_lower

    def _has_type(self, pokemon, type_name: str) -> bool:
        types = getattr(pokemon, "types", None) or []
        return any(str(t).lower() == type_name.lower() for t in types)

    def _is_grounded(self, pokemon) -> bool:
        if hasattr(pokemon, "is_grounded"):
            try:
                return bool(pokemon.is_grounded())
            except TypeError:
                try:
                    return bool(pokemon.is_grounded(None))
                except Exception:
                    pass
        return bool(getattr(pokemon, "grounded", True))

    def _has_safeguard(self, pokemon) -> bool:
        side = getattr(pokemon, "side", None)
        conditions = getattr(side, "conditions", {}) if side else {}
        for key in conditions.keys():
            if str(key).lower() == "safeguard":
                return True
        return False

    def _has_substitute(self, pokemon) -> bool:
        volatiles = getattr(pokemon, "volatiles", {})
        return "substitute" in {str(k).lower() for k in volatiles.keys()}

    def _effect_is_move(self, effect: Optional[Any]) -> bool:
        if effect is None:
            return False
        if isinstance(effect, str):
            return effect.startswith("move:")
        return hasattr(effect, "name") or hasattr(effect, "category")

    def _terrain(self, battle) -> str:
        if not battle:
            return ""
        field = getattr(battle, "field", None)
        terrain = getattr(field, "terrain", getattr(battle, "terrain", ""))
        return str(terrain or "").lower()

    def _is_self_inflicted(self, pokemon, source, effect: Optional[Any], *, bypass: bool) -> bool:
        if bypass:
            return True
        if source is pokemon and source is not None:
            return True
        if isinstance(effect, str):
            if effect.startswith("item:") or effect.startswith("self:"):
                return True
        return False

    def on_start(
        self,
        pokemon,
        *,
        battle=None,
        source=None,
        effect: Optional[Any] = None,
        previous=None,
        bypass_protection: bool = False,
        **kwargs,
    ) -> bool:
        """Attempt to apply burn to ``pokemon``."""

        if previous not in {None, 0, "", "brn"} and previous != getattr(pokemon, "status", None):
            return False

        if self._has_type(pokemon, "fire"):
            return False

        if self._has_ability(pokemon, self.IMMUNE_ABILITIES):
            return False

        is_self_inflicted = self._is_self_inflicted(
            pokemon, source, effect, bypass=bypass_protection
        )

        if not is_self_inflicted:
            terrain = self._terrain(battle)
            if terrain == "mistyterrain" and self._is_grounded(pokemon):
                return False
            if self._has_safeguard(pokemon):
                return False
            if self._has_substitute(pokemon) and self._effect_is_move(effect):
                return False

        setattr(pokemon, "status", "brn")
        if getattr(pokemon, "status", None) == "tox":
            setattr(pokemon, "toxic_counter", 1)
        else:
            setattr(pokemon, "toxic_counter", 0)
        return True

    def _residual_denominator(self, pokemon) -> int:
        if self._has_ability(pokemon, {"heatproof"}):
            return 32
        return 16

    def on_residual(self, pokemon, *, battle=None) -> int:
        """Apply residual burn damage to ``pokemon``."""

        if not pokemon or getattr(pokemon, "hp", 0) <= 0:
            return 0
        if self._has_ability(pokemon, {"magic guard"}):
            return 0
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 1)) or 1
        denom = self._residual_denominator(pokemon)
        damage = max(1, max_hp // denom)
        pokemon.hp = max(0, getattr(pokemon, "hp", 0) - damage)
        return damage

    def modify_attack(self, atk: int, *, attacker=None, defender=None, move=None):
        """Return the burn-modified Attack stat."""

        if not attacker or getattr(attacker, "status", None) != "brn":
            return atk
        if move is None:
            return atk
        category = getattr(move, "category", None)
        if not category and hasattr(move, "raw"):
            category = move.raw.get("category")
        if str(category or "").lower() != "physical":
            return atk
        if self._has_ability(attacker, self.IGNORE_HALVING_ABILITIES):
            return atk
        move_name = getattr(move, "id", None) or getattr(move, "key", None) or getattr(
            move, "name", ""
        )
        if str(move_name).lower() in self.FACADE_NAMES:
            return atk
        return atk // 2


__all__ = ["BurnStatus"]
