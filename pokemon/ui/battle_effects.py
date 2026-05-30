"""Effects panel renderer (ANSI-safe, width-aware).

Renders a single-column panel showing:
- Field/global timers (Weather, Terrain, Rooms, etc)
- Side A/B timers & hazards (Screens, Tailwind, Hazards)
- On-field Pokémon: name/meta chips, HP line, stages, timed effects, item/ability

This reuses helpers from battle_render.py to keep visuals consistent.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from pokemon.battle.battledata import _caller_is_admin

# Reuse existing ANSI-safe helpers and theme
from pokemon.ui.battle_render import (
	THEME,
	ansi_len,
	display_name,
	fmt_hp_line,
	gender_chip,
	rpad,
	status_badge,
	viewer_prefers_ascii_symbols,
)
from pokemon.ui.box_utils import render_box

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _timer_chip(name: str, left: Optional[int] = None, total: Optional[int] = None) -> str:
	"""Return a compact timer chip like "⏱ Rain 4/5" or "⏱ Taunt 2t" (when total unknown).
	Skips if no name or no time info."""
	if not name:
		return ""
	if left is None and total is None:
		return name
	if total is not None and left is not None:
		return f"⏱ {name} {left}/{total}"
	if left is not None:
		return f"⏱ {name} {left}t"
	return f"⏱ {name}"


_LABEL_OVERRIDES = {
	"auroraveil": "Aurora Veil",
	"choicelock": "Choice Lock",
	"electricterrain": "Electric Terrain",
	"gmaxsteelsurge": "G-Max Steelsurge",
	"grassyterrain": "Grassy Terrain",
	"lightscreen": "Light Screen",
	"magicroom": "Magic Room",
	"mistyterrain": "Misty Terrain",
	"psychicterrain": "Psychic Terrain",
	"raindance": "Rain",
	"sandstorm": "Sandstorm",
	"stealthrock": "Stealth Rock",
	"stickyweb": "Sticky Web",
	"sunnyday": "Harsh Sunlight",
	"tailwind": "Tailwind",
	"toxicspikes": "Toxic Spikes",
	"trickroom": "Trick Room",
	"wonderroom": "Wonder Room",
}


def _normalize_lookup_key(value: Any) -> str:
	return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _human_label(value: Any) -> str:
	text = str(value or "").strip()
	if not text:
		return ""
	key = _normalize_lookup_key(text)
	if key in _LABEL_OVERRIDES:
		return _LABEL_OVERRIDES[key]
	text = text.replace("_", " ").replace("-", " ")
	text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
	return " ".join(part[:1].upper() + part[1:] for part in text.split())


def _entry_display_name(entry: Any) -> Optional[str]:
	if entry is None:
		return None
	raw = getattr(entry, "raw", None)
	if isinstance(raw, dict):
		name = raw.get("name")
		if name:
			return str(name)
	if isinstance(entry, dict):
		name = entry.get("name") or entry.get("id")
		if name:
			return str(name)
	for attr in ("display_name", "name", "id", "key"):
		name = getattr(entry, attr, None)
		if name:
			return str(name)
	return None


def _lookup_dex_name(value: Any, dex_attr: str) -> Optional[str]:
	text = str(value or "").strip()
	if not text:
		return None
	try:
		from pokemon import dex as dex_mod
	except Exception:  # pragma: no cover - dex is optional in isolated tests
		return None

	dex_map = getattr(dex_mod, dex_attr, {}) or {}
	candidates = [text, text.lower(), text.title(), text.capitalize(), _normalize_lookup_key(text)]
	for candidate in candidates:
		entry = dex_map.get(candidate)
		name = _entry_display_name(entry)
		if name:
			return name

	target_key = _normalize_lookup_key(text)
	if not target_key:
		return None
	for key, entry in dex_map.items():
		entry_name = _entry_display_name(entry)
		if _normalize_lookup_key(key) == target_key or _normalize_lookup_key(entry_name) == target_key:
			return entry_name
	return None


def _object_name(value: Any, *, dex_attr: Optional[str] = None) -> Optional[str]:
	if value is None:
		return None
	if isinstance(value, str):
		text = value.strip()
	else:
		text = _entry_display_name(value) or str(value).strip()
	if not text or text.lower() in {"-", "none", "null", "0"}:
		return None
	if dex_attr:
		dex_name = _lookup_dex_name(text, dex_attr)
		if dex_name:
			return dex_name
	return _human_label(text)


def _pokemon_item_name(mon) -> Optional[str]:
	for attr in ("item_name", "held_item_name", "item", "held_item"):
		if hasattr(mon, attr):
			name = _object_name(getattr(mon, attr, None), dex_attr="ITEMDEX")
			if name:
				return name
	return None


def _pokemon_ability_name(mon) -> Optional[str]:
	for attr in ("ability_name", "ability"):
		if hasattr(mon, attr):
			name = _object_name(getattr(mon, attr, None), dex_attr="ABILITYDEX")
			if name:
				return name
	return None


def _reveal(name: Optional[str], revealed: bool, is_self: bool, *, missing: str = "None") -> str:
	"""Return revealed name, '?' if hidden and not self, or a missing placeholder."""
	if name:
		if revealed or is_self:
			return name
		return "?"
	return missing


def _wrap_tokens(tokens: List[str], width: int) -> List[str]:
	"""Wrap space-separated tokens within width (ANSI-safe)."""
	lines: List[str] = []
	cur = ""
	for tok in tokens:
		tok = tok.strip()
		if not tok:
			continue
		if not cur:
			cur = tok
			continue
		if ansi_len(cur) + 2 + ansi_len(tok) <= width:
			cur = f"{cur}  {tok}"
		else:
			lines.append(cur)
			cur = tok
	if cur:
		lines.append(cur)
	return lines


def _stages_line(boosts: Dict[str, int]) -> str:
	"""Return condensed stat stage string with colors, or '—' if all zero."""
	if not boosts:
		return "—"
	order = (
		(("atk", "attack"), "Atk"),
		(("def", "defense"), "Def"),
		(("spa", "special_attack", "spatk", "specialattack"), "SpA"),
		(("spd", "special_defense", "spdef", "specialdefense"), "SpD"),
		(("spe", "speed"), "Spe"),
		(("accuracy", "acc"), "Acc"),
		(("evasion", "eva"), "Eva"),
	)
	parts: List[str] = []
	for keys, label in order:
		v = 0
		for key in keys:
			v = int(boosts.get(key, 0) or 0)
			if v:
				break
		if v == 0:
			continue
		col = THEME["ok"] if v > 0 else THEME["bad"]
		sign = "+" if v > 0 else ""
		parts.append(f"{col}{label}{sign}{v}|n")
	return " ".join(parts) if parts else "—"


def _hazard_active(hazards: Dict[str, Any], *keys: str) -> bool:
	for key in keys:
		if key in hazards and hazards[key] not in (False, None, 0, ""):
			return True
	return False


def _hazard_count(value: Any) -> int:
	if value in (False, None, 0, ""):
		return 0
	if value is True or isinstance(value, dict):
		return 1
	try:
		return max(0, int(value))
	except (TypeError, ValueError):
		return 1


def _hazards_line(h: Dict[str, int] | None) -> str:
	"""Compact hazards string for a side."""
	if not h:
		return "None"
	parts: List[str] = []
	if _hazard_active(h, "sr", "rocks", "stealthrock"):
		parts.append("SR")
	sp = _hazard_count(h.get("spikes", 0))
	if sp:
		parts.append(f"Spikes×{sp}")
	ts = _hazard_count(h.get("tspikes", h.get("toxicspikes", 0)))
	if ts:
		parts.append(f"TSpikes×{ts}")
	if _hazard_active(h, "web", "stickyweb"):
		parts.append("Web")
	if _hazard_active(h, "steelsurge", "gmaxsteelsurge"):
		parts.append("Steelsurge")
	return " • ".join(parts) if parts else "None"


def _mapping(obj: Any) -> Dict[str, Any]:
	return dict(obj or {}) if isinstance(obj, dict) else {}


def _state_value(state: Any, *keys: str) -> Any:
	if isinstance(state, dict):
		for key in keys:
			if key in state:
				return state[key]
		return None
	for key in keys:
		value = getattr(state, key, None)
		if value is not None:
			return value
	return None


def _effect_turns(state: Any) -> Tuple[Optional[int], Optional[int]]:
	if isinstance(state, int) and not isinstance(state, bool):
		return state, None
	left = _state_value(state, "turns_left", "duration_left", "left", "duration", "turns")
	total = _state_value(state, "total", "duration_total", "max_duration")
	try:
		left = int(left) if left is not None else None
	except (TypeError, ValueError):
		left = None
	try:
		total = int(total) if total is not None else None
	except (TypeError, ValueError):
		total = None
	return left, total


def _format_effect(name: Any, state: Any = None) -> str:
	label = _human_label(_state_value(state, "name", "id") or name)
	if not label:
		return ""
	left, total = _effect_turns(state)
	extra = _state_value(state, "source", "move")
	if isinstance(state, str) and _normalize_lookup_key(state) != _normalize_lookup_key(name):
		extra = state
	if extra:
		label = f"{label}({_human_label(extra)})"
	return _timer_chip(label, left, total)


def _pokemon_effects(mon) -> List[str]:
	effects: List[str] = []
	seen: set[str] = set()

	def add_effect(label: str) -> None:
		key = _normalize_lookup_key(label)
		if label and key not in seen:
			seen.add(key)
			effects.append(label)

	for eff in getattr(mon, "effects", []) or []:
		if isinstance(eff, dict):
			name = eff.get("key") or eff.get("name") or eff.get("id")
			if name:
				add_effect(_format_effect(name, eff))
		else:
			add_effect(_format_effect(eff))

	for key, state in _mapping(getattr(mon, "volatiles", None)).items():
		if state is False or state is None:
			continue
		add_effect(_format_effect(key, state))
	return effects


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class EffectsAdapter:
	"""Lightweight adapter around a battle session/state so the renderer can be robust
	against engine differences. Only the attributes used below are expected."""

	def __init__(self, session, viewer):
		self.session = session
		self.viewer = viewer
		self.state = getattr(session, "state", session)
		logic = getattr(session, "logic", None)
		self.data = getattr(logic, "data", None) or getattr(session, "data", None)
		self.battle = getattr(session, "battle", None) or getattr(logic, "battle", None)
		self.field = (
			getattr(self.battle, "field", None)
			or getattr(self.state, "field", None)
			or self.state
		)

	def title(self) -> str:
		a = getattr(self.session, "captainA", None)
		b = getattr(self.session, "captainB", None)
		enc = (getattr(self.state, "encounter_kind", "") or "").lower()
		left = getattr(a, "name", "?")
		if enc == "wild":
			mon = getattr(getattr(b, "active_pokemon", None), "name", "Wild Pokémon")
			right = f"Wild {mon}"
		else:
			right = getattr(b, "name", "?")
		return f"{THEME['title']}{left}|n {THEME['vs']} {THEME['title']}{right}|n"

	def turn(self) -> int:
		return int(getattr(self.state, "round", getattr(self.state, "turn", 0)) or 0)

	def viewer_role(self) -> str:
		c = self.viewer
		if not c:
			return "W"
		if c in getattr(self.session, "teamA", []) or c == getattr(self.session, "captainA", None):
			return "A"
		if c in getattr(self.session, "teamB", []) or c == getattr(self.session, "captainB", None):
			return "B"
		return "W"

	def _reveal_source(self):
		for source in (self.data, self.battle, self.session):
			if source is not None and hasattr(source, "get_revealed_ability_for_viewer"):
				return source
		return None

	def _admin_reveal_enabled(self) -> bool:
		if self.data is not None:
			return bool(getattr(self.data, "admin_ability_reveal", True))
		if self.battle is not None:
			return bool(getattr(self.battle, "admin_ability_reveal", True))
		getter = getattr(self.session, "get_admin_ability_reveal", None)
		if callable(getter):
			return bool(getter())
		return True

	def ability_display(self, mon, pokemon_side: str, owns_pokemon: bool) -> str:
		"""Return the ability text visible to this viewer."""

		actual = _pokemon_ability_name(mon)
		if owns_pokemon:
			return actual or "None"

		viewer_role = self.viewer_role()
		revealed = None
		source = self._reveal_source()
		if source is not None:
			getter = getattr(source, "get_revealed_ability_for_viewer", None)
			if callable(getter):
				try:
					revealed = getter(viewer_role, mon, pokemon_side=pokemon_side)
				except TypeError:
					revealed = getter(viewer_role, mon)
		if revealed:
			return str(revealed)

		if actual and self._admin_reveal_enabled() and _caller_is_admin(self.viewer):
			return f"{actual} [admin]"
		return "Unknown"

	def monA(self):
		return getattr(getattr(self.session, "captainA", None), "active_pokemon", None)

	def monB(self):
		return getattr(getattr(self.session, "captainB", None), "active_pokemon", None)

	# ---- Field/global ----
	def field_timers(self) -> List[Tuple[str, int | None, int | None]]:
		out: List[Tuple[str, int | None, int | None]] = []
		# Weather
		wname = getattr(self.field, "weather", None) or getattr(self.state, "weather", None)
		if not wname:
			wname = getattr(self.state, "roomweather", None)
		if wname:
			left, total = _effect_turns(
				getattr(self.field, "weather_state", None) or getattr(self.state, "weather_state", None)
			)
			left = left if left is not None else getattr(self.state, "weather_left", None)
			total = total if total is not None else getattr(self.state, "weather_total", None)
			out.append(
				(
					_human_label(wname),
					left,
					total,
				)
			)
		# Terrain
		tname = getattr(self.field, "terrain", None) or getattr(self.state, "terrain", None)
		if tname:
			left, total = _effect_turns(
				getattr(self.field, "terrain_state", None) or getattr(self.state, "terrain_state", None)
			)
			left = left if left is not None else getattr(self.state, "terrain_left", None)
			total = total if total is not None else getattr(self.state, "terrain_total", None)
			out.append(
				(
					_human_label(tname),
					left,
					total,
				)
			)
		pseudo_weather = _mapping(getattr(self.field, "pseudo_weather", None))
		for key, state in pseudo_weather.items():
			if key in {wname, tname}:
				continue
			left, total = _effect_turns(state)
			out.append((_human_label(_state_value(state, "name", "id") or key), left, total))
		# Rooms / Gravity (common flags)
		for key, label in (
			("trick_room", "Trick Room"),
			("gravity", "Gravity"),
			("magic_room", "Magic Room"),
			("wonder_room", "Wonder Room"),
		):
			if getattr(self.state, key, None) and _normalize_lookup_key(label) not in {
				_normalize_lookup_key(item[0]) for item in out
			}:
				out.append(
					(
						label,
						getattr(self.state, f"{key}_left", None),
						getattr(self.state, f"{key}_total", None),
					)
				)
		return out

	# ---- Side timers & hazards ----
	def _side_obj(self, side: str):
		side_lower = side.lower()
		for attr in (f"side_{side_lower}", f"side{side}", side_lower, side):
			obj = getattr(self.state, attr, None)
			if obj:
				return obj
		participants = list(getattr(self.battle, "participants", []) or [])
		for participant in participants:
			if str(getattr(participant, "team", "") or "").upper() == side:
				return getattr(participant, "side", None)
		idx = 0 if side == "A" else 1
		if len(participants) > idx:
			return getattr(participants[idx], "side", None)
		mon = self.monA() if side == "A" else self.monB()
		return getattr(mon, "side", None)

	def side_data(self, side: str) -> Tuple[List[Tuple[str, int | None, int | None]], Dict[str, int]]:
		s = self._side_obj(side)
		if not s:
			return ([], {})
		timers: List[Tuple[str, int | None, int | None]] = []
		for key, label in (
			("light_screen", "Light Screen"),
			("reflect", "Reflect"),
			("aurora_veil", "Aurora Veil"),
			("safeguard", "Safeguard"),
			("mist", "Mist"),
			("tailwind", "Tailwind"),
		):
			if getattr(s, key, None):
				timers.append(
					(
						label,
						getattr(s, f"{key}_left", None),
						getattr(s, f"{key}_total", None),
					)
				)
		condition_sources = (
			_mapping(getattr(s, "conditions", None)),
			_mapping(getattr(s, "side_conditions", None)),
			_mapping(getattr(s, "sideConditions", None)),
			_mapping(getattr(s, "screens", None)),
		)
		haz = _mapping(getattr(s, "hazards", None))
		hazard_keys = {"rocks", "stealthrock", "spikes", "toxicspikes", "tspikes", "stickyweb", "web", "gmaxsteelsurge"}
		seen_timers = {_normalize_lookup_key(label) for label, _left, _total in timers}
		for source in condition_sources:
			for key, state in source.items():
				if state is False or state is None:
					continue
				norm = _normalize_lookup_key(key)
				if norm in hazard_keys:
					haz.setdefault(norm, 1)
					continue
				label = _human_label(key)
				if _normalize_lookup_key(label) in seen_timers:
					continue
				left, total = _effect_turns(state)
				timers.append((label, left, total))
				seen_timers.add(_normalize_lookup_key(label))
		return (timers, haz)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_effects_panel(
	session,
	viewer,
	*,
	total_width: int = 78,
	brief: bool = False,
	focus: Optional[str] = None,
) -> str:
	"""Render the full effects panel. `focus` can be "me" or "opp" to limit Pokémon section."""
	ad = EffectsAdapter(session, viewer)
	ascii_symbols = viewer_prefers_ascii_symbols(viewer)

	inner = max(40, total_width - 2)

	title = "Active Battle States & Effects"

	header = f" {ad.title()}".ljust(inner - 14) + f" Turn: {ad.turn()}".rjust(14)
	rows: List[str] = [rpad(header, inner)]

	# --- Field ---
	rows.append(rpad("─ Field " + ("─" * max(0, inner - 8)), inner))
	field_tokens = [_timer_chip(*t) for t in ad.field_timers() if _timer_chip(*t)]
	if field_tokens:
		for line in _wrap_tokens(field_tokens, inner):
			rows.append(rpad(line, inner))
	else:
		rows.append(rpad("None", inner))

	# --- Sides ---
	for side_label, side_key in (("Side A", "A"), ("Side B", "B")):
		rows.append(rpad(f"─ {side_label} " + ("─" * max(0, inner - len(side_label) - 3)), inner))
		timers, hazards = ad.side_data(side_key)
		side_tokens = [_timer_chip(*t) for t in timers if _timer_chip(*t)]
		haz_line = f"Hazards: {_hazards_line(hazards)}"
		if side_tokens:
			for line in _wrap_tokens(side_tokens, inner):
				rows.append(rpad(line, inner))
		else:
			rows.append(rpad("—", inner))
		rows.append(rpad(haz_line, inner))

	# --- Pokémon ---
	if not brief:
		rows.append(rpad("─ On-Field Pokémon " + ("─" * max(0, inner - 20)), inner))
		role = ad.viewer_role()
		for mon, pokemon_side, self_side in (
			(ad.monA(), "A", role in ("A", "W") and focus != "opp" or focus == "me" and role == "A"),
			(ad.monB(), "B", role in ("B", "W") and focus != "me" or focus == "opp" and role in ("A", "B")),
		):
			if not mon:
				continue
			# Line 1: Name + chips
			name_raw = display_name(mon)
			name_color = f"{THEME['name']}{name_raw}|n"
			chips = "  ".join(
				[
					p
					for p in (
						gender_chip(mon, ascii_symbols=ascii_symbols),
						f"Lv{getattr(mon, 'level', '?')}",
						status_badge(mon),
					)
					if p
				]
			)
			line1 = name_color if ansi_len(f"{name_color}  {chips}") > inner else f"{name_color}  {chips}"
			rows.append(rpad(line1, inner))
			# HP
			rows.append(rpad(fmt_hp_line(mon, inner, show_abs=self_side if role != "W" else self_side), inner))
			# Item/Ability with reveal
			is_self = role == pokemon_side
			item = _reveal(_pokemon_item_name(mon), bool(getattr(mon, "item_revealed", False)), is_self)
			abil = ad.ability_display(mon, pokemon_side, is_self)
			rows.append(rpad(f"Item: {item}   Ability: {abil}", inner))
			# Stages
			rows.append(rpad(f"Stages: {_stages_line(getattr(mon, 'boosts', {}))}", inner))
			# Effects (volatiles with optional timers)
			effects = _pokemon_effects(mon)
			if effects:
				for line in _wrap_tokens(effects, inner):
					rows.append(rpad(f"Effects: {line}", inner))
			else:
				rows.append(rpad("Effects: —", inner))
	return render_box(title, inner, rows)
