"""Battle UI renderers for the text battle HUD.

The module keeps the original boxed renderer as the legacy style and adds a
classic-modern renderer inspired by the old MU* display.  Both styles use
Evennia pipe-ANSI markup and measure visible width after stripping those tags.
"""

from pokemon.ui.box_utils import render_box
from utils.battle_display import strip_ansi

# ---------------- Theme ----------------
# Pipe-ANSI color tokens only; callers can later expose a runtime theme toggle.
THEME = {
	"title": "|W",
	"vs": "|Wvs|n",
	"name": "|w",
	"label": "|W",
	"ok": "|g",
	"warn": "|y",
	"bad": "|r",
	"dim": "|n",
	"gender_m": "|C",  # bright cyan
	"gender_f": "|M",  # bright magenta
	"gender_n": "|x",  # dim/grey
}
ASCII_SYMBOL_CLIENT_PREFIXES = ("BEIP",)

BATTLE_UI_STYLE_LEGACY = "legacy"
BATTLE_UI_STYLE_CLASSIC_MODERN = "classic_modern"
BATTLE_UI_STYLE_PF1 = "pf1"
DEFAULT_BATTLE_UI_STYLE = BATTLE_UI_STYLE_CLASSIC_MODERN
BATTLE_UI_STYLES = (BATTLE_UI_STYLE_LEGACY, BATTLE_UI_STYLE_CLASSIC_MODERN, BATTLE_UI_STYLE_PF1)
_STYLE_ALIASES = {
	"": DEFAULT_BATTLE_UI_STYLE,
	"current": DEFAULT_BATTLE_UI_STYLE,
	"default": DEFAULT_BATTLE_UI_STYLE,
	"boxed": BATTLE_UI_STYLE_LEGACY,
	"legacy": BATTLE_UI_STYLE_LEGACY,
	"classic": BATTLE_UI_STYLE_CLASSIC_MODERN,
	"classic-modern": BATTLE_UI_STYLE_CLASSIC_MODERN,
	"classic_modern": BATTLE_UI_STYLE_CLASSIC_MODERN,
	"modern": BATTLE_UI_STYLE_CLASSIC_MODERN,
	"pf1": BATTLE_UI_STYLE_PF1,
	"classic_pf1": BATTLE_UI_STYLE_PF1,
	"classic-pf1": BATTLE_UI_STYLE_PF1,
	"muck": BATTLE_UI_STYLE_PF1,
	"muf": BATTLE_UI_STYLE_PF1,
}

# ---------------- ANSI-safe helpers ----------------


def ansi_len(s: str) -> int:
	return len(strip_ansi(s or ""))


def normalize_battle_ui_style(style: str | None, default: str | None = DEFAULT_BATTLE_UI_STYLE) -> str | None:
	"""Return a supported battle UI style name or ``default`` for unknown input."""

	key = str(style or "").strip().lower().replace(" ", "_")
	key = key.replace("-", "_")
	if key in _STYLE_ALIASES:
		return _STYLE_ALIASES[key]
	return default


def _iter_viewer_sessions(viewer):
	"""Yield sessions associated with ``viewer`` or its account, if available."""

	seen = set()
	for source in (viewer, getattr(viewer, "account", None)):
		if source is None:
			continue
		direct = getattr(source, "session", None)
		if direct is not None and id(direct) not in seen:
			seen.add(id(direct))
			yield direct
		sessions = getattr(source, "sessions", None)
		for accessor in ("all", "get"):
			method = getattr(sessions, accessor, None)
			if not callable(method):
				continue
			try:
				result = method()
			except TypeError:
				continue
			if result is None:
				continue
			if isinstance(result, (list, tuple, set)):
				items = result
			else:
				items = (result,)
			for session in items:
				if session is not None and id(session) not in seen:
					seen.add(id(session))
					yield session


def viewer_prefers_ascii_symbols(viewer) -> bool:
	"""Return whether battle UI symbols should use ASCII for this viewer."""

	db = getattr(viewer, "db", None)
	preference = getattr(db, "battle_ascii_symbols", None)
	if preference is not None:
		if isinstance(preference, str):
			return preference.strip().lower() in ("1", "true", "yes", "on")
		return bool(preference)

	for session in _iter_viewer_sessions(viewer):
		flags = getattr(session, "protocol_flags", None) or {}
		clientname = str(flags.get("CLIENTNAME", "") or "").upper()
		if any(clientname.startswith(prefix) for prefix in ASCII_SYMBOL_CLIENT_PREFIXES):
			return True
	return False


def rpad(s: str, width: int, fill: str = " ") -> str:
	pad = max(0, width - ansi_len(s))
	return s + (fill * pad)


def lpad(s: str, width: int, fill: str = " ") -> str:
	pad = max(0, width - ansi_len(s))
	return (fill * pad) + s


def center_ansi(s: str, width: int) -> str:
	missing = max(0, width - ansi_len(s))
	left = missing // 2
	right = missing - left
	return (" " * left) + s + (" " * right)


def ellipsize(text: str, width: int) -> str:
	"""Safely shorten raw (non-ANSI) text to ``width`` visible chars with an ellipsis."""
	if width <= 0:
		return ""
	vis = text or ""
	if len(vis) <= width:
		return vis
	if width == 1:
		return "…"
	# reserve one char for ellipsis
	return vis[: width - 1].rstrip() + "…"


def ellipsize_ascii(text: str, width: int) -> str:
	"""Shorten raw text to ``width`` visible chars using an ASCII marker."""

	if width <= 0:
		return ""
	vis = str(text or "")
	if len(vis) <= width:
		return vis
	if width <= 3:
		return vis[:width]
	return vis[: width - 3].rstrip() + "..."


# ---------------- Badges / chips ----------------


def status_badge(mon) -> str:
	"""Return a short status badge like |yPAR|n or |rBRN|n, or empty."""
	code = getattr(mon, "status", 0)
	# Accept either enum-ish or string-ish statuses
	text = getattr(mon, "status_name", None) or (code if isinstance(code, str) else "")
	text = (text or "").upper()
	if text in ("PAR", "BRN", "PSN", "SLP", "FRZ", "TOX"):
		color = {"PAR": "|y", "BRN": "|r", "PSN": "|m", "SLP": "|c", "FRZ": "|C", "TOX": "|m"}.get(text, "|y")
		return f"{color}{text}|n"
	return ""


def gender_chip(mon, *, ascii_symbols: bool = False) -> str:
	"""Return a colored gender marker."""

	g = getattr(mon, "gender", None)
	if isinstance(g, str):
		g = g.strip().upper()
	if g in ("M", "MALE", "♂"):
		return f"{THEME['gender_m']}{'M' if ascii_symbols else '♂'}|n"
	if g in ("F", "FEMALE", "♀"):
		return f"{THEME['gender_f']}{'F' if ascii_symbols else '♀'}|n"
	return f"{THEME['gender_n']}{'-' if ascii_symbols else '–'}|n"


def display_name(mon) -> str:
	"""Return nickname/species composite or fallback name (no ANSI)."""
	nick = (getattr(mon, "nickname", None) or "").strip()
	species = (getattr(mon, "species", None) or getattr(mon, "name", "") or "?").strip()
	if nick and nick.lower() != species.lower():
		return f"{nick} ({species})"
	return species or nick or "?"


def party_pips(trainer, max_team: int = 6, *, ascii_symbols: bool = False) -> str:
	"""Return a compact team summary up to ``max_team`` slots."""

	team = list(getattr(trainer, "team", []))[:max_team]
	out = []
	for mon in team:
		if not mon:
			out.append("|x.|n" if ascii_symbols else "·")
			continue
		hp, mx = getattr(mon, "hp", 0), getattr(mon, "max_hp", 0)
		if mx <= 0 or hp <= 0:
			out.append("|rX|n" if ascii_symbols else "|r×|n")
		elif status_badge(mon):
			out.append("|yS|n" if ascii_symbols else "|y◐|n")
		else:
			p = 100 * hp // mx if mx else 0
			if p <= 25:
				out.append("|yo|n" if ascii_symbols else "|y◐|n")
			else:
				out.append("|gO|n" if ascii_symbols else "|g●|n")
	# pad to max_team with faint dots
	while len(out) < max_team:
		out.append("|x.|n" if ascii_symbols else "·")
	return " ".join(out)


# ---------------- Bars / numbers ----------------


def hp_bar(cur: int, maxhp: int, width: int = 28) -> str:
	cur = max(0, min(cur, maxhp))
	ratio = 0.0 if maxhp <= 0 else cur / maxhp
	filled = int(width * ratio)
	empty = width - filled
	color = THEME["ok"] if ratio > 0.5 else THEME["warn"] if ratio > 0.2 else THEME["bad"]
	return f"{color}{'█' * filled}{' ' * empty}|n"


def hp_bar_ascii(cur: int, maxhp: int, width: int = 20) -> str:
	"""Return an ASCII HP bar using conservative foreground colors."""

	cur = max(0, min(cur, maxhp))
	ratio = 0.0 if maxhp <= 0 else cur / maxhp
	filled = int(round(width * ratio))
	filled = max(0, min(width, filled))
	empty = width - filled
	color = THEME["ok"] if ratio > 0.5 else THEME["warn"] if ratio > 0.2 else THEME["bad"]
	return f"{color}{'|' * filled}|n|x{'-' * empty}|n"


def fmt_hp_line(mon, colw: int, show_abs: bool = True) -> str:
	"""Return a width-safe HP line that fits inside `colw`.
	Tries right-side text in this order (as space allows):
	- "hp/max (pct%)"  -> requires larger space
	- "hp/max"
	- "pct%"
	If none fit beside a minimally readable bar, shows the bar only."""
	hp = int(getattr(mon, "hp", 0) or 0)
	mx = int(getattr(mon, "max_hp", 0) or 0)
	pct = 0 if mx <= 0 else int(round(100 * hp / mx))

	prefix = f"{THEME['label']}HP|n: "
	sep_two = "  "
	sep_one = " "

	# Build candidate right-hand texts from most to least verbose
	candidates: list[str] = []
	if show_abs:
		candidates.append(f"{hp}/{mx} ({pct}%)")
		candidates.append(f"{hp}/{mx}")
	candidates.append(f"{pct}%")

	def try_fit(sep: str, right: str, min_bar: int) -> str | None:
		avail = colw - ansi_len(prefix) - ansi_len(sep) - ansi_len(right)
		if avail >= min_bar:
			return f"{prefix}{hp_bar(hp, mx, avail)}{sep}{right}"
		return None

	# Prefer a decent-sized bar with two-space separator
	for right in candidates:
		line = try_fit(sep_two, right, min_bar=10)
		if line:
			return line
	# Try again with a single space separator, allow a smaller bar
	for right in candidates:
		line = try_fit(sep_one, right, min_bar=6)
		if line:
			return line
	# Last resort: bar only; ensure at least 3 cells of bar
	bar_only = max(3, colw - ansi_len(prefix))
	return f"{prefix}{hp_bar(hp, mx, bar_only)}"


def _name_and_chips_lines(mon, colw: int, *, ascii_symbols: bool = False) -> list[str]:
	"""Adaptive name/meta row(s) with gender, level and status chips."""
	raw_name = display_name(mon)
	name_colored = f"{THEME['name']}{raw_name}|n"
	gchip = gender_chip(mon, ascii_symbols=ascii_symbols)
	level = getattr(mon, "level", None)
	lv_chip = f"Lv{level}" if level is not None else ""
	sb = status_badge(mon)
	chips = "  ".join([p for p in (gchip, lv_chip, sb) if p])
	one_line = f"{name_colored}  {chips}" if chips else name_colored
	if ansi_len(one_line) <= colw:
		return [rpad(one_line, colw)]
	# two-line variant
	trunc = raw_name
	if ansi_len(name_colored) > colw:
		trunc = ellipsize(raw_name, colw)
	name_line = rpad(f"{THEME['name']}{trunc}|n", colw)
	chips_line = rpad(chips, colw) if chips else ""
	return [name_line] + ([chips_line] if chips_line else [])


# ---------------- Title helpers ----------------


def _is_wild_battle(me, foe, state) -> bool:
        encounter = getattr(state, "encounter_kind", "").lower()
        if encounter == "wild":
                return True
        if encounter == "trainer":
                return False
        if getattr(foe, "is_wild", False):
                return True
        # Heuristic: foe is an NPC shell with a single active Pokémon and no name for a player group
        party = getattr(foe, "team", None)
        is_npc = getattr(foe, "is_npc", False)
        return bool(is_npc and isinstance(party, (list, tuple)) and len(party) <= 1)


def _wild_species(foe) -> str:
	mon = getattr(foe, "active_pokemon", None)
	return getattr(mon, "name", "Wild Pokémon")


def make_title(me, foe, state) -> str:
	player_name = getattr(me, "name", "?")
	if _is_wild_battle(me, foe, state):
		return f"{THEME['title']}{player_name}|n {THEME['vs']} {THEME['title']}Wild {_wild_species(foe)}|n"
	else:
		return f"{THEME['title']}{player_name}|n {THEME['vs']} {THEME['title']}{getattr(foe, 'name', '?')}|n"


# ---------------- Column blocks ----------------


def render_trainer_block(
	trainer,
	colw: int,
	*,
	show_abs: bool = True,
	ascii_symbols: bool = False,
) -> list[str]:
	lines: list[str] = []
	mon = getattr(trainer, "active_pokemon", None)
	if mon:
		lines.extend(_name_and_chips_lines(mon, colw, ascii_symbols=ascii_symbols))
		lines.append(rpad(fmt_hp_line(mon, colw, show_abs=show_abs), colw))
	else:
		lines.append(rpad("(No active Pokémon)", colw))
	lines.append(rpad(f"{THEME['label']}Team|n: {party_pips(trainer, ascii_symbols=ascii_symbols)}", colw))
	return [rpad(line, colw) for line in lines]


# ---------------- Main render ----------------


def render_legacy_battle_ui(
	state,
	viewer,
	total_width: int = 78,
	waiting_on=None,
	ascii_symbols: bool = False,
) -> str:
	"""
	Render the battle UI for `viewer`.
	- Two balanced columns (viewer left).
	- Title shows captains or 'vs Wild <Species>'.
	- Footer: Weather • Field • Turn, plus optional "Waiting on …".
	"""
	# layout constants
	gutter = 3

	inner = max(40, total_width - 2)  # inside the outer box
	left_w = (inner - gutter) // 2
	right_w = inner - gutter - left_w

	# sides
	my_side = state.get_side(viewer)
	if my_side == "B":
		left_side, right_side = "B", "A"
	else:
		left_side, right_side = "A", "B"
	me = state.get_trainer(left_side)
	foe = state.get_trainer(right_side)
	show_left = my_side == left_side
	show_right = my_side == right_side

	# ----- Title -----
	title = make_title(me, foe, state)

	# ----- Content -----
	left_lines = render_trainer_block(me, left_w, show_abs=show_left, ascii_symbols=ascii_symbols)
	right_lines = render_trainer_block(foe, right_w, show_abs=show_right, ascii_symbols=ascii_symbols)

	# equalize height
	max_rows = max(len(left_lines), len(right_lines))
	while len(left_lines) < max_rows:
		left_lines.append(" " * left_w)
	while len(right_lines) < max_rows:
		right_lines.append(" " * right_w)

	rows = []
	for L, R in zip(left_lines, right_lines):
		combined = L + (" " * gutter) + R
		rows.append(rpad(combined, inner))

	# ----- Footer -----
	weather = getattr(state, "weather", getattr(state, "roomweather", "-")) or "-"
	field = getattr(state, "field", "-")
	turn = getattr(state, "round_no", getattr(state, "turn", getattr(state, "round", 0)))
	footer_info = (
		f" {THEME['label']}Weather|n: {weather}   {THEME['label']}Field|n: {field}   {THEME['label']}Turn|n: {turn}"
	)
	footer = rpad(footer_info, inner)

	wait_line = None
	if waiting_on:
		name = getattr(waiting_on, "name", str(waiting_on))
		wait_line = rpad(f" Waiting on {name}...", inner)

	return render_box(title, inner, rows, footer=footer, waiting=wait_line)


# ---------------- Classic-modern renderer ----------------


def _classic_width(total_width: int | None) -> int:
	"""Clamp the classic renderer to widths that behave well in MUD clients."""

	try:
		width = int(total_width or 78)
	except (TypeError, ValueError):
		width = 78
	return max(60, min(width, 80))


def _classic_rule(label: str, width: int, char: str = "=") -> str:
	"""Return a centered ASCII divider."""

	clean = ellipsize_ascii(label.strip(), max(0, width - 4))
	if not clean:
		return char * width
	text = f" {clean} "
	fill = max(0, width - len(text))
	left = fill // 2
	right = fill - left
	return (char * left) + text + (char * right)


def _classic_turn_line(turn: int | str, width: int) -> str:
	"""Return the top turn marker."""

	prefix = f"== Turn {turn} "
	if len(prefix) >= width:
		return ellipsize_ascii(prefix.rstrip(), width)
	return prefix + ("=" * (width - len(prefix)))


def _classic_state_value(value, fallback: str = "-") -> str:
	"""Return a compact display value for weather/field names."""

	if value in (None, ""):
		return fallback
	text = str(value).replace("_", " ").strip()
	if not text:
		return fallback
	return text[:1].upper() + text[1:]


def _battle_turn(state) -> int | str:
	"""Return the best available battle turn/round number."""

	return getattr(state, "round_no", getattr(state, "turn", getattr(state, "round", 1))) or 1


def _classic_field_cell(label: str, value, width: int) -> str:
	"""Return a padded ``Label: value`` cell."""

	prefix = f"{THEME['label']}{label}|n: "
	value_width = max(0, width - ansi_len(prefix))
	text = prefix + ellipsize_ascii(_classic_state_value(value), value_width)
	return rpad(text, width)


def _classic_info_row(state, width: int) -> str:
	"""Return the weather/field/round row without fragile outer edges."""

	sep_width = 6
	round_width = 10 if width >= 68 else 9
	remaining = max(20, width - sep_width - round_width)
	weather_width = remaining // 2
	field_width = remaining - weather_width
	weather = getattr(state, "weather", getattr(state, "roomweather", "-")) or "-"
	field = getattr(state, "field", "-") or "-"
	turn = _battle_turn(state)
	weather_cell = _classic_field_cell("Weather", weather, weather_width)
	field_cell = _classic_field_cell("Field", field, field_width)
	round_cell = _classic_field_cell("Round", turn, round_width)
	return rpad(f"{weather_cell} | {field_cell} | {round_cell}", width)


def _classic_is_wild_side(trainer, side: str, state) -> bool:
	"""Return whether ``trainer`` should be labeled as the wild side."""

	encounter = str(getattr(state, "encounter_kind", "") or "").lower()
	if encounter == "wild" and side == "B":
		return True
	return bool(getattr(trainer, "is_wild", False))


def _classic_section_label(trainer, side: str, state) -> str:
	"""Return the section label for a team block."""

	if _classic_is_wild_side(trainer, side, state):
		return "WILD Pokemon"
	return f"Team {side}"


def _classic_trainer_name(trainer, width: int, side: str, state) -> str:
	"""Return the trainer name line."""

	if _classic_is_wild_side(trainer, side, state):
		mon = getattr(trainer, "active_pokemon", None)
		name = f"Wild {getattr(mon, 'name', 'Pokemon')}"
	else:
		name = getattr(trainer, "name", getattr(trainer, "key", "?"))
	return f"{THEME['title']}{ellipsize_ascii(name, width)}|n"


def fmt_hp_line_classic(mon, width: int, show_abs: bool = True) -> str:
	"""Return an ASCII HP line that fits within ``width`` visible columns."""

	hp = int(getattr(mon, "hp", 0) or 0)
	mx = int(getattr(mon, "max_hp", 0) or 0)
	pct = 0 if mx <= 0 else int(round(100 * hp / mx))
	prefix = f"{THEME['label']}HP|n: "
	right = f"{hp}/{mx} {pct}%" if show_abs else f"{pct}%"
	available = width - ansi_len(prefix) - 1 - len(right)
	if available >= 8:
		bar_width = min(20, available)
		return rpad(f"{prefix}{hp_bar_ascii(hp, mx, bar_width)} {right}", width)
	percent_only = f"{prefix}{right}"
	if ansi_len(percent_only) <= width:
		return rpad(percent_only, width)
	return rpad(ellipsize_ascii(strip_ansi(percent_only), width), width)


def _classic_pokemon_line(
	index: int,
	mon,
	width: int,
	*,
	show_abs: bool,
	ascii_symbols: bool = False,
) -> str:
	"""Return a single compact active Pokemon row."""

	name_width = 26 if width >= 74 else 21
	level_width = 11 if width >= 74 else 9
	hp_width = max(20, width - name_width - level_width)

	prefix = f"{index} "
	gchip = gender_chip(mon, ascii_symbols=ascii_symbols)
	name_room = max(4, name_width - len(prefix) - ansi_len(gchip) - 1)
	name = ellipsize_ascii(display_name(mon), name_room)
	name_field = rpad(f"{prefix}{name} {gchip}", name_width)

	level = getattr(mon, "level", None)
	status = status_badge(mon)
	level_text = f"Lv {level}" if level is not None else ""
	if status:
		level_text = f"{level_text} {status}".strip()
	level_field = rpad(level_text, level_width)
	line = name_field + level_field + fmt_hp_line_classic(mon, hp_width, show_abs=show_abs)
	if ansi_len(line) <= width:
		return line

	hp_width = max(18, width - name_width - level_width)
	line = name_field + level_field + fmt_hp_line_classic(mon, hp_width, show_abs=show_abs)
	return rpad(line, width)


def render_classic_trainer_block(
	trainer,
	width: int,
	*,
	side: str,
	state,
	show_abs: bool,
	ascii_symbols: bool = False,
) -> list[str]:
	"""Return the classic-modern lines for one side."""

	lines: list[str] = []
	lines.append(_classic_trainer_name(trainer, width, side, state))
	mon = getattr(trainer, "active_pokemon", None)
	if mon:
		lines.append(_classic_pokemon_line(1, mon, width, show_abs=show_abs, ascii_symbols=ascii_symbols))
	else:
		lines.append(rpad("1 (No active Pokemon)", width))
	lines.append(f"{THEME['label']}Team|n: {party_pips(trainer, ascii_symbols=True)}")
	return [line if ansi_len(line) <= width else ellipsize_ascii(strip_ansi(line), width) for line in lines]


def render_classic_modern_battle_ui(
	state,
	viewer,
	total_width: int = 78,
	waiting_on=None,
	ascii_symbols: bool = False,
) -> str:
	"""Render a compact ASCII battle HUD inspired by the legacy MU* display."""

	width = _classic_width(total_width)
	my_side = state.get_side(viewer)
	if my_side == "B":
		sides = ("B", "A")
	else:
		sides = ("A", "B")

	lines: list[str] = [_classic_turn_line(_battle_turn(state), width)]
	for idx, side in enumerate(sides):
		trainer = state.get_trainer(side)
		if trainer is None:
			continue
		lines.append(_classic_rule(_classic_section_label(trainer, side, state), width))
		lines.extend(
			render_classic_trainer_block(
				trainer,
				width,
				side=side,
				state=state,
				show_abs=(my_side == side),
				ascii_symbols=ascii_symbols,
			)
		)
		if idx == 0:
			lines.append(_classic_info_row(state, width))

	if waiting_on:
		name = getattr(waiting_on, "name", str(waiting_on))
		lines.append(ellipsize_ascii(f"Waiting on {name}...", width))

	return "\n".join(line if ansi_len(line) <= width else ellipsize_ascii(strip_ansi(line), width) for line in lines)


# ---------------- PF1 renderer ----------------


def _pf1_team_color(side: str) -> str:
	"""Return a PF1-inspired side color."""

	return "|C" if str(side).upper() == "A" else "|r"


def _pf1_status_code(mon) -> str:
	"""Return a PF1-style three-character status cell."""

	text = getattr(mon, "status_name", None)
	if text is None:
		text = getattr(mon, "status", "")
	text = str(text or "").strip().upper()
	status_map = {
		"PAR": ("|y", "PRZ"),
		"PARALYZED": ("|y", "PRZ"),
		"PRZ": ("|y", "PRZ"),
		"BRN": ("|r", "BRN"),
		"BURN": ("|r", "BRN"),
		"BURNED": ("|r", "BRN"),
		"PSN": ("|m", "PSN"),
		"POISON": ("|m", "PSN"),
		"POISONED": ("|m", "PSN"),
		"TOX": ("|m", "TOX"),
		"TOXIC": ("|m", "TOX"),
		"SLP": ("|c", "SLP"),
		"SLEEP": ("|c", "SLP"),
		"ASLEEP": ("|c", "SLP"),
		"FRZ": ("|C", "FRZ"),
		"FROZEN": ("|C", "FRZ"),
	}
	color, code = status_map.get(text, ("|w", "NRM"))
	return f"{color}{code}|n"


def _pf1_percent(mon) -> int:
	"""Return rounded HP percent, preserving over-heal displays."""

	hp = int(getattr(mon, "hp", 0) or 0)
	mx = int(getattr(mon, "max_hp", 0) or 0)
	return 0 if mx <= 0 else int(round(100 * hp / mx))


def _pf1_percent_bar(percent: int, width: int = 10) -> str:
	"""Return the old PF1 10-cell percent bar with conservative colors."""

	if width <= 0:
		return ""
	filled = int(percent // 10)
	if percent > 0 and filled == 0:
		filled = 1
	filled = max(0, min(width, filled))
	parts: list[str] = []
	for idx in range(1, width + 1):
		if idx > filled:
			parts.append(" ")
		elif idx < 3:
			parts.append(f"{THEME['bad']}||n")
		elif idx < 6:
			parts.append(f"{THEME['warn']}||n")
		else:
			parts.append(f"{THEME['ok']}||n")
	return "".join(parts)


def _pf1_hp_color(percent: int) -> str:
	"""Return the PF1 HP-number color for a percent value."""

	if percent <= 25:
		return THEME["bad"]
	if percent <= 50:
		return THEME["warn"]
	return THEME["ok"]


def _pf1_party_markers(trainer, max_team: int = 6) -> str:
	"""Return PF1-style party markers: O healthy, S status, X fainted."""

	team = list(getattr(trainer, "team", []))[:max_team]
	out: list[str] = []
	for mon in team:
		if not mon:
			out.append("|x.|n")
			continue
		hp = int(getattr(mon, "hp", 0) or 0)
		mx = int(getattr(mon, "max_hp", 0) or 0)
		if mx <= 0 or hp <= 0:
			out.append("|xX|n")
		elif strip_ansi(_pf1_status_code(mon)) != "NRM":
			out.append("|mS|n")
		else:
			out.append("|gO|n")
	while len(out) < max_team:
		out.append("|x.|n")
	return "".join(out)


def _pf1_banner(label: str, width: int, *, side: str | None = None, markers: str = "") -> str:
	"""Return a PF1-like team banner without a fragile right border."""

	color = _pf1_team_color(side or "A")
	prefix = f"== {markers} " if markers else "== "
	text = f"{prefix}===== {label} "
	fill = max(0, width - ansi_len(text))
	return f"{color}{text}{'=' * fill}|n"


def _pf1_species(mon) -> str:
	"""Return a species label for the PF1 identity column."""

	return str(getattr(mon, "species", None) or getattr(mon, "base_species", None) or getattr(mon, "name", "") or "?")


def _pf1_hp_cell(mon, *, show_abs: bool) -> str:
	"""Return the PF1 HP cell."""

	hp = int(getattr(mon, "hp", 0) or 0)
	mx = int(getattr(mon, "max_hp", 0) or 0)
	percent = _pf1_percent(mon)
	color = _pf1_hp_color(percent)
	if show_abs:
		return f"{THEME['label']}HP|n: {color}{hp:>3}|n/|x{mx:>3}|n {color}{percent:>3}%|n"
	return f"{THEME['label']}HP|n: {_pf1_percent_bar(percent)} {percent:>3}%"


def _pf1_lead_cell(pos: str, mon, *, show_abs: bool) -> str:
	"""Return the PF1 left-side position/HP/status cell."""

	percent = _pf1_percent(mon)
	status = _pf1_status_code(mon)
	if show_abs:
		hp_text = f"{percent:>3}%"
	else:
		hp_text = f"{_pf1_percent_bar(percent)} {percent:>3}%"
	return f"{_pf1_team_color(pos[:1])}{pos}|n {hp_text} {status}"


def _pf1_identity_cell(mon, width: int, *, ascii_symbols: bool = False) -> str:
	"""Return a compact PF1 identity cell with level, name, gender and species."""

	level = getattr(mon, "level", None)
	level_text = f"Lv {level}" if level is not None else "Lv -"
	gchip = gender_chip(mon, ascii_symbols=ascii_symbols)
	name = display_name(mon)
	species = _pf1_species(mon)
	if species and species.lower() != strip_ansi(name).lower():
		text = f"{level_text} {name} {gchip} / {species}"
	else:
		text = f"{level_text} {name} {gchip}"
	if ansi_len(text) <= width:
		return rpad(text, width)
	gender_room = ansi_len(gchip) + 1
	base_room = max(4, width - len(level_text) - gender_room - 2)
	short = f"{level_text} {ellipsize_ascii(name, base_room)} {gchip}"
	if ansi_len(short) <= width:
		return rpad(short, width)
	return rpad(ellipsize_ascii(strip_ansi(short), width), width)


def _pf1_pokemon_row(
	pos: str,
	mon,
	width: int,
	*,
	show_abs: bool,
	ascii_symbols: bool = False,
) -> str:
	"""Return one PF1-style active Pokemon row."""

	lead = _pf1_lead_cell(pos, mon, show_abs=show_abs)
	hp_cell = _pf1_hp_cell(mon, show_abs=show_abs)
	identity_width = width - ansi_len(lead) - ansi_len(hp_cell) - 6
	if identity_width < 18:
		lead = f"{_pf1_team_color(pos[:1])}{pos}|n {_pf1_status_code(mon)}"
		identity_width = width - ansi_len(lead) - ansi_len(hp_cell) - 6
	identity = _pf1_identity_cell(mon, max(8, identity_width), ascii_symbols=ascii_symbols)
	line = f"{lead} | {identity} | {hp_cell}"
	if ansi_len(line) <= width:
		return rpad(line, width)
	return rpad(ellipsize_ascii(strip_ansi(line), width), width)


def _pf1_trainer_line(trainer, side: str, width: int, state) -> str | None:
	"""Return the optional trainer header line used in PF1 trainer battles."""

	if _classic_is_wild_side(trainer, side, state):
		return None
	name = getattr(trainer, "name", getattr(trainer, "key", "")) or ""
	if not name:
		return None
	text = f"{_pf1_team_color(side)}{side}|n {THEME['title']}{ellipsize_ascii(name, max(0, width - 4))}|n"
	return rpad(text, width)


def _pf1_weather_rows(state, width: int) -> list[str]:
	"""Return the PF1 weather/field/round divider block."""

	weather = _classic_state_value(getattr(state, "weather", getattr(state, "roomweather", "-")) or "-")
	field = _classic_state_value(getattr(state, "field", "-") or "-")
	turn = _battle_turn(state)
	weather_cell = _classic_field_cell("Weather", weather, 26 if width >= 76 else 22)
	field_cell = _classic_field_cell("Field", field, 24 if width >= 76 else 20)
	round_cell = _classic_field_cell("Round", turn, 10)
	info = f"{weather_cell} | {field_cell} | {round_cell}"
	return ["-" * width, rpad(info, width), "-" * width]


def render_pf1_battle_ui(
	state,
	viewer,
	total_width: int = 78,
	waiting_on=None,
	ascii_symbols: bool = False,
) -> str:
	"""Render a PF1/MUCK-inspired battle HUD using width-safe ASCII."""

	width = _classic_width(total_width)
	my_side = state.get_side(viewer)
	lines: list[str] = []
	for idx, side in enumerate(("A", "B")):
		trainer = state.get_trainer(side)
		if trainer is None:
			continue
		label = "WILD Pokemon" if _classic_is_wild_side(trainer, side, state) else f"Team {side}"
		markers = "" if _classic_is_wild_side(trainer, side, state) else _pf1_party_markers(trainer)
		lines.append(_pf1_banner(label, width, side=side, markers=markers))
		trainer_line = _pf1_trainer_line(trainer, side, width, state)
		if trainer_line:
			lines.append(trainer_line)
		mon = getattr(trainer, "active_pokemon", None)
		if mon:
			lines.append(
				_pf1_pokemon_row(
					f"{side}1",
					mon,
					width,
					show_abs=(my_side == side),
					ascii_symbols=ascii_symbols,
				)
			)
		else:
			lines.append(rpad(f"{_pf1_team_color(side)}{side}1|n (No active Pokemon)", width))
		if idx == 0:
			lines.extend(_pf1_weather_rows(state, width))

	if waiting_on:
		name = getattr(waiting_on, "name", str(waiting_on))
		lines.append(ellipsize_ascii(f"Waiting on {name}...", width))

	return "\n".join(line if ansi_len(line) <= width else ellipsize_ascii(strip_ansi(line), width) for line in lines)


def render_battle_ui(
	state,
	viewer,
	total_width: int = 78,
	waiting_on=None,
	style: str | None = None,
	ascii_symbols: bool | None = None,
) -> str:
	"""Render the selected battle UI style."""

	if ascii_symbols is None:
		ascii_symbols = viewer_prefers_ascii_symbols(viewer)

	normalized_style = normalize_battle_ui_style(style)
	if normalized_style == BATTLE_UI_STYLE_PF1:
		return render_pf1_battle_ui(
			state,
			viewer,
			total_width=total_width,
			waiting_on=waiting_on,
			ascii_symbols=ascii_symbols,
		)
	if normalized_style == BATTLE_UI_STYLE_CLASSIC_MODERN:
		return render_classic_modern_battle_ui(
			state,
			viewer,
			total_width=total_width,
			waiting_on=waiting_on,
			ascii_symbols=ascii_symbols,
		)
	return render_legacy_battle_ui(
		state,
		viewer,
		total_width=total_width,
		waiting_on=waiting_on,
		ascii_symbols=ascii_symbols,
	)
