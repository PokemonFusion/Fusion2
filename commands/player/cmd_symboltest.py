"""Command for rendering client glyph diagnostics."""

from evennia.commands.command import Command

ANSI_COLORS = (
	("|r", "r"),
	("|g", "g"),
	("|y", "y"),
	("|b", "b"),
	("|m", "m"),
	("|c", "c"),
	("|w", "w"),
	("|x", "x"),
	("|R", "R"),
	("|G", "G"),
	("|Y", "Y"),
	("|B", "B"),
	("|M", "M"),
	("|C", "C"),
	("|W", "W"),
	("|X", "X"),
)

TRUECOLOR_SAMPLES = (
	("|#FF55CC", "pink"),
	("|#00B7FF", "cyan"),
	("|#00FF00", "green"),
	("|#FFD400", "gold"),
)

UI_GLYPHS = (
	("female sign", (0x2640,), "|M", "F"),
	("female text", (0x2640, 0xFE0E), "|M", "F"),
	("male sign", (0x2642,), "|C", "M"),
	("male text", (0x2642, 0xFE0E), "|C", "M"),
	("full pip", (0x25CF,), "|g", "O"),
	("half pip", (0x25D0,), "|y", "o"),
	("faint pip", (0x00B7,), "|x", "."),
	("fainted", (0x00D7,), "|r", "X"),
	("hp block", (0x2588,), "|g", "|"),
	("en dash", (0x2013,), "|x", "-"),
	("em dash", (0x2014,), "|x", "-"),
	("bullet", (0x2022,), "|w", "*"),
	("ellipsis", (0x2026,), "|w", "..."),
	("timer", (0x23F1,), "|w", "t"),
	("pokemon e", (0x00E9,), "|w", "e"),
	("box h", (0x2500,), "|W", "-"),
	("box v", (0x2502,), "|W", "|"),
	("box tl", (0x250C,), "|W", "+"),
	("box tr", (0x2510,), "|W", "+"),
	("box bl", (0x2514,), "|W", "+"),
	("box br", (0x2518,), "|W", "+"),
	("turn tl", (0x256D,), "|W", "+"),
	("turn tr", (0x256E,), "|W", "+"),
	("turn bl", (0x2570,), "|W", "+"),
	("turn br", (0x256F,), "|W", "+"),
)


def _glyph(codepoints: tuple[int, ...]) -> str:
	return "".join(chr(codepoint) for codepoint in codepoints)


def _codepoint_label(text: str) -> str:
	return " ".join(f"U+{ord(char):04X}" for char in text)


def _render_ascii_grid() -> list[str]:
	chars = [chr(codepoint) for codepoint in range(32, 127)]
	lines = ["|WPrintable ASCII 32-126|n"]
	for start in range(0, len(chars), 16):
		chunk = "".join(chars[start : start + 16])
		first = 32 + start
		last = first + len(chunk) - 1
		lines.append(f"{first:03d}-{last:03d}: {chunk}")
	return lines


def _render_color_rows() -> list[str]:
	bright = " ".join(f"{tag}{label}|n" for tag, label in ANSI_COLORS[:8])
	normal = " ".join(f"{tag}{label}|n" for tag, label in ANSI_COLORS[8:])
	truecolor = " ".join(f"{tag}{label}|n" for tag, label in TRUECOLOR_SAMPLES)
	female = chr(0x2640)
	male = chr(0x2642)
	female_text = female + chr(0xFE0E)
	male_text = male + chr(0xFE0E)
	return [
		"|WColor Stress|n",
		f"ANSI bright: {bright}",
		f"ANSI normal: {normal}",
		f"Truecolor:   {truecolor}",
		"Female raw:  " + " ".join(f"{tag}{female}|n" for tag, _ in ANSI_COLORS),
		"Female text: " + " ".join(f"{tag}{female_text}|n" for tag, _ in ANSI_COLORS),
		"Male raw:    " + " ".join(f"{tag}{male}|n" for tag, _ in ANSI_COLORS),
		"Male text:   " + " ".join(f"{tag}{male_text}|n" for tag, _ in ANSI_COLORS),
	]


def _render_ui_glyphs() -> list[str]:
	lines = ["|WUI Glyph Samples|n"]
	lines.append("name          codepoint      glyph  ascii")
	lines.append("------------  -------------  -----  -----")
	for name, codepoints, color, fallback in UI_GLYPHS:
		glyph = _glyph(codepoints)
		lines.append(
			f"{name:<12}  {_codepoint_label(glyph):<13}  {color}{glyph}|n     {color}{fallback}|n"
		)
	return lines


def render_symbol_test(mode: str = "all") -> str:
	"""Return a screenshot-friendly client symbol diagnostic sheet."""

	mode = (mode or "all").strip().lower()
	sections = []
	if mode in ("all", "ascii"):
		sections.append(_render_ascii_grid())
	if mode in ("all", "ui", "glyph", "glyphs"):
		sections.append(_render_ui_glyphs())
	if mode in ("all", "color", "colors"):
		sections.append(_render_color_rows())
	if not sections:
		return "Usage: +symboltest [all|ascii|ui|colors]"
	lines = []
	for section in sections:
		if lines:
			lines.append("")
		lines.extend(section)
	return "\n".join(lines)


class CmdSymbolTest(Command):
	"""Render a screenshot-friendly symbol and color test sheet.

	Usage:
		+symboltest [all|ascii|ui|colors]
	"""

	key = "+symboltest"
	aliases = ["+glyphs", "+uisymbols"]
	locks = "cmd:all()"
	help_category = "General"

	def func(self):
		mode = (self.args or "all").strip().lower() or "all"
		self.caller.msg(render_symbol_test(mode))
