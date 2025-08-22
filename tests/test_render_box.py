import importlib.util
from pathlib import Path

from utils.battle_display import strip_ansi

spec = importlib.util.spec_from_file_location(
	"box_utils", Path(__file__).resolve().parents[1] / "pokemon" / "ui" / "box_utils.py"
)
box_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(box_utils)
render_box = box_utils.render_box


def ansi_len(s: str) -> int:
	return len(strip_ansi(s or ""))


def rpad(s: str, width: int, fill: str = " ") -> str:
	pad = max(0, width - ansi_len(s))
	return s + (fill * pad)


def _expected_top(title: str, inner: int) -> str:
	title_len = ansi_len(title)
	left = (inner - title_len - 2) // 2
	right = inner - title_len - 2 - left
	return "┌" + ("─" * left) + " " + title + " " + ("─" * right) + "┐"


def test_render_box_centers_title_and_borders():
	inner = 10
	rows = [rpad("hello", inner)]
	result = render_box("Title", inner, rows)
	lines = result.splitlines()
	assert lines[0] == _expected_top("Title", inner)
	assert lines[1] == "│hello     │"
	assert lines[-1] == "└" + ("─" * inner) + "┘"


def test_render_box_footer_and_waiting():
	inner = 12
	rows = [rpad("line", inner)]
	footer = rpad("Footer", inner)
	waiting = rpad("Wait", inner)
	result = render_box("T", inner, rows, footer=footer, waiting=waiting)
	lines = result.splitlines()
	assert lines[0] == _expected_top("T", inner)
	assert lines[1] == "│line        │"
	assert lines[2] == f"│{footer}│"
	assert lines[3] == f"│{waiting}│"
	assert lines[4] == "└" + ("─" * inner) + "┘"
