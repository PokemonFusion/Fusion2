"""Tests rendering of battle interfaces from different perspectives."""

import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia.ansi
ansi_mod = types.SimpleNamespace(
    GREEN=lambda s: s,
    YELLOW=lambda s: s,
    RED=lambda s: s,
    parse_ansi=lambda s: s,
)
utils_mod = types.ModuleType("evennia.utils")
utils_mod.ansi = ansi_mod
sys.modules["evennia.utils"] = utils_mod

iface_path = os.path.join(ROOT, "pokemon", "battle", "interface.py")
spec = importlib.util.spec_from_file_location("pokemon.battle.interface", iface_path)
iface = importlib.util.module_from_spec(spec)
sys.modules["pokemon.battle.interface"] = iface
spec.loader.exec_module(iface)
render_interfaces = iface.render_interfaces
from pokemon.battle.state import BattleState


class DummyMon:
    """Simplified Pokémon stub used for interface rendering tests."""

    def __init__(self, name: str, hp: int, max_hp: int) -> None:
        self.name = name
        self.level = 5
        self.hp = hp
        self.max_hp = max_hp
        self.status = ""


class DummyTrainer:
    """Minimal trainer holding a single active Pokémon."""

    def __init__(self, name: str, mon: DummyMon) -> None:
        self.name = name
        self.active_pokemon = mon
        self.team = [mon]


def test_render_interfaces_hp_and_percentages() -> None:
    """The viewer sees absolute HP for their side and percentages for the foe."""

    mon_a = DummyMon("Pika", 15, 20)
    mon_b = DummyMon("Bulba", 30, 60)
    t_a = DummyTrainer("Ash", mon_a)
    t_b = DummyTrainer("Gary", mon_b)
    st = BattleState()

    iface_a, iface_b, iface_w = render_interfaces(t_a, t_b, st)

    # Team A sees its own HP numerically and the opponent in percent
    assert "15/20" in iface_a
    assert "30/60" not in iface_a
    assert "50%" in iface_a

    # Team B mirrors this perspective
    assert "30/60" in iface_b
    assert "15/20" not in iface_b
    assert "75%" in iface_b

    # Watchers should only see percentages for both sides
    assert "15/20" not in iface_w and "30/60" not in iface_w
    assert "50%" in iface_w and "75%" in iface_w
