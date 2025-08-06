import os
import sys
import types
import importlib.util
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def setup_env():
    for mod in [
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.battle.battledata",
        "pokemon.battle.engine",
        "pokemon.dex.functions.moves_funcs",
    ]:
        sys.modules.pop(mod, None)

    pkg_battle = types.ModuleType("pokemon.battle")
    utils_stub = types.ModuleType("pokemon.battle.utils")
    utils_stub.apply_boost = lambda *a, **k: None
    pkg_battle.utils = utils_stub
    pkg_battle.__path__ = []
    sys.modules["pokemon.battle"] = pkg_battle
    sys.modules["pokemon.battle.utils"] = utils_stub

    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = bd_mod
    bd_spec.loader.exec_module(bd_mod)
    Pokemon = bd_mod.Pokemon

    eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
    eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
    eng_mod = importlib.util.module_from_spec(eng_spec)
    sys.modules[eng_spec.name] = eng_mod
    eng_spec.loader.exec_module(eng_mod)
    Battle = eng_mod.Battle
    BattleParticipant = eng_mod.BattleParticipant
    BattleType = eng_mod.BattleType

    mv_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
    mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", mv_path)
    mv_mod = importlib.util.module_from_spec(mv_spec)
    sys.modules[mv_spec.name] = mv_mod
    mv_spec.loader.exec_module(mv_mod)

    return {
        "Pokemon": Pokemon,
        "Battle": Battle,
        "BattleParticipant": BattleParticipant,
        "BattleType": BattleType,
        "moves": mv_mod,
    }


@pytest.fixture
def env():
    data = setup_env()
    yield data
    for mod in [
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.battle.battledata",
        "pokemon.battle.engine",
        "pokemon.dex.functions.moves_funcs",
    ]:
        sys.modules.pop(mod, None)


def setup_battle(env):
    Pokemon = env["Pokemon"]
    Battle = env["Battle"]
    BattleParticipant = env["BattleParticipant"]
    BattleType = env["BattleType"]
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    user.volatiles = {}
    target.volatiles = {}
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    return battle, user, target


def test_attract_prevents_move(env, monkeypatch):
    battle, user, target = setup_battle(env)
    mv_mod = env["moves"]
    mv_mod.Attract().onStart(user, target)
    monkeypatch.setattr(mv_mod, "random", lambda: 0.0)
    assert battle.status_prevents_move(target)


def test_aquaring_heals_on_residual(env):
    battle, user, _ = setup_battle(env)
    mv_mod = env["moves"]
    user.hp = 50
    mv_mod.Aquaring().onStart(user)
    battle.residual()
    assert user.hp == 56
