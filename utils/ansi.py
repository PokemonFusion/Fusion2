from evennia.utils import ansi as _ansi


def _make_color_func(code: str):
    """Return a simple colour-wrapper for `code`."""
    return lambda text: _ansi.parse_ansi(f"|{code}{text}|n")

# Add convenience colour functions if they don't exist in Evennia's ansi module
for _name, _code in [
    ("RED", "r"),
    ("GREEN", "g"),
    ("YELLOW", "y"),
    ("BLUE", "b"),
    ("MAGENTA", "m"),
    ("CYAN", "c"),
]:
    if not hasattr(_ansi, _name):
        setattr(_ansi, _name, _make_color_func(_code))

ansi = _ansi
