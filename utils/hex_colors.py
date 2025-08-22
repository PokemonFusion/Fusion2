"""
Truecolor 24bit hex color support, on the form `|#00FF00`, `|[00FF00` or `|#0F0` or `|[#0F0`
"""

import re


class HexColors:
	"""Convert Evennia-style hex color codes to ANSI sequences."""

	_RE_FG = r"\|#"
	_RE_BG = r"\|\[#"
	_RE_FG_OR_BG = r"\|\[?#"
	_RE_HEX_LONG = "[0-9a-fA-F]{6}"
	_RE_HEX_SHORT = "[0-9a-fA-F]{3}"
	_RE_BYTE = "[0-2]?[0-9]?[0-9]"
	_RE_XTERM_TRUECOLOR = rf"\[([34])8;2;({_RE_BYTE});({_RE_BYTE});({_RE_BYTE})m"

	# Used in hex_sub
	_RE_HEX_PATTERN = f"({_RE_FG_OR_BG})({_RE_HEX_LONG}|{_RE_HEX_SHORT})"

	_GREYS = "abcdefghijklmnopqrstuvwxyz"

	TRUECOLOR_FG = rf"\x1b[38;2;{_RE_BYTE};{_RE_BYTE};{_RE_BYTE}m"
	TRUECOLOR_BG = rf"\x1b[48;2;{_RE_BYTE};{_RE_BYTE};{_RE_BYTE}m"

	hex_sub = re.compile(rf"{_RE_HEX_PATTERN}", re.DOTALL)

	def _split_hex_to_bytes(self, tag: str) -> tuple[str, str, str]:
		"""Split a hex string into byte pairs."""
		strip_leading = re.compile(rf"{self._RE_FG_OR_BG}")
		tag = strip_leading.sub("", tag)
		if len(tag) == 6:
			r, g, b = (tag[i : i + 2] for i in range(0, 6, 2))
		else:
			r, g, b = (tag[i : i + 1] * 2 for i in range(0, 3))
		return r, g, b

	def _grey_int(self, num: int) -> int:
		return round(max((int(num) - 8), 0) / 10)

	def _hue_int(self, num: int) -> int:
		return round(max((int(num) - 45), 0) / 40)

	def _hex_to_rgb_24_bit(self, hex_code: str) -> tuple[int, int, int]:
		hex_code = re.sub(rf"{self._RE_FG_OR_BG}", "", hex_code)
		r, g, b = self._split_hex_to_bytes(hex_code)
		return int(r, 16), int(g, 16), int(b, 16)

	def _rgb_24_bit_to_256(self, r: int, g: int, b: int) -> tuple[int, int, int]:
		return self._hue_int(r), self._hue_int(g), self._hue_int(b)

	def sub_truecolor(self, match: re.Match, truecolor: bool = False) -> str:
		indicator, tag = match.groups()
		indicator = indicator.replace("#", "")
		r, g, b = self._hex_to_rgb_24_bit(tag)
		if not truecolor:
			r, g, b = self._rgb_24_bit_to_256(r, g, b)
			return f"{indicator}{r}{g}{b}"
		else:
			seq = "\033["
			seq += "4" if "[" in indicator else "3"
			seq += f"8;2;{r};{g};{b}m"
			return seq

	def xterm_truecolor_to_html_style(self, fg: str = "", bg: str = "") -> str:
		prop = 'style="'
		if fg:
			res = re.search(self._RE_XTERM_TRUECOLOR, fg, re.DOTALL)
			fg_bg, r, g, b = res.groups()
			r = hex(int(r))[2:].zfill(2)
			g = hex(int(g))[2:].zfill(2)
			b = hex(int(b))[2:].zfill(2)
			prop += f"color: #{r}{g}{b};"
		if bg:
			res = re.search(self._RE_XTERM_TRUECOLOR, bg, re.DOTALL)
			fg_bg, r, g, b = res.groups()
			r = hex(int(r))[2:].zfill(2)
			g = hex(int(g))[2:].zfill(2)
			b = hex(int(b))[2:].zfill(2)
			prop += f"background-color: #{r}{g}{b};"
		prop += '"'
		return prop
