"""Utility functions for rendering bordered UI boxes."""

from utils.battle_display import strip_ansi


def _ansi_len(s: str) -> int:
	"""Return visible length of a string, ignoring ANSI color codes."""
	return len(strip_ansi(s or ""))


def render_box(
	title: str,
	inner: int,
	rows: list[str],
	footer: str | None = None,
	waiting: str | None = None,
) -> str:
	"""Render a bordered box with a centered title and optional footer/waiting lines.

	Parameters
	----------
	title:
	    Title text to center on the top border.
	inner:
	    Width of the interior of the box (excluding borders).
	rows:
	    Content rows already padded to ``inner`` characters.
	footer:
	    Optional footer line, already padded to ``inner``.
	waiting:
	    Optional "waiting on" line, already padded to ``inner``.
	"""

	border_v = "│"
	border_h = "─"
	corner_l = "┌"
	corner_r = "┐"
	corner_bl = "└"
	corner_br = "┘"

	title_len = _ansi_len(title)
	left_pad = max(0, (inner - title_len - 2) // 2)
	right_pad = max(0, inner - title_len - 2 - left_pad)
	top = corner_l + (border_h * left_pad) + " " + title + " " + (border_h * right_pad) + corner_r

	box_lines = [top]
	box_lines.extend(border_v + row + border_v for row in rows)

	if footer is not None:
		box_lines.append(border_v + footer + border_v)
	if waiting is not None:
		box_lines.append(border_v + waiting + border_v)

	bottom = corner_bl + (border_h * inner) + corner_br
	box_lines.append(bottom)
	return "\n".join(box_lines)
