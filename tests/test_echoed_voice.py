import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Load modules
eng_spec = importlib.util.spec_from_file_location(
    "pokemon.battle.engine", os.path.join(ROOT, "pokemon", "battle", "engine.py")
)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)

bd_spec = importlib.util.spec_from_file_location(
    "pokemon.battle.battledata", os.path.join(ROOT, "pokemon", "battle", "battledata.py")
)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)

mv_spec = importlib.util.spec_from_file_location(
    "pokemon.dex.functions.moves_funcs", os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)
Echoedvoice = mv_mod.Echoedvoice

# Attach packages
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
pkg_battle.engine = eng_mod
pkg_battle.battledata = bd_mod
sys.modules["pokemon.battle"] = pkg_battle

data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# Minimal MoveDex entry
move_entry = types.SimpleNamespace(
    name="Echoed Voice",
    type="Normal",
    category="Special",
    power=40,
    accuracy=100,
    raw={
        "priority": 0,
        "onTry": "Echoedvoice.onTry",
        "basePowerCallback": "Echoedvoice.basePowerCallback",
        "condition": {"duration": 2, "onFieldStart": "Echoedvoice.onFieldStart", "onFieldRestart": "Echoedvoice.onFieldRestart"},
    },
)

pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.MOVEDEX = {"echoedvoice": move_entry}
pokemon_dex.entities = importlib.import_module("pokemon.dex.entities")
pokemon_dex.Move = pokemon_dex.entities.Move
pokemon_dex.Pokemon = pokemon_dex.entities.Pokemon
Pokemon = bd_mod.Pokemon
Move = bd_mod.Move
sys.modules["pokemon.dex"] = pokemon_dex
sys.modules["pokemon.dex.functions.moves_funcs"] = mv_mod

dam_spec = importlib.util.spec_from_file_location(
    "pokemon.battle.damage", os.path.join(ROOT, "pokemon", "battle", "damage.py")
)
dam_mod = importlib.util.module_from_spec(dam_spec)
sys.modules[dam_spec.name] = dam_mod
dam_spec.loader.exec_module(dam_mod)
pkg_battle.damage_calc = dam_mod.damage_calc


def test_ontry_creates_field_effect():
    battle = eng_mod.Battle(eng_mod.BattleType.WILD, [])
    user = Pokemon("User")
    target = Pokemon("Target")
    stats = types.SimpleNamespace(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    user.base_stats = stats
    target.base_stats = stats
    user.num = 1
    target.num = 2
    user.types = ["Normal"]
    target.types = ["Normal"]
    move = eng_mod.BattleMove(
        name="Echoed Voice",
        power=40,
        onTry=Echoedvoice().onTry,
        type="Normal",
    )
    move.execute(user, target, battle)
    assert battle.field.get_pseudo_weather("echoedvoice") is not None


def test_base_power_scales_with_multiplier():
    battle = eng_mod.Battle(eng_mod.BattleType.WILD, [])
    battle.field.add_pseudo_weather("echoedvoice", {"duration": 2, "multiplier": 3})
    user = Pokemon("User")
    target = Pokemon("Target")
    stats = types.SimpleNamespace(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    user.base_stats = stats
    target.base_stats = stats
    user.num = 1
    target.num = 2
    user.types = ["Normal"]
    target.types = ["Normal"]
    move_obj = types.SimpleNamespace(basePower=40, power=40)
    power = Echoedvoice().basePowerCallback(user, target, move_obj, battle=battle)
    assert power == 120
