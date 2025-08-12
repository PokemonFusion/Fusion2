import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Store originals
try:
    import evennia  # type: ignore
    orig_create_object = evennia.create_object
except Exception:
    evennia = types.ModuleType("evennia")
    orig_create_object = lambda cls, key=None: cls()
    evennia.create_object = orig_create_object
    evennia.DefaultRoom = type("DefaultRoom", (), {})
    evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
    evennia.utils = types.ModuleType("evennia.utils")
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
    sys.modules["evennia.utils"] = evennia.utils
    evennia.server = types.ModuleType("evennia.server")
    evennia.server.models = types.ModuleType("evennia.server.models")
    evennia.server.models.ServerConfig = type("ServerConfig", (), {})
    sys.modules["evennia.server"] = evennia.server
    sys.modules["evennia.server.models"] = evennia.server.models
    sys.modules["evennia"] = evennia
else:
    evennia.create_object = lambda cls, key=None: cls()
orig_models_pkg = sys.modules.get("pokemon.models")
orig_models_core = sys.modules.get("pokemon.models.core")
orig_generation = sys.modules.get("pokemon.generation")
orig_spawn = sys.modules.get("helpers.pokemon_spawn")
orig_capture = sys.modules.get("pokemon.battle.capture")

battleroom_mod = types.ModuleType("typeclasses.rooms")
class BattleRoom:
    def __init__(self, key=None):
        self.key = key
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.locks = types.SimpleNamespace(add=lambda *a, **k: None)
    def delete(self):
        pass
battleroom_mod.BattleRoom = BattleRoom
battleroom_mod.MapRoom = type("MapRoom", (), {})
battleroom_mod.Room = type("Room", (), {})

# Interface and handler stubs
iface = types.ModuleType("pokemon.battle.interface")
iface.display_battle_interface = lambda *a, **k: ""
iface.format_turn_banner = lambda turn: ""
iface.render_interfaces = lambda *a, **k: ("", "", "")
sys.modules["pokemon.battle.interface"] = iface
watchers = types.ModuleType("pokemon.battle.watchers")
watchers.add_watcher = lambda *a, **k: None
watchers.remove_watcher = lambda *a, **k: None
watchers.notify_watchers = lambda *a, **k: None
watchers.WatcherManager = type(
    "WatcherManager",
    (),
    {
        "add_watcher": lambda self, w: None,
        "remove_watcher": lambda self, w: None,
        "notify": lambda self, m: None,
        "add_observer": lambda self, w: None,
        "remove_observer": lambda self, w: None,
    },
)
sys.modules["pokemon.battle.watchers"] = watchers

handler_mod = types.ModuleType("pokemon.battle.handler")
handler_mod.battle_handler = types.SimpleNamespace(register=lambda *a, **k: None,
                                                   unregister=lambda *a, **k: None,
                                                   restore=lambda *a, **k: None,
                                                   save=lambda *a, **k: None,
                                                   next_id=lambda: 1)

# Pokemon model stub
class FakeCollection:
    def __init__(self):
        self.items = []
    def add(self, obj):
        self.items.append(obj)
    def all(self):
        return self.items

class FakeManager:
    def __init__(self):
        self.store = {}
        self.counter = 1
    def create(self, **kwargs):
        if "name" in kwargs and "species" not in kwargs:
            kwargs["species"] = kwargs.pop("name")
        obj = FakeOwnedPokemon(**kwargs)
        obj.id = self.counter
        self.counter += 1
        self.store[obj.unique_id] = obj
        return obj
    def get(self, uid):
        return self.store[uid]

    def filter(self, **kwargs):
        manager = self

        class _QuerySet:
            def delete(self_inner):
                to_delete = []
                for obj in manager.store.values():
                    match = True
                    for k, v in kwargs.items():
                        attr = k.split("__")[0]
                        if getattr(obj, attr, None) != v:
                            match = False
                            break
                    if match:
                        to_delete.append(obj.unique_id)
                for uid in to_delete:
                    manager.store.pop(uid, None)

            def filter(self_inner, **kw):
                return manager.filter(**kw)

        return _QuerySet()

class FakeOwnedPokemon:
    objects = FakeManager()

    def __init__(
        self,
        species,
        level=1,
        trainer=None,
        ability=None,
        nature=None,
        gender=None,
        ivs=None,
        evs=None,
        is_wild=False,
        ai_trainer=None,
        is_template=False,
        is_battle_instance=False,
        current_hp=10,
    ):
        self.species = species
        self.level = level
        self.trainer = trainer
        self.is_wild = is_wild
        self.ai_trainer = ai_trainer
        self.is_template = is_template
        self.is_battle_instance = is_battle_instance
        self.ability = ability
        self.nature = nature
        self.gender = gender
        self.ivs = ivs or [0]*6
        self.evs = evs or [0]*6
        self.unique_id = str(self.__class__.objects.counter)
        self.current_hp = current_hp

    @property
    def computed_level(self):
        return self.level

    def set_level(self, lvl):
        self.level = lvl

    def heal(self):
        pass

    def learn_level_up_moves(self, *args, **kwargs):
        pass

    def save(self):
        pass

    def delete(self):
        self.__class__.objects.store.pop(self.unique_id, None)

    def delete_if_wild(self):
        if self.is_wild and self.trainer is None and self.ai_trainer is None:
            self.delete()

models_pkg = types.ModuleType("pokemon.models")
models_mod_core = types.ModuleType("pokemon.models.core")
models_mod_core.OwnedPokemon = FakeOwnedPokemon
models_pkg.core = models_mod_core

# Generation and stats stubs
class DummyInst:
    def __init__(self, name, level):
        self.species = types.SimpleNamespace(name=name, types=["Electric"])
        self.level = level
        self.stats = types.SimpleNamespace(hp=10)
        self.moves = ["tackle"]
        self.ability = None

gen_mod = types.ModuleType("pokemon.generation")

def generate_pokemon(name, level=5):
    return DummyInst(name, level)

gen_mod.generate_pokemon = generate_pokemon
gen_mod.NATURES = {}

spawn_mod = types.ModuleType("helpers.pokemon_spawn")
spawn_mod.get_spawn = lambda loc: None

# ------------------------------------------------------------
# Test setup/teardown
# ------------------------------------------------------------

def setup_module(module):
    evennia.create_object = lambda cls, key=None: cls()
    pokemon_pkg = types.ModuleType("pokemon")
    pokemon_pkg.__path__ = []
    pokemon_pkg.generation = gen_mod
    pokemon_pkg.models = models_pkg
    pokemon_pkg.breeding = types.ModuleType("pokemon.breeding")
    dex_mod = types.ModuleType("pokemon.dex")
    dex_mod.MOVEDEX = {"tackle": {"pp": 10}}
    dex_mod.POKEDEX = {}
    pokemon_pkg.dex = dex_mod
    sys.modules["pokemon"] = pokemon_pkg
    sys.modules["pokemon.breeding"] = pokemon_pkg.breeding
    sys.modules["pokemon.dex"] = dex_mod
    sys.modules["typeclasses.rooms"] = battleroom_mod
    sys.modules["pokemon.battle.interface"] = iface
    sys.modules["pokemon.battle.handler"] = handler_mod
    sys.modules["pokemon.models"] = models_pkg
    sys.modules["pokemon.models.core"] = models_mod_core
    sys.modules["pokemon.generation"] = gen_mod
    sys.modules["helpers.pokemon_spawn"] = spawn_mod

    cap_path = os.path.join(ROOT, "pokemon", "battle", "capture.py")
    cap_spec = importlib.util.spec_from_file_location("pokemon.battle.capture", cap_path)
    cap_mod = importlib.util.module_from_spec(cap_spec)
    sys.modules[cap_spec.name] = cap_mod
    cap_spec.loader.exec_module(cap_mod)
    cap_mod.attempt_capture = lambda *a, **k: True
    sys.modules["pokemon.battle.capture"] = cap_mod

    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    module.bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = module.bd_mod
    bd_spec.loader.exec_module(module.bd_mod)
    module.Pokemon = module.bd_mod.Pokemon

    st_path = os.path.join(ROOT, "pokemon", "battle", "state.py")
    st_spec = importlib.util.spec_from_file_location("pokemon.battle.state", st_path)
    module.st_mod = importlib.util.module_from_spec(st_spec)
    sys.modules[st_spec.name] = module.st_mod
    st_spec.loader.exec_module(module.st_mod)

    eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
    eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
    module.engine = importlib.util.module_from_spec(eng_spec)
    sys.modules[eng_spec.name] = module.engine
    eng_spec.loader.exec_module(module.engine)
    module.Battle = module.engine.Battle
    module.BattleParticipant = module.engine.BattleParticipant
    module.Action = module.engine.Action
    module.ActionType = module.engine.ActionType
    module.BattleType = module.engine.BattleType

    bi_path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
    bi_spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", bi_path)
    module.bi_mod = importlib.util.module_from_spec(bi_spec)
    sys.modules[bi_spec.name] = module.bi_mod
    bi_spec.loader.exec_module(module.bi_mod)
    module.BattleSession = module.bi_mod.BattleSession

# Dummy classes
class DummyStorage:
    def __init__(self):
        self.active_pokemon = types.SimpleNamespace(all=lambda: [])
        self.stored_pokemon = FakeCollection()

class DummyRoom:
    def __init__(self):
        self.db = types.SimpleNamespace(weather="clear")
        self.ndb = types.SimpleNamespace()

class DummyAttr(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)

class DummyPlayer:
    def __init__(self):
        self.key = "Player"
        self.id = 1
        self.db = types.SimpleNamespace()
        self.ndb = DummyAttr()
        self.location = DummyRoom()
        self.storage = DummyStorage()
        self.trainer = "trainer"
    def msg(self, *a, **k):
        pass
    def move_to(self, room, quiet=False):
        self.location = room

import pytest


@pytest.mark.skip("requires full battle system")
def test_temp_pokemon_persists_after_restore():
    random_choice = bi_mod.random.choice
    bi_mod.random.choice = lambda opts: "pokemon"
    player = DummyPlayer()
    inst = BattleSession(player)
    inst.start()
    pid = inst.temp_pokemon_ids[0] if inst.temp_pokemon_ids else next(iter(FakeOwnedPokemon.objects.store))
    assert pid in FakeOwnedPokemon.objects.store
    restored = BattleSession.restore(inst.room, inst.battle_id)
    assert pid in restored.temp_pokemon_ids or pid in FakeOwnedPokemon.objects.store
    bi_mod.random.choice = random_choice


def test_capture_converts_pokemon():
    wild_db = FakeOwnedPokemon.objects.create(species="Bulbasaur", level=5, is_wild=True)
    wild = Pokemon("Bulbasaur", hp=1, max_hp=10, model_id=wild_db.unique_id)
    attacker = Pokemon("Pikachu")
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [wild], is_ai=False)
    p1.active = [attacker]
    p2.active = [wild]
    p1.trainer = "trainer"
    p1.storage = types.SimpleNamespace(stored_pokemon=FakeCollection())
    action = Action(p1, ActionType.ITEM, p2, item="Pokeball", priority=6)
    p1.pending_action = action
    random.seed(0)
    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()
    dbpoke = FakeOwnedPokemon.objects.get(wild_db.unique_id)
    assert dbpoke is not None


@pytest.mark.skip("requires full battle system")
def test_uncaught_pokemon_deleted_on_end():
    random_choice = bi_mod.random.choice
    bi_mod.random.choice = lambda opts: "pokemon"
    player = DummyPlayer()
    inst = BattleSession(player)
    inst.start()
    pid = inst.temp_pokemon_ids[0] if inst.temp_pokemon_ids else next(iter(FakeOwnedPokemon.objects.store))
    inst.end()
    bi_mod.random.choice = random_choice

def teardown_module(module):
    evennia.create_object = orig_create_object
    if orig_models_pkg is not None:
        sys.modules["pokemon.models"] = orig_models_pkg
    else:
        sys.modules.pop("pokemon.models", None)
    if orig_models_core is not None:
        sys.modules["pokemon.models.core"] = orig_models_core
    else:
        sys.modules.pop("pokemon.models.core", None)
    if orig_generation is not None:
        sys.modules["pokemon.generation"] = orig_generation
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_spawn is not None:
        sys.modules["helpers.pokemon_spawn"] = orig_spawn
    else:
        sys.modules.pop("helpers.pokemon_spawn", None)
    if orig_capture is not None:
        sys.modules["pokemon.battle.capture"] = orig_capture
    else:
        sys.modules.pop("pokemon.battle.capture", None)
