import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def setup_env():
    utils_stub = types.ModuleType("pokemon.battle.utils")
    utils_stub.get_modified_stat = lambda p, s: getattr(p.base_stats, s, 0)
    utils_stub.apply_boost = lambda *a, **k: None
    pkg_battle = types.ModuleType("pokemon.battle")
    pkg_battle.__path__ = []
    pkg_battle.utils = utils_stub
    pkg_root = types.ModuleType("pokemon")
    pkg_root.__path__ = []
    pkg_root.battle = pkg_battle
    sys.modules["pokemon"] = pkg_root
    sys.modules["pokemon.battle"] = pkg_battle
    sys.modules["pokemon.battle.utils"] = utils_stub

    ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
    ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
    ent_mod = importlib.util.module_from_spec(ent_spec)
    sys.modules[ent_spec.name] = ent_mod
    ent_spec.loader.exec_module(ent_mod)
    Stats = ent_mod.Stats
    Move = ent_mod.Move

    pokemon_dex = types.ModuleType("pokemon.dex")
    pokemon_dex.__path__ = []
    pokemon_dex.entities = ent_mod
    pokemon_dex.Move = ent_mod.Move
    pokemon_dex.Pokemon = ent_mod.Pokemon
    sys.modules["pokemon.dex"] = pokemon_dex
    sys.modules["pokemon.dex.functions"] = types.ModuleType("pokemon.dex.functions")
    pkg_root.dex = pokemon_dex

    data_stub = types.ModuleType("pokemon.data")
    data_stub.__path__ = []
    data_stub.TYPE_CHART = {}
    sys.modules["pokemon.data"] = data_stub

    damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
    d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
    d_mod = importlib.util.module_from_spec(d_spec)
    sys.modules[d_spec.name] = d_mod
    d_spec.loader.exec_module(d_mod)
    pkg_battle.damage_calc = d_mod.damage_calc

    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = bd_mod
    bd_spec.loader.exec_module(bd_mod)
    Pokemon = bd_mod.Pokemon

    moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
    mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
    mv_mod = importlib.util.module_from_spec(mv_spec)
    sys.modules[mv_spec.name] = mv_mod
    mv_spec.loader.exec_module(mv_mod)
    Fly = mv_mod.Fly
    Dig = mv_mod.Dig

    def cleanup():
        for m in [
            "pokemon",
            "pokemon.battle",
            "pokemon.battle.utils",
            "pokemon.dex",
            "pokemon.dex.functions",
            "pokemon.dex.entities",
            "pokemon.data",
            "pokemon.battle.damage",
            "pokemon.battle.battledata",
        ]:
            sys.modules.pop(m, None)

    return {
        "Pokemon": Pokemon,
        "Move": Move,
        "Stats": Stats,
        "Fly": Fly,
        "Dig": Dig,
        "pkg_battle": pkg_battle,
        "cleanup": cleanup,
    }


def setup_pokemon(env):
    Pokemon = env["Pokemon"]
    Stats = env["Stats"]
    user = Pokemon("User")
    target = Pokemon("Target")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke, num in ((user, 1), (target, 2)):
        poke.base_stats = base
        poke.num = num
        poke.types = ["Normal"]
    return user, target


def run_two_turn(move_cls, move_obj, volatile, env):
    user, target = setup_pokemon(env)
    move = move_cls()
    start = target.hp
    assert move.onTryMove(user) is False
    assert user.volatiles.get(volatile)
    assert target.hp == start
    assert move.onTryMove(user) is True
    dmg_res = env["pkg_battle"].damage_calc(user, target, move_obj)
    dmg = sum(dmg_res.debug.get("damage", []))
    if dmg:
        target.hp = max(0, target.hp - dmg)
    assert volatile not in user.volatiles
    assert target.hp < start


def test_fly_two_turn_damage_and_cleanup():
    env = setup_env()
    Move = env["Move"]
    move_obj = Move("Fly", 0, "Flying", "Physical", 90, 100, None, {})
    try:
        run_two_turn(env["Fly"], move_obj, "fly", env)
    finally:
        env["cleanup"]()


def test_dig_two_turn_damage_and_cleanup():
    env = setup_env()
    Move = env["Move"]
    move_obj = Move("Dig", 0, "Ground", "Physical", 80, 100, None, {})
    try:
        run_two_turn(env["Dig"], move_obj, "dig", env)
    finally:
        env["cleanup"]()


def test_semi_invuln_moves_can_hit():
    env = setup_env()
    Move = env["Move"]
    fly = env["Fly"]()
    dig = env["Dig"]()
    try:
        user, _ = setup_pokemon(env)
        fly.onTryMove(user)
        assert fly.onInvulnerability(user, None, Move("Gust", 0, "Flying", "Special", 40, 100, None, {})) is False
        dig.onTryMove(user)
        assert (
            dig.onInvulnerability(user, None, Move("Earthquake", 0, "Ground", "Physical", 100, 100, None, {})) is False
        )
    finally:
        env["cleanup"]()
