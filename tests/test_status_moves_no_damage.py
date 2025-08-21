import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def setup_env():
    for mod in [
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.battle.battledata",
        "pokemon.battle.engine",
    ]:
        sys.modules.pop(mod, None)

    pkg_battle = types.ModuleType("pokemon.battle")
    utils_stub = types.ModuleType("pokemon.battle.utils")
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

    dmg_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
    dmg_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", dmg_path)
    dmg_mod = importlib.util.module_from_spec(dmg_spec)
    sys.modules[dmg_spec.name] = dmg_mod
    dmg_spec.loader.exec_module(dmg_mod)

    return {
        "Pokemon": Pokemon,
        "Battle": eng_mod.Battle,
        "BattleParticipant": eng_mod.BattleParticipant,
        "BattleType": eng_mod.BattleType,
        "BattleMove": eng_mod.BattleMove,
        "utils": utils_stub,
        "damage": dmg_mod,
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
    ]:
        sys.modules.pop(mod, None)


def setup_battle(env):
    Pokemon = env["Pokemon"]
    Battle = env["Battle"]
    BattleParticipant = env["BattleParticipant"]
    BattleType = env["BattleType"]
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    return battle, user, target


def test_status_move_applies_boost_without_damage(env, monkeypatch):
    battle, user, target = setup_battle(env)
    called = {}

    def fake_apply_boost(pokemon, boosts):
        called["pokemon"] = pokemon
        called["boosts"] = boosts
        pokemon.boosts = boosts

    monkeypatch.setattr(env["utils"], "apply_boost", fake_apply_boost, raising=False)
    dmg_mod = env["damage"]
    monkeypatch.setattr(dmg_mod.random, "random", lambda: 0.0)
    monkeypatch.setattr(dmg_mod.random, "randint", lambda a, b: b)

    BattleMove = env["BattleMove"]
    move = BattleMove(
        "Howl",
        power=50,
        raw={"category": "Status", "target": "self", "boosts": {"atk": 1}},
    )
    move.execute(user, target, battle)
    assert target.hp == 100
    assert user.boosts.get("atk") == 1
    assert called["pokemon"] is user
    dmg = battle._deal_damage(user, target, move)
    assert dmg == 0
