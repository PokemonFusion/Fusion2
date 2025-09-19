import importlib.util
import os
import random
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


battle_pkg = types.ModuleType("pokemon.battle")
battle_pkg.__path__ = []
sys.modules.setdefault("pokemon.battle", battle_pkg)

battledata = load_module(
    "pokemon.battle.battledata",
    os.path.join(ROOT, "pokemon", "battle", "battledata.py"),
)
engine = load_module(
    "pokemon.battle.engine",
    os.path.join(ROOT, "pokemon", "battle", "engine.py"),
)
damage_mod = load_module(
    "pokemon.battle.damage",
    os.path.join(ROOT, "pokemon", "battle", "damage.py"),
)
entities = load_module(
    "pokemon.dex.entities",
    os.path.join(ROOT, "pokemon", "dex", "entities.py"),
)
items_funcs = load_module(
    "pokemon.dex.functions.items_funcs",
    os.path.join(ROOT, "pokemon", "dex", "functions", "items_funcs.py"),
)


Pokemon = battledata.Pokemon
Battle = engine.Battle
BattleParticipant = engine.BattleParticipant
BattleType = engine.BattleType
Move = battledata.Move
Stats = entities.Stats
Flameorb = items_funcs.Flameorb


def make_stats(value: int = 100) -> Stats:
    return Stats(hp=value, attack=value, defense=value, special_attack=value, special_defense=value, speed=value)


def build_battle(
    *,
    attacker_status=None,
    defender_status=None,
    defender_ability=None,
    defender_types=None,
    attacker_types=None,
):
    attacker = Pokemon("Attacker", level=50, hp=200, max_hp=200)
    defender = Pokemon("Defender", level=50, hp=200, max_hp=200)
    attacker.base_stats = make_stats(120)
    attacker.types = attacker_types or ["Normal"]
    defender.base_stats = make_stats(120)
    defender.types = defender_types or ["Normal"]
    for mon in (attacker, defender):
        mon.boosts = {
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
        }
    if attacker_status:
        attacker.setStatus(attacker_status, source=attacker)
    if defender_status:
        defender.setStatus(defender_status, source=defender)
    if defender_ability:
        defender.ability = defender_ability
    part1 = BattleParticipant("P1", [attacker])
    part2 = BattleParticipant("P2", [defender])
    part1.active = [attacker]
    part2.active = [defender]
    battle = Battle(BattleType.WILD, [part1, part2])
    attacker.battle = battle
    defender.battle = battle
    return battle, attacker, defender


def physical_move(name: str = "Tackle", power: int = 70):
    raw = {"name": name, "category": "Physical", "type": "Normal", "basePower": power, "accuracy": 100}
    move = Move(name)
    move.power = power
    move.type = "Normal"
    move.category = "Physical"
    move.accuracy = 100
    move.raw = raw
    move.key = name.lower()
    return move


def run_damage(attacker, defender, move):
    rng = random.Random(0)
    result = damage_mod.damage_calc(attacker, defender, move, battle=None, rng=rng)
    return result.debug.get("damage", [0])[0]


def test_burn_residual_damage_standard():
    battle, _, burned = build_battle(defender_status="brn")
    burned.max_hp = 160
    burned.hp = 160
    battle.residual()
    assert burned.hp == 160 - (160 // 16)


def test_burn_residual_heatproof():
    battle, _, burned = build_battle(defender_status="brn", defender_ability="Heatproof")
    burned.max_hp = 128
    burned.hp = 128
    battle.residual()
    assert burned.hp == 128 - max(1, 128 // 32)


def test_burn_residual_magic_guard():
    battle, _, burned = build_battle(defender_status="brn", defender_ability="Magic Guard")
    start = burned.hp
    battle.residual()
    assert burned.hp == start


def test_burn_halves_physical_attack():
    _, attacker, defender = build_battle()
    move = physical_move()
    baseline = run_damage(attacker, defender, move)
    attacker.setStatus("brn", source=attacker)
    burned = run_damage(attacker, defender, move)
    assert burned < baseline
    assert abs(burned * 2 - baseline) <= 5


def test_burn_guts_ignores_attack_drop():
    _, attacker, defender = build_battle()
    attacker.ability = "Guts"
    move = physical_move()
    baseline = run_damage(attacker, defender, move)
    attacker.setStatus("brn", source=attacker)
    boosted = run_damage(attacker, defender, move)
    assert boosted == baseline


def test_burn_facade_not_halved():
    _, attacker, defender = build_battle()
    move = physical_move("Facade", 70)
    facade_baseline = run_damage(attacker, defender, move)
    attacker.setStatus("brn", source=attacker)
    facade_burned = run_damage(attacker, defender, move)
    assert facade_burned >= facade_baseline


def test_fire_type_is_immune_to_burn():
    battle, _, defender = build_battle(defender_types=["Fire"])
    defender.hp = defender.max_hp = 100
    result = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect=None)
    assert result is False
    assert defender.status != "brn"


def test_water_veil_blocks_burn():
    battle, _, defender = build_battle(defender_ability="Water Veil")
    result = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0])
    assert not result
    assert defender.status != "brn"


def test_misty_terrain_blocks_external_burn():
    battle, _, defender = build_battle()
    battle.field.terrain = "mistyterrain"
    result = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
    assert not result
    assert defender.status != "brn"


def test_safeguard_blocks_burn():
    battle, _, defender = build_battle()
    defender.side.conditions["safeguard"] = {}
    result = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
    assert not result
    assert defender.status != "brn"


def test_substitute_blocks_move_inflicted_burn():
    battle, _, defender = build_battle()
    defender.volatiles["substitute"] = True
    result = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
    assert not result
    assert defender.status != "brn"


def test_flame_orb_burns_through_protection():
    battle, pokemon, _ = build_battle()
    pokemon.status = 0
    pokemon.side.conditions["safeguard"] = {}
    battle.field.terrain = "mistyterrain"
    orb = Flameorb()
    orb.onResidual(pokemon=pokemon)
    assert pokemon.status == "brn"


def test_flame_orb_respects_immunity():
    battle, pokemon, _ = build_battle(attacker_types=["Fire"])
    pokemon.status = 0
    orb = Flameorb()
    orb.onResidual(pokemon=pokemon)
    assert pokemon.status != "brn"


def test_magic_guard_prevents_chip_but_not_attack_drop():
    _, attacker, defender = build_battle()
    attacker.ability = "Magic Guard"
    attacker.setStatus("brn", source=attacker)
    before = attacker.hp
    battle = attacker.battle
    battle.residual()
    assert attacker.hp == before
    move = physical_move()
    burned_damage = run_damage(attacker, defender, move)
    attacker.setStatus(0)
    normal_damage = run_damage(attacker, defender, move)
    assert burned_damage < normal_damage
