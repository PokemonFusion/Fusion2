"""Exercise HP bars through real Telnet/HTML ANSI parsing, in SQLite memory."""

import html
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
from django.conf import settings

settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
import django
from django.db.backends.base.base import BaseDatabaseWrapper

_connect = BaseDatabaseWrapper.connect


def memory_only(connection):
    """Reject accidental access to any game database."""
    assert connection.vendor == "sqlite" and connection.settings_dict["NAME"] == ":memory:"
    return _connect(connection)


with patch.object(BaseDatabaseWrapper, "connect", memory_only):
    django.setup()
    from evennia.utils.ansi import parse_ansi
    from evennia.utils.text2html import parse_html

    from pokemon.battle.interface import display_battle_interface
    from pokemon.battle.state import BattleState
    from pokemon.ui.battle_render import _pf1_percent_bar, hp_bar_ascii
    from utils.battle_display import strip_ansi

    for percent in range(101):
        for width in (10, 20, 28):
            raw = hp_bar_ascii(percent, 100, width)
            visible = parse_ansi(raw, strip_ansi=True)
            assert len(visible) == width, (percent, width, visible)
            assert set(visible) <= {"|", "-"}, (percent, visible)
            assert strip_ansi(raw) == visible
            rendered = html.unescape(re.sub(r"<[^>]+>", "", parse_html(raw))).replace("\xa0", " ")
            assert rendered == visible, (percent, rendered, visible)
        raw = _pf1_percent_bar(percent)
        visible = parse_ansi(raw, strip_ansi=True)
        assert len(visible) == 10 and set(visible) <= {"|", " "}, (percent, visible)
        assert strip_ansi(raw) == visible

    mon_a = SimpleNamespace(name="Squirtle", species="Squirtle", level=5, hp=7, max_hp=19, status="par", gender="M")
    mon_b = SimpleNamespace(name="Rattata", species="Rattata", level=5, hp=12, max_hp=18, status="", gender="F")
    player = SimpleNamespace(name="Player", key="Player", active_pokemon=mon_a, team=[mon_a], is_npc=False)
    foe = SimpleNamespace(name="Wild", key="Wild", active_pokemon=mon_b, team=[mon_b], is_npc=True)
    state = BattleState(encounter_kind="wild")
    for style in ("classic_modern", "pf1", "legacy"):
        for width in (60, 78, 100):
            raw = display_battle_interface(player, foe, state, viewer_team="A", style=style, total_width=width)
            visible = parse_ansi(raw, strip_ansi=True)
            assert strip_ansi(raw) == visible, (style, width)
            assert "7/19" in visible or "  7" in visible, visible
            assert not re.search(r"\|n[-| ]", visible), visible
            assert "||n" not in visible, visible

print("Real HP render checks passed: 101 percentages, Telnet/HTML parsing and three HUD styles; SQLite memory only.")
