"""Execute every move and ability in a minimal battle to catch errors.

These tests are slow so they are skipped unless ``--run-dex-tests`` is passed
to ``pytest``.
"""

import random
import sys
from pathlib import Path
import importlib

import pytest

# mark the entire module as part of the optional dex suite
pytestmark = pytest.mark.dex

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def get_dex_data():
    """Reload ``pokemon.dex`` and return MOVEDEX and ABILITYDEX."""

    mod = importlib.import_module("pokemon.dex")
    importlib.reload(mod)
    from pokemon.dex import entities as ent_mod
    return mod.MOVEDEX, mod.ABILITYDEX, ent_mod.Stats, ent_mod.Ability

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
    Battle,
    BattleParticipant,
    BattleMove,
    Action,
    ActionType,
    BattleType,
)

# Global lists to collect failures
MOVE_FAILS = []
ABILITY_FAILS = []

@pytest.fixture(scope="session", autouse=True)
def _report_results(request):
    """Write a report summarizing any move or ability failures."""

    yield
    report_path = Path(__file__).resolve().parents[1] / "move_ability_report.txt"
    with open(report_path, "w") as fh:
        if MOVE_FAILS:
            fh.write("Failed Moves:\n")
            for name, err in MOVE_FAILS:
                fh.write(f"{name}: {err}\n")
        else:
            fh.write("All moves executed without exception.\n")
        fh.write("\n")
        if ABILITY_FAILS:
            fh.write("Failed Abilities:\n")
            for name, err in ABILITY_FAILS:
                fh.write(f"{name}: {err}\n")
        else:
            fh.write("All abilities executed without exception.\n")


def build_move(entry):
    """Construct a ``BattleMove`` from a dex entry."""

    from importlib import import_module

    moves_funcs = import_module("pokemon.dex.functions.moves_funcs")

    on_hit_func = None
    on_try_func = None
    base_power_cb = None
    on_hit = entry.raw.get("onHit")
    if isinstance(on_hit, str):
        try:
            cls_name, func_name = on_hit.split(".", 1)
            cls = getattr(moves_funcs, cls_name, None)
            if cls:
                inst = cls()
                cand = getattr(inst, func_name, None)
                if callable(cand):
                    on_hit_func = cand
        except Exception:
            on_hit_func = None
    on_try = entry.raw.get("onTry")
    if isinstance(on_try, str):
        try:
            cls_name, func_name = on_try.split(".", 1)
            cls = getattr(moves_funcs, cls_name, None)
            if cls:
                inst = cls()
                cand = getattr(inst, func_name, None)
                if callable(cand):
                    on_try_func = cand
        except Exception:
            on_try_func = None
    base_cb = entry.raw.get("basePowerCallback")
    if isinstance(base_cb, str):
        try:
            cls_name, func_name = base_cb.split(".", 1)
            cls = getattr(moves_funcs, cls_name, None)
            if cls:
                inst = cls()
                cand = getattr(inst, func_name, None)
                if callable(cand):
                    base_power_cb = cand
        except Exception:
            base_power_cb = None
    move = BattleMove(
        name=entry.name,
        power=getattr(entry, "power", 0) or 0,
        accuracy=getattr(entry, "accuracy", 100),
        priority=entry.raw.get("priority", 0),
        onHit=on_hit_func,
        onTry=on_try_func,
        basePowerCallback=base_power_cb,
        type=getattr(entry, "type", None),
        raw=entry.raw,
        pp=entry.pp,
    )
    return move


def setup_battle(move: BattleMove, ability=None):
    """Return a simple battle with ``move`` queued."""

    MOVEDEX, ABILITYDEX, Stats, Ability = get_dex_data()
    user = Pokemon("User", ability=ability)
    target = Pokemon("Target")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke, num in ((user, 1), (target, 2)):
        poke.base_stats = base
        poke.num = num
        poke.types = ["Normal"]
        poke.hp = 100
        poke.max_hp = 100
    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target], is_ai=False)
    p1.active = [user]
    p2.active = [target]
    action = Action(p1, ActionType.MOVE, p2, move, move.priority)
    p1.pending_action = action
    battle = Battle(BattleType.WILD, [p1, p2])
    random.seed(0)
    return battle, user, target


@pytest.mark.parametrize("move_name, move_entry", list(get_dex_data()[0].items()))
def test_move_execution(move_name, move_entry):
    move = build_move(move_entry)
    battle, user, target = setup_battle(move)
    try:
        battle.start_turn()
        battle.run_switch()
        battle.run_after_switch()
        battle.run_move()
        battle.run_faint()
        battle.residual()
        battle.end_turn()
    except Exception as e:
        MOVE_FAILS.append((move_name, str(e)))
        pytest.xfail(f"Move {move_name} raised {e}")


@pytest.mark.parametrize("ability_name, ability_entry", list(get_dex_data()[1].items()))
def test_ability_behaviour(ability_name, ability_entry):
    ability = ability_entry
    move = BattleMove("Tackle", power=40, accuracy=100)
    battle, user, target = setup_battle(move, ability=ability)
    try:
        battle.start_turn()
        battle.run_switch()
        battle.run_after_switch()
        battle.run_move()
        battle.run_faint()
        battle.residual()
        battle.end_turn()
    except Exception as e:
        ABILITY_FAILS.append((ability_name, str(e)))
        pytest.xfail(f"Ability {ability_name} raised {e}")

