"""Rendering functions for trainer and Pokémon sheets."""

import re
from types import SimpleNamespace

from evennia.utils.evtable import EvTable

from pokemon.dex import MOVEDEX, POKEDEX
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.models.stats import DISPLAY_STAT_MAP, STAT_KEY_MAP, exp_for_level, level_for_exp
from pokemon.utils.pokemon_like import PokemonLike
from utils.ansi import ansi
from utils.ansi_widgets import (
        THEME as WIDGET_THEME,
        apply_screen_reader,
        bar,
        chip,
        get_theme,
        header_box,
        infer_hp_phrase,
        infer_xp_phrase,
        join_items,
        kv_row,
        money_line,
        section_divider,
        stat_summary_row,
        status_code,
        themed_line,
        type_chip,
)
from utils.inventory_view import (
        gather_inventory_pairs,
        format_inventory_by_category,
        format_inventory_table,
)
from utils.display_helpers import (
        format_move_details,
        get_egg_description,
        get_status_effects,
)
from utils.faction_utils import get_faction_and_rank
from utils.xp_utils import get_display_xp, get_next_level_xp

__all__ = [
        "display_pokemon_sheet",
        "display_trainer_sheet",
        "display_full_inventory",
        "display_inventory_by_category",
]

# ---- Theme & helpers ---------------------------------------------------------
# Pipe-ANSI friendly theme; override as needed from call-sites later if desired.
THEME = {
        "accent": "|W",
        "muted": "|x",
        "border": "|g",
        "value": "|w",
        "warn": "|y",
        "bad": "|r",
        "good": "|G",
}

# Canonical-ish type colors. Fallback to default if unknown.
TYPE_COLORS = {
	"Normal": "|w",
	"Fire": "|r",
	"Water": "|B",
	"Electric": "|y",
	"Grass": "|g",
	"Ice": "|C",
	"Fighting": "|R",
	"Poison": "|m",
	"Ground": "|Y",
	"Flying": "|c",
	"Psychic": "|M",
	"Bug": "|G",
	"Rock": "|Y",
	"Ghost": "|M",
	"Dragon": "|b",
	"Dark": "|n",
	"Steel": "|W",
	"Fairy": "|P",
}


def _get_pokemon_types(pokemon: PokemonLike) -> list[str]:
	"""Return a list of type strings for ``pokemon``."""
	types = getattr(pokemon, "types", None) or getattr(pokemon, "type", None) or getattr(pokemon, "type_", None)
	if types:
		return [types] if isinstance(types, str) else list(types)

	species = getattr(pokemon, "species", None) or getattr(pokemon, "name", None)
	if not species:
		return []

	name = str(species)
	entry = POKEDEX.get(name) or POKEDEX.get(name.capitalize()) or POKEDEX.get(name.lower())
	if entry:
		types = getattr(entry, "types", None)
		if not types and isinstance(entry, dict):
			types = entry.get("types")
		if types:
			return list(types)
	return []


def _color_type(type_name: str) -> str:
	"""Return the given type name with color codes."""
	tname = type_name.capitalize()
	prefix = TYPE_COLORS.get(tname, THEME["value"])
	return f"{prefix}{tname}|n"


def _title_bar(text: str, width: int = 78) -> str:
	"""Return a centered title bar with ANSI-aware width."""
	border = f"{THEME['border']}-|n"
	title = f"{THEME['accent']}{text}|n"
	side = "-" * max(0, (width - len(text) - 2) // 2)
	return f"{THEME['border']}{side}[|n{title}{THEME['border']}] {side}|n".ljust(width)


def display_trainer_sheet(character, mode: str | None = None) -> str:
        """Return a formatted sheet for a trainer character.

        Parameters
        ----------
        character : object
                The trainer or player character to render.
        mode : str, optional
                One of ``"full"``, ``"brief"`` or ``"inventory"``.  ``None``
                falls back to full mode.
        """

        width = 60
        char = character
        db = getattr(char, "db", SimpleNamespace())

        requested_mode = (mode or getattr(db, "sheet_mode", "full") or "full").lower()
        if requested_mode not in {"full", "brief", "inventory"}:
                requested_mode = "full"

        name = getattr(char, "key", "Unknown")

        palette = get_theme(WIDGET_THEME)

        attr_handler = getattr(char, "attributes", None)
        try:
                screen_reader = bool(attr_handler.get("sheet_screen_reader", default=False)) if attr_handler else False
        except Exception:
                screen_reader = False

        def _as_int(value):
                try:
                        return int(value)
                except (TypeError, ValueError):
                        return None

        def _chip(value, default: str, color: str):
                text = str(value) if value not in (None, "") else default
                if text.strip() == "":
                        text = default
                if isinstance(text, str) and "|" in text:
                        return text
                return chip(text, color)

        level_val = _as_int(getattr(db, "level", None))
        level_str = str(level_val) if level_val is not None else "—"

        fusion_species = getattr(db, "fusion_species", None)
        species = fusion_species or getattr(char, "species", None) or "Human"
        morphology = getattr(db, "morphology", None)
        if not morphology:
                morphology = "Fusion" if fusion_species else "Human"
        gender = getattr(db, "gender", None) or getattr(char, "gender", "?") or "?"
        status_raw = getattr(db, "status", None) or "None"
        faction_display = get_faction_and_rank(char) or "None"

        species_display = _chip(species, "—", palette.get("value", "|y"))
        morph_display = _chip(morphology, "—", palette.get("type", "|c"))
        gender_display = _chip(gender, "?", "|b")
        status_display = status_code(status_raw, theme=palette, screen_reader=screen_reader)
        faction_chip = _chip(faction_display, "None", "|C")

        nature = getattr(db, "nature", getattr(char, "nature", None)) or "—"
        ability = getattr(db, "ability", getattr(char, "ability", None)) or "—"
        held_item = (
                getattr(db, "held_item", None)
                or getattr(db, "held", None)
                or getattr(db, "helditem", None)
                or getattr(char, "held_item", None)
                or "Nothing"
        )

        raw_types = getattr(db, "types", None) or getattr(char, "types", None) or []
        if isinstance(raw_types, str):
                type_list = [raw_types]
        else:
                type_list = list(raw_types)
        type_str = " / ".join(type_chip(t, theme=palette, screen_reader=screen_reader) for t in type_list) if type_list else type_chip(None, theme=palette, screen_reader=screen_reader)

        try:
                show_numbers = bool(attr_handler.get("sheet_debug", default=False)) if attr_handler else False
        except Exception:
                show_numbers = False

        hp_current = _as_int(getattr(db, "hp", None))
        hp_max = _as_int(getattr(db, "max_hp", None))
        if hp_max is None:
                hp_max = _as_int(getattr(db, "hp_max", None))
        if hp_max is None:
                stats_dict = getattr(db, "stats", None)
                if isinstance(stats_dict, dict):
                        hp_max = _as_int(stats_dict.get("hp"))

        xp_total = None
        for xp_attr in ("total_exp", "xp", "experience"):
                xp_total = _as_int(getattr(db, xp_attr, None))
                if xp_total is not None:
                        break
        xp_to_next = None
        for xp_attr in ("exp_to_next", "xp_to_next"):
                xp_to_next = _as_int(getattr(db, xp_attr, None))
                if xp_to_next is not None:
                        break

        hp_ratio = None
        if hp_current is not None and hp_max and hp_max > 0:
                hp_ratio = max(0.0, min(1.0, hp_current / hp_max))
                hp_label_text = f"{hp_current}/{hp_max}" if show_numbers else infer_hp_phrase(hp_current, hp_max)
                hp_color = "|G" if hp_ratio >= 0.66 else "|y" if hp_ratio >= 0.33 else "|r"
                hp_label = chip(hp_label_text, hp_color)
                hp_display = f"{bar(hp_current, hp_max)} {hp_label}"
        else:
                hp_display = chip("Unknown", "|x")

        xp_ratio = None
        xp_progress = None
        xp_span = None
        next_requirement = None
        if xp_total is not None:
                growth_rate = getattr(db, "growth_rate", getattr(char, "growth_rate", "medium_fast"))
                try:
                        current_level = level_val if level_val is not None else level_for_exp(xp_total, growth_rate)
                        current_level = max(1, int(current_level))
                        next_level = min(current_level + 1, 100)
                        current_floor = exp_for_level(current_level, growth_rate)
                        next_req = exp_for_level(next_level, growth_rate)
                        next_requirement = next_req
                        span = max(1, next_req - current_floor)
                        progress = xp_total - current_floor
                        xp_progress = max(0, progress)
                        xp_span = span
                        xp_ratio = max(0.0, min(1.0, progress / span))
                except Exception:
                        xp_ratio = None

        xp_label_text: str
        if xp_total is not None and next_requirement is not None:
                xp_label_text = f"{xp_total:,} / {next_requirement:,}"
                if xp_to_next is not None:
                        xp_label_text += f" ({xp_to_next:,} to next)"
        elif xp_total is not None and show_numbers:
                xp_label_text = f"{xp_total:,} XP"
        elif xp_to_next is not None:
                xp_label_text = infer_xp_phrase(xp_to_next)
        else:
                xp_label_text = "Unknown"

        xp_label = chip(xp_label_text, palette.get("type", "|c"), theme=palette, screen_reader=screen_reader)
        if xp_ratio is not None and xp_progress is not None and xp_span is not None:
                xp_display = f"{bar(xp_progress, xp_span)} {xp_label}"
        else:
                xp_display = xp_label

        inv_pairs = gather_inventory_pairs(char)
        inventory_display = join_items(inv_pairs, max_items=5, theme=palette, screen_reader=screen_reader)
        if not inventory_display:
                inventory_display = chip("Empty", palette.get("muted", "|x"), theme=palette, screen_reader=screen_reader)

        def _first_attr(*names):
                for attr in names:
                        value = getattr(db, attr, None)
                        if value is not None:
                                return value
                return None

        wallet_value = _first_attr("money", "wallet", "cash", "credits", "pokedollars")
        bank_value = _first_attr("bank", "savings", "account")
        money_display = money_line(wallet_value, bank_value, theme=palette, screen_reader=screen_reader)
        if not money_display:
                money_display = chip("Unknown", palette.get("muted", "|x"), theme=palette, screen_reader=screen_reader)

        header_label = {
                "brief": "Trainer Snapshot",
                "inventory": "Trainer Inventory",
        }.get(requested_mode, "Trainer Card")
        morph_text = str(morphology or "—")
        title = f"|y{header_label}|n · |w{morph_text}|n"
        header = header_box(
                title,
                left=f"|W{name}|n",
                right=chip(f"Lv {level_str}", palette.get("type", "|c"), theme=palette, screen_reader=screen_reader),
                width=width,
                theme=palette,
                screen_reader=screen_reader,
        )

        if requested_mode == "inventory":
                lines = [
                        header,
                        section_divider("Inventory", width=width, theme=palette, screen_reader=screen_reader),
                        kv_row("Inventory", inventory_display, width=width, theme=palette, screen_reader=screen_reader),
                        kv_row("Money", money_display, width=width, theme=palette, screen_reader=screen_reader),
                ]
                sheet = "\n".join(line for line in lines if line)
                return apply_screen_reader(sheet) if screen_reader else sheet

        stats_dict = getattr(db, "stats", None)
        stat_values = {}
        if isinstance(stats_dict, dict):
                stat_values.update(stats_dict)
        for attr in ("phys_atk", "phys_def", "sp_atk", "sp_def", "speed"):
                value = getattr(db, attr, None)
                if value is None:
                        value = getattr(char, attr, None)
                if value is not None:
                        stat_values[attr] = value

        hp_display: str
        if hp_ratio is not None:
                hp_label_text = f"{hp_current}/{hp_max}" if show_numbers else infer_hp_phrase(hp_current, hp_max)
                if screen_reader:
                        hp_label = f"({hp_label_text})"
                else:
                        hp_color = palette['ok'] if hp_ratio >= 0.66 else palette['warn'] if hp_ratio >= 0.33 else palette['bad']
                        hp_label = chip(hp_label_text, hp_color, theme=palette, screen_reader=screen_reader)
                pct = int(round(hp_ratio * 100))
                hp_display = f"{bar(hp_current, hp_max)} {hp_label}  {pct}%  {status_code(status_raw, theme=palette, screen_reader=screen_reader)}"
        else:
                hp_display = chip("Unknown", palette.get("muted", "|x"), theme=palette, screen_reader=screen_reader)

        profile_block = [
                section_divider("Profile", width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Species", species_display, "Morph", morph_display, width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Sex", gender_display, "Faction", faction_chip, width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Status", status_display, "Type", type_str, width=width, theme=palette, screen_reader=screen_reader),
        ]

        traits_block = [
                section_divider("Traits", width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Nature", str(nature), "Ability", str(ability), width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Held Item", str(held_item), width=width, theme=palette, screen_reader=screen_reader),
        ]

        vitals_block = [
                section_divider("Vitals", width=width, theme=palette, screen_reader=screen_reader),
                kv_row("HP", hp_display, "EXP", xp_display, width=width, theme=palette, screen_reader=screen_reader),
                stat_summary_row(stat_values, theme=palette, screen_reader=screen_reader, width=width),
        ]

        resources_block = [
                section_divider("Resources", width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Inventory", inventory_display, width=width, theme=palette, screen_reader=screen_reader),
                kv_row("Money", money_display, width=width, theme=palette, screen_reader=screen_reader),
        ]

        if requested_mode == "brief":
                lines = [header] + profile_block + vitals_block + [kv_row("Money", money_display, width=width, theme=palette, screen_reader=screen_reader)]
                sheet = "\n".join(line for line in lines if line)
                return apply_screen_reader(sheet) if screen_reader else sheet

        tips_line = "|wTips|n        : +sheet/brief  ·  +sheet/inv  ·  +sheet/pokemon"
        full_lines = [header] + profile_block + traits_block + vitals_block + resources_block + [themed_line(width=width, theme=palette, screen_reader=screen_reader), tips_line]
        sheet = "\n".join(line for line in full_lines if line)
        return apply_screen_reader(sheet) if screen_reader else sheet


def display_full_inventory(caller, page: int = 1, *, cols: int = 3, find: str = "") -> str:
        """Return a paginated inventory table for ``caller``."""

        width = 60
        palette = get_theme(WIDGET_THEME)
        name = getattr(caller, "key", "Unknown")

        attr_handler = getattr(caller, "attributes", None)
        try:
                screen_reader = bool(attr_handler.get("sheet_screen_reader", default=False)) if attr_handler else False
        except Exception:
                screen_reader = False

        pairs = gather_inventory_pairs(caller)
        filtered_pairs = pairs
        if find:
                needle = find.lower()
                filtered_pairs = [(n, c) for (n, c) in pairs if needle in n.lower()]

        header_right = (
                f"|w{len(filtered_pairs)} of {len(pairs)} items|n"
                if find else f"|w{len(pairs)} items|n"
        )
        header = header_box(
                "Inventory",
                left=f"|W{name}|n",
                right=header_right,
                width=width,
                theme=palette,
                screen_reader=screen_reader,
        )
        tips = "|wTips|n : +sheet/inv [page]    ·    +sheet/inv cols <n>    ·    +sheet"
        if not filtered_pairs:
                _, footer = format_inventory_table([], page=1, rows=10, cols=cols, width=width)
                sheet = "\n".join((header, "|w(no matches)|n" if find else "|w(empty)|n", footer, tips))
                return apply_screen_reader(sheet) if screen_reader else sheet

        body, footer = format_inventory_table(filtered_pairs, page=page, rows=10, cols=cols, width=width)
        sheet = "\n".join((header, body, footer, tips))
        return apply_screen_reader(sheet) if screen_reader else sheet


def display_inventory_by_category(caller, *, cols: int = 3, find: str = "") -> str:
        """Return a themed inventory overview grouped by category."""

        width = 60
        palette = get_theme(WIDGET_THEME)
        name = getattr(caller, "key", "Unknown")

        attr_handler = getattr(caller, "attributes", None)
        try:
                screen_reader = bool(attr_handler.get("sheet_screen_reader", default=False)) if attr_handler else False
        except Exception:
                screen_reader = False

        pairs = gather_inventory_pairs(caller)
        filtered_pairs = pairs
        if find:
                needle = find.lower()
                filtered_pairs = [(n, c) for (n, c) in pairs if needle in n.lower()]

        header_right = f"|w{len(filtered_pairs)} of {len(pairs)} items|n" if find else f"|w{len(pairs)} items|n"
        header = header_box(
                "Inventory by Category",
                left=f"|W{name}|n",
                right=header_right,
                width=width,
                theme=palette,
                screen_reader=screen_reader,
        )

        body = format_inventory_by_category(pairs, cols=cols, width=width, find=find)
        tips = "|wTips|n : +sheet/inv/cat cols <n>  ·  +sheet/inv/cat find <term>"
        sheet = "\n".join((header, body, tips))
        return apply_screen_reader(sheet) if screen_reader else sheet


def _hp_bar(current: int, maximum: int, width: int = 20) -> str:
	"""Return a colored HP bar with percentage."""
	if maximum <= 0:
		return ""
	ratio = max(0.0, min(1.0, current / maximum))
	filled = int(width * ratio)
	if ratio > 0.5:
		color = ansi.GREEN
	elif ratio > 0.25:
		color = ansi.YELLOW
	else:
		color = ansi.RED
	bar = color("█" * filled + " " * (width - filled))
	pct = int(ratio * 100)
	return f"{bar} {THEME['muted']}({pct}%)|n"


def _maybe_stat_breakdown(pokemon: PokemonLike) -> str | None:
	"""Optional IV/EV/nature breakdown if attributes exist on ``pokemon``."""
	ivs = getattr(pokemon, "ivs", None)
	evs = getattr(pokemon, "evs", None)
	if not ivs and not evs:
		return None

	def _row(src, label):
		"""Return a formatted row for either dict, sequence or object data."""
		if not src:
			return None
		if hasattr(src, "items"):
			mapping = {STAT_KEY_MAP.get(k, k): v for k, v in src.items()}
		else:
			try:
				seq = list(src)
			except TypeError:
				seq = [
					getattr(src, "hp", 0),
					getattr(src, "attack", 0),
					getattr(src, "defense", 0),
					getattr(src, "special_attack", 0),
					getattr(src, "special_defense", 0),
					getattr(src, "speed", 0),
				]
			mapping = {
				"hp": seq[0] if len(seq) > 0 else 0,
				"attack": seq[1] if len(seq) > 1 else 0,
				"defense": seq[2] if len(seq) > 2 else 0,
				"special_attack": seq[3] if len(seq) > 3 else 0,
				"special_defense": seq[4] if len(seq) > 4 else 0,
				"speed": seq[5] if len(seq) > 5 else 0,
			}
		return [
			label,
			str(mapping.get("hp", 0)),
			str(mapping.get("attack", 0)),
			str(mapping.get("defense", 0)),
			str(mapping.get("special_attack", 0)),
			str(mapping.get("special_defense", 0)),
			str(mapping.get("speed", 0)),
		]

	table = EvTable(
		"|w |n",
		"|wHP|n",
		"|wAtk|n",
		"|wDef|n",
		"|wSpA|n",
		"|wSpD|n",
		"|wSpe|n",
		border="table",
	)
	row_iv = _row(ivs, f"{THEME['muted']}IV|n")
	row_ev = _row(evs, f"{THEME['muted']}EV|n")
	if row_iv:
		table.add_row(*row_iv)
	if row_ev:
		table.add_row(*row_ev)
	return str(table)


def display_pokemon_sheet(caller, pokemon: PokemonLike, slot: int | None = None, mode: str = "full") -> str:
	"""Return a formatted sheet for ``pokemon``.

	Parameters
	----------
	caller : object
	    The calling object (unused but kept for API compatibility).
	pokemon : PokemonLike
	    The Pokémon to display.
	slot : int or None, optional
	    The party slot for labeling.
	mode : str, optional
	    One of ``"full"``, ``"brief"`` or ``"moves"``.
	"""
	name = getattr(pokemon, "name", "Unknown")
	species = getattr(pokemon, "species", name)
	gender = getattr(pokemon, "gender", "?")

	level = getattr(pokemon, "level", None)
	if level is None:
		xp_val = get_display_xp(pokemon)
		growth = getattr(pokemon, "growth_rate", "medium_fast")
		level = level_for_exp(xp_val, growth)

	xp = get_display_xp(pokemon)
	next_xp = get_next_level_xp(pokemon)

	hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
	max_hp = get_max_hp(pokemon)

	header = name if slot is None else f"Slot {slot}: {name}"
	lines = [_title_bar(header)]

	types = _get_pokemon_types(pokemon)
	type_str = " / ".join(_color_type(t) for t in types) if types else f"{THEME['muted']}?|n"
	status_str = get_status_effects(pokemon) or "NORM"
	nature = getattr(pokemon, "nature", None) or "?"
	ability = getattr(pokemon, "ability", None) or "?"
	held = getattr(pokemon, "held_item", None) or "Nothing"

	xp_to = max(0, (next_xp or 0) - (xp or 0))
	xp_pct = 0 if not next_xp else int(min(100, max(0, (xp / next_xp) * 100)))

	top = EvTable(border="none")
	top.add_row(
		f"{THEME['muted']}Species|n: {THEME['value']}{species}|n    "
		f"{THEME['muted']}Gender|n: {THEME['value']}{gender}|n    "
		f"{THEME['muted']}Type|n: {type_str}"
	)
	top.add_row(
		f"{THEME['muted']}Level|n: {THEME['value']}{level}|n    "
		f"{THEME['muted']}XP|n: {THEME['value']}{xp}|n/{next_xp} "
		f"{THEME['muted']}({xp_pct}% to next, {xp_to} xp)|n"
	)
	lines.append(str(top))

	lines.append(
		f"{THEME['muted']}HP|n: {THEME['value']}{hp}|n/{max_hp} {_hp_bar(hp, max_hp)}   "
		f"{THEME['muted']}Status|n: {status_str}"
	)
	lines.append(
		f"{THEME['muted']}Nature|n: {THEME['value']}{nature}|n   "
		f"{THEME['muted']}Ability|n: {THEME['value']}{ability}|n   "
		f"{THEME['muted']}Held|n: {THEME['value']}{held}|n"
	)

	stats = {STAT_KEY_MAP.get(k, k): v for k, v in get_stats(pokemon).items()}
	headers = [
		DISPLAY_STAT_MAP[s]
		for s in [
			"hp",
			"attack",
			"defense",
			"special_attack",
			"special_defense",
			"speed",
		]
	]
	table = EvTable(*headers, border="table")
	table.add_row(
		*(
			str(stats.get(s, "?"))
			for s in [
				"hp",
				"attack",
				"defense",
				"special_attack",
				"special_defense",
				"speed",
			]
		)
	)
	lines.append(str(table))

	iv_ev = _maybe_stat_breakdown(pokemon)
	if iv_ev:
		lines.append(f"{THEME['muted']}IV/EV Breakdown|n")
		lines.append(iv_ev)

	moves_display: list = []
	slots_qs = getattr(pokemon, "activemoveslot_set", None)
	if slots_qs:
		try:
			qs = list(slots_qs.all().order_by("slot"))
		except Exception:
			try:
				qs = list(slots_qs.order_by("slot"))
			except Exception:
				qs = list(slots_qs)
		bonuses = getattr(pokemon, "pp_bonuses", {}) or {}
		for slot_obj in qs[:4]:
			move_obj = getattr(slot_obj, "move", None)
			if not move_obj:
				continue
			mname = getattr(move_obj, "name", str(move_obj))
			cur_pp = getattr(slot_obj, "current_pp", None)
			norm = re.sub(r"[\s'\-]", "", mname.lower())
			dex_entry = MOVEDEX.get(norm)
			base_pp = getattr(dex_entry, "pp", None)
			if base_pp is None and isinstance(dex_entry, dict):
				base_pp = dex_entry.get("pp")
			max_pp = None
			if base_pp is not None:
				max_pp = int(base_pp) + int(bonuses.get(norm, 0))
			if cur_pp is None:
				cur_pp = max_pp
			moves_display.append(SimpleNamespace(name=mname, current_pp=cur_pp, max_pp=max_pp))
	else:
		moves_display.extend(getattr(pokemon, "moves", []) or [])

	if mode in ("full", "moves"):
		lines.append(_title_bar("Moves"))
		for mv in moves_display:
			lines.append("  " + format_move_details(mv))

	hatch = getattr(pokemon, "hatch", None)
	if getattr(pokemon, "egg", False):
		lines.append(get_egg_description(hatch or 0))

	if mode == "brief":
		lines = []
		type_brief = "/".join(t[:3].upper() for t in (types or [])) or "?"
		stat_spe = stats.get("speed", "?")
		lines.append(
			f"{THEME['value']}{name}|n "
			f"(Lv {level} {type_brief})  "
			f"HP {hp}/{max_hp}  "
			f"Spe {stat_spe}  "
			f"{THEME['muted']}[{status_str}]|n"
		)
		if moves_display:
			mvnames = [getattr(mv, "name", str(mv)) for mv in moves_display[:4]]
			lines.append(f"{THEME['muted']}Moves|n: {', '.join(mvnames)}")
		return "\n".join(lines)

	return "\n".join(lines)
