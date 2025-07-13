import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Provide a minimal evennia stub so pokemon.battle modules import cleanly
evennia = sys.modules.get("evennia")
if evennia is None:
    evennia = types.ModuleType("evennia")
    sys.modules["evennia"] = evennia
if not hasattr(evennia, "create_object"):
    evennia.create_object = lambda *a, **k: None
if not hasattr(evennia, "search_object"):
    evennia.search_object = lambda *a, **k: []
if not hasattr(evennia, "DefaultRoom"):
    evennia.DefaultRoom = type("DefaultRoom", (), {})
if not hasattr(evennia, "objects"):
    evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
if not hasattr(evennia, "utils"):
    evennia.utils = types.ModuleType("evennia.utils")
    sys.modules["evennia.utils"] = evennia.utils
if not hasattr(evennia.utils, "ansi"):
    evennia.utils.ansi = types.SimpleNamespace(
        parse_ansi=lambda s: s,
        RED=lambda s: s,
        GREEN=lambda s: s,
        YELLOW=lambda s: s,
        BLUE=lambda s: s,
        MAGENTA=lambda s: s,
        CYAN=lambda s: s,
        strip_ansi=lambda s: s,
    )
if not hasattr(evennia, "server"):
    evennia.server = types.ModuleType("evennia.server")
    evennia.server.models = types.ModuleType("evennia.server.models")
    evennia.server.models.ServerConfig = type("ServerConfig", (), {})
    sys.modules["evennia.server"] = evennia.server
    sys.modules["evennia.server.models"] = evennia.server.models

if "typeclasses.rooms" not in sys.modules:
    rooms_mod = types.ModuleType("typeclasses.rooms")
    rooms_mod.Room = type("Room", (), {})
    sys.modules["typeclasses.rooms"] = rooms_mod

if "typeclasses.battleroom" not in sys.modules:
    battleroom_mod = types.ModuleType("typeclasses.battleroom")
    battleroom_mod.BattleRoom = type("BattleRoom", (), {})
    sys.modules["typeclasses.battleroom"] = battleroom_mod

# Setup minimal package hierarchy with stubs
pkg_root = types.ModuleType('pokemon')
pkg_root.__path__ = []

utils_stub = types.ModuleType('pokemon.battle.utils')
utils_stub.get_modified_stat = lambda p, s: getattr(p.base_stats, s, 0)
utils_stub.apply_boost = lambda *a, **k: None

pkg_battle = types.ModuleType('pokemon.battle')
pkg_battle.__path__ = []
pkg_battle.__spec__ = importlib.util.spec_from_loader('pokemon.battle', loader=None, is_package=True)
pkg_battle.utils = utils_stub
pkg_root.battle = pkg_battle

sys.modules['pokemon'] = pkg_root
sys.modules['pokemon.battle'] = pkg_battle
sys.modules['pokemon.battle.utils'] = utils_stub

# Load entity dataclasses
ent_path = os.path.join(ROOT, 'pokemon', 'dex', 'entities.py')
ent_spec = importlib.util.spec_from_file_location('pokemon.dex.entities', ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats
Move = ent_mod.Move
PokemonData = ent_mod.Pokemon

pokemon_dex = types.ModuleType('pokemon.dex')
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.Move = Move
pokemon_dex.Pokemon = PokemonData
pokemon_dex.MOVEDEX = {}

pkg_root.dex = pokemon_dex
sys.modules['pokemon.dex'] = pokemon_dex

# Minimal TYPE_CHART for effectiveness (not used here)
data_stub = types.ModuleType('pokemon.data')
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules['pokemon.data'] = data_stub

# Load damage module
d_path = os.path.join(ROOT, 'pokemon', 'battle', 'damage.py')
d_spec = importlib.util.spec_from_file_location('pokemon.battle.damage', d_path)
d_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = d_mod
d_spec.loader.exec_module(d_mod)

# Helper to run a simple damage calculation
StatsBase = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
species = PokemonData('Charmander', num=4, types=['Fire'], base_stats=StatsBase)

random.seed(0)

def run(use_types):
    user = types.SimpleNamespace(name='User', num=1, base_stats=StatsBase, species=species)
    if use_types:
        user.types = ['Fire']
    target = types.SimpleNamespace(name='Target', num=2, base_stats=StatsBase, types=['Grass'])
    move = Move('Ember', num=0, type='Fire', category='Special', power=40, accuracy=100, pp=None, raw={})
    res = d_mod.damage_calc(user, target, move)
    return sum(res.debug.get('damage', []))


def test_stab_falls_back_to_species_types():
    dmg_without_attr = run(False)
    dmg_with_attr = run(True)
    assert dmg_without_attr == dmg_with_attr

# Cleanup imported modules so other tests use real packages
for mod in [
    'pokemon', 'pokemon.battle', 'pokemon.battle.utils',
    'pokemon.dex', 'pokemon.dex.entities', 'pokemon.data',
    'pokemon.battle.damage']:
    sys.modules.pop(mod, None)

