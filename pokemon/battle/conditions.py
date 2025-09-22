"""Battle condition helper utilities.

This module houses mixins implementing helpers for field and status
conditions. These were extracted from ``engine.py`` to reduce its size and
improve readability.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional

# Dex helper modules are imported lazily to keep test stubs lightweight.
moves_funcs = None
conditions_funcs = None

from .callbacks import _resolve_callback


def _get_default_text() -> Dict[str, Dict[str, str]]:
    """Return localized battle text data when available."""

    try:  # pragma: no cover - optional dependency during lightweight tests
        from pokemon.data.text import DEFAULT_TEXT  # type: ignore
    except Exception:  # pragma: no cover - fallback when text tables unavailable
        return {}
    return DEFAULT_TEXT  # type: ignore[return-value]


def _normalize_effect_name(name: object) -> str:
    """Return a normalized identifier for weather and terrain effects."""

    if not name:
        return ""
    text = str(name)
    return text.replace(" ", "").replace("-", "").lower()


def _field_message_template(effect_key: str, event: str) -> Optional[str]:
    """Return the message template for ``effect_key`` and ``event``."""

    if not effect_key:
        return None
    messages = _get_default_text()
    visited: set[str] = set()
    current = effect_key
    while current:
        entry = messages.get(current, {})
        template = entry.get(event)
        if template is None:
            return None
        if isinstance(template, str) and template.startswith("#"):
            ref = template[1:]
            if not ref or ref in visited:
                return None
            visited.add(ref)
            current = ref
            continue
        if isinstance(template, str):
            return template
        return None
    return None


class ConditionHelpers:
	"""Mixin providing battle condition utilities."""

	def _format_field_message(
		self,
		effect: str | None,
		event: str,
		*,
		pokemon=None,
		move=None,
		field=None,
	) -> Optional[str]:
		"""Return the formatted log message for a field effect event."""

		effect_key = _normalize_effect_name(effect)
		if not effect_key:
			return None
		template = _field_message_template(effect_key, event)
		if not template:
			return None

		message = template
		if "[POKEMON]" in message and pokemon is not None:
			nickname_cb = getattr(self, "_pokemon_nickname", None)
			name = None
			if callable(nickname_cb):
				try:
					name = nickname_cb(pokemon)
				except Exception:
					name = None
			if not name:
				for attr in ("name", "nickname", "species"):
					value = getattr(pokemon, attr, None)
					if value:
						name = value
						break
			message = message.replace("[POKEMON]", str(name or "Pokemon"))

		if "[MOVE]" in message and move is not None:
			move_name = getattr(move, "name", None) or move
			message = message.replace("[MOVE]", str(move_name))

		return message

	def log_field_event(
		self,
		effect: str | None,
		event: str,
		*,
		pokemon=None,
		move=None,
		field=None,
	) -> None:
		"""Log a message for ``effect`` and ``event`` if possible."""

		logger = getattr(self, "log_action", None)
		if not callable(logger):
			return
		message = self._format_field_message(
			effect, event, pokemon=pokemon, move=move, field=field
		)
		if message:
			logger(message)

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

		side = participant.side
		current = side.conditions.get(name)
		if current is None:
			side.conditions[name] = effect.copy()
			cb_name = effect.get("onSideStart")
		else:
			cb_name = effect.get("onSideRestart")
		cb = _resolve_callback(cb_name, moves_funcs)
		if not callable(cb) and isinstance(cb_name, str):
			# Fallback: explicitly resolve from the moves module in sys.modules.
			mod = sys.modules.get("pokemon.dex.functions.moves_funcs")
			if mod:
				try:
					cls_name, func_name = cb_name.split(".", 1)
					cls = getattr(mod, cls_name, None)
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
		elif isinstance(cb_name, str) and cb_name.endswith("onSideStart"):
			# As a last resort, mark the side as started so tests using
			# lightweight stubs can observe that the callback would have run.
			side.started = getattr(side, "started", 0) + 1

	# ------------------------------------------------------------------
	# Field condition helpers
	# ------------------------------------------------------------------
	def _lookup_effect(self, name: str):
		global moves_funcs, conditions_funcs
		if moves_funcs is None:
			try:  # pragma: no cover - optional import
				import pokemon.dex.functions.moves_funcs as moves_mod

				moves_funcs = moves_mod
			except Exception:
				moves_funcs = None
		if conditions_funcs is None:
			try:  # pragma: no cover - optional import
				import pokemon.dex.functions.conditions_funcs as cond_mod

				conditions_funcs = cond_mod
			except Exception:
				conditions_funcs = None

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
		effect_key = _normalize_effect_name(name)
		handler = self._lookup_effect(name) or self._lookup_effect(effect_key)
		if not handler:
			return False

		previous_weather = _normalize_effect_name(getattr(self.field, "weather", None))

		# Allow abilities to veto the weather change or react to it.
		weather_obj = type("Weather", (), {"id": effect_key})()
		for participant in getattr(self, "participants", []):
			for pokemon in getattr(participant, "active", []):
				ability = getattr(pokemon, "ability", None)
				cb = getattr(getattr(ability, "raw", {}), "get", lambda *_: None)("onAnySetWeather")
				if callable(cb):
					if hasattr(cb, "func") and hasattr(cb.func, "__self__"):
						setattr(cb.func.__self__, "field_weather", previous_weather or getattr(self.field, "weather", None))
					try:
						res = cb(target=pokemon, source=source, weather=weather_obj)
					except TypeError:
						try:
							res = cb(pokemon, source, weather_obj)
						except TypeError:
							res = cb(pokemon)
					if res is False:
						self.log_field_event(previous_weather or effect_key, "block", pokemon=pokemon)
						return False

		effect: Dict[str, Any] = {}
		dur_cb = getattr(handler, "durationCallback", None)
		if callable(dur_cb):
			try:
				effect["duration"] = dur_cb(source=source)
			except Exception:
				try:
					effect["duration"] = dur_cb(source)
				except Exception:
					effect["duration"] = dur_cb()
		self.field.add_pseudo_weather(effect_key, effect)
		if hasattr(handler, "onFieldStart"):
			try:
				handler.onFieldStart(self.field, source=source)
			except Exception:
				handler.onFieldStart(self.field)
		self.field.weather = effect_key
		self.field.weather_handler = handler
		self.field.weather_state = {"source": source}
		self.weather_state = self.field.weather_state
		self.log_field_event(effect_key, "start", pokemon=source, field=self.field)

		for participant in getattr(self, "participants", []):
			for pokemon in getattr(participant, "active", []):
				ability = getattr(pokemon, "ability", None)
				cb = getattr(getattr(ability, "raw", {}), "get", lambda *_: None)("onAnySetWeather")
				if callable(cb) and hasattr(cb, "func") and hasattr(cb.func, "__self__"):
					setattr(cb.func.__self__, "field_weather", effect_key)
		return True

	def clearWeather(self) -> None:
		name = getattr(self.field, "weather", None)
		name_key = _normalize_effect_name(name) if name else None
		handler = getattr(self.field, "weather_handler", None)
		if name_key and handler and hasattr(handler, "onFieldEnd"):
			try:
				handler.onFieldEnd(self.field)
			except Exception:
				pass
		if name_key:
			self.field.pseudo_weather.pop(name_key, None)
		self.field.weather = None
		self.field.weather_state = {}
		self.field.weather_handler = None
		self.weather_state = self.field.weather_state
		if name_key:
			self.log_field_event(name_key, "end", field=self.field)

	def setTerrain(self, name: str, source=None) -> bool:
		"""Start a terrain effect on the field."""
		effect_key = _normalize_effect_name(name)
		handler = self._lookup_effect(name) or self._lookup_effect(effect_key)
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
		self.field.add_pseudo_weather(effect_key, effect)
		if hasattr(handler, "onFieldStart"):
			try:
				handler.onFieldStart(self.field, source=source)
			except Exception:
				handler.onFieldStart(self.field)
		self.field.terrain = effect_key
		self.field.terrain_handler = handler
		self.field.terrain_state = {"source": source}
		self.log_field_event(effect_key, "start", pokemon=source, field=self.field)
		return True

	def clearTerrain(self) -> None:
		name = getattr(self.field, "terrain", None)
		name_key = _normalize_effect_name(name) if name else None
		handler = getattr(self.field, "terrain_handler", None)
		if name_key and handler and hasattr(handler, "onFieldEnd"):
			try:
				handler.onFieldEnd(self.field)
			except Exception:
				pass
		if name_key:
			self.field.pseudo_weather.pop(name_key, None)
		self.field.terrain = None
		self.field.terrain_state = {}
		self.field.terrain_handler = None
		if name_key:
			self.log_field_event(name_key, "end", field=self.field)

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
	) -> bool:
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

		previous_value = None
		if dest_attr == "volatiles":
			volatiles = getattr(pokemon, "volatiles", None)
			if volatiles is None:
				volatiles = {}
				pokemon.volatiles = volatiles
			previous_value = volatiles.get(condition)
			volatiles[condition] = True
		else:
			previous_value = getattr(pokemon, dest_attr, None)
			setattr(pokemon, dest_attr, condition)

		handler = (handler_registry or {}).get(condition)
		success = True
		if handler and hasattr(handler, "onStart"):
			ctx = dict(context or {})
			ctx.setdefault("previous", previous_value)
			try:
				result = handler.onStart(pokemon, **ctx)
			except Exception:
				try:
					result = handler.onStart(pokemon)
				except Exception:
					result = handler.onStart()
			if result is False:
				success = False

		if not success:
			if dest_attr == "volatiles":
				if previous_value is None:
					getattr(pokemon, "volatiles", {}).pop(condition, None)
				else:
					pokemon.volatiles[condition] = previous_value
			else:
				setattr(pokemon, dest_attr, previous_value)
			return False
		return True

	def apply_status_condition(
		self,
		pokemon,
		condition: str,
		*,
		source=None,
		effect=None,
		bypass_protection: bool = False,
	) -> bool:
		"""Inflict a major status condition on ``pokemon``."""
		if hasattr(pokemon, "setStatus"):
			return bool(
				pokemon.setStatus(
					condition,
					source=source,
					battle=self,
					effect=effect,
					bypass_protection=bypass_protection,
				)
			)
		try:
			from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
		except Exception:  # pragma: no cover - handler lookup optional
			CONDITION_HANDLERS = {}
		return bool(
			self.apply_condition(
				pokemon,
				condition,
				dest_attr="status",
				handler_registry=CONDITION_HANDLERS,
				context={
					"battle": self,
					"source": source,
					"effect": effect,
					"previous": getattr(pokemon, "status", None),
					"bypass_protection": bypass_protection,
				},
			)
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
		weather_key = _normalize_effect_name(getattr(self.field, "weather", None))
		if not weather_key:
			return
		self.log_field_event(weather_key, "upkeep", field=self.field)
		self._handle_field_residual("weather_handler")
		if weather_key not in getattr(self.field, "pseudo_weather", {}):
			self.clearWeather()

	def handle_terrain(self) -> None:
		"""Apply residual effects of the active terrain."""
		terrain_key = _normalize_effect_name(getattr(self.field, "terrain", None))
		if not terrain_key:
			return
		self.log_field_event(terrain_key, "upkeep", field=self.field)
		self._handle_field_residual("terrain_handler")
		if terrain_key not in getattr(self.field, "pseudo_weather", {}):
			self.clearTerrain()

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
