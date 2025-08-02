import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def setup_modules():
    originals = {name: sys.modules.get(name) for name in [
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.battle.engine",
        "pokemon.battle.battledata",
        "pokemon.dex.functions.moves_funcs",
        "pokemon.dex.functions.abilities_funcs",
        "pokemon.dex",
        "pokemon.data",
    ]}

    pkg_battle = types.ModuleType("pokemon.battle")
    pkg_battle.__path__ = []
    utils_stub = types.ModuleType("pokemon.battle.utils")
    utils_stub.apply_boost = lambda *args, **kwargs: None
    pkg_battle.utils = utils_stub
    sys.modules["pokemon.battle"] = pkg_battle
    sys.modules["pokemon.battle.utils"] = utils_stub

    ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
    ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
    ent_mod = importlib.util.module_from_spec(ent_spec)
    sys.modules[ent_spec.name] = ent_mod
    ent_spec.loader.exec_module(ent_mod)
    Stats = ent_mod.Stats
    Ability = ent_mod.Ability

    pokemon_dex = types.ModuleType("pokemon.dex")
    pokemon_dex.__path__ = []
    pokemon_dex.entities = ent_mod
    pokemon_dex.MOVEDEX = {}
    pokemon_dex.Move = ent_mod.Move
    pokemon_dex.Pokemon = ent_mod.Pokemon
    sys.modules["pokemon.dex"] = pokemon_dex

    data_stub = types.ModuleType("pokemon.data")
    data_stub.__path__ = []
    data_stub.TYPE_CHART = {}
    sys.modules["pokemon.data"] = data_stub

    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = bd_mod
    bd_spec.loader.exec_module(bd_mod)
    Pokemon = bd_mod.Pokemon

    eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
    eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
    engine = importlib.util.module_from_spec(eng_spec)
    sys.modules[eng_spec.name] = engine
    eng_spec.loader.exec_module(engine)

    moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
    mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
    mv_mod = importlib.util.module_from_spec(mv_spec)
    sys.modules[mv_spec.name] = mv_mod
    mv_spec.loader.exec_module(mv_mod)

    abil_path = os.path.join(ROOT, "pokemon", "dex", "functions", "abilities_funcs.py")
    ab_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.abilities_funcs", abil_path)
    ab_mod = importlib.util.module_from_spec(ab_spec)
    sys.modules[ab_spec.name] = ab_mod
    ab_spec.loader.exec_module(ab_mod)

    return Stats, Ability, Pokemon, engine, mv_mod, ab_mod, originals


def cleanup_modules(originals):
    for name, mod in originals.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


def test_imposter_transforms_on_switch_in():
    Stats, Ability, Pokemon, engine, mv_mod, ab_mod, originals = setup_modules()

    BattleParticipant = engine.BattleParticipant
    Battle = engine.Battle
    BattleType = engine.BattleType

    ability = Ability(name="Imposter", num=150, raw={
        "onStart": ab_mod.Imposter().onStart,
        "onSwitchIn": ab_mod.Imposter().onSwitchIn,
    })

    user = Pokemon("User", ability=ability)
    target = Pokemon("Target")
    base_user = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    base_target = Stats(hp=100, atk=70, def_=60, spa=60, spd=60, spe=60)
    user.base_stats = base_user
    target.base_stats = base_target
    user.num = 1
    target.num = 2
    user.types = ["Normal"]
    target.types = ["Fire"]

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target], is_ai=False)
    p1.active = [user]
    p2.active = [target]

    battle = Battle(BattleType.WILD, [p1, p2])
    random.seed(0)

    try:
        battle.start_turn()
        battle.run_switch()

        assert getattr(user, "transformed", False)
        assert "transform_backup" in user.tempvals
        assert user.base_stats.attack == base_target.attack
    finally:
        cleanup_modules(originals)
