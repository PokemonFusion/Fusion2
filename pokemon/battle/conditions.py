"""Battle condition helper utilities.

This module houses mixins implementing helpers for field and status
conditions. These were extracted from ``engine.py`` to reduce its size and
improve readability.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

try:  # pragma: no cover - optional dependency during tests
    from pokemon.dex.functions import moves_funcs, conditions_funcs
except Exception:  # pragma: no cover - fall back when modules unavailable
    moves_funcs = None
    conditions_funcs = None


class ConditionHelpers:
    """Mixin providing battle condition utilities."""

    # ------------------------------------------------------------------
    # Side conditions
    # ------------------------------------------------------------------
    def add_side_condition(
        self,
        participant,
        name: str,
        effect: Dict,
        source=None,
        *,
        moves_funcs=None,
    ) -> None:
        """Apply a side condition to ``participant``."""

        moves_funcs = moves_funcs or {}
        side = participant.side
        current = side.conditions.get(name)
        if current is None:
            side.conditions[name] = effect.copy()
            cb = effect.get("onSideStart")
        else:
            cb = effect.get("onSideRestart")
        if isinstance(cb, str) and moves_funcs:
            try:
                cls_name, func_name = cb.split(".", 1)
                cls = getattr(moves_funcs, cls_name, None)
                if cls:
                    cb = getattr(cls(), func_name, None)
            except Exception:
                cb = None
        if callable(cb):
            try:
                cb(side, source)
            except Exception:
                try:
                    cb(side)
                except Exception:
                    cb()

    # ------------------------------------------------------------------
    # Field condition helpers
    # ------------------------------------------------------------------
    def _lookup_effect(self, name: str):
        if not moves_funcs and not conditions_funcs:
            return None

        key = name.replace(" ", "").replace("-", "").lower()
        cls_name = key.capitalize()
        handler = getattr(conditions_funcs, cls_name, None)
        if handler is None:
            handler = getattr(moves_funcs, cls_name, None)
        if handler:
            try:
                return handler()
            except Exception:
                return handler
        return None

    def setWeather(self, name: str, source=None) -> bool:
        """Start a weather effect on the field."""
        handler = self._lookup_effect(name)
        if not handler:
            return False
        effect = {}
        dur_cb = getattr(handler, "durationCallback", None)
        if callable(dur_cb):
            try:
                effect["duration"] = dur_cb(source=source)
            except Exception:
                try:
                    effect["duration"] = dur_cb(source)
                except Exception:
                    effect["duration"] = dur_cb()
        self.field.add_pseudo_weather(name, effect)
        if hasattr(handler, "onFieldStart"):
            try:
                handler.onFieldStart(self.field, source=source)
            except Exception:
                handler.onFieldStart(self.field)
        self.field.weather = name
        self.field.weather_handler = handler
        return True

    def clearWeather(self) -> None:
        name = getattr(self.field, "weather", None)
        handler = getattr(self.field, "weather_handler", None)
        if name and handler and hasattr(handler, "onFieldEnd"):
            try:
                handler.onFieldEnd(self.field)
            except Exception:
                pass
        if name:
            self.field.pseudo_weather.pop(name, None)
        self.field.weather = None
        self.field.weather_state = {}
        self.field.weather_handler = None

    def setTerrain(self, name: str, source=None) -> bool:
        """Start a terrain effect on the field."""
        handler = self._lookup_effect(name)
        if not handler:
            return False
        effect = {}
        dur_cb = getattr(handler, "durationCallback", None)
        if callable(dur_cb):
            try:
                effect["duration"] = dur_cb(source=source)
            except Exception:
                try:
                    effect["duration"] = dur_cb(source)
                except Exception:
                    effect["duration"] = dur_cb()
        self.field.add_pseudo_weather(name, effect)
        if hasattr(handler, "onFieldStart"):
            try:
                handler.onFieldStart(self.field, source=source)
            except Exception:
                handler.onFieldStart(self.field)
        self.field.terrain = name
        self.field.terrain_handler = handler
        return True

    def clearTerrain(self) -> None:
        name = getattr(self.field, "terrain", None)
        handler = getattr(self.field, "terrain_handler", None)
        if name and handler and hasattr(handler, "onFieldEnd"):
            try:
                handler.onFieldEnd(self.field)
            except Exception:
                pass
        if name:
            self.field.pseudo_weather.pop(name, None)
        self.field.terrain = None
        self.field.terrain_state = {}
        self.field.terrain_handler = None

    def apply_entry_hazards(self, pokemon) -> None:
        """Apply entry hazard effects to ``pokemon`` if present."""
        side = getattr(pokemon, "side", None)
        if not side:
            return

        name_map = {
            "rocks": "stealthrock",
            "spikes": "spikes",
            "toxicspikes": "toxicspikes",
            "stickyweb": "stickyweb",
            "steelsurge": "gmaxsteelsurge",
        }

        for name, active in list(side.hazards.items()):
            if not active:
                continue
            effect = name_map.get(name, name)
            handler = None
            if moves_funcs:
                handler = getattr(moves_funcs, effect.capitalize(), None)
                if handler:
                    try:
                        handler = handler()
                    except Exception:
                        pass
            if not handler:
                continue
            cb = getattr(handler, "onEntryHazard", None)
            if callable(cb):
                try:
                    cb(pokemon=pokemon)
                except Exception:
                    try:
                        cb(pokemon)
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Generic battle condition helpers
    # ------------------------------------------------------------------
    def apply_condition(
        self,
        pokemon,
        condition: str,
        *,
        dest_attr: str,
        handler_registry: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generic helper to apply a battle condition to ``pokemon``.

        Parameters
        ----------
        pokemon:
            The target combatant receiving the condition.
        condition:
            Name of the condition being applied.
        dest_attr:
            Attribute on ``pokemon`` used to store the condition (``status`` or
            ``volatiles``).
        handler_registry:
            Mapping of condition names to handler instances.
        context:
            Additional keyword arguments passed to the handler's ``onStart``
            method, if available.
        """

        if dest_attr == "volatiles":
            volatiles = getattr(pokemon, "volatiles", None)
            if volatiles is None:
                volatiles = {}
                pokemon.volatiles = volatiles
            volatiles[condition] = True
        else:
            setattr(pokemon, dest_attr, condition)

        handler = (handler_registry or {}).get(condition)
        if handler and hasattr(handler, "onStart"):
            ctx = context or {}
            try:
                handler.onStart(pokemon, **ctx)
            except Exception:
                try:
                    handler.onStart(pokemon)
                except Exception:
                    handler.onStart()

    def apply_status_condition(self, pokemon, condition: str) -> None:
        """Inflict a major status condition on ``pokemon``."""
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:  # pragma: no cover - handler lookup optional
            CONDITION_HANDLERS = {}
        self.apply_condition(
            pokemon,
            condition,
            dest_attr="status",
            handler_registry=CONDITION_HANDLERS,
            context={"battle": self},
        )

    def apply_volatile_status(self, pokemon, condition: str) -> None:
        """Apply a volatile status to ``pokemon``."""
        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:  # pragma: no cover - handler lookup optional
            VOLATILE_HANDLERS = {}
        self.apply_condition(
            pokemon,
            condition,
            dest_attr="volatiles",
            handler_registry=VOLATILE_HANDLERS,
            context={"battle": self},
        )

    def _handle_field_residual(self, effect_attr: str) -> None:
        """Trigger the :py:meth:`onFieldResidual` callback for a field effect.

        Parameters
        ----------
        effect_attr:
            Name of the attribute on ``self.field`` that stores the handler
            instance.
        """
        handler = getattr(self.field, effect_attr, None)
        if handler and hasattr(handler, "onFieldResidual"):
            try:
                handler.onFieldResidual(self.field)
            except Exception:
                pass

    def handle_weather(self) -> None:
        """Apply residual effects of the current weather."""
        self._handle_field_residual("weather_handler")

    def handle_terrain(self) -> None:
        """Apply residual effects of the active terrain."""
        self._handle_field_residual("terrain_handler")

    def update_hazards(self) -> None:
        """Update hazard effects on the field."""
        for part in self.participants:
            for hazard, data in list(part.side.hazards.items()):
                if isinstance(data, dict):
                    duration = data.get("duration")
                    if duration is not None:
                        data["duration"] = duration - 1
                        if data["duration"] <= 0:
                            part.side.hazards[hazard] = False


__all__ = ["ConditionHelpers"]
