import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def setup_env():
    sys.path.insert(0, ROOT)
    # stub battle package and utils
    pkg_battle = types.ModuleType("pokemon.battle")
    pkg_battle.__path__ = []
    utils_stub = types.ModuleType("pokemon.battle.utils")
    utils_stub.get_modified_stat = lambda p, s: getattr(p.base_stats, s, 0)
    utils_stub.apply_boost = lambda *a, **k: None
    pkg_battle.utils = utils_stub
    sys.modules["pokemon.battle"] = pkg_battle
    sys.modules["pokemon.battle.utils"] = utils_stub

    # load entities
    ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
    ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
    ent_mod = importlib.util.module_from_spec(ent_spec)
    sys.modules[ent_spec.name] = ent_mod
    ent_spec.loader.exec_module(ent_mod)

    # minimal dex package
    pokemon_dex = types.ModuleType("pokemon.dex")
    pokemon_dex.__path__ = []
    pokemon_dex.entities = ent_mod
    pokemon_dex.MOVEDEX = {}
    pokemon_dex.Move = ent_mod.Move
    pokemon_dex.Pokemon = ent_mod.Pokemon
    sys.modules["pokemon.dex"] = pokemon_dex

    # root package
    pkg_root = types.ModuleType("pokemon")
    pkg_root.__path__ = []
    pkg_root.dex = pokemon_dex
    pkg_root.battle = pkg_battle
    sys.modules["pokemon"] = pkg_root

    # data stub
    data_stub = types.ModuleType("pokemon.data")
    data_stub.__path__ = []
    data_stub.TYPE_CHART = {}
    sys.modules["pokemon.data"] = data_stub

    # load damage module
    dmg_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
    dmg_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", dmg_path)
    dmg_mod = importlib.util.module_from_spec(dmg_spec)
    sys.modules[dmg_spec.name] = dmg_mod
    dmg_spec.loader.exec_module(dmg_mod)
    pkg_battle.damage_calc = dmg_mod.damage_calc

    # load battledata and engine
    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = bd_mod
    bd_spec.loader.exec_module(bd_mod)

    eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
    eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
    eng_mod = importlib.util.module_from_spec(eng_spec)
    sys.modules[eng_spec.name] = eng_mod
    eng_spec.loader.exec_module(eng_mod)

    return ent_mod, bd_mod, eng_mod


def teardown_env():
    for mod in [
        "pokemon",
        "pokemon.dex",
        "pokemon.data",
        "pokemon.battle.utils",
        "pokemon.battle.damage",
        "pokemon.battle.battledata",
        "pokemon.battle.engine",
        "pokemon.battle",
    ]:
        sys.modules.pop(mod, None)
    if sys.path and sys.path[0] == ROOT:
        sys.path.pop(0)


def test_ability_and_item_modify_priority():
    ent_mod, bd_mod, eng_mod = setup_env()
    Ability = ent_mod.Ability
    Item = ent_mod.Item
    Stats = ent_mod.Stats
    Pokemon = bd_mod.Pokemon
    Battle = eng_mod.Battle
    BattleMove = eng_mod.BattleMove
    BattleParticipant = eng_mod.BattleParticipant
    Action = eng_mod.Action
    ActionType = eng_mod.ActionType

    abil = Ability(name="A", num=0, raw={"onModifyPriority": lambda pr, **_: pr + 1})
    item = Item(name="I", num=0, raw={"onFractionalPriority": lambda **_: 0.1})

    user = Pokemon("User")
    user.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=30)
    user.ability = abil
    user.item = item
    user.moves = [BattleMove("Growl", priority=0)]

    opp = Pokemon("Opp")
    opp.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=40)
    opp.moves = [BattleMove("Tackle", priority=0)]

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [opp], is_ai=False)
    p1.active = [user]
    p2.active = [opp]

    a1 = Action(p1, ActionType.MOVE, p2, user.moves[0], user.moves[0].priority)
    a2 = Action(p2, ActionType.MOVE, p1, opp.moves[0], opp.moves[0].priority)

    battle = Battle.__new__(Battle)
    battle.field = bd_mod.Field()
    ordered = battle.order_actions([a1, a2])
    teardown_env()
    assert ordered[0] is a1


def test_quash_forces_last():
    ent_mod, bd_mod, eng_mod = setup_env()
    Stats = ent_mod.Stats
    Pokemon = bd_mod.Pokemon
    Battle = eng_mod.Battle
    BattleMove = eng_mod.BattleMove
    BattleParticipant = eng_mod.BattleParticipant
    Action = eng_mod.Action
    ActionType = eng_mod.ActionType

    user = Pokemon("User")
    user.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=60)
    user.moves = [BattleMove("Tackle", priority=0)]

    opp = Pokemon("Opp")
    opp.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    opp.moves = [BattleMove("Tackle", priority=0)]
    opp.tempvals = {"quash": True}

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [opp], is_ai=False)
    p1.active = [user]
    p2.active = [opp]

    a1 = Action(p1, ActionType.MOVE, p2, user.moves[0], user.moves[0].priority)
    a2 = Action(p2, ActionType.MOVE, p1, opp.moves[0], opp.moves[0].priority)

    battle = Battle.__new__(Battle)
    battle.field = bd_mod.Field()
    ordered = battle.order_actions([a1, a2])
    teardown_env()
    assert ordered[-1] is a2


def test_trick_room_reverses_speed():
    ent_mod, bd_mod, eng_mod = setup_env()
    Stats = ent_mod.Stats
    Pokemon = bd_mod.Pokemon
    Battle = eng_mod.Battle
    BattleMove = eng_mod.BattleMove
    BattleParticipant = eng_mod.BattleParticipant
    Action = eng_mod.Action
    ActionType = eng_mod.ActionType

    fast = Pokemon("Fast")
    fast.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=100)
    fast.moves = [BattleMove("Tackle", priority=0)]

    slow = Pokemon("Slow")
    slow.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=10)
    slow.moves = [BattleMove("Tackle", priority=0)]

    p1 = BattleParticipant("P1", [fast], is_ai=False)
    p2 = BattleParticipant("P2", [slow], is_ai=False)
    p1.active = [fast]
    p2.active = [slow]

    a1 = Action(p1, ActionType.MOVE, p2, fast.moves[0], 0)
    a2 = Action(p2, ActionType.MOVE, p1, slow.moves[0], 0)

    battle = Battle.__new__(Battle)
    battle.field = bd_mod.Field()
    battle.field.add_pseudo_weather("trickroom", {"duration": 5})
    ordered = battle.order_actions([a1, a2])
    teardown_env()
    assert ordered[0] is a2
