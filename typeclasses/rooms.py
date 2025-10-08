"""
Room

Rooms are simple containers that has no location of their own.

"""

import random
import re
import shutil

from evennia.objects.objects import DefaultRoom

try:
	from evennia.utils.ansi import strip_ansi
except Exception:  # pragma: no cover - fallback if Evennia not available

	def strip_ansi(value: str) -> str:
		return value


from pokemon.battle.battleinstance import BattleSession
from utils.ansi import ansi

try:
	from evennia.utils.logger import log_err, log_info
except Exception:  # pragma: no cover - fallback if Evennia not available
	import logging

	_log = logging.getLogger(__name__)

	def log_info(*args, **kwargs):
		_log.info(*args, **kwargs)


from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
	"""
	Rooms are like any Object, except their location is None
	(which is default). They also use basetype_setup() to
	add locks so they cannot be puppeted or picked up.
	(to change that, use at_object_creation instead)

	See mygame/typeclasses/objects.py for a list of
	properties and methods available on all Objects.
	"""

	pass


class FusionRoom(Room):
	"""Room with support for hunting and shop flags."""

	# -------- Layout configuration --------
	WIDTH_DEFAULT = 78
	PAD_LEFT = 2
	UI_DEFAULT_MODE = "fancy"  # fancy | simple | sr
	# Theme (color) configuration
	UI_DEFAULT_THEME = "green"  # name of theme
	THEMES = {
		# primary = frame/section headings, accent = ids or small notes
		"green": {"primary": "|g", "accent": "|y"},
		"blue": {"primary": "|b", "accent": "|y"},
		"red": {"primary": "|r", "accent": "|y"},
		"magenta": {"primary": "|m", "accent": "|y"},
		"cyan": {"primary": "|c", "accent": "|y"},
		"white": {"primary": "|w", "accent": "|y"},
	}

	def at_object_creation(self):
		super().at_object_creation()
		self.db.is_pokemon_center = False
		self.db.is_item_store = False
		self.db.is_item_shop = False
		self.db.store_inventory = {}
		self.db.allow_hunting = False
		self.db.encounter_rate = 100
		self.db.hunt_chart = []
		# Extra hunting related settings
		self.db.npc_chance = 15  # percent chance of trainer battle
		self.db.itemfinder_rate = 5  # percent chance of finding item
		self.db.noitem = False
		self.db.tp_cost = 0
		# Track the current weather affecting this room
		self.db.weather = "clear"

	def set_hunt_chart(self, chart):
		"""Helper to set this room's hunt chart."""
		self.db.hunt_chart = chart

	def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
		super().at_object_receive(moved_obj, source_location, move_type=move_type, **kwargs)
		if not hasattr(moved_obj, "id"):
			return

		battle_id = getattr(moved_obj.db, "battle_id", None)
		if battle_id is not None:
			instance = BattleSession.restore(self, battle_id)
			if instance:
				moved_obj.ndb.battle_instance = instance

	def at_init(self):
		"""Rebuild non-persistent battle data after reload."""
		result = super().at_init()
		log_info(f"FusionRoom #{self.id} running at_init()...")
		battle_ids = getattr(self.db, "battles", None)
		if not isinstance(battle_ids, list):
			log_info("No battle list found or invalid format; skipping restore")
			return result or ""
		for bid in battle_ids:
			log_info(f"Restoring BattleSession {bid} in FusionRoom #{self.id}")
			try:
				BattleSession.restore(self, bid)
			except Exception:
				log_err(
					f"Error restoring BattleSession {bid} in FusionRoom #{self.id}",
					exc_info=True,
				)
		return result or ""

	def get_random_pokemon(self):
		"""Return a Pokémon name selected from the hunt chart."""
		if not self.db.allow_hunting or not self.db.hunt_chart:
			return None
		population = [e.get("name") for e in self.db.hunt_chart]
		weights = [e.get("weight", 1) for e in self.db.hunt_chart]
		return random.choices(population, weights=weights, k=1)[0]

	# ------------------------------------------------------------------
	# Weather helpers
	# ------------------------------------------------------------------
	def get_weather(self) -> str:
		"""Return the current weather in this room."""
		# `self.db` is an AttributeHandler. Using the handler's `get` method can
		# fail if an attribute named ``get`` was inadvertently stored on the
		# object, shadowing the method. Access the attribute directly instead to
		# avoid this edge case.
		return getattr(self.db, "weather", "clear")

	def set_weather(self, weather: str) -> None:
		"""Set the room's weather."""
		self.db.weather = str(weather).lower()

	# ---------- ANSI + width helpers ----------
	def _term_width(self, looker) -> int:
		"""
		Determine target render width for wrapping/alignment.
		Uses a stored client width if available; otherwise system fallback.
		Clamps to a reasonable range for readability.
		"""
		try:
			cols = getattr(looker.ndb, "cols", None) or shutil.get_terminal_size((80, 25)).columns
		except Exception:
			cols = self.WIDTH_DEFAULT + 2
		return max(60, min(int(cols) - 2, 100))

	def _ansi_len(self, s: str) -> int:
		return len(strip_ansi(s or ""))

	# ---------- Theme helpers ----------
	def _theme(self, looker):
		"""Return active theme dict for this viewer."""
		name = getattr(looker.db, "ui_theme", None) or self.UI_DEFAULT_THEME
		return self.THEMES.get(name, self.THEMES[self.UI_DEFAULT_THEME])

	def _tc(self, looker, key: str) -> str:
		"""Theme color code lookup (primary/accent)."""
		return self._theme(looker).get(key, "|g")

	def _wrap_ansi(self, text: str, width: int, indent: int = 0) -> str:
		"""
		Wrap text to `width` while measuring length without ANSI codes.
		Preserves ANSI color in the output.
		"""
		lines = []
		pad = " " * indent
		for raw in (text or "").splitlines():
			raw = raw.rstrip()
			if not raw:
				lines.append("")
				continue
			words = raw.split(" ")
			cur = pad
			cur_len = self._ansi_len(cur)
			for w in words:
				add = w if cur.strip() == "" else " " + w
				if cur_len + self._ansi_len(add) > width:
					lines.append(cur)
					cur = pad + w
				else:
					cur += add
				cur_len = self._ansi_len(cur)
			lines.append(cur)
		return "\n".join(lines)

	def _rule(self, looker, width: int, char: str = "─") -> str:
		"""Section rule using the active theme color."""
		return self._tc(looker, "primary") + (char * width) + "|n"

	def _title_box(self, looker, title: str, width: int) -> str:
		"""
		Boxed header for fancy mode.
		IMPORTANT: Re-apply theme color after the title text to avoid color bleed
		if the title contains |n (e.g., from yellow (#id)).
		"""
		color = self._tc(looker, "primary")
		inner = max(0, width - 2)
		vis = self._ansi_len(title)
		pad_l = max(0, (inner - vis) // 2)
		pad_r = max(0, inner - vis - pad_l)
		top = f"{color}" + "╔" + "═" * inner + "╗" + "|n"
		mid = f"{color}║|n" + " " * pad_l + title + f"{color}" + " " * pad_r + "║|n"
		bot = f"{color}" + "╚" + "═" * inner + "╝" + "|n"
		return "\n".join([top, mid, bot])

	def _ui_mode(self, looker) -> str:
		"""
		Player preference for look rendering.
		Store per-player via:   <player>.db.ui_mode = "fancy"|"simple"|"sr"
		"""
		mode = getattr(looker.db, "ui_mode", None)
		if mode in ("fancy", "simple", "sr"):
			return mode
		return self.UI_DEFAULT_MODE

	def _color_exit_name(self, name: str) -> str:
		"""Return exit name with hotkey parentheses highlighted."""
		if not name:
			return ""

		def repl(match: re.Match) -> str:
			inner = match.group(1)
			return f"|c(|w{inner}|c)"

		colored = re.sub(r"\(([^)]*)\)", repl, name)
		return f"|c{colored}|n"

	# ------------------------------------------------------------------
	# Look/appearance helpers
	# ------------------------------------------------------------------
	def return_appearance(self, looker, **kwargs):
		"""Return the look description for this room."""
		if not looker:
			return ""

		is_builder = looker.check_permstring("Builder")
		ui_mode = self._ui_mode(looker)

		width = min(self._term_width(looker), self.WIDTH_DEFAULT)
		# Visual style per mode
		if ui_mode == "fancy":
			rule = self._rule(looker, width, char="─")
		else:
			rule = self._rule(looker, width, char="-")

		# Title (room name), builder sees dbref.
		title = f"{self._tc(looker, 'primary')}|h{self.key}|n" + (
			f" {self._tc(looker, 'accent')}(#{self.id})|n" if is_builder else ""
		)

		# Description (wrapped, ANSI-safe)
		desc = self.db.desc or self.default_description
		desc_wrapped = self._wrap_ansi(desc, width, indent=self.PAD_LEFT)

		# Fancy gets a boxed header; others just the title line
		if ui_mode == "fancy":
			header = self._title_box(looker, title, width)
			output = [header, "", desc_wrapped]
		else:
			output = [title, "", desc_wrapped]

		# Weather (only if not 'clear')
		weather = (self.get_weather() or "").lower()
		if weather and weather != "clear":
			output.append(self._wrap_ansi(f"|wIt's {weather} here.|n", width, indent=self.PAD_LEFT))

		exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
		prioritized = [ex for ex in exits if ex.db.priority is not None]
		unprioritized = [ex for ex in exits if ex.db.priority is None]
		prioritized.sort(key=lambda e: e.db.priority)
		exit_lines = []
		for ex in prioritized + unprioritized:
			if ex.db.dark and not is_builder:
				continue
			name = self._color_exit_name(ex.key)
			flags = []
			if not ex.access(looker, "traverse"):
				flags.append("|rLocked|n")
			if ex.db.dark:
				flags.append("|mDark|n")
			flag_str = f" [{' '.join(flags)}]" if flags else ""
			id_str = f"|y(#{ex.id})|n" if is_builder else ""

			# align: [name.................][id/flags]
			reserve = max(10, self._ansi_len(id_str + flag_str) + 1)
			name_width = max(10, width - self.PAD_LEFT - reserve)
			shown = name
			if self._ansi_len(name) > name_width:
				# basic truncation; ANSI-safe (might cut mid-sequence only if name inserts codes outside color wrapper)
				shown = self._truncate_ansi(name, name_width)
			spaces = " " * max(1, width - self.PAD_LEFT - self._ansi_len(shown) - self._ansi_len(id_str + flag_str))
			exit_lines.append(" " * self.PAD_LEFT + f"{shown}{spaces}{id_str}{flag_str}")

		characters = self.filter_visible(self.contents_get(content_type="character"), looker, **kwargs)
		players = [c for c in characters if c.has_account and not c.attributes.get("npc")]
		# Make sure the looker shows up in the player list even if filtered out
		if looker.has_account and not looker.attributes.get("npc") and looker not in players:
			players.append(looker)
		npcs = [c for c in characters if not c.has_account or c.attributes.get("npc")]

		items = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)

		def _fmt_item(obj):
			"""Return ANSI-formatted item name for fancy/simple view."""
			name = getattr(obj, "key", "") or "Unknown"
			if hasattr(obj, "get_display_name"):
				try:
					name = obj.get_display_name(looker=looker, **kwargs)
				except Exception:
					name = getattr(obj, "key", name) or name
			if is_builder:
				ident = getattr(obj, "id", None)
				ident_str = f"#{ident}" if ident is not None else "#?"
				name += f" |y({ident_str})|n"
				db = getattr(obj, "db", None)
				if getattr(db, "dark", False):
					name += " |m(Dark)|n"
			return name

		item_names = [_fmt_item(obj) for obj in items]

		def _fmt_item_sr(obj):
			"""Return plain-text item name for screen reader mode."""
			base = getattr(obj, "key", "") or "Unknown"
			if hasattr(obj, "get_display_name"):
				try:
					base = obj.get_display_name(looker=looker, **kwargs)
				except Exception:
					base = getattr(obj, "key", base) or base
			text = strip_ansi(base)
			if is_builder:
				ident = getattr(obj, "id", None)
				ident_str = f" #{ident}" if ident is not None else " #?"
				text += ident_str
				db = getattr(obj, "db", None)
				if getattr(db, "dark", False):
					text += " (Dark)"
			return text

		sr_item_lines = [_fmt_item_sr(obj) for obj in items]

		def _fmt_char(c, color="|w"):
			s = f"{color}{c.key}|n"
			if is_builder:
				s += f" |y(#{c.id})|n"
			if getattr(c.db, "dark", False) and is_builder:
				s += " |m(Dark)|n"
			return s

		player_names = [_fmt_char(p, "|w") for p in players]
		npc_names = [_fmt_char(n, "|y") for n in npcs]

		# ----- Render sections depending on ui_mode -----
		box = []
		if ui_mode in ("fancy", "simple"):
			# Decorative headings
			box.extend([rule, f"{self._tc(looker, 'primary')}  :Exits:|n"])
			if exit_lines:
				box.extend(exit_lines)
			else:
				box.append(" " * self.PAD_LEFT + "|xNone|n")
			box.append(rule)
			box.append(f"{self._tc(looker, 'primary')}  :Items:|n")
			if item_names:
				box.append(self._wrap_ansi(", ".join(item_names), width, indent=self.PAD_LEFT))
			else:
				box.append(" " * self.PAD_LEFT + "|xNone|n")
			box.append(rule)
			if player_names:
				box.append(f"{self._tc(looker, 'primary')}  :Players:|n")
				box.append(self._wrap_ansi(", ".join(player_names), width, indent=self.PAD_LEFT))
				box.append(rule)
			if npc_names:
				box.append(f"{self._tc(looker, 'primary')}  :Non-Player Characters:|n")
				box.append(self._wrap_ansi(", ".join(npc_names), width, indent=self.PAD_LEFT))
				box.append(rule)
		else:
			# Screen reader: no boxes, one item per line, explicit labels, minimal punctuation
			box.append("Exits:")
			if exit_lines:
				# Rebuild exit lines without spacing tricks; one-per-line
				for ex in prioritized + unprioritized:
					if ex.db.dark and not is_builder:
						continue
					n = ex.key
					flags = []
					if not ex.access(looker, "traverse"):
						flags.append("Locked")
					if ex.db.dark:
						flags.append("Dark")
					meta = f" #{ex.id}" if is_builder else ""
					flag_text = f" [{' '.join(flags)}]" if flags else ""
					box.append(f"- {n}{meta}{flag_text}")
			else:
				box.append("- None")
			box.append("Items:")
			if sr_item_lines:
				for line in sr_item_lines:
					box.append(f"- {line}")
			else:
				box.append("- None")
			if player_names:
				box.append("Players:")
				for p in players:
					meta = f" #{p.id}" if is_builder else ""
					box.append(f"- {p.key}{meta}")
			if npcs:
				box.append("Non-Player Characters:")
				for n in npcs:
					meta = f" #{n.id}" if is_builder else ""
					box.append(f"- {n.key}{meta}")

		if self.db.is_item_store:
			box.append("|yThere is a store here, use +store/list to see its contents.|n")
		if self.db.is_pokemon_center:
			box.append("|yThere is a Pokemon center here. Use +pokestore to access your Pokemon storage.|n")

		# Finalize output
		output.append("\n".join(box))
		text = "\n".join(output)
		if ui_mode == "sr":
			# Remove color codes and box-drawing chars for screen readers
			text = strip_ansi(text)
			# Replace box-drawing remnants if any slipped through
			text = text.replace("╔", "").replace("╗", "").replace("╚", "").replace("╝", "")
			text = text.replace("║", "")
		return text

	def _truncate_ansi(self, s: str, max_visible: int) -> str:
		"""
		Truncate ANSI-colored string to max_visible characters (visible width),
		preserving ANSI sequences. Adds an ellipsis if truncated.
		"""
		if max_visible <= 0:
			return ""
		if self._ansi_len(s) <= max_visible:
			return s
		out = []
		visible = 0
		i = 0
		while i < len(s) and visible < max_visible - 1:  # leave room for ellipsis
			ch = s[i]
			if ch == "|":  # Evennia-style ANSI pipe codes
				out.append(ch)
				i += 1
				if i < len(s):
					out.append(s[i])  # next char (code letter)
					i += 1
				continue
			out.append(ch)
			visible += 1
			i += 1
		out.append("…")
		return "".join(out)


class BattleRoom(Room):
	"""A basic room for handling battles."""

	def at_object_creation(self):
		super().at_object_creation()
		# Mark as temporary; cleanup should remove this room after battle
		self.locks.add("view:all();delete:perm(Builders)")


class MapRoom(Room):
	"""Room representing a virtual 2D grid map."""

	map_width: int = 10
	map_height: int = 10
	tile_display: str = "."
	map_data: dict = {}

	def at_object_creation(self):
		super().at_object_creation()
		if not self.map_data:
			self.map_data = {(x, y): self.tile_display for x in range(self.map_width) for y in range(self.map_height)}

	def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
		super().at_object_receive(moved_obj, source_location, move_type=move_type, **kwargs)
		if not moved_obj.attributes.has("xy"):
			moved_obj.db.xy = (0, 0)
		self.display_map(moved_obj)

	def move_entity(self, entity, dx: int, dy: int) -> None:
		"""Move entity inside the map."""
		x, y = entity.db.xy
		new_x = max(0, min(self.map_width - 1, x + dx))
		new_y = max(0, min(self.map_height - 1, y + dy))
		entity.db.xy = (new_x, new_y)
		self.display_map(entity)

	def display_map(self, viewer) -> None:
		"""Display a simple ASCII map to viewer."""
		output = "|w-- Virtual Map --|n\n"
		px, py = viewer.db.xy
		for j in range(self.map_height):
			for i in range(self.map_width):
				if (i, j) == (px, py):
					output += ansi.RED("@")
				else:
					output += self.map_data.get((i, j), self.tile_display)
			output += "\n"
		viewer.msg(output)
